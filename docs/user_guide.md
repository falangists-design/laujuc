# Laujuc User Guide

## Overview
Laujuc is a developer-focused framework for automating user input in QA workflows and
accessibility scenarios. The bundled desktop application demonstrates how to build,
profile, and run automation flows with a modern UI.

## Main Tabs

### Сценарии
- Create and replay automation scenarios.
- Export Selenium-ready templates.
- Record input sequences for repetitive workflows.

### Профили
- Capture and analyze input patterns.
- Review summaries to understand test coverage and latency.

### Настройки
- Configure CPS, hotkeys, and active buttons.
- Export or import profiles in JSON/XML.
- Toggle activation requirement and switch between dark/light themes.
- Export/import activation keys for team onboarding.

### Документация
- Embedded reference for API usage and developer notes.

## Accessibility
- Hotkey-driven navigation for quick access.
- High-contrast accent color for visual clarity.
- Scenarios can be used to assist users with repetitive tasks.

## Launcher & Activation
- Generate activation keys using the separate `laujuc keygen` application.
- Import the key file in the launcher or settings, then enter the key to unlock the UI.
- Session timer shows remaining activation time.

## Packaging note (Windows)
- If a packaged build shows a missing DLL ordinal error, rebuild with PyInstaller using
  `--collect-all PySide6 --collect-all shiboken6 --collect-submodules PySide6 --collect-submodules shiboken6`
  to ensure Qt runtime libraries are bundled.
