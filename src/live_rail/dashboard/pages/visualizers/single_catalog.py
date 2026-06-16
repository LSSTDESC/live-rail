"""Single catalog visualizer page.

Provides an interactive photo-z visualization for a selected dataset,
using the existing wrapper infrastructure.
"""

import dash
import numpy as np
import plotly.graph_objs as go
from dash import Input, Output, State, callback, dcc, html, no_update

from live_rail.backend import BackendProvider

dash.register_page(__name__, path="/visualize/single", name="Single Catalog")


def layout(dataset_id=None, **kwargs):
    initial_dataset_id = int(dataset_id) if dataset_id else None

    return html.Div(
        [
            html.H2("Single Catalog Visualizer"),
            html.Hr(),
            # Dataset selector
            html.Div(
                [
                    html.Label("Dataset"),
                    dcc.Dropdown(id="viz-s-dataset", placeholder="Select dataset...",
                                 value=initial_dataset_id),
                    html.Button(
                        "Load",
                        id="viz-s-load-btn",
                        n_clicks=0,
                        style={"marginLeft": "12px", "padding": "6px 16px"},
                    ),
                    html.Span(id="viz-s-load-status", style={"marginLeft": "12px"}),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "16px"},
            ),
            # Stores
            dcc.Store(id="viz-s-initial-dataset", data=initial_dataset_id),
            dcc.Store(id="viz-s-dataset-id", data=None),
            dcc.Store(id="viz-s-n-objects", data=0),
            # Main visualizer container (hidden until loaded)
            html.Div(id="viz-s-container", style={"display": "none"}, children=[
                # Object selection
                html.Div(
                    [
                        html.Button("< Back", id="viz-s-back-btn", n_clicks=0,
                                    style={"padding": "6px 12px", "marginRight": "12px"}),
                        html.Div(
                            [
                                dcc.Slider(id="viz-s-slider", min=0, max=1, value=0, step=1,
                                           tooltip={"placement": "bottom"}),
                            ],
                            style={"flex": "1", "minWidth": "200px"},
                        ),
                        html.Button("Next >", id="viz-s-next-btn", n_clicks=0,
                                    style={"padding": "6px 12px", "marginLeft": "12px"}),
                        html.Span(id="viz-s-counter", style={"marginLeft": "12px", "fontWeight": "bold"}),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "16px",
                           "padding": "12px", "backgroundColor": "#fafafa", "borderRadius": "4px"},
                ),
                # Plots row
                html.Div(
                    [
                        # Spectrum
                        html.Div(
                            [
                                html.H4("Photometric Spectrum"),
                                dcc.Graph(id="viz-s-spectrum", config={"responsive": True},
                                          style={"height": "300px"}),
                            ],
                            style={"flex": "1", "padding": "8px"},
                        ),
                        # Color-Color
                        html.Div(
                            [
                                html.H4("Color-Color Diagram"),
                                dcc.Graph(id="viz-s-colorcolor", config={"responsive": True},
                                          style={"height": "300px"}),
                            ],
                            style={"flex": "1", "padding": "8px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "8px"},
                ),
                # Redshift PDFs
                html.Div(
                    [
                        html.H4("Redshift Estimates"),
                        html.Div([
                            html.Label("Estimates:"),
                            dcc.Checklist(id="viz-s-estimate-checks", inline=True,
                                          style={"marginLeft": "8px"}),
                        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px",
                                  "flexWrap": "wrap"}),
                        html.Div([
                            html.Label("z range:"),
                            dcc.RangeSlider(id="viz-s-zrange", min=0, max=5, value=[0, 3],
                                            step=0.1, marks={i: str(i) for i in range(6)}),
                        ], style={"maxWidth": "400px", "marginBottom": "8px"}),
                        dcc.Graph(id="viz-s-redshift", config={"responsive": True},
                                  style={"height": "350px"}),
                    ],
                    style={"padding": "8px", "marginTop": "8px"},
                ),
            ]),
        ]
    )


# --- Callbacks ---

@callback(
    Output("viz-s-dataset", "options"),
    Input("viz-s-dataset", "id"),
)
def populate_datasets(_):
    try:
        datasets = BackendProvider.get().dataset.get_rows()
        return [{"label": f"{d.name} ({d.n_objects} obj)", "value": d.id_} for d in datasets]
    except Exception:
        return []


@callback(
    Output("viz-s-dataset-id", "data"),
    Output("viz-s-n-objects", "data"),
    Output("viz-s-container", "style"),
    Output("viz-s-slider", "max"),
    Output("viz-s-slider", "marks"),
    Output("viz-s-slider", "value"),
    Output("viz-s-load-status", "children"),
    Input("viz-s-load-btn", "n_clicks"),
    Input("viz-s-initial-dataset", "data"),
    State("viz-s-dataset", "value"),
)
def load_dataset(n_clicks, initial_dataset_id, dataset_id):
    dataset_id = dataset_id or initial_dataset_id
    if not dataset_id:
        return None, 0, {"display": "none"}, 1, {}, 0, ""

    try:
        provider = BackendProvider.get()
        ds = provider.dataset.get_row(dataset_id)
        n = ds.n_objects
        max_val = n - 1
        marks = {i: str(i) for i in range(0, n, max(1, n // 10))}
        return (
            dataset_id,
            n,
            {"display": "block"},
            max_val,
            marks,
            0,
            html.Span(f"Loaded: {ds.name}", style={"color": "green"}),
        )
    except Exception as e:
        return None, 0, {"display": "none"}, 1, {}, 0, html.Span(f"Error: {e}", style={"color": "red"})


@callback(
    Output("viz-s-slider", "value", allow_duplicate=True),
    Input("viz-s-back-btn", "n_clicks"),
    Input("viz-s-next-btn", "n_clicks"),
    State("viz-s-slider", "value"),
    State("viz-s-n-objects", "data"),
    prevent_initial_call=True,
)
def navigate_object(back_clicks, next_clicks, current, n_objects):
    ctx = dash.ctx
    if ctx.triggered_id == "viz-s-back-btn":
        return max(0, (current or 0) - 1)
    elif ctx.triggered_id == "viz-s-next-btn":
        return min((n_objects or 1) - 1, (current or 0) + 1)
    return current or 0


@callback(
    Output("viz-s-counter", "children"),
    Input("viz-s-slider", "value"),
    State("viz-s-n-objects", "data"),
)
def update_counter(idx, n_objects):
    return f"Object {(idx or 0) + 1} of {n_objects or 0}"


_wrapper_cache: dict[int, object] = {}


def _get_wrapper(dataset_id, provider):
    """Get or create the catalog wrapper for a dataset (cached)."""
    if dataset_id in _wrapper_cache:
        return _wrapper_cache[dataset_id]

    if provider.is_local:
        from live_rail.wrappers.rail_svc_wrapper import RailSvcLocalCatalogWrapper
        wrapper = RailSvcLocalCatalogWrapper(dataset_id)
    else:
        from live_rail.wrappers.rail_svc_wrapper import RailSvcRemoteCatalogWrapper
        wrapper = RailSvcRemoteCatalogWrapper(dataset_id)

    _wrapper_cache[dataset_id] = wrapper
    return wrapper


@callback(
    Output("viz-s-spectrum", "figure"),
    Output("viz-s-colorcolor", "figure"),
    Output("viz-s-estimate-checks", "options"),
    Output("viz-s-estimate-checks", "value"),
    Input("viz-s-slider", "value"),
    Input("viz-s-dataset-id", "data"),
    State("viz-s-estimate-checks", "value"),
)
def update_on_object_change(idx, dataset_id, prev_estimates):
    if not dataset_id:
        return no_update, no_update, no_update, no_update

    try:
        provider = BackendProvider.get()
        wrapper = _get_wrapper(dataset_id, provider)
        obj = wrapper.get_object(idx or 0)

        # Spectrum figure
        band_names = obj.get_band_names()
        spec = obj.get_spectrum()
        midpoints = spec["midpoints"]
        mags = spec["mags"]
        mag_errs = spec["mag_errors"]

        spectrum_fig = go.Figure()
        spectrum_fig.add_trace(go.Scatter(
            x=midpoints.tolist(), y=mags.tolist(),
            mode="markers+lines",
            error_y=dict(type="data", array=mag_errs.tolist(), visible=True),
            name="Magnitudes",
            text=band_names,
            hovertemplate="%{text}<br>%{y:.2f} mag<extra></extra>",
        ))
        spectrum_fig.update_layout(
            xaxis_title="Wavelength (nm)", yaxis_title="Magnitude",
            yaxis_autorange="reversed", template="plotly_white",
            margin=dict(t=10, b=40, l=50, r=10),
            showlegend=False,
        )

        # Color-color: plot all adjacent pairs
        colors = obj.get_colors()
        color_names = list(colors.keys())
        color_vals = [colors[c][0] for c in color_names]
        color_fig = _build_color_color_figure(color_names, color_vals)

        # Estimate options — preserve previous selections
        estimate_names = obj.get_estimate_names()
        est_opts = [{"label": n, "value": n} for n in estimate_names]
        if prev_estimates:
            est_values = [e for e in prev_estimates if e in estimate_names]
        else:
            est_values = estimate_names

        return spectrum_fig, color_fig, est_opts, est_values

    except Exception as e:
        empty_fig = go.Figure()
        empty_fig.add_annotation(text=f"Error: {e}", showarrow=False)
        return empty_fig, go.Figure(), [], []


def _build_color_color_figure(color_names: list[str], color_vals: list[float]) -> go.Figure:
    """Build a color-color diagram showing all adjacent color pairs."""
    fig = go.Figure()

    if len(color_names) < 2:
        return fig

    # Each point is (color_i, color_i+1) for adjacent pairs
    x_vals = []
    y_vals = []
    labels = []
    for i in range(len(color_names) - 1):
        x = np.clip(float(color_vals[i]), -1, 2)
        y = np.clip(float(color_vals[i + 1]), -1, 2)
        x_vals.append(x)
        y_vals.append(y)
        labels.append(f"{color_names[i]} vs {color_names[i + 1]}")

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode="markers+lines+text",
        marker=dict(size=10, color=list(range(len(x_vals))),
                    colorscale="Viridis", showscale=False),
        line=dict(color="gray", width=1, dash="dot"),
        text=[cn.split(" - ")[0] if " - " in cn else cn[:3] for cn in color_names[:-1]],
        textposition="top center",
        textfont=dict(size=9),
        hovertext=labels,
        hoverinfo="text+x+y",
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(title="Color[i]", range=[-1, 2]),
        yaxis=dict(title="Color[i+1]", range=[-1, 2]),
        template="plotly_white",
        margin=dict(t=10, b=40, l=50, r=10),
    )
    return fig


@callback(
    Output("viz-s-redshift", "figure"),
    Input("viz-s-estimate-checks", "value"),
    Input("viz-s-zrange", "value"),
    Input("viz-s-slider", "value"),
    State("viz-s-dataset-id", "data"),
)
def update_redshift(selected_estimates, zrange, idx, dataset_id):
    if not dataset_id:
        return go.Figure()

    try:
        provider = BackendProvider.get()
        wrapper = _get_wrapper(dataset_id, provider)
        obj = wrapper.get_object(idx or 0)

        zgrid = np.linspace(zrange[0], zrange[1], 301)
        estimates = obj.get_redshift_estimates()

        fig = go.Figure()
        palette = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#f781bf"]

        for i, name in enumerate(selected_estimates or []):
            if name in estimates:
                ensemble = estimates[name]
                try:
                    pdf_vals = np.squeeze(ensemble.pdf(zgrid))
                    fig.add_trace(go.Scatter(
                        x=zgrid.tolist(), y=pdf_vals.tolist(),
                        mode="lines", name=name,
                        line=dict(color=palette[i % len(palette)]),
                    ))
                except Exception:
                    pass

        # True redshift marker
        true_z = obj.get_true_redshift()
        if true_z is not None and not np.isnan(true_z):
            fig.add_vline(x=float(true_z), line_dash="dash", line_color="gray",
                          annotation_text="true z")

        fig.update_layout(
            xaxis_title="Redshift", yaxis_title="p(z)",
            template="plotly_white", margin=dict(t=10, b=40, l=50, r=10),
        )
        return fig
    except Exception:
        return go.Figure()
