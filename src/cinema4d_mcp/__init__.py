"""Cinema 4D MCP Server - Connect Claude to Cinema 4D."""

__version__ = "0.1.2"
__all__ = ["main", "main_wrapper", "mcp_app", "__version__"]

from . import server

mcp_app = server.mcp_app


def main() -> None:
    """Main entry point for the package."""
    server.mcp_app.run()


def main_wrapper() -> None:
    """Entry point for the wrapper script."""
    main()