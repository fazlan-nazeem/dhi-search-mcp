# DHI Search MCP Server

An MCP (Model Context Protocol) server that provides Docker Hardened Image catalog search functionality for AI assistants. It allows LLMs to search for secure, minimal container images, check catalog statistics, and list available repositories in the DHI catalog.

## Features

- **search_dhi_catalog**: Search for Docker Hardened Image matches using fuzzy matching.
- **get_dhi_statistics**: Get catalog statistics (counts by type, e.g., IMAGE, HELM_CHART).
- **list_dhi_images**: List all available images, optionally filtered by type.
- **list_image_tags**: List all tags for a specific image repository.
- **get_compliance_info**: Detect FIPS and STIG compliance for a specific image repository based on its tags.
- **get_image_support_info**: Retrieve lifecycle information (End of Life, End of Support) for an image tag.
- **Connectivity Test**: Built-in `--test` flag to verify credentials without an MCP client.

## Prerequisites

Set the following environment variables (required for both local and Docker execution):

```bash
export DOCKER_USERNAME="your_docker_username"
export DOCKER_PAT="your_docker_personal_access_token"
```

## Troubleshooting: "Invalid JSON" Error

If you run `dhi-search` directly in your terminal, you will see an error like:
`ERROR Received exception from stream: 1 validation error for JSONRPCMessage ... Invalid JSON: EOF while parsing a value`.

**This is expected behavior.** The server uses the `stdio` transport and is waiting for JSON-RPC messages from an MCP client (like Claude Desktop). To test your setup without an MCP client, use the `--test` flag described below.

---

## Running Locally

### 1. Setup Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Verify Connectivity

```bash
dhi-search --test
```

### 3. Debugging with MCP Inspector

To test the tools interactively:

```bash
mcp dev src/dhi_search_mcp/server.py
```

---

## Running with Docker

### 1. Build the Image

```bash
docker build -t dhi-search-mcp .
```

### 2. Verify Connectivity

```bash
docker run --rm \
  -e DOCKER_USERNAME=$DOCKER_USERNAME \
  -e DOCKER_PAT=$DOCKER_PAT \
  dhi-search-mcp --test
```

### 3. Run the Server (for MCP Clients)

```bash
docker run -i --rm \
  -e DOCKER_USERNAME=$DOCKER_USERNAME \
  -e DOCKER_PAT=$DOCKER_PAT \
  dhi-search-mcp
```
> [!NOTE]
> The `-i` flag is required for stdio communication.

---

## Claude Desktop Integration

Add the following to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

### Option A: Local Installation (Best for development)

```json
{
  "mcpServers": {
    "dhi-search-local": {
      "command": "/Users/fazlannazeem/projects/dhi-search-mcp/.venv/bin/dhi-search",
      "env": {
        "DOCKER_USERNAME": "your_username",
        "DOCKER_PAT": "your_pat"
      }
    }
  }
}
```

### Option B: Docker (Best for clean environments)

```json
{
  "mcpServers": {
    "dhi-search-docker": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "DOCKER_USERNAME=your_username",
        "-e", "DOCKER_PAT=your_pat",
        "dhi-search-mcp"
      ]
    }
  }
}
```

## Development

- **core.py**: Logic for authentication, GraphQL querying, and fuzzy matching.
- **server.py**: Defines the MCP tools and entry point.
