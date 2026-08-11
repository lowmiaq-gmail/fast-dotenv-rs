import json
import os
import shlex
import sys
from contextlib import contextmanager
from typing import IO, Any, Dict, Iterator, List, Optional

if sys.platform == "win32":
    from subprocess import Popen

try:
    import click
except ImportError:  # pragma: no cover - exercised in a no-extra install
    sys.stderr.write(
        "It seems python-dotenv is not installed with cli option. \n"
        'Run pip install "python-dotenv[cli]" to fix this.'
    )
    sys.exit(1)

from .main import dotenv_values, set_key, unset_key
from .version import __version__


def enumerate_env() -> Optional[str]:
    try:
        cwd = os.getcwd()
    except FileNotFoundError:
        return None
    return os.path.join(cwd, ".env")


@click.group()
@click.option(
    "-f",
    "--file",
    default=enumerate_env(),
    type=click.Path(file_okay=True),
    help="Location of the .env file, defaults to .env file in current working directory.",
)
@click.option(
    "-q",
    "--quote",
    default="always",
    type=click.Choice(["always", "never", "auto"]),
    help="Whether to quote or not the variable values. Default mode is always. This does not affect parsing.",
)
@click.option(
    "-e",
    "--export",
    default=False,
    type=click.BOOL,
    help="Whether to write the dot file as an executable bash script.",
)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, file: Any, quote: Any, export: Any) -> None:
    """This script is used to set, get or unset values from a .env file."""
    ctx.obj = {"QUOTE": quote, "EXPORT": export, "FILE": file}


@contextmanager
def stream_file(path: os.PathLike) -> Iterator[IO[str]]:
    try:
        with open(path) as stream:
            yield stream
    except OSError as exc:
        print(f"Error opening env file: {exc}", file=sys.stderr)
        sys.exit(2)


@cli.command(name="list")
@click.pass_context
@click.option(
    "--format",
    "output_format",
    default="simple",
    type=click.Choice(["simple", "json", "shell", "export"]),
    help="The format in which to display the list. Default format is simple, which displays name=value without quotes.",
)
def list_values(ctx: click.Context, output_format: str) -> None:
    """Display all the stored key/value."""
    with stream_file(ctx.obj["FILE"]) as stream:
        values = dotenv_values(stream=stream)
    if output_format == "json":
        click.echo(json.dumps(values, indent=2, sort_keys=True))
    else:
        prefix = "export " if output_format == "export" else ""
        for key in sorted(values):
            value = values[key]
            if value is not None:
                if output_format in ("export", "shell"):
                    value = shlex.quote(value)
                click.echo(f"{prefix}{key}={value}")


@cli.command(name="set")
@click.pass_context
@click.argument("key", required=True)
@click.argument("value", required=True)
def set_value(ctx: click.Context, key: Any, value: Any) -> None:
    """Store the given key/value."""
    success, key, value = set_key(
        ctx.obj["FILE"], key, value, ctx.obj["QUOTE"], ctx.obj["EXPORT"]
    )
    if success:
        click.echo(f"{key}={value}")
    else:
        sys.exit(1)


@cli.command()
@click.pass_context
@click.argument("key", required=True)
def get(ctx: click.Context, key: Any) -> None:
    """Retrieve the value for the given key."""
    with stream_file(ctx.obj["FILE"]) as stream:
        values = dotenv_values(stream=stream)
    stored_value = values.get(key)
    if stored_value:
        click.echo(stored_value)
    else:
        sys.exit(1)


@cli.command()
@click.pass_context
@click.argument("key", required=True)
def unset(ctx: click.Context, key: Any) -> None:
    """Removes the given key."""
    success, key = unset_key(ctx.obj["FILE"], key, ctx.obj["QUOTE"])
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        sys.exit(1)


@cli.command(
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    }
)
@click.pass_context
@click.option(
    "--override/--no-override",
    default=True,
    help="Override variables from the environment file with those from the .env file.",
)
@click.argument("commandline", nargs=-1, type=click.UNPROCESSED)
def run(ctx: click.Context, override: bool, commandline: tuple[str, ...]) -> None:
    """Run command with environment variables present."""
    file = ctx.obj["FILE"]
    if not os.path.isfile(file):
        raise click.BadParameter(f"Invalid value for '-f' \"{file}\" does not exist.", ctx=ctx)
    dotenv_as_dict = {
        key: value
        for key, value in dotenv_values(file).items()
        if value is not None and (override or key not in os.environ)
    }
    if not commandline:
        click.echo("No command given.")
        sys.exit(1)
    run_command([*commandline, *ctx.args], dotenv_as_dict)


def run_command(command: List[str], env: Dict[str, str]) -> None:
    cmd_env = os.environ.copy()
    cmd_env.update(env)
    if sys.platform == "win32":
        p = Popen(command, universal_newlines=True, bufsize=0, shell=False, env=cmd_env)
        _, _ = p.communicate()
        sys.exit(p.returncode)
    os.execvpe(command[0], args=command, env=cmd_env)
