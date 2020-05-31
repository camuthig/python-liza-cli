from __future__ import annotations

from enum import Enum
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import typer

from liza_cli.bitbucket import BitBucket
from liza_cli.config import Config, Repository, PullRequest, User, Update, ActivityType

app = typer.Typer()


@dataclass
class State:
    client: Optional[BitBucket] = None
    config_file: Path = None
    config: Config = None


state = State()


def err(message: str, code: Optional[int] = 1):
    typer.secho(message, fg=typer.colors.RED, err=True)
    return typer.Exit(code)


def not_logged_in():
    raise err("You must configure credentials first.")


def write_config():
    with state.config_file.open("w") as f:
        f.write(state.config.json(indent=4, sort_keys=True))


def create_default_config():
    state.config = Config(repositories={},)

    write_config()


@app.command()
def credentials(username: str, token: str):
    """
    Configure the credentials for your user.

    Liza uses an app password to access BitBucket. You can create the password here:

    https://bitbucket.org/account/settings/app-passwords/

    Liza needs access to:

        - Account read

        - Repositories read

        - Pull requests read
    """
    client = BitBucket(username, token, user_uuid=None)
    user = client.get_user()
    if user is None:
        raise err("Invalid login credentials")

    state.config.user_uuid = user["uuid"]
    state.config.token = token
    state.config.username = username

    write_config()

    typer.secho("Token saved", fg=typer.colors.GREEN)


@app.command()
def reset():
    """
    Reset your Liza application

    This will delete all configurations including watched repositories and credentials.
    """
    delete = typer.confirm("This will delete all data. Are you sure?")
    if delete:
        state.config_file.unlink()

        typer.secho("Reset all data.", fg=typer.colors.GREEN)


@app.command()
def watched():
    """
    List the repositories that you are currently watching
    """
    for r in state.config.repositories.values():
        typer.echo(r.name)


@app.command()
def watch(repository_name: str = typer.Argument(..., metavar="name")):
    """
    Add a new repository to your watched list.
    """
    if not state.client:
        not_logged_in()

    if repository_name in state.config.repositories.keys():
        typer.secho(f"You are already watching {repository_name}")
        return

    repository = state.client.get_repository(repository_name)

    r = Repository(name=repository["full_name"], uuid=repository["uuid"])

    pull_requests = state.client.get_assigned_and_authored_pull_requests(
        repository_name
    )

    for pull_request in pull_requests:
        p = PullRequest.parse_obj(pull_request)
        r.pull_requests[p.id] = p

    state.config.repositories[r.name] = r

    write_config()

    typer.secho(f"You are now watching {repository_name}", fg=typer.colors.GREEN)


@app.command()
def unwatch(repository_name: str = typer.Argument(..., metavar="name")):
    """
    Remove a repository from your watched list.
    """
    if not state.client:
        not_logged_in()

    if repository_name not in state.config.repositories.keys():
        typer.secho(f"You are not watching {repository_name}")
        return

    del state.config.repositories[repository_name]

    write_config()

    typer.secho(f"You are no longer watching {repository_name}", fg=typer.colors.GREEN)


def update_watched_pulled_requests():
    for repository in state.config.repositories.values():
        updated = {}
        pull_requests = state.client.get_assigned_and_authored_pull_requests(
            repository.name
        )
        for pull_request in pull_requests:
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
        activities = state.client.get_pull_request_activity(
            repository.name, pull_request.id
        )
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
    """
    Read the latest activity information from BitBucket for all watched repositories
    """
    if not state.client:
        not_logged_in()

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
def updates(
    count: bool = typer.Option(
        False, "--count", "-c", help="Only the count of updates"
    ),
    repository_name: Optional[str] = typer.Option(None, "--repository", "-r"),
    output_format: Format = Format.TABLE,
):
    """
    List all active pull requests and see which have updates.
    """
    if count:
        t = 0
        for repository in state.config.repositories.values():
            if repository_name and repository_name != repository.name:
                continue

            for pull_request in repository.pull_requests.values():
                if pull_request.has_unread_updates():
                    t += len(pull_request.updates)

        typer.echo(t)
        return

    from liza_cli.formatters import (
        PlainFormatter,
        Formatter,
        TableFormatter,
        JsonFormatter,
    )

    def get_formatter() -> Formatter:
        formatters = {
            Format.PLAIN: PlainFormatter,
            Format.JSON: JsonFormatter,
            Format.TABLE: TableFormatter,
        }

        return formatters[output_format]()

    formatter = get_formatter()

    rs = state.config.repositories.values()
    if repository_name:
        rs = [r for r in rs if repository_name == r.name]

    formatter.format_updates(rs)


def paginate_or_select_pull_requests(
    repository: Optional[str], id: Optional[int], action: Callable[[PullRequest], None],
):
    if id is not None and repository is None:
        raise err(f"You must include a repository when providing a pull request ID")

    if id is not None:
        r = state.config.repositories.get(repository)
        if r is None:
            raise err(f"Not watching repository {repository}")

        pr = r.pull_requests.get(id)
        if pr is None:
            raise err(
                f"Could not find a pull request with id {id} for repository {repository}"
            )

        action(pr)
        return

    if repository is not None:
        r = state.config.repositories.get(repository)
        if r is None:
            raise err(f"Not watching repository {repository}")

        prs = r.pull_requests_with_repository()
    else:
        prs = state.config.pull_requests_with_repository()

    size = 10
    pages = [prs[i : i + size] for i in range(0, len(prs), size)]
    for offset, page in enumerate(pages):
        for i, data in enumerate(page):
            number = typer.style(f"[{i}]", fg=typer.colors.WHITE)
            number_of_updates = typer.style("(0 updates)", fg=typer.colors.GREEN)
            if data.has_unread_updates():
                number_of_updates = typer.style(
                    f"({len(data.updates)} updates)", fg=typer.colors.BRIGHT_RED
                )
            info = typer.style(
                f"{data.repository.name}:{data.id} - {data.title}",
                fg=typer.colors.WHITE,
            )
            typer.echo(f"  {number} {number_of_updates} {info}")

        choice = typer.prompt(f"Choose a pull request (0-{len(page)-1}, n)")

        if choice == "n":
            continue

        try:
            choice = int(choice)
        except ValueError:
            raise err(f"Invalid selection")

        if choice >= size or choice < 0:
            raise err(f"{choice} is an invalid selection")

        choice = page[choice]

        pr = state.config.repositories[choice.repository.name].pull_requests[choice.id]
        action(pr)
        return


@app.command()
def read(repository: Optional[str] = None, id: Optional[int] = None):
    """
    Mark a pull request as read.
    """

    def mark_read(pull_request: PullRequest):
        pull_request.mark_read()
        write_config()

    paginate_or_select_pull_requests(repository, id, mark_read)


@app.command()
def unread(repository: Optional[str] = None, id: Optional[int] = None):
    """
    Mark a pull request as unread.
    """

    def mark_read(pull_request: PullRequest):
        reset_date = pull_request.last_updated - timedelta(minutes=1)
        pull_request.mark_read(reset_date)
        write_config()

    paginate_or_select_pull_requests(repository, id, mark_read)


@app.command(name="open")
def open_pr(repository: Optional[str] = None, id: Optional[int] = None):
    """
    Open a pull request in the browser and mark it as read.
    """

    def open_and_mark_read(pull_request: PullRequest):
        import webbrowser

        webbrowser.open(pull_request.links.html.href)
        pull_request.mark_read()
        write_config()

    paginate_or_select_pull_requests(repository, id, open_and_mark_read)


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
