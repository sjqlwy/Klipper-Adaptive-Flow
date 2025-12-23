#!/usr/bin/env python3
"""
Adaptive Flow Print Analyzer

Analyzes print session logs and provides tuning suggestions via LLM.
Works with any OpenAI-compatible API (OpenAI, Anthropic, Ollama, OpenRouter, etc.)

Usage:
    python3 analyze_print.py                    # Analyze most recent print
    python3 analyze_print.py <summary.json>     # Analyze specific print
    python3 analyze_print.py --auto             # Auto-apply safe suggestions
    
Configuration:
    Set environment variables or edit CONFIG below:
    - ADAPTIVE_FLOW_API_KEY: Your API key
    - ADAPTIVE_FLOW_API_URL: API endpoint (default: OpenAI)
    - ADAPTIVE_FLOW_MODEL: Model name (default: gpt-4o-mini)
"""

import os
import sys
import json
import glob
import csv
from datetime import datetime

# =============================================================================
# CONFIGURATION - Edit these or use environment variables
# =============================================================================
CONFIG = {
    # API Settings (OpenAI-compatible endpoint)
    'api_key': os.environ.get('ADAPTIVE_FLOW_API_KEY', ''),
    'api_url': os.environ.get('ADAPTIVE_FLOW_API_URL', 'https://api.openai.com/v1/chat/completions'),
    'model': os.environ.get('ADAPTIVE_FLOW_MODEL', 'gpt-4o-mini'),
    
    # Alternative providers (uncomment to use):
    # Anthropic (via their OpenAI-compatible endpoint):
    # 'api_url': 'https://api.anthropic.com/v1/messages',
    # 'model': 'claude-3-haiku-20240307',
    
    # Ollama (local, free):
    # 'api_url': 'http://localhost:11434/v1/chat/completions',
    # 'model': 'llama3.1',
    # 'api_key': 'ollama',  # Ollama doesn't need a real key
    
    # OpenRouter (multi-model):
    # 'api_url': 'https://openrouter.ai/api/v1/chat/completions',
    # 'model': 'anthropic/claude-3-haiku',
    
    # Log directory
    'log_dir': os.path.expanduser('~/printer_data/logs/adaptive_flow'),
    
    # Printer connection (for auto-apply)
    'moonraker_url': 'http://localhost:7125',  # or http://192.168.1.66:7125
}

# =============================================================================
# ANALYSIS PROMPT - The secret sauce
# =============================================================================
ANALYSIS_PROMPT = """You are an expert 3D printing engineer analyzing thermal control data from a Klipper printer running Adaptive Flow temperature control.

## System Overview
The Adaptive Flow system dynamically adjusts extruder temperature based on:
- **Flow boost**: Temperature increases with volumetric flow (mm³/s)
- **Speed boost**: Extra heating for high linear speeds (>100mm/s)
- **Dynamic PA**: Pressure Advance scales with temperature boost

## Current Configuration
- speed_boost_k: 0.08 (°C per mm/s above 100mm/s threshold)
- Max boost: 50°C above base temperature
- Loop interval: 1 second
- Ramp rate (rise): 4.0°C/s
- Ramp rate (fall): 1.0°C/s for PLA, 1.5°C/s for PETG

## Print Session Data
```json
{summary_json}
```

## Detailed CSV Sample (last 100 rows if available)
```csv
{csv_sample}
```

## Analysis Tasks
1. **Thermal Response**: Is the heater keeping up? (Look at avg_pwm, max_pwm)
2. **Boost Effectiveness**: Is boost appropriate for the flow rates seen?
3. **Under-extrusion Risk**: High speed + low boost = possible under-extrusion
4. **Over-heating Risk**: High boost + high PWM = heater saturated
5. **PA Adjustment**: Is dynamic PA helping or hurting?

## Output Format
Provide your analysis in this exact JSON format:
```json
{
    "assessment": "Brief 1-2 sentence overall assessment",
    "issues": [
        {"severity": "high|medium|low", "description": "Issue description"}
    ],
    "suggestions": [
        {
            "parameter": "parameter_name",
            "current": "current_value",
            "suggested": "new_value", 
            "reason": "Why this change helps",
            "safe_to_auto_apply": true|false
        }
    ],
    "print_quality_prediction": "excellent|good|fair|poor",
    "notes": "Any additional observations"
}
```

Be specific with parameter names that match the auto_flow.cfg variables:
- speed_boost_k, speed_boost_threshold
- ramp_rate_rise, ramp_rate_fall
- max_boost_limit
- flow_smoothing

Only mark safe_to_auto_apply=true for conservative changes that won't cause print failures."""


def load_summary(summary_path):
    """Load summary JSON file."""
    with open(summary_path, 'r') as f:
        return json.load(f)


def load_csv_sample(csv_path, max_rows=100):
    """Load last N rows of CSV for detailed analysis."""
    if not os.path.exists(csv_path):
        return "CSV file not found"
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Get header + last max_rows
        if len(rows) <= max_rows + 1:
            sample_rows = rows
        else:
            sample_rows = [rows[0]] + rows[-(max_rows):]
        
        return '\n'.join([','.join(row) for row in sample_rows])
    except Exception as e:
        return f"Error reading CSV: {e}"


def find_latest_summary():
    """Find the most recent summary JSON file."""
    pattern = os.path.join(CONFIG['log_dir'], '*_summary.json')
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def call_llm_api(prompt, summary_json, csv_sample):
    """Call the LLM API with the analysis prompt."""
    import urllib.request
    import ssl
    
    if not CONFIG['api_key']:
        print("ERROR: No API key configured.")
        print("Set ADAPTIVE_FLOW_API_KEY environment variable or edit CONFIG in this script.")
        print("\nFor free local analysis, install Ollama and uncomment the Ollama config.")
        return None
    
    # Build the full prompt
    full_prompt = ANALYSIS_PROMPT.replace('{summary_json}', json.dumps(summary_json, indent=2))
    full_prompt = full_prompt.replace('{csv_sample}', csv_sample)
    
    # Prepare API request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CONFIG["api_key"]}'
    }
    
    payload = {
        'model': CONFIG['model'],
        'messages': [
            {'role': 'system', 'content': 'You are a 3D printing thermal control expert. Always respond with valid JSON.'},
            {'role': 'user', 'content': full_prompt}
        ],
        'temperature': 0.3,  # Low temp for consistent, focused analysis
        'max_tokens': 2000
    }
    
    try:
        # Handle Anthropic's different API format
        if 'anthropic.com' in CONFIG['api_url']:
            headers['x-api-key'] = CONFIG['api_key']
            headers['anthropic-version'] = '2023-06-01'
            del headers['Authorization']
            payload = {
                'model': CONFIG['model'],
                'max_tokens': 2000,
                'messages': payload['messages']
            }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(CONFIG['api_url'], data=data, headers=headers)
        
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        # Extract content based on API format
        if 'choices' in result:
            # OpenAI format
            content = result['choices'][0]['message']['content']
        elif 'content' in result:
            # Anthropic format
            content = result['content'][0]['text']
        else:
            content = str(result)
        
        return content
        
    except Exception as e:
        print(f"API Error: {e}")
        return None


def parse_llm_response(response_text):
    """Extract JSON from LLM response."""
    # Try to find JSON block in response
    try:
        # Look for ```json ... ``` block
        if '```json' in response_text:
            start = response_text.index('```json') + 7
            end = response_text.index('```', start)
            json_str = response_text[start:end].strip()
        elif '```' in response_text:
            start = response_text.index('```') + 3
            end = response_text.index('```', start)
            json_str = response_text[start:end].strip()
        else:
            # Try to parse the whole thing
            json_str = response_text.strip()
        
        return json.loads(json_str)
    except Exception as e:
        print(f"Warning: Could not parse JSON response: {e}")
        print("Raw response:")
        print(response_text)
        return None


def apply_suggestion(suggestion, moonraker_url):
    """Apply a suggestion via Moonraker API."""
    import urllib.request
    
    param = suggestion['parameter']
    value = suggestion['suggested']
    
    # Map parameter names to Klipper commands
    param_commands = {
        'speed_boost_k': f'SET_GCODE_VARIABLE MACRO=_AUTO_TEMP_CORE VARIABLE=speed_boost_k VALUE={value}',
        'speed_boost_threshold': f'SET_GCODE_VARIABLE MACRO=_AUTO_TEMP_CORE VARIABLE=speed_boost_threshold VALUE={value}',
        'ramp_rate_fall': f'SAVE_VARIABLE VARIABLE=material_ramp_fall VALUE={value}',
        'ramp_rate_rise': f'SAVE_VARIABLE VARIABLE=material_ramp_rise VALUE={value}',
        'max_boost_limit': f'SET_GCODE_VARIABLE MACRO=_AUTO_TEMP_CORE VARIABLE=max_boost_limit VALUE={value}',
        'flow_smoothing': f'SET_GCODE_VARIABLE MACRO=_AUTO_TEMP_CORE VARIABLE=flow_smoothing VALUE={value}',
    }
    
    if param not in param_commands:
        print(f"  Unknown parameter: {param}")
        return False
    
    gcode = param_commands[param]
    
    try:
        url = f"{moonraker_url}/printer/gcode/script?script={urllib.parse.quote(gcode)}"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"  ✓ Applied: {gcode}")
                return True
    except Exception as e:
        print(f"  ✗ Failed to apply {param}: {e}")
    
    return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Adaptive Flow print sessions')
    parser.add_argument('summary_file', nargs='?', help='Path to summary JSON (default: most recent)')
    parser.add_argument('--auto', action='store_true', help='Auto-apply safe suggestions')
    parser.add_argument('--raw', action='store_true', help='Show raw LLM response')
    args = parser.parse_args()
    
    # Find summary file
    if args.summary_file:
        summary_path = args.summary_file
    else:
        summary_path = find_latest_summary()
        if not summary_path:
            print(f"No print logs found in {CONFIG['log_dir']}")
            print("Run a print first to generate logs.")
            return 1
    
    print(f"Analyzing: {summary_path}")
    print("-" * 60)
    
    # Load data
    summary = load_summary(summary_path)
    csv_path = summary_path.replace('_summary.json', '.csv')
    csv_sample = load_csv_sample(csv_path)
    
    # Print quick stats
    print(f"Material: {summary.get('material', 'Unknown')}")
    print(f"Duration: {summary.get('duration_min', 0)} minutes")
    print(f"Samples: {summary.get('samples', 0)}")
    print(f"Avg Boost: {summary.get('avg_boost', 0)}°C, Max: {summary.get('max_boost', 0)}°C")
    print(f"Avg PWM: {summary.get('avg_pwm', 0):.1%}, Max: {summary.get('max_pwm', 0):.1%}")
    print("-" * 60)
    print("Sending to LLM for analysis...")
    
    # Call LLM
    response = call_llm_api(ANALYSIS_PROMPT, summary, csv_sample)
    
    if not response:
        return 1
    
    if args.raw:
        print("\nRaw LLM Response:")
        print(response)
        return 0
    
    # Parse response
    analysis = parse_llm_response(response)
    
    if not analysis:
        return 1
    
    # Display results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    print(f"\n📊 Assessment: {analysis.get('assessment', 'N/A')}")
    print(f"🎯 Quality Prediction: {analysis.get('print_quality_prediction', 'N/A').upper()}")
    
    issues = analysis.get('issues', [])
    if issues:
        print(f"\n⚠️  Issues Found ({len(issues)}):")
        for issue in issues:
            severity = issue.get('severity', 'unknown').upper()
            icon = '🔴' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else '🟢'
            print(f"  {icon} [{severity}] {issue.get('description', '')}")
    
    suggestions = analysis.get('suggestions', [])
    if suggestions:
        print(f"\n💡 Suggestions ({len(suggestions)}):")
        for i, sug in enumerate(suggestions, 1):
            safe = "✓ SAFE" if sug.get('safe_to_auto_apply') else "⚠ MANUAL"
            print(f"\n  {i}. {sug.get('parameter', 'unknown')}")
            print(f"     Current: {sug.get('current', '?')} → Suggested: {sug.get('suggested', '?')}")
            print(f"     Reason: {sug.get('reason', '')}")
            print(f"     [{safe}]")
    
    notes = analysis.get('notes', '')
    if notes:
        print(f"\n📝 Notes: {notes}")
    
    # Auto-apply if requested
    if args.auto and suggestions:
        print("\n" + "-" * 60)
        print("AUTO-APPLYING SAFE SUGGESTIONS...")
        
        import urllib.parse
        
        for sug in suggestions:
            if sug.get('safe_to_auto_apply'):
                apply_suggestion(sug, CONFIG['moonraker_url'])
        
        print("\nNote: Changes are temporary until Klipper restart.")
        print("To make permanent, edit auto_flow.cfg")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
