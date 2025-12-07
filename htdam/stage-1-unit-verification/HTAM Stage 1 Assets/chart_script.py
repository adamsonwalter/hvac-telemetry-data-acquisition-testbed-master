
import plotly.graph_objects as go
import json

# Data
physics_ranges = [
    {"parameter": "CHWST", "unit": "°C", "validMin": 3, "validMax": 20, "typicalMin": 6, "typicalMax": 15, "constraint": "", "severity": "green"},
    {"parameter": "CHWRT", "unit": "°C", "validMin": 5, "validMax": 30, "typicalMin": 11, "typicalMax": 25, "constraint": "CHWRT≥CHWST", "severity": "green"},
    {"parameter": "CDWRT", "unit": "°C", "validMin": 15, "validMax": 45, "typicalMin": 18, "typicalMax": 40, "constraint": "CDWRT>CHWST", "severity": "green"},
    {"parameter": "CHW Flow", "unit": "m³/s", "validMin": 0, "validMax": 0.2, "typicalMin": "", "typicalMax": "", "constraint": "Never neg", "severity": "green"},
    {"parameter": "Power", "unit": "kW", "validMin": 0, "validMax": 1000, "typicalMin": "", "typicalMax": "", "constraint": "Never neg", "severity": "green"}
]

penalty_thresholds = [
    {"violation": "CHWST out [3,20]", "violationPercent": "< 5%", "penalty": "0.00", "action": "Continue", "severity": "green"},
    {"violation": "CHWST out [3,20]", "violationPercent": "5-10%", "penalty": "-0.02", "action": "Flag&Continue", "severity": "yellow"},
    {"violation": "CHWST out [3,20]", "violationPercent": "> 10%", "penalty": "-0.10", "action": "HALT", "severity": "red"},
    {"violation": "CHWRT<CHWST", "violationPercent": "0-1%", "penalty": "-0.05", "action": "Continue (drop)", "severity": "yellow"},
    {"violation": "CHWRT<CHWST", "violationPercent": "> 1%", "penalty": "-0.10", "action": "HALT", "severity": "red"},
    {"violation": "CDWRT≤CHWST", "violationPercent": "> 1%", "penalty": "-0.10", "action": "HALT (neg lift)", "severity": "red"},
    {"violation": "Flow < 0", "violationPercent": "Any", "penalty": "-0.10", "action": "HALT", "severity": "red"},
    {"violation": "Power < 0", "violationPercent": "Any", "penalty": "-0.10", "action": "HALT", "severity": "red"}
]

# Color mapping
color_map = {"green": "#A5D6A7", "yellow": "#FFEB8A", "red": "#FFCDD2"}

# Create figure with table
fig = go.Figure()

# Section 1: Physics Ranges
physics_headers = ["Parameter", "Unit", "Valid Min", "Valid Max", "Typical Min", "Typical Max", "Constraint"]
physics_cells = [
    [p["parameter"] for p in physics_ranges],
    [p["unit"] for p in physics_ranges],
    [str(p["validMin"]) for p in physics_ranges],
    [str(p["validMax"]) for p in physics_ranges],
    [str(p.get("typicalMin", "")) for p in physics_ranges],
    [str(p.get("typicalMax", "")) for p in physics_ranges],
    [p.get("constraint", "") for p in physics_ranges]
]
physics_colors = [[color_map[p["severity"]] for p in physics_ranges] for _ in physics_headers]

# Section 2: Penalty Thresholds
penalty_headers = ["Violation", "% Threshold", "Penalty", "Action"]
penalty_cells = [
    [p["violation"] for p in penalty_thresholds],
    [p["violationPercent"] for p in penalty_thresholds],
    [p["penalty"] for p in penalty_thresholds],
    [p["action"] for p in penalty_thresholds]
]
penalty_colors = [[color_map[p["severity"]] for p in penalty_thresholds] for _ in penalty_headers]

# Combine both sections with spacing
all_headers = physics_headers + [""] + penalty_headers
all_cells = []
max_rows = max(len(physics_ranges), len(penalty_thresholds))

# Build combined cells
for i, ph in enumerate(physics_headers):
    col_data = []
    for j in range(max_rows):
        if j < len(physics_ranges):
            col_data.append(physics_cells[i][j])
        else:
            col_data.append("")
    all_cells.append(col_data)

# Add spacer column
all_cells.append([""] * max_rows)

# Add penalty columns
for i, peh in enumerate(penalty_headers):
    col_data = []
    for j in range(max_rows):
        if j < len(penalty_thresholds):
            col_data.append(penalty_cells[i][j])
        else:
            col_data.append("")
    all_cells.append(col_data)

# Build colors
all_colors = []
for i in range(len(physics_headers)):
    col_colors = []
    for j in range(max_rows):
        if j < len(physics_ranges):
            col_colors.append(color_map[physics_ranges[j]["severity"]])
        else:
            col_colors.append("white")
    all_colors.append(col_colors)

# Spacer column
all_colors.append(["white"] * max_rows)

# Penalty colors
for i in range(len(penalty_headers)):
    col_colors = []
    for j in range(max_rows):
        if j < len(penalty_thresholds):
            col_colors.append(color_map[penalty_thresholds[j]["severity"]])
        else:
            col_colors.append("white")
    all_colors.append(col_colors)

# Create table
fig.add_trace(go.Table(
    header=dict(
        values=all_headers,
        fill_color='#13343B',
        font=dict(color='white', size=12),
        align='center',
        height=30
    ),
    cells=dict(
        values=all_cells,
        fill_color=all_colors,
        align='left',
        height=25,
        font=dict(size=11)
    )
))

fig.update_layout(
    title="HTDAM v2.0 Stage 1 Reference Chart"
)

# Save as PNG and SVG
fig.write_image("chart.png")
fig.write_image("chart.svg", format="svg")
