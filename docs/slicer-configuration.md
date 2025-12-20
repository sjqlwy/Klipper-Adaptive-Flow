# Slicer Configuration

How to configure your slicer to work with Klipper Adaptive Flow.

---

## Start G-code

Add these lines to your slicer's start G-code. The key is calling `AT_START` **after** your heating commands.

### PrusaSlicer / SuperSlicer / OrcaSlicer

```gcode
; Start G-code
M104 S[first_layer_temperature] ; Set hotend temp
M140 S[first_layer_bed_temperature] ; Set bed temp
G28 ; Home
M190 S[first_layer_bed_temperature] ; Wait for bed
M109 S[first_layer_temperature] ; Wait for hotend
; Your purge line, bed mesh, etc here

AT_START ; Enable adaptive flow - MUST be after heating!
```

### Cura

```gcode
; Start G-code
M104 S{material_print_temperature_layer_0} ; Set hotend temp
M140 S{material_bed_temperature_layer_0} ; Set bed temp
G28 ; Home
M190 S{material_bed_temperature_layer_0} ; Wait for bed
M109 S{material_print_temperature_layer_0} ; Wait for hotend
; Your purge line, bed mesh, etc here

AT_START ; Enable adaptive flow - MUST be after heating!
```

### Using PRINT_START Macro (Recommended)

If you use a `PRINT_START` macro, add `AT_START` at the end:

**Slicer start G-code:**
```gcode
PRINT_START BED=[first_layer_bed_temperature] EXTRUDER=[first_layer_temperature]
```

**In your printer.cfg:**
```ini
[gcode_macro PRINT_START]
gcode:
    {% set BED = params.BED|default(60)|int %}
    {% set EXTRUDER = params.EXTRUDER|default(200)|int %}
    
    G28                          ; Home all axes
    M190 S{BED}                  ; Wait for bed temp
    M109 S{EXTRUDER}             ; Wait for extruder temp
    BED_MESH_CALIBRATE           ; Optional: bed mesh
    
    ; Your purge line here
    
    AT_START                     ; Enable adaptive flow (AFTER heating!)
```

---

## End G-code

### PrusaSlicer / SuperSlicer / OrcaSlicer

```gcode
AT_END ; Disable adaptive flow and report stats
M104 S0 ; Turn off hotend
M140 S0 ; Turn off bed
G28 X Y ; Home X/Y
M84 ; Disable motors
```

### Using PRINT_END Macro

**Slicer end G-code:**
```gcode
PRINT_END
```

**In your printer.cfg:**
```ini
[gcode_macro PRINT_END]
gcode:
    AT_END                       ; Disable adaptive flow first!
    M104 S0                      ; Turn off hotend
    M140 S0                      ; Turn off bed
    G91                          ; Relative positioning
    G1 Z10 F3000                 ; Raise Z 10mm
    G90                          ; Absolute positioning
    G28 X Y                      ; Home X/Y
    M84                          ; Disable motors
```

---

## Why Order Matters

### AT_START Must Be After Heating

`AT_START` reads `printer.extruder.target` to detect material. If called before `M109`, the target is 0 and detection fails.

**Wrong:**
```gcode
AT_START        ; ❌ Target temp is 0!
M109 S240       ; Heating happens after
```

**Correct:**
```gcode
M109 S240       ; Heat first
AT_START        ; ✅ Now target is 240, detects PETG
```

### AT_END Must Be Before Heater Off

`AT_END` reports statistics and saves learned values. If the heater is already off, some stats may be incorrect.

**Wrong:**
```gcode
M104 S0         ; Heater off
AT_END          ; ❌ Thermal stats meaningless
```

**Correct:**
```gcode
AT_END          ; ✅ Report and save while still hot
M104 S0         ; Then turn off heater
```

---

## Filament-Specific Start G-code

Some slicers support per-filament start G-code. You can optionally pass material type explicitly:

### PrusaSlicer Filament Settings

In **Filament Settings → Custom G-code → Start G-code**:

```gcode
; This runs before the print start g-code
SET_GCODE_VARIABLE MACRO=_AUTO_TEMP_CORE VARIABLE=detected_material VALUE="'PETG'"
```

This overrides auto-detection for specific filament profiles.

---

## Temperature Settings

### First Layer Temperature

Set your normal first layer temperature. The script doesn't boost during the first few layers (focuses on adhesion).

### Other Layers

Set your normal printing temperature. The script boosts automatically when needed.

| Material | Recommended Slicer Temp |
|----------|------------------------|
| PLA | 200-215°C |
| PETG | 235-245°C |
| ABS/ASA | 245-255°C |
| TPU | 220-235°C |

---

## Pressure Advance

### Disable In Slicer

The script manages PA dynamically. Set Linear Advance / Pressure Advance to **0** in your slicer:

- **PrusaSlicer:** Printer Settings → Advanced → Pressure Advance = 0
- **Cura:** Not applicable (Cura doesn't have PA)
- **SuperSlicer:** Same as PrusaSlicer

### Store Values In Klipper

Instead of slicer PA, save calibrated values to Klipper:

```gcode
AT_SET_PA MATERIAL=PLA PA=0.045
AT_SET_PA MATERIAL=PETG PA=0.055
```

These are loaded automatically when `AT_START` detects the material.

---

## Max Volumetric Speed

Set this in your slicer to match your hardware:

| Setup | Slicer Limit |
|-------|--------------|
| 40W heater + Standard nozzle | 17 mm³/s |
| 40W heater + High Flow nozzle | 24 mm³/s |
| 60W heater + Standard nozzle | 20 mm³/s |
| 60W heater + High Flow nozzle | 32 mm³/s |

### Where To Set

- **PrusaSlicer:** Filament Settings → Advanced → Max volumetric speed
- **SuperSlicer:** Same location
- **Cura:** Not directly available — control via speed limits
- **OrcaSlicer:** Filament → Advanced → Max volumetric speed

---

## Retraction Settings

Use your normal retraction settings. The script does not modify retraction behavior.

Recommended starting points for E3D Revo:

| Material | Retraction Distance | Retraction Speed |
|----------|---------------------|------------------|
| PLA | 0.4-0.6 mm | 35 mm/s |
| PETG | 0.6-0.8 mm | 30 mm/s |
| ABS/ASA | 0.4-0.6 mm | 35 mm/s |
| TPU | 1.0-2.0 mm | 20 mm/s |

---

## Example: Complete OrcaSlicer Setup

### Machine Start G-code
```gcode
PRINT_START BED=[hot_plate_temp_initial_layer] EXTRUDER=[nozzle_temperature_initial_layer]
```

### Machine End G-code
```gcode
PRINT_END
```

### Filament Settings
- Max volumetric speed: 24 mm³/s (for 40W + HF)
- Pressure advance: 0

### printer.cfg
```ini
[gcode_macro PRINT_START]
gcode:
    {% set BED = params.BED|default(60)|int %}
    {% set EXTRUDER = params.EXTRUDER|default(200)|int %}
    
    G28
    M190 S{BED}
    M109 S{EXTRUDER}
    
    AT_START

[gcode_macro PRINT_END]
gcode:
    AT_END
    M104 S0
    M140 S0
    G28 X Y
    M84
```
