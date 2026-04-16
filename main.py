"""Application CLI entrypoint.

This module boots structured logging, initializes database schema/seed data,
and starts the MCP server runtime.
"""

from enterprise_mcp.data.db import init_database
from enterprise_mcp.logging import configure_logging
from enterprise_mcp.mcp.common import mcp


def main() -> None:
    """Start the MCP server using local runtime defaults."""
    configure_logging()
    init_database()
    mcp.run()


if __name__ == "__main__":
    main()
