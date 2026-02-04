# Dynamic Z-Window (DynZ)

DynZ is an intelligent learning system that detects and adapts to challenging print geometries like convex surfaces, domes, and spheres.

## What Problem Does DynZ Solve?

When your 3D printer prints **curved surfaces** (like the top of a dome or a sphere), it faces a unique challenge:

1. **The nozzle moves very fast** (lots of quick direction changes to follow the curve)
2. **But it's extruding very little plastic** (short segments = low flow)
3. **The hotend has to work hard** to maintain temperature (high heater demand)

This combination can cause:
- **Temperature drops** (the hotend can't keep up)
- **Inconsistent extrusion** (plastic doesn't melt evenly)
- **Surface defects** (visible artifacts on your print)

## How DynZ Fixes This

DynZ is a **learning system** that watches for these stressful conditions and **automatically slows down** the printer when needed.

### Step-by-Step Process

1. **Dividing the Print into Zones**
   - DynZ divides your print's height into "bins" (by default, each bin is 1mm tall)
   - Example: If your print is 50mm tall, DynZ creates 50 bins (one for each millimeter)

2. **Detecting Stress**
   - As the print progresses, DynZ checks if **all three** of these are happening at once:
     - **High speed** (nozzle moving fast, e.g., >80 mm/s)
     - **Low flow** (extruding little plastic, e.g., <8 mm³/s)
     - **High heater effort** (hotend working hard, e.g., >70% power)
   - If all three are true, DynZ says "this is a stress zone!"

3. **Building a Score**
   - Each time stress is detected in a Z-bin, DynZ adds points to that bin's "stress score"
   - When conditions improve, the score slowly decays (goes back down)
   - This prevents false positives from brief spikes

4. **Taking Action**
   - If a bin's score gets high enough (default: ≥4.0 points), DynZ **reduces acceleration**
   - This slows down the printer's movements, giving the hotend time to catch up
   - The system "remembers" stress zones, so it can pre-emptively slow down on future layers

5. **Returning to Normal**
   - When the score drops back down (default: ≤1.5 points), DynZ releases the acceleration limit
   - The printer returns to full speed

## Real-World Example

Imagine printing a model with a **dome** on top:

| Z-Height | What Happens | DynZ Action |
|----------|--------------|-------------|
| 0-30mm | Printing walls (steady flow, normal speed) | **IDLE** - No stress, normal printing |
| 31mm | Dome starts (speed increases, flow drops) | **LEARNING** - Detects stress, score starts climbing |
| 32-35mm | Dome curve (continuous stress) | **CLAMPING** - Score hits 4.0, reduces acceleration to 3200 mm/s² |
| 36mm | Dome flattens (conditions improve) | **CLAMPING** - Still active, score decaying |
| 37mm | Score drops to 1.5 | **IDLE** - Returns to normal acceleration |

## Configuration

DynZ is enabled by default. To customize, edit `auto_flow_user.cfg`:

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

### Parameter Guide

| Parameter | What It Does | Default | When to Change |
|-----------|-------------|---------|----------------|
| `dynz_enable` | Turn DynZ on/off | `True` | Disable if you don't print domes/spheres |
| `dynz_bin_height` | Size of each Z zone | `1.0` mm | Smaller (0.5mm) = more sensitive, larger (2.0mm) = more stable |
| `dynz_speed_thresh` | "High speed" threshold | `80` mm/s | Lower = catches slower moves as stress |
| `dynz_flow_max` | "Low flow" threshold | `8` mm³/s | Higher = catches more situations as stress |
| `dynz_pwm_thresh` | "High heater effort" threshold | `0.70` (70%) | Lower = triggers more easily |
| `dynz_score_inc` | Score added per stress detection | `1.0` | Higher = faster response |
| `dynz_score_decay` | Score multiplier when no stress | `0.90` (10% decay) | Higher (0.95) = longer memory |
| `dynz_activate_score` | Points needed to slow down | `4.0` | Lower = reacts faster, higher = more patient |
| `dynz_deactivate_score` | Points needed to return to normal | `1.5` | Higher = stays active longer |
| `dynz_accel_relief` | Slowed-down acceleration | `3200` mm/s² | Lower = gentler (safer), higher = faster (riskier) |

## Monitoring

Check DynZ status during a print:
```
AT_DYNZ_STATUS
```

> See [COMMANDS.md](COMMANDS.md#at_dynz_status) for full command documentation.

Output:
```
===== DYNZ STATUS =====
DynZ: ENABLED
State: ACTIVE (accel relief applied)
Z Height: 45.20 mm
Z Bin: 45 (bin height 1.0 mm)
Bin Score: 5.23
Activate ≥ 4.0
Deactivate ≤ 1.5
Accel (current): 3200 mm/s²
Accel (base):    5000 mm/s²
Accel (relief):  3200 mm/s²
Mode: CLAMPING (convex stress detected)
=======================
```

### Status Modes

| Mode | Description |
|------|-------------|
| **IDLE** | Everything's normal, no stress detected |
| **LEARNING** | Stress detected, but not enough to act yet (score building) |
| **CLAMPING** | Stress is high enough, printer is slowed down |

## How Stress Detection Works

DynZ considers a moment "stressed" when ALL three conditions are true simultaneously:

```
Speed > dynz_speed_thresh (80 mm/s)
  AND
Flow < dynz_flow_max (8 mm³/s)
  AND
Heater PWM > dynz_pwm_thresh (0.70)
```

This combination typically occurs on:
- Dome tops (rapid small movements)
- Sphere surfaces (constant direction changes)
- Small circular features at height
- Any geometry with lots of short, fast segments

## Tuning Tips

### If DynZ is Too Aggressive (slowing down when it shouldn't)
```ini
variable_dynz_speed_thresh: 100.0     # Only catch very fast moves
variable_dynz_flow_max: 6.0           # Only catch very low flows
variable_dynz_pwm_thresh: 0.80        # Only react to severe heater stress
variable_dynz_activate_score: 6.0     # Need more stress to trigger
```

### If DynZ is Not Aggressive Enough (artifacts still appearing)
```ini
variable_dynz_speed_thresh: 60.0      # Catch slower moves
variable_dynz_flow_max: 10.0          # Catch higher flows
variable_dynz_pwm_thresh: 0.60        # Trigger more easily
variable_dynz_activate_score: 3.0     # React sooner
variable_dynz_accel_relief: 2500      # Slow down more when triggered
```

### For Smoother Transitions
```ini
variable_dynz_score_decay: 0.95       # Slower decay = longer memory
variable_dynz_deactivate_score: 2.5   # Higher = stays active longer
```

## Clearing Learned Data

DynZ stores bin scores in Klipper's save_variables. To clear all learned stress zones:

```bash
# SSH into your printer
cd ~/printer_data/config
# Edit your save_variables file and remove lines starting with "dynz_bin_"
```

Or create a macro:
```ini
[gcode_macro AT_DYNZ_CLEAR]
gcode:
    # Note: This requires manual editing of variables.cfg
    RESPOND MSG="DynZ: Clear bin scores by editing variables.cfg"
    RESPOND MSG="Remove all lines starting with dynz_bin_"
```

## Logging

When print logging is enabled, DynZ state is captured in the CSV:
- `dynz_active`: 1 if relief is active, 0 if not
- `accel`: Current acceleration value

This allows post-print analysis to see when and where DynZ activated.

## Bottom Line

**DynZ is like a smart co-pilot** that watches for dangerous conditions (fast moves + low flow + hot heater) and automatically eases off the throttle when needed. It learns where your print has tricky geometry and adapts to keep extrusion smooth.