"""Utility functions for Cinema 4D MCP Server."""

import socket
import sys
import logging
from typing import Optional

from .config import C4D_HOST, C4D_PORT, C4D_TIMEOUT_CHECK, C4D_LOG_LEVEL

# Logger name for this package
LOG_NAME = "cinema4d-mcp"

# Use a single logger; avoid re-adding handlers if already configured
logger = logging.getLogger(LOG_NAME)
if not logger.handlers:
    _level = getattr(logging, C4D_LOG_LEVEL, logging.DEBUG)
    logger.setLevel(_level)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(_handler)


def check_c4d_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
    timeout: Optional[int] = None,
) -> bool:
    """
    Check if the Cinema 4D socket server is reachable.

    Args:
        host: C4D host (default from config).
        port: C4D port (default from config).
        timeout: Socket timeout in seconds (default from config C4D_TIMEOUT_CHECK).

    Returns:
        True if connection succeeds, False otherwise.
    """
    host = host if host is not None else C4D_HOST
    port = port if port is not None else C4D_PORT
    timeout = timeout if timeout is not None else C4D_TIMEOUT_CHECK
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error("Error checking Cinema 4D connection: %s", e)
        return False
