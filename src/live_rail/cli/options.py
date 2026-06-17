from functools import partial
from typing import Any

import click

__all__ = [
    "port",
    "debug",
    "data_path",
    "pz_estimate_path",
    "pz_estimates_yaml",
]


class PartialOption:
    """Wraps click.option with partial arguments for convenient reuse"""

    def __init__(self, *param_decls: str, **kwargs: Any) -> None:
        self._partial = partial(click.option, *param_decls, cls=click.Option, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._partial(*args, **kwargs)


class PartialArgument:
    """Wraps click.argument with partial arguments for convenient reuse"""

    def __init__(self, *param_decls: Any, **kwargs: Any) -> None:
        self._partial = partial(click.argument, *param_decls, cls=click.Argument, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return self._partial(*args, **kwargs)


debug = PartialOption(
    "--debug",
    help="Debugging Output",
    default=False,
    is_flag=True,
)

port = PartialOption(
    "--port",
    help="Server port",
    type=int,
    default=8050,
)


data_path = PartialOption(
    "--data-path",
    type=click.Path(),
    default=None,
    help="Path for data file",
)


pz_estimate_path = PartialOption(
    "--pz-estimate-path",
    type=click.Path(),
    default=None,
    help="Path for pz_estimate file",
)

pz_estimates_yaml = PartialOption(
    "--pz-estimates-yaml",
    type=click.Path(),
    default=None,
    help="Path to a yaml dict with pz_estimate files",
)
