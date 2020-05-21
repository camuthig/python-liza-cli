import json

import httpx

from dataclasses import dataclass
from typing import Dict


@dataclass
class BitBucket:
    username: str
    token: str
    endpoint = "https://api.bitbucket.org/2.0"

    def _get(self, path: str):
        return httpx.get(f"{self.endpoint}{path}", auth=(self.username, self.token))

    def test_token(self):
        response = self._get("/user")

        if response.status_code != 200:
            return False

        return True

    def get_repository(self, workspace, name) -> Dict:
        response = self._get(f"/repositories/{workspace}/{name}")

        return json.loads(response.content)
