import asyncio
import dash
from dash import dcc, html, Input, Output, State, callback, ALL
import plotly.graph_objs as go
import numpy as np
from typing import Optional, List, Dict, Tuple, Any
import plotly.express as px
import logging

from pathlib import Path
from rail.utils import catalog_utils
from rail_svc import db, local_sync

from live_rail.wrappers.object_wrapper import CatalogWrapper, ObjectWrapper
from live_rail.wrappers.rail_svc_wrapper import RailSvcCatalogWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CatalogRedshiftVisualizer:
    # Style constants
    CONTROL_STYLE = {
        'width': '25%',
        'minWidth': '200px',
        'paddingRight': '10px',
        'boxSizing': 'border-box',
        'overflowY': 'auto',
        'height': '100%'
    }
    
    PLOT_STYLE = {
        'width': '75%',
        'boxSizing': 'border-box',
        'height': '100%'
    }
    
    PANEL_CONTAINER_STYLE = {
        'display': 'flex',
        'height': '100%',
        'gap': '10px'
    }
    
    PANEL_BASE_STYLE = {
        'padding': '15px',
        'boxSizing': 'border-box',
        'display': 'flex',
        'flexDirection': 'column'
    }
    
    # Color scheme constants
    SPECTRUM_BORDER_COLOR = '#f57c00'
    COLOR_COLOR_BORDER_COLOR = '#7b1fa2'
    REDSHIFT_BORDER_COLOR = '#388e3c'
    
    # Consistent color scheme for estimators (expanded palette)
    ESTIMATOR_COLORS = {
        'precomputed': px.colors.qualitative.Set1,  # Vibrant colors for precomputed
        'live': px.colors.qualitative.Set2,  # Different palette for live estimates
    }
    
    def __init__(self, catalog_wrapper: CatalogWrapper, catalog_name: str = "Catalog"):
        """
        Initialize the visualizer with a CatalogWrapper instance.
        
        Parameters
        ----------
        catalog_wrapper : CatalogWrapper
            The wrapper containing the catalog
        catalog_name : str, optional
            Display name for the catalog
        """
        logger.info(f"Initializing CatalogRedshiftVisualizer with {catalog_wrapper}")
        self.catalog = catalog_wrapper
        self.catalog_name = catalog_name
        self.app = dash.Dash(__name__)
        self.current_object_idx = 0
        self.n_objects = self.catalog.get_nobjects()
        
        # Track estimator color assignments
        self.estimator_color_map = {}
        
        logger.info(f"Loaded catalog with {self.n_objects} objects")
        
        self.setup_layout()
        self.setup_callbacks()
    
    def _get_estimator_color(self, estimator_name: str, is_precomputed: bool) -> str:
        """
        Get a consistent color for an estimator.
        
        Parameters
        ----------
        estimator_name : str
            Name of the estimator
        is_precomputed : bool
            Whether this is a precomputed estimate
            
        Returns
        -------
        str
            CSS color string
        """
        key = ('precomputed' if is_precomputed else 'live', estimator_name)
        
        if key not in self.estimator_color_map:
            palette = self.ESTIMATOR_COLORS['precomputed' if is_precomputed else 'live']
            color_idx = len([k for k in self.estimator_color_map.keys() if k[0] == key[0]])
            self.estimator_color_map[key] = palette[color_idx % len(palette)]
        
        return self.estimator_color_map[key]
    
    def _create_panel_header(self, title: str) -> html.H3:
        """Create a standardized panel header."""
        return html.H3(title, style={'margin': '0 0 10px 0'})
    
    def _create_control_panel_layout(
        self, 
        controls: html.Div, 
        plot_id: str
    ) -> html.Div:
        """
        Create a standardized layout with controls on left and plot on right.
        
        Parameters
        ----------
        controls : html.Div
            The control elements to display
        plot_id : str
            The ID for the graph component
            
        Returns
        -------
        html.Div
            The complete panel layout
        """
        return html.Div([
            html.Div([controls], style=self.CONTROL_STYLE),
            html.Div([
                dcc.Graph(
                    id=plot_id,
                    style={'height': '100%', 'width': '100%'},
                    config={'responsive': True}
                )
            ], style=self.PLOT_STYLE)
        ], style=self.PANEL_CONTAINER_STYLE)
    
    def _create_panel(
        self, 
        title: str, 
        controls: html.Div, 
        plot_id: str,
        border_color: str,
        additional_style: Optional[Dict[str, Any]] = None
    ) -> html.Div:
        """
        Create a complete panel with title, controls, and plot area.
        
        Parameters
        ----------
        title : str
            Panel title
        controls : html.Div
            Control elements
        plot_id : str
            Graph component ID
        border_color : str
            CSS color for border
        additional_style : Optional[Dict[str, Any]]
            Additional style properties
            
        Returns
        -------
        html.Div
            Complete panel component
        """
        style = {
            **self.PANEL_BASE_STYLE,
            'border': f'2px solid {border_color}'
        }
        if additional_style:
            style.update(additional_style)
        
        return html.Div([
            self._create_panel_header(title),
            self._create_control_panel_layout(controls, plot_id)
        ], style=style)
    
    def setup_layout(self):
        """Create the 4-pane layout for the dashboard."""
        logger.info("Setting up dashboard layout")
        self.app.layout = html.Div([
            html.H1(f"Redshift Explorer - {self.catalog_name}", 
                   style={
                       'textAlign': 'center', 
                       'margin': '0',
                       'padding': '15px 0',
                       'backgroundColor': '#f5f5f5',
                       'borderBottom': '2px solid #ddd',
                       'height': '60px',
                       'boxSizing': 'border-box'
                   }),
            
            # Main container with flex layout
            html.Div([
                # Pane 1: Object Selection (top) - 10% of remaining space
                self._create_object_selection_panel(),
                
                # Middle row: Spectrum and Color-Color side by side - 25% of remaining space
                html.Div([
                    # Pane 2: Spectrum (left)
                    self._create_spectrum_panel(),
                    
                    # Pane 3: Color-Color Diagram (right)
                    self._create_color_color_panel()
                ], style={
                    'display': 'flex',
                    'gap': '10px',
                    'padding': '10px',
                    'height': '25%',
                    'minHeight': '200px',
                    'boxSizing': 'border-box'
                }),
                
                # Pane 4: Redshift Estimates (bottom) - 65% of remaining space
                self._create_redshift_panel()
            ], style={
                'height': 'calc(100vh - 60px)',
                'overflow': 'hidden',
                'display': 'flex',
                'flexDirection': 'column',
                'boxSizing': 'border-box'
            }),
            
            # Use dcc.Store for state management
            dcc.Store(id='current-object-idx', data=self.current_object_idx),
            dcc.Store(id='magnitude-adjustments', data={}),
            dcc.Store(id='family-data', data=None),  # Store family samples data
        ], style={
            'margin': '0',
            'padding': '0',
            'height': '100vh',
            'overflow': 'hidden',
            'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        })
    
    def _create_object_selection_panel(self) -> html.Div:
        """Create the object selection panel - 10% of window."""
        return html.Div([
            html.H3("Object Selection", style={'margin': '0 0 15px 0'}),
            html.Div([
                # Back button
                html.Button(
                    '← Back',
                    id='back-button',
                    n_clicks=0,
                    disabled=True,
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
            'padding': '15px',
            'backgroundColor': '#fafafa',
            'borderBottom': '1px solid #ddd',
            'height': '10%',
            'minHeight': '80px',
            'boxSizing': 'border-box'
        })
    
    def _create_spectrum_panel(self) -> html.Div:
        """Create the spectrum visualization panel."""
        controls = html.Div([
            html.Details([
                html.Summary("Magnitude Adjustments", 
                           style={'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}),
                html.Div([
                    html.Div(id='magnitude-sliders-container'),
                    html.Hr(style={'margin': '10px 0'}),
                    html.Button(
                        'Reset Magnitudes',
                        id='reset-magnitudes-button',
                        n_clicks=0,
                        style={
                            'padding': '5px 10px',
                            'fontSize': '12px',
                            'cursor': 'pointer',
                            'backgroundColor': '#ff9800',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'width': '100%'
                        }
                    )
                ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'})
            ], open=False, style={'marginBottom': '15px'}),
        ])
        
        return self._create_panel(
            title="Photometric Spectrum",
            controls=controls,
            plot_id='spectrum-plot',
            border_color=self.SPECTRUM_BORDER_COLOR,
            additional_style={
                'flex': '1',
                'minWidth': '400px',
                'height': '100%'
            }
        )
    
    def _create_color_color_panel(self) -> html.Div:
        """Create the color-color diagram panel."""
        controls = self._create_color_controls()
        
        return self._create_panel(
            title="Color-Color Relations",
            controls=controls,
            plot_id='color-color-plot',
            border_color=self.COLOR_COLOR_BORDER_COLOR,
            additional_style={
                'flex': '1',
                'minWidth': '400px',
                'height': '100%'
            }
        )
    
    def _create_redshift_panel(self) -> html.Div:
        """Create the redshift estimates panel - uses remaining 65% of window."""
        controls = self._create_redshift_controls()
        
        return self._create_panel(
            title="Redshift Estimates",
            controls=controls,
            plot_id='redshift-plot',
            border_color=self.REDSHIFT_BORDER_COLOR,
            additional_style={
                'margin': '10px',
                'height': '65%',
                'minHeight': '300px',
                'boxSizing': 'border-box'
            }
        )
    
    def _create_color_controls(self) -> html.Div:
        """Create controls for color-color diagram."""
        return html.Div([
            html.Label("X-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-x-dropdown', style={'marginBottom': 10}),
            html.Label("Y-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-y-dropdown', style={'marginBottom': 10}),
        ])
    
    def _create_redshift_controls(self) -> html.Div:
        """Create controls for redshift display - organized with nested sections."""
        return html.Div([
            # Magnitude and Error Controls
            html.Details([
                html.Summary("Magnitude & Error Controls", 
                           style={'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}),
                html.Div([
                    html.Label("Error Scale:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'fontSize': '12px'}),
                    dcc.Slider(
                        id='error-scale-slider',
                        min=0.1,
                        max=3.0,
                        value=1.0,
                        step=0.1,
                        marks={i/10: f'{i/10:.1f}' for i in range(1, 31, 5)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'})
            ], open=False, style={'marginBottom': '15px'}),
            
            # Pre-computed Estimates
            html.Details([
                html.Summary("Pre-computed Estimates", 
                           style={'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}),
                html.Div([
                    dcc.Checklist(
                        id='precomputed-estimate-checklist',
                        inline=False,
                    ),
                ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'})
            ], open=True, style={'marginBottom': '15px'}),
            
            # Live Estimators
            html.Details([
                html.Summary("Live Estimators", 
                           style={'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}),
                html.Div([
                    dcc.Checklist(
                        id='live-estimator-checklist',
                        inline=False,
                    ),
                ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'})
            ], open=False, style={'marginBottom': '15px'}),
            
            # Plot Options
            html.Details([
                html.Summary("Plot Options", 
                           style={'fontWeight': 'bold', 'cursor': 'pointer', 'marginBottom': '10px'}),
                html.Div([
                    dcc.Checklist(
                        id='plot-options-checklist',
                        options=[
                            {'label': 'Show ensemble families', 'value': 'show_families'}
                        ],
                        value=[],
                        inline=False,
                        style={'marginBottom': '10px'}
                    ),
                    html.Label("Number of samples:", 
                             style={'fontWeight': 'bold', 'marginBottom': '5px','fontSize': '12px'}),
                    dcc.Slider(
                        id='n-samples-slider',
                        min=5,
                        max=100,
                        value=20,
                        step=5,
                        marks={i: str(i) for i in range(5, 101, 20)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Hr(style={'margin': '10px 0'}),
                    html.Label("Redshift Grid Range:", 
                             style={'fontWeight': 'bold', 'marginBottom': '5px', 'fontSize': '12px'}),
                    dcc.RangeSlider(
                        id='redshift-range',
                        min=0,
                        max=5,
                        value=[0, 3],
                        step=0.1,
                        marks={i: str(i) for i in range(6)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px'})
            ], open=False, style={'marginBottom': '15px'}),
        ])
    
    def setup_callbacks(self):
        """Setup all interactive callbacks."""
        logger.info("Setting up callbacks")
        
        @self.app.callback(
            [Output('current-object-idx', 'data'),
             Output('object-slider', 'value')],
            [Input('back-button', 'n_clicks'),
             Input('next-button', 'n_clicks'),
             Input('object-slider', 'value')],
            [State('current-object-idx', 'data')],
            prevent_initial_call=False
        )
        def update_object_idx(
            back_clicks: int, 
            next_clicks: int, 
            slider_value: int, 
            current_idx: Optional[int]
        ) -> Tuple[int, int]:
            """Update the current object index based on navigation controls."""
            if current_idx is None:
                current_idx = 0
            
            ctx = dash.callback_context
            if not ctx.triggered:
                logger.debug("Initial callback - setting index to 0")
                return 0, 0
            
            try:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                logger.debug(f"Triggered by: {trigger_id}, current_idx: {current_idx}")
                
                if trigger_id == 'next-button':
                    new_idx = min(current_idx + 1, self.n_objects - 1)
                    logger.info(f"Next button clicked: {current_idx} -> {new_idx}")
                elif trigger_id == 'back-button':
                    new_idx = max(current_idx - 1, 0)
                    logger.info(f"Back button clicked: {current_idx} -> {new_idx}")
                elif trigger_id == 'object-slider':
                    new_idx = slider_value
                    logger.info(f"Slider moved to: {new_idx}")
                else:
                    new_idx = current_idx
                    logger.debug(f"Unknown trigger, keeping index at {current_idx}")
                    
                return new_idx, new_idx
            except Exception as e:
                logger.error(f"Error updating object index: {e}", exc_info=True)
                return current_idx if current_idx is not None else 0, current_idx if current_idx is not None else 0
        
        @self.app.callback(
            [Output('back-button', 'disabled'),
             Output('next-button', 'disabled'),
             Output('object-counter', 'children')],
            [Input('current-object-idx', 'data')]
        )
        def update_navigation_state(idx: Optional[int]) -> Tuple[bool, bool, str]:
            """Update navigation button states and counter display."""
            try:
                if idx is None:
                    idx = 0
                    
                back_disabled = (idx == 0)
                next_disabled = (idx == self.n_objects - 1)
                counter_text = f"{idx + 1} of {self.n_objects}"
                logger.debug(f"Navigation state updated: idx={idx}, back={back_disabled}, next={next_disabled}")
                return back_disabled, next_disabled, counter_text
            except Exception as e:
                logger.error(f"Error updating navigation state: {e}", exc_info=True)
                return True, True, "Error"
        
        @self.app.callback(
            [Output('magnitude-sliders-container', 'children'),
             Output('magnitude-adjustments', 'data')],
            [Input('current-object-idx', 'data'),
             Input('reset-magnitudes-button', 'n_clicks'),
             Input({'type': 'magnitude-slider', 'band': ALL}, 'value')],
            [State({'type': 'magnitude-slider', 'band': ALL}, 'id'),
             State('magnitude-adjustments', 'data')],
            prevent_initial_call=False
        )
        def update_magnitude_sliders(
            idx: Optional[int],
            reset_clicks: int,
            slider_values: List[float],
            slider_ids: List[Dict],
            current_adjustments: Dict
        ) -> Tuple[List[html.Div], Dict]:
            """Create magnitude adjustment sliders and track their values."""
            if idx is None:
                idx = 0
            
            ctx = dash.callback_context
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            
            # Reset adjustments if reset button clicked
            if trigger_id == 'reset-magnitudes-button':
                current_adjustments = {}
            
            # Initialize adjustments if None
            if current_adjustments is None:
                current_adjustments = {}
            
            # Update adjustments from slider changes
            if trigger_id and 'magnitude-slider' in trigger_id and slider_ids:
                for slider_id, value in zip(slider_ids, slider_values):
                    key = slider_id['band']
                    current_adjustments[key] = value
            
            try:
                obj = self.catalog.get_object(idx)
                if obj is None:
                    return [], {}
                
                band_names = obj.get_band_names()
                mags = obj.get_magnitudes()
                
                sliders = []
                for band, mag in zip(band_names, mags):
                    # Keep existing adjustment or default to 0
                    current_val = current_adjustments.get(band, 0.0)
                    
                    sliders.append(html.Div([
                        html.Label(f"{band}:", style={'fontSize': '11px', 'fontWeight': 'bold'}),
                        dcc.Slider(
                            id={'type': 'magnitude-slider', 'band': band},
                            min=-2.0,
                            max=2.0,
                            value=current_val,
                            step=0.05,
                            marks={i: f'{i:+.1f}' for i in [-2, -1, 0, 1, 2]},
                            tooltip={"placement": "bottom", "always_visible": True}
                        ),
                    ], style={'marginBottom': '8px'}))
                
                return sliders, current_adjustments
            except Exception as e:
                logger.error(f"Error creating magnitude sliders: {e}", exc_info=True)
                return [], {}
        
        @self.app.callback(
            [Output('color-x-dropdown', 'options'),
             Output('color-y-dropdown', 'options'),
             Output('color-x-dropdown', 'value'),
             Output('color-y-dropdown', 'value')],
            [Input('current-object-idx', 'data')],
            [State('color-x-dropdown', 'value'),
             State('color-y-dropdown', 'value')],
            prevent_initial_call=False
        )
        def update_color_dropdowns(
            idx: Optional[int],
            current_x: Optional[str],
            current_y: Optional[str]
        ) -> Tuple[List[Dict], List[Dict], Optional[str], Optional[str]]:
            """Update color dropdown options based on current object, preserving selections."""
            if idx is None:
                idx = 0
            
            try:
                obj = self.catalog.get_object(idx)
                logger.info(f"Got object for color dropdowns: {obj}")

                if obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return [], [], None, None
                
                colors = obj.get_colors()
                color_names = list(colors.keys())
                
                options = [{'label': name, 'value': name} for name in color_names]
                
                # Try to preserve current selections if they exist in new object
                if current_x and current_x in color_names:
                    default_x = current_x
                else:
                    default_x = color_names[0] if len(color_names) > 0 else None
                
                if current_y and current_y in color_names:
                    default_y = current_y
                else:
                    default_y = color_names[1] if len(color_names) > 1 else default_x
                
                logger.debug(f"Updated color dropdowns: {len(color_names)} colors")
                return options, options, default_x, default_y
            except Exception as e:
                logger.error(f"Error updating color dropdowns: {e}", exc_info=True)
                return [], [], None, None
        
        @self.app.callback(
            [Output('precomputed-estimate-checklist', 'options'),
             Output('precomputed-estimate-checklist', 'value'),
             Output('live-estimator-checklist', 'options'),
             Output('live-estimator-checklist', 'value')],
            [Input('current-object-idx', 'data')],
            [State('precomputed-estimate-checklist', 'value'),
             State('live-estimator-checklist', 'value')],
            prevent_initial_call=False
        )
        def update_redshift_checklists(
            idx: Optional[int],
            current_precomputed: Optional[List[str]],
            current_live: Optional[List[str]]
        ) -> Tuple[List[Dict], List[str], List[Dict], List[str]]:
            """Update redshift estimate checklists, preserving selections."""
            if idx is None:
                idx = 0
            
            if current_precomputed is None:
                current_precomputed = []
            if current_live is None:
                current_live = []
                
            try:
                obj = self.catalog.get_object(idx)
                if obj is None:
                    return [], [], [], []
                
                # Get pre-computed estimates
                precomputed_names = obj.get_estimate_names()
                precomputed_options = [{'label': name, 'value': f'precomputed_{name}'} 
                                      for name in precomputed_names]
                
                # Preserve selections that still exist
                precomputed_values = [val for val in current_precomputed 
                                     if val in [f'precomputed_{name}' for name in precomputed_names]]
                
                # If nothing selected, select all precomputed by default (only on first load)
                ctx = dash.callback_context
                if not ctx.triggered or (not current_precomputed and not current_live):
                    precomputed_values = [f'precomputed_{name}' for name in precomputed_names]
                
                # Get available estimators from the wrapper
                estimators = obj.get_wrapped_estimators()
                estimator_names = list(estimators.keys())
                
                live_options = [{'label': name, 'value': f'live_{name}'} 
                               for name in estimator_names]
                
                # Preserve live selections that still exist
                live_values = [val for val in current_live 
                              if val in [f'live_{name}' for name in estimator_names]]
                
                logger.debug(f"Updated redshift checklists: {len(precomputed_names)} pre-computed, "
                           f"{len(estimator_names)} live estimators")
                return precomputed_options, precomputed_values, live_options, live_values
            except Exception as e:
                logger.error(f"Error updating redshift checklists: {e}", exc_info=True)
                return [], [], [], []
        
        @self.app.callback(
            Output('spectrum-plot', 'figure'),
            [Input('current-object-idx', 'data'),
             Input('magnitude-adjustments', 'data'),
             Input('family-data', 'data'),
             Input('plot-options-checklist', 'value')]
        )
        def update_spectrum(
            idx: Optional[int],
            mag_adjustments: Optional[Dict],
            family_data: Optional[Dict],
            plot_options: List[str]
        ) -> go.Figure:
            """Update the spectrum plot with magnitude adjustments and family data."""
            if idx is None:
                idx = 0
            
            if mag_adjustments is None:
                mag_adjustments = {}
            
            show_families = 'show_families' in (plot_options or [])
            
            try:
                logger.info(f"Updating spectrum plot for object {idx}")
                obj = self.catalog.get_object(idx)
                logger.info(f"Got object for spectrum: {obj}")

                if obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure()
                
                fig = go.Figure()
                
                # Plot family spectra if available
                if show_families and family_data is not None:
                    self._add_family_spectra_to_plot(fig, obj, family_data)
                
                # Plot main spectrum
                spectrum_data = obj.get_spectrum()
                wavelengths = spectrum_data['midpoints']
                mags = spectrum_data['mags'].copy()
                mag_errors = spectrum_data['mag_errors']
                band_names = obj.get_band_names()
                
                # Apply magnitude adjustments
                for j, band in enumerate(band_names):
                    if band in mag_adjustments:
                        mags[j] += mag_adjustments[band]
                
                fig.add_trace(go.Scatter(
                    x=wavelengths,
                    y=mags,
                    error_y=dict(type='data', array=mag_errors),
                    mode='markers+lines',
                    name='Current Spectrum',
                    marker=dict(size=10, color='#1f77b4'),
                    line=dict(width=3, color='#1f77b4'),
                ))
                
                fig.update_layout(
                    xaxis_title='Wavelength (Å)',
                    yaxis_title='Magnitude (AB)',
                    yaxis_autorange='reversed',
                    hovermode='closest',
                    template='plotly_white',
                    margin=dict(l=50, r=20, t=30, b=50),
                    legend=dict(yanchor="bottom", y=0.99, xanchor="right", x=0.99)
                )
                
                fig.update_xaxes(range=[3000, 17000])
                
                logger.info(f"Successfully updated spectrum plot for object {idx}")
                return fig
            except Exception as e:
                logger.error(f"Error updating spectrum plot: {e}", exc_info=True)
                return go.Figure()
        
        @self.app.callback(
            Output('color-color-plot', 'figure'),
            [Input('current-object-idx', 'data'),
             Input('color-x-dropdown', 'value'),
             Input('color-y-dropdown', 'value'),
             Input('magnitude-adjustments', 'data'),
             Input('family-data', 'data'),
             Input('plot-options-checklist', 'value')]
        )
        def update_color_color(
            idx: Optional[int],
            x_color: Optional[str], 
            y_color: Optional[str],
            mag_adjustments: Optional[Dict],
            family_data: Optional[Dict],
            plot_options: List[str]
        ) -> go.Figure:
            """Update the color-color diagram with magnitude adjustments and family data."""
            if idx is None:
                idx = 0
                
            if not x_color or not y_color:
                return go.Figure()
            
            if mag_adjustments is None:
                mag_adjustments = {}
            
            show_families = 'show_families' in (plot_options or [])
            
            try:
                logger.info(f"Updating color-color plot: {x_color} vs {y_color}")
                obj = self.catalog.get_object(idx)
                logger.info(f"Got object for color-color: {obj}")

                if obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure()
                
                fig = go.Figure()
                
                # Plot family color-color points if available
                if show_families and family_data is not None:
                    self._add_family_colors_to_plot(fig, obj, family_data, x_color, y_color)
                
                # Get adjusted magnitudes for main object
                mags = obj.get_magnitudes().copy()
                mag_errors = obj.get_magnitude_errors()
                band_names = obj.get_band_names()
                
                # Apply adjustments
                for j, band in enumerate(band_names):
                    if band in mag_adjustments:
                        mags[j] += mag_adjustments[band]
                
                # Recalculate colors
                colors_dict = {}
                n = len(band_names)
                for i in range(n-1):
                    color_name = f"{band_names[i]} - {band_names[i+1]}"
                    colors_dict[color_name] = (
                        mags[i] - mags[i+1], 
                        np.sqrt(mag_errors[i]**2 + mag_errors[i+1]**2)
                    )
                
                x_val, x_err = colors_dict.get(x_color, (0, 0))
                y_val, y_err = colors_dict.get(y_color, (0, 0))
                
                # Plot main object
                fig.add_trace(go.Scatter(
                    x=[x_val],
                    y=[y_val],
                    error_x=dict(type='data', array=[x_err]),
                    error_y=dict(type='data', array=[y_err]),
                    mode='markers',
                    marker=dict(size=15, color='red', symbol='diamond'),
                    name='Current Object',
                ))
                
                fig.update_xaxes(range=[-3, 3])
                fig.update_yaxes(range=[-3, 3])
                
                fig.update_layout(
                    xaxis_title=x_color,
                    yaxis_title=y_color,
                    hovermode='closest',
                    template='plotly_white',
                    margin=dict(l=50, r=20, t=30, b=50)
                )
                
                logger.info(f"Successfully updated color-color plot")
                return fig
            except Exception as e:
                logger.error(f"Error updating color-color plot: {e}", exc_info=True)
                return go.Figure()
        
        @self.app.callback(
            [Output('redshift-plot', 'figure'),
             Output('family-data', 'data')],
            [Input('current-object-idx', 'data'),
             Input('precomputed-estimate-checklist', 'value'),
             Input('live-estimator-checklist', 'value'),
             Input('redshift-range', 'value'),
             Input('error-scale-slider', 'value'),
             Input('magnitude-adjustments', 'data'),
             Input('plot-options-checklist', 'value'),
             Input('n-samples-slider', 'value')]
        )
        def update_redshift_plot(
            idx: Optional[int],
            precomputed_selected: Optional[List[str]],
            live_selected: Optional[List[str]],
            z_range: List[float],
            error_scale: float,
            mag_adjustments: Optional[Dict],
            plot_options: List[str],
            n_samples: int
        ) -> Tuple[go.Figure, Optional[Dict]]:
            """Update the redshift probability distribution plot with on-the-fly estimation."""
            if idx is None:
                idx = 0
            
            if mag_adjustments is None:
                mag_adjustments = {}
            
            show_families = 'show_families' in (plot_options or [])
            
            try:
                logger.info(f"Updating redshift plot for object {idx}")
                obj = self.catalog.get_object(idx)

                logger.info(f"Got object for redshift: {obj}")

                if obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure(), None
                
                # Create redshift grid
                z_grid = np.linspace(z_range[0], z_range[1], 500)
                
                fig = go.Figure()
                
                # Initialize family data storage
                family_data = None
                
                # Plot pre-computed estimates
                if precomputed_selected:
                    self._add_precomputed_estimates_to_plot(
                        fig, obj, precomputed_selected, z_grid, idx
                    )
                
                # Plot live estimates (on-the-fly)
                if live_selected:
                    family_data = self._add_live_estimates_to_plot(
                        fig, obj, live_selected, z_grid, idx, 
                        error_scale, mag_adjustments, show_families, n_samples
                    )
                
                # Add true redshift if available
                self._add_true_redshift_to_plot(fig, obj, z_range)
                
                fig.update_layout(
                    xaxis_title='Redshift',
                    yaxis_title='Probability Density',
                    hovermode='x unified',
                    template='plotly_white',
                    margin=dict(l=50, r=20, t=30, b=50),
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="right",
                        x=0.99,
                        bgcolor="rgba(255,255,255,0.8)"
                    )
                )
                
                logger.info(f"Successfully updated redshift plot for object {idx}")
                return fig, family_data
            except Exception as e:
                logger.error(f"Error updating redshift plot: {e}", exc_info=True)
                return go.Figure(), None
    
    def _add_family_spectra_to_plot(
        self,
        fig: go.Figure,
        obj: ObjectWrapper,
        family_data: Dict
    ) -> None:
        """
        Add family spectra to the spectrum plot.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        obj : ObjectWrapper
            Object wrapper
        family_data : Dict
            Dictionary containing family samples data
        """
        try:
            band_names = obj.get_band_names()
            spectrum_data = obj.get_spectrum()
            wavelengths = spectrum_data['midpoints']
            
            # Extract samples from family_data
            samples_list = family_data.get('samples', [])
            
            for sample_idx, sample_mags in enumerate(samples_list):
                fig.add_trace(go.Scatter(
                    x=wavelengths,
                    y=sample_mags,
                    mode='lines',
                    name=f'Family member' if sample_idx == 0 else None,
                    line=dict(width=1, color='gray'),
                    opacity=0.8,
                    showlegend=(sample_idx == 0),
                    legendgroup='family_spectra'
                ))
            
            logger.debug(f"Added {len(samples_list)} family spectra to plot")
        except Exception as e:
            logger.warning(f"Error adding family spectra to plot: {e}")
    
    def _add_family_colors_to_plot(
        self,
        fig: go.Figure,
        obj: ObjectWrapper,
        family_data: Dict,
        x_color: str,
        y_color: str
    ) -> None:
        """
        Add family color-color points to the plot.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        obj : ObjectWrapper
            Object wrapper
        family_data : Dict
            Dictionary containing family samples data
        x_color : str
            X-axis color name
        y_color : str
            Y-axis color name
        """
        try:
            band_names = obj.get_band_names()
            samples_list = family_data.get('samples', [])
            
            x_vals = []
            y_vals = []
            
            for sample_mags in samples_list:
                # Calculate colors for this sample
                colors_dict = {}
                n = len(band_names)
                for i in range(n-1):
                    color_name = f"{band_names[i]} - {band_names[i+1]}"
                    colors_dict[color_name] = sample_mags[i] - sample_mags[i+1]
                
                x_val = colors_dict.get(x_color, None)
                y_val = colors_dict.get(y_color, None)
                
                if x_val is not None and y_val is not None:
                    x_vals.append(x_val)
                    y_vals.append(y_val)
            
            if x_vals and y_vals:
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='markers',
                    marker=dict(size=6, color='gray', opacity=0.8),
                    name='Family members',
                    showlegend=True
                ))
            
            logger.debug(f"Added {len(x_vals)} family color-color points to plot")
        except Exception as e:
            logger.warning(f"Error adding family colors to plot: {e}")
    
    def _add_precomputed_estimates_to_plot(
        self,
        fig: go.Figure,
        obj: ObjectWrapper,
        precomputed_selected: List[str],
        z_grid: np.ndarray,
        idx: int
    ) -> None:
        """
        Add pre-computed redshift estimates to the plot.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        obj : ObjectWrapper
            Object wrapper
        precomputed_selected : List[str]
            Selected pre-computed estimate names
        z_grid : np.ndarray
            Redshift grid for PDF evaluation
        idx : int
            Current object index
        """
        try:
            logger.info(f"Adding pre-computed estimates: {idx}")

            precomputed_estimates = obj.get_redshift_estimates()

            logger.info(f"Pre-computed estimates loop: {precomputed_selected}")
            
            for i, estimate_key in enumerate(precomputed_selected):
                try:
                    logger.debug(f"Adding pre-computed estimate 1: {estimate_key}")

                    estimate_name = estimate_key.replace('precomputed_', '')
                    if estimate_name not in precomputed_estimates:
                        logger.warning(f"Pre-computed estimate {estimate_name} not found")
                        continue
                    
                    ensemble = precomputed_estimates[estimate_name]
                    pdf = np.squeeze(ensemble.pdf(z_grid))
                    mode_val = obj._get_mode(ensemble)

                    logger.debug(f"Adding pre-computed estimate 2: {estimate_name}")
                    
                    # Use consistent color scheme
                    color = self._get_estimator_color(estimate_name, is_precomputed=True)
                    
                    # Add PDF curve
                    fig.add_trace(go.Scatter(
                        x=z_grid,
                        y=pdf,
                        mode='lines',
                        name=f'Pre-computed: {estimate_name}',
                        line=dict(width=3, color=color)
                    ))

                    logger.debug(f"Adding pre-computed estimate 3: {estimate_name}")
                    # Add mode marker
                    if mode_val is not None and mode_val > 0:
                        mode_idx = np.argmin(np.abs(z_grid - mode_val))
                        fig.add_trace(go.Scatter(
                            x=[mode_val],
                            y=[pdf[mode_idx]],
                            mode='markers',
                            marker=dict(size=12, symbol='diamond', color=color),
                            name=f'Pre-computed {estimate_name} mode',
                            showlegend=False
                        ))
                    logger.debug(f"Added pre-computed estimate: {estimate_name}")
                except Exception as e:
                    logger.warning(f"Error plotting pre-computed estimate {estimate_key}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error adding pre-computed estimates to plot: {e}")
    
    def _add_live_estimates_to_plot(
        self,
        fig: go.Figure,
        obj: ObjectWrapper,
        live_selected: List[str],
        z_grid: np.ndarray,
        idx: int,
        error_scale: float,
        mag_adjustments: Dict,
        show_families: bool,
        n_samples: int
    ) -> Optional[Dict]:
        """
        Add live redshift estimates to the plot with on-the-fly calculation.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        obj : ObjectWrapper
            Object wrapper
        live_selected : List[str]
            Selected live estimator names
        z_grid : np.ndarray
            Redshift grid for PDF evaluation
        idx : int
            Current object index
        error_scale : float
            Error scaling factor
        mag_adjustments : Dict
            Magnitude adjustments
        show_families : bool
            Whether to show ensemble families
        n_samples : int
            Number of samples for ensemble families
            
        Returns
        -------
        Optional[Dict]
            Dictionary containing family sample data for spectrum/color-color plots
        """
        family_data = None
        
        try:
            logger.debug(f"Live estimators: {live_selected}")
            
            # Get base input data
            base_input_data = obj._input_data.copy()
            
            # Apply magnitude adjustments
            band_names = obj.get_band_names()
            mag_column_map = obj._parent._mag_column_map
            mag_err_column_map = obj._parent._mag_err_column_map
            
            for band in band_names:
                if band in mag_adjustments:
                    # Find the magnitude column name for this band
                    if band in mag_column_map:
                        mag_col = mag_column_map[band]
                        base_input_data[mag_col] = base_input_data[mag_col] + mag_adjustments[band]
            
            # Apply error scale
            for band in band_names:
                if band in mag_err_column_map:
                    err_col = mag_err_column_map[band]
                    base_input_data[err_col] = base_input_data[err_col] * error_scale
            
            # Build samples for family if needed
            samples_data = None
            samples_mags_list = []
            
            if show_families:
                try:
                    logger.info(f"Building samples for show_families={show_families}")
                    samples_data = ObjectWrapper.build_catalog_samples(
                        inputs_data=base_input_data,
                        band_names=band_names,
                        mag_column_map=mag_column_map,
                        mag_err_column_map=mag_err_column_map,
                        mag_err_scale=error_scale,
                        n_samples=n_samples,
                    )
                    
                    # Extract magnitude values for spectrum/color-color plotting
                    for sample_idx in range(n_samples):
                        sample_mags = []
                        for band in band_names:
                            mag_col = mag_column_map[band]
                            sample_mags.append(samples_data[mag_col][sample_idx])
                        samples_mags_list.append(sample_mags)
                    
                    logger.info(f"Built {len(samples_mags_list)} samples")
                except Exception as e:
                    logger.warning(f"Error building samples: {e}")
                    show_families = False
            
            # Store family data for spectrum and color-color plots
            if samples_mags_list:
                family_data = {'samples': samples_mags_list}
            
            for estimate_key in live_selected:
                logger.debug(f"Processing live estimator: {estimate_key}")

                try:
                    # Parse estimator name from key (format: live_estimatorname)
                    estimator_name = estimate_key.replace('live_', '')
                    
                    # Use consistent color scheme
                    color = self._get_estimator_color(estimator_name, is_precomputed=False)
                    
                    # Compute single estimate
                    try:
                        ensemble = obj.estimate_redshift(estimator_name)
                        pdf = np.squeeze(ensemble.pdf(z_grid))
                        mode_val = obj._get_mode(ensemble)
                        
                        # Add PDF curve with dashed line for live estimates
                        fig.add_trace(go.Scatter(
                            x=z_grid,
                            y=pdf,
                            mode='lines',
                            name=f'Live: {estimator_name}',
                            line=dict(width=3, color=color, dash='dash')
                        ))
                        
                        # Add mode marker
                        if mode_val is not None and mode_val > 0:
                            mode_idx = np.argmin(np.abs(z_grid - mode_val))
                            fig.add_trace(go.Scatter(
                                x=[mode_val],
                                y=[pdf[mode_idx]],
                                mode='markers',
                                marker=dict(size=10, symbol='circle', color=color),
                                name=f'Live {estimator_name} mode',
                                showlegend=False
                            ))
                        
                        logger.debug(f"Added live estimate: {estimator_name}")
                    except Exception as e:
                        logger.warning(f"Error computing single estimate for {estimator_name}: {e}")
                    
                    # Compute ensemble family if requested
                    if show_families and samples_data is not None:
                        try:
                            logger.info(f"Estimating redshifts for family: {estimator_name}")
                            
                            # Estimate redshifts for all samples
                            ensemble_family = obj.estimate_many_redshifts(
                                estimator_name, 
                                samples_data
                            )
                            logger.info(f"Got ensemble_family {ensemble_family}")
                            
                            all_pdfs = np.squeeze(ensemble_family.pdf(z_grid))
                            logger.info(f"Got all_pdfs {all_pdfs.shape}")
                            
                            # Plot each PDF in the family with reduced opacity
                            for sample_idx in range(n_samples):
                                try:
                                    # Extract single ensemble from family
                                    sample_pdf = all_pdfs[sample_idx]
                                    
                                    logger.info(f"Pdf shape {sample_pdf.shape}")
                                    
                                    fig.add_trace(go.Scatter(
                                        x=z_grid,
                                        y=sample_pdf,
                                        mode='lines',
                                        name=f'{estimator_name} family' if sample_idx == 0 else None,
                                        line=dict(width=1, color=color, dash='dot'),
                                        opacity=0.5,
                                        showlegend=(sample_idx == 0),
                                        legendgroup=f'{estimator_name}_family'
                                    ))

                                    logger.info(f"done {sample_pdf.shape}")

                                except Exception as e:
                                    logger.warning(f"Error plotting family member {sample_idx}: {e}")
                                    continue
                            
                            logger.debug(f"Added ensemble family for {estimator_name}")
                        except Exception as e:
                            logger.warning(f"Error computing ensemble family for {estimator_name}: {e}")
                    
                except Exception as e:
                    logger.warning(f"Error plotting estimate {estimate_key}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error adding live estimates to plot: {e}")
        
        return family_data
    
    def _add_true_redshift_to_plot(
        self,
        fig: go.Figure,
        obj: ObjectWrapper,
        z_range: List[float]
    ) -> None:
        """
        Add true redshift line to the plot if available.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add line to
        obj : ObjectWrapper
            Object wrapper
        z_range : List[float]
            Redshift range [min, max]
        """
        try:
            true_z = obj.get_true_redshift()
            if true_z is not None and z_range[0] <= true_z <= z_range[1]:
                fig.add_vline(
                    x=true_z,
                    line=dict(color='black', width=3, dash='dash'),
                    annotation_text='True z',
                    annotation_position='top'
                )
                logger.debug(f"Added true redshift marker at z={true_z}")
        except Exception as e:
            logger.warning(f"Error adding true redshift to plot: {e}")
    
    def run(self, debug: bool = True, port: int = 8050) -> None:
        """
        Run the Dash application.
        
        Parameters
        ----------
        debug : bool, optional
            Whether to run in debug mode, by default True
        port : int, optional
            Port number to run on, by default 8050
        """
        logger.info(f"Starting Dash server on port {port} (debug={debug})")
        try:
            self.app.run(debug=debug, port=port)
        except Exception as e:
            logger.error(f"Error running Dash application: {e}", exc_info=True)
            raise

    @classmethod
    def main(cls, catalog_name: str = "roman_rubin") -> None:
        """
        Main entry point for the application.
        
        Parameters
        ----------
        catalog_name : str, optional
            Name of the catalog to load
        
        Initializes database, loads catalog, and starts the visualizer.
        """
        logger.info("Starting CatalogRedshiftVisualizer application")
        
        # Close any existing database connections
        try:
            asyncio.run(db.close_db())
            logger.info("Closed existing database connections")
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"Could not close database (may not be open): {e}")
        except Exception as e:
            logger.error(f"Unexpected error closing database: {e}")
        
        # Initialize database
        try:
            db.init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
        
        # Load catalog configuration
        try:
            catalog_utils.load_yaml('sandbox_catalogs.yaml')
            logger.info("Loaded catalog configuration from sandbox_catalogs.yaml")
        except FileNotFoundError as e:
            logger.error("Catalog configuration file not found: sandbox_catalogs.yaml")
            raise
        except Exception as e:
            logger.error(f"Failed to load catalog configuration: {e}", exc_info=True)
            raise
        
        # Create catalog wrapper
        try:
            # You can specify which dataset
            wrapper = RailSvcCatalogWrapper(3)
            logger.info(f"Created RailSvcCatalogWrapper for '{catalog_name}'")
        except Exception as e:
            logger.error(f"Failed to create catalog wrapper: {e}", exc_info=True)
            raise
        
        # Create and run visualizer
        try:
            viz = CatalogRedshiftVisualizer(wrapper, catalog_name=catalog_name)
            viz.run(debug=True, port=8051)  # Set debug=True to see detailed logs
        except Exception as e:
            logger.error(f"Failed to run visualizer: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    # You can pass a different catalog name as a command-line argument
    import sys
    CatalogRedshiftVisualizer.main(catalog_name="sandbox")
