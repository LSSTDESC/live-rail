"""Multi catalog visualizer page.

Provides cross-catalog photo-z comparison for matched (collection) datasets.
Same layout as single catalog: spectrum + color-color on top, redshift below.
"""

import dash
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from dash import Input, Output, State, callback, dcc, html

from live_rail.backend import BackendProvider
from live_rail.wrappers.rail_svc_wrapper import RailSvcLocalCatalogWrapper, RailSvcRemoteCatalogWrapper

dash.register_page(__name__, path="/visualize/multi", name="Multi Catalog")


def layout(dataset_id=None, **kwargs):
    initial_dataset_id = int(dataset_id) if dataset_id else None

    return html.Div(
        [
            html.H2("Multi Catalog Visualizer"),
            html.Hr(),
            # Dataset selector (collections only)
            html.Div(
                [
                    html.Label("Matched Dataset (collection)"),
                    dcc.Dropdown(
                        id="viz-m-dataset", placeholder="Select matched dataset...", value=initial_dataset_id
                    ),
                    html.Button(
                        "Load",
                        id="viz-m-load-btn",
                        n_clicks=0,
                        style={"marginLeft": "12px", "padding": "6px 16px"},
                    ),
                    html.Span(id="viz-m-load-status", style={"marginLeft": "12px"}),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "16px"},
            ),
            # Stores
            dcc.Store(id="viz-m-initial-dataset", data=initial_dataset_id),
            dcc.Store(id="viz-m-dataset-id", data=None),
            dcc.Store(id="viz-m-n-objects", data=0),
            dcc.Store(id="viz-m-catalog-names", data=[]),
            # Main container (hidden until loaded)
            html.Div(
                id="viz-m-container",
                style={"display": "none"},
                children=[
                    # Object navigation
                    html.Div(
                        [
                            html.Button(
                                "< Back",
                                id="viz-m-back-btn",
                                n_clicks=0,
                                style={"padding": "6px 12px", "marginRight": "12px"},
                            ),
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="viz-m-slider",
                                        min=0,
                                        max=1,
                                        value=0,
                                        step=1,
                                        tooltip={"placement": "bottom"},
                                    )
                                ],
                                style={"flex": "1", "minWidth": "200px"},
                            ),
                            html.Button(
                                "Next >",
                                id="viz-m-next-btn",
                                n_clicks=0,
                                style={"padding": "6px 12px", "marginLeft": "12px"},
                            ),
                            html.Span(id="viz-m-counter", style={"marginLeft": "12px", "fontWeight": "bold"}),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "marginBottom": "16px",
                            "padding": "12px",
                            "backgroundColor": "#fafafa",
                            "borderRadius": "4px",
                        },
                    ),
                    # Top row: Spectrum + Color-Color side by side
                    html.Div(
                        [
                            # Spectrum
                            html.Div(
                                [
                                    html.H4("Photometric Spectra"),
                                    dcc.Dropdown(id="viz-m-catalog-select", style={"display": "none"}),
                                    dcc.Graph(
                                        id="viz-m-spectrum",
                                        config={"responsive": True},
                                        style={"height": "300px"},
                                    ),
                                ],
                                style={"flex": "1", "padding": "8px"},
                            ),
                            # Color-Color
                            html.Div(
                                [
                                    html.H4("Color-Color Diagram"),
                                    dcc.Graph(
                                        id="viz-m-colorcolor",
                                        config={"responsive": True},
                                        style={"height": "300px"},
                                    ),
                                ],
                                style={"flex": "1", "padding": "8px"},
                            ),
                        ],
                        style={"display": "flex", "gap": "8px"},
                    ),
                    # Bottom: Redshift estimates
                    html.Div(
                        [
                            html.H4("Combined Redshift Estimates"),
                            html.Div(
                                [
                                    html.Label("Estimates:"),
                                    dcc.Checklist(
                                        id="viz-m-estimate-checks", inline=True, style={"marginLeft": "8px"}
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "marginBottom": "8px",
                                    "flexWrap": "wrap",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label("z range:"),
                                    dcc.RangeSlider(
                                        id="viz-m-zrange",
                                        min=0,
                                        max=5,
                                        value=[0, 3],
                                        step=0.1,
                                        marks={i: str(i) for i in range(6)},
                                    ),
                                ],
                                style={"maxWidth": "400px", "marginBottom": "8px"},
                            ),
                            dcc.Graph(
                                id="viz-m-redshift", config={"responsive": True}, style={"height": "350px"}
                            ),
                        ],
                        style={"padding": "8px", "marginTop": "8px"},
                    ),
                ],
            ),
        ]
    )


# --- Callbacks ---


@callback(
    Output("viz-m-dataset", "options"),
    Input("viz-m-dataset", "id"),
)
def populate_datasets(_):
    try:
        datasets = BackendProvider.get().dataset.get_rows()
        return [
            {"label": f"{d.name} ({d.n_objects} obj)", "value": d.id_} for d in datasets if d.is_collection
        ]
    except Exception:
        return []


@callback(
    Output("viz-m-dataset-id", "data"),
    Output("viz-m-n-objects", "data"),
    Output("viz-m-catalog-names", "data"),
    Output("viz-m-container", "style"),
    Output("viz-m-slider", "max"),
    Output("viz-m-slider", "marks"),
    Output("viz-m-slider", "value"),
    Output("viz-m-catalog-select", "options"),
    Output("viz-m-catalog-select", "value"),
    Output("viz-m-load-status", "children"),
    Input("viz-m-load-btn", "n_clicks"),
    Input("viz-m-initial-dataset", "data"),
    State("viz-m-dataset", "value"),
)
def load_dataset(n_clicks, initial_dataset_id, dataset_id):
    dataset_id = dataset_id or initial_dataset_id
    if not dataset_id:
        return None, 0, [], {"display": "none"}, 1, {}, 0, [], None, ""

    try:
        provider = BackendProvider.get()
        assocs = provider.dataset_assoc.find_by(matched_dataset_id=dataset_id)
        catalog_names = []
        for a in assocs:
            comp = provider.dataset.get_row(a.component_dataset_id)
            catalog_names.append(comp.name)

        ds = provider.dataset.get_row(dataset_id)
        n = ds.n_objects
        max_val = n - 1
        marks = {i: str(i) for i in range(0, n, max(1, n // 10))}
        cat_opts = [{"label": c, "value": c} for c in catalog_names]
        first_cat = catalog_names[0] if catalog_names else None

        return (
            dataset_id,
            n,
            catalog_names,
            {"display": "block"},
            max_val,
            marks,
            0,
            cat_opts,
            first_cat,
            html.Span(f"Loaded: {ds.name} ({len(catalog_names)} catalogs)", style={"color": "green"}),
        )
    except Exception as e:
        return (
            None,
            0,
            [],
            {"display": "none"},
            1,
            {},
            0,
            [],
            None,
            html.Span(f"Error: {e}", style={"color": "red"}),
        )


@callback(
    Output("viz-m-slider", "value", allow_duplicate=True),
    Input("viz-m-back-btn", "n_clicks"),
    Input("viz-m-next-btn", "n_clicks"),
    State("viz-m-slider", "value"),
    State("viz-m-n-objects", "data"),
    prevent_initial_call=True,
)
def navigate(back_clicks, next_clicks, current, n_objects):
    ctx = dash.ctx
    if ctx.triggered_id == "viz-m-back-btn":
        return max(0, (current or 0) - 1)
    elif ctx.triggered_id == "viz-m-next-btn":
        return min((n_objects or 1) - 1, (current or 0) + 1)
    return current or 0


@callback(
    Output("viz-m-counter", "children"),
    Input("viz-m-slider", "value"),
    State("viz-m-n-objects", "data"),
)
def update_counter(idx, n_objects):
    return f"Object {(idx or 0) + 1} of {n_objects or 0}"


_component_wrapper_cache: dict[int, object] = {}


def _get_component_wrapper(dataset_id, provider):
    """Get or create a single-catalog wrapper for a component dataset (cached)."""
    if dataset_id in _component_wrapper_cache:
        return _component_wrapper_cache[dataset_id]

    if provider.is_local:
        wrapper = RailSvcLocalCatalogWrapper(dataset_id)
    else:
        wrapper = RailSvcRemoteCatalogWrapper(dataset_id)

    _component_wrapper_cache[dataset_id] = wrapper
    return wrapper


def _get_first_component(dataset_id, provider):
    """Get the first component wrapper for a matched dataset."""
    assocs = provider.dataset_assoc.find_by(matched_dataset_id=dataset_id)
    if not assocs:
        return None
    comp = provider.dataset.get_row(assocs[0].component_dataset_id)
    return _get_component_wrapper(comp.id_, provider)


@callback(
    Output("viz-m-spectrum", "figure"),
    Output("viz-m-colorcolor", "figure"),
    Output("viz-m-estimate-checks", "options"),
    Output("viz-m-estimate-checks", "value"),
    Input("viz-m-slider", "value"),
    Input("viz-m-dataset-id", "data"),
    State("viz-m-estimate-checks", "value"),
)
def update_spectrum_and_colors(idx, dataset_id, prev_estimates):
    if not dataset_id:
        return go.Figure(), go.Figure(), [], []

    try:
        provider = BackendProvider.get()
        assocs = provider.dataset_assoc.find_by(matched_dataset_id=dataset_id)
        palette = px.colors.qualitative.Plotly

        spectrum_fig = go.Figure()
        color_fig = go.Figure()
        combined_estimate_names = []
        component_estimate_names = []

        # Combined (matched) dataset estimates
        matched_ds = provider.dataset.get_row(dataset_id)
        matched_wrapper = _get_component_wrapper(dataset_id, provider)
        matched_obj = matched_wrapper.get_object(idx or 0)
        for est_name in matched_obj.get_estimate_names():
            label = f"{matched_ds.name}/{est_name}"
            if label not in combined_estimate_names:
                combined_estimate_names.append(label)

        for i, assoc in enumerate(assocs):
            comp = provider.dataset.get_row(assoc.component_dataset_id)
            wrapper = _get_component_wrapper(comp.id_, provider)
            obj = wrapper.get_object(idx or 0)

            # Spectrum — show all catalogs
            spec = obj.get_spectrum()
            spectrum_fig.add_trace(
                go.Scatter(
                    x=spec["midpoints"].tolist(),
                    y=spec["mags"].tolist(),
                    mode="markers+lines",
                    error_y=dict(type="data", array=spec["mag_errors"].tolist(), visible=True),
                    name=comp.name,
                    line=dict(color=palette[i % len(palette)]),
                )
            )

            # Color-color: all adjacent pairs for each catalog
            colors = obj.get_colors()
            color_names = list(colors.keys())
            color_vals = [colors[c][0] for c in color_names]
            if len(color_names) >= 2:
                x_vals = [np.clip(float(color_vals[j]), -1, 2) for j in range(len(color_names) - 1)]
                y_vals = [np.clip(float(color_vals[j + 1]), -1, 2) for j in range(len(color_names) - 1)]
                color_fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="markers+lines",
                        marker=dict(size=8, color=palette[i % len(palette)]),
                        line=dict(color=palette[i % len(palette)], width=1, dash="dot"),
                        name=comp.name,
                        hovertext=[
                            f"{color_names[j]} vs {color_names[j + 1]}" for j in range(len(color_names) - 1)
                        ],
                        hoverinfo="text+x+y",
                    )
                )

            # Gather component estimate names
            for est_name in obj.get_estimate_names():
                label = f"{comp.name}/{est_name}"
                if label not in component_estimate_names:
                    component_estimate_names.append(label)

        spectrum_fig.update_layout(
            xaxis_title="Wavelength (nm)",
            yaxis_title="Magnitude",
            yaxis_autorange="reversed",
            template="plotly_white",
            margin=dict(t=10, b=40, l=50, r=10),
        )

        color_fig.update_layout(
            xaxis=dict(title="Color[i]", range=[-1, 2]),
            yaxis=dict(title="Color[i+1]", range=[-1, 2]),
            template="plotly_white",
            margin=dict(t=10, b=40, l=50, r=10),
        )

        # Estimate options: combined first, then components
        all_estimate_names = combined_estimate_names + component_estimate_names
        est_opts = [{"label": n, "value": n} for n in all_estimate_names]
        if prev_estimates:
            est_values = [e for e in prev_estimates if e in all_estimate_names]
        else:
            # Default: only combined dataset estimates enabled
            est_values = combined_estimate_names

        return spectrum_fig, color_fig, est_opts, est_values

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {e}", showarrow=False)
        return fig, go.Figure(), [], []


@callback(
    Output("viz-m-redshift", "figure"),
    Input("viz-m-estimate-checks", "value"),
    Input("viz-m-zrange", "value"),
    Input("viz-m-slider", "value"),
    State("viz-m-dataset-id", "data"),
)
def update_redshift(selected_estimates, zrange, idx, dataset_id):
    if not dataset_id:
        return go.Figure()

    try:
        provider = BackendProvider.get()
        assocs = provider.dataset_assoc.find_by(matched_dataset_id=dataset_id)
        palette = px.colors.qualitative.Dark24

        zgrid = np.linspace(zrange[0], zrange[1], 301)
        fig = go.Figure()
        color_idx = 0

        # Combined (matched) dataset estimates
        matched_ds = provider.dataset.get_row(dataset_id)
        matched_wrapper = _get_component_wrapper(dataset_id, provider)
        matched_obj = matched_wrapper.get_object(idx or 0)
        matched_estimates = matched_obj.get_redshift_estimates()

        for est_name, ensemble in matched_estimates.items():
            label = f"{matched_ds.name}/{est_name}"
            if selected_estimates and label not in selected_estimates:
                continue
            try:
                pdf_vals = np.squeeze(ensemble.pdf(zgrid))
                fig.add_trace(
                    go.Scatter(
                        x=zgrid.tolist(),
                        y=pdf_vals.tolist(),
                        mode="lines",
                        name=label,
                        line=dict(color=palette[color_idx % len(palette)]),
                    )
                )
                color_idx += 1
            except Exception:
                pass

        # Component dataset estimates
        for assoc in assocs:
            comp = provider.dataset.get_row(assoc.component_dataset_id)
            wrapper = _get_component_wrapper(comp.id_, provider)
            obj = wrapper.get_object(idx or 0)
            estimates = obj.get_redshift_estimates()

            for est_name, ensemble in estimates.items():
                label = f"{comp.name}/{est_name}"
                if selected_estimates and label not in selected_estimates:
                    continue
                try:
                    pdf_vals = np.squeeze(ensemble.pdf(zgrid))
                    fig.add_trace(
                        go.Scatter(
                            x=zgrid.tolist(),
                            y=pdf_vals.tolist(),
                            mode="lines",
                            name=label,
                            line=dict(color=palette[color_idx % len(palette)]),
                        )
                    )
                    color_idx += 1
                except Exception:
                    pass

        # True redshift from first component
        if assocs:
            comp0 = provider.dataset.get_row(assocs[0].component_dataset_id)
            w = _get_component_wrapper(comp0.id_, provider)
            true_z = w.get_object(idx or 0).get_true_redshift()
            if true_z is not None and not np.isnan(true_z):
                fig.add_vline(x=float(true_z), line_dash="dash", line_color="gray", annotation_text="true z")

        fig.update_layout(
            xaxis_title="Redshift",
            yaxis_title="p(z)",
            template="plotly_white",
            margin=dict(t=10, b=40, l=50, r=10),
        )
        return fig
    except Exception:
        return go.Figure()
