#!/bin/bash
# Klipper Adaptive Flow Diagnostic Script
# This tests what flow data sources are actually available and working

echo "=================================================="
echo "KLIPPER ADAPTIVE FLOW DIAGNOSTIC"
echo "=================================================="
echo ""

# Check if extruder_monitor module exists and is loaded
echo "1. Checking Python modules..."
if [ -f ~/klipper/klippy/extras/extruder_monitor.py ]; then
    echo "   ✓ extruder_monitor.py exists"
    MOD_DATE=$(stat -c %y ~/klipper/klippy/extras/extruder_monitor.py)
    echo "     Modified: $MOD_DATE"
else
    echo "   ✗ extruder_monitor.py NOT FOUND"
fi

if [ -f ~/klipper/klippy/extras/gcode_interceptor.py ]; then
    echo "   ✓ gcode_interceptor.py exists"
else
    echo "   ✗ gcode_interceptor.py NOT FOUND"
fi

# Check if modules are loaded in Klipper
echo ""
echo "2. Checking if modules loaded in Klipper..."
if grep -q "extruder_monitor" ~/printer_data/logs/klippy.log 2>/dev/null; then
    echo "   ✓ extruder_monitor loaded"
    grep "extruder_monitor" ~/printer_data/logs/klippy.log | tail -2
else
    echo "   ✗ extruder_monitor NOT loaded or not in logs"
fi

# Check printer.cfg includes
echo ""
echo "3. Checking printer.cfg includes..."
if grep -q "extruder_monitor" ~/printer_data/config/printer.cfg; then
    echo "   ✓ [extruder_monitor] in printer.cfg"
else
    echo "   ✗ [extruder_monitor] NOT in printer.cfg"
fi

if grep -q "gcode_interceptor" ~/printer_data/config/printer.cfg; then
    echo "   ✓ [gcode_interceptor] in printer.cfg"
else
    echo "   ✗ [gcode_interceptor] NOT in printer.cfg"
fi

if grep -q "auto_flow_defaults.cfg" ~/printer_data/config/printer.cfg; then
    echo "   ✓ auto_flow_defaults.cfg included"
else
    echo "   ✗ auto_flow_defaults.cfg NOT included"
fi

# Check extruder configuration
echo ""
echo "4. Checking extruder configuration..."
echo "   Extruder step_pin:"
grep "step_pin:" ~/printer_data/config/printer.cfg | grep -i "extruder" -A 1 | head -3

# Check what flow detection method is configured
echo ""
echo "5. Checking flow detection code..."
grep -A 5 "CAN bus extruders" ~/printer_data/config/auto_flow_defaults.cfg | head -10

# Create a test macro file
echo ""
echo "6. Creating diagnostic test macro..."
cat > ~/printer_data/config/flow_diagnostic.cfg << 'EOFMACRO'
# Adaptive Flow Diagnostic Macro
# Run TEST_FLOW_VALUES during a print to see actual values

[gcode_macro TEST_FLOW_VALUES]
description: Show all flow-related values from available sources
gcode:
    RESPOND MSG="=== FLOW DIAGNOSTIC ==="
    {% if "motion_report" in printer %}
        {% set mr_vel = printer.motion_report.live_extruder_velocity|default(-999)|float %}
        RESPOND MSG="motion_report.live_extruder_velocity = {mr_vel}"
    {% else %}
        RESPOND MSG="motion_report NOT AVAILABLE"
    {% endif %}
    
    {% if "extruder_monitor" in printer %}
        RESPOND MSG="extruder_monitor found"
        {% set pred = printer.extruder_monitor.predicted_extrusion_rate|default(-999)|float %}
        {% set curr = printer.extruder_monitor.current_extrusion_rate|default(-999)|float %}
        RESPOND MSG="  predicted_extrusion_rate = {pred}"
        RESPOND MSG="  current_extrusion_rate = {curr}"
    {% else %}
        RESPOND MSG="extruder_monitor NOT AVAILABLE"
    {% endif %}
    
    {% set calc_flow = printer["gcode_macro _AUTO_TEMP_CORE"].last_vol_flow|default(-999)|float %}
    RESPOND MSG="Core loop last_vol_flow = {calc_flow}"
    RESPOND MSG="=== END DIAGNOSTIC ==="
EOFMACRO

echo ""
echo "=================================================="
echo "DIAGNOSTIC COMPLETE"
echo "=================================================="
echo ""
echo "NEXT STEPS:"
echo "1. Fix your printer.cfg (remove broken line at end)"
echo "   Run: sed -i '/test_flow_debug.cfg/d' ~/printer_data/config/printer.cfg"
echo ""
echo "2. Add diagnostic macro to printer.cfg:"
echo "   Add this line near the top: [include flow_diagnostic.cfg]"
echo ""
echo "3. Restart Klipper: sudo systemctl restart klipper"
echo ""
echo "4. Start a print and run: TEST_FLOW_VALUES"
echo ""
echo "5. Send the output to diagnose the issue"
echo ""
