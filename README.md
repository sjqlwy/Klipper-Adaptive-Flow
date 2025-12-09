# Klipper Adaptive Flow & Crash Guard

**A closed-loop flow control and artifact detection system for Klipper.**

This system uses the TMC driver feedback from your extruder to actively manage temperature, pressure advance, and print speed in real-time. It requires **no external sensors** and **no slicer modifications**.

## Features

### 1. 🌊 Hydro-Dynamic Temp Boosting
Automatically raises the Hotend Temperature as flow rate increases (Feed-Forward). This compensates for the thermal lag of the heater block during high-speed moves.

### 2. 🛡️ Extrusion Crash Detection
Monitors the extruder motor for sudden resistance spikes (Load Deltas).
*   **Blobs/Tangles/Clogs:** If the nozzle hits a blob or the filament tangles, the resistance spikes.
*   **Automatic Recovery:** If >3 spikes are detected in a single layer, the system automatically slows the print speed to **50%** for the next 3 layers to allow the print to recover, then restores full speed.

### 3. 🧠 Smart Cornering ("Sticky Heat")
Prevents the "Bulging Corner" issue common with other auto-temp scripts.
*   The script heats up fast but cools down *very slowly*.
*   This ensures the plastic remains fluid during the deceleration phase of a corner, preventing internal pressure buildup.

### 4. 📐 Dynamic Pressure Advance
Automatically **lowers** Pressure Advance (PA) as the temperature rises.
*   Hotter plastic is more fluid and requires less PA.
*   This prevents "gaps" or "cutting corners" caused by aggressive PA at high temperatures.

### 5. 👁️ Machine-Side Layer Watcher
Uses a Z-height monitor to detect layer changes automatically. You do not need to add custom G-Code to your Slicer.

---

## Installation

### Step 1: Install the Python Extension
This script is required to read the TMC register data.

1.  Copy `extras/extruder_monitor.py` to your Klipper extras directory:
    ```bash
    cp extras/extruder_monitor.py ~/klipper/klippy/extras/
    ```
2.  Restart the Klipper service:
    ```bash
    sudo service klipper restart
    ```

### Step 2: Install the Configuration
1.  Copy `config/auto_flow.cfg` to your configuration directory (usually `~/printer_data/config/`).
2.  Open your `printer.cfg` and add the following:

```ini
[include auto_flow.cfg]

[extruder_monitor]
# Change this to match your specific driver (e.g., tmc2209 extruder)
driver_name: tmc2209 extruder

[save_variables]
filename: ~/printer_data/config/sfs_auto_flow_vars.cfg


[gcode_macro PRINT_START]
gcode:
    # ... (Your heating and homing code) ...
    
    # Initialize Adaptive Flow
    AT_RESET_STATE
    AT_ENABLE


[gcode_macro PRINT_END]
gcode:
    # Disable Adaptive Flow
    AT_DISABLE
    
    # ... (Your parking and cooldown code) ...



Tuning & Usage
1. Flow K (Speed Boost)
How much temp to add based on speed.
Command: AT_SET_FLOW_K K=0.5
Meaning: For every 1mm³/s of flow, add ~0.5°C.
2. Viscosity K (Resistance Boost)
How much temp to add if the extruder is struggling (high load).
Command: AT_SET_VISC_K K=0.1
Meaning: If strain increases, boost temp to melt plastic faster.
3. Crash Sensitivity
To adjust how sensitive the crash detection is, edit auto_flow.cfg:
load_delta > 20: Lower this number to make it more sensitive (detect smaller blobs). Raise it if you get false positives.
Requirements
Klipper Firmware
TMC Stepper Driver on Extruder (TMC2209, TMC2130, TMC5160)
[save_variables] enabled
