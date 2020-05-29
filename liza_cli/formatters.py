import abc
import json
import typer

from datetime import datetime, timezone
from tabulate import tabulate
from typing import List

from liza_cli.config import Repository


def format_time(d: datetime) -> str:
    return d.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%Y-%m-%dT%H:%M")


class Formatter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def format_updates(self, repositories: List[Repository]):
        raise NotImplementedError


class TabulatorFormatter(Formatter, metaclass=abc.ABCMeta):
    @staticmethod
    def get_data(repositories: List[Repository]) -> List[List[str]]:
        data = []
        for repository in repositories:
            for pull_request in repository.pull_requests.values():
                title = pull_request.title
                if len(title) > 35:
                    title = title[:35] + "..."

                number_of_updates = 0
                if pull_request.has_unread_updates():
                    number_of_updates = len(pull_request.updates)

                # WIP capture the link for each pull request
                data.append(
                    [
                        repository.name,
                        title,
                        number_of_updates,
                        format_time(pull_request.last_updated),
                        format_time(pull_request.last_read),
                        "",
                    ]
                )

        return data


class PlainFormatter(TabulatorFormatter):
    def format_updates(self, repositories: List[Repository]):
        typer.secho(
            tabulate(tabular_data=self.get_data(repositories), tablefmt="plain")
        )


class TableFormatter(TabulatorFormatter):
    @staticmethod
    def _print_updates_header() -> List[str]:
        return [
            "repository",
            "pull request",
            "# of updates",
            "last updated",
            "last read",
            "link",
        ]

    def format_updates(self, repositories: List[Repository]):
        typer.secho(
            tabulate(
                tabular_data=self.get_data(repositories),
                headers=self._print_updates_header(),
                tablefmt="github",
            )
        )


class JsonFormatter(Formatter):
    def format_updates(self, repositories: List[Repository]):
        data = []

        for repository in repositories:
            for pull_request in repository.pull_requests.values():
                title = pull_request.title
                number_of_updates = 0
                if pull_request.has_unread_updates():
                    number_of_updates = len(pull_request.updates)

                # WIP capture the link for each pull request
                datum = {
                    "repository": repository.name,
                    "pull_request": title,
                    "number_of_updates": number_of_updates,
                    "last_updated": format_time(pull_request.last_updated),
                    "last_read": format_time(pull_request.last_read),
                    "link": "",
                }
                data.append(datum)

        typer.secho(json.dumps(data, indent=4))
