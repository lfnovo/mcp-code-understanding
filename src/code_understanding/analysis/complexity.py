import logging
import lizard
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("code_understanding.analysis.complexity")

class CodeComplexityAnalyzer:
    def __init__(self, repo_manager, repo_map_builder):
        self.repo_manager = repo_manager
        self.repo_map_builder = repo_map_builder
    
    async def analyze_repo_critical_files(
        self,
        repo_path: str,
        files: Optional[List[str]] = None,
        directories: Optional[List[str]] = None,
        limit: int = 50,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze repository to identify critical files based on complexity metrics.
        
        Args:
            repo_path: Path/URL matching what was provided to clone_repo
            files: Optional list of specific files to analyze
            directories: Optional list of specific directories to analyze
            limit: Maximum number of files to return (default: 50)
            include_metrics: Include detailed metrics in response (default: True)
            
        Returns:
            dict: Response with analysis results or error information
        """
        logger.info(f"Starting analysis of critical files for repo: {repo_path}")
        
        # TODO 1: Repository Status Validation
        try:
            # Attempt to get repository to validate its existence and status
            repo = await self.repo_manager.get_repository(repo_path)
            logger.debug(f"Repository validation successful for {repo_path}")
        except KeyError:
            # Repository not found in cache
            logger.error(f"Repository not found in cache: {repo_path}")
            return {
                "status": "error", 
                "error": f"Repository not found. Please clone it first using clone_repo with URL: {repo_path}"
            }
        except ValueError as e:
            # Repository path is invalid
            logger.error(f"Invalid repository path: {repo_path}. Error: {str(e)}")
            return {
                "status": "error",
                "error": f"Invalid repository path: {str(e)}"
            }
        except Exception as e:
            # Other repository-related errors
            logger.error(f"Error accessing repository {repo_path}: {str(e)}", exc_info=True)
            
            # Check if this is a "clone in progress" situation
            if "clone in progress" in str(e).lower():
                return {
                    "status": "waiting",
                    "message": f"Repository clone is in progress. Please try again later."
                }
            
            return {
                "status": "error",
                "error": f"Repository error: {str(e)}"
            }
        
        # TODO 2: File Selection Strategy
        try:
            # Use existing RepoMapBuilder method to get target files
            target_files = await self.repo_map_builder.gather_files_targeted(
                str(repo.root_path),
                files=files,
                directories=directories
            )
            
            # Check if we have files to analyze
            if not target_files:
                logger.info(f"No matching source files found in {repo_path} with specified criteria")
                return {
                    "status": "success",
                    "files": [],
                    "total_files_analyzed": 0,
                    "message": "No matching source files found with the specified criteria"
                }
            
            logger.info(f"Selected {len(target_files)} files for complexity analysis")
            
        except Exception as e:
            logger.error(f"Error during file selection: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": f"Failed to gather target files: {str(e)}"
            }
        
        # TODO 3: Complexity Analysis Integration
        # TODO 4: Result Processing
        
        # Temporary placeholder for remaining implementation
        return {
            "status": "success",
            "files": [
                {
                    "path": "src/core/engine.py",
                    "importance_score": 42.5,
                    "metrics": {
                        "total_ccn": 15,
                        "max_ccn": 8,
                        "function_count": 12,
                        "nloc": 145
                    }
                },
                {
                    "path": "src/services/processor.py",
                    "importance_score": 38.2,
                    "metrics": {
                        "total_ccn": 12,
                        "max_ccn": 6,
                        "function_count": 10,
                        "nloc": 120
                    }
                },
                {
                    "path": "src/utils/helpers.py",
                    "importance_score": 25.1,
                    "metrics": {
                        "total_ccn": 8,
                        "max_ccn": 4,
                        "function_count": 6,
                        "nloc": 85
                    }
                }
            ],
            "total_files_analyzed": 25
        }
    
    def calculate_importance_score(self, function_count, total_ccn, max_ccn, nloc):
        """Calculate importance score using the weighted formula."""
        return (2.0 * function_count) + (1.5 * total_ccn) + (1.2 * max_ccn) + (0.05 * nloc) 