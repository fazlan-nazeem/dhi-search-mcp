"""Core search logic for Docker Hardened Image catalog."""

import os
import requests
from fuzzywuzzy import process, fuzz
from typing import Any


class DHISearchError(Exception):
    """Exception raised for DHI search errors."""
    pass


def get_jwt_token() -> str:
    """Exchanges Docker PAT for JWT token using auth/token endpoint.
    
    Returns:
        JWT token string.
        
    Raises:
        DHISearchError: If authentication fails or credentials are missing.
    """
    username = os.getenv('DOCKER_USERNAME')
    pat = os.getenv('DOCKER_PAT')

    if not username or not pat:
        raise DHISearchError(
            "DOCKER_USERNAME and DOCKER_PAT environment variables must be set."
        )

    url = 'https://hub.docker.com/v2/auth/token'
    
    try:
        payload = {
            'identifier': username,
            'secret': pat
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        token = data.get('token') or data.get('access_token')
        if not token:
            raise DHISearchError("No token received from authentication endpoint.")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"Error authenticating: {e}"
        if 'response' in locals() and response.content:
            error_msg += f" Response: {response.content.decode()}"
        raise DHISearchError(error_msg)


def fetch_catalog(token: str, query: str | None = None) -> dict[str, Any]:
    """Fetches data from the Docker Scout GraphQL API.
    
    Args:
        token: JWT token for authentication.
        query: Optional GraphQL query string. If None, fetches the default DHI catalog.
        
    Returns:
        GraphQL response data as dictionary.
        
    Raises:
        DHISearchError: If the API request fails.
    """
    url = 'https://api.scout.docker.com/v1/graphql'
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'dhi-search-mcp/1.0'
    }
    
    if not query:
        query = """
        query dhiListRepositories {
          dhiListRepositories {
            items {
              name
              type
              tagNames
            }
          }
        }
        """
    
    payload = {'query': query}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching from API: {e}"
        if 'response' in locals() and response.content:
            error_msg += f" Response: {response.content.decode()}"
        raise DHISearchError(error_msg)


def extract_image_names(catalog_data: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Extracts image names and stats from the GraphQL response.
    
    Args:
        catalog_data: Raw GraphQL response data.
        
    Returns:
        Tuple of (image_data dict mapping names to tags, stats dict with type counts).
        
    Raises:
        DHISearchError: If the response format is unexpected.
    """
    stats: dict[str, int] = {}
    image_data: dict[str, list[str]] = {}
    
    try:
        items = catalog_data['data']['dhiListRepositories']['items']
        for item in items:
            name = item.get('name')
            item_type = item.get('type', 'Unknown')
            
            if name:
                stats[item_type] = stats.get(item_type, 0) + 1
                tags = item.get('tagNames', []) or []
                image_data[name] = tags
                
    except (KeyError, TypeError) as e:
        raise DHISearchError(f"Error parsing GraphQL response: {e}")

    return image_data, stats


def find_matches(input_image: str, catalog_image_data: dict[str, list[str]]) -> list[str]:
    """Finds fuzzy matches for a given image name.
    
    Args:
        input_image: The image name to search for.
        catalog_image_data: Dict mapping catalog image names to their tags.
        
    Returns:
        List of matching image names, sorted by match quality.
    """
    catalog_images = list(catalog_image_data.keys())
    query = input_image.lower()
    
    # Aliases for known mappings
    aliases = {
        '.net': 'dotnet',
    }
    
    for k, v in aliases.items():
        if k in query:
            query = query.replace(k, v)
    
    # Common words that might cause false positives
    stop_words = {'runtime', 'sdk', 'cli', 'agent', 'operator', 'server', 
                  'client', 'driver', 'plugin', 'controller'}
    
    query_parts = query.split()
    core_parts = [p for p in query_parts if p not in stop_words]
    core_name = " ".join(core_parts) if core_parts else query
    
    matches = process.extract(query, catalog_images, limit=5, scorer=fuzz.WRatio)
    
    results = []
    for name, score in matches:
        if score < 85:
            continue
            
        name_clean = name.replace('-', ' ').replace('_', ' ').lower()
        if core_name and len(core_name) > 2:
            if core_name not in name_clean:
                core_score = fuzz.partial_ratio(core_name, name_clean)
                if core_score < 80:
                    continue
                    
        keywords_to_enforce = ['cli', 'sdk']
        should_continue = False
        for kw in keywords_to_enforce:
            if kw in query_parts and kw not in name_clean:
                should_continue = True
                break
        
        if should_continue:
            tags = catalog_image_data.get(name, [])
            tags_str = " ".join(tags).lower()
            
            all_keywords_found_in_tags = True
            for kw in keywords_to_enforce:
                if kw in query_parts:
                    if kw not in name_clean and kw not in tags_str:
                        all_keywords_found_in_tags = False
                        break
            
            if not all_keywords_found_in_tags:
                continue

        results.append((name, score))
              
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]


def check_compliance(tags: list[str]) -> dict[str, bool]:
    """Checks for FIPS and STIG compliance from a list of tags.
    
    Args:
        tags: List of image tags.
        
    Returns:
        Dictionary with 'fips' and 'stig' boolean values.
    """
    tags_lower = [t.lower() for t in tags]
    
    # FIPS detection: presence of '-fips' in any tag
    is_fips = any("-fips" in t for t in tags_lower)
    
    # STIG detection: presence of 'stig' in any tag
    is_stig = any("stig" in t for t in tags_lower)
    
    return {
        "fips": is_fips,
        "stig": is_stig
    }


def get_repository_tags(repo_name: str) -> list[str]:
    """Fetches all tags for a specific repository from the catalog.
    
    Args:
        repo_name: The name of the repository.
        
    Returns:
        List of tag strings.
        
    Raises:
        DHISearchError: If repository is not found or API fails.
    """
    token = get_jwt_token()
    catalog_data = fetch_catalog(token)
    
    try:
        items = catalog_data['data']['dhiListRepositories']['items']
        for item in items:
            if item.get('name') == repo_name:
                return item.get('tagNames', []) or []
                
        raise DHISearchError(f"Repository '{repo_name}' not found in catalog.")
    except (KeyError, TypeError) as e:
        raise DHISearchError(f"Error parsing GraphQL response: {e}")


def get_tag_support_info(repo_name: str, tag: str) -> dict[str, Any]:
    """Retrieves support and lifecycle information for a specific tag.
    
    Args:
        repo_name: Repository name.
        tag: Specific tag name.
        
    Returns:
        Dictionary with displayName, endOfLife, and endOfSupport.
        
    Raises:
        DHISearchError: If repository or tag info is not found.
    """
    token = get_jwt_token()
    
    query = f"""
    query {{
      dhiRepository(repoName: "{repo_name}") {{
        ... on DhiImageRepositoryDetails {{
          tagDefinitions {{
            displayName
            tagNames
            endOfLife
            endOfSupport
          }}
        }}
      }}
    }}
    """
    
    response = fetch_catalog(token, query)
    
    try:
        tag_definitions = response.get('data', {}).get('dhiRepository', {}).get('tagDefinitions', [])
        if not tag_definitions:
            return {
                "repository": repo_name,
                "tag": tag,
                "info": "No support information found for this repository."
            }
            
        for defn in tag_definitions:
            if tag in defn.get('tagNames', []):
                return {
                    "repository": repo_name,
                    "tag": tag,
                    "display_name": defn.get('displayName'),
                    "end_of_life": defn.get('endOfLife'),
                    "end_of_support": defn.get('endOfSupport')
                }
                
        return {
            "repository": repo_name,
            "tag": tag,
            "info": f"Tag '{tag}' not found in support definitions."
        }
    except (KeyError, TypeError) as e:
        raise DHISearchError(f"Error extracting support info: {e}")


def get_catalog_data() -> tuple[dict[str, list[str]], dict[str, int]]:
    """Fetches and parses the DHI catalog.
    
    Returns:
        Tuple of (image_data, stats).
        
    Raises:
        DHISearchError: If fetching or parsing fails.
    """
    token = get_jwt_token()
    catalog_data = fetch_catalog(token)
    return extract_image_names(catalog_data)
