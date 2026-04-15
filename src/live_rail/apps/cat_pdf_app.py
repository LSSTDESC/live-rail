from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import numpy as np

from rail.utils import catalog_utils

def build_cat_pdf_app(app_name, wrapper):

    var_names = list(catalog_utils.get_active_tag().band_name_dict().values())

    assert wrapper.n_obj == 1
    
    # Initialize the Dash app
    app = Dash(__name__)

    slider_div_list = []

    for name_ in var_names:
        slider_div_list.append(
            html.Div([
                html.Label(f'{name_}:'),
                dcc.Slider(id=name_, min=20, max=25, step=0.1, value=22.0, 
                        marks={i: str(i) for i in range(20, 26)},
                        tooltip={"placement": "bottom", "always_visible": True},
                        updatemode='drag') # Add this line         
            ], style={'margin': '10px'})
        )

    # Define the layout
    app.layout = html.Div([
        html.H1("PDF Explorer"),    
        html.Div(
            slider_div_list, 
            style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'}
        ),    
        html.Div([
            dcc.Graph(id='pdf-plot')
        ], style={'width': '48%', 'display': 'inline-block'}),
    ])

    # Callback to update the plot
    @app.callback(
        Output('pdf-plot', 'figure'),
        {name_ : Input(name_, 'drag_value') for name_ in var_names}
    )
    def update_plot(**kwargs):    
        dd = {}
        for name_ in var_names:
            dd[name_] = np.array([kwargs.get(name_)])
            dd[f"{name_}_err"] = np.array([0.01])
        data = wrapper(dd)
    
        xvals = np.linspace(0., 3., 301)

        yvals = np.squeeze(data.pdf(xvals))
    
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xvals, y=yvals, mode='lines'))
        fig.update_layout(
            title='PDF',
            xaxis_title='z',
            yaxis_title='p(z)',
            hovermode='x unified'
        )
    
        return fig


    return app
