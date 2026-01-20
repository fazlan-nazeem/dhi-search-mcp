"""MCP Server for Docker Hardened Image catalog search."""

import sys
import argparse
from mcp.server.fastmcp import FastMCP
from dhi_search_mcp.core import (
    get_catalog_data,
    find_matches,
    get_repository_tags,
    check_compliance,
    get_tag_support_info,
    DHISearchError,
)

# Create the MCP server
mcp = FastMCP("DHI Search")


@mcp.tool()
def search_dhi_catalog(image_names: list[str]) -> dict:
    """Search for Docker Hardened Image matches for a list of image names.
    
    Args:
        image_names: List of image names to search for (e.g., ["PostgreSQL", ".NET Runtime", "nginx"])
        
    Returns:
        Dictionary with matched and unmatched results.
    """
    try:
        catalog_data, stats = get_catalog_data()
        
        matched = {}
        unmatched = []
        
        for image_name in image_names:
            matches = find_matches(image_name, catalog_data)
            if matches:
                matched[image_name] = matches[:3]  # Top 3 matches
            else:
                unmatched.append(image_name)
        
        return {
            "matched": matched,
            "unmatched": unmatched,
            "summary": {
                "total_searched": len(image_names),
                "matched_count": len(matched),
                "unmatched_count": len(unmatched)
            }
        }
    except DHISearchError as e:
        return {"error": str(e)}


@mcp.tool()
def get_dhi_statistics() -> dict:
    """Get statistics about the Docker Hardened Image catalog.
    
    Returns:
        Dictionary with catalog statistics including counts by type.
    """
    try:
        catalog_data, stats = get_catalog_data()
        
        return {
            "statistics": stats,
            "total_items": sum(stats.values())
        }
    except DHISearchError as e:
        return {"error": str(e)}


@mcp.tool()
def list_dhi_images(image_type: str | None = None) -> dict:
    """List all available images in the Docker Hardened Image catalog.
    
    Args:
        image_type: Optional filter by type (e.g., "IMAGE" or "HELM_CHART"). If not provided, lists all images.
        
    Returns:
        Dictionary with list of image names and count.
    """
    try:
        catalog_data, stats = get_catalog_data()
        
        # If no filter, return all image names
        if image_type is None:
            image_names = sorted(catalog_data.keys())
        else:
            # Need to re-fetch to filter by type
            from dhi_search_mcp.core import get_jwt_token, fetch_catalog
            token = get_jwt_token()
            raw_data = fetch_catalog(token)
            
            items = raw_data['data']['dhiListRepositories']['items']
            image_names = sorted([
                item['name'] for item in items 
                if item.get('type') == image_type and item.get('name')
            ])
        
        return {
            "images": image_names,
            "count": len(image_names),
            "filter": image_type
        }
    except DHISearchError as e:
        return {"error": str(e)}


@mcp.tool()
def list_image_tags(repository_name: str) -> dict:
    """List all tags for a specific Docker Hardened Image repository.
    
    Args:
        repository_name: The name of the repository (e.g., "postgres", "nginx")
        
    Returns:
        Dictionary with list of tags and count.
    """
    try:
        tags = get_repository_tags(repository_name)
        return {
            "repository": repository_name,
            "tags": tags,
            "count": len(tags)
        }
    except DHISearchError as e:
        return {"error": str(e)}


@mcp.tool()
def get_compliance_info(repository_name: str) -> dict:
    """Check if a specific Docker Hardened Image repository has FIPS or STIG compliant variants.
    
    Args:
        repository_name: The name of the repository (e.g., "postgres", "nginx")
        
    Returns:
        Dictionary with compliance information (fips, stig) and details.
    """
    try:
        tags = get_repository_tags(repository_name)
        compliance = check_compliance(tags)
        
        # Extract fips and stig tags for better visibility
        fips_tags = [t for t in tags if "-fips" in t.lower()]
        stig_tags = [t for t in tags if "stig" in t.lower()]
        
        return {
            "repository": repository_name,
            "compliance": compliance,
            "details": {
                "fips_tags": fips_tags,
                "stig_tags": stig_tags
            },
            "summary": f"FIPS: {'Supported' if compliance['fips'] else 'Not found'}, STIG: {'Supported' if compliance['stig'] else 'Not found'}"
        }
    except DHISearchError as e:
        return {"error": str(e)}


@mcp.tool()
def get_image_support_info(repository_name: str, tag: str) -> dict:
    """Get lifecycle information (End of Life, End of Support) for a specific image tag.
    
    Args:
        repository_name: The name of the repository (e.g., "postgres", "nginx")
        tag: The specific tag (e.g., "16", "3.20")
        
    Returns:
        Dictionary with lifecycle dates and display name.
    """
    try:
        return get_tag_support_info(repository_name, tag)
    except DHISearchError as e:
        return {"error": str(e)}


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="DHI Search MCP Server")
    parser.add_argument("--test", action="store_true", help="Test connectivity to DHI catalog and exit")
    
    args = parser.parse_args()
    
    if args.test:
        print("Testing DHI Catalog connectivity...")
        try:
            catalog_data, stats = get_catalog_data()
            print("Successfully connected to DHI Catalog!")
            print(f"Catalog contains {sum(stats.values())} items.")
            for item_type, count in stats.items():
                print(f"  - {item_type}: {count}")
                
            # Test tag and compliance retrieval for a known image (e.g., alpine or the first one)
            first_repo = next(iter(catalog_data.keys()))
            print(f"\nTesting tag retrieval for: {first_repo}")
            tags = get_repository_tags(first_repo)
            print(f"Found {len(tags)} tags.")
            
            compliance = check_compliance(tags)
            print(f"Compliance: FIPS={compliance['fips']}, STIG={compliance['stig']}")
            
            # Test support info retrieval for the first tag of the first repo
            if tags:
                first_tag = tags[0]
                print(f"\nTesting support info for: {first_repo}:{first_tag}")
                info = get_tag_support_info(first_repo, first_tag)
                print(f"Support Info: {info}")
            
            sys.exit(0)
        except DHISearchError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    mcp.run()


if __name__ == "__main__":
    main()
