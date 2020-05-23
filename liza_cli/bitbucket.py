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
        return httpx.get(f"{self.endpoint}{path}", auth=(self.username, self.token), params=params or {})

    def get_user(self) -> Optional[Dict]:
        response = self._get("/user")

        if response.status_code != 200:
            return None

        return json.loads(response.content)

    def get_repository(self, workspace: str, name: str) -> Dict:
        response = self._get(f"/repositories/{workspace}/{name}")

        return json.loads(response.content)

    def get_pull_requests(self, workspace: str, name: str) -> Dict:
        # query = q=state%3D%22OPEN%22%20AND%20reviewers.uuid%3D%22%7Bac5bf988-50ef-478a-844c-e791cef46b65%7D%22&page=1
        params = {
            "pagelen": 25,
            "q": f'state="OPEN" AND reviewers.uuid="{self.user_uuid}"',
            "state": "OPEN",
        }
        response = self._get(f"/repositories/{workspace}/{name}/pullrequests", params=params)

        print(response.content)

        return json.loads(response.content)

    def get_pull_request_activity(self, workspace: str, name: str, id: str) -> Dict:
        response = self._get(f"/repositories/{workspace}/{name}/pullrequests/{id}/activity")

        print(response.content)

        return json.loads(response.content)
