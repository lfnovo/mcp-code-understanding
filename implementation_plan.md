# Implementation Plan for get_repo_critical_files MCP Endpoint

## Task Summary
Iterate on the existing MCP server endpoint that analyzes a codebase to identify the most structurally significant files based on code complexity metrics. This will help clients focus their code understanding efforts on the most critical parts of a system first.

## Key Requirements
1. Create a new endpoint `get_repo_critical_files` that:
   - Takes parameters: repo_path, files (optional), directories (optional), limit (default 50)
   - Returns a list of files ranked by importance score with metrics
   - Works with repositories previously cloned via clone_repo

2. The importance score calculation should use:
   - Function count (weight: 2.0)
   - Total cyclomatic complexity (weight: 1.5)
   - Maximum cyclomatic complexity (weight: 1.2)
   - Lines of code (weight: 0.05)

3. The response should include:
   - File paths
   - Importance scores
   - Detailed metrics (total_ccn, max_ccn, function_count, nloc)
   - Total files analyzed

## Existing Code Structure
The MCP server follows a "thin layer, with backend delegation" pattern:
1. The `app.py` file contains endpoint definitions that are thin wrappers
2. The actual implementation logic is delegated to specialized modules
3. The endpoints handle parameter validation and response formatting

For example, the `get_repo_structure` endpoint delegates to `RepoMapBuilder.get_repo_structure()` and the `get_source_repo_map` endpoint delegates to `RepoMapBuilder.get_repo_map_content()`.

## Implementation Plan
1. Create a new module for code complexity analysis (e.g., `src/code_understanding/analysis/complexity.py`)
2. Implement a `CodeComplexityAnalyzer` class that uses Lizard for analysis
3. Integrate with existing repository management and file selection logic
4. Update the `get_repo_critical_files` endpoint to delegate to this new module

## Reusable Components
1. `RepoMapBuilder.gather_files_targeted()` - For file selection based on directories/files parameters
2. `RepositoryManager.get_repository()` - For repository validation and access
3. `FileFilter` - For filtering source code files
4. The existing error handling and response formatting patterns

## Lizard Integration
The `scripts/lizard_analyzer.py` file provides a reference implementation for using Lizard to analyze code complexity. We can adapt this for our new module, particularly the `calculate_llm_priority_score` function.
