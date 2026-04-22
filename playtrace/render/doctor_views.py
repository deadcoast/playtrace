from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from playtrace.models.doctor import DoctorFinding, DoctorSnapshot
from playtrace.render.theme import Theme


SEVERITY_STYLES = {
    "info": "dim",
    "warn": "warning",
    "error": "danger",
}


def render_doctor(console, theme: Theme, snapshot: DoctorSnapshot) -> None:
    header = Text()
    header.append("playtrace DOCTOR\n", style=f"bold {theme.accent}")
    header.append("Environment and persisted-data audit", style=theme.dim)
    console.print(Panel(header, border_style=theme.accent, padding=(1, 2)))

    console.print(_findings_panel(theme, "Environment", snapshot.environment_findings))
    console.print()
    console.print(_findings_panel(theme, "Data", snapshot.data_findings))
    console.print()
    console.print(_remediation_panel(theme, snapshot))


def _findings_panel(theme: Theme, title: str, findings: list[DoctorFinding]) -> Panel:
    if not findings:
        body = Text("No findings in this section.", style=theme.success)
        return Panel(body, title=title, border_style=theme.success, padding=(1, 2))

    table = Table(show_header=True, header_style=f"bold {theme.text}")
    table.add_column("Severity")
    table.add_column("Finding", ratio=4)
    table.add_column("Code", ratio=2)

    for finding in findings:
        style_name = SEVERITY_STYLES.get(finding.severity, "dim")
        style = getattr(theme, style_name)
        table.add_row(
            f"[{style}]{finding.severity}[/{style}]",
            finding.summary,
            finding.code,
        )

    border_style = theme.warning if any(f.severity != "info" for f in findings) else theme.success
    return Panel(table, title=title, border_style=border_style, padding=(1, 2))


def _remediation_panel(theme: Theme, snapshot: DoctorSnapshot) -> Panel:
    lines: list[str] = []
    seen: set[str] = set()
    for finding in [*snapshot.environment_findings, *snapshot.data_findings]:
        for line in finding.remediation:
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)

    if not lines:
        lines.append("No corrective action is required right now.")

    body = Text()
    for line in lines:
        body.append(f"- {line}\n", style=theme.text)

    return Panel(body, title="How to correct this", border_style=theme.accent, padding=(1, 2))
