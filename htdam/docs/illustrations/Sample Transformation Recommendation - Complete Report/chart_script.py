
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Create 2x2 subplot layout
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Transform Options', 'COP Confidence', 
                    'Load Distrib', 'Use Case Matrix'),
    specs=[[{"type": "bar"}, {"type": "bar"}],
           [{"type": "pie"}, {"type": "table"}]],
    vertical_spacing=0.15,
    horizontal_spacing=0.12
)

# Panel 1: Transformation Options Comparison
options = ['Option 1<br>(Raw)', 'Option 2<br>(Derived)', 'Option 3<br>(Estimated)']
quality_scores = [0.84, 0.82, 0.50]
colors1 = ['#2E8B57', '#D2BA4C', '#DB4545']

fig.add_trace(go.Bar(
    x=options,
    y=quality_scores,
    marker_color=colors1,
    text=[f'{score:.2f}' for score in quality_scores],
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>Quality: %{y:.2f}<extra></extra>',
    showlegend=False
), row=1, col=1)

# Panel 2: COP Analysis Confidence
cop_labels = ['Opt1 WITH<br>Power', 'Opt1 W/O<br>Power', 'Opt2 Fault<br>Detect', 'Opt3 Est<br>Power']
cop_values = [0.95, 0, 0.90, 0.45]
colors2 = ['#2E8B57', '#9FA8B0', '#1FB8CD', '#DB4545']

fig.add_trace(go.Bar(
    x=cop_labels,
    y=cop_values,
    marker_color=colors2,
    text=['0.95', 'N/A', '0.90', '0.45'],
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>Confidence: %{text}<extra></extra>',
    showlegend=False
), row=1, col=2)

# Panel 3: Load Distribution Over Year
load_labels = ['IDLE<br>(<2°C)', 'PART<br>(2-4°C)', 'FULL<br>(>4°C)']
load_values = [80.9, 13.7, 5.4]
colors3 = ['#9FA8B0', '#1FB8CD', '#D2BA4C']

fig.add_trace(go.Pie(
    labels=load_labels,
    values=load_values,
    marker_colors=colors3,
    textinfo='label+percent',
    textposition='inside',
    hovertemplate='<b>%{label}</b><br>%{percent}<extra></extra>',
    showlegend=False
), row=2, col=1)

# Panel 4: Recommendation Matrix (as table)
use_cases = ['COP Analysis', 'Efficiency', 'Fault Detect', 'Monitoring', 'Health Check']
opt1_symbols = ['✓', '✓', '◐', '◐', '✗']
opt2_symbols = ['✗', '✗', '✓', '✓', '✓']
opt3_symbols = ['◐', '◐', '◐', '✓', '✓']

# Create cell colors for the table
cell_colors = []
for i in range(len(use_cases)):
    row_colors = ['#F5F5F5']  # Use case column (light gray)
    # Option 1
    if opt1_symbols[i] == '✓':
        row_colors.append('#A5D6A7')  # Light green
    elif opt1_symbols[i] == '◐':
        row_colors.append('#FFEB8A')  # Light yellow
    else:
        row_colors.append('#FFCDD2')  # Light red
    # Option 2
    if opt2_symbols[i] == '✓':
        row_colors.append('#A5D6A7')
    elif opt2_symbols[i] == '◐':
        row_colors.append('#FFEB8A')
    else:
        row_colors.append('#FFCDD2')
    # Option 3
    if opt3_symbols[i] == '✓':
        row_colors.append('#A5D6A7')
    elif opt3_symbols[i] == '◐':
        row_colors.append('#FFEB8A')
    else:
        row_colors.append('#FFCDD2')
    cell_colors.append(row_colors)

fig.add_trace(go.Table(
    header=dict(
        values=['<b>Use Case</b>', '<b>Opt1</b>', '<b>Opt2</b>', '<b>Opt3</b>'],
        fill_color='#E0E0E0',
        align='center',
        font=dict(size=11)
    ),
    cells=dict(
        values=[use_cases, opt1_symbols, opt2_symbols, opt3_symbols],
        fill_color=[['#F5F5F5']*len(use_cases)] + [[row[i] for row in cell_colors] for i in range(1, 4)],
        align='center',
        font=dict(size=12),
        height=25
    )
), row=2, col=2)

# Update axes
fig.update_yaxes(title_text='Quality Score', range=[0, 1.0], row=1, col=1)
fig.update_yaxes(title_text='Confidence', range=[0, 1.0], row=1, col=2)
fig.update_xaxes(title_text='', row=1, col=1)
fig.update_xaxes(title_text='', row=1, col=2)

# Update main layout
fig.update_layout(
    title_text='BarTech L22 MSSB Ch2: Transform Rec',
    showlegend=False
)

fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')

# Save as PNG and SVG
fig.write_image('chart.png')
fig.write_image('chart.svg', format='svg')
