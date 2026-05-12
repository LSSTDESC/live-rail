from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import numpy as np

from rail.utils import catalog_utils


APP_NAME = 'PZ Pdf Family Explorer'

def build_cat_pdf_cloud_app(wrapper):

    var_names = list(catalog_utils.get_active_tag().band_name_dict().values())

    assert wrapper.n_obj > 1
    n_samples = wrapper.n_obj
    
    # Initialize the Dash app
    app = Dash(APP_NAME)

    slider_div_list = [
        html.Div([
            html.Label('error_scale:'),
            dcc.Slider(
                id='error_scale', min=0, max=0.2, step=0.005, value=0.01, 
                marks={i: str(i) for i in np.linspace(0, 0.2, 5)},
                tooltip={"placement": "bottom", "always_visible": True},
                updatemode='drag'
            ) # Add this line         
        ], style={'margin': '10px'})
    ]

    for name_ in var_names:
        slider_div_list.append(
            html.Div([
                html.Label(f'{name_}:'),
                dcc.Slider(id=name_, min=22, max=25, step=0.02, value=24.0, 
                        marks={i: str(i) for i in range(22, 25)},
                        tooltip={"placement": "bottom", "always_visible": True},
                        updatemode='drag') # Add this line         
            ], style={'margin': '10px'})
        )
        
    
        
    # Define the layout
    app.layout = html.Div([
        html.H1(APP_NAME),    
        html.Div(
            slider_div_list, 
            style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'}
        ),    
        html.Div([
            dcc.Graph(id='pdf-plot')
        ], style={'width': '48%', 'display': 'inline-block'}),
    ])

    sliders = {name_ : Input(name_, 'drag_value') for name_ in var_names}
    sliders['error_scale'] = Input('error_scale', 'drag_value')
    
    # Callback to update the plot
    @app.callback(
        Output('pdf-plot', 'figure'),
        sliders,
    )
    def update_plot(**kwargs):    
        dd = {}
        error_scale = kwargs.get('error_scale')
        for name_ in var_names:
            dd[name_] = np.random.normal(
                loc=kwargs.get(name_),
                scale=error_scale,
                size=n_samples,
            )
            dd[f"{name_}_err"] = np.array([error_scale]*n_samples)

        data = wrapper(dd)
        
        xvals = np.linspace(0., 3., 301)
        yvals = data.pdf(xvals)
    
        fig = go.Figure()
        for i, y_ in enumerate(yvals):
            fig.add_trace(go.Scatter(x=xvals, y=y_, mode='lines', name=f"pdf {i}"))
        fig.update_layout(
            title='PDF',
            xaxis_title='z',
            yaxis_title='p(z)',
            hovermode='x unified'
        )
    
        return fig


    return app
