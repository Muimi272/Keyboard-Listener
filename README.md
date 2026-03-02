# Keyboard Listener

<p align="center">
  <img src="icon.png" alt="Keyboard Listener Icon" width="80"/>
</p>

<p align="center">
  A lightweight Windows system-tray application that silently tracks and records every key press in the background, with a live dashboard for real-time statistics.
</p>

---

## ✨ Features

- **System Tray Operation** – Runs entirely from the Windows system tray with no visible window cluttering your taskbar.
- **Global Keyboard Hook** – Captures every key-down event system-wide, regardless of which application is in focus.
- **Live Dashboard** – A clean, dark-themed GUI window showing:
  - Current status (Counting / Paused) with a color indicator
  - Total key presses accumulated
  - Configured batch-save threshold
  - Path of the active data file
  - A scrollable table of all tracked keys, sorted by press count (highest first)
- **Pause / Resume** – Instantly pause and resume counting from the tray menu. A red dot appears on the tray icon while paused.
- **Persistent Storage** – Key-press data is saved to a JSON file so counts survive application restarts.
- **Batch Auto-Save** – Data is written to disk automatically every *N* key presses (configurable), minimising I/O overhead.
- **Config File** – All tunable parameters live in a human-readable `config.json` that can be opened directly from the tray menu.
- **ESC to Exit** – Pressing the `ESC` key anywhere triggers a clean shutdown (saves data first).
- **PyInstaller-Ready** – Resource paths are resolved correctly when the app is bundled as a standalone `.exe`.

---

## 📥 Download

Pre-built Windows executables are available on the [**Releases**](../../releases) page.  
Download the latest `.exe`, place `icon.png` in the same folder, and run it — no Python installation required.

---

## 🖥️ Dashboard Preview

The dashboard window (`700 × 640 px`) is opened from the tray menu via **Open Dashboard**.

| Section | Description |
|---|---|
| **Status** | Shows `Counting` (green) or `Paused` (red) |
| **Total key presses** | Running total since the data file was created |
| **Batch save threshold** | How often (in key presses) data is auto-saved |
| **Data file** | Name/path of the JSON file being written to |
| **Top Key Presses table** | All tracked keys ranked by count, updated every second |
| **Version footer** | Displays the version string; hover to see author credit |

---

## ⚙️ Configuration

On first launch a `config.json` file is created automatically next to the executable:

```json
{
  "BATCH_THRESHOLD": 10,
  "DATA_FILE": "data.json",
  "VERSION": "1.1"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `BATCH_THRESHOLD` | integer | `10` | Save to disk every this many key presses. Must be a positive integer. |
| `DATA_FILE` | string | `"data.json"` | Path (relative or absolute) to the file where key-press data is stored. |
| `VERSION` | string | `"1.1"` | Version string displayed in the dashboard footer. |

You can open `config.json` directly from the tray menu (**Open Config**).  
Changes take effect on the **next launch** of the application.

---

## 📂 Data File Format

Key-press counts are stored in `data.json` (or whichever file is set in `config.json`):

```json
{
  "key_counts": {
    "A": 412,
    "Space": 308,
    "Backspace": 97,
    "Enter": 54
  },
  "total_press": 1234
}
```

| Field | Type | Description |
|---|---|---|
| `key_counts` | object | Maps each key name to its total press count. |
| `total_press` | integer | Sum of all individual key counts. |

The file is updated automatically every `BATCH_THRESHOLD` presses and again when the program exits cleanly.

---

## ⌨️ Supported Keys

The application recognises over 80 keys via a built-in virtual-key code map, including:

- **Alphanumeric** – `A`–`Z`, `0`–`9`
- **Function keys** – `F1`–`F12`
- **Modifier keys** – `Shift`, `Ctrl`, `Alt`, `LShift`, `RShift`, `LCtrl`, `RCtrl`, `LAlt`, `RAlt`
- **Navigation** – `ArrowUp/Down/Left/Right`, `Home`, `End`, `PageUp`, `PageDown`, `Insert`, `Delete`
- **Numpad** – `Num0`–`Num9`, `NumAdd`, `NumSubtract`, `NumMultiply`, `NumDivide`, `NumDecimal`
- **Special** – `Space`, `Tab`, `Enter`, `Backspace`, `ESC`, `CapsLock`, `NumLock`, `ScrollLock`, `PrintScreen`, `Windows`, `ContextMenu`
- **Punctuation** – `` ` ``, `-`, `=`, `[`, `]`, `\`, `;`, `'`, `,`, `.`, `/`

Any key whose virtual-key code is not in the map is recorded as `Unknown(<vk_code>)`.

---

## 🚀 Running from Source

### Requirements

- Windows (the keyboard hook library is Windows-only)
- Python 3.8+

### Install dependencies

```bash
pip install pyhooked pystray Pillow
```

### Run

```bash
python src/Keyboard_Listener.py
```

Make sure `icon.png` is in the same directory as the script (or the executable).

---

## 🗂️ Project Structure

```
Keyboard-Listener/
├── src/
│   └── Keyboard_Listener.py   # Main application source
├── icon.png                   # Tray / window icon
├── config.json                # Auto-generated on first run
├── data.json                  # Auto-generated on first run
└── README.md
```

---

## 📋 Tray Menu

| Menu Item | Action |
|---|---|
| **Pause Counting** / **Resume Counting** | Toggle key-press tracking on/off |
| **Open Dashboard** | Open the live statistics window |
| **Open Config** | Open `config.json` in the system default editor |
| **Exit** | Save data and shut down the application |

---

## 📜 License

This project is licensed under the terms of the [LICENSE](LICENSE) file in this repository.