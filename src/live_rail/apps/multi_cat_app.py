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

from live_rail.wrappers.object_wrapper import MultiCatalogWrapper
from live_rail.wrappers.rail_svc_wrapper import RailSvcSimpleMultiCatalogWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiCatalogRedshiftVisualizer:
    # Style constants
    CONTROL_STYLE = {
        'width': '20%',
        'minWidth': '150px',
        'paddingRight': '10px',
        'boxSizing': 'border-box',
        'overflowY': 'auto'
    }
    
    PLOT_STYLE = {
        'width': '80%',
        'boxSizing': 'border-box'
    }
    
    PANEL_CONTAINER_STYLE = {
        'display': 'flex',
        'height': 'calc(100% - 40px)',
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
    
    def __init__(self, catalog_wrapper: MultiCatalogWrapper):
        """
        Initialize the visualizer with a MultiCatalogWrapper instance.
        
        Parameters
        ----------
        catalog_wrapper : MultiCatalogWrapper
            The wrapper containing multiple catalogs
        """
        logger.info("Initializing MultiCatalogRedshiftVisualizer with {catalog_wrapper}")
        self.catalog = catalog_wrapper
        self.app = dash.Dash(__name__)
        self.current_object_idx = 0
        self.n_objects = self.catalog.get_nobjects()
        
        # Get catalog names for selection controls
        self.catalog_names = list(self.catalog._catalogs.keys())
        logger.info(f"Loaded {len(self.catalog_names)} catalogs with {self.n_objects} objects")
        
        self.setup_layout()
        self.setup_callbacks()
    
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
                    style={'height': '100%'},
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
            html.H1("Multi-Catalog Redshift Explorer", 
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
                self._create_object_selection_panel(),
                
                # Middle row: Spectrum and Color-Color side by side
                html.Div([
                    # Pane 2: Spectrum (left)
                    self._create_spectrum_panel(),
                    
                    # Pane 3: Color-Color Diagram (right)
                    self._create_color_color_panel()
                ], style={
                    'display': 'flex',
                    'gap': '10px',
                    'padding': '10px',
                    'height': '40vh',
                    'minHeight': '300px',
                    'flexWrap': 'wrap'
                }),
                
                # Pane 4: Redshift Estimates (bottom)
                self._create_redshift_panel()
            ], style={
                'height': 'calc(100vh - 84px)',
                'overflow': 'auto',
                'display': 'flex',
                'flexDirection': 'column'
            }),
            
            # Use dcc.Store for state management
            dcc.Store(id='current-object-idx', data=self.current_object_idx)
        ], style={
            'margin': '0',
            'padding': '0',
            'height': '100vh',
            'overflow': 'hidden',
            'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        })
    
    def _create_object_selection_panel(self) -> html.Div:
        """Create the object selection panel."""
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
            'padding': '20px',
            'backgroundColor': '#fafafa',
            'borderBottom': '1px solid #ddd'
        })
    
    def _create_spectrum_panel(self) -> html.Div:
        """Create the spectrum visualization panel."""
        controls = html.Div([
            html.Label("Show Catalogs:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Checklist(
                id='spectrum-catalog-checklist',
                options=[{'label': name, 'value': name} for name in self.catalog_names],
                value=self.catalog_names,  # All selected by default
                inline=False,
                style={'marginBottom': '10px'}
            )
        ])
        
        return self._create_panel(
            title="Photometric Spectrum",
            controls=controls,
            plot_id='spectrum-plot',
            border_color=self.SPECTRUM_BORDER_COLOR,
            additional_style={
                'flex': '1',
                'minWidth': '400px'
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
                'minWidth': '400px'
            }
        )
    
    def _create_redshift_panel(self) -> html.Div:
        """Create the redshift estimates panel."""
        controls = self._create_redshift_controls()
        
        return self._create_panel(
            title="Redshift Estimates",
            controls=controls,
            plot_id='redshift-plot',
            border_color=self.REDSHIFT_BORDER_COLOR,
            additional_style={
                'margin': '10px',
                'height': 'calc(50vh - 20px)',
                'minHeight': '300px'
            }
        )
    
    def _create_color_controls(self) -> html.Div:
        """Create controls for color-color diagram."""
        return html.Div([
            html.Label("Select Catalog:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='color-catalog-dropdown',
                options=[{'label': name, 'value': name} for name in self.catalog_names],
                value=self.catalog_names[0] if self.catalog_names else None,
                style={'marginBottom': 10}
            ),
            html.Label("X-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-x-dropdown', style={'marginBottom': 10}),
            html.Label("Y-axis Color:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(id='color-y-dropdown', style={'marginBottom': 10}),
        ])
    
    def _create_redshift_controls(self) -> html.Div:
        """Create controls for redshift display."""
        return html.Div([
            html.Div([
                html.Label("Combined Estimates:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                dcc.Checklist(
                    id='combined-estimate-checklist',
                    inline=False,
                    style={'marginBottom': 15}
                ),
            ]),
            html.Hr(style={'margin': '10px 0'}),
            html.Div([
                html.Label("Individual Catalog Estimates:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.Div(id='catalog-estimate-checklists-container')
            ]),
            html.Hr(style={'margin': '10px 0'}),
            html.Label("Redshift Grid Range:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
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
        logger.info("Setting up callbacks")
        
        @self.app.callback(
            [Output('current-object-idx', 'data'),
             Output('object-slider', 'value')],
            [Input('back-button', 'n_clicks'),
             Input('next-button', 'n_clicks'),
             Input('object-slider', 'value')],
            [State('current-object-idx', 'data')],
            prevent_initial_call=False  # Allow initial call to set up state
        )
        def update_object_idx(
            back_clicks: int, 
            next_clicks: int, 
            slider_value: int, 
            current_idx: Optional[int]
        ) -> Tuple[int, int]:
            """
            Update the current object index based on navigation controls

            Parameters
            ----------
            back_clicks : int
                Number of back button clicks
            next_clicks : int
                Number of next button clicks
            slider_value : int
                Current slider value
            current_idx : Optional[int]
                Current object index from store
                
            Returns
            -------
            Tuple[int, int]
                New index for store and slider
            """
            # Handle initial call or None value
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
            """
            Update navigation button states and counter display.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
                
            Returns
            -------
            Tuple[bool, bool, str]
                Back button disabled state, next button disabled state, counter text
            """
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
            [Output('color-x-dropdown', 'options'),
             Output('color-y-dropdown', 'options'),
             Output('color-x-dropdown', 'value'),
             Output('color-y-dropdown', 'value')],
            [Input('current-object-idx', 'data'),
             Input('color-catalog-dropdown', 'value')]
        )
        def update_color_dropdowns(
            idx: Optional[int], 
            catalog_name: Optional[str]
        ) -> Tuple[List[Dict], List[Dict], Optional[str], Optional[str]]:
            """
            Update color dropdown options based on selected catalog.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
            catalog_name : Optional[str]
                Selected catalog name
                
            Returns
            -------
            Tuple[List[Dict], List[Dict], Optional[str], Optional[str]]
                X options, Y options, X default value, Y default value
            """
            if idx is None:
                idx = 0
                
            if not catalog_name:
                logger.debug("No catalog selected for color dropdowns")
                return [], [], None, None
            
            try:
                multi_obj = self.catalog.get_wrapper(idx)
                logger.info(f"Got 2 {multi_obj}")

                if multi_obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return [], [], None, None
                
                catalog_obj = multi_obj.objects.get(catalog_name)
                if not catalog_obj:
                    logger.warning(f"Catalog {catalog_name} not found for object {idx}")
                    return [], [], None, None
                
                colors = catalog_obj.get_colors()
                color_names = list(colors.keys())
                
                options = [{'label': name, 'value': name} for name in color_names]
                default_x = color_names[0] if len(color_names) > 0 else None
                default_y = color_names[1] if len(color_names) > 1 else default_x
                
                logger.debug(f"Updated color dropdowns for {catalog_name}: {len(color_names)} colors")
                return options, options, default_x, default_y
            except Exception as e:
                logger.error(f"Error updating color dropdowns: {e}", exc_info=True)
                return [], [], None, None
        
        @self.app.callback(
            [Output('combined-estimate-checklist', 'options'),
             Output('combined-estimate-checklist', 'value'),
             Output('catalog-estimate-checklists-container', 'children')],
            Input('current-object-idx', 'data')
        )
        def update_redshift_checklists(
            idx: Optional[int]
        ) -> Tuple[List[Dict], List[str], List[html.Div]]:
            """
            Update redshift estimate checklists for combined and individual catalogs.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
                
            Returns
            -------
            Tuple[List[Dict], List[str], List[html.Div]]
                Combined options, combined values, catalog checklist components
            """
            if idx is None:
                idx = 0
                
            try:
                # Get combined estimates
                combined_names = self.catalog.get_estimate_names()
                combined_options = [{'label': name, 'value': f'combined_{name}'} 
                                  for name in combined_names]
                combined_values = [f'combined_{name}' for name in combined_names]
                
                # Create checklists for each catalog
                catalog_checklists = []
                for cat_name in self.catalog_names:
                    try:
                        catalog = self.catalog.get_catalog(cat_name)
                        estimate_names = catalog.get_estimate_names()
                        
                        if estimate_names:
                            catalog_checklists.append(
                                html.Div([
                                    html.Label(
                                        f"{cat_name}:",
                                        style={'fontWeight': 'bold', 'fontSize': '12px', 'marginTop': '5px'}
                                    ),
                                    dcc.Checklist(
                                        id={'type': 'catalog-estimate-checklist', 'catalog': cat_name},
                                        options=[{'label': name, 'value': f'{cat_name}_{name}'} 
                                                for name in estimate_names],
                                        value=[f'{cat_name}_{name}' for name in estimate_names],
                                        inline=False,
                                        style={'fontSize': '11px', 'marginLeft': '10px'}
                                    )
                                ], style={'marginBottom': '10px'})
                            )
                    except Exception as e:
                        logger.warning(f"Error processing catalog {cat_name}: {e}")
                        continue
                
                logger.debug(f"Updated redshift checklists: {len(combined_names)} combined, "
                           f"{len(catalog_checklists)} catalogs")
                return combined_options, combined_values, catalog_checklists
            except Exception as e:
                logger.error(f"Error updating redshift checklists: {e}", exc_info=True)
                return [], [], []
        
        @self.app.callback(
            Output('spectrum-plot', 'figure'),
            [Input('current-object-idx', 'data'),
             Input('spectrum-catalog-checklist', 'value')]
        )
        def update_spectrum(
            idx: Optional[int], 
            selected_catalogs: Optional[List[str]]
        ) -> go.Figure:
            """
            Update the spectrum plot for selected catalogs.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
            selected_catalogs : Optional[List[str]]
                List of selected catalog names
                
            Returns
            -------
            go.Figure
                Plotly figure with spectrum data
            """
            if idx is None:
                idx = 0
                
            if not selected_catalogs:
                logger.debug("No catalogs selected for spectrum")
                return go.Figure()
            
            try:
                logger.info(f"Updating spectrum plot for object {idx} with catalogs: {selected_catalogs}")
                multi_obj = self.catalog.get_wrapper(idx)
                logger.info(f"Got 3 {multi_obj}")

                if multi_obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure()
                
                fig = go.Figure()
                colors = px.colors.qualitative.Plotly
                
                for i, cat_name in enumerate(selected_catalogs):
                    try:
                        catalog_obj = multi_obj._objects.get(cat_name)
                        if not catalog_obj:
                            logger.warning(f"Catalog {cat_name} not found for object {idx}")
                            continue
                        
                        spectrum_data = catalog_obj.get_spectrum()
                        wavelengths = spectrum_data['midpoints']
                        mags = spectrum_data['mags'].copy()
                        mag_errors = spectrum_data['mag_errors']
                        
                        color = colors[i % len(colors)]
                        
                        fig.add_trace(go.Scatter(
                            x=wavelengths,
                            y=mags,
                            error_y=dict(type='data', array=mag_errors),
                            mode='markers+lines',
                            name=cat_name,
                            marker=dict(size=10, color=color),
                            line=dict(width=2, color=color),
                        ))
                        logger.debug(f"Added spectrum trace for {cat_name}")
                    except Exception as e:
                        logger.warning(f"Error plotting spectrum for {cat_name}: {e}")
                        continue
                
                fig.update_layout(
                    xaxis_title='Wavelength (Å)',
                    yaxis_title='Magnitude (AB)',
                    yaxis_autorange='reversed',
                    hovermode='closest',
                    template='plotly_white',
                    height=400,
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
             Input('color-catalog-dropdown', 'value'),
             Input('color-x-dropdown', 'value'),
             Input('color-y-dropdown', 'value')]
        )
        def update_color_color(
            idx: Optional[int], 
            catalog_name: Optional[str], 
            x_color: Optional[str], 
            y_color: Optional[str]
        ) -> go.Figure:
            """
            Update the color-color diagram.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
            catalog_name : Optional[str]
                Selected catalog name
            x_color : Optional[str]
                X-axis color selection
            y_color : Optional[str]
                Y-axis color selection
                
            Returns
            -------
            go.Figure
                Plotly figure with color-color plot
            """
            if idx is None:
                idx = 0
                
            if not catalog_name or not x_color or not y_color:
                return go.Figure()
            
            try:
                logger.info(f"Updating color-color plot: {x_color} vs {y_color} for {catalog_name}")
                multi_obj = self.catalog.get_wrapper(idx)
                logger.info(f"Got 4 {multi_obj}")

                if multi_obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure()
                
                catalog_obj = multi_obj._objects.get(catalog_name)
                if not catalog_obj:
                    logger.warning(f"Catalog {catalog_name} not found for object {idx}")
                    return go.Figure()
                
                colors = catalog_obj.get_colors()
                
                x_val, x_err = colors.get(x_color, (0, 0))
                y_val, y_err = colors.get(y_color, (0, 0))
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=[x_val],
                    y=[y_val],
                    error_x=dict(type='data', array=[x_err]),
                    error_y=dict(type='data', array=[y_err]),
                    mode='markers',
                    marker=dict(size=15, color='red'),
                    name=f'Selected Object ({catalog_name})',
                ))
                
                fig.update_xaxes(range=[-3, 3])
                fig.update_yaxes(range=[-3, 3])
                
                fig.update_layout(
                    xaxis_title=x_color,
                    yaxis_title=y_color,
                    hovermode='closest',
                    template='plotly_white',
                    height=400
                )
                
                logger.info(f"Successfully updated color-color plot")
                return fig
            except Exception as e:
                logger.error(f"Error updating color-color plot: {e}", exc_info=True)
                return go.Figure()
        
        @self.app.callback(
            Output('redshift-plot', 'figure'),
            [Input('current-object-idx', 'data'),
             Input('combined-estimate-checklist', 'value'),
             Input({'type': 'catalog-estimate-checklist', 'catalog': ALL}, 'value'),
             Input('redshift-range', 'value')],
            [State({'type': 'catalog-estimate-checklist', 'catalog': ALL}, 'id')]
        )
        def update_redshift_plot(
            idx: Optional[int],
            combined_selected: Optional[List[str]],
            catalog_selected_list: List[List[str]],
            z_range: List[float],
            catalog_ids: List[Dict]
        ) -> go.Figure:
            """
            Update the redshift probability distribution plot.
            
            Parameters
            ----------
            idx : Optional[int]
                Current object index
            combined_selected : Optional[List[str]]
                Selected combined estimates
            catalog_selected_list : List[List[str]]
                Selected estimates for each catalog
            z_range : List[float]
                Redshift range [min, max]
            catalog_ids : List[Dict]
                Catalog identifier dictionaries
                
            Returns
            -------
            go.Figure
                Plotly figure with redshift distributions
            """
            if idx is None:
                idx = 0
            try:
                logger.info(f"Updating redshift plot for object {idx} {self.catalog}")
                multi_obj = self.catalog.get_wrapper(idx)

                logger.info(f"Got 1 {multi_obj}")

                if multi_obj is None:
                    logger.warning(f"Could not retrieve object at index {idx}")
                    return go.Figure()
                
                # Create redshift grid
                z_grid = np.linspace(z_range[0], z_range[1], 500)
                
                fig = go.Figure()
                
                # Plot combined estimates
                if combined_selected:
                    self._add_combined_estimates_to_plot(
                        fig, multi_obj, combined_selected, z_grid, idx
                    )
                
                # Plot individual catalog estimates
                if catalog_selected_list and catalog_ids:
                    self._add_catalog_estimates_to_plot(
                        fig, multi_obj, catalog_selected_list, catalog_ids, z_grid, idx
                    )
                
                # Add true redshift if available
                self._add_true_redshift_to_plot(fig, multi_obj, z_range)
                
                fig.update_layout(
                    xaxis_title='Redshift',
                    yaxis_title='Probability Density',
                    hovermode='x unified',
                    template='plotly_white',
                    height=400,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="right",
                        x=0.99,
                        bgcolor="rgba(255,255,255,0.8)"
                    )
                )
                
                logger.info(f"Successfully updated redshift plot for object {idx}")
                return fig
            except Exception as e:
                logger.error(f"Error updating redshift plot: {e}", exc_info=True)
                return go.Figure()
    
    def _add_combined_estimates_to_plot(
        self,
        fig: go.Figure,
        multi_obj: Any,
        combined_selected: List[str],
        z_grid: np.ndarray,
        idx: int
    ) -> None:
        """
        Add combined redshift estimates to the plot.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        multi_obj : Any
            Multi-catalog object
        combined_selected : List[str]
            Selected combined estimate names
        z_grid : np.ndarray
            Redshift grid for PDF evaluation
        idx : int
            Current object index
        """

        
        try:
            logger.info(f"starting loop: {idx}")

            combined_estimates = multi_obj.get_redshift_estimates()
            combined_colors = px.colors.qualitative.Dark24

            logger.info(f"starting loop: {combined_selected}")

            
            for i, estimate_key in enumerate(combined_selected):
                
                try:
                    logger.debug(f"Adding 1 combined estimate: {estimate_key}")

                    estimate_name = estimate_key.replace('combined_', '')
                    if estimate_name not in combined_estimates:
                        logger.warning(f"Combined estimate {estimate_name} not found")
                        continue
                    
                    ensemble = combined_estimates[estimate_name]
                    pdf = np.squeeze(ensemble.pdf(z_grid))
                    mode_val = multi_obj._get_mode(ensemble)

                    logger.debug(f"Adding 2 combined estimate: {estimate_name}")
                    
                    color = combined_colors[i % len(combined_colors)]
                    
                    # Add PDF curve
                    fig.add_trace(go.Scatter(
                        x=z_grid,
                        y=pdf,
                        mode='lines',
                        name=f'Combined: {estimate_name}',
                        line=dict(width=3, color=color)
                    ))

                    logger.debug(f"Adding 3 combined estimate: {estimate_name}")
                    
                    # Add mode marker
                    if mode_val is not None and mode_val > 0:
                        mode_idx = np.argmin(np.abs(z_grid - mode_val))
                        fig.add_trace(go.Scatter(
                            x=[mode_val],
                            y=[pdf[mode_idx]],
                            mode='markers',
                            marker=dict(size=12, symbol='diamond', color=color),
                            name=f'Combined {estimate_name} mode',
                            showlegend=False
                        ))
                    logger.debug(f"Added combined estimate: {estimate_name}")
                except Exception as e:
                    logger.warning(f"Error plotting combined estimate {estimate_key}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error adding combined estimates to plot: {e}")
    
    def _add_catalog_estimates_to_plot(
        self,
        fig: go.Figure,
        multi_obj: Any,
        catalog_selected_list: List[List[str]],
        catalog_ids: List[Dict],
        z_grid: np.ndarray,
        idx: int
    ) -> None:
        """
        Add individual catalog redshift estimates to the plot.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add traces to
        multi_obj : Any
            Multi-catalog object
        catalog_selected_list : List[List[str]]
            Selected estimates for each catalog
        catalog_ids : List[Dict]
            Catalog identifier dictionaries
        z_grid : np.ndarray
            Redshift grid for PDF evaluation
        idx : int
            Current object index
        """
        try:
            catalog_colors = px.colors.qualitative.Light24
            color_idx = 0

            logging.debug(f"{catalog_ids}")

            for catalog_selected, catalog_id in zip(catalog_selected_list, catalog_ids):

                logging.debug(f"{catalog_selected}, {catalog_id}")
                if not catalog_selected:
                    continue
                
                try:
                    cat_name = catalog_id['catalog']
                    catalog_obj = multi_obj._objects.get(cat_name)
                    
                    if not catalog_obj:
                        logger.warning(f"Catalog {cat_name} not found for object {idx}")
                        continue
                    
                    catalog_estimates = catalog_obj.get_redshift_estimates()
                    
                    for estimate_key in catalog_selected:
                        logging.debug(f"{catalog_selected}, {estimate_key}")

                        try:
                            # Parse estimate name from key (format: catalog_estimatename)
                            estimate_name = estimate_key.replace(f'{cat_name}_', '')
                            
                            if estimate_name not in catalog_estimates:
                                logger.warning(f"Estimate {estimate_name} not found in {cat_name}")
                                continue
                            
                            ensemble = catalog_estimates[estimate_name]
                            pdf = np.squeeze(ensemble.pdf(z_grid))
                            mode_val = catalog_obj._get_mode(ensemble)
                            
                            color = catalog_colors[color_idx % len(catalog_colors)]
                            color_idx += 1
                            
                            # Add PDF curve with dashed line for catalog estimates
                            fig.add_trace(go.Scatter(
                                x=z_grid,
                                y=pdf,
                                mode='lines',
                                name=f'{cat_name}: {estimate_name}',
                                line=dict(width=2, color=color, dash='dash')
                            ))
                            
                            # Add mode marker
                            if mode_val is not None and mode_val > 0:
                                mode_idx = np.argmin(np.abs(z_grid - mode_val))
                                fig.add_trace(go.Scatter(
                                    x=[mode_val],
                                    y=[pdf[mode_idx]],
                                    mode='markers',
                                    marker=dict(size=8, symbol='circle', color=color),
                                    name=f'{cat_name} {estimate_name} mode',
                                    showlegend=False
                                ))
                            logger.debug(f"Added catalog estimate: {cat_name} - {estimate_name}")
                        except Exception as e:
                            logger.warning(f"Error plotting estimate {estimate_key}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error processing catalog estimates: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error adding catalog estimates to plot: {e}")
    
    def _add_true_redshift_to_plot(
        self,
        fig: go.Figure,
        multi_obj: Any,
        z_range: List[float]
    ) -> None:
        """
        Add true redshift line to the plot if available.
        
        Parameters
        ----------
        fig : go.Figure
            Plotly figure to add line to
        multi_obj : Any
            Multi-catalog object
        z_range : List[float]
            Redshift range [min, max]
        """
        try:
            true_z = multi_obj.get_true_redshift()
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
    def main(cls) -> None:
        """
        Main entry point for the application.
        
        Initializes database, loads catalogs, and starts the visualizer.
        """
        logger.info("Starting MultiCatalogRedshiftVisualizer application")
        
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
            wrapper = RailSvcSimpleMultiCatalogWrapper(3)
            logger.info("Created RailSvcSimpleMultiCatalogWrapper with 3 objects")
        except Exception as e:
            logger.error(f"Failed to create catalog wrapper: {e}", exc_info=True)
            raise
        
        # Create and run visualizer
        try:
            viz = MultiCatalogRedshiftVisualizer(wrapper)
            viz.run(debug=True, port=8051)  # Set debug=True to see detailed logs
        except Exception as e:
            logger.error(f"Failed to run visualizer: {e}", exc_info=True)
            raise

        
if __name__ == '__main__':
    MultiCatalogRedshiftVisualizer.main()
