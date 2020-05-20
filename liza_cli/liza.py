import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import typer

from liza_cli import bitbucket

app = typer.Typer()


@dataclass
class State:
    config_file: Path = None
    config: Dict = None


state = State()


@app.command()
def credentials(username: str, token: str):
    if not bitbucket.test_token(username, token):
        typer.secho('Invalid login credentials', fg=typer.colors.RED)
        return

    state.config['token'] = token
    state.config['username'] = username

    with state.config_file.open('w') as f:
        f.write(json.dumps(state.config, indent=4, sort_keys=True))

    typer.secho('Token saved', fg=typer.colors.GREEN)


@app.callback()
def main(config: Path = typer.Option(default=Path(Path.home(), '.liza'))):
    if not config.exists():
        with config.open('w') as f:
            f.write("{}")

    with config.open('r') as f:
        content = f.read()

    state.config = json.loads(content)
    state.config_file = config


if __name__ == "__main__":
    app()
