# Klipper Adaptive Flow — Lookahead Branch

This branch adds **live G-code lookahead** to the Adaptive Flow system, enabling predictive temperature and pressure advance adjustments based on upcoming extrusion moves.

## What's New in This Branch

The `lookahead-feature` branch extends the original Adaptive Flow with:

| Feature | Description |
|---------|-------------|
| **Live G-code parsing** | `extruder_monitor.py` intercepts incoming `G0/G1` commands in real-time |
| **Lookahead buffer** | Stores upcoming extrusion segments (E delta + duration) |
| **Predicted extrusion rate** | Calculates expected mm/s based on buffered moves |
| **Proactive temp boost** | Raises temperature *before* high-flow sections arrive |
| **Smoother transitions** | Reduces under-extrusion at flow ramp-ups |

## How It Works

```
G-code Stream → extruder_monitor.py → Lookahead Buffer
                                            ↓
                            predicted_extrusion_rate (mm/s)
                                            ↓
                     auto_flow.cfg → lookahead_boost → M104 / PA adjust
```

1. As G-code streams to Klipper, `extruder_monitor.py` parses `G0/G1` moves
2. It calculates upcoming extrusion demand and stores it in a buffer
3. Every 1 second, `auto_flow.cfg` reads `predicted_extrusion_rate`
4. If upcoming flow > current flow, it applies a **lookahead boost** to temperature
5. Temperature ramps *before* the high-flow section, not after

## Files

| File | Purpose |
|------|---------|
| `extruder_monitor.py` | Klipper module — TMC load reading + live lookahead |
| `auto_flow.cfg` | Macros for adaptive temp, PA, blob detection, and lookahead boost |

## Installation

1. Copy `extruder_monitor.py` to Klipper extras:
   ```bash
   cp extruder_monitor.py ~/klipper/klippy/extras/
   ```

2. Add `auto_flow.cfg` to your config:
   ```ini
   [include auto_flow.cfg]
   ```

3. Restart Klipper:
   ```bash
   sudo service klipper restart
   ```

4. Check logs for:
   ```
   Live G-code lookahead hook installed.
   ```

## Usage

Enable adaptive flow before printing:
```gcode
AT_INIT_MATERIAL MATERIAL=PLA
```

The system will automatically:
- Monitor extruder load (SG_RESULT)
- Track live extrusion velocity
- Parse upcoming G-code for lookahead
- Adjust temperature and pressure advance in real-time

## Tuning

In `auto_flow.cfg`, the lookahead boost multiplier can be adjusted:
```jinja
{% set lookahead_boost = lookahead_delta * 0.5 %}  ; 0.5°C per mm³/s
```

Increase for more aggressive pre-heating, decrease if you see overheating on small prints.

## Compatibility

- Requires TMC driver with StallGuard (e.g., TMC2209)
- Tested on Klipper with Raspberry Pi
- Minimal CPU/USB overhead (host-side parsing only)

## Branch Info

| Branch | Description |
|--------|-------------|
| `main` | Original Adaptive Flow (reactive only) |
| `lookahead-feature` | **This branch** — adds predictive lookahead |



