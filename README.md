# Klipper Adaptive Flow

Automatic temperature and pressure advance control for E3D Revo hotends on Klipper. Dynamically boosts nozzle temperature during high-flow sections and adjusts PA in real-time — no manual tuning required.

## Features

- **Dynamic temperature** — flow/speed/acceleration-based boost
- **Dynamic PA** — scales with temperature boost automatically
- **Smart Cooling** — adjusts part fan based on flow rate and layer time
- **5-second lookahead** — pre-heats before flow spikes
- **Dynamic Z-Window (DynZ)** — learns and adapts to convex surfaces
- **Per-material profiles** — PLA, PETG, ABS, ASA, TPU, Nylon, PC, HIPS (user-editable)
- **First layer skip** — consistent squish on layer 1
- **Heater monitoring** — won't request more than your heater can deliver
- **Print analysis** — AI-powered tuning suggestions (optional)

## Installation

```bash
cd ~ && git clone https://github.com/barnard704344/Klipper-Adaptive-Flow.git
cd Klipper-Adaptive-Flow
cp gcode_interceptor.py extruder_monitor.py ~/klipper/klippy/extras/
cp auto_flow.cfg material_profiles.cfg ~/printer_data/config/
sudo systemctl restart klipper
```

Add to `printer.cfg`:
```ini
[include auto_flow.cfg]
[gcode_interceptor]
[extruder_monitor]
```

## Slicer Setup

**Start G-code** (OrcaSlicer/PrusaSlicer/SuperSlicer):
```gcode
PRINT_START BED=[bed_temperature_initial_layer_single] EXTRUDER=[nozzle_temperature_initial_layer] MATERIAL={filament_type[0]}
```

`{filament_type[0]}` is a built-in slicer variable that automatically passes the material type (PLA, PETG, ABS, etc.) from your filament profile. No manual setup needed — it just works.

**End G-code:**
```gcode
PRINT_END
```

**Important:** Disable Pressure Advance in your slicer — this system handles PA dynamically.

See [PRINT_START.example](PRINT_START.example) for a complete example.

## Printer Macros

Add `AT_START` after heating and `AT_END` at print end:

```ini
[gcode_macro PRINT_START]
gcode:
    # ... your heating, homing, leveling ...
    AT_START MATERIAL={params.MATERIAL|default("PLA")}   # Enable adaptive flow

[gcode_macro PRINT_END]
gcode:
    AT_END                                # Disable adaptive flow
    TURN_OFF_HEATERS                      # Must come AFTER AT_END
    # ... your cooldown, park, etc ...
```

The `MATERIAL` parameter is passed from your slicer's start G-code (see above). If omitted, material is auto-detected from extruder temperature.

> **Important:** Call `AT_END` *before* `TURN_OFF_HEATERS` to ensure the control loop stops first.

## Configuration

### Basic Setup (most users)

Edit `auto_flow.cfg`:
```ini
variable_use_high_flow_nozzle: True   # False for standard Revo
```

### Material Profiles (optional customization)

Edit `material_profiles.cfg` to customize per-material boost curves:
```ini
[gcode_macro _AF_PROFILE_PETG]
variable_flow_k: 1.20           # Temp boost per mm³/s flow
variable_speed_boost_k: 0.08    # Temp boost per mm/s above 100
variable_max_boost: 40.0        # Max temp increase cap (°C)
variable_ramp_rise: 4.0         # Heat up rate (°C/s)
variable_ramp_fall: 1.5         # Cool down rate (°C/s)
...
```

**[Full configuration reference →](docs/CONFIGURATION.md)**

## Commands

| Command | Description |
|---------|-------------|
| `AT_STATUS` | Show current state, flow, boost, PA |
| `AT_DYNZ_STATUS` | Show Dynamic Z-Window learning state |
| `AT_SC_STATUS` | Show Smart Cooling status |
| `AT_SET_PA MATERIAL=X PA=Y` | Save calibrated PA |
| `AT_LIST_PA` | Show all PA values |

## How It Works

1. **Flow boost**: Temperature increases with volumetric flow rate
2. **Speed boost**: Extra heating for high-speed thin walls (>100mm/s)
3. **Lookahead**: Predicts flow 5 seconds ahead for pre-heating
4. **Dynamic PA**: Automatically reduces PA as temperature increases

Example during a print:
```
Base temp: 230°C, Base PA: 0.060
High flow detected → Boost +20°C → Temp 250°C, PA 0.048
```

## Dynamic Z-Window (DynZ)

DynZ is an intelligent learning system that detects and adapts to challenging print geometries like convex surfaces, domes, and spheres.

### The Problem

Convex surfaces create "stress zones" where:
- High toolhead speed (rapid direction changes)
- Low volumetric flow (short segments)
- High heater demand (constant temp adjustments)

This combination can cause thermal lag, inconsistent extrusion, and surface artifacts.

### How DynZ Works

1. **Learning**: DynZ divides Z-height into bins (default 1mm) and tracks stress conditions in each
2. **Detection**: When speed is high, flow is low, and heater PWM is high simultaneously, it's flagged as stress
3. **Scoring**: Each Z bin accumulates a stress score over time (scores decay when conditions improve)
4. **Relief**: When a bin's score exceeds the threshold, DynZ reduces acceleration to ease thermal demand
5. **Memory**: Stress patterns persist across layers, so the system "remembers" where domes start

### Configuration

DynZ is enabled by default. To customize, edit `auto_flow.cfg`:

```ini
# Enable/disable DynZ
variable_dynz_enable: True

# Z bin size (1.0mm = stable, 0.5mm = more sensitive)
variable_dynz_bin_height: 1.0

# Stress detection thresholds
variable_dynz_speed_thresh: 80.0      # mm/s toolhead speed
variable_dynz_flow_max: 8.0           # mm³/s volumetric flow
variable_dynz_pwm_thresh: 0.70        # heater duty cycle (0-1)

# Score thresholds
variable_dynz_activate_score: 4.0     # score to trigger relief
variable_dynz_deactivate_score: 1.5   # score to exit relief

# Acceleration during stress relief
variable_dynz_accel_relief: 3200      # mm/s² (lower = gentler moves)
```

### Monitoring

Check DynZ status during a print:
```
AT_DYNZ_STATUS
```

Output:
```
DynZ: ENABLED
State: ACTIVE (accel relief applied)
Z Height: 45.20 mm
Z Bin: 45 (bin height 1.0 mm)
Bin Score: 5.23
Accel (current): 3200 mm/s²
Mode: CLAMPING (convex stress detected)
```

## Smart Cooling

Smart Cooling automatically adjusts the part cooling fan based on flow rate and layer time, optimizing print quality without manual fan speed management.

### How It Works

1. **Flow-based reduction**: At high flow rates, the fast-moving plastic creates its own airflow and needs less fan cooling. Smart Cooling reduces fan speed proportionally.

2. **Layer time boost**: Short layers (fast prints or small features) don't have enough time to cool between layers. Smart Cooling increases fan speed for these quick layers.

3. **Material awareness**: Each material profile has its own cooling preferences (PLA wants high cooling, ABS wants minimal).

### Configuration

Smart Cooling is enabled by default. To customize, edit `auto_flow.cfg`:

```ini
# Enable/disable Smart Cooling
variable_sc_enable: True

# Flow threshold where cooling reduction starts (mm³/s)
variable_sc_flow_gate: 8.0

# Fan reduction per mm³/s above flow_gate (0-1 scale)
variable_sc_flow_k: 0.03

# Layer time threshold - layers faster than this get extra cooling
variable_sc_short_layer_time: 15.0

# Min/max fan limits (0.0-1.0 = 0-100%)
variable_sc_min_fan: 0.20
variable_sc_max_fan: 1.00

# First layer fan (usually 0 for bed adhesion)
variable_sc_first_layer_fan: 0.0
```

### Material Profile Overrides

Each material in `material_profiles.cfg` has its own cooling settings:

| Material | Min Fan | Max Fan | Notes |
|----------|---------|---------|-------|
| PLA | 50% | 100% | Needs aggressive cooling |
| PETG | 30% | 70% | Too much causes layer adhesion issues |
| ABS/ASA | 0% | 40% | Minimal cooling to prevent warping |
| TPU | 10% | 50% | Low cooling for layer adhesion |
| Nylon | 10% | 50% | Warps easily with too much cooling |
| PC | 0% | 30% | Very low cooling, high temps |

### Monitoring

Check Smart Cooling status during a print:
```
AT_SC_STATUS
```

Output:
```
Smart Cooling: ENABLED
Current Fan: 65%
Layer Time: 12.3s
Fan Range: 30% - 70%
Flow Gate: 10.0 mm³/s
```

## Optional: Print Analysis

After printing, get AI-powered suggestions to improve your settings:

```bash
cd ~/Klipper-Adaptive-Flow
python3 analyze_print.py
```

The AI analyzes your print data and suggests parameter adjustments:
- Suggestions marked **[✓ SAFE]** can be auto-applied
- Suggestions marked **[⚠ MANUAL]** require your review

**Providers:** GitHub Models (free), OpenAI, Anthropic

**[Setup guide →](docs/ANALYSIS.md)**

## Requirements

- E3D Revo hotend (HF or Standard)
- Klipper firmware
- 40W or 60W heater

## File Structure

| File | Purpose |
|------|---------|
| `auto_flow.cfg` | Main control logic |
| `material_profiles.cfg` | User-editable material profiles |
| `extruder_monitor.py` | Lookahead + logging (Klipper extra) |
| `gcode_interceptor.py` | G-code parsing (Klipper extra) |
| `analyze_print.py` | Post-print LLM analysis (optional) |
| `moonraker_hook.py` | Auto-analysis after print (optional) |

## License

MIT



