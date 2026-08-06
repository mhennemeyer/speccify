"""Speccify CLI — playbooks for coding agents."""

from __future__ import annotations

import typer

from speccify_cli.commands.add import add_command
from speccify_cli.commands.check import check_command
from speccify_cli.commands.init import init_command
from speccify_cli.commands.lint import lint_command
from speccify_cli.commands.lock import lock_command
from speccify_cli.commands.pull import pull_command
from speccify_cli.commands.search import search_command
from speccify_cli.commands.show import show_command
from speccify_cli.commands.verify import verify_command

app = typer.Typer(
    name="speccify",
    help="Speccify — playbooks for complex, recurring workflows.",
    no_args_is_help=True,
    add_completion=False,
)

app.command("init")(init_command)
app.command("search")(search_command)
app.command("add")(add_command)
app.command("lock")(lock_command)
app.command("pull")(pull_command)
app.command("verify")(verify_command)
app.command("show")(show_command)
app.command("lint")(lint_command)
app.command("check")(check_command)


@app.callback()
def _root() -> None:
    """Speccify — playbooks for complex, recurring workflows."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
