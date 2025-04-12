# MCP Code Understanding Service Redesign Overview

## Current System Overview

The MCP Code Understanding service currently uses TreeSitter for code parsing and analysis. While functional, this approach requires significant custom code for parsing, caching, and state management. The system currently handles:

- Repository cloning and management
- Code parsing and analysis using TreeSitter
- Custom caching implementation
- File system operations and cleanup
- Pattern-based code search

## Motivation for Redesign

We're transitioning from TreeSitter to Ader's RepoMap for several reasons:

1. RepoMap provides more robust code understanding capabilities
2. Reduces need for custom parsing and caching logic
3. Better handles large codebases
4. Provides background processing capabilities
5. More maintainable and scalable solution

## What We're Keeping

1. Repository Management System:

   - Robust cloning functionality
   - Repository path handling
   - Git operations
   - Basic file system operations

2. Core API Structure:
   - FastMCP server implementation
   - Basic endpoint architecture
   - Error handling patterns
   - Logging infrastructure

## What We're Changing

1. Removing:

   - All TreeSitter-related code
   - Custom caching implementation
   - Memory management code
   - State recovery logic
   - Existing test suite

2. Adding:

   - RepoMap integration
   - PathSpec-based file filtering
   - Background processing management
   - Enhanced language support
   - New test suite

3. Modifying:
   - API endpoints to match new specification
   - File exclusion handling
   - Response formats for build status

## Integration Points

1. RepoMap Integration:

   - Called during repository clone/refresh
   - Runs as background process
   - Provides code understanding capabilities
   - Handles its own caching

2. Subprocess Usage:
   - Git operations (clone, pull)
   - RepoMap initialization and building
   - Any external tool interactions
   - Cross-platform command execution

## Cross-Platform Considerations

Must work consistently across:

- Linux
- macOS
- Windows
- Various file systems
- Different path separators
- Different process management

## Critical Implementation Examples

The following example scripts MUST be used as implementation guides. These have been thoroughly tested and validated - any deviation from their patterns must be explicitly approved:

### 1. RepoMap Integration (`test_repo_map_simple.py`)

- Demonstrates correct initialization and usage of Ader's RepoMap
- Shows proper configuration and setup
- Illustrates file gathering methodology
- CRITICAL: This is the only approved way to interface with Ader's RepoMap
- Must be followed methodically to ensure compatibility

### 2. Pattern Search Implementation (`pattern_search_test.py`)

- Provides validated pattern search implementation
- Shows correct file traversal and filtering
- Demonstrates proper error handling
- Must be used as exact reference for pattern search functionality

### 3. File Extraction (`extract_repo_files.py`)

- Shows how to parse RepoMap output
- Demonstrates file comparison methodology
- Critical for tracking excluded files
- Must be used to validate RepoMap file coverage

See `implementation_spec.md` for detailed implementation specifications.
