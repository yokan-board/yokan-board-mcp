#!/usr/bin/env python
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
import fastmcp as mcp_lib

# --- Configuration ---
MCP_SERVER_URL = "http://localhost:8888/mcp"
# Replace with your actual token and user ID from the Yokan API
# You can obtain a token by sending a POST request to the /login endpoint of your Yokan API.
YOKAN_API_TOKEN = "your-jwt-token"
YOKAN_USER_ID = 1

async def main():
    # Initialize the client with the authentication token
    client = mcp_lib.Client(MCP_SERVER_URL, auth=f"Bearer {YOKAN_API_TOKEN}")

    async with client:
        try:
            # Define the authentication context required by the tools
            auth_context = {"user_id": YOKAN_USER_ID, "token": YOKAN_API_TOKEN}

            # 1. Create a new board
            board_name = "My New MCP Board"
            create_result = await client.call_tool(
                "create_board",
                {
                    "name": board_name,
                    "auth": auth_context,
                },
            )
            board_id = create_result.data
            print(f"Successfully created board with ID: {board_id}")

            # 2. Get the list of boards to verify creation
            get_boards_result = await client.call_tool("get_boards", {"auth": auth_context})
            boards = get_boards_result.data
            print("Current boards:")
            for board in boards:
                print(f"- {board['name']} (ID: {board['id']})")

            # 3. Delete the board
            await client.call_tool(
                "delete_board",
                {
                    "board_id": board_id,
                    "auth": auth_context,
                },
            )
            print(f"Successfully deleted board with ID: {board_id}")

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())