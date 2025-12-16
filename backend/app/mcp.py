import os
import asyncio
from langchain_core.tools import tool
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

MCP_SERVER_URL = os.getenv("MCP_MANIM_URL", "http://localhost:9000/sse")
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

@tool
async def generate_manim_animation(manim_code: str) -> str:
    """
    Generates a math/geometric animation video using the Manim library. requires python scripts if not provide you need to generate it and MUST return a URL to the generated video.
    """
    print(f"🔌 Connecting to Manim Server at {MCP_SERVER_URL}...")
    
    try:
        # Establish connection to the SSE endpoint
        async with sse_client(url=MCP_SERVER_URL) as streams:
            # Create a session using the read/write streams
            async with ClientSession(streams[0], streams[1]) as session:
                
                # Handshake
                await session.initialize()
                
                result = await session.call_tool(
                    "execute_manim_code",
                    arguments={"manim_code": manim_code}
                )

                output_text = result.content[0].text
                print("✅ Manim animation generation completed.")
            
            if "SUCCESS_VIDEO_PATH:" in output_text:
                internal_path = output_text.split("SUCCESS_VIDEO_PATH:")[1].strip()
                
                if "/app/media" in internal_path:
                    relative_path = internal_path.replace("/app/media", "")

                    video_url = f"{BACKEND_BASE_URL}/assets{relative_path}"

                    print(f"🎬 Video available at: {video_url}")
    
                    return f"Animation generated successfully! Available at - {video_url}"
                else:
                    return "Error: Unexpected video path format received from Manim server."
            else:
                return "Error: Manim server did not return a video path."              

    except ConnectionRefusedError:
        return "Error: Could not connect to Manim Docker container. Is it running on port 9000?"
    except Exception as e:
        return f"Error executing Manim animation: {str(e)}"