
import plotly.graph_objects as go
import numpy as np

# Data from the JSON
baseline = 0.88
transient_penalty = -0.02
resampling_penalty = -0.02
final_score = 0.84

# Create figure
fig = go.Figure()

# Create stacked horizontal bar showing quality progression
# We'll show the progression as segments
categories = ['After Sync', 'Transient', 'Resampling', 'Final Score']
values = [baseline, transient_penalty, resampling_penalty, 0]  # Last is placeholder
cumulative = [baseline, baseline + transient_penalty, baseline + transient_penalty + resampling_penalty, final_score]

# Add bars for each stage
# Green segment for good quality (0.84-1.0)
fig.add_trace(go.Bar(
    y=['Quality'],
    x=[final_score],
    orientation='h',
    marker=dict(color='#2E8B57'),
    name='Good (>0.84)',
    showlegend=False,
    hovertemplate='Final Score: 0.84<br>GOOD for COP<extra></extra>'
))

# Yellow segment for moderate quality (0.7-0.84)
# This would show the buffer between final and threshold
yellow_start = 0.7
yellow_width = 0.14
fig.add_trace(go.Bar(
    y=['Quality'],
    x=[yellow_width],
    orientation='h',
    marker=dict(color='#D2BA4C'),
    name='Moderate',
    showlegend=False,
    base=yellow_start,
    hovertemplate='Moderate: 0.70-0.84<extra></extra>'
))

# Red segment for poor quality (<0.7)
fig.add_trace(go.Bar(
    y=['Quality'],
    x=[yellow_start],
    orientation='h',
    marker=dict(color='#DB4545'),
    name='Poor (<0.7)',
    showlegend=False,
    base=0,
    hovertemplate='Poor: <0.70<extra></extra>'
))

# Add markers to show the progression
fig.add_trace(go.Scatter(
    x=[baseline],
    y=['Quality'],
    mode='markers+text',
    marker=dict(size=12, color='black', symbol='diamond'),
    text=['0.88'],
    textposition='top center',
    name='After Sync',
    hovertemplate='After Sync: 0.88<extra></extra>',
    showlegend=True
))

fig.add_trace(go.Scatter(
    x=[baseline + transient_penalty],
    y=['Quality'],
    mode='markers+text',
    marker=dict(size=12, color='black', symbol='diamond'),
    text=['0.86'],
    textposition='top center',
    name='Transient (-0.02)',
    hovertemplate='After Transient: 0.86<extra></extra>',
    showlegend=True
))

fig.add_trace(go.Scatter(
    x=[final_score],
    y=['Quality'],
    mode='markers+text',
    marker=dict(size=14, color='white', symbol='star', line=dict(color='black', width=2)),
    text=['0.84'],
    textposition='top center',
    name='Final (-0.02)',
    hovertemplate='Final Score: 0.84 (GOOD)<extra></extra>',
    showlegend=True
))

# Update layout
fig.update_layout(
    title='Signal Quality Score: GOOD (0.84)',
    xaxis_title='Quality Score',
    yaxis_title='',
    xaxis=dict(range=[0, 1], tickformat='.2f'),
    barmode='overlay',
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.05,
        xanchor='center',
        x=0.5
    )
)

fig.update_traces(cliponaxis=False)

# Save as PNG and SVG
fig.write_image('chart.png')
fig.write_image('chart.svg', format='svg')
