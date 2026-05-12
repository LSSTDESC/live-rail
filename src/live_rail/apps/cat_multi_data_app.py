import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import numpy as np

APP_NAME = 'Data Explorer'


def build_multi_data_app(cat_data, pz_data):

    eval_grid = np.linspace(0, 3, 301)
    true_redshifts = cat_data['redshift']
    n_rows = len(true_redshifts)    
    pz_estimates = {key: val.ancil['zmode'] for key, val in pz_data.items()}
    pdfs = {key: val.pdf(eval_grid) for key, val in pz_data.items()}
    keys = list(pz_data.keys())
    
    # Initialize the Dash app
    app = dash.Dash(__name__)

    # Define the layout
    app.layout = html.Div([
        html.H1("P(z) interactive plotter", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 30}),
    
        html.Div([
            html.Div([
                html.Label("Select Row:", style={'fontWeight': 'bold', 'fontSize': 16}),
                dcc.Slider(
                    id='row-slider',
                    min=0,
                    max=n_rows - 1,
                    value=0,
                    marks={i: str(i) for i in range(0, n_rows, max(1, n_rows // 10))},
                    step=1,
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'width': '80%', 'margin': 'auto', 'marginBottom': 30}),        
            html.Div([
                html.Button(
                    '◀ Previous',
                    id='prev-button',
                    n_clicks=0,
                    style={'marginRight': 10, 'padding': '10px 20px', 'fontSize': 14}
                ),
                html.Button(
                    'Next ▶',
                    id='next-button',
                    n_clicks=0,
                    style={'padding': '10px 20px', 'fontSize': 14}
                ),
                ], style={'textAlign': 'center', 'marginBottom': 20}
            ),
            html.Div(
                id='row-info',
                style={'textAlign': 'center', 'fontSize': 16, 'marginBottom': 20}
            ),
            dcc.Graph(id='row-plot', style={'height': '500px'}),
            html.Div([
                html.H3("Statistics:", style={'color': '#2c3e50'}),
                html.Div(id='statistics', style={'fontSize': 14, 'lineHeight': 1.8})
            ], style={
                'width': '80%', 'margin': 'auto', 'marginTop': 30, 'padding': 20, 
                'backgroundColor': '#f8f9fa', 'borderRadius': 10
                }
            ),
            ])
        ], style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}
    )

    # Callback for navigation buttons
    @app.callback(
        Output('row-slider', 'value'),
        Input('prev-button', 'n_clicks'),
        Input('next-button', 'n_clicks'),
        State('row-slider', 'value')
    )
    def update_slider(prev_clicks, next_clicks, current_value):
        ctx = dash.callback_context
    
        if not ctx.triggered:
            return current_value
    
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
        if button_id == 'prev-button' and current_value > 0:
            return current_value - 1
        elif button_id == 'next-button' and current_value < n_rows - 1:
            return current_value + 1
    
        return current_value

    # Callback for updating the plot and statistics
    @app.callback(
        [Output('row-plot', 'figure'),
        Output('row-info', 'children'),
        Output('statistics', 'children')],
        Input('row-slider', 'value')
    )
    def update_plot(selected_row):
        # Get the selected row data

        x_values = eval_grid
        
        # Create the plot
        fig = go.Figure()

        for key in keys:
            pdf = pdfs[key][selected_row]
            fig.add_trace(go.Scatter(
                x=x_values,
                y=pdf,
                mode='lines+markers',
                name=key,
                marker=dict(size=4)
            ))

        fig.add_vline(
            x=true_redshifts[selected_row],
            line_width=2,
            line_dash="dash",
            line_color="red"
        )
        
        fig.update_layout(
            title=f'Plot of Object {selected_row}',
            xaxis_title='z',
            yaxis_title='p(z)',
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
    
        # Row info
        row_info = html.Div([
            html.Span(f"Displaying Row {selected_row} of {n_rows - 1}", 
                    style={'fontWeight': 'bold', 'color': '#2c3e50'})
        ])
    
        # Calculate statistics
        stats = html.Div([])
    
        return fig, row_info, stats

    return app
