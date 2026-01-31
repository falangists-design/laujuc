# laujuc

Laujuc is an open-source input automation framework focused on software testing and
accessibility. It ships with a standalone desktop demo that showcases recording,
playback, profiling, and integrations with popular QA tooling.

## Features

- Modular architecture: `input_core`, `settings_manager`, `gui_layer`.
- Cross-platform UI built with PySide6.
- Scenario recording & playback, profiling summaries, logging.
- JSON/XML configuration export/import.
- Integrated developer documentation view inside the app.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python app.py
```

## Packaging (single-file executable)

Use PyInstaller to build a standalone executable.

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name laujuc --icon laujuc/resources/laujuc_icon.svg app.py
```

## Project layout

```
app.py
laujuc/
  input_core.py
  settings_manager.py
  gui_layer.py
  resources/
    laujuc_icon.svg
```

## License

MIT
