"""Tests for the live-rail CLI."""

from click.testing import CliRunner

from live_rail.cli.commands import cli


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "dashboard" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_dashboard_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "--backend" in result.output
        assert "--db-url" in result.output
        assert "--server-url" in result.output
        assert "--token" in result.output
        assert "--catalog-yaml" in result.output
        assert "--port" in result.output
        assert "--debug" in result.output

    def test_no_other_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "view-data" not in result.output
        assert "pdf" not in result.output
