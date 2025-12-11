# Klipper Adaptive Flow 

**A closed-loop flow control detection system for Klipper.**

This system uses the TMC driver feedback from your extruder to actively manage temperature and pressure advance.
<br>Configured for TMC 2209 drivers.
<br> In your slicer filament settings, disable pressure advance. 

## Installation

### Step 1: Install the Python Extension
This script is required to read the TMC register data.

1.  Copy `extruder_monitor.py` to your Klipper extras directory:
2.  ~/klipper/klippy/extras/
    
3.  Restart the Klipper service:
    

### Step 2: Install the Configuration
1.  Copy `auto_flow.cfg` to your configuration directory (usually `~/printer_data/config/`).
2.  Open your `printer.cfg` and add the following:

```    
    [include auto_flow.cfg]

    [extruder_monitor]
    #This must match the name of your extruder stepper section
    stepper: extruder
    #Change this to match your specific driver (e.g., tmc2209 extruder)
    driver_name: tmc2209 extruder

    [save_variables]
    filename: ~/printer_data/config/sfs_auto_flow_vars.cfg
  ```
3.  In your TMC section of your extruder add in:
   ```
    [tmc2209 extruder]
    run_current: 0.650
    stealthchop_threshold: 0
    driver_SGTHRS: 120
```

4.  Add the following to your `PRINT_START` macro : - Edit to suit your build

    ```ini
    [gcode_macro PRINT_START]
gcode:
  # =================================================================
  # 1. PARAMETER SETUP
  # =================================================================
  {% set target_bed      = params.BED|default(60)|int %}
  {% set target_extruder = params.EXTRUDER|default(200)|int %}
  {% set material        = params.MATERIAL|default("PLA")|string %}
  
  # Default Config (Prevent Undefined Errors)
  {% set tol = 2 %}            # Bed tolerance (+/- deg)
  {% set probe_temp = 150 %}   # Safe temp for probing (no ooze)
  {% set soak_min = 0 %}       # Optional heat soak time

  # Geometry helpers
  {% set x_wait = printer.toolhead.axis_maximum.x|float / 2 %}
  {% set y_wait = printer.toolhead.axis_maximum.y|float / 2 %}

  # =================================================================
  # 2. MATERIAL CONFIGURATION
  # =================================================================
  {% set load_k = 0.0 %}   
  {% set speed_k = 0.0 %}  
  {% set pa_val = 0.0 %}
  {% set max_temp_safety = 300 %}

  {% if 'PLA' in material %}
      {% set load_k = 0.10 %}
      {% set speed_k = 0.50 %}
      {% set pa_val = 0.040 %}
      {% set max_temp_safety = 235 %}
  {% elif 'PETG' in material %}
      {% set load_k = 0.15 %}
      {% set speed_k = 0.60 %}
      {% set pa_val = 0.060 %}
      {% set max_temp_safety = 265 %}
  {% elif 'ABS' in material or 'ASA' in material %}
      {% set load_k = 0.20 %}
      {% set speed_k = 0.80 %}
      {% set pa_val = 0.050 %}
      {% set max_temp_safety = 290 %}
  {% elif 'PC' in material or 'NYLON' in material %}
      {% set load_k = 0.25 %}
      {% set speed_k = 0.90 %}
      {% set pa_val = 0.055 %}
      {% set max_temp_safety = 300 %}
  {% elif 'TPU' in material %}
      {% set load_k = 0.0 %}
      {% set speed_k = 0.0 %}
      {% set pa_val = 0.20 %} 
      {% set max_temp_safety = 240 %}
  {% endif %}

  # =================================================================
  # 3. PREPARATION
  # =================================================================
  AT_RESET_STATE
  AT_DISABLE
  
  M117 Homing...
  G28
  G90

  M117 Heating bed to {target_bed}C
  M140 S{target_bed}
  TEMPERATURE_WAIT SENSOR=heater_bed MINIMUM={target_bed - tol} MAXIMUM={target_bed + tol}

  {% if soak_min > 0 %}
    M117 Soaking bed...
    G4 P{soak_min * 60000}
  {% endif %}

  # Heat nozzle to safe probe temp
  M117 Nozzle to {probe_temp}C
  M104 S{probe_temp}
  M109 S{probe_temp}

  # =================================================================
  # 4. QGL / MESH (Adjust based on printer type)
  # =================================================================
  # If Voron/Trident:
  # QUAD_GANTRY_LEVEL
  # G28 Z

  M117 Meshing...
  BED_MESH_CLEAR
  BED_MESH_CALIBRATE ADAPTIVE=1

  # =================================================================
  # 5. PRINT HEAT & ACTIVATE
  # =================================================================
  M117 Heating nozzle to {target_extruder}C
  M104 S{target_extruder}
  M109 S{target_extruder}

  {% if pa_val > 0 %}
      SET_PRESSURE_ADVANCE ADVANCE={pa_val}
  {% endif %}

  {% if load_k > 0 or speed_k > 0 %}
      AT_SET_VISC_K K={load_k}
      AT_SET_FLOW_K K={speed_k}
      AT_SET_MAX MAX={max_temp_safety}
      AT_ENABLE
      RESPOND MSG="Adaptive Flow: ON ({material})"
  {% else %}
      AT_DISABLE
      RESPOND MSG="Adaptive Flow: OFF ({material})"
  {% endif %}

  # =================================================================
  # 6. PRIME LINE
  # =================================================================
  M117 Priming...
  G0 X{x_wait - 50} Y4 F10000
  G0 Z0.4
  G91
  G1 X100 E20 F1000
  G90
  M117 Printing...

    
5.  Add the following to your `PRINT_END` macro :

    ```ini
    [gcode_macro PRINT_END]
    gcode:
        # 1. Disable Systems
        AT_DISABLE
        
        

### Step 3: Configure Your Slicer (Orca Slicer)
Add the following to your **Machine G-code** settings in Orca Slicer (under Printer Settings → Machine G-code → Machine start G-code):

```gcode
PRINT_START BED={first_layer_bed_temperature[0]} EXTRUDER={first_layer_temperature[0]} MATERIAL={filament_type[0]}
```

This passes the bed temperature, extruder temperature, and filament type from the slicer to your `PRINT_START` macro.

---

## Tuning & Usage

### 1. Flow K (Speed Boost)
How much temp to add based on speed.

**Command:** `AT_SET_FLOW_K K=0.5`

**Meaning:** For every 1mm³/s of flow, add ~0.5°C.

### 2. Viscosity K (Resistance Boost)
How much temp to add if the extruder is struggling (high load).

**Command:** `AT_SET_VISC_K K=0.1`

**Meaning:** If strain increases, boost temp to melt plastic faster.

### 3. Max Temperature Limit
Set the maximum temperature ceiling for safety.

**Command:** `AT_SET_MAX MAX=300`

**Meaning:** Prevents the auto-temp system from exceeding this temperature.

### 4. Crash Sensitivity
To adjust how sensitive the crash detection is, edit `auto_flow.cfg`:

*   `load_delta > 20`: Lower this number to make it more sensitive (detect smaller blobs). Raise it if you get false positives.

---

## Requirements

*   Klipper Firmware
*   TMC Stepper Driver on Extruder (TMC2209, TMC2130, TMC5160)
*   `[save_variables]` enabled
