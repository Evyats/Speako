# Speako

Speako is a lightweight Windows tray app that turns speech into polished text or AI-ready prompts. It records from your microphone, transcribes with OpenAI, runs the text through an editable processing pipeline, and copies or pastes the result into your active application.

## Screenshots

### Recording

![Recording and preset chooser](docs/screenshots/recording.png)

### Settings

<p align="center">
  <img src="docs/screenshots/general-settings.png" alt="General settings" width="260">
  <img src="docs/screenshots/presets.png" alt="Preset list" width="260">
  <img src="docs/screenshots/pipeline-editor.png" alt="Pipeline editor" width="260">
</p>

## Features

- Global start/stop shortcut with a hold-to-select preset menu
- Hebrew, English, or automatic language detection
- Editable presets composed of independent GPT processing nodes
- Per-node model and reasoning controls
- Automatic clipboard copy and optional `Ctrl+V`
- Microphone selection, light/dark themes, and recent workflow details
- Cancellation by pressing the shortcut during processing

## Requirements

- Windows 10 or 11
- Python 3.11+
- An OpenAI API key with API billing enabled

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Add your key to `.env`:

```env
OPENAI_API_KEY=your-api-key
```

Then start Speako:

```powershell
python -m speako
```

## Usage

1. Press `Ctrl+Alt+Space` to start recording.
2. Press it again to stop and process the recording.
3. Press it during processing to cancel.

To choose another preset, keep the initial shortcut held, move with `↑` / `↓` or click a preset, then release the shortcut. If you make no selection, Speako uses the first preset. Completed output is copied and pasted automatically unless automatic paste is disabled in Settings.

Speako stores settings and recent workflow details under `%APPDATA%\Speako`. Audio is processed in memory and is not saved to disk by Speako. Keep `.env` private and never commit it.
