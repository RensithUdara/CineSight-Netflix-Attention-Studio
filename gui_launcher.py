import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import URLError
from urllib.request import urlopen


APP_TITLE = "Netflix Attention Studio"
ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe" if platform.system() == "Windows" else ROOT / ".venv" / "bin" / "python"
DEBUG_PROFILE = ROOT / ".chrome-debug-profile"
DEBUG_URL = "http://127.0.0.1:9222/json/version"


class AttentionLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x680")
        self.minsize(940, 620)
        self.configure(bg="#09090c")

        self.controller = None
        self.reader_thread = None
        self.log_queue = queue.Queue()
        self.mode = tk.StringVar(value="single")
        self.status = tk.StringVar(value="Ready")
        self.chrome_status = tk.StringVar(value="Chrome debug: checking")

        self.camera_index = tk.IntVar(value=0)
        self.digital_zoom = tk.DoubleVar(value=2.0)
        self.yaw_threshold = tk.DoubleVar(value=25.0)
        self.pitch_threshold = tk.DoubleVar(value=20.0)
        self.away_grace = tk.DoubleVar(value=1.5)
        self.back_grace = tk.DoubleVar(value=0.8)
        self.min_absent = tk.DoubleVar(value=2.0)

        self._build_style()
        self._build_ui()
        self._poll_log()
        self._poll_process()
        self.after(300, self.refresh_chrome_status)

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#09090c", foreground="#f5f5f6", font=("Segoe UI", 10))
        style.configure("TFrame", background="#09090c")
        style.configure("Hero.TFrame", background="#b00610")
        style.configure("AccentLine.TFrame", background="#e50914")
        style.configure("Panel.TFrame", background="#17171d", relief="flat")
        style.configure("Toolbar.TFrame", background="#17171d")
        style.configure("TLabel", background="#09090c", foreground="#f5f5f6")
        style.configure("Muted.TLabel", background="#09090c", foreground="#b7bdc9")
        style.configure("Panel.TLabel", background="#17171d", foreground="#f5f5f6")
        style.configure("MutedPanel.TLabel", background="#17171d", foreground="#aeb4c2")
        style.configure("Title.TLabel", background="#09090c", foreground="#ffffff", font=("Segoe UI Semibold", 26))
        style.configure("Subtitle.TLabel", background="#09090c", foreground="#c8ceda", font=("Segoe UI", 11))
        style.configure("Hero.TLabel", background="#b00610", foreground="#ffffff", font=("Segoe UI Semibold", 12), padding=(14, 9))
        style.configure("Status.TLabel", background="#24242d", foreground="#f0f3fa", padding=(12, 8))
        style.configure("TButton", background="#2b2d38", foreground="#f7f7f8", borderwidth=0, padding=(14, 10), font=("Segoe UI Semibold", 10))
        style.map("TButton", background=[("active", "#393c4a"), ("disabled", "#1d1e25")], foreground=[("disabled", "#777d8d")])
        style.configure("Primary.TButton", background="#e50914", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#ff1f2c"), ("pressed", "#99050d"), ("disabled", "#4d1519")])
        style.configure("Chrome.TButton", background="#d19a16", foreground="#141414")
        style.map("Chrome.TButton", background=[("active", "#f4b929"), ("pressed", "#9d710d")])
        style.configure("Danger.TButton", background="#7f121a", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b01622"), ("pressed", "#530b10")])
        style.configure("Restart.TButton", background="#6f42c1", foreground="#ffffff")
        style.map("Restart.TButton", background=[("active", "#8457d6"), ("pressed", "#4f2b91")])
        style.configure("Check.TButton", background="#00a8cc", foreground="#071013")
        style.map("Check.TButton", background=[("active", "#33d6f5"), ("pressed", "#08788f")])
        style.configure("Play.TButton", background="#1db954", foreground="#06120a")
        style.map("Play.TButton", background=[("active", "#35d46e"), ("pressed", "#11843a")])
        style.configure("Pause.TButton", background="#ffb020", foreground="#15100a")
        style.map("Pause.TButton", background=[("active", "#ffc85a"), ("pressed", "#bd7a00")])
        style.configure("Toggle.TButton", background="#ff4d8d", foreground="#ffffff")
        style.map("Toggle.TButton", background=[("active", "#ff75a8"), ("pressed", "#bf2b62")])
        style.configure("Time.TButton", background="#4f7cff", foreground="#ffffff")
        style.map("Time.TButton", background=[("active", "#7598ff"), ("pressed", "#3159c9")])
        style.configure("Mode.TRadiobutton", background="#211c21", foreground="#f5f5f6", padding=(12, 10), font=("Segoe UI Semibold", 10))
        style.map("Mode.TRadiobutton", background=[("active", "#302331"), ("selected", "#3a1519")], foreground=[("selected", "#ffffff")])
        style.configure("Horizontal.TScale", background="#17171d", troughcolor="#34313a")

    def _build_ui(self):
        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Launch Chrome, choose viewer count, tune attention behavior, and control Netflix from one place.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))
        ttk.Frame(root, style="AccentLine.TFrame", height=4).pack(fill="x", pady=(0, 16))
        ttk.Label(root, text="SMART VIEWING CONTROL", style="Hero.TLabel").pack(fill="x", pady=(0, 16))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Panel.TFrame", padding=(20, 20, 12, 20))
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        right = ttk.Frame(body, style="Panel.TFrame", padding=20)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(4, weight=1)
        right.columnconfigure(0, weight=1)

        controls = self._build_scroll_area(left)
        self._build_controls(controls)
        self._build_monitor(right)

    def _build_scroll_area(self, parent):
        """Create a scrollable settings column for compact laptop screens."""
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        canvas = tk.Canvas(
            parent,
            width=250,
            bg="#17171d",
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, style="Panel.TFrame")

        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        def update_scroll_region(_event=None):
            """Keep the scrollbar range synced with the content height."""
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_content(event):
            """Match the embedded frame width to the visible canvas width."""
            canvas.itemconfigure(window_id, width=event.width)

        def on_mousewheel(event):
            """Scroll only while the pointer is over the settings panel."""
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_content)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        return content

    def _build_controls(self, parent):
        ttk.Label(parent, text="Viewer Mode", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        mode_box = ttk.Frame(parent, style="Panel.TFrame")
        mode_box.pack(fill="x", pady=(8, 18))
        ttk.Radiobutton(
            mode_box,
            text="1 viewer",
            value="single",
            variable=self.mode,
            style="Mode.TRadiobutton",
            command=self._mode_changed,
        ).pack(side="left", fill="x", expand=True)
        ttk.Radiobutton(
            mode_box,
            text="2 viewers",
            value="two",
            variable=self.mode,
            style="Mode.TRadiobutton",
            command=self._mode_changed,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._slider(parent, "Camera", self.camera_index, 0, 4, is_int=True)
        self._slider(parent, "Digital zoom", self.digital_zoom, 1.0, 3.5)
        self._slider(parent, "Yaw tolerance", self.yaw_threshold, 10, 45)
        self._slider(parent, "Pitch tolerance", self.pitch_threshold, 10, 45)
        self._slider(parent, "Pause delay", self.away_grace, 0.3, 4.0)
        self._slider(parent, "Resume delay", self.back_grace, 0.2, 3.0)
        self._slider(parent, "Seek-back minimum", self.min_absent, 0.5, 6.0)

        ttk.Frame(parent, style="AccentLine.TFrame", height=3).pack(fill="x", pady=(18, 14))
        actions = ttk.Frame(parent, style="Panel.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Open Chrome", style="Chrome.TButton", command=self.launch_chrome).pack(fill="x")
        ttk.Button(actions, text="Start Controller", style="Primary.TButton", command=self.start_controller).pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Stop Controller", style="Danger.TButton", command=self.stop_controller).pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Restart", style="Restart.TButton", command=self.restart_controller).pack(fill="x", pady=(8, 0))

    def _build_monitor(self, parent):
        top = ttk.Frame(parent, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, textvariable=self.status, style="Status.TLabel").grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(top, textvariable=self.chrome_status, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        ttk.Label(parent, text="Playback", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).grid(row=1, column=0, sticky="nw", pady=(16, 8))
        playback = ttk.Frame(parent, style="Toolbar.TFrame")
        playback.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        for label, style_name, command in (
            ("Check Player", "Check.TButton", lambda: self.run_seek_command("--check")),
            ("Play", "Play.TButton", lambda: self.run_seek_command("--play")),
            ("Pause", "Pause.TButton", lambda: self.run_seek_command("--pause")),
            ("Toggle", "Toggle.TButton", lambda: self.run_seek_command("--toggle")),
            ("Current Time", "Time.TButton", lambda: self.run_seek_command("--get-time")),
        ):
            ttk.Button(playback, text=label, style=style_name, command=command).pack(side="left", padx=(0, 8))

        ttk.Label(parent, text="Live Log", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).grid(row=3, column=0, sticky="nw")
        log_frame = ttk.Frame(parent, style="Panel.TFrame")
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(
            log_frame,
            bg="#08080b",
            fg="#f2f3f5",
            insertbackground="#ffffff",
            relief="flat",
            wrap="word",
            height=12,
            font=("Consolas", 10),
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._write_log("Ready. Open Chrome, sign in to Netflix if needed, then start the controller.")

    def _slider(self, parent, label, variable, start, end, is_int=False):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(11, 0))

        header = ttk.Frame(row, style="Panel.TFrame")
        header.pack(fill="x")
        text = ttk.Label(header, text=label, style="MutedPanel.TLabel")
        text.pack(side="left", anchor="w")
        value = tk.Label(
            header,
            text="",
            bg="#2a1115",
            fg="#ffffff",
            padx=8,
            pady=2,
            font=("Segoe UI Semibold", 9),
        )
        value.pack(side="right")

        def update_value(*_):
            raw = variable.get()
            value.configure(text=str(int(raw)) if is_int else f"{raw:.1f}")

        scale = tk.Scale(
            row,
            from_=start,
            to=end,
            variable=variable,
            orient="horizontal",
            showvalue=False,
            resolution=1 if is_int else 0.1,
            bg="#17171d",
            fg="#ffffff",
            troughcolor="#3a2428",
            activebackground="#ff1f2c",
            highlightthickness=0,
            bd=0,
            sliderlength=22,
            width=12,
            command=lambda *_: update_value(),
        )
        scale.pack(fill="x", pady=(6, 0))
        variable.trace_add("write", update_value)
        update_value()

    def _mode_changed(self):
        self._write_log(f"Viewer mode set to {'2 viewers' if self.mode.get() == 'two' else '1 viewer'}.")
        if self.is_controller_running():
            self.restart_controller()

    def script_for_mode(self):
        """Pick the attention script that matches the selected viewer count."""
        if self.mode.get() == "two":
            return ROOT / "head" / "netflix_attention_2p.py"
        return ROOT / "head" / "netflix_attention.py"

    def env_for_controller(self):
        """Pass GUI tuning values to the controller without editing source files."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["NETFLIX_ATTENTION_CAMERA_INDEX"] = str(self.camera_index.get())
        env["NETFLIX_ATTENTION_DIGITAL_ZOOM"] = f"{self.digital_zoom.get():.2f}"
        env["NETFLIX_ATTENTION_YAW_THRESHOLD"] = f"{self.yaw_threshold.get():.1f}"
        env["NETFLIX_ATTENTION_PITCH_THRESHOLD"] = f"{self.pitch_threshold.get():.1f}"
        env["NETFLIX_ATTENTION_AWAY_GRACE"] = f"{self.away_grace.get():.2f}"
        env["NETFLIX_ATTENTION_BACK_GRACE"] = f"{self.back_grace.get():.2f}"
        env["NETFLIX_ATTENTION_MIN_ABSENT"] = f"{self.min_absent.get():.2f}"
        return env

    def find_python(self):
        """Prefer the project virtual environment, then fall back to this Python."""
        if PYTHON.exists():
            return str(PYTHON)
        return sys.executable

    def find_chrome(self):
        """Locate Chrome across the common Windows, macOS, and Linux paths."""
        candidates = []
        if platform.system() == "Windows":
            candidates.extend([
                Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ])
        elif platform.system() == "Darwin":
            candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
        else:
            return "google-chrome"
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def launch_chrome(self):
        chrome = self.find_chrome()
        if not chrome:
            messagebox.showerror(APP_TITLE, "Could not find Google Chrome.")
            return
        DEBUG_PROFILE.mkdir(exist_ok=True)
        args = [
            chrome,
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=9222",
            f"--user-data-dir={DEBUG_PROFILE}",
            "https://www.netflix.com/browse",
        ]
        try:
            subprocess.Popen(args, cwd=ROOT)
            self._write_log("Chrome launched with remote debugging on port 9222.")
            self.after(1200, self.refresh_chrome_status)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch Chrome:\n{exc}")

    def refresh_chrome_status(self):
        """Probe Chrome DevTools to show whether Netflix automation can connect."""
        try:
            with urlopen(DEBUG_URL, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
            browser = data.get("Browser", "Chrome")
            self.chrome_status.set(f"Chrome debug: online ({browser})")
        except (URLError, OSError, TimeoutError, json.JSONDecodeError):
            self.chrome_status.set("Chrome debug: offline")

    def start_controller(self):
        if self.is_controller_running():
            self._write_log("Controller is already running.")
            return
        script = self.script_for_mode()
        self.refresh_chrome_status()
        self._write_log(f"Starting {script.name}...")
        try:
            self.controller = subprocess.Popen(
                [self.find_python(), str(script)],
                cwd=ROOT,
                env=self.env_for_controller(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not start controller:\n{exc}")
            return
        self.status.set(f"Running: {'2 viewers' if self.mode.get() == 'two' else '1 viewer'}")
        self.reader_thread = threading.Thread(target=self._read_controller_output, daemon=True)
        self.reader_thread.start()

    def _read_controller_output(self):
        """Forward controller stdout into the Tk event loop through a queue."""
        if not self.controller or not self.controller.stdout:
            return
        for line in self.controller.stdout:
            self.log_queue.put(line.rstrip())

    def stop_controller(self):
        if not self.is_controller_running():
            self.status.set("Ready")
            self._write_log("Controller is not running.")
            return
        self._write_log("Stopping controller...")
        self.controller.terminate()
        try:
            self.controller.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.controller.kill()
            self.controller.wait(timeout=2)
        self.status.set("Stopped")

    def restart_controller(self):
        if self.is_controller_running():
            self.stop_controller()
        self.after(300, self.start_controller)

    def is_controller_running(self):
        """Return True while the attention controller subprocess is alive."""
        return self.controller is not None and self.controller.poll() is None

    def run_seek_command(self, flag):
        """Run a Netflix playback helper command without blocking the GUI."""
        def worker():
            cmd = [self.find_python(), str(ROOT / "netflix_seek_test.py"), flag]
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            self.log_queue.put(f"$ python netflix_seek_test.py {flag}")
            try:
                result = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                )
                output = (result.stdout + result.stderr).strip()
                self.log_queue.put(output or f"Command finished with exit code {result.returncode}.")
            except subprocess.TimeoutExpired:
                self.log_queue.put("Command timed out.")
            except OSError as exc:
                self.log_queue.put(f"Command failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _poll_process(self):
        """Refresh controller status and Chrome connectivity on a timer."""
        if self.controller is not None and self.controller.poll() is not None:
            code = self.controller.returncode
            self.status.set("Ready" if code == 0 else f"Controller exited ({code})")
            self.controller = None
        self.refresh_chrome_status()
        self.after(3000, self._poll_process)

    def _poll_log(self):
        """Drain background-thread log messages into the Tk text widget."""
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._write_log(line)
        self.after(100, self._poll_log)

    def _write_log(self, line):
        """Append a timestamped line to the live log panel."""
        stamp = time.strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{stamp}] {line}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def destroy(self):
        if self.is_controller_running():
            self.stop_controller()
        super().destroy()


if __name__ == "__main__":
    app = AttentionLauncher()
    app.mainloop()
