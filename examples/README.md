# MCP Client Examples

This directory contains example client code for interacting with the Yokan Board MCP Server.

## `mcp_client.py`

This Python script demonstrates how to use the `fastmcp` client library to interact with the Yokan Board MCP server. It includes examples of:

-   Authenticating with the Yokan API to obtain a JWT token.
-   Initializing the `fastmcp` client.
-   Calling various tools exposed by the MCP server, such as `create_board`, `get_boards`, and `delete_board`.

### How to Run

1.  Ensure the Yokan Board MCP Server is running (see the main `README.md` for instructions).
2.  Ensure you have a valid Yokan API instance running and accessible.
3.  Update the `YOKAN_API_TOKEN` and `YOKAN_USER_ID` variables in `mcp_client.py` with your actual token and user ID.
4.  Run the script:
    ```bash
    python mcp_client.py
    ```
