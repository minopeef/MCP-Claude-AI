"""Cinema 4D MCP Server."""

import socket
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context
from starlette.routing import Route
from starlette.responses import JSONResponse

from .config import (
    C4D_HOST,
    C4D_PORT,
    C4D_TIMEOUT_CHECK,
    C4D_TIMEOUT_DEFAULT,
    C4D_TIMEOUT_LONG,
    LONG_TIMEOUT_COMMANDS,
)
from .utils import logger, check_c4d_connection

# Constants
MSG_NOT_CONNECTED = "❌ Not connected to Cinema 4D"
RECV_CHUNK_SIZE = 8192


@dataclass
class C4DConnection:
    sock: Optional[socket.socket] = None
    connected: bool = False


@asynccontextmanager
async def c4d_connection_context():
    """Asynchronous context manager for Cinema 4D connection."""
    connection = C4DConnection()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(C4D_TIMEOUT_CHECK)
        sock.connect((C4D_HOST, C4D_PORT))
        connection.sock = sock
        connection.connected = True
        logger.info("✅ Connected to Cinema 4D at %s:%s", C4D_HOST, C4D_PORT)
        yield connection
    except Exception as e:
        logger.error("❌ Failed to connect to Cinema 4D: %s", e)
        connection.connected = False
        yield connection
    finally:
        if connection.sock:
            connection.sock.close()
            logger.info("🔌 Disconnected from Cinema 4D")


def _run_command(connection: C4DConnection, command: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    """Execute a command and return either an error string or the response dict."""
    if not connection.connected or not connection.sock:
        return MSG_NOT_CONNECTED
    response = send_to_c4d(connection, command)
    if "error" in response:
        return f"❌ Error: {response['error']}"
    return response


def send_to_c4d(connection: C4DConnection, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to Cinema 4D and get the response with improved timeout handling."""
    if not connection.connected or not connection.sock:
        return {"error": "Not connected to Cinema 4D"}

    # Set appropriate timeout based on command type
    command_type = command.get("command", "")

    # Long-running operations use configurable long timeout
    if command_type in LONG_TIMEOUT_COMMANDS:
        timeout = C4D_TIMEOUT_LONG
        logger.info(f"Using extended timeout ({timeout}s) for {command_type}")
    else:
        timeout = C4D_TIMEOUT_DEFAULT

    try:
        # Convert command to JSON and send it
        command_json = json.dumps(command) + "\n"  # Add newline as message delimiter
        logger.debug(f"Sending command: {command_type}")
        connection.sock.sendall(command_json.encode("utf-8"))

        # Set socket timeout
        connection.sock.settimeout(timeout)

        # Receive response
        response_data = b""
        start_time = time.time()
        max_time = start_time + timeout

        # Log for long-running operations
        if command_type in LONG_TIMEOUT_COMMANDS:
            logger.info(
                f"Waiting for response from {command_type} (timeout: {timeout}s)"
            )

        while time.time() < max_time:
            try:
                chunk = connection.sock.recv(RECV_CHUNK_SIZE)
                if not chunk:
                    # If we receive an empty chunk, the connection might be closed
                    if not response_data:
                        logger.error(
                            f"Connection closed by Cinema 4D during {command_type}"
                        )
                        return {
                            "error": f"Connection closed by Cinema 4D during {command_type}"
                        }
                    break

                response_data += chunk

                # For long operations, log progress on data receipt
                elapsed = time.time() - start_time
                if command_type in LONG_TIMEOUT_COMMANDS and elapsed > 5:
                    logger.debug(
                        f"Received partial data for {command_type} ({len(response_data)} bytes, {elapsed:.1f}s elapsed)"
                    )

                if b"\n" in chunk:  # Message complete when we see a newline
                    logger.debug(f"Received complete response for {command_type}")
                    break

            except socket.timeout:
                logger.error(f"Socket timeout while receiving data for {command_type}")
                return {
                    "error": f"Timeout waiting for response from Cinema 4D ({timeout}s) for {command_type}"
                }

        # Parse and return response
        if not response_data:
            logger.error(f"No response received from Cinema 4D for {command_type}")
            return {"error": f"No response received from Cinema 4D for {command_type}"}

        response_text = response_data.decode("utf-8").strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, log the exact response for debugging
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response (first 200 chars): {response_text[:200]}...")
            return {"error": f"Invalid response from Cinema 4D: {str(e)}"}

    except socket.timeout:
        logger.error(f"Socket timeout during {command_type} ({timeout}s)")
        return {
            "error": f"Timeout communicating with Cinema 4D ({timeout}s) for {command_type}"
        }
    except Exception as e:
        logger.error(f"Communication error during {command_type}: {str(e)}")
        return {"error": f"Communication error: {str(e)}"}


async def homepage(request):
    """Handle homepage requests to check if server is running."""
    c4d_available = check_c4d_connection(C4D_HOST, C4D_PORT)
    return JSONResponse(
        {
            "status": "ok",
            "cinema4d_connected": c4d_available,
            "host": C4D_HOST,
            "port": C4D_PORT,
        }
    )


# Initialize our FastMCP server
mcp = FastMCP(title="Cinema4D", routes=[Route("/", endpoint=homepage)])


@mcp.tool()
async def get_scene_info(ctx: Context) -> str:
    """Get information about the current Cinema 4D scene."""
    async with c4d_connection_context() as connection:
        result = _run_command(connection, {"command": "get_scene_info"})
        if isinstance(result, str):
            return result
        scene_info = result.get("scene_info", {})
        return f"""
# Cinema 4D Scene Information
- **Filename**: {scene_info.get('filename', 'Untitled')}
- **Objects**: {scene_info.get('object_count', 0)}
- **Polygons**: {scene_info.get('polygon_count', 0):,}
- **Materials**: {scene_info.get('material_count', 0)}
- **Current Frame**: {scene_info.get('current_frame', 0)}
- **FPS**: {scene_info.get('fps', 30)}
- **Frame Range**: {scene_info.get('frame_start', 0)} - {scene_info.get('frame_end', 90)}
"""


@mcp.tool()
async def add_primitive(
    primitive_type: str,
    name: Optional[str] = None,
    position: Optional[List[float]] = None,
    size: Optional[List[float]] = None,
    ctx: Context = None,
) -> str:
    """
    Add a primitive object to the Cinema 4D scene.

    Args:
        primitive_type: Type of primitive (cube, sphere, cone, cylinder, plane, etc.)
        name: Optional name for the new object
        position: Optional [x, y, z] position
        size: Optional [x, y, z] size or dimensions
    """
    command = {"command": "add_primitive", "type": primitive_type}
    if name:
        command["object_name"] = name
    if position:
        command["position"] = position
    if size:
        command["size"] = size
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def modify_object(
    object_name: str, properties: Dict[str, Any], ctx: Context
) -> str:
    """
    Modify properties of an existing object.

    Args:
        object_name: Name of the object to modify
        properties: Dictionary of properties to modify (position, rotation, scale, etc.)
    """
    async with c4d_connection_context() as connection:
        return _run_command(
            connection,
            {"command": "modify_object", "object_name": object_name, "properties": properties},
        )


@mcp.tool()
async def list_objects(ctx: Context) -> str:
    """List all objects in the current Cinema 4D scene."""
    async with c4d_connection_context() as connection:
        result = _run_command(connection, {"command": "list_objects"})
        if isinstance(result, str):
            return result
        return result


@mcp.tool()
async def create_material(
    name: str,
    color: Optional[List[float]] = None,
    properties: Optional[Dict[str, Any]] = None,
    ctx: Context = None,
) -> str:
    """
    Create a new material in Cinema 4D.

    Args:
        name: Name for the new material
        color: Optional [R, G, B] color (values 0-1)
        properties: Optional additional material properties
    """
    command = {"command": "create_material", "material_name": name}
    if color:
        command["color"] = color
    if properties:
        command["properties"] = properties
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def apply_material(material_name: str, object_name: str, ctx: Context) -> str:
    """
    Apply a material to an object.

    Args:
        material_name: Name of the material to apply
        object_name: Name of the object to apply the material to
    """
    async with c4d_connection_context() as connection:
        return _run_command(
            connection,
            {"command": "apply_material", "material_name": material_name, "object_name": object_name},
        )


@mcp.tool()
async def render_frame(
    output_path: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    ctx: Context = None,
) -> str:
    """
    Render the current frame.

    Args:
        output_path: Optional path to save the rendered image
        width: Optional render width in pixels
        height: Optional render height in pixels
    """
    command = {"command": "render_frame"}
    if output_path:
        command["output_path"] = output_path
    if width:
        command["width"] = width
    if height:
        command["height"] = height
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def set_keyframe(
    object_name: str, property_name: str, value: Any, frame: int, ctx: Context
) -> str:
    """
    Set a keyframe for an object property.

    Args:
        object_name: Name of the object
        property_name: Name of the property to keyframe (e.g., 'position.x')
        value: Value to set at the keyframe
        frame: Frame number to set the keyframe at
    """
    async with c4d_connection_context() as connection:
        return _run_command(
            connection,
            {
                "command": "set_keyframe",
                "object_name": object_name,
                "property_name": property_name,
                "value": value,
                "frame": frame,
            },
        )


@mcp.tool()
async def save_scene(file_path: Optional[str] = None, ctx: Context = None) -> str:
    """
    Save the current Cinema 4D scene.

    Args:
        file_path: Optional path to save the scene to
    """
    command = {"command": "save_scene"}
    if file_path:
        command["file_path"] = file_path
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def load_scene(file_path: str, ctx: Context) -> str:
    """
    Load a Cinema 4D scene file.

    Args:
        file_path: Path to the scene file to load
    """
    async with c4d_connection_context() as connection:
        return _run_command(connection, {"command": "load_scene", "file_path": file_path})


@mcp.tool()
async def create_mograph_cloner(
    cloner_type: str, name: Optional[str] = None, ctx: Context = None
) -> str:
    """
    Create a MoGraph Cloner object of specified type.

    Args:
        cloner_type: Type of cloner (grid, radial, linear)
        name: Optional name for the cloner
    """
    command = {"command": "create_mograph_cloner", "mode": cloner_type}
    if name:
        command["cloner_name"] = name
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def add_effector(
    effector_type: str,
    name: Optional[str] = None,
    target: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Add a MoGraph Effector to the scene.

    Args:
        effector_type: Type of effector (random, shader, field)
        name: Optional name for the effector
        target: Optional target object (e.g., cloner) to apply the effector to
    """
    command = {"command": "add_effector", "effector_type": effector_type}
    if name:
        command["effector_name"] = name
    if target:
        command["cloner_name"] = target
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def apply_mograph_fields(
    field_type: str,
    target: Optional[str] = None,
    field_name: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    ctx: Context = None,
) -> str:
    """
    Create and apply a MoGraph Field.

    Args:
        field_type: Type of field (spherical, box, cylindrical, linear, radial, noise)
        target: Optional target object to apply the field to
        field_name: Optional name for the field
        parameters: Optional parameters for the field (strength, falloff)
    """
    command = {"command": "apply_mograph_fields", "field_type": field_type}
    if target:
        command["target_name"] = target
    if field_name:
        command["field_name"] = field_name
    if parameters:
        command["parameters"] = parameters
    logger.debug("Sending apply_mograph_fields: %s", command)
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def create_soft_body(object_name: str, ctx: Context = None) -> str:
    """
    Add soft body dynamics to the specified object.

    Args:
        object_name: Name of the object to convert to a soft body
    """
    async with c4d_connection_context() as connection:
        return _run_command(
            connection, {"command": "create_soft_body", "object_name": object_name}
        )


@mcp.tool()
async def apply_dynamics(
    object_name: str, dynamics_type: str, ctx: Context = None
) -> str:
    """
    Add dynamics (rigid or soft) to the specified object.

    Args:
        object_name: Name of the object to apply dynamics to
        dynamics_type: Type of dynamics to apply (rigid, soft)
    """
    async with c4d_connection_context() as connection:
        return _run_command(
            connection,
            {"command": "apply_dynamics", "object_name": object_name, "type": dynamics_type},
        )


@mcp.tool()
async def create_abstract_shape(
    shape_type: str, name: Optional[str] = None, ctx: Context = None
) -> str:
    """
    Create an organic, abstract shape.

    Args:
        shape_type: Type of shape (blob, metaball)
        name: Optional name for the shape
    """
    command = {"command": "create_abstract_shape", "shape_type": shape_type}
    if name:
        command["object_name"] = name
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def create_camera(
    name: Optional[str] = None,
    position: Optional[List[float]] = None,
    properties: Optional[Dict[str, Any]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a new camera in the scene.

    Args:
        name: Optional name for the new camera.
        position: Optional [x, y, z] position.
        properties: Optional dictionary of camera properties (e.g., {"focal_length": 50}).
    """
    command = {"command": "create_camera"}
    if name:
        command["name"] = name
    if position:
        command["position"] = position
    if properties:
        command["properties"] = properties
    async with c4d_connection_context() as connection:
        result = _run_command(connection, command)
        if isinstance(result, str):
            return {"error": result}
        return result


@mcp.tool()
async def create_light(
    light_type: str, name: Optional[str] = None, ctx: Context = None
) -> str:
    """
    Add a light to the scene.

    Args:
        light_type: Type of light (area, dome, spot)
        name: Optional name for the light
    """
    command = {"command": "create_light", "type": light_type}
    if name:
        command["object_name"] = name
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def apply_shader(
    shader_type: str,
    material_name: Optional[str] = None,
    object_name: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Create and apply a specialized shader material.

    Args:
        shader_type: Type of shader (noise, gradient, fresnel, etc)
        material_name: Optional name of material to apply shader to
        object_name: Optional name of object to apply the material to
    """
    command = {"command": "apply_shader", "shader_type": shader_type}
    if material_name:
        command["material_name"] = material_name
    if object_name:
        command["object_name"] = object_name
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def animate_camera(
    animation_type: str,
    camera_name: Optional[str] = None,
    positions: Optional[List[List[float]]] = None,
    frames: Optional[List[int]] = None,
    ctx: Context = None,
) -> str:
    """
    Create a camera animation.

    Args:
        animation_type: Type of animation (wiggle, orbit, spline, linear)
        camera_name: Optional name of camera to animate
        positions: Optional list of [x,y,z] camera positions for keyframes
        frames: Optional list of frame numbers for keyframes
    """
    command = {"command": "animate_camera", "path_type": animation_type}
    if camera_name:
        command["camera_name"] = camera_name
    if positions:
        command["positions"] = positions
        command["frames"] = frames if frames else [i * 15 for i in range(len(positions))]
    if animation_type == "orbit" and not positions:
        radius, height, points = 200, 100, 12
        orbit_positions = []
        orbit_frames = []
        for i in range(points):
            angle = (i / points) * 2 * math.pi
            orbit_positions.append([radius * math.cos(angle), height, radius * math.sin(angle)])
            orbit_frames.append(i * 10)
        command["positions"] = orbit_positions
        command["frames"] = orbit_frames
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def execute_python_script(script: str, ctx: Context) -> str:
    """
    Execute a Python script in Cinema 4D.

    Args:
        script: Python code to execute in Cinema 4D
    """
    async with c4d_connection_context() as connection:
        return _run_command(connection, {"command": "execute_python", "script": script})


@mcp.tool()
async def group_objects(
    object_names: List[str], group_name: Optional[str] = None, ctx: Context = None
) -> str:
    """
    Group multiple objects under a null object.

    Args:
        object_names: List of object names to group
        group_name: Optional name for the group
    """
    command = {"command": "group_objects", "object_names": object_names}
    if group_name:
        command["group_name"] = group_name
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.tool()
async def render_preview(
    width: Optional[int] = None,
    height: Optional[int] = None,
    frame: Optional[int] = None,
    ctx: Context = None,
) -> str:
    """
    Render the current view and return a base64-encoded preview image.

    Args:
        width: Optional preview width in pixels
        height: Optional preview height in pixels
        frame: Optional frame number to render
    """
    command = {"command": "render_preview"}
    if width:
        command["width"] = width
    if height:
        command["height"] = height
    if frame is not None:
        command["frame"] = frame
    async with c4d_connection_context() as connection:
        result = _run_command(connection, command)
        if isinstance(result, str):
            return result
        if "image_data" not in result:
            return "❌ Error: No image data returned from Cinema 4D"
        return result


@mcp.tool()
async def snapshot_scene(
    file_path: Optional[str] = None, include_assets: bool = False, ctx: Context = None
) -> str:
    """
    Create a snapshot of the current scene state.

    Args:
        file_path: Optional path to save the snapshot
        include_assets: Whether to include external assets in the snapshot
    """
    command = {"command": "snapshot_scene", "include_assets": include_assets}
    if file_path:
        command["file_path"] = file_path
    async with c4d_connection_context() as connection:
        return _run_command(connection, command)


@mcp.resource("c4d://primitives")
def get_primitives_info() -> str:
    """Get information about available Cinema 4D primitives."""
    return """
# Cinema 4D Primitive Objects

## Cube
- **Parameters**: size, segments

## Sphere
- **Parameters**: radius, segments

## Cylinder
- **Parameters**: radius, height, segments

## Cone
- **Parameters**: radius, height, segments

## Plane
- **Parameters**: width, height, segments

## Torus
- **Parameters**: outer radius, inner radius, segments

## Pyramid
- **Parameters**: width, height, depth

## Platonic
- **Parameters**: radius, type (tetrahedron, hexahedron, octahedron, dodecahedron, icosahedron)
"""


@mcp.resource("c4d://material_types")
def get_material_types() -> str:
    """Get information about available Cinema 4D material types and their properties."""
    return """
# Cinema 4D Material Types

## Standard Material
- **Color**: Base diffuse color
- **Specular**: Highlight color and intensity
- **Reflection**: Surface reflectivity
- **Transparency**: Surface transparency
- **Bump**: Surface bumpiness or displacement

## Physical Material
- **Base Color**: Main surface color
- **Specular**: Surface glossiness and reflectivity
- **Roughness**: Surface irregularity
- **Metallic**: Metal-like properties
- **Transparency**: Light transmission properties
- **Emission**: Self-illumination properties
- **Normal**: Surface detail without geometry
- **Displacement**: Surface geometry modification
"""


@mcp.resource("c4d://status")
def get_connection_status() -> str:
    """Get the current connection status to Cinema 4D."""
    is_connected = check_c4d_connection(C4D_HOST, C4D_PORT)
    status = (
        "✅ Connected to Cinema 4D" if is_connected else "❌ Not connected to Cinema 4D"
    )

    return f"""
# Cinema 4D Connection Status
{status}

## Connection Details
- **Host**: {C4D_HOST}
- **Port**: {C4D_PORT}
"""


mcp_app = mcp
