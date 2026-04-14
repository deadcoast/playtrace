from __future__ import annotations

import typer

from playtrace.cli.cmd_doctor import register_doctor
from playtrace.cli.cmd_export import register_export
from playtrace.cli.cmd_inspect import register_inspect
from playtrace.cli.cmd_map import register_map
from playtrace.cli.cmd_report import register_report
from playtrace.cli.cmd_scan import register_scan
from playtrace.cli.cmd_sessions import register_sessions
from playtrace.cli.cmd_titles import register_titles

app = typer.Typer(
    help="Native Windows executable history and session analysis.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

register_scan(app)
register_report(app)
register_titles(app)
register_sessions(app)
register_inspect(app)
register_map(app)
register_doctor(app)
register_export(app)