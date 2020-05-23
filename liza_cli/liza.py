from __future__ import annotations
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

import typer

from liza_cli.bitbucket import BitBucket

app = typer.Typer()


class Repository(BaseModel):
    id: int
    has_updates: bool = False
    last_read: datetime
    name: str


class Config(BaseModel):
    token: Optional[str]
    username: Optional[str]
    user_uuid: Optional[str]
    repositories: Dict[str, Repository]


@dataclass
class State:
    client: Optional[BitBucket] = None
    config_file: Path = None
    config: Config = None


state = State()


def not_logged_in():
    typer.secho("You must configure credentials first.", fg=typer.colors.RED, err=True)
    return 1


def write_config():
    with state.config_file.open("w") as f:
        f.write(state.config.json(indent=4, sort_keys=True))


def create_default_config():
    state.config = Config(repositories={},)

    write_config()


@app.command()
def credentials(username: str, token: str):
    client = BitBucket(username, token, user_uuid=None)
    user = client.get_user()
    if user is None:
        typer.secho("Invalid login credentials", fg=typer.colors.RED)
        return

    state.config.user_uuid = user['uuid']
    state.config.token = token
    state.config.username = username

    write_config()

    typer.secho("Token saved", fg=typer.colors.GREEN)


@app.command()
def reset():
    delete = typer.confirm("This will delete all data. Are you sure?")
    if delete:
        state.config_file.unlink()

        typer.secho("Reset all data.", fg=typer.colors.GREEN)


@app.command()
def watched():
    for r in state.config.repositories.values():
        typer.echo(r.name)


@app.command()
def watch(workspace: str, name: str):
    if not state.client:
        return not_logged_in()

    repository = state.client.get_repository(workspace, name)

    r = Repository(
        name=repository["full_name"], id=repository["id"], last_read=datetime.now(),
    )

    if r.name in state.config.repositories.keys():
        typer.secho(f"You are already watching {workspace}/{name}")
        return

    state.config.repositories[r.name] = r

    write_config()

    typer.secho(f"You are now watching {workspace}/{name}", fg=typer.colors.GREEN)


@app.command()
def unwatch(workspace: str, name: str):
    if not state.client:
        return not_logged_in()

    full_name = f"{workspace}/{name}"

    if full_name not in state.config.repositories.keys():
        typer.secho(f"You are not watching {workspace}/{name}")
        return

    del state.config.repositories[full_name]

    write_config()

    typer.secho(f"You are no longer watching {workspace}/{name}", fg=typer.colors.GREEN)


@app.command()
def update():
    if not state.client:
        return not_logged_in()

    date_keys = {
        "update": "date",
        "comment": "created_on",
        "approval": "date",
    }
    for repository in state.config.repositories.values():
        activities = state.client.get_pull_request_activity(*repository.name.split('/'), repository["id"])
        for activity in activities:
            data = activity.values().pop()
            activity_type = activity.keys().pop()

            date_of_activity = datetime.fromisoformat(data[date_keys[activity_type]])

            if date_of_activity < repository.last_read:
                break;

            if date_of_activity > repository.last_read:
                repository.has_updates = True

        repository.last_read = datetime.now()

    write_config()


@app.callback()
def main(config: Path = typer.Option(default=Path(Path.home(), ".liza"))):
    state.config_file = config
    if not config.exists():
        create_default_config()

    state.config = Config.parse_file(config.absolute())
    state.config_file = config

    if state.config.username and state.config.token:
        state.client = BitBucket(state.config.username, state.config.token, state.config.user_uuid)


if __name__ == "__main__":
    app()
