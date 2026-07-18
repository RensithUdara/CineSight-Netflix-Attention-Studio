# CineSight Netflix Attention Studio 🎬👀

An attention-aware Netflix controller that uses your webcam to understand whether viewers are watching, looking away, or missing from the camera frame. It can pause, resume, and seek back automatically so you do not miss important moments.

## ✨ Highlights

- 🎛️ **Custom GUI launcher** with Netflix-themed controls
- 👤 **Single-viewer mode** for one person watching
- 👥 **Two-viewer mode** for shared viewing
- 👀 **Head-pose attention detection** using MediaPipe Face Landmarker
- ⏸️ **Auto pause** when a visible viewer looks away
- ▶️ **Auto resume** when attention returns
- ⏪ **Seek-back on return** when a viewer leaves the camera frame
- 🔴 **Netflix-style dark UI** with colorful action buttons
- 🧪 **CLI playback tool** for play, pause, toggle, check, and seek
- ⚙️ **Tunable sensitivity** from the GUI

## 🧠 How It Works

CineSight watches the webcam feed and estimates head direction from MediaPipe facial landmarks.

It separates two different attention states:

- **Looking away:** face is visible, but head pose is outside the configured yaw or pitch tolerance. Netflix pauses after a short grace period.
- **Absent:** face is no longer visible. Netflix keeps playing, records the absence duration, and seeks back when the viewer returns.

In two-viewer mode, the app tracks the left and right faces as **P1** and **P2**. Playback decisions are based on the visible calibrated viewers, while seek-back timing runs when at least one viewer is absent.

## 🖥️ Project Structure

```text
.
├── gui_launcher.py              # Main desktop GUI
├── run_gui.bat                  # Windows launcher for the GUI
├── netflix_seek_test.py         # CLI Netflix playback controller
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
└── head/
    ├── netflix_attention.py     # Single-viewer attention controller
    ├── netflix_attention_2p.py  # Two-viewer attention controller
    └── face_landmarker.task     # MediaPipe model file
```

## 📦 Requirements

- 🐍 Python 3.10+
- 🌐 Google Chrome
- 📷 Webcam
- 🎞️ Netflix account and video loaded in Chrome
- 🪟 Windows recommended for the included GUI launcher

Python packages:

```text
opencv-python
mediapipe
numpy
websocket-client
```

## 🚀 Quick Start

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Install dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Open the GUI

Double-click:

```text
run_gui.bat
```

Or run manually:

```powershell
.venv\Scripts\python.exe gui_launcher.py
```

## 🎛️ GUI Features

The GUI is the easiest way to use the project.

### Viewer Mode

- 👤 **1 viewer** runs `head/netflix_attention.py`
- 👥 **2 viewers** runs `head/netflix_attention_2p.py`

Switching viewer mode while the controller is running automatically restarts the correct script.

### Action Buttons

- 🟡 **Open Chrome** launches Chrome with remote debugging enabled
- 🔴 **Start Controller** starts the selected attention mode
- 🟥 **Stop Controller** stops the camera/controller process
- 🟣 **Restart** restarts the active mode
- 🔵 **Check Player** tests whether Netflix is reachable
- 🟢 **Play** resumes Netflix
- 🟠 **Pause** pauses Netflix
- 🩷 **Toggle** switches play/pause
- 🔷 **Current Time** prints the current playback position

### Sensitivity Controls

- 📷 **Camera**: choose webcam index
- 🔎 **Digital zoom**: improve detection for distant faces
- ↔️ **Yaw tolerance**: left/right head-turn sensitivity
- ↕️ **Pitch tolerance**: up/down head-tilt sensitivity
- ⏱️ **Pause delay**: time before pausing when looking away
- ⚡ **Resume delay**: time before resuming when attention returns
- ⏪ **Seek-back minimum**: minimum absence needed before rewind

## 🌐 Chrome Setup

On Windows, Netflix control uses Chrome DevTools Protocol. The GUI handles this when you click **Open Chrome**.

Manual command:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="$PWD\.chrome-debug-profile" https://www.netflix.com/browse
```

After Chrome opens:

1. Sign in to Netflix if needed.
2. Open a video.
3. Start playback once.
4. Return to the GUI and click **Start Controller**.

## 🧪 CLI Usage

You can control Netflix directly from the terminal:

```powershell
.venv\Scripts\python.exe netflix_seek_test.py --check
.venv\Scripts\python.exe netflix_seek_test.py --play
.venv\Scripts\python.exe netflix_seek_test.py --pause
.venv\Scripts\python.exe netflix_seek_test.py --toggle
.venv\Scripts\python.exe netflix_seek_test.py --get-time
```

Seek examples:

```powershell
.venv\Scripts\python.exe netflix_seek_test.py --minutes 18 --seconds 30
.venv\Scripts\python.exe netflix_seek_test.py --time 1091243
```

## 🎥 Direct Script Usage

Single viewer:

```powershell
.venv\Scripts\python.exe head\netflix_attention.py
```

Two viewers:

```powershell
.venv\Scripts\python.exe head\netflix_attention_2p.py
```

Press **q** in the camera overlay window to quit.

## ⚙️ Environment Configuration

The GUI passes these values automatically, but advanced users can set them manually:

| Variable | Default | Description |
|---|---:|---|
| `NETFLIX_ATTENTION_CAMERA_INDEX` | `0` | Webcam index |
| `NETFLIX_ATTENTION_DIGITAL_ZOOM` | `2.0` | Detection zoom factor |
| `NETFLIX_ATTENTION_YAW_THRESHOLD` | `25` | Left/right tolerance in degrees |
| `NETFLIX_ATTENTION_PITCH_THRESHOLD` | `20` | Up/down tolerance in degrees |
| `NETFLIX_ATTENTION_AWAY_GRACE` | `1.5` | Seconds before pause |
| `NETFLIX_ATTENTION_BACK_GRACE` | `0.8` | Seconds before resume |
| `NETFLIX_ATTENTION_MIN_ABSENT` | `2.0` | Minimum absence before seek-back |
| `NETFLIX_ATTENTION_FILTER_LENGTH` | `10` | Head-pose smoothing frames |
| `NETFLIX_ATTENTION_AUTO_CALIB_FRAMES` | `30` | Calibration frames |

Example:

```powershell
$env:NETFLIX_ATTENTION_DIGITAL_ZOOM="2.5"
$env:NETFLIX_ATTENTION_AWAY_GRACE="2.0"
.venv\Scripts\python.exe head\netflix_attention.py
```

## 🧩 Key Technologies

- 🧠 **MediaPipe Face Landmarker** for face mesh and landmarks
- 📷 **OpenCV** for camera capture and overlays
- 📊 **NumPy** for head-pose vector math
- 🌐 **Chrome DevTools Protocol** for Windows Netflix control
- 🪟 **Tkinter** for the desktop GUI

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| Chrome debug is offline | Click **Open Chrome** in the GUI |
| Netflix player check fails | Open a Netflix video and start playback once |
| Camera does not open | Try another camera index in the GUI |
| Face is not detected | Increase digital zoom, improve lighting, or sit closer |
| Playback flickers | Increase pause delay or resume delay |
| Seek-back does not happen | Increase absence time beyond the seek-back minimum |
| Two-viewer tracking swaps people | Sit consistently left/right; identity is positional |
| MediaPipe model missing | Ensure `head/face_landmarker.task` exists |

## 📌 Notes

- This project is not affiliated with Netflix.
- It does not bypass Netflix authentication, DRM, subscriptions, or access controls.
- It requires your own Netflix account and a video opened in Chrome.
- Webcam processing runs locally on your machine.

## 📄 License

This project is released under the **MIT License**. See [LICENSE](LICENSE) for details.

## 🙌 Credits

- Google MediaPipe for face landmark detection
- OpenCV for real-time camera processing
- Python and Tkinter for the desktop app foundation

