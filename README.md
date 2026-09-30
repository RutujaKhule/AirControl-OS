# AirControl OS

AirControl OS is a desktop application for controlling the mouse with webcam hand gestures and issuing desktop, media, and scrolling commands by voice. It uses a Qt interface with a live camera preview, hand-tracking status, activity history, settings, onboarding, and an optional system tray.

## Features

- Live mirrored webcam preview with MediaPipe hand landmarks.
- One-hand tracking, normalized cursor control, EMA smoothing, and PyAutoGUI mouse actions.
- Pinch click, pinch-and-hold drag, V-shaped right click, vertical scrolling, and fist pause/resume.
- Voice commands for launching supported applications, media keys, volume, and scrolling.
- Live camera, hand, gesture, voice, and system status cards.
- In-memory activity history, settings persistence, first-run onboarding, and optional tray controls.
- Camera processing is configured to process every frame (`FRAME_SKIP_EVERY_N = 1`).

## Technology Stack

- Python
- PySide6 for the desktop GUI, signals, and worker threads
- OpenCV for camera capture, frame conversion, and landmark rendering
- MediaPipe Hands for hand landmarks
- NumPy for image data
- PyAutoGUI for mouse, keyboard, and scroll actions
- SpeechRecognition and PyAudio for microphone capture and Google speech recognition

## System Requirements

- Windows is the primary target. Camera and mouse-control support on other operating systems depends on the installed OpenCV, PyAutoGUI, and audio backends.
- Python with compatible wheels for the dependencies in `requirements.txt`. The current development environment was validated with Python 3.10.
- A webcam, a microphone for voice commands, and a logged-in desktop session for cursor control.
- Internet access for Google speech recognition. Recognition requests use a 4-second timeout; voice app-launch commands are Windows-specific.
- Windows microphone privacy permission and an available, unoccupied camera. MediaPipe detection quality depends on lighting, framing, and hand visibility.

## Installation

From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PyAudio installation fails, install a compatible PyAudio wheel for your Python version and platform, then rerun the requirements command.

## How to Run

```powershell
python main.py
```

On first launch, complete the onboarding wizard. The app then opens the main window and starts the camera and voice workers. Camera or microphone availability is reflected in the status UI; voice can be toggled with `V`.

## Gesture Controls

| Gesture | Action |
| --- | --- |
| Point with the index fingertip | Move the cursor |
| Touch thumb and index finger together, then release | Left click |
| Hold the pinch for the configured drag interval (250 ms by default) | Drag; release the pinch to drop |
| Raise index and middle fingers in a separated V, with ring and pinky folded | Right click |
| Move the index fingertip vertically | Scroll up or down |
| Make and hold a closed fist for 350 ms | Toggle pause/resume; release and make a new fist for the next toggle |

The detector is configured for one hand. It uses the first detected hand for control; additional hands are not independently controlled.

## Voice Commands

Speak naturally into the microphone. Recognition uses the Google service through SpeechRecognition and requires internet connectivity.

- Open apps: `Open`, `Launch`, `Start`, or `Run` followed by Chrome, Notepad, Calculator, Paint, Explorer, Command Prompt, PowerShell, Spotify, Word, Excel, PowerPoint, Edge, or Firefox.
- Media: `Play`, `Pause`, `Next`, `Skip`, `Previous`, `Back`, or `Stop`.
- Volume: `Volume up`, `Louder`, `Turn it up`, `Volume down`, `Quieter`, `Lower volume`, `Softer`, or `Mute`.
- Scrolling: `Scroll up`, `Page up`, `Scroll down`, or `Page down`. Add an amount such as `a lot`, `little`, `bit`, or `slight`.

Application launching is supported only on Windows. Media and scroll actions use PyAutoGUI and depend on the active desktop/application.

## Project Architecture

1. `main.py` loads persisted settings, runs onboarding when needed, creates the main window and tray manager, and wires application shortcuts and dialogs.
2. `CameraCapture` reads and mirrors frames. `VideoWorker` runs camera capture, MediaPipe detection, gesture recognition, and cursor/action signal emission on a `QThread`.
3. `HandDetector` returns normalized landmarks and draws them on the preview frame. `GestureRecognizer` converts landmarks into cursor coordinates and gesture results.
4. `MainWindow` receives worker signals, updates the preview and status cards, and routes normalized cursor coordinates to `CursorController`.
5. `CursorController` applies the existing EMA smoother, maps normalized coordinates to screen pixels once, clamps to screen bounds, and calls PyAutoGUI. Cursor movement bypasses PyAutoGUI's per-call pause while retaining its global failsafe.
6. `VoiceListener` captures microphone audio on its own `QThread`; `VoiceExecutor` maps recognized phrases to supported app, media, and scroll actions.
7. `core.persistence` stores app, gesture, and voice settings as JSON. The activity history is held in memory.

## Folder Structure

```text
AirControl_os/
|-- assets/                         # Reserved for project assets
|-- main.py                         # Application entry point
|-- requirements.txt                # Python dependencies
|-- test_cards.py                   # Legacy GUI-card diagnostic script
|-- README.md
|-- src/aircontrol/
    |-- core/                       # Camera, config, cursor, history, persistence
    |-- gesture/                    # MediaPipe hand detection and recognition
    |-- gui/                        # Main window, dialogs, onboarding, tray, worker
    |-- utils/                      # Smoothing and cooldown helpers
    |-- voice/                      # Microphone listener and command executor
```

`test_cards.py` is an ad-hoc GUI diagnostic, not a complete automated test suite; constructing its `MainWindow` starts the camera and voice workers.

## Configuration

Use **File > Settings** to adjust the camera index, requested resolution/FPS, MediaPipe confidence, cursor smoothing, pinch threshold, click cooldown, drag duration, scroll sensitivity, gesture cooldowns, and voice recognition settings. Applying settings saves them and restarts the camera and voice workers. Runtime camera processing is forced to every frame even if an older settings file contains a different frame-skip value.

Defaults include a 1280x720 camera request, 30 FPS camera target, one tracked hand, 0.5 detection/tracking confidence, cursor EMA alpha 0.6, pinch threshold 0.06, click cooldown 400 ms, drag hold 250 ms, scroll sensitivity 15, right-click cooldown 800 ms, and fist hold 350 ms. Camera devices may not honor the requested resolution or frame rate.

Settings are saved at `%LOCALAPPDATA%\AirControl OS\settings.json` on Windows. On macOS they are stored under `~/Library/Application Support/AirControl OS`; on Linux they use `$XDG_CONFIG_HOME/aircontrol-os` or `~/.config/aircontrol-os`.

## Troubleshooting

- **Camera Offline:** Check camera privacy permissions, close other applications using the camera, and select the correct camera index in Settings.
- **No hand detected:** Improve lighting, keep the full hand in frame, and ensure the camera preview shows it clearly. Only one hand is used for control.
- **Cursor feels noisy or sluggish:** Adjust cursor smoothing in Settings. Higher EMA alpha follows new coordinates more quickly; lower alpha filters more jitter.
- **Voice unavailable or not recognizing phrases:** Check microphone permissions and input-device availability. Speech recognition requires network access and times out after 4 seconds; PyAudio installation can vary by Python version.
- **Voice launches no app:** Application launching is Windows-only and depends on the target app being installed and discoverable by Windows.
- **Tray or shortcuts unavailable:** Tray support depends on the desktop environment. The `Ctrl+Alt+P`, `Ctrl+Alt+V`, and `Ctrl+Alt+S` shortcuts are Qt application shortcuts, not guaranteed OS-wide hotkeys.
- **Clean shutdown:** Close the main window or choose Exit from the tray menu. Camera and voice workers use stop requests and bounded waits.

## Known Limitations

- Physical gesture recognition and cursor control depend on the camera view, lighting, device performance, and hand placement.
- The current implementation controls one hand and does not select between multiple users/hands.
- Voice transcription depends on Google's online recognition service; there is no offline speech backend.
- Voice app launching is Windows-specific.
- Activity history is limited to the latest 200 entries in memory and is not persisted across launches.
- The repository does not currently contain a comprehensive automated hardware-in-the-loop or pytest suite. `test_cards.py` is not a replacement for one.
- A 60-second visible-window runtime test processed 650 frames, detected 192 hand frames, issued 192 cursor-movement calls, and recorded no fist pause transition. A separate 60-second tray-hidden test processed 748 frames, detected 449 hand frames, issued 449 cursor-movement calls, and also recorded no pause transition.
- Frame cadence varied with device load. Process CPU ranged roughly 74–91% during the visible test; MediaPipe inference remained about 25 ms per frame. Reducing model complexity may lower CPU use but could affect detection quality and has not been validated here.

## Future Enhancement Ideas

- Add repeatable unit tests for gesture edge cases and settings persistence, plus hardware-in-the-loop tests for camera and mouse behavior.
- Add camera calibration and guided lighting/framing diagnostics.
- Offer a configurable offline speech-recognition backend.
- Add explicit hand selection for multi-hand or multi-user setups.