# MCP-Claude-AI Server

MCP-Claude-AI Server connects Cinema 4D to Claude via the Model Context Protocol, enabling prompt-assisted 3D scene manipulation from an AI assistant.

## Table of Contents

- Components
- Prerequisites
- Installation
- Setup
- Usage
- Testing
- Troubleshooting and Debugging
- Project File Structure
- Tool Commands
- Compatibility and Roadmap
- Recent Fixes

## Components

1. **C4D Plugin**: A socket server that runs inside Cinema 4D, listens for commands from the MCP server, and executes them in the Cinema 4D environment. Delivered as `mcp_server_plugin.pyp`.

2. **MCP Server**: A Python server (FastMCP) that implements the MCP protocol and exposes tools that send JSON commands over TCP to the Cinema 4D plugin. Connection is configurable via `C4D_HOST` and `C4D_PORT` (default: 127.0.0.1:5555).

## Prerequisites

- Cinema 4D (R2024+ recommended)
- Python 3.9 or higher (for the MCP server)

## Installation

### Clone the Repository

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd cinema4d-mcp
```

### Install the MCP Server Package

From the project root:

```bash
pip install -e .
```

Or with uv:

```bash
uv sync
```

### Make the Wrapper Script Executable (Unix-like systems)

```bash
chmod +x bin/cinema4d-mcp-wrapper
```

## Setup

### Cinema 4D Plugin Setup

1. **Copy the plugin**: Copy `c4d_plugin/mcp_server_plugin.pyp` into Cinema 4D’s plugin folder:
   - macOS: `~/Library/Preferences/Maxon/Maxon Cinema 4D/plugins/`
   - Windows: `%APPDATA%\Maxon\Maxon Cinema 4D\plugins\`

2. **Start the socket server in C4D**:
   - Open Cinema 4D.
   - Go to Extensions > Socket Server Plugin.
   - In the Socket Server Control dialog, click Start Server.

### Claude Desktop (or Cursor) Configuration

Edit the MCP client config so it runs the Cinema 4D MCP server.

**Development (run from project):**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Or in Claude Desktop: Settings > Developer > Edit Config.

Add an MCP server entry, for example:

```json
"mcpServers": {
  "cinema4d": {
    "command": "python3",
    "args": ["/path/to/cinema4d-mcp/main.py"]
  }
}
```

Replace `/path/to/cinema4d-mcp` with the actual path to this project.

**Installed package (published / wrapper):**

```json
"mcpServers": {
  "cinema4d": {
    "command": "cinema4d-mcp-wrapper",
    "args": []
  }
}
```

Restart Claude Desktop (or your MCP host) after changing the config.

## Usage

1. Start the Cinema 4D Socket Server in C4D (see Setup).
2. Start your MCP client (e.g. Claude Desktop or Cursor) with the cinema4d server configured.
3. Use the tool commands listed below to interact with Cinema 4D through the assistant.

## Testing

### Command Line

Run the server directly to confirm it starts and connects to Cinema 4D:

```bash
python main.py
```

Or from the installed package:

```bash
cinema4d-mcp-wrapper
```

Expected: startup logs and a message indicating connection to the Cinema 4D socket (or a clear failure if C4D is not running or the plugin is not started).

### MCP Test Harness

The repo includes a small test harness for predefined command sequences.

- **Test command file**: `tests/mcp_test_harness.jsonl` — JSONL file where each line is one MCP command with parameters.
- **GUI test runner**: `tests/mcp_test_harness_gui.py` — Tkinter GUI to load a JSONL file and run commands in order.

Run the GUI:

```bash
python tests/mcp_test_harness_gui.py
```

You can select a JSONL file, run the sequence, and inspect responses from Cinema 4D. Useful for testing new commands, verifying the plugin after changes, and reproducing scenes for debugging.

## Troubleshooting and Debugging

1. **Logs**: Check MCP client logs (e.g. Claude Desktop: `~/Library/Logs/Claude/mcp*.log` on macOS, or the equivalent on Windows). Use `tail -f` on the relevant log to watch output while reproducing an issue.

2. **Cinema 4D**: After opening the MCP client, verify that Cinema 4D’s console or Socket Server UI shows an incoming connection.

3. **Wrapper**: Run the server by hand to see errors:
   ```bash
   cinema4d-mcp-wrapper
   ```

4. **Missing mcp module**: If the client reports that the `mcp` module is not found, install it (and the project) in the same Python used by the config:
   ```bash
   pip install mcp
   pip install -e .
   ```

5. **Advanced debugging**: Use the MCP Inspector (from the modelcontextprotocol organization) to run and inspect the server, for example:
   ```bash
   npx @modelcontextprotocol/inspector uv --directory /path/to/cinema4d-mcp run cinema4d-mcp
   ```
   Replace `/path/to/cinema4d-mcp` with your project path.

## Project File Structure

```
cinema4d-mcp/
├── .gitignore
├── .python-version
├── LICENSE
├── README.md
├── main.py
├── pyproject.toml
├── setup.py
├── uv.lock
├── bin/
│   └── cinema4d-mcp-wrapper
├── c4d_plugin/
│   └── mcp_server_plugin.pyp
├── src/
│   └── cinema4d_mcp/
│       ├── __init__.py
│       ├── config.py
│       ├── server.py
│       └── utils.py
└── tests/
    ├── test_server.py
    ├── mcp_test_harness.jsonl
    └── mcp_test_harness_gui.py
```

- `main.py`: Script entry point; adds paths and calls package `main()`.
- `src/cinema4d_mcp/server.py`: FastMCP app, tool definitions, and TCP communication with the C4D plugin.
- `src/cinema4d_mcp/config.py`: `C4D_HOST` and `C4D_PORT` from environment.
- `bin/cinema4d-mcp-wrapper`: Shell script that finds a Python with `mcp` and runs `cinema4d_mcp` as a module.

## Tool Commands

### General Scene and Execution

- `get_scene_info`: Summary of the active Cinema 4D scene.
- `list_objects`: List scene objects with hierarchy.
- `group_objects`: Group selected objects under a new null.
- `execute_python`: Run custom Python code inside Cinema 4D.
- `save_scene`: Save the current project to disk.
- `load_scene`: Load a `.c4d` file.
- `set_keyframe`: Set a keyframe on an object property (position, rotation, etc.).

### Object Creation and Modification

- `add_primitive`: Add a primitive (cube, sphere, cone, etc.).
- `modify_object`: Change transform or attributes of an existing object.
- `create_abstract_shape`: Create an organic, non-standard abstract shape.

### Cameras and Animation

- `create_camera`: Add a camera.
- `animate_camera`: Animate a camera along a path (linear or spline).

### Lighting and Materials

- `create_light`: Add a light (omni, spot, etc.).
- `create_material`: Create a standard Cinema 4D material.
- `apply_material`: Apply a material to an object.
- `apply_shader`: Generate and apply a stylized or procedural shader.

### Redshift

- `validate_redshift_materials`: Check Redshift material setup and connections. Redshift materials are not fully implemented.

### MoGraph and Fields

- `create_mograph_cloner`: Add a MoGraph Cloner (linear, radial, grid, etc.).
- `add_effector`: Add a MoGraph Effector (e.g. Random, Plain).
- `apply_mograph_fields`: Add and link a MoGraph Field to objects.

### Dynamics and Physics

- `create_soft_body`: Add a Soft Body tag.
- `apply_dynamics`: Apply Rigid or Soft Body physics.

### Rendering and Preview

- `render_frame`: Render a frame and save to disk. May fail at large resolutions (MemoryError: Bitmap Init failed).
- `render_preview`: Quick preview render; returns base64 image for the AI.
- `snapshot_scene`: Capture scene summary (objects plus preview image).

## Compatibility and Roadmap

| Cinema 4D Version | Python Version | Status        | Notes |
|-------------------|----------------|---------------|-------|
| R21 / S22         | Python 2.7     | Not supported | Legacy API and Python version |
| R23               | Python 3.7     | Not planned   | Not tested |
| S24 / R25 / S26   | Python 3.9     | Possible TBD  | Needs testing and fallbacks |
| 2023.0 / 2023.1   | Python 3.9     | In progress   | Fallback support for core features |
| 2023.2            | Python 3.10    | In progress   | Aligns with testing base |
| 2024.0            | Python 3.11    | Supported     | Verified |
| 2025.0+           | Python 3.11    | Fully supported | Primary development target |

**Goals:**

- **Short term**: Compatibility with C4D 2023.1+ (Python 3.9 and 3.10).
- **Mid term**: Conditional handling for missing MoGraph and Field APIs.
- **Long term**: Optional legacy plugin for R23–S26 if needed.

## Recent Fixes

- **Context awareness**: Object tracking uses GUIDs. Commands that create objects return context (guid, actual_name, etc.); later commands use these GUIDs to find objects reliably.
- **Object finding**: `find_object_by_name` updated to handle GUIDs (numeric string format), fix recursion issues, and behave correctly when `doc.SearchObject` fails.
- **GUID handling**: Handlers for `apply_material`, `create_mograph_cloner`, `add_effector`, `apply_mograph_fields`, `set_keyframe`, and `group_objects` detect GUIDs in parameters (object_name, target, target_name, list items) and resolve them correctly.
- **create_mograph_cloner**: AttributeError for missing MoGraph parameters (e.g. MG_LINEAR_PERSTEP) addressed with getattr fallbacks; fixed logic so the correct object is used for cloning.
- **Rendering**: TypeError in `render_frame` around `doc.ExecutePasses` fixed. `snapshot_scene` uses the correct base64 render path. Large `render_frame` still subject to memory limits.
- **Registration**: AttributeError for `c4d.NilGuid` fixed.
