FROM manimcommunity/manim:v0.18.1

USER root

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py .

RUN mkdir -p /app/media && \
    chown -R manimuser:manimuser /app

USER manimuser

EXPOSE 8000

CMD ["python", "mcp_server.py"]