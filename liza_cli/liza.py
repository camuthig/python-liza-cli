from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import typer

from liza_cli.bitbucket import BitBucket
from liza_cli.config import Config, Repository, PullRequest, User, Update, ActivityType
from liza_cli.formatters import PlainFormatter, Formatter, TableFormatter, JsonFormatter

app = typer.Typer()


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

    state.config.user_uuid = user["uuid"]
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

    r = Repository(name=repository["full_name"], uuid=repository["uuid"])

    if r.name in state.config.repositories.keys():
        typer.secho(f"You are already watching {workspace}/{name}")
        return

    pull_request_page = state.client.get_assigned_and_authored_pull_requests(
        workspace, name
    )
    for pull_request in pull_request_page["values"]:
        p = PullRequest.parse_obj(pull_request)
        r.pull_requests[p.id] = p

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


def update_watched_pulled_requests():
    for repository in state.config.repositories.values():
        updated = {}
        pull_request_page = state.client.get_assigned_and_authored_pull_requests(
            *repository.name.split("/")
        )
        for pull_request in pull_request_page["values"]:
            p = PullRequest.parse_obj(pull_request)
            if p.id in repository.pull_requests:
                updated[p.id] = repository.pull_requests.get(p.id)
            else:
                updated[p.id] = p

        repository.pull_requests = updated


def update_pull_requests(repository: Repository):
    date_keys = {
        "approval": "date",
        "comment": "created_on",
        "update": "date",
    }

    user_keys = {
        "approval": "user",
        "comment": "user",
        "update": "author",
    }
    for pull_request in repository.pull_requests.values():
        page = state.client.get_pull_request_activity(
            *repository.name.split("/"), pull_request.id
        )
        activities: List[Dict[str, Any]] = page["values"]
        updates: List[Update] = []
        for activity in activities:
            activity_type = list(activity.keys())[0]
            data = activity[activity_type]

            date_of_activity = datetime.fromisoformat(data[date_keys[activity_type]])

            if date_of_activity < pull_request.last_read:
                break

            update_author = User.parse_obj(data[user_keys[activity_type]])
            if update_author.uuid == state.config.user_uuid:
                # Ignore changes from ourselves
                continue

            if (
                not pull_request.is_authored_by(state.config.user_uuid)
                and activity_type == "approval"
            ):
                # Ignore approvals if we are only a reviewer on the PR
                continue

            updates.append(
                Update(
                    date=date_of_activity,
                    activity_type=ActivityType(activity_type),
                    author=update_author,
                )
            )

        pull_request.updates = updates
        pull_request.mark_updated()


@app.command()
def update():
    if not state.client:
        return not_logged_in()

    update_watched_pulled_requests()

    for repository in state.config.repositories.values():
        update_pull_requests(repository)

    typer.secho("Update complete", fg=typer.colors.GREEN)

    write_config()


class Format(str, Enum):
    JSON = "json"
    PLAIN = "plain"
    TABLE = "table"


@app.command()
def updates(count: bool = False, output_format: Format = Format.PLAIN):
    if count:
        t = 0
        for repository in state.config.repositories.values():
            for pull_request in repository.pull_requests.values():
                t += len(pull_request.updates)

        typer.secho(t)
        return

    def get_formatter() -> Formatter:
        formatters = {
            Format.PLAIN: PlainFormatter,
            Format.JSON: JsonFormatter,
            Format.TABLE: TableFormatter,
        }

        return formatters[output_format]()

    formatter = get_formatter()

    formatter.format_updates(list(state.config.repositories.values()))


@app.callback()
def main(config: Path = typer.Option(default=Path(Path.home(), ".liza"))):
    state.config_file = config
    if not config.exists():
        create_default_config()

    state.config = Config.parse_file(config.absolute())
    state.config_file = config

    if state.config.username and state.config.token:
        state.client = BitBucket(
            state.config.username, state.config.token, state.config.user_uuid
        )


if __name__ == "__main__":
    app()
