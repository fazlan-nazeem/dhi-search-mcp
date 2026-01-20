FROM python:3.12-slim

WORKDIR /app

# Copy all necessary files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package (not editable for production)
RUN pip install --no-cache-dir .

# Set the entrypoint to run the MCP server
ENTRYPOINT ["python", "-m", "dhi_search_mcp.server"]
