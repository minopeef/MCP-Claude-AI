#!/usr/bin/env python3
"""
Cinema 4D MCP Server - Main entry point script.

Runs as a script or module; ensures package is on path and starts the MCP server.
"""

import os
import sys
import traceback

# Ensure package is importable when run as script from project root
_root = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_root, "src")
if os.path.isdir(_src):
    sys.path.insert(0, _src)
sys.path.insert(0, _root)


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    """Main entry point."""
    _log("========== CINEMA 4D MCP SERVER STARTING ==========")
    _log(f"Python: {sys.version.split()[0]}")
    _log(f"CWD: {os.getcwd()}")

    try:
        from cinema4d_mcp.config import C4D_HOST, C4D_PORT, C4D_TIMEOUT_CHECK
    except ImportError:
        C4D_HOST = os.environ.get("C4D_HOST", "127.0.0.1")
        C4D_PORT = int(os.environ.get("C4D_PORT", "5555"))
        C4D_TIMEOUT_CHECK = 5

    _log(f"Checking Cinema 4D at {C4D_HOST}:{C4D_PORT} ...")
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(C4D_TIMEOUT_CHECK)
            sock.connect((C4D_HOST, C4D_PORT))
        _log("✅ Connected to Cinema 4D socket.")
    except Exception as e:
        _log(f"❌ No Cinema 4D socket: {e}")
        _log("   Server will start; C4D tools will fail until the plugin is running.")

    try:
        from cinema4d_mcp import main as _run
        _log("🚀 Starting Cinema 4D MCP Server...")
        _run()
    except Exception as e:
        _log(f"❌ Error: {e}")
        _log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
