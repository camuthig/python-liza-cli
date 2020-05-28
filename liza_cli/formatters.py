import abc
import json

import typer

from tabulate import tabulate
from typing import List

from liza_cli.config import Repository


class Formatter(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def format_updates(self, repositories: List[Repository]):
        raise NotImplementedError


class TabulatorFormatter(Formatter, metaclass=abc.ABCMeta):
    def get_data(self, repositories: List[Repository]) -> List[List[str]]:
        data = []
        for repository in repositories:
            for pull_request in repository.pull_requests.values():
                if len(pull_request.updates) == 0:
                    continue

                workspace, name = repository.name.split('/')

                title = pull_request.title
                if len(title) > 35:
                    title = title[:35] + '...'

                # WIP capture the link for each pull request
                data.append([workspace, name, title, len(pull_request.updates), ''])

        return data


class PlainFormatter(TabulatorFormatter):
    def format_updates(self, repositories: List[Repository]):
        typer.secho(tabulate(tabular_data=self.get_data(repositories), tablefmt='plain'))


class TableFormatter(TabulatorFormatter):
    @staticmethod
    def _print_updates_header() -> List[str]:
        return ["workspace", "repository", "pull request", "# of updates", "link"]

    def format_updates(self, repositories: List[Repository]):
        typer.secho(
            tabulate(tabular_data=self.get_data(repositories), headers=self._print_updates_header(), tablefmt="github")
        )


class JsonFormatter(Formatter):
    def format_updates(self, repositories: List[Repository]):
        data = []

        for repository in repositories:
            for pull_request in repository.pull_requests.values():
                if len(pull_request.updates) == 0:
                    continue

                workspace, name = repository.name.split('/')

                title = pull_request.title

                # WIP capture the link for each pull request
                datum = {
                    "workspace": workspace,
                    "name": name,
                    "pull_request": title,
                    "number_of_updates": len(pull_request.updates),
                    "link": ""
                }
                data.append(datum)

        typer.secho(json.dumps(data, indent=4))
