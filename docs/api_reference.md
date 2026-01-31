# Laujuc API Reference

## input_core

### InputCore
- `click_mouse(button: MouseButton)` — simulate a mouse click.
- `press_key(key: str)` — press a key.
- `release_key(key: str)` — release a key.
- `type_text(text: str)` — type a string with configurable delay.

### AutomationScenario
- `add_action(action, payload)` — append an automation step.
- `play(engine)` — execute the scenario on the provided input engine.

### InputProfiler
- `start(name)` — begin a profiling session.
- `record(event_type, payload)` — record a profiling event.
- `stop()` — return a profile summary.

### IntegrationBridge
- `to_selenium_script(scenario)` — generate Selenium script stub.
- `to_appium_script(scenario)` — generate Appium stub.

## settings_manager

### SettingsManager
- `load()` — read JSON settings.
- `save(settings)` — persist JSON settings.
- `export_xml(settings, target)` — export XML.
- `import_xml(source)` — load XML into settings object.
