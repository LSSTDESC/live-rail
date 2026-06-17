from importlib.metadata import version as _pkg_version

import click

from live_rail.app import main

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
    main(
        port=port,
        debug=debug,
        backend=backend,
        db_url=db_url,
        server_url=server_url,
        token=token,
        catalog_yaml=catalog_yaml,
    )
    return 0


@cli.command(name="setup")
@click.argument("profile")
@click.option("--skip-download", is_flag=True, default=False, help="Skip data download step")
@click.option("--catalog-yaml", default=None, help="Override catalog YAML path")
@click.option("--list-profiles", "list_profiles_flag", is_flag=True, default=False,
              help="List available profiles")
def setup(profile: str, skip_download: bool, catalog_yaml: str | None, list_profiles_flag: bool) -> None:
    """Run a data setup profile.

    PROFILE is the name of the setup profile to run (e.g. 'pzdc').
    Use --list-profiles to see available options.
    """
    from live_rail.setup import get_profile, list_profiles

    if list_profiles_flag:
        profiles = list_profiles()
        if not profiles:
            click.echo("No setup profiles available.")
        else:
            click.echo("Available setup profiles:")
            for name, desc in profiles:
                click.echo(f"  {name:12s} {desc}")
        return

    try:
        profile_cls = get_profile(profile)
    except KeyError as e:
        raise click.BadParameter(str(e), param_hint="'PROFILE'") from e

    instance = profile_cls()
    click.echo(f"Running setup profile: {instance.name}")
    instance.run(skip_download=skip_download, catalog_yaml=catalog_yaml)
    click.echo("Setup complete.")
