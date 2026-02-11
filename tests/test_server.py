"""Tests for the Cinema 4D MCP Server."""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure package is importable when running tests from repo root (e.g. python tests/test_server.py)
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_tests_dir)
_src = os.path.join(_repo_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from cinema4d_mcp.server import send_to_c4d, C4DConnection

class TestC4DServer(unittest.TestCase):
    """Test cases for Cinema 4D server functionality."""

    def test_connection_disconnected(self):
        """Test behavior when connection is disconnected."""
        connection = C4DConnection(sock=None, connected=False)
        result = send_to_c4d(connection, {"command": "test"})
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Not connected to Cinema 4D")

    def test_send_to_c4d(self):
        """Test sending commands to C4D with a mocked socket."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'{"result": "success"}\n'

        connection = C4DConnection(sock=mock_sock, connected=True)
        result = send_to_c4d(connection, {"command": "test"})

        self.assertEqual(result, {"result": "success"})
        mock_sock.sendall.assert_called_once_with(b'{"command": "test"}\n')

    def test_send_to_c4d_response_in_multiple_chunks(self):
        """Test that response received in multiple recv chunks is assembled correctly."""
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [b'{"result": "succ', b'ess"}\n']

        connection = C4DConnection(sock=mock_sock, connected=True)
        result = send_to_c4d(connection, {"command": "test"})

        self.assertEqual(result, {"result": "success"})
        self.assertEqual(mock_sock.recv.call_count, 2)

    def test_send_to_c4d_exception(self):
        """Test error handling when sending fails."""
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = Exception("Test error")

        connection = C4DConnection(sock=mock_sock, connected=True)
        result = send_to_c4d(connection, {"command": "test"})

        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])


if __name__ == "__main__":
    unittest.main()