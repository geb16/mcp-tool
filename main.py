from enterprise_mcp.data.db import init_database
from enterprise_mcp.logging import configure_logging
from enterprise_mcp.mcp.common import mcp


def main() -> None:
    configure_logging()
    init_database()
    mcp.run()


if __name__ == "__main__":
    main()
