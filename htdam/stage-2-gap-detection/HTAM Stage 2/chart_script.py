
import plotly.graph_objects as go
import pandas as pd

# Define color mapping based on severity
color_map = {
    'green': '#B3E5EC',  # Light cyan for benign
    'yellow': '#FFEB8A',  # Light yellow for minor
    'orange': '#FFCDD2',  # Light red for uncertain
    'red': '#FFCDD2'      # Light red for anomaly/required
}

# Build the table data
header_values = ['Category', 'Key', 'Details', 'Notes']
cell_values = [[], [], [], []]

# Section 1: Gap Classification Thresholds
cell_values[0].append('<b>GAP CLASSIFICATION</b>')
cell_values[1].append('')
cell_values[2].append('')
cell_values[3].append('')

classifications = [
    ('NORMAL', '≤ 1.5 × T_nom', '≤ 1,350 s', 'green'),
    ('MINOR_GAP', '1.5–4.0 × T_nom', '1,350–3,600 s', 'yellow'),
    ('MAJOR_GAP', '> 4.0 × T_nom', '> 3,600 s', 'orange')
]

for cls, rng, ex, sev in classifications:
    cell_values[0].append('Threshold')
    cell_values[1].append(cls)
    cell_values[2].append(rng)
    cell_values[3].append(ex)

# Section 2: Gap Semantics
cell_values[0].append('<b>GAP SEMANTICS</b>')
cell_values[1].append('')
cell_values[2].append('')
cell_values[3].append('')

semantics = [
    ('COV_CONSTANT', '±0.5% change', 'Penalty: 0.0', 'green'),
    ('COV_MINOR', '0.5–2% drift', 'Penalty: -0.02', 'yellow'),
    ('SENSOR_ANOMALY', '>5°C jump', 'Penalty: -0.05', 'red')
]

for sem, trig, pen, sev in semantics:
    cell_values[0].append('Semantic')
    cell_values[1].append(sem)
    cell_values[2].append(trig)
    cell_values[3].append(pen)

# Section 3: Penalty Structure
cell_values[0].append('<b>PENALTY STRUCT</b>')
cell_values[1].append('')
cell_values[2].append('')
cell_values[3].append('')

penalties = [
    ('COV_CONSTANT', '0.0 per gap', 'Benign stable', 'green'),
    ('COV_MINOR', '-0.02 per gap', 'Slow change', 'yellow'),
    ('SENSOR_ANOMALY', '-0.05 per gap', 'Suspicious', 'red'),
    ('EXCLUDED', '-0.03 per gap', 'Data loss', 'orange')
]

for ptype, pval, reason, sev in penalties:
    cell_values[0].append('Penalty')
    cell_values[1].append(ptype)
    cell_values[2].append(pval)
    cell_values[3].append(reason)

# Section 4: Exclusion Window Criteria
cell_values[0].append('<b>EXCLUSION WINDOW</b>')
cell_values[1].append('')
cell_values[2].append('')
cell_values[3].append('')

criteria = [
    ('Multi-stream', '≥2 streams', 'REQUIRED', 'red'),
    ('Duration', '≥8 hrs gap', 'REQUIRED', 'red'),
    ('Approval', 'User review', 'REQUIRED', 'red'),
    ('Documentation', 'Reason log', 'RECOMMENDED', 'yellow')
]

for crit, req, stat, sev in criteria:
    cell_values[0].append('Criterion')
    cell_values[1].append(crit)
    cell_values[2].append(req)
    cell_values[3].append(stat)

# Create fill colors based on severity
fill_colors = []
row_colors = {
    0: '#E0E0E0',  # Header rows (gray)
    # Classify based on content
}

# Build fill color list
current_row = 0
fill_colors.append('#E0E0E0')  # Section 1 header

# Section 1: Classifications
for _, _, _, sev in classifications:
    fill_colors.append(color_map[sev])

fill_colors.append('#E0E0E0')  # Section 2 header

# Section 2: Semantics
for _, _, _, sev in semantics:
    fill_colors.append(color_map[sev])

fill_colors.append('#E0E0E0')  # Section 3 header

# Section 3: Penalties
for _, _, _, sev in penalties:
    fill_colors.append(color_map[sev])

fill_colors.append('#E0E0E0')  # Section 4 header

# Section 4: Criteria
for _, _, _, sev in criteria:
    fill_colors.append(color_map[sev])

# Transpose for plotly table format
fill_color_matrix = [[c] * 4 for c in fill_colors]

fig = go.Figure(data=[go.Table(
    header=dict(
        values=['<b>' + h + '</b>' for h in header_values],
        fill_color='#13343B',
        font=dict(color='white', size=12),
        align='left',
        height=30
    ),
    cells=dict(
        values=cell_values,
        fill_color=[fill_colors] * 4,
        align='left',
        font=dict(size=11),
        height=25
    )
)])

fig.update_layout(
    title='HTDAM v2 Stage 2 Gap Detection'
)

# Save as PNG and SVG
fig.write_image('htdam_reference.png')
fig.write_image('htdam_reference.svg', format='svg')
