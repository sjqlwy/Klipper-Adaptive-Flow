# Configuration Reference

Detailed configuration options for Klipper Adaptive Flow.

## Quick Start

Most users only need to set one option in `auto_flow.cfg`:

```ini
variable_use_high_flow_nozzle: True   # False for standard Revo nozzles
```

Everything else auto-configures based on your material.

---

## How It Works

### Temperature Control
- **Flow boost**: Temperature increases with volumetric flow (mm³/s)
- **Speed boost**: Extra heating for high-speed thin walls (>100mm/s)
- **Acceleration boost**: Detects corners via motion analysis
- **Lookahead**: 5-second prediction buffer for pre-heating

### Dynamic Pressure Advance
PA automatically scales with temperature boost:
```
PA_adjusted = PA_base × (1 - boost × 0.01)
```

Example: Base PA 0.060, +20°C boost → PA becomes 0.048

Higher temperature = lower filament viscosity = less PA needed.

---

## Material Settings

### Per-Material Defaults

These are applied automatically when `AT_START` detects your material:

| Material | Flow K | Flow Gate | Max Temp | PA | Ramp Rise | Ramp Fall |
|----------|--------|-----------|----------|-----|-----------|-----------|
| PLA | 0.80 (HF) / 0.40 (Std) | 10 / 8 mm³/s | 235°C | 0.040 | 4.0°C/s | 1.0°C/s |
| PETG | 2.00 (HF) / 1.80 (Std) | 14 / 10 mm³/s | 280°C | 0.060 | 4.0°C/s | 1.5°C/s |
| ABS/ASA | 0.80 | 12 / 9 mm³/s | 290°C | 0.050 | 4.0°C/s | 1.0°C/s |
| TPU | 0.00 (disabled) | 5 mm³/s | 240°C | 0.200 | 2.0°C/s | 0.5°C/s |
| NYLON | 0.90 | 12 / 9 mm³/s | 275°C | 0.055 | 4.0°C/s | 1.0°C/s |
| PC | 0.70 | 11 / 8 mm³/s | 300°C | 0.045 | 4.0°C/s | 1.0°C/s |

### What Each Setting Does

- **Flow K**: Temperature boost per mm³/s of flow (higher = more aggressive)
- **Flow Gate**: Minimum flow to trigger boost (based on E3D Revo datasheet)
- **Max Temp**: Safety limit for that material
- **PA**: Default Pressure Advance value
- **Ramp Rise**: How fast temperature increases (°C/second)
- **Ramp Fall**: How fast temperature decreases (°C/second) — higher = less corner bulging

---

## Advanced Configuration

Edit these variables in `auto_flow.cfg` if needed:

### Temperature Control

```ini
variable_max_boost_limit: 50.0        # Max boost above base temp (°C)
variable_ramp_rate_rise: 4.0          # Heat up speed (°C/s)
variable_ramp_rate_fall: 1.0          # Cool down speed (°C/s) — increase to reduce corner bulging
```

### Speed-Based Boost

For high-speed thin walls that don't trigger flow-based boost:

```ini
variable_speed_boost_threshold: 100.0  # Linear speed (mm/s) to trigger boost
variable_speed_boost_k: 0.05           # °C per mm/s above threshold
```

Example: 200mm/s outer walls → `(200-100) × 0.05 = +5°C` boost

### Flow Smoothing

```ini
variable_flow_smoothing: 0.15          # 0.0-1.0, lower = faster response
```

### First Layer Mode

```ini
variable_first_layer_skip: True        # Disable boost on first layer
variable_first_layer_height: 0.3       # Z height considered "first layer"
```

First layer detection uses Z height as fallback when slicer layer info is unavailable.

### Thermal Safety

```ini
variable_thermal_runaway_threshold: 15.0   # Max overshoot before emergency
variable_thermal_undertemp_threshold: 10.0 # Max undershoot before warning
```

### Heater Duty Cycle Limits

Automatically managed — no config needed:
- **95%+ PWM**: Freeze boost at current level
- **99%+ PWM**: Actively reduce boost
- **<90% PWM**: Safe for K-value learning

### Lookahead Settings

Configured in `extruder_monitor.py`:
- **Buffer size**: 5 seconds of predicted flow
- **Update rate**: 1 second loop
- **Weight**: 0.8 (80% confidence in prediction)

### Self-Learning

```ini
variable_self_learning_enabled: True   # Auto-adjust K-values over time
variable_learning_rate: 0.05           # How aggressively to adjust
variable_pa_auto_learning: True        # Experimental PA auto-tuning
variable_pa_learning_rate: 0.002       # PA adjustment rate
```

---

## Commands Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `AT_START` | Enable adaptive flow (call after heating) |
| `AT_END` | Stop loop, save learned values (call before TURN_OFF_HEATERS) |
| `AT_STATUS` | Show current state, flow, boost, PA, PWM |

### PA Commands

| Command | Description |
|---------|-------------|
| `AT_SET_PA MATERIAL=X PA=Y` | Save calibrated PA for a material |
| `AT_GET_PA MATERIAL=X` | Show PA for a material |
| `AT_LIST_PA` | List all PA values |

### Manual Override

| Command | Description |
|---------|-------------|
| `AT_SET_FLOW_K K=X` | Set flow boost multiplier |
| `AT_SET_FLOW_GATE GATE=X` | Set minimum flow threshold |
| `AT_SET_MAX MAX=X` | Set max temperature limit |
| `AT_ENABLE` | Enable the system |
| `AT_DISABLE` | Disable the system |

---

## AT_STATUS Output Explained

```
╔═══════════════════════════════════════════╗
║      ADAPTIVE FLOW STATUS                 ║
╠═══════════════════════════════════════════╣
║ System: ✓ ENABLED                         ║  # Is the system active?
║ Hotend: Revo HF (High Flow)               ║  # Which nozzle type
╠═══════════════════════════════════════════╣
║ TEMPERATURE                               ║
╠═══════════════════════════════════════════╣
║ Actual:     252.1°C                       ║  # Current hotend temp
║ Target:     252.0°C                       ║  # What we're requesting
║ Base:       230.0°C                       ║  # Slicer's base temp
║ Boost:     +22.0°C                        ║  # Current boost amount
║ Max Limit:  280°C                         ║  # Safety cap
╠═══════════════════════════════════════════╣
║ FLOW & SPEED                              ║
╠═══════════════════════════════════════════╣
║ Flow K:       2.00                        ║  # Boost multiplier
║ Flow Gate:   14.0 mm³/s                   ║  # Min flow for boost
║ Current Flow: 8.34 mm³/s                  ║  # Live volumetric flow
║ Toolhead:   169.2 mm/s (>100)             ║  # Linear speed
║ Predicted:    9.63 mm/s                   ║  # 5s lookahead prediction
╠═══════════════════════════════════════════╣
║ PRESSURE ADVANCE                          ║
╠═══════════════════════════════════════════╣
║ Base PA:     0.060                        ║  # Material default
║ Current PA:  0.048                        ║  # Adjusted for temp boost
╠═══════════════════════════════════════════╣
║ SAFETY                                    ║
╠═══════════════════════════════════════════╣
║ Heater PWM:    86%                        ║  # Heater duty cycle
║ Z Height:     9.43 mm                     ║  # Current Z
║ First Layer: NO                           ║  # First layer mode?
║ Thermal Faults: 0/3                       ║  # Fault counter
╚═══════════════════════════════════════════╝
```

---

## Troubleshooting

### No boost happening
- Check `AT_STATUS` — is system ENABLED?
- Is flow above the gate? (e.g., 14 mm³/s for PETG HF)
- Is it first layer? (boost disabled)
- Is heater at 95%+ PWM? (boost frozen)

### Corner bulging
- Increase `ramp_rate_fall` (faster cooldown) — PETG defaults to 1.5°C/s
- Check PA is being applied (AT_STATUS shows current PA)
- Reduce `speed_k` for less aggressive boost

### Under-extrusion at high speed
- Speed boost should help (default: +5°C at 200mm/s)
- Increase `speed_boost_k` if needed
- Check heater isn't saturated (PWM < 95%)

### PA showing 0.000
- Fixed in latest version — update `auto_flow.cfg`
- Run `AT_LIST_PA` to verify defaults are set

### Heaters stay on after print
- Fixed in latest version — `AT_END` now stops the control loop immediately
- Ensure `AT_END` is called before `TURN_OFF_HEATERS` in PRINT_END

---

## Data Sources

### Native Klipper (no Python required)
- `printer.motion_report.live_extruder_velocity` → volumetric flow
- `printer.motion_report.live_velocity` → toolhead speed
- `printer.extruder.power` → heater PWM %
- `printer.toolhead.position.z` → Z height

### Python Extras (enhanced features)
- `extruder_monitor.py` → 5-second lookahead, corner detection
- `gcode_interceptor.py` → G-code stream parsing
