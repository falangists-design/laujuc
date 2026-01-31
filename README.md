# laujuc

Laujuc is an open-source input automation framework focused on software testing and
accessibility. It ships with a standalone desktop demo that showcases recording,
playback, profiling, and integrations with popular QA tooling.

## Features

- Modular architecture: `input_core`, `settings_manager`, `gui_layer`.
- Cross-platform UI built with PySide6.
- Scenario recording & playback, profiling summaries, logging.
- Launcher with activation key flow and theme switching.
- JSON/XML configuration export/import.
- Integrated developer documentation view inside the app.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python app.py
```

To generate activation keys separately:

```bash
python keygen_app.py
```

## Packaging (single-file executable)

Use PyInstaller to build a standalone executable.

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name laujuc --icon laujuc/resources/laujuc_icon.svg \
  --clean --noconfirm --collect-all PySide6 --collect-all shiboken6 \
  --collect-submodules PySide6 --collect-submodules shiboken6 app.py
pyinstaller --onefile --noconsole --name laujuc-keygen --icon laujuc/resources/laujuc_icon.svg \
  --clean --noconfirm --collect-all PySide6 --collect-all shiboken6 \
  --collect-submodules PySide6 --collect-submodules shiboken6 keygen_app.py
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
