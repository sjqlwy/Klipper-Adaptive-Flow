# Material & Temperature Configuration

The system automatically configures temperature behavior based on detected material. No manual setup required.

---

## Material Auto-Detection

When `AT_START` runs, material is detected from your slicer's temperature setting:

| Temperature | Detected Material |
|-------------|-------------------|
| 280°C+ | PC (Polycarbonate) |
| 260-280°C | NYLON |
| 240-260°C | ABS / ASA |
| 220-240°C | PETG |
| 180-220°C | PLA |
| 160-180°C | TPU |

**No slicer plugins needed** — just set your normal print temperature.

---

## Per-Material Settings

Each material has tuned settings applied automatically:

### Flow Gates (When Boosting Activates)

Temperature boost only triggers when flow exceeds these thresholds, based on E3D Revo datasheet ratings:

| Material | High Flow Nozzle | Standard Nozzle | E3D Rated Max |
|----------|------------------|-----------------|---------------|
| PLA | 10 mm³/s | 8 mm³/s | 13 mm³/s @ 220°C |
| PETG | 14 mm³/s | 10 mm³/s | 17 mm³/s @ 240°C |
| ABS/ASA | 12 mm³/s | 9 mm³/s | 15 mm³/s @ 260°C |
| PC | 11 mm³/s | 8 mm³/s | — |
| NYLON | 12 mm³/s | 9 mm³/s | — |
| TPU | 5 mm³/s | 5 mm³/s | (boost disabled) |

**Why flow gates?** Prevents unnecessary temperature fluctuations during normal printing. Only boosts when you're actually pushing the hotend's limits.

### Speed K-Values (Boost Multiplier)

Controls how aggressively temperature increases with flow:

| Material | High Flow | Standard | Notes |
|----------|-----------|----------|-------|
| PLA | 0.80 | 0.40 | Low viscosity, moderate boost |
| PETG | 2.00 | 1.80 | High viscosity, aggressive boost |
| ABS/ASA | 0.80 | 0.80 | Medium viscosity |
| PC | 0.70 | 0.70 | Similar to ABS |
| NYLON | 0.90 | 0.90 | Moderate boost |
| TPU | 0.00 | 0.00 | Boost disabled (flexible) |

**Formula:** `temp_boost = flow_rate × speed_k`

Example: PETG at 15 mm³/s with HF nozzle → `15 × 2.0 = 30°C boost`

### Maximum Temperature Limits

Safety caps per material:

| Material | Max Temp |
|----------|----------|
| PLA | 235°C |
| PETG | 280°C (HF) / 270°C (Std) |
| ABS/ASA | 290°C |
| PC | 300°C |
| NYLON | 275°C |
| TPU | 240°C |

---

## Temperature Boost Behavior

### How Boosting Works

1. **Flow Calculation** — Live extrusion velocity × filament cross-section = volumetric flow
2. **Gate Check** — Only boost if flow exceeds material's gate threshold
3. **Boost Calculation** — `flow × speed_k` = raw boost amount
4. **Smoothing** — Exponential average prevents jitter
5. **Ramping** — Heats fast (4°C/s), cools slow (0.2°C/s)
6. **Safety Cap** — Never exceeds max temp for material

### Asymmetric Ramping ("Sticky Heat")

| Direction | Rate | Why |
|-----------|------|-----|
| Heating | 4°C/second | Quick response to flow increases |
| Cooling | 0.2°C/second | Maintains heat through corners and brief pauses |

**Why slow cooling?** During corners and short pauses, the plastic in the nozzle is still hot. Rapid cooling would increase viscosity, causing corner bulging.

### Acceleration Kick

Detects rapid flow increases and pre-heats before the move arrives:

```
If flow_acceleration > 2 mm³/s²:
    extra_boost = acceleration × 2.0
```

Prevents under-extrusion at the start of fast infill sections.

### Lookahead Boost

Parses upcoming G-code to predict flow changes:

- Sees high-flow moves coming in the next 2 seconds
- Pre-heats before they arrive
- Eliminates thermal lag at flow transitions

---

## Slicer Temperature Settings

### Recommended Approach

Set your slicer to **normal quality temperatures**. The script handles high-flow situations automatically.

| Material | Slicer Temp | Script Boosts To |
|----------|-------------|------------------|
| PLA | 200-210°C | up to 235°C |
| PETG | 235-245°C | up to 280°C |
| ABS/ASA | 245-255°C | up to 290°C |

### Max Volumetric Speed

Set in your slicer based on your heater:

| Setup | Recommended Limit |
|-------|-------------------|
| 40W + Standard Nozzle | 17 mm³/s |
| 40W + High Flow Nozzle | 24 mm³/s |
| 60W + Standard Nozzle | 20 mm³/s |
| 60W + High Flow Nozzle | 32 mm³/s |

**Note:** Above 26 mm³/s, the 40W heater runs at 100% duty cycle with no headroom for boosting.

---

## Self-Learning K-Values

The system monitors thermal response and auto-tunes over time:

### How It Works

1. **Monitors** actual vs target temperature during boosting
2. **Detects** patterns:
   - Consistently too cold → heater can't keep up → increase K
   - Consistently too hot → over-boosting → decrease K
3. **Adjusts** K-value by ±0.05 every 50 samples
4. **Saves** learned value for future prints

### Settings

```ini
variable_self_learning_enabled: True   # Enable/disable
variable_learning_rate: 0.05           # Adjustment per window
```

### Viewing Learned Values

At print end, the system reports average thermal error:
```
AT_END: Avg thermal error: 1.2C over 150 samples (negative=overshoot)
```

---

## Thermal Safety

### Runaway Protection

If temperature exceeds target by more than threshold:

1. **First fault** — Warning, boost reset to 0, drop to base temp
2. **Three consecutive faults** — Emergency shutdown

```ini
variable_thermal_runaway_threshold: 15.0   # °C above target
```

### Undertemp Detection

If heater can't keep up (temp drops below target):

1. **Warning message** displayed
2. **Boost reduced by 50%** to lower demand

```ini
variable_thermal_undertemp_threshold: 10.0   # °C below target
```

---

## Community Defaults

Material settings are fetched from a shared GitHub repository:

- **Auto-cached locally** for 24 hours
- **Works offline** after first fetch
- **Your saved values override** community defaults

Check community values:
```gcode
GET_COMMUNITY_DEFAULTS MATERIAL=PETG HF=1
```

Community defaults file: [community_defaults.json](../community_defaults.json)
