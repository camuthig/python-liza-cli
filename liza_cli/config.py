from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List

from pydantic import BaseModel, HttpUrl


class Link(BaseModel):
    href: HttpUrl


class ActivityType(str, Enum):
    APPROVAL = "approval"
    COMMENT = "comment"
    UPDATE = "update"


class User(BaseModel):
    class Links(BaseModel):
        avatar: Link

    uuid: str
    display_name: str
    links: Links


class Update(BaseModel):
    date: datetime
    activity_type: ActivityType
    author: User


class PullRequest(BaseModel):
    class Links(BaseModel):
        html: Link

    id: int
    title: str = ""
    author: User
    links: Links
    updates: List[Update] = []
    last_read: datetime = datetime.now(timezone.utc)
    last_updated: datetime = datetime.now(timezone.utc)

    def is_authored_by(self, uuid: str) -> bool:
        return uuid == self.author.uuid

    def mark_read(self, at: datetime = datetime.now(timezone.utc)):
        self.last_read = at

    def mark_updated(self):
        self.last_updated = datetime.now(timezone.utc)

    def unread_updates(self):
        if self.last_read > self.last_updated:
            return []

        return self.updates

    def has_unread_updates(self):
        return len(self.unread_updates()) > 0


class Repository(BaseModel):
    has_updates: bool = False
    name: str
    pull_requests: Dict[int, PullRequest] = {}
    uuid: str

    def pull_requests_with_repository(self):
        prs = []
        for pr in self.pull_requests.values():
            prs.append(PullRequestWithRepository(**pr.dict(), repository=self))

        return prs


class PullRequestWithRepository(PullRequest):
    repository: Repository


class Config(BaseModel):
    token: Optional[str]
    username: Optional[str]
    user_uuid: Optional[str]
    repositories: Dict[str, Repository]

    def pull_requests_with_repository(self) -> List[PullRequestWithRepository]:
        prs = []
        for r in self.repositories.values():
            prs += r.pull_requests_with_repository()

        return prs
