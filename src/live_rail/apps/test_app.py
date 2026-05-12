
import asyncio
import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objs as go
import numpy as np
from typing import Optional
import plotly.express as px

from pathlib import Path
from rail.utils import catalog_utils
from rail_svc import db, local_sync

from live_rail.wrappers.object_wrapper import CatalogWrapper
from live_rail.wrappers.rail_svc_wrapper import RailSvcCatalogWrapper


class AstronomicalDataVisualizer:
    def __init__(self, catalog_wrapper):
        """
        Initialize the visualizer with a CatalogWrapper instance.
        
        Parameters
        ----------
        catalog_wrapper : CatalogWrapper
            The catalog containing astronomical objects
        """
        self.catalog = catalog_wrapper
        self.app = dash.Dash(__name__)
        self.current_object_idx = 0
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Create the 4-pane layout for the dashboard."""
        self.app.layout = html.Div([
            html.H1("Redshift explorer", 
                   style={'textAlign': 'center', 'marginBottom': 30}),
            
            # Main container with grid layout
            html.Div([
                # Pane 1: Object Selection (top)
                html.Div([
                    html.H3("Object Selection"),
                    self._create_selection_pane()
                ],  style={
                    'width': '100%',
                    'height': '10vh',
                    'padding': '10px',
                    'boxSizing': 'border-box'
                }),
                
                html.Div([

                    # Pane 2: Spectrum (left mid)
                    html.Div([
                        html.H3("Photometric Spectrum"),
                        dcc.Graph(id='spectrum-plot')
                    ], style={
                        'width': '50%',
                        'height': '30vh',
                        'border': '2px solid #f57c00',
                        'padding': '10px',
                        'boxSizing': 'border-box',
                        'display': 'inline-block',
                        'verticalAlign': 'top'
                    }),
                    
                    # Pane 3: Color-Color Diagram (right mid)
                    html.Div([
                        html.H3("Color-Color Relations"),
                        self._create_color_controls(),
                        dcc.Graph(id='color-color-plot')
                    ], style={
                        'width': '50%',
                        'height': '30vh',
                        'border': '2px solid #7b1fa2',
                        'padding': '10px',
                        'boxSizing': 'border-box',
                        'display': 'inline-block',
                        'verticalAlign': 'top'
                    }),

                ],  style={}),  # Remove whitespace between inline-block elements
                
                # Pane 4: Redshift Estimates (bottom)
                html.Div([
                    html.H3("Redshift Estimates"),
                    self._create_redshift_controls(),
                    dcc.Graph(id='redshift-plot')
                ], style={
                    'width': '100%',
                    'height': '50vh',
                    'border': '2px solid #388e3c',
                    'padding': '10px',
                    'boxSizing': 'border-box'
                }),

                html.Div([], style={
                    'width': '100%',
                    'height': '10vh',
                    'border': '2px solid #388e3c',
                    'padding': '10px',
                    'boxSizing': 'border-box'
                }),

                    
            ], style={
                'margin': '0',
                'padding': '0',
                'height': '100vh',
                'overflow': 'hidden'                
            }),
            
            # Hidden div to store current object data
            html.Div(id='current-object-idx', style={'display': 'none'}, 
                    children=str(self.current_object_idx))
        ])
    
    def _create_selection_pane(self):
        """Create the object selection controls."""
        n_objects = self.catalog.get_nobjects()
        
        # Get initial object to determine number of bands
        obj = self.catalog.get_object(0)
        band_names = obj.get_band_names()
        
        selection_controls = [
            html.Label("Select Object:"),
            dcc.Slider(
                id='object-slider',
                min=0,
                max=n_objects - 1,
                value=0,
                marks={i: str(i) for i in range(0, n_objects, max(1, n_objects // 10))},
                step=1,
                tooltip={"placement": "bottom", "always_visible": True}
            ),
        ]
        
        return html.Div(selection_controls)
    
    def _create_color_controls(self):
        """Create controls for color-color diagram."""
        return html.Div([
            html.Label("X-axis Color:"),
            dcc.Dropdown(id='color-x-dropdown', style={'marginBottom': 10}),
            html.Label("Y-axis Color:"),
            dcc.Dropdown(id='color-y-dropdown', style={'marginBottom': 10}),
        ])
    
    def _create_redshift_controls(self):
        """Create controls for redshift display."""
        return html.Div([
            html.Label("Select Estimates to Display:"),
            dcc.Checklist(
                id='redshift-estimate-checklist',
                inline=False,
                style={'marginBottom': 10}
            ),
            html.Label("Redshift Grid Range:"),
            dcc.RangeSlider(
                id='redshift-range',
                min=0,
                max=5,
                value=[0, 3],
                step=0.1,
                marks={i: str(i) for i in range(6)},
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ])
    
    def setup_callbacks(self):
        """Setup all interactive callbacks."""
        
        @self.app.callback(
            Output('current-object-idx', 'children'),
            Input('object-slider', 'value')
        )
        def update_object_idx(idx):
            return str(idx)
        
        @self.app.callback(
            [Output('color-x-dropdown', 'options'),
             Output('color-y-dropdown', 'options'),
             Output('color-x-dropdown', 'value'),
             Output('color-y-dropdown', 'value')],
            Input('current-object-idx', 'children')
        )
        def update_color_dropdowns(idx_str):
            idx = int(idx_str)
            obj = self.catalog.get_object(idx)
            colors = obj.get_colors()
            color_names = list(colors.keys())
            
            options = [{'label': name, 'value': name} for name in color_names]
            default_x = color_names[0] if len(color_names) > 0 else None
            default_y = color_names[1] if len(color_names) > 1 else default_x
            
            return options, options, default_x, default_y
        
        @self.app.callback(
            [Output('redshift-estimate-checklist', 'options'),
             Output('redshift-estimate-checklist', 'value')],
            Input('current-object-idx', 'children')
        )
        def update_redshift_checklist(idx_str):
            idx = int(idx_str)
            obj = self.catalog.get_object(idx)
            estimate_names = obj.get_estimate_names()
            
            options = [{'label': name, 'value': name} for name in estimate_names]
            # By default, select all estimates
            values = estimate_names
            
            return options, values
        
        @self.app.callback(
            Output('spectrum-plot', 'figure'),
            [Input('current-object-idx', 'children')]
        )
        def update_spectrum(idx_str):
            idx = int(idx_str)
            obj = self.catalog.get_object(idx)
            
            spectrum_data = obj.get_spectrum()
            band_names = obj.get_band_names()
            wavelengths = spectrum_data['midpoints']  # or appropriate key
            mags = spectrum_data['mags'].copy()
            mag_errors = spectrum_data['mag_errors']
            
            fig = go.Figure()
            
            # Add error bars
            fig.add_trace(go.Scatter(
                x=wavelengths,
                y=mags,
                error_y=dict(type='data', array=mag_errors),
                mode='markers',
                name='Photometry',
                marker=dict(size=10),
                line=dict(width=2),
            ))
            
            fig.update_layout(
                xaxis_title='Wavelength (Å)',
                yaxis_title='Magnitude (AB)',
                yaxis_autorange='reversed',  # Magnitudes increase downward
                hovermode='closest',
                template='plotly_white',
                height=400
            )

            fig.update_xaxes(range=[3000, 10000])                        
            #fig.update_yaxes(range=[30, 15])            
                        
            return fig
        
        @self.app.callback(
            Output('color-color-plot', 'figure'),
            [Input('current-object-idx', 'children'),
             Input('color-x-dropdown', 'value'),
             Input('color-y-dropdown', 'value'),
            ]
        )
        def update_color_color(idx_str, x_color, y_color):
            idx = int(idx_str)
            obj = self.catalog.get_object(idx)
            
            mags = obj.get_magnitudes().copy()
            mag_errors = obj.get_magnitude_errors()
            band_names = obj.get_band_names()
                        
            colors = {}
            n = len(band_names)
            for i in range(n-1):
                color_name = f"{band_names[i]} - {band_names[i+1]}"
                colors[color_name] = (
                    mags[i] - mags[i+1],
                    np.sqrt(mag_errors[i]**2 + mag_errors[i+1]**2)
                )
            
            if not x_color or not y_color:
                return go.Figure()
            
            x_val, x_err = colors.get(x_color, (0, 0))
            y_val, y_err = colors.get(y_color, (0, 0))
            
            fig = go.Figure()
            
            # Add the selected object
            fig.add_trace(go.Scatter(
                x=[x_val],
                y=[y_val],
                error_x=dict(type='data', array=[x_err]),
                error_y=dict(type='data', array=[y_err]),
                mode='markers',
                marker=dict(size=15, color='red'),
                name='Selected Object',
            ))

            fig.update_xaxes(range=[-3, 3])
            fig.update_yaxes(range=[-3, 3])            
            
            # Optionally: Add all objects from catalog for context
            # This would require iterating through catalog
            
            fig.update_layout(
                xaxis_title=x_color,
                yaxis_title=y_color,
                hovermode='closest',
                template='plotly_white',
                height=400
            )
            
            return fig
        
        @self.app.callback(
            Output('redshift-plot', 'figure'),
            [Input('current-object-idx', 'children'),
             Input('redshift-estimate-checklist', 'value'),
             Input('redshift-range', 'value')]
        )
        def update_redshift_plot(idx_str, selected_estimates, z_range):
            idx = int(idx_str)
            obj = self.catalog.get_object(idx)
            
            if not selected_estimates:
                return go.Figure()
            
            # Create redshift grid
            z_grid = np.linspace(z_range[0], z_range[1], 500)
            
            # Get PDFs for selected estimates
            pdfs = obj.get_redshifts_pdfs(z_grid)
            modes = obj.get_redshift_modes()
            
            fig = go.Figure()
            
            # Plot each selected estimate
            for estimate_name in selected_estimates:
                if estimate_name in pdfs:
                    pdf = pdfs[estimate_name]
                    mode_val = modes.get(estimate_name)
                    
                    # Add PDF curve
                    fig.add_trace(go.Scatter(
                        x=z_grid,
                        y=pdf,
                        mode='lines',
                        name=estimate_name,
                        line=dict(width=2)
                    ))
                    
                    # Add mode marker
                    if mode_val is not None:
                        mode_idx = np.argmin(np.abs(z_grid - mode_val))
                        fig.add_trace(go.Scatter(
                            x=[mode_val],
                            y=[pdf[mode_idx]],
                            mode='markers',
                            marker=dict(size=10, symbol='diamond'),
                            name=f'{estimate_name} mode',
                            showlegend=False
                        ))
            
            # Add true redshift if available
            true_z = obj.get_true_redshift()
            if true_z is not None and z_range[0] <= true_z[0] <= z_range[1]:
                fig.add_vline(
                    x=true_z[0],
                    line=dict(color='black', width=2, dash='dash'),
                    annotation_text='True z',
                    annotation_position='top'
                )
            
            fig.update_layout(
                xaxis_title='Redshift',
                yaxis_title='Probability Density',
                hovermode='x unified',
                template='plotly_white',
                height=400,
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            
            return fig
    
    def run(self, debug=True, port=8050):
        """Run the Dash application."""
        self.app.run(debug=debug, port=port)


    @classmethod
    def main(cls):

        try:
            asyncio.run(db.close_db())
        except:
            pass
        db.init_db()
        catalog_utils.load_yaml('default_catalogs.yaml')
        wrapper = RailSvcCatalogWrapper(1)
        viz = AstronomicalDataVisualizer(wrapper)
        viz.run(debug=False, port=8051)

        
if __name__ == '__main__':

    AstronomicalDataVisualizer.main()
