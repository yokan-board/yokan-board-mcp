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

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )
    yokan_api_base_url: str = Field(..., alias="YOKAN_API_BASE_URL")
    #    mcp_server_base_url: str = Field("http://macbook-pro-2018.fairway17:8888/mcp", alias="MCP_SERVER_BASE_URL")
    mcp_server_base_url: str = Field(
        "http://localhost:8888/mcp", alias="MCP_SERVER_BASE_URL"
    )


def get_settings() -> Settings:
    return Settings()


settings = get_settings()