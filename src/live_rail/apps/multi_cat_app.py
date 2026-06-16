import asyncio
import dash
from dash import dcc, html, Input, Output, State, ALL
import plotly.graph_objs as go
import numpy as np
import plotly.express as px
import logging

from rail.utils import catalog_utils
from rail_svc import db

from live_rail.wrappers.object_wrapper import MultiCatalogWrapper
from live_rail.wrappers.rail_svc_wrapper import RailSvcLocalSimpleMultiCatalogWrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiCatalogRedshiftVisualizer:
    """Interactive dashboard for exploring multi-catalog photometric redshift estimates."""
    
    # Color schemes
    ESTIMATOR_COLORS = {
        'combined': px.colors.qualitative.Dark24,
        'catalog': px.colors.qualitative.Light24,
        'spectrum': px.colors.qualitative.Plotly,
    }
    
    def __init__(self, catalog_wrapper: MultiCatalogWrapper):
        """Initialize visualizer with multi-catalog wrapper."""
        logger.info(f"Initializing visualizer with {catalog_wrapper}")
        self.catalog = catalog_wrapper
        self.app = dash.Dash(__name__)
        self.n_objects = self.catalog.get_nobjects()
        self.catalog_names = list(self.catalog._catalogs.keys())
        
        logger.info(f"Loaded {len(self.catalog_names)} catalogs with {self.n_objects} objects")
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Create dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.H1("Multi-Catalog Redshift Explorer", 
                   style={'textAlign': 'center', 'margin': '0', 'padding': '15px 0',
                          'backgroundColor': '#f5f5f5', 'borderBottom': '2px solid #ddd',
                          'height': '60px', 'boxSizing': 'border-box'}),
            
            html.Div([
                # Object Selection (10%)
                self.create_selection_panel(),
                
                # Spectrum and Color-Color (25%)
                html.Div([
                    self.create_plot_panel("Photometric Spectrum", 'spectrum-plot', 
                                          self.create_spectrum_controls(), '#f57c00'),
                    self.create_plot_panel("Color-Color Relations", 'color-color-plot',
                                          self.create_color_controls(), '#7b1fa2'),
                ], style={'display': 'flex', 'gap': '10px', 'padding': '10px',
                         'height': '25%', 'minHeight': '200px', 'boxSizing': 'border-box'}),
                
                # Redshift Estimates (65%)
                self.create_plot_panel("Redshift Estimates", 'redshift-plot',
                                      self.create_redshift_controls(), '#388e3c',
                                      {'margin': '10px', 'height': '65%', 'minHeight': '300px'}),
            ], style={'height': 'calc(100vh - 60px)', 'overflow': 'hidden',
                     'display': 'flex', 'flexDirection': 'column', 'boxSizing': 'border-box'}),
            
            # State storage
            dcc.Store(id='current-object-idx', data=0),
        ], style={'margin': '0', 'padding': '0', 'height': '100vh', 'overflow': 'hidden',
                 'fontFamily': 'Arial, sans-serif'})
    
    def create_selection_panel(self):
        """Create object selection panel."""
        return html.Div([
            html.H3("Object Selection", style={'margin': '0 0 15px 0'}),
            html.Div([
                html.Button('← Back', id='back-button', n_clicks=0, disabled=True,
                           style={'padding': '10px 20px', 'fontSize': '14px', 'cursor': 'pointer',
                                 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none',
                                 'borderRadius': '4px', 'marginRight': '15px', 'minWidth': '100px'}),
                html.Div([
                    html.Label("Select Object:", style={'fontWeight': 'bold', 'marginBottom': '8px',
                                                        'display': 'block', 'fontSize': '14px'}),
                    html.Div([  # Wrap slider in a div for styling
                        dcc.Slider(id='object-slider', min=0, max=self.n_objects - 1, value=0, step=1,
                                  marks={i: str(i) for i in range(0, self.n_objects, max(1, self.n_objects // 10))},
                                  tooltip={"placement": "bottom", "always_visible": True}, 
                                  updatemode='drag'),
                    ], style={'marginBottom': '10px'}),  # Style moved to wrapper div
                    html.Div([
                        html.Span("Object ", style={'fontSize': '14px'}),
                        html.Span(id='object-counter', children=f"1 of {self.n_objects}",
                                 style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#2196F3'})
                    ], style={'textAlign': 'center'})
                ], style={'flex': '1', 'minWidth': '300px', 'maxWidth': '600px'}),
                html.Button('Next →', id='next-button', n_clicks=0,
                           style={'padding': '10px 20px', 'fontSize': '14px', 'cursor': 'pointer',
                                 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none',
                                 'borderRadius': '4px', 'marginLeft': '15px', 'minWidth': '100px'}),
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '10px'})
        ], style={'padding': '15px', 'backgroundColor': '#fafafa', 'borderBottom': '1px solid #ddd',
                 'height': '10%', 'minHeight': '80px', 'boxSizing': 'border-box'})
    
    def create_color_controls(self):
        """Create color-color panel controls."""
        return html.Div([
            html.Label("Select Catalog:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='color-catalog-dropdown',
                options=[{'label': name, 'value': name} for name in self.catalog_names],
                value=self.catalog_names[0] if self.catalog_names else None
            ),
            html.Div(style={'marginBottom': '10px'}),  # Spacing
            html.Label("X-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-x-dropdown'),
            html.Div(style={'marginBottom': '10px'}),  # Spacing
            html.Label("Y-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-y-dropdown'),
        ])
    
    def create_redshift_controls(self):
        """Create redshift panel controls."""
        section_style = {'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'}
        header_style = {'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}
        
        return html.Div([
            # Combined Estimates
            html.Details([
                html.Summary("Combined Estimates", style=header_style),
                html.Div([
                    dcc.Checklist(id='combined-estimate-checklist', inline=False)
                ], style=section_style)
            ], open=True, style={'marginBottom': '15px'}),
            
            # Individual Catalog Estimates
            html.Details([
                html.Summary("Individual Catalog Estimates", style=header_style),
                html.Div([
                    html.Div(id='catalog-estimate-checklists-container')
                ], style=section_style)
            ], open=False, style={'marginBottom': '15px'}),
            
            # Plot Options
            html.Details([
                html.Summary("Plot Options", style=header_style),
                html.Div([
                    html.Label("Redshift Grid Range:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'fontSize': '12px'}),
                    html.Div([  # Wrap RangeSlider in a div for styling
                        dcc.RangeSlider(
                            id='redshift-range',
                            min=0, max=5, value=[0, 3], step=0.1,
                            marks={i: str(i) for i in range(6)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'marginTop': '10px'})  # Style moved to wrapper div
                ], style=section_style)
            ], open=False, style={'marginBottom': '15px'}),
        ])
        
    def create_plot_panel(self, title, plot_id, controls, border_color, extra_style=None):
        """Create a panel with controls and plot."""
        style = {'padding': '15px', 'boxSizing': 'border-box', 'display': 'flex',
                'flexDirection': 'column', 'border': f'2px solid {border_color}',
                'flex': '1', 'minWidth': '400px', 'height': '100%'}
        if extra_style:
            style.update(extra_style)
        
        return html.Div([
            html.H3(title, style={'margin': '0 0 10px 0'}),
            html.Div([
                html.Div([controls], style={'width': '25%', 'minWidth': '200px', 'paddingRight': '10px',
                                           'boxSizing': 'border-box', 'overflowY': 'auto', 'height': '100%'}),
                html.Div([
                    dcc.Graph(id=plot_id, style={'height': '100%', 'width': '100%'}, config={'responsive': True})
                ], style={'width': '75%', 'boxSizing': 'border-box', 'height': '100%'})
            ], style={'display': 'flex', 'height': 'calc(100% - 40px)', 'gap': '10px'})
        ], style=style)
    
    def create_spectrum_controls(self):
        """Create spectrum panel controls."""
        return html.Div([
            html.Label("Show Catalogs:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Checklist(
                id='spectrum-catalog-checklist',
                options=[{'label': name, 'value': name} for name in self.catalog_names],
                value=self.catalog_names,
                inline=False,
                style={'marginBottom': '10px'}
            )
        ])
    
    def setup_callbacks(self):
        """Setup all interactive callbacks."""
        
        @self.app.callback(
            [Output('current-object-idx', 'data'), Output('object-slider', 'value')],
            [Input('back-button', 'n_clicks'), Input('next-button', 'n_clicks'), Input('object-slider', 'value')],
            [State('current-object-idx', 'data')]
        )
        def update_object_idx(back_clicks, next_clicks, slider_value, current_idx):
            """Update object index from navigation."""
            if current_idx is None:
                current_idx = 0
            
            ctx = dash.callback_context
            if not ctx.triggered:
                return 0, 0
            
            trigger = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger == 'next-button':
                new_idx = min(current_idx + 1, self.n_objects - 1)
            elif trigger == 'back-button':
                new_idx = max(current_idx - 1, 0)
            elif trigger == 'object-slider':
                new_idx = slider_value
            else:
                new_idx = current_idx
            
            return new_idx, new_idx
        
        @self.app.callback(
            [Output('back-button', 'disabled'), Output('next-button', 'disabled'), Output('object-counter', 'children')],
            [Input('current-object-idx', 'data')]
        )
        def update_navigation_state(idx):
            """Update navigation buttons."""
            if idx is None:
                idx = 0
            return (idx == 0), (idx == self.n_objects - 1), f"{idx + 1} of {self.n_objects}"
        
        @self.app.callback(
            [Output('color-x-dropdown', 'options'), Output('color-y-dropdown', 'options'),
             Output('color-x-dropdown', 'value'), Output('color-y-dropdown', 'value')],
            [Input('current-object-idx', 'data'), Input('color-catalog-dropdown', 'value')],
            [State('color-x-dropdown', 'value'), State('color-y-dropdown', 'value')]
        )
        def update_color_dropdowns(idx, catalog_name, current_x, current_y):
            """Update color dropdowns, preserving selections."""
            if idx is None or not catalog_name:
                return [], [], None, None
            
            multi_obj = self.catalog.get_wrapper(idx)
            if multi_obj is None:
                return [], [], None, None
            
            catalog_obj = multi_obj.objects.get(catalog_name)
            if not catalog_obj:
                return [], [], None, None
            
            color_names = list(catalog_obj.get_colors().keys())
            options = [{'label': name, 'value': name} for name in color_names]
            
            # Preserve selections if they exist
            x = current_x if current_x in color_names else (color_names[0] if color_names else None)
            y = current_y if current_y in color_names else (color_names[1] if len(color_names) > 1 else x)
            
            return options, options, x, y
        
        @self.app.callback(
            [Output('combined-estimate-checklist', 'options'), Output('combined-estimate-checklist', 'value'),
             Output('catalog-estimate-checklists-container', 'children')],
            [Input('current-object-idx', 'data')],
            [State('combined-estimate-checklist', 'value'),
             State({'type': 'catalog-estimate-checklist', 'catalog': ALL}, 'value')]
        )
        def update_redshift_checklists(idx, current_combined, current_catalog_values):
            """Update redshift checklists, preserving selections."""
            if idx is None:
                idx = 0
            
            # Combined estimates
            combined_names = self.catalog.get_estimate_names()
            combined_options = [{'label': n, 'value': f'combined_{n}'} for n in combined_names]
            combined_keys = [f'combined_{n}' for n in combined_names]
            
            # Preserve or default
            ctx = dash.callback_context
            if not ctx.triggered or not current_combined:
                combined_values = combined_keys  # Select all on first load
            else:
                combined_values = [v for v in (current_combined or []) if v in combined_keys]
            
            # Catalog checklists
            catalog_checklists = []
            for i, cat_name in enumerate(self.catalog_names):
                try:
                    catalog = self.catalog.get_catalog(cat_name)
                    estimate_names = catalog.get_estimate_names()
                    
                    if estimate_names:
                        # Preserve selections for this catalog
                        catalog_keys = [f'{cat_name}_{name}' for name in estimate_names]
                        
                        # Get current values for this catalog (if they exist)
                        if current_catalog_values and i < len(current_catalog_values):
                            catalog_values = [v for v in current_catalog_values[i] if v in catalog_keys]
                        else:
                            catalog_values = catalog_keys  # Default: select all
                        
                        catalog_checklists.append(
                            html.Div([
                                html.Label(f"{cat_name}:",
                                         style={'fontWeight': 'bold', 'fontSize': '12px', 'marginTop': '5px'}),
                                dcc.Checklist(
                                    id={'type': 'catalog-estimate-checklist', 'catalog': cat_name},
                                    options=[{'label': name, 'value': f'{cat_name}_{name}'} 
                                            for name in estimate_names],
                                    value=catalog_values,
                                    inline=False,
                                    style={'fontSize': '11px', 'marginLeft': '10px'}
                                )
                            ], style={'marginBottom': '10px'})
                        )
                except Exception as e:
                    logger.warning(f"Error processing catalog {cat_name}: {e}")
                    continue
            
            return combined_options, combined_values, catalog_checklists
        
        @self.app.callback(
            Output('spectrum-plot', 'figure'),
            [Input('current-object-idx', 'data'), Input('spectrum-catalog-checklist', 'value')]
        )
        def update_spectrum(idx, selected_catalogs):
            """Update spectrum plot."""
            if idx is None or not selected_catalogs:
                return go.Figure()
            
            multi_obj = self.catalog.get_wrapper(idx)
            if multi_obj is None:
                return go.Figure()
            
            fig = go.Figure()
            colors = self.ESTIMATOR_COLORS['spectrum']
            
            for i, cat_name in enumerate(selected_catalogs):
                try:
                    catalog_obj = multi_obj._objects.get(cat_name)
                    if not catalog_obj:
                        continue
                    
                    spectrum_data = catalog_obj.get_spectrum()
                    wavelengths = spectrum_data['midpoints']
                    mags = spectrum_data['mags']
                    errors = spectrum_data['mag_errors']
                    
                    color = colors[i % len(colors)]
                    
                    fig.add_trace(go.Scatter(
                        x=wavelengths, y=mags,
                        error_y=dict(type='data', array=errors),
                        mode='markers+lines', name=cat_name,
                        marker=dict(size=10, color=color),
                        line=dict(width=2, color=color)
                    ))
                except Exception as e:
                    logger.warning(f"Error plotting spectrum for {cat_name}: {e}")
                    continue
            
            fig.update_layout(
                xaxis_title='Wavelength (Å)', yaxis_title='Magnitude (AB)',
                yaxis_autorange='reversed', template='plotly_white',
                margin=dict(l=50, r=20, t=30, b=50),
                legend=dict(yanchor="bottom", y=0.99, xanchor="right", x=0.99)
            )
            fig.update_xaxes(range=[3000, 17000])
            
            return fig
        
        @self.app.callback(
            Output('color-color-plot', 'figure'),
            [Input('current-object-idx', 'data'), Input('color-catalog-dropdown', 'value'),
             Input('color-x-dropdown', 'value'), Input('color-y-dropdown', 'value')]
        )
        def update_color_color(idx, catalog_name, x_color, y_color):
            """Update color-color plot."""
            if idx is None or not catalog_name or not x_color or not y_color:
                return go.Figure()
            
            multi_obj = self.catalog.get_wrapper(idx)
            if multi_obj is None:
                return go.Figure()
            
            catalog_obj = multi_obj._objects.get(catalog_name)
            if not catalog_obj:
                return go.Figure()
            
            colors = catalog_obj.get_colors()
            x_val, x_err = colors.get(x_color, (0, 0))
            y_val, y_err = colors.get(y_color, (0, 0))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[x_val], y=[y_val],
                error_x=dict(type='data', array=[x_err]),
                error_y=dict(type='data', array=[y_err]),
                mode='markers', marker=dict(size=15, color='red', symbol='diamond'),
                name=f'{catalog_name}'
            ))
            
            fig.update_layout(
                xaxis_title=x_color, yaxis_title=y_color, template='plotly_white',
                margin=dict(l=50, r=20, t=30, b=50)
            )
            fig.update_xaxes(range=[-3, 3])
            fig.update_yaxes(range=[-3, 3])
            
            return fig
        
        @self.app.callback(
            Output('redshift-plot', 'figure'),
            [Input('current-object-idx', 'data'), Input('combined-estimate-checklist', 'value'),
             Input({'type': 'catalog-estimate-checklist', 'catalog': ALL}, 'value'),
             Input('redshift-range', 'value')],
            [State({'type': 'catalog-estimate-checklist', 'catalog': ALL}, 'id')]
        )
        def update_redshift_plot(idx, combined_selected, catalog_selected_list, z_range, catalog_ids):
            """Update redshift plot."""
            if idx is None:
                idx = 0
            
            multi_obj = self.catalog.get_wrapper(idx)
            if multi_obj is None:
                return go.Figure()
            
            z_grid = np.linspace(z_range[0], z_range[1], 500)
            fig = go.Figure()
            
            # Plot combined estimates
            if combined_selected:
                combined_estimates = multi_obj.get_redshift_estimates()
                colors = self.ESTIMATOR_COLORS['combined']
                
                for i, key in enumerate(combined_selected):
                    try:
                        name = key.replace('combined_', '')
                        if name not in combined_estimates:
                            continue
                        
                        ensemble = combined_estimates[name]
                        pdf = np.squeeze(ensemble.pdf(z_grid))
                        mode_val = multi_obj._get_mode(ensemble)
                        
                        color = colors[i % len(colors)]
                        
                        fig.add_trace(go.Scatter(
                            x=z_grid, y=pdf, mode='lines',
                            name=f'Combined: {name}',
                            line=dict(width=3, color=color)
                        ))
                        
                        if mode_val and mode_val > 0:
                            mode_idx = np.argmin(np.abs(z_grid - mode_val))
                            fig.add_trace(go.Scatter(
                                x=[mode_val], y=[pdf[mode_idx]], mode='markers',
                                marker=dict(size=12, symbol='diamond', color=color),
                                showlegend=False
                            ))
                    except Exception as e:
                        logger.warning(f"Error plotting combined estimate {key}: {e}")
                        continue
            
            # Plot individual catalog estimates
            if catalog_selected_list and catalog_ids:
                colors = self.ESTIMATOR_COLORS['catalog']
                color_idx = 0
                
                for catalog_selected, catalog_id in zip(catalog_selected_list, catalog_ids):
                    if not catalog_selected:
                        continue
                    
                    try:
                        cat_name = catalog_id['catalog']
                        catalog_obj = multi_obj._objects.get(cat_name)
                        
                        if not catalog_obj:
                            continue
                        
                        catalog_estimates = catalog_obj.get_redshift_estimates()
                        
                        for key in catalog_selected:
                            try:
                                name = key.replace(f'{cat_name}_', '')
                                
                                if name not in catalog_estimates:
                                    continue
                                
                                ensemble = catalog_estimates[name]
                                pdf = np.squeeze(ensemble.pdf(z_grid))
                                mode_val = catalog_obj._get_mode(ensemble)
                                
                                color = colors[color_idx % len(colors)]
                                color_idx += 1
                                
                                fig.add_trace(go.Scatter(
                                    x=z_grid, y=pdf, mode='lines',
                                    name=f'{cat_name}: {name}',
                                    line=dict(width=2, color=color, dash='dash')
                                ))
                                
                                if mode_val and mode_val > 0:
                                    mode_idx = np.argmin(np.abs(z_grid - mode_val))
                                    fig.add_trace(go.Scatter(
                                        x=[mode_val], y=[pdf[mode_idx]], mode='markers',
                                        marker=dict(size=8, symbol='circle', color=color),
                                        showlegend=False
                                    ))
                            except Exception as e:
                                logger.warning(f"Error plotting {key}: {e}")
                                continue
                    except Exception as e:
                        logger.warning(f"Error processing catalog: {e}")
                        continue
            
            # Add true redshift
            true_z = multi_obj.get_true_redshift()
            if true_z and z_range[0] <= true_z <= z_range[1]:
                fig.add_vline(x=true_z, line=dict(color='black', width=3, dash='dash'),
                             annotation_text='True z', annotation_position='top')
            
            fig.update_layout(
                xaxis_title='Redshift', yaxis_title='Probability Density',
                hovermode='x unified', template='plotly_white',
                margin=dict(l=50, r=20, t=30, b=50),
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99,
                           bgcolor="rgba(255,255,255,0.8)")
            )
            
            return fig
    
    def run(self, debug: bool = True, port: int = 8050):
        """Run the dashboard."""
        logger.info(f"Starting server on port {port}")
        self.app.run(debug=debug, port=port)
    
    @classmethod
    def main(cls):
        """Main entry point."""
        logger.info("Starting application")
        
        # Close existing DB
        try:
            asyncio.run(db.close_db())
        except Exception as e:
            logger.warning(f"Could not close DB: {e}")
        
        # Initialize
        db.init_db()
        catalog_utils.load_yaml('nb/sandbox_catalogs.yaml')
        wrapper = RailSvcLocalSimpleMultiCatalogWrapper(3)
        
        # Run
        viz = cls(wrapper)
        viz.run(debug=True, port=8051)


if __name__ == '__main__':
    MultiCatalogRedshiftVisualizer.main()
