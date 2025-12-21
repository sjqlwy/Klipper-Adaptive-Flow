# Klipper Adaptive Flow

Automatic temperature and pressure advance control for E3D Revo hotends on Klipper. Dynamically boosts nozzle temperature during high-flow sections and adjusts PA in real-time — no manual tuning required.

## Features

- **Dynamic temperature** — flow/speed/acceleration-based boost
- **Dynamic PA** — scales with temperature boost automatically
- **5-second lookahead** — pre-heats before flow spikes
- **First layer skip** — consistent squish on layer 1
- **Heater monitoring** — won't request more than your heater can deliver
- **Self-learning** — optimizes K-values and PA over time
- **Per-material profiles** — auto-detects PLA, PETG, ABS, TPU, etc.

## Installation

```bash
cd ~ && git clone https://github.com/barnard704344/Klipper-Adaptive-Flow.git
cd Klipper-Adaptive-Flow
cp gcode_interceptor.py extruder_monitor.py ~/klipper/klippy/extras/
cp auto_flow.cfg ~/printer_data/config/
sudo systemctl restart klipper
```

Add to `printer.cfg`:
```ini
[include auto_flow.cfg]
[gcode_interceptor]
[extruder_monitor]
```

## Slicer Setup

**Start G-code:**
```gcode
PRINT_START BED=[bed_temperature_initial_layer_single] EXTRUDER=[nozzle_temperature_initial_layer] MATERIAL=[filament_type]
```

**End G-code:**
```gcode
PRINT_END
```

See [PRINT_START.example](PRINT_START.example) for a complete example.

## Printer Macros

Add `AT_START` after heating and `AT_END` at print end in your macros:

```ini
[gcode_macro PRINT_START]
gcode:
    # ... your heating, homing, leveling ...
    AT_START                          # Enable adaptive flow

[gcode_macro PRINT_END]
gcode:
    AT_END                            # Stop loop, save learned values
    TURN_OFF_HEATERS                  # Must come AFTER AT_END
    # ... your cooldown, park, etc ...
```

> **Important:** Call `AT_END` *before* `TURN_OFF_HEATERS` to ensure the control loop stops first.

## Configuration

One setting for most users — edit `auto_flow.cfg`:
```ini
variable_use_high_flow_nozzle: True   # False for standard Revo
```

**[Full configuration reference →](docs/CONFIGURATION.md)**

## Commands

| Command | Description |
|---------|-------------|
| `AT_STATUS` | Show current state, flow, boost, PA |
| `AT_SET_PA MATERIAL=X PA=Y` | Save calibrated PA |
| `AT_LIST_PA` | Show all PA values |

## How It Works

1. **Flow boost**: Temperature increases with volumetric flow rate
2. **Speed boost**: Extra heating for high-speed thin walls (>100mm/s)
3. **Lookahead**: Predicts flow 5 seconds ahead for pre-heating
4. **Dynamic PA**: Automatically reduces PA as temperature increases (higher temp = lower viscosity = less PA needed)

Example during a print:
```
Base temp: 230°C, Base PA: 0.060
High flow detected → Boost +20°C → Temp 250°C, PA 0.048
```

## Requirements

- E3D Revo hotend (HF or Standard)
- Klipper firmware
- 40W or 60W heater

## License

MIT



