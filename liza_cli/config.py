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
    id: int
    title: str = ""
    author: User
    updates: List[Update] = []
    last_read: datetime = datetime.now(timezone.utc)
    last_updated: datetime = datetime.now(timezone.utc)

    def is_authored_by(self, uuid: str) -> bool:
        return uuid == self.author.uuid

    def mark_read(self):
        self.last_read = datetime.now(timezone.utc)

    def mark_updated(self):
        self.last_updated = datetime.now(timezone.utc)

    def has_unread_updates(self):
        if self.last_read > self.last_updated:
            return False

        return len(self.updates) > 0


class Repository(BaseModel):
    has_updates: bool = False
    name: str
    pull_requests: Dict[int, PullRequest] = {}
    uuid: str


class Config(BaseModel):
    token: Optional[str]
    username: Optional[str]
    user_uuid: Optional[str]
    repositories: Dict[str, Repository]
