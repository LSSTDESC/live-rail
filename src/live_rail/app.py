"""Entry point for running the RAIL dashboard directly."""

from live_rail.backend import BackendMode, BackendProvider, BackendSettings
from live_rail.dashboard import create_app


def main(
    port: int = 8050,
    debug: bool = True,
    backend: str = "local",
    db_url: str = "sqlite+aiosqlite:///rail_svc.db",
    server_url: str = "http://localhost:8000",
    token: str | None = None,
    catalog_yaml: str | None = "nb/sandbox_catalogs.yaml",
) -> None:
    settings = BackendSettings(
        mode=BackendMode(backend),
        db_url=db_url,
        server_url=server_url,
        auth_token=token,
        catalog_yaml=catalog_yaml,
    )
    provider = BackendProvider.get()
    provider.configure(settings)
    provider.initialize()

    app = create_app(debug=debug)
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    main()
