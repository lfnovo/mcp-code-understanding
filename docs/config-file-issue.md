# Config File Management Issue

## Background
- Server config should follow standard OS conventions: `~/.config/mcp-code-understanding/config.yaml` for Linux/Mac
- Default config is packaged with our code but should be copied to user's config directory on first run
- Root-level `config.yaml` is maintained for local development convenience

## Recent Changes
1. Modified `config.py` to:
   - Use `~/.config/mcp-code-understanding/config.yaml` as the standard location
   - Added `ensure_default_config()` to copy default config on first run
   - Maintained development mode config search path (`./config.yaml`) for local dev
   - Improved error handling and logging

## Current State & Issues
- Package builds and installs via pipx successfully
- When running `mcp-code-understanding`, we get error:
```
Failed to create default config: 'code_understanding.config' is not a package
TypeError: 'code_understanding.config' is not a package
```
- The config directory `~/.config/mcp-code-understanding/` is not being created
- The server falls back to default config but warns about missing config file

## Installation Method
```bash
# Build wheel
python -m build

# Install with pipx
pipx install dist/code_understanding_mcp_server-0.1.0-py3-none-any.whl --force
```

## Key Problem
The code tries to use `importlib.resources` to access the default config file, but fails because:
1. We're trying to access `code_understanding.config` as a package
2. The error suggests our package structure might not be correct for this approach

## Config Search Order
1. `./config.yaml` (for local development)
2. `~/.config/mcp-code-understanding/config.yaml` (standard OS location)
3. Fall back to default configuration if no config file found

## Next Steps for Investigation
1. Review how we're packaging the default config.yaml (check pyproject.toml package_data settings)
2. Consider alternative approaches to accessing packaged config file
3. Verify the package structure is correct for using importlib.resources
4. May need to modify how we're accessing the default config within the package

## Relevant Files
- `src/code_understanding/config.py` - Main config handling
- `src/code_understanding/config/config.yaml` - Default config
- `pyproject.toml` - Package configuration

## Current Config Search Implementation
```python
def get_config_search_paths() -> List[str]:
    """Get list of paths to search for config file."""
    paths = []
    
    # Development mode - check current directory first
    paths.append("./config.yaml")
    
    # Standard .config directory location
    config_dir = Path.home() / ".config" / "mcp-code-understanding"
    paths.append(str(config_dir / "config.yaml"))
    
    return paths
```

## Notes
- The root-level config.yaml is maintained to support local development
- When installed via pipx, the standard OS config location should be used
- Default config from the package should be copied to the standard location on first run
- Error handling has been improved to better report config-related issues 