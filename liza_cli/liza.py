import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import typer

app = typer.Typer()


@dataclass
class State:
    config_file: Path = None
    config: Dict = None


state = State()


@app.command()
def token(t: str = typer.Argument(..., metavar='token')):
    state.config['token'] = t

    with open(state.config_file, 'w') as f:
        f.write(json.dumps(state.config, indent=4, sort_keys=True))
    typer.secho('Token saved', fg=typer.colors.GREEN)


@app.callback()
def main(config: Path = typer.Option(default=Path(Path.home(), '.liza'))):
    if not config.exists():
        with open(config, 'w') as f:
            f.write("{}")

    with open(config, 'r') as f:
        content = f.read()

    state.config = json.loads(content)
    state.config_file = config


if __name__ == "__main__":
    app()
