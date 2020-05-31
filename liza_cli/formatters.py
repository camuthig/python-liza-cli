import abc
import json
import typer

from datetime import datetime, timezone
from tabulate import tabulate
from typing import List

from liza_cli.config import PullRequestWithRepository


def format_time(d: datetime) -> str:
    return d.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%Y-%m-%dT%H:%M")


class Formatter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def format_updates(self, pull_requests: List[PullRequestWithRepository]):
        raise NotImplementedError


class TabulatorFormatter(Formatter, metaclass=abc.ABCMeta):
    @staticmethod
    def get_data(pull_requests: List[PullRequestWithRepository]) -> List[List[str]]:
        data = []
        for pull_request in pull_requests:
            title = pull_request.title
            if len(title) > 35:
                title = title[:35] + "..."

            number_of_updates = 0
            if pull_request.has_unread_updates():
                number_of_updates = len(pull_request.updates)

            data.append(
                [
                    pull_request.repository.name,
                    title,
                    number_of_updates,
                    format_time(pull_request.last_updated),
                    format_time(pull_request.last_read),
                    pull_request.links.html.href,
                ]
            )

        return data


class PlainFormatter(TabulatorFormatter):
    def format_updates(self, pull_requests: List[PullRequestWithRepository]):
        typer.secho(
            tabulate(tabular_data=self.get_data(pull_requests), tablefmt="plain")
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

    def format_updates(self, pull_requests: List[PullRequestWithRepository]):
        typer.secho(
            tabulate(
                tabular_data=self.get_data(pull_requests),
                headers=self._print_updates_header(),
                tablefmt="github",
            )
        )


class JsonFormatter(Formatter):
    def format_updates(self, pull_requests: List[PullRequestWithRepository]):
        data = []

        for pull_request in pull_requests:
            datum = {
                "repository": pull_request.repository.name,
                "pull_request": pull_request.title,
                "number_of_updates": len(pull_request.unread_updates()),
                "last_updated": format_time(pull_request.last_updated),
                "last_read": format_time(pull_request.last_read),
                "link": pull_request.links.html.href,
            }
            data.append(datum)

        typer.secho(json.dumps(data, indent=4))
