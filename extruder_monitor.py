---

### 2. `extras/extruder_monitor.py`
*Save this file in the `extras` folder.*

```python
import logging

class ExtruderMonitor:
    def __init__(self, config):
        self.printer = config.get_printer()
        config.get("stepper", "extruder")
        self.driver_name = config.get("driver_name", "tmc2209 extruder")
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

    def handle_connect(self):
        try:
            self.tmc = self.printer.lookup_object(self.driver_name)
        except Exception as e:
             raise self.printer.config_error(f"ExtruderMonitor: Driver '{self.driver_name}' not found. Check printer.cfg.")

        gcode = self.printer.lookup_object('gcode')
        gcode.register_command("GET_EXTRUDER_LOAD", self.cmd_GET_EXTRUDER_LOAD,
                               desc="Get current extruder load")

    def cmd_GET_EXTRUDER_LOAD(self, gcmd):
        try:
            mcu_tmc = self.tmc.mcu_tmc
            val = mcu_tmc.get_register('SG_RESULT')
            if not isinstance(val, int):
                val = int(val)
            gcmd.respond_info(f"Extruder Load (SG_RESULT): {val}")
        except Exception as e:
            try:
                # Fallback for some TMC implementations
                val = self.tmc.get_register('SG_RESULT')
                gcmd.respond_info(f"Extruder Load (via Helper): {val}")
            except:
                gcmd.respond_info(f"Error reading TMC: {str(e)}")

    def get_status(self, eventtime):
        try:
            if hasattr(self, 'tmc'):
                val = self.tmc.mcu_tmc.get_register('SG_RESULT')
                return {'load': int(val)}
        except:
            pass
        return {'load': -1}

def load_config(config):
    return ExtruderMonitor(config)
