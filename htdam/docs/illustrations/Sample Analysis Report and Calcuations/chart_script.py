
import plotly.graph_objects as go

# Data from the provided JSON
streams = ['CDWRT', 'CHWRT', 'CHWST']  # Reversed order for better visualization (highest quality on top)
recoverable = [89, 87, 72]
anomaly = [9, 10, 17]
excluded = [2, 3, 11]

# Colors following the instructions with more vivid yellow
color_recoverable = '#2E8B57'  # Sea green
color_anomaly = '#FFEB8A'      # Light yellow (more vivid)
color_excluded = '#DB4545'     # Bright red

# Create the figure
fig = go.Figure()

# Add bars for each category (stacked)
fig.add_trace(go.Bar(
    name='Recoverable',
    y=streams,
    x=recoverable,
    orientation='h',
    marker=dict(color=color_recoverable),
    text=[f'<b>{v}%</b>' for v in recoverable],
    textposition='inside',
    textfont=dict(size=16, color='white'),
    hovertemplate='%{y}<br>Recoverable: %{x}%<extra></extra>'
))

fig.add_trace(go.Bar(
    name='Anomaly',
    y=streams,
    x=anomaly,
    orientation='h',
    marker=dict(color=color_anomaly),
    text=[f'<b>{v}%</b>' for v in anomaly],
    textposition='inside',
    textfont=dict(size=16, color='#13343B'),
    hovertemplate='%{y}<br>Anomaly: %{x}%<extra></extra>'
))

fig.add_trace(go.Bar(
    name='Excluded',
    y=streams,
    x=excluded,
    orientation='h',
    marker=dict(color=color_excluded),
    text=[f'<b>{v}%</b>' for v in excluded],
    textposition='inside',
    textfont=dict(size=16, color='white'),
    hovertemplate='%{y}<br>Excluded: %{x}%<extra></extra>'
))

# Update layout with proper title and subtitle
fig.update_layout(
    title='BarTech L22 Chiller 2: Quality',
    barmode='stack',
    xaxis_title='Percentage (%)',
    yaxis_title='Stream',
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.05,
        xanchor='center',
        x=0.5
    ),
    uniformtext_minsize=14,
    uniformtext_mode='hide'
)

# Update axes
fig.update_xaxes(range=[0, 100])
fig.update_traces(cliponaxis=False)

# Save the chart
fig.write_image('chart.png')
fig.write_image('chart.svg', format='svg')
