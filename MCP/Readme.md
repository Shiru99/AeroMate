# ✈️ AeroMate MCP Server

This is an MCP (Model Context Protocol) server that executes Manim animation code and returns the generated video. It allows users to send Manim scripts and receive the rendered animation.

## Run

1. docker build -t mcp_manim .
2. docker run --name manim-server -p 9000:8000 -v ./manim_output:/app/media --env-file .env mcp_manim