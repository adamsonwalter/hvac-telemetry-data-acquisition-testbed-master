
import plotly.graph_objects as go
import pandas as pd

# Data for materiality penalties
categories = ['Baseline', 'Unit Verif', 'Gap Resoltn', 'Sync Precisn', 'Final Score']
values = [1.00, 1.00, 0.93, 0.88, 0.88]
cumulative_values = [1.00, -0.00, -0.07, -0.05, 0.88]

# Create waterfall-style horizontal bar chart
fig = go.Figure()

# Add bars for each penalty stage
colors = ['#2E8B57', '#1FB8CD', '#D2BA4C', '#DB4545', '#2E8B57']

for i, (cat, val) in enumerate(zip(categories, values)):
    if i == 0:  # Baseline
        fig.add_trace(go.Bar(
            y=[cat],
            x=[val],
            orientation='h',
            marker=dict(color=colors[i]),
            text=[f'{val:.2f}'],
            textposition='inside',
            name=cat,
            showlegend=False
        ))
    elif i == len(categories) - 1:  # Final score
        fig.add_trace(go.Bar(
            y=[cat],
            x=[val],
            orientation='h',
            marker=dict(color=colors[i] if val >= 0.85 else '#DB4545'),
            text=[f'{val:.2f} (GOOD)'],
            textposition='inside',
            name=cat,
            showlegend=False
        ))
    else:  # Intermediate penalties
        fig.add_trace(go.Bar(
            y=[cat],
            x=[val],
            orientation='h',
            marker=dict(color=colors[i]),
            text=[f'{val:.2f}'],
            textposition='inside',
            name=cat,
            showlegend=False
        ))

fig.update_layout(
    title='Material Penalty Score',
    xaxis_title='Conf Score',
    yaxis_title='',
    barmode='overlay',
    xaxis=dict(range=[0, 1.05]),
    yaxis=dict(categoryorder='array', categoryarray=categories[::-1])
)

fig.update_traces(cliponaxis=False)

# Save as PNG and SVG
fig.write_image('chart.png')
fig.write_image('chart.svg', format='svg')
