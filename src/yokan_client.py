# Yokan Board MCP
#
# Copyright (C) 2025 Julian I. Kamil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import httpx
from typing import List, Optional, Dict, Any

from . import yokan_models
from . import yokan_models


class YokanClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    def _get_auth_headers(self, token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def list_boards(self, user_id: int, token: str) -> List[yokan_models.Board]:
        headers = self._get_auth_headers(token)
        response = await self.client.get(
            f"{self.base_url}/users/{user_id}/boards", headers=headers
        )
        response.raise_for_status()
        return [yokan_models.Board(**board) for board in response.json()["data"]]

    async def get_board(self, board_id: int, token: str) -> yokan_models.Board:
        headers = self._get_auth_headers(token)
        response = await self.client.get(
            f"{self.base_url}/boards/{board_id}", headers=headers
        )
        response.raise_for_status()
        return yokan_models.Board(**response.json()["data"])

    async def create_board(
        self, user_id: int, name: str, data: Dict[str, Any], token: str
    ) -> int:
        headers = self._get_auth_headers(token)
        json_data = {"user_id": user_id, "name": name, "data": data}
        response = await self.client.post(
            f"{self.base_url}/boards", headers=headers, json=json_data
        )
        response.raise_for_status()
        return response.json()["data"]["id"]

    async def update_board(
        self, board_id: int, name: str, data: Dict[str, Any], token: str
    ) -> int:
        headers = self._get_auth_headers(token)
        json_data = {"name": name, "data": data}
        response = await self.client.put(
            f"{self.base_url}/boards/{board_id}", headers=headers, json=json_data
        )
        response.raise_for_status()
        return response.json()["changes"]

    async def delete_board(self, board_id: int, token: str) -> int:
        headers = self._get_auth_headers(token)
        response = await self.client.delete(
            f"{self.base_url}/boards/{board_id}", headers=headers
        )
        response.raise_for_status()
        return response.json()["changes"]