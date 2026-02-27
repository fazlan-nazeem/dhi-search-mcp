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

---

## Running with Docker & Claude Desktop

### 1. Build the Image

```bash
docker build -t dhi-search-mcp .
```

### 2. Check Connectivity

```bash
docker run -i --rm -e DOCKER_USERNAME="your_username" -e DOCKER_PAT="your_pat" dhi-search-mcp --test
```

If the test is successful, you should see output similar to:

```bash
Successfully connected to DHI Catalog!
Catalog contains 287 items.
  - IMAGE: 259
  - HELM_CHART: 28
```

### 3. Claude Desktop Integration

Add the following to your Claude Desktop config (`~/Library/Application\ Support/Claude/claude_desktop_config.json`):

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

### 4. Test the Integration

Sample input prompts

```
is kubectl available in the DHI catalog?
is there a helm chart for Grafana?
what are the tags for the postgres versions available in the DHI catalog?
Is there a FIPS compliant image for prometheus
```

#### Claude Desktop
![alt text](dhi-search-mcp-claude.gif "Claude Desktop")

---

## Running with Docker MCP Gateway

The server can be used with the [Docker MCP Gateway](https://github.com/docker/mcp-gateway) via the included `server.yaml` or the pre-built catalog published to Docker Hub.

### Option 1: Use the published catalog

Pull the catalog directly from Docker Hub and add it to a profile:

```bash
docker mcp catalog pull demonstrationorg/dhi-search-catalog:latest
docker mcp profile server add <profile-id> --catalog demonstrationorg/dhi-search-catalog:latest
```

### Option 2: Create a local catalog from server.yaml

```bash
docker mcp catalog create dhi-search-catalog --title "DHI Search" --server file://./server.yaml
docker mcp profile server add <profile-id> --catalog dhi-search-catalog
```

### Option 3: Run directly via MCP Gateway

```bash
docker mcp gateway run --server file://./server.yaml
```

