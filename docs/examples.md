# Examples

## Web Form Automation (Selenium)
```python
from laujuc.input_core import AutomationScenario, ScenarioAction, MouseButton
from laujuc.input_core import IntegrationBridge

scenario = AutomationScenario(name="Form Test")
scenario.add_action(ScenarioAction.CLICK, {"button": MouseButton.LEFT.value})
scenario.add_action(ScenarioAction.KEY_PRESS, {"key": "A"})
scenario.add_action(ScenarioAction.KEY_RELEASE, {"key": "A"})

bridge = IntegrationBridge()
print(bridge.to_selenium_script(scenario))
```

## Accessibility Macro
```python
from laujuc.input_core import AutomationScenario, ScenarioAction

scenario = AutomationScenario(name="Accessibility Macro")
scenario.add_action(ScenarioAction.KEY_PRESS, {"key": "TAB"})
scenario.add_action(ScenarioAction.KEY_RELEASE, {"key": "TAB"})
```
