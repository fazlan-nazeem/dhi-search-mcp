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

The server uses the `stdio` transport and is waiting for JSON-RPC messages from an MCP client (like Claude Desktop). To test your setup without an MCP client, use the `--test` flag described below.

```bash
dhi-search --test
```


---

## Running with Docker & Claude Desktop

### 1. Build the Image

```bash
docker build -t dhi-search-mcp .
```



## 2. Claude Desktop Integration

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

## 3. Test the Integration

Sample input prompts

```
is kubectl available in the DHI catalog?
is there a helm chart for Grafana?
what are the tags for the postgres versions available in the DHI catalog?
Is there a FIPS compliant image for prometheus
```
