"""Configuration handling for Cinema 4D MCP Server."""

import os
from dataclasses import dataclass
from typing import List

__all__ = [
    "C4D_HOST",
    "C4D_PORT",
    "C4D_TIMEOUT_DEFAULT",
    "C4D_TIMEOUT_LONG",
    "C4D_TIMEOUT_CHECK",
    "C4D_LOG_LEVEL",
    "LONG_TIMEOUT_COMMANDS",
    "C4DConfig",
]

# Environment keys
_ENV_HOST = "C4D_HOST"
_ENV_PORT = "C4D_PORT"
_ENV_TIMEOUT_DEFAULT = "C4D_TIMEOUT_DEFAULT"
_ENV_TIMEOUT_LONG = "C4D_TIMEOUT_LONG"
_ENV_TIMEOUT_CHECK = "C4D_TIMEOUT_CHECK"
_ENV_LOG_LEVEL = "C4D_LOG_LEVEL"

# Defaults (aligned with C4D plugin: host 127.0.0.1, port 5555)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
DEFAULT_TIMEOUT = 20
LONG_OPERATION_TIMEOUT = 120
CONNECTION_CHECK_TIMEOUT = 5
VALID_PORT_RANGE = (1, 65535)

# Commands that use long timeout (render, snapshot, field operations)
LONG_TIMEOUT_COMMANDS: List[str] = [
    "render_frame",
    "render_preview",
    "snapshot_scene",
    "apply_mograph_fields",
]


def _parse_port() -> int:
    raw = os.environ.get(_ENV_PORT, str(DEFAULT_PORT))
    try:
        port = int(raw)
        if VALID_PORT_RANGE[0] <= port <= VALID_PORT_RANGE[1]:
            return port
    except ValueError:
        pass
    return DEFAULT_PORT


def _parse_timeout(env_key: str, default: int) -> int:
    raw = os.environ.get(env_key)
    if raw is None:
        return default
    try:
        value = int(raw)
        return max(1, value) if value > 0 else default
    except ValueError:
        return default


# Resolved configuration values
C4D_HOST: str = os.environ.get(_ENV_HOST, DEFAULT_HOST)
C4D_PORT: int = _parse_port()
C4D_TIMEOUT_DEFAULT: int = _parse_timeout(_ENV_TIMEOUT_DEFAULT, DEFAULT_TIMEOUT)
C4D_TIMEOUT_LONG: int = _parse_timeout(_ENV_TIMEOUT_LONG, LONG_OPERATION_TIMEOUT)
C4D_TIMEOUT_CHECK: int = _parse_timeout(_ENV_TIMEOUT_CHECK, CONNECTION_CHECK_TIMEOUT)
C4D_LOG_LEVEL: str = os.environ.get(_ENV_LOG_LEVEL, "DEBUG").upper()


@dataclass(frozen=True)
class C4DConfig:
    """Immutable config snapshot for passing around or testing."""

    host: str
    port: int
    timeout_default: int
    timeout_long: int
    timeout_check: int
    long_timeout_commands: tuple

    @classmethod
    def from_env(cls) -> "C4DConfig":
        return cls(
            host=C4D_HOST,
            port=C4D_PORT,
            timeout_default=C4D_TIMEOUT_DEFAULT,
            timeout_long=C4D_TIMEOUT_LONG,
            timeout_check=C4D_TIMEOUT_CHECK,
            long_timeout_commands=tuple(LONG_TIMEOUT_COMMANDS),
        )
