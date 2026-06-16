from importlib.metadata import version as _pkg_version

import click

from . import options

__version__ = _pkg_version("live-rail")


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Live RAIL dashboard"""


@cli.command(name="dashboard")
@options.port()
@options.debug()
@click.option("--backend", type=click.Choice(["local", "remote"]), default="local", help="Backend mode")
@click.option("--db-url", default="sqlite+aiosqlite:///rail_svc.db", help="Database URL (local mode)")
@click.option("--server-url", default="http://localhost:8000", help="Server URL (remote mode)")
@click.option("--token", default=None, help="Auth token (remote mode)")
@click.option("--catalog-yaml", default="nb/sandbox_catalogs.yaml", help="RAIL catalog YAML config")
def dashboard(
    port: int,
    debug: bool,
    backend: str,
    db_url: str,
    server_url: str,
    token: str | None,
    catalog_yaml: str | None,
) -> int:
    """Launch the unified RAIL dashboard."""
    from live_rail.app import main
    main(port=port, debug=debug, backend=backend, db_url=db_url, server_url=server_url,
         token=token, catalog_yaml=catalog_yaml)
    return 0
