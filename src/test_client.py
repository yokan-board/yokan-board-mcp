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

import asyncio
import pytest
import httpx
import fastmcp as mcp_lib
from mcp import McpError
from fastmcp.exceptions import NotFoundError, ToolError
from mcp import McpError
from pytest_asyncio import fixture as async_fixture

from .config import get_settings
from . import yokan_models
from .main import AuthContext, NOT_FOUND

settings = get_settings()


# --- Helper function for Yokan API login ---
async def login_user(username, password):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.yokan_api_base_url}/login",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        return data["token"], data["data"]["id"]


# --- Pytest Fixtures ---
@async_fixture(scope="module")
async def auth_data():
    # Replace with actual test user credentials for Yokan API
    # Ensure this user exists in your Yokan Kanban Board instance
    username = "user"
    password = "password"
    token, user_id = await login_user(username, password)
    return {"token": token, "user_id": user_id}


@async_fixture(scope="function")
async def mcp_client(auth_data):
    client = mcp_lib.Client(
        get_settings().mcp_server_base_url, auth=f"Bearer {auth_data['token']}"
    )
    async with client:
        yield client


@async_fixture(scope="function")
async def created_board_id(mcp_client, auth_data):
    board_name = "Test Board for MCP Integration"
    # Since FastMCP requires auth parameter, we pass it explicitly
    result = await mcp_client.call_tool(
        "create_board",
        {
            "name": board_name,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    board_id = result.data
    # Add longer delay to ensure board is fully created and persisted
    await asyncio.sleep(0.5)

    # Double-check that the board exists before yielding
    try:
        get_result = await mcp_client.call_tool(
            "get_board",
            {
                "board_id": board_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
        # If this doesn't raise an exception, the board exists
    except Exception as e:
        print(f"Warning: Board {board_id} might not be ready: {e}")
        # We'll still yield the ID, but log this for debugging

    yield board_id
    await mcp_client.call_tool(
        "delete_board",
        {
            "board_id": board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )


@async_fixture(scope="function")
async def created_column_id(mcp_client, created_board_id, auth_data):
    column_name = "Test Column"
    result = await mcp_client.call_tool(
        "create_column",
        {
            "board_id": created_board_id,
            "name": column_name,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    column_id = result.data.id
    yield column_id
    # No cleanup needed as deleting the board will delete the column


# --- Integration Tests ---
@pytest.mark.asyncio
async def test_create_board(mcp_client, auth_data):
    board_name = "Another Test Board"
    board_id = (
        await mcp_client.call_tool(
            "create_board",
            {
                "name": board_name,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data
    await asyncio.sleep(0.1)
    assert isinstance(board_id, int)
    assert board_id > 0


@pytest.mark.asyncio
async def test_get_boards(mcp_client, auth_data, created_board_id):
    result = await mcp_client.call_tool(
        "get_boards",
        {"auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]}},
    )
    boards = result.data
    assert isinstance(boards, list)
    assert any(board["id"] == created_board_id for board in boards)


@pytest.mark.asyncio
async def test_get_board(mcp_client, created_board_id, auth_data):
    result = await mcp_client.call_tool(
        "get_board",
        {
            "board_id": created_board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    board = result.data
    # Handle both model object and dict formats
    board_id_value = board.id if hasattr(board, "id") else board["id"]
    board_name_value = board.name if hasattr(board, "name") else board["name"]
    assert board_id_value == created_board_id
    assert board_name_value == "Test Board for MCP Integration"


@pytest.mark.asyncio
async def test_update_board(mcp_client, created_board_id, auth_data):
    new_name = "Updated Test Board Name"
    result = await mcp_client.call_tool(
        "update_board",
        {
            "board_id": created_board_id,
            "name": new_name,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    changes = result.data
    assert changes == 1
    updated_result = await mcp_client.call_tool(
        "get_board",
        {
            "board_id": created_board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    updated_board = updated_result.data
    # Handle both model object and dict formats
    updated_board_name = (
        updated_board.name if hasattr(updated_board, "name") else updated_board["name"]
    )
    assert updated_board_name == new_name


@pytest.mark.asyncio
async def test_delete_board(mcp_client, auth_data):
    # Step 1: Create a board and save the ID
    create_result = await mcp_client.call_tool(
        "create_board",
        {
            "name": "Test Board for Deletion",
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    board_id = create_result.data
    await asyncio.sleep(0.5)  # Ensure board is created

    # Step 2: Get the board with the saved ID, confirm that call is successful
    get_result = await mcp_client.call_tool(
        "get_board",
        {
            "board_id": board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    retrieved_board = get_result.data
    assert retrieved_board.id == board_id

    # Step 3: If the previous step was successful, call delete board, and confirm it is successful
    delete_result = await mcp_client.call_tool(
        "delete_board",
        {
            "board_id": board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    changes = delete_result.data
    assert changes == 1

    # Verify the board is actually deleted
    with pytest.raises(ToolError):
        await mcp_client.call_tool(
            "get_board",
            {
                "board_id": board_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )


# This test will create its own board and delete it, so it doesn't rely on created_board_id fixture
@pytest.mark.asyncio
async def test_delete_non_existent_board(mcp_client, auth_data):
    non_existent_id = 999999  # Assuming this ID does not exist
    with pytest.raises(ToolError):
        await mcp_client.call_tool(
            "delete_board",
            {
                "board_id": non_existent_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )


# --- Column Management Tests ---


@pytest.mark.asyncio
async def test_create_column(mcp_client, created_board_id, auth_data):
    column_name = "New Test Column"
    result = await mcp_client.call_tool(
        "create_column",
        {
            "board_id": created_board_id,
            "name": column_name,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    column = result.data
    assert column.title == column_name
    assert column.id is not None


@pytest.mark.asyncio
async def test_get_columns(mcp_client, created_board_id, created_column_id, auth_data):
    result = await mcp_client.call_tool(
        "get_columns",
        {
            "board_id": created_board_id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    columns = result.data
    assert isinstance(columns, list)
    assert any(
        (col.id if hasattr(col, "id") else col["id"]) == created_column_id
        for col in columns
    )


@pytest.mark.asyncio
async def test_update_column(
    mcp_client, created_board_id, created_column_id, auth_data
):
    new_name = "Updated Column Name"
    result = await mcp_client.call_tool(
        "update_column",
        {
            "board_id": created_board_id,
            "column_id": created_column_id,
            "name": new_name,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    updated_column = result.data
    assert updated_column.title == new_name


@pytest.mark.asyncio
async def test_reorder_columns(mcp_client, created_board_id, auth_data):
    # Create a few columns
    col1 = (
        await mcp_client.call_tool(
            "create_column",
            {
                "board_id": created_board_id,
                "name": "Column 1",
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data
    col2 = (
        await mcp_client.call_tool(
            "create_column",
            {
                "board_id": created_board_id,
                "name": "Column 2",
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data

    # Reorder them
    new_order = [col2.id, col1.id]
    result = await mcp_client.call_tool(
        "reorder_columns",
        {
            "board_id": created_board_id,
            "column_ids": new_order,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    assert result.data == 1

    # Verify the new order
    board = (
        await mcp_client.call_tool(
            "get_board",
            {
                "board_id": created_board_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data
    assert board.data["columnOrder"] == new_order


@pytest.mark.asyncio
async def test_delete_column(mcp_client, created_board_id, auth_data):
    # Create a column to delete
    column_to_delete = (
        await mcp_client.call_tool(
            "create_column",
            {
                "board_id": created_board_id,
                "name": "To Be Deleted",
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data

    # Delete it
    result = await mcp_client.call_tool(
        "delete_column",
        {
            "board_id": created_board_id,
            "column_id": column_to_delete.id,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    assert result.data == 1

    # Verify it's gone
    columns = (
        await mcp_client.call_tool(
            "get_columns",
            {
                "board_id": created_board_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data
    assert not any(col["id"] == column_to_delete.id for col in columns)


@pytest.mark.asyncio
async def test_update_column_color(mcp_client, created_board_id, auth_data):
    # Create a column to update its color
    column_to_update = (
        await mcp_client.call_tool(
            "create_column",
            {
                "board_id": created_board_id,
                "name": "Color Test Column",
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data

    new_color = "#FF0000"  # Red
    result = await mcp_client.call_tool(
        "update_column_color",
        {
            "board_id": created_board_id,
            "column_id": column_to_update.id,
            "color": new_color,
            "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
        },
    )
    updated_column = result.data
    assert updated_column.highlightColor == new_color

    # Verify by getting the board again
    board = (
        await mcp_client.call_tool(
            "get_board",
            {
                "board_id": created_board_id,
                "auth": {"user_id": auth_data["user_id"], "token": auth_data["token"]},
            },
        )
    ).data
    assert board.data["columns"][column_to_update.id]["highlightColor"] == new_color
