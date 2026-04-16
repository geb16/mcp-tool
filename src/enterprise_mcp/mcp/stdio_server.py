"""Stdio transport entrypoint.

Bootstraps logging/database initialization and starts MCP stdio server mode.
"""

from enterprise_mcp.data.db import init_database
from enterprise_mcp.logging import configure_logging
from enterprise_mcp.mcp.common import mcp

if __name__ == "__main__":
    configure_logging()
    init_database()
    mcp.run()
