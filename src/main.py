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

import logging
import httpx
import uuid
from typing import List, Dict, Any, Optional, Callable, TypeVar, Coroutine, Annotated
import fastmcp as mcp_lib
from mcp import McpError
from mcp.types import ErrorData

# MCP Error Codes (integers)
UNAUTHENTICATED = 401
PERMISSION_DENIED = 403
NOT_FOUND = 404
INVALID_ARGUMENT = 400
UNKNOWN = 500


from fastmcp import Context
from pydantic import BaseModel
import functools

from .yokan_client import YokanClient

from . import yokan_models

from .config import get_settings


app_instance = mcp_lib.FastMCP("Yokan Kanban Board MCP Server")
app = app_instance.http_app()


class AuthContext(BaseModel):
    user_id: int
    token: str


yokan_client = YokanClient(base_url=get_settings().yokan_api_base_url)


R = TypeVar("R")


def error_handler(
    func: Callable[..., Coroutine[Any, Any, R]],
) -> Callable[..., Coroutine[Any, Any, R]]:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> R:
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            detail = e.response.json().get("message", str(e))
            if status_code == 401:
                raise McpError(error=ErrorData(code=UNAUTHENTICATED, message=detail))
            elif status_code == 403:
                raise McpError(error=ErrorData(code=PERMISSION_DENIED, message=detail))
            elif status_code == 404:
                raise McpError(error=ErrorData(code=NOT_FOUND, message=detail))
            elif status_code == 400:
                raise McpError(error=ErrorData(code=INVALID_ARGUMENT, message=detail))
            else:
                raise McpError(error=ErrorData(code=UNKNOWN, message=detail))
        except Exception as e:
            raise McpError(error=ErrorData(code=UNKNOWN, message=str(e)))

    return wrapper


@app_instance.tool
@error_handler
async def get_boards(
    auth: AuthContext,
) -> List[yokan_models.Board]:
    """Retrieves all Kanban boards for the authenticated user.

    Args:
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        List[yokan_models.Board]: A list of Kanban boards.
    """
    return await yokan_client.list_boards(user_id=auth.user_id, token=auth.token)


@app_instance.tool
@error_handler
async def get_board(
    board_id: int,
    auth: AuthContext,
) -> yokan_models.Board:
    """Retrieves a specific Kanban board by its ID.

    Args:
        board_id (int): The ID of the board to retrieve.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        yokan_models.Board: The requested Kanban board.
    """
    return await yokan_client.get_board(board_id=board_id, token=auth.token)


@app_instance.tool
@error_handler
async def create_board(
    name: str,
    auth: AuthContext,
    columns: List[str] = [],
) -> int:
    """Creates a new Kanban board with an optional list of initial column names.

    Args:
        name (str): The name of the new board.
        auth (AuthContext): The authentication context containing user ID and token.
        columns (List[str], optional): A list of names for initial columns. Defaults to an empty list.

    Returns:
        int: The ID of the newly created board.
    """
    data = (
        {
            "columns": {col: {"id": col, "title": col, "tasks": []} for col in columns},
            "columnOrder": columns,
        }
        if columns
        else {}
    )
    return await yokan_client.create_board(
        user_id=auth.user_id, name=name, data=data, token=auth.token
    )


@app_instance.tool
@error_handler
async def update_board(
    board_id: int,
    name: str,
    auth: AuthContext,
) -> int:
    """Updates the name of a Kanban board.

    Args:
        board_id (int): The ID of the board to update.
        name (str): The new name for the board.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        int: The ID of the updated board.
    """
    # For now, we only support updating the name.
    # The `data` field will be fetched from the existing board.
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    return await yokan_client.update_board(
        board_id=board_id, name=name, data=board.data, token=auth.token
    )


@app_instance.tool
@error_handler
async def delete_board(
    board_id: int,
    auth: AuthContext,
) -> int:
    """Deletes a Kanban board by its ID.

    Args:
        board_id (int): The ID of the board to delete.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        int: The ID of the deleted board.
    """
    return await yokan_client.delete_board(board_id=board_id, token=auth.token)


@app_instance.tool
@error_handler
async def create_column(
    board_id: int,
    name: str,
    auth: AuthContext,
) -> yokan_models.Column:
    """Creates a new column in a specified board.

    Args:
        board_id (int): The ID of the board to add the column to.
        name (str): The name of the new column.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        yokan_models.Column: The newly created column object.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data:
        board.data["columns"] = {}
    if "columnOrder" not in board.data:
        board.data["columnOrder"] = []
    new_column_id = str(uuid.uuid4())
    new_column = yokan_models.Column(
        id=new_column_id,
        title=name,
        tasks=[],
        highlightColor="#AF522B",
        minimized=False,
    )
    board.data["columns"][new_column_id] = new_column.dict()
    board.data["columnOrder"].append(new_column_id)
    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )
    return new_column


@app_instance.tool
@error_handler
async def get_columns(
    board_id: int,
    auth: AuthContext,
) -> List[yokan_models.Column]:
    """Retrieves all columns for a given board.

    Args:
        board_id (int): The ID of the board to retrieve columns from.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        List[yokan_models.Column]: A list of column objects.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data:
        return []
    return [yokan_models.Column(**col) for col in board.data["columns"].values()]


@app_instance.tool
@error_handler
async def update_column(
    board_id: int,
    column_id: str,
    name: str,
    auth: AuthContext,
) -> yokan_models.Column:
    """Updates the name of a column.

    Args:
        board_id (int): The ID of the board containing the column.
        column_id (str): The ID of the column to update.
        name (str): The new name for the column.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        yokan_models.Column: The updated column object.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))
    column = board.data["columns"][column_id]
    column["title"] = name
    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )
    return yokan_models.Column(**column)


@app_instance.tool
@error_handler
async def reorder_columns(
    board_id: int,
    column_ids: List[str],
    auth: AuthContext,
) -> int:
    """Reorders columns within a board.

    Args:
        board_id (int): The ID of the board containing the columns.
        column_ids (List[str]): A list of column IDs in the desired new order.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        int: The ID of the updated board.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    board.data["columnOrder"] = column_ids
    return await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )


@app_instance.tool
@error_handler
async def delete_column(
    board_id: int,
    column_id: str,
    auth: AuthContext,
) -> int:
    """Deletes a column from a board.

    Args:
        board_id (int): The ID of the board containing the column.
        column_id (str): The ID of the column to delete.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        int: The ID of the updated board.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))
    del board.data["columns"][column_id]
    if "columnOrder" in board.data:
        board.data["columnOrder"].remove(column_id)
    return await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )


@app_instance.tool
@error_handler
async def update_column_color(
    board_id: int,
    column_id: str,
    color: str,
    auth: AuthContext,
) -> yokan_models.Column:
    """Updates the highlight color of a specified column.

    Args:
        board_id (int): The ID of the board containing the column.
        column_id (str): The ID of the column to update.
        color (str): The new highlight color for the column (e.g., "red", "#FF0000").
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        yokan_models.Column: The updated column object.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))

    column = board.data["columns"][column_id]
    column["highlightColor"] = color

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )
    return yokan_models.Column(**column)


@app_instance.tool
@error_handler
async def create_task(
    board_id: int,
    column_id: str,
    title: str,
    auth: AuthContext,
    description: Optional[str] = None,
    dueDate: Optional[str] = None,
) -> str:
    """Creates a new task in a specified column with optional description and due date.

    Args:
        board_id (int): The ID of the board containing the column.
        column_id (str): The ID of the column to add the task to.
        title (str): The title of the new task.
        auth (AuthContext): The authentication context containing user ID and token.
        description (Optional[str], optional): The description of the task. Defaults to None.
        dueDate (Optional[str], optional): The due date of the task (e.g., "YYYY-MM-DD"). Defaults to None.

    Returns:
        str: The ID of the newly created task.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))

    column = board.data["columns"][column_id]
    if "tasks" not in column:
        column["tasks"] = []

    task_id = str(uuid.uuid4())
    new_task = {
        "id": task_id,
        "content": title,
        "description": description,
        "dueDate": dueDate,
    }
    column["tasks"].append(new_task)

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )
    return task_id


@app_instance.tool
@error_handler
async def create_tasks(
    board_id: int,
    column_id: str,
    tasks: List[Dict],
    auth: AuthContext,
) -> List[str]:
    """Creates multiple new tasks in a specified column.

    Args:
        board_id (int): The ID of the board containing the column.
        column_id (str): The ID of the column to add the tasks to.
        tasks (List[Dict]): A list of dictionaries, where each dictionary represents a task and contains 'title' and optional 'description' and 'dueDate'.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        List[str]: A list of IDs for the newly created tasks.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))

    column = board.data["columns"][column_id]
    if "tasks" not in column:
        column["tasks"] = []

    new_task_ids = []
    for task_data in tasks:
        task_id = str(uuid.uuid4())
        new_task = {
            "id": task_id,
            "content": task_data.get("title"),
            "description": task_data.get("description"),
            "dueDate": task_data.get("dueDate"),
        }
        column["tasks"].append(new_task)
        new_task_ids.append(task_id)

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )
    return new_task_ids


@app_instance.tool
@error_handler
async def get_tasks(
    board_id: int,
    auth: AuthContext,
    column_id: Optional[str] = None,
) -> List[Dict]:
    """Retrieves all tasks for a given board, optionally filtered by column.

    Args:
        board_id (int): The ID of the board to retrieve tasks from.
        auth (AuthContext): The authentication context containing user ID and token.
        column_id (Optional[str], optional): The ID of the column to filter tasks by. If None, retrieves tasks from all columns. Defaults to None.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a task.
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data:
        return []

    if column_id:
        if column_id not in board.data["columns"]:
            raise McpError(error=ErrorData(code=NOT_FOUND, message="Column not found"))
        return board.data["columns"][column_id].get("tasks", [])

    all_tasks = []
    for col in board.data["columns"].values():
        all_tasks.extend(col.get("tasks", []))
    return all_tasks


@app_instance.tool
@error_handler
async def update_task(
    board_id: int,
    task_id: str,
    auth: AuthContext,
    title: Optional[str] = None,
    description: Optional[str] = None,
    dueDate: Optional[str] = None,
    subtasks: Optional[List[str]] = None,
) -> None:
    """Updates the title, description, due date, and/or subtasks of an existing task.

    Args:
        board_id (int): The ID of the board containing the task.
        task_id (str): The ID of the task to update.
        auth (AuthContext): The authentication context containing user ID and token.
        title (Optional[str], optional): The new title for the task. Defaults to None.
        description (Optional[str], optional): The new description for the task. Defaults to None.
        dueDate (Optional[str], optional): The new due date for the task (e.g., "YYYY-MM-DD"). Defaults to None.
        subtasks (Optional[List[str]], optional): A list of subtask IDs. Defaults to None.

    Returns:
        None
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Task not found"))

    task_found = False
    for column in board.data["columns"].values():
        for task in column.get("tasks", []):
            if task.get("id") == task_id:
                if title is not None:
                    task["content"] = title
                if description is not None:
                    task["description"] = description
                if dueDate is not None:
                    task["dueDate"] = dueDate
                if subtasks is not None:
                    task["subtasks"] = subtasks
                task_found = True
                break
        if task_found:
            break

    if not task_found:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Task not found"))

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )


@app_instance.tool
@error_handler
async def move_task(
    board_id: int,
    task_id: str,
    new_column_id: str,
    auth: AuthContext,
) -> None:
    """Moves a task from one column to another.

    Args:
        board_id (int): The ID of the board containing the task.
        task_id (str): The ID of the task to move.
        new_column_id (str): The ID of the destination column.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        None
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data or new_column_id not in board.data["columns"]:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="New column not found"))

    task_to_move = None
    for column in board.data["columns"].values():
        for i, task in enumerate(column.get("tasks", [])):
            if task.get("id") == task_id:
                task_to_move = column["tasks"].pop(i)
                break
        if task_to_move:
            break

    if not task_to_move:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Task not found"))

    board.data["columns"][new_column_id].setdefault("tasks", []).append(task_to_move)

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )


@app_instance.tool
@error_handler
async def delete_task(
    board_id: int,
    task_id: str,
    auth: AuthContext,
) -> None:
    """Deletes a task from a board.

    Args:
        board_id (int): The ID of the board containing the task.
        task_id (str): The ID of the task to delete.
        auth (AuthContext): The authentication context containing user ID and token.

    Returns:
        None
    """
    board = await yokan_client.get_board(board_id=board_id, token=auth.token)
    if "columns" not in board.data:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Task not found"))

    task_found = False
    for column in board.data["columns"].values():
        for i, task in enumerate(column.get("tasks", [])):
            if task.get("id") == task_id:
                del column["tasks"][i]
                task_found = True
                break
        if task_found:
            break

    if not task_found:
        raise McpError(error=ErrorData(code=NOT_FOUND, message="Task not found"))

    await yokan_client.update_board(
        board_id=board_id, name=board.name, data=board.data, token=auth.token
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Yokan API Base URL: {get_settings().yokan_api_base_url}")
    app_instance.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8888,
        path="/mcp",
    )