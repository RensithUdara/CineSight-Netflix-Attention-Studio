"""
Netflix Seek Test
=================
Controls Netflix playback (seek, play, pause, toggle) by injecting
JavaScript into an open Netflix tab.

macOS uses AppleScript to talk to Chrome. Windows uses the Chrome DevTools
Protocol, so Chrome must be launched with --remote-debugging-port=9222.

Usage:
  python netflix_seek_test.py --play
  python netflix_seek_test.py --pause
  python netflix_seek_test.py --toggle
  python netflix_seek_test.py --get-time
  python netflix_seek_test.py --minutes 18 --seconds 30
  python netflix_seek_test.py --time 1091243
  python netflix_seek_test.py --check

Chrome must have a Netflix tab open with a video loaded.
"""

import subprocess
import argparse
import sys
import time


# The injected script writes command results into this shared DOM attribute.
_ATTR = "data-nf-result"

def _nf_js(action: str) -> str:
    """
    Build a script that finds the Netflix player and runs a small action.

    The action can use `pl` for the Netflix player object and `_set(value)`
    to return data through the shared DOM attribute.
    """
    return (
        f"var _set=function(v){{document.body.setAttribute('{_ATTR}',v);}};"
        f"try{{"
        f"  var vp=netflix.appContext.state.playerApp.getAPI().videoPlayer;"
        f"  var pl=vp.getVideoPlayerBySessionId(vp.getAllPlayerSessionIds()[0]);"
        f"  {action}"
        f"}}catch(e){{_set('ERROR:'+e.message);}}"
    )


# Reusable playback commands sent through the platform-specific executors.
_JS_CHECK  = _nf_js("_set('OK:'+pl.getCurrentTime());")
_JS_TIME   = _nf_js("_set('TIME:'+pl.getCurrentTime());")
_JS_PLAY   = _nf_js("pl.play();  _set('PLAYING');")
_JS_PAUSE  = _nf_js("pl.pause(); _set('PAUSED');")
_JS_TOGGLE = _nf_js(
    "if(pl.isPaused()){pl.play(); _set('TOGGLED:PLAYING');}"
    "else{pl.pause(); _set('TOGGLED:PAUSED');}"
)

def _js_seek(ms: int) -> str:
    return _nf_js(f"pl.seek({ms}); _set('SEEKED_TO:{ms}');")


def _inject_and_read_mac(inner_js: str) -> str:
    """
    Execute a command in the Netflix tab through AppleScript.

    AppleScript's direct JavaScript execution runs in Chrome's isolated world,
    so the command is injected as a page script and read back from the DOM.
    """
    def esc(js: str) -> str:
        """Escape JS for embedding inside an AppleScript double-quoted string."""
        return js.replace("\\", "\\\\").replace('"', '\\"')

    # Inject a self-removing script tag so the command runs in the page world.
    inject_js = (
        "(function(){"
        "var s=document.createElement('script');"
        "s.textContent=" + repr(inner_js) + ";"
        "document.body.appendChild(s);s.remove();"
        "})();"
    )
    # Read the shared result attribute back from Chrome's isolated world.
    read_js = f"document.body.getAttribute('{_ATTR}');"

    script = f'''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "netflix.com" then
                    execute t javascript "{esc(inject_js)}"
                    set r to execute t javascript "{esc(read_js)}"
                    return r as string
                end if
            end repeat
        end repeat
    end tell
    return "NO_TAB"
    '''
    result = subprocess.run(["osascript", "-e", script],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    output = result.stdout.strip()
    if output == "NO_TAB":
        raise RuntimeError(
            "No Netflix tab found in Chrome — open Netflix first!")
    return output


def _inject_and_read_windows(inner_js: str) -> str:
    """Execute a command in the Netflix tab through Chrome DevTools."""
    import urllib.request
    import json
    try:
        import websocket
    except ImportError:
        raise RuntimeError("Please install dependencies: pip install -r requirements.txt")

    try:
        req = urllib.request.Request("http://127.0.0.1:9222/json")
        with urllib.request.urlopen(req) as response:
            tabs = json.loads(response.read().decode())
        
        n_tab = next((t for t in tabs if 'url' in t and 'netflix.com' in t['url'].lower()), None)
        if not n_tab:
            raise RuntimeError("No Netflix tab found in Chrome — open Netflix first!")
            
        ws_url = n_tab.get('webSocketDebuggerUrl')
        if not ws_url:
            raise RuntimeError("Netflix tab found, but no WebSocket URL (Chrome not debuggable?)")
            
        ws = websocket.create_connection(ws_url)
        
        # DevTools evaluates this wrapper in the target Netflix tab.
        inject_js = (
            "(function(){"
            "var s=document.createElement('script');"
            "s.textContent=" + json.dumps(inner_js) + ";"
            "document.body.appendChild(s);s.remove();"
            f"return document.body.getAttribute('{_ATTR}');"
            "})();"
        )
        
        payload = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": inject_js,
                "returnByValue": True
            }
        }
        ws.send(json.dumps(payload))
        result = json.loads(ws.recv())
        ws.close()
        
        if 'result' in result and 'result' in result['result']:
            val = result['result']['result'].get('value')
            if val is not None:
                return str(val)
        return "ERROR: CDP Evaluation failed"
        
    except urllib.error.URLError:
        raise RuntimeError("Could not connect to Chrome. Did you start it with --remote-debugging-port=9222?")


def inject_and_read(inner_js: str) -> str:
    import platform
    if platform.system() == "Windows":
        return _inject_and_read_windows(inner_js)
    else:
        return _inject_and_read_mac(inner_js)


# High-level player actions.

def _ms_to_mmss(ms_str: str) -> str:
    sec = int(float(ms_str)) // 1000
    m, s = divmod(sec, 60)
    return f"{m:02d}:{s:02d}"


def check_player() -> bool:
    """Verify the Netflix player API is reachable. Returns True if OK."""
    print("[*] Checking Netflix player API…")
    r = inject_and_read(_JS_CHECK)
    if r.startswith("OK:"):
        ms = r[3:]
        print(f"    [OK]  Player found!  Position: {_ms_to_mmss(ms)}  ({ms} ms)")
        return True
    print(f"    [FAIL]  Player check failed: {r}")
    return False


def get_current_time():
    """Print the current playback position."""
    print("[*] Fetching current position…")
    r = inject_and_read(_JS_TIME)
    if r.startswith("TIME:"):
        ms = r[5:]
        print(f"    {_ms_to_mmss(ms)}  ({ms} ms)")
    else:
        print(f"    [FAIL]  {r}")


def play_video():
    print("[*] Sending play…")
    r = inject_and_read(_JS_PLAY)
    if r == "PLAYING":
        print("    Playing.")
    else:
        print(f"    [FAIL]  Play failed: {r}"); sys.exit(1)


def pause_video():
    print("[*] Sending pause…")
    r = inject_and_read(_JS_PAUSE)
    if r == "PAUSED":
        print("    Paused.")
    else:
        print(f"    [FAIL]  Pause failed: {r}"); sys.exit(1)


def toggle_playback():
    print("[*] Toggling play/pause…")
    r = inject_and_read(_JS_TOGGLE)
    if r == "TOGGLED:PLAYING":
        print("    Was paused -> now playing.")
    elif r == "TOGGLED:PAUSED":
        print("    Was playing -> now paused.")
    else:
        print(f"    [FAIL]  Toggle failed: {r}"); sys.exit(1)


def seek_to(ms: int):
    print(f"[*] Seeking to {_ms_to_mmss(str(ms * 1000))}  ({ms} ms)…")
    r = inject_and_read(_js_seek(ms))
    if r.startswith("SEEKED_TO:"):
        print("    Seek sent.")
    else:
        print(f"    [FAIL]  Seek failed: {r}"); sys.exit(1)


def parse_args():
    """Parse command-line playback and seek options."""
    p = argparse.ArgumentParser(
        description="Control Netflix playback via JS injection (no extra libs).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python netflix_seek_test.py --play
  python netflix_seek_test.py --pause
  python netflix_seek_test.py --toggle
  python netflix_seek_test.py --get-time
  python netflix_seek_test.py --minutes 18 --seconds 30
  python netflix_seek_test.py --time 1091243
  python netflix_seek_test.py --check
        """
    )
    p.add_argument("--play",       action="store_true", help="Resume playback")
    p.add_argument("--pause",      action="store_true", help="Pause playback")
    p.add_argument("--toggle",     action="store_true", help="Toggle play/pause")
    p.add_argument("--get-time",   action="store_true", help="Print current position")
    p.add_argument("--check",      action="store_true", help="Check player API accessibility")
    p.add_argument("--time",       type=int, metavar="MS",  help="Seek to millisecond offset")
    p.add_argument("--minutes",    type=int, default=0, metavar="MIN")
    p.add_argument("--seconds",    type=int, default=0, metavar="SEC")
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 55)
    print("  Netflix Player Control")
    print("=" * 55)

    try:
        if args.check:
            sys.exit(0 if check_player() else 1)

        if args.get_time:
            get_current_time(); sys.exit(0)

        if args.play:
            play_video(); sys.exit(0)

        if args.pause:
            pause_video(); sys.exit(0)

        if args.toggle:
            toggle_playback(); sys.exit(0)

        # Resolve the requested seek target, if any.
        if args.time is not None:
            target_ms = args.time
        elif args.minutes or args.seconds:
            target_ms = (args.minutes * 60 + args.seconds) * 1000
        else:
            # Interactive fallback for manual terminal use.
            print("\nNo target provided.")
            print("  m = MM:SS   t = raw milliseconds")
            choice = input("Choice [m/t]: ").strip().lower()
            if choice == "m":
                ts = input("MM:SS : ").strip().split(":")
                if len(ts) != 2:
                    print("Bad format."); sys.exit(1)
                target_ms = (int(ts[0]) * 60 + int(ts[1])) * 1000
            else:
                target_ms = int(input("Milliseconds: ").strip())

        if not check_player():
            print("\n[!] Make sure Chrome has a Netflix video open and loaded.")
            sys.exit(1)

        seek_to(target_ms)
        time.sleep(0.8)
        get_current_time()
        print("\n[Done]")

    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
