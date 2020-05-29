import json

import httpx

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class BitBucket:
    username: str
    token: str
    user_uuid: Optional[str]
    endpoint = "https://api.bitbucket.org/2.0"

    def _get(self, path: str, params: Dict = None):
        return httpx.get(
            f"{self.endpoint}{path}",
            auth=(self.username, self.token),
            params=params or {},
        )

    def get_user(self) -> Optional[Dict]:
        response = self._get("/user")

        if response.status_code != 200:
            return None

        return json.loads(response.content)

    def get_repository(self, workspace: str, name: str) -> Dict:
        response = self._get(f"/repositories/{workspace}/{name}")

        return json.loads(response.content)

    def get_assigned_and_authored_pull_requests(self, workspace: str, name: str) -> Dict:
        # WIP Implement pagination
        params = {
            "pagelen": 25,
            "q": f'state="OPEN" AND (author.uuid="{self.user_uuid}" OR reviewers.uuid="{self.user_uuid}")',
            "state": "OPEN",
        }
        response = self._get(
            f"/repositories/{workspace}/{name}/pullrequests", params=params
        )

        return json.loads(response.content)

    def get_pull_request_activity(self, workspace: str, name: str, id: int) -> Dict:
        # WIP Implement pagination
        response = self._get(
            f"/repositories/{workspace}/{name}/pullrequests/{id}/activity"
        )

        return json.loads(response.content)
