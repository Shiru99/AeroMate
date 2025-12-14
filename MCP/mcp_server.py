import subprocess
import os
import shutil
import uuid
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Manim Animation Server")

MANIM_EXECUTABLE = os.getenv("MANIM_EXECUTABLE", "manim")
BASE_DIR = os.getenv("MEDIA_DIR", "/app/media")
os.makedirs(BASE_DIR, exist_ok=True)

@mcp.tool()
def execute_manim_code(manim_code: str) -> str:
    """Execute the Manim code to generate an animation."""
    
    # Create a unique ID for this run to avoid collisions
    run_id = str(uuid.uuid4())
    tmpdir = os.path.join(BASE_DIR, run_id)
    os.makedirs(tmpdir, exist_ok=True)
    
    script_path = os.path.join(tmpdir, "scene.py")
    
    try:
        # Write the code to the file
        with open(script_path, "w") as script_file:
            script_file.write(manim_code)
        
        # Run Manim
        # -ql = Quality Low (faster rendering for testing), use -qh for high
        cmd = [MANIM_EXECUTABLE, "-ql", "-p", script_path]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        if result.returncode == 0:
            # Find the generated mp4 file
            video_dir = os.path.join(tmpdir, "media", "videos", "scene", "480p15") # path depends on quality flags
            return f"Execution successful. Files are located in: {tmpdir}"
        else:
            return f"Execution failed: {result.stderr}"

    except Exception as e:
        return f"Error during execution: {str(e)}"

@mcp.tool()
def cleanup_manim_temp_dir(directory_path: str) -> str:
    """Clean up the specified Manim temporary directory."""
    try:
        if os.path.exists(directory_path) and directory_path.startswith(BASE_DIR):
            shutil.rmtree(directory_path)
            return f"Cleanup successful for: {directory_path}"
        else:
            return f"Directory not found or invalid permission: {directory_path}"
    except Exception as e:
        return f"Failed to cleanup: {str(e)}"

if __name__ == "__main__":
    import sys
    import uvicorn

    if "--stdio" in sys.argv:
        mcp.run(transport="stdio")
    else:
        print("🚀 Starting Manim MCP Server on 0.0.0.0:8000")
        uvicorn.run(mcp.sse_app, host="0.0.0.0", port=8000)