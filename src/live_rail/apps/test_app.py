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


class SingleCatalogRedshiftVisualizer:
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
        self.n_objects = self.catalog.get_nobjects()
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Create the 4-pane layout for the dashboard."""
        self.app.layout = html.Div([
                html.H1("Redshift Explorer", 
                       style={
                               'textAlign': 'center', 
                               'margin': '0',
                               'padding': '20px 0',
                               'backgroundColor': '#f5f5f5',
                               'borderBottom': '2px solid #ddd'
                       }),
                
                # Main container with flex layout
                html.Div([
                        # Pane 1: Object Selection (top)
                        html.Div([
                                html.H3("Object Selection", style={'margin': '0 0 15px 0'}),
                                html.Div([
                                        # Back button
                                        html.Button(
                                                '← Back',
                                                id='back-button',
                                                n_clicks=0,
                                                disabled=True,  # Initially disabled
                                                style={
                                                        'padding': '10px 20px',
                                                        'fontSize': '14px',
                                                        'cursor': 'pointer',
                                                        'backgroundColor': '#2196F3',
                                                        'color': 'white',
                                                        'border': 'none',
                                                        'borderRadius': '4px',
                                                        'marginRight': '15px',
                                                        'minWidth': '100px'
                                                }
                                        ),
                                        # Selection controls container
                                        html.Div([
                                                html.Div([
                                                        html.Label(
                                                                "Select Object:",
                                                                style={
                                                                        'fontWeight': 'bold',
                                                                        'marginBottom': '8px',
                                                                        'display': 'block',
                                                                        'fontSize': '14px'
                                                                }
                                                        ),
                                                        html.Div([
                                                                dcc.Slider(
                                                                        id='object-slider',
                                                                        min=0,
                                                                        max=self.n_objects - 1,
                                                                        value=0,
                                                                        marks={i: str(i) for i in range(0, self.n_objects, max(1, self.n_objects // 10))},
                                                                        step=1,
                                                                        tooltip={"placement": "bottom", "always_visible": True},
                                                                        updatemode='drag'
                                                                ),
                                                        ], style={'marginBottom': '10px'}),
                                                        html.Div([
                                                                html.Span("Object ", style={'fontSize': '14px'}),
                                                                html.Span(
                                                                        id='object-counter',
                                                                        children=f"1 of {self.n_objects}",
                                                                        style={
                                                                                'fontWeight': 'bold',
                                                                                'fontSize': '14px',
                                                                                'color': '#2196F3'
                                                                        }
                                                                )
                                                        ], style={'textAlign': 'center'})
                                                ], style={'width': '100%'})
                                        ], style={
                                                'flex': '1',
                                                'display': 'flex',
                                                'alignItems': 'center',
                                                'justifyContent': 'center',
                                                'minWidth': '300px',
                                                'maxWidth': '600px'
                                        }),
                                        # Next button
                                        html.Button(
                                                'Next →',
                                                id='next-button',
                                                n_clicks=0,
                                                style={
                                                        'padding': '10px 20px',
                                                        'fontSize': '14px',
                                                        'cursor': 'pointer',
                                                        'backgroundColor': '#2196F3',
                                                        'color': 'white',
                                                        'border': 'none',
                                                        'borderRadius': '4px',
                                                        'marginLeft': '15px',
                                                        'minWidth': '100px'
                                                }
                                        )
                                ], style={
                                        'display': 'flex',
                                        'alignItems': 'center',
                                        'justifyContent': 'center',
                                        'gap': '10px',
                                        'width': '100%'
                                })
                        ], style={
                                'padding': '20px',
                                'backgroundColor': '#fafafa',
                                'borderBottom': '1px solid #ddd'
                        }),
                        
                        # Middle row: Spectrum and Color-Color side by side
                        html.Div([
                                # Pane 2: Spectrum (left)
                                html.Div([
                                        html.H3("Photometric Spectrum", style={'margin': '0 0 10px 0'}),
                                        dcc.Graph(
                                                id='spectrum-plot',
                                                style={'height': '100%'},
                                                config={'responsive': True}
                                        )
                                ], style={
                                        'flex': '1',
                                        'minWidth': '400px',
                                        'border': '2px solid #f57c00',
                                        'padding': '15px',
                                        'boxSizing': 'border-box',
                                        'display': 'flex',
                                        'flexDirection': 'column'
                                }),
                                
                                # Pane 3: Color-Color Diagram (right)
                                html.Div([
                                        html.H3("Color-Color Relations", style={'margin': '0 0 10px 0'}),
                                        html.Div([
                                                # Controls on the left (20%)
                                                html.Div([
                                                        self._create_color_controls()
                                                ], style={
                                                        'width': '20%',
                                                        'minWidth': '150px',
                                                        'paddingRight': '10px',
                                                        'boxSizing': 'border-box',
                                                        'overflowY': 'auto'
                                                }),
                                                # Plot on the right (80%)
                                                html.Div([
                                                        dcc.Graph(
                                                                id='color-color-plot',
                                                                style={'height': '100%'},
                                                                config={'responsive': True}
                                                        )
                                                ], style={
                                                        'width': '80%',
                                                        'boxSizing': 'border-box'
                                                })
                                        ], style={
                                                'display': 'flex',
                                                'height': 'calc(100% - 40px)',
                                                'gap': '10px'
                                        })
                                ], style={
                                        'flex': '1',
                                        'minWidth': '400px',
                                        'border': '2px solid #7b1fa2',
                                        'padding': '15px',
                                        'boxSizing': 'border-box',
                                        'display': 'flex',
                                        'flexDirection': 'column'
                                })
                        ], style={
                                'display': 'flex',
                                'gap': '10px',
                                'padding': '10px',
                                'height': '40vh',
                                'minHeight': '300px',
                                'flexWrap': 'wrap'  # Allow wrapping on small screens
                        }),
                        
                        # Pane 4: Redshift Estimates (bottom)
                        html.Div([
                                html.H3("Redshift Estimates", style={'margin': '0 0 10px 0'}),
                                html.Div([
                                        # Controls on the left (20%)
                                        html.Div([
                                                self._create_redshift_controls()
                                        ], style={
                                                'width': '20%',
                                                'minWidth': '150px',
                                                'paddingRight': '10px',
                                                'boxSizing': 'border-box',
                                                'overflowY': 'auto'
                                        }),
                                        # Plot on the right (80%)
                                        html.Div([
                                                dcc.Graph(
                                                        id='redshift-plot',
                                                        style={'height': '100%'},
                                                        config={'responsive': True}
                                                )
                                        ], style={
                                                'width': '80%',
                                                'boxSizing': 'border-box'
                                        })
                                ], style={
                                        'display': 'flex',
                                        'height': 'calc(100% - 40px)',
                                        'gap': '10px'
                                })
                        ], style={
                                'border': '2px solid #388e3c',
                                'padding': '15px',
                                'margin': '10px',
                                'boxSizing': 'border-box',
                                'height': 'calc(50vh - 20px)',
                                'minHeight': '300px',
                                'display': 'flex',
                                'flexDirection': 'column'
                        })
                ], style={
                        'height': 'calc(100vh - 84px)',  # Subtract header height
                        'overflow': 'auto',
                        'display': 'flex',
                        'flexDirection': 'column'
                }),
                
                # Hidden div to store current object data
                html.Div(id='current-object-idx', style={'display': 'none'}, 
                        children=str(self.current_object_idx))
        ], style={
                'margin': '0',
                'padding': '0',
                'height': '100vh',
                'overflow': 'hidden',
                'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        })
        
        
    def _create_selection_pane(self):
        """Create the object selection controls."""
        # This method is no longer needed as controls are inline
        pass
    
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
            [Output('current-object-idx', 'children'),
             Output('object-slider', 'value')],
            [Input('back-button', 'n_clicks'),
             Input('next-button', 'n_clicks'),
             Input('object-slider', 'value')],
            [State('current-object-idx', 'children')]
        )
        def update_object_idx(back_clicks, next_clicks, slider_value, current_idx):
            ctx = dash.callback_context
            if not ctx.triggered:
                return str(self.current_object_idx), self.current_object_idx
                
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            current_idx = int(current_idx)
            
            if trigger_id == 'next-button':
                new_idx = min(current_idx + 1, self.n_objects - 1)
            elif trigger_id == 'back-button':
                new_idx = max(current_idx - 1, 0)
            elif trigger_id == 'object-slider':
                new_idx = slider_value
            else:
                new_idx = current_idx
                
            return str(new_idx), new_idx
        
        @self.app.callback(
            [Output('back-button', 'disabled'),
             Output('next-button', 'disabled'),
             Output('object-counter', 'children')],
            [Input('current-object-idx', 'children')]
        )
        def update_navigation_state(idx_str):
            idx = int(idx_str)
            back_disabled = (idx == 0)
            next_disabled = (idx == self.n_objects - 1)
            counter_text = f"{idx + 1} of {self.n_objects}"
            return back_disabled, next_disabled, counter_text
        
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
        catalog_utils.load_yaml('sandbox_catalogs.yaml')
        wrapper = RailSvcCatalogWrapper(3)
        viz = SingleCatalogRedshiftVisualizer(wrapper)
        viz.run(debug=False, port=8051)

        
if __name__ == '__main__':

    SingleCatalogRedshiftVisualizer.main()
