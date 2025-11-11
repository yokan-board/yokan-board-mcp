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

import pytest
import respx
import httpx
from typing import List, Dict, Any

from .yokan_client import YokanClient
from . import yokan_models
from .config import get_settings


@pytest.fixture
def client():
    return YokanClient(base_url=get_settings().yokan_api_base_url)


@pytest.mark.asyncio
@respx.mock
async def test_list_boards(client):
    user_id = 1
    token = "test_token"
    mock_boards_data = [
        {"id": 101, "user_id": 1, "name": "Board 1", "data": {}},
        {"id": 102, "user_id": 1, "name": "Board 2", "data": {}},
    ]
    respx.get(f"{get_settings().yokan_api_base_url}/users/{user_id}/boards").respond(
        200, json={"message": "success", "data": mock_boards_data}
    )

    boards = await client.list_boards(user_id, token)
    assert len(boards) == 2
    assert isinstance(boards[0], yokan_models.Board)
    assert boards[0].id == 101


@pytest.mark.asyncio
@respx.mock
async def test_get_board(client):
    board_id = 101
    token = "test_token"
    mock_board_data = {"id": 101, "user_id": 1, "name": "Board 1", "data": {}}
    respx.get(f"{get_settings().yokan_api_base_url}/boards/{board_id}").respond(
        200, json={"message": "success", "data": mock_board_data}
    )

    board = await client.get_board(board_id, token)
    assert isinstance(board, yokan_models.Board)
    assert board.id == 101
    assert board.name == "Board 1"


@pytest.mark.asyncio
@respx.mock
async def test_create_board(client):
    user_id = 1
    name = "New Board"
    data = {"columns": {}}
    token = "test_token"
    mock_response_id = 103
    respx.post(f"{get_settings().yokan_api_base_url}/boards").respond(
        201, json={"message": "success", "data": {"id": mock_response_id}}
    )

    board_id = await client.create_board(user_id, name, data, token)
    assert board_id == mock_response_id


@pytest.mark.asyncio
@respx.mock
async def test_update_board(client):
    board_id = 101
    name = "Updated Board Name"
    data = {"columns": {}}
    token = "test_token"
    mock_changes = 1
    respx.put(f"{get_settings().yokan_api_base_url}/boards/{board_id}").respond(
        200,
        json={"message": "success", "data": {"id": board_id}, "changes": mock_changes},
    )

    changes = await client.update_board(board_id, name, data, token)
    assert changes == mock_changes


@pytest.mark.asyncio
@respx.mock
async def test_delete_board(client):
    board_id = 101
    token = "test_token"
    mock_changes = 1
    respx.delete(f"{get_settings().yokan_api_base_url}/boards/{board_id}").respond(
        200, json={"message": "deleted", "changes": mock_changes}
    )

    changes = await client.delete_board(board_id, token)
    assert changes == mock_changes


@pytest.mark.asyncio
@respx.mock
async def test_list_boards_http_error(client):
    user_id = 1
    token = "test_token"
    respx.get(f"{get_settings().yokan_api_base_url}/users/{user_id}/boards").respond(
        404, json={"message": "Not Found"}
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.list_boards(user_id, token)