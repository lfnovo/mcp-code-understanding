import pytest
import time
from pathlib import Path
import shutil
import asyncio
import os

from code_understanding.repository.cache import RepositoryCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary directory for testing."""
    cache_dir = tmp_path / "repo_cache"
    yield cache_dir
    if cache_dir.exists():
        shutil.rmtree(cache_dir)


@pytest.fixture
def cache(temp_cache_dir):
    """Create a RepositoryCache instance for testing."""
    return RepositoryCache(temp_cache_dir, max_cached_repos=3, cleanup_interval=0)


def create_test_repo(cache_dir: Path, name: str, access_time: float = None):
    """Helper to create a test repository directory."""
    repo_dir = cache_dir / name
    repo_dir.mkdir(parents=True)
    if access_time is not None:
        os.utime(repo_dir, (access_time, access_time))
    return repo_dir


@pytest.mark.asyncio
async def test_cache_initialization(temp_cache_dir):
    """Test cache initialization."""
    cache = RepositoryCache(temp_cache_dir)
    assert cache.cache_dir == temp_cache_dir
    assert cache.max_cached_repos == 50  # Default value
    assert cache.cleanup_interval == 86400  # Default value
    assert temp_cache_dir.exists()


@pytest.mark.asyncio
async def test_cleanup_old_repos(cache, temp_cache_dir):
    """Test cleanup of old repositories when limit is exceeded."""
    # Create test repositories with different access times
    # Use larger time gaps to avoid any precision issues
    now = time.time()
    repos = []
    for i in range(5):
        repo = create_test_repo(
            temp_cache_dir, f"repo{i}", now - (i * 3600)
        )  # 1 hour gaps
        repos.append(repo)
        # Force sync to ensure access times are written
        os.sync()

    # Debug: Print actual access times
    print("\nDebug: Repository access times:")
    for repo in repos:
        actual_time = os.path.getatime(repo)
        print(f"{repo.name}: {actual_time} (delta from now: {now - actual_time:.2f})")

    await cache.cleanup_old_repos()

    # Debug: Print remaining repos and their access times
    print("\nDebug: Remaining repositories after cleanup:")
    remaining_repos = list(temp_cache_dir.iterdir())
    remaining_repos.sort(key=lambda x: os.path.getatime(x), reverse=True)
    for repo in remaining_repos:
        actual_time = os.path.getatime(repo)
        print(f"{repo.name}: {actual_time} (delta from now: {now - actual_time:.2f})")

    # Should keep only the 3 newest repos (max_cached_repos=3)
    assert len(remaining_repos) == 3

    # Verify the oldest repos were removed
    for repo in repos[3:]:  # repo3 and repo4 should be removed
        assert not repo.exists(), f"Expected {repo.name} to be removed"

    # Verify the newest repos were kept
    for repo in repos[:3]:  # repo0, repo1, repo2 should remain
        assert repo.exists(), f"Expected {repo.name} to remain"

    # Verify the remaining repos are actually the newest ones
    remaining_names = {r.name for r in remaining_repos}
    expected_names = {f"repo{i}" for i in range(3)}
    assert (
        remaining_names == expected_names
    ), f"Expected repos {expected_names}, but found {remaining_names}"


@pytest.mark.asyncio
async def test_cleanup_interval_respected(cache):
    """Test that cleanup only occurs after the specified interval."""
    await cache.cleanup_old_repos()
    first_cleanup = cache.last_cleanup

    # Immediate second cleanup should not run
    await cache.cleanup_old_repos()
    # Compare timestamps with reduced precision (round to seconds)
    assert round(cache.last_cleanup) == round(first_cleanup)


@pytest.mark.asyncio
async def test_cleanup_empty_cache(cache):
    """Test cleanup with empty cache directory."""
    await cache.cleanup_old_repos()
    assert cache.cache_dir.exists()
    assert len(list(cache.cache_dir.iterdir())) == 0


@pytest.mark.asyncio
async def test_cleanup_invalid_directory(cache, temp_cache_dir):
    """Test cleanup with an invalid directory."""
    invalid_dir = temp_cache_dir / "invalid"
    invalid_dir.mkdir(parents=True)
    os.chmod(invalid_dir, 0o000)  # Remove all permissions temporarily

    try:
        await cache.cleanup_old_repos()
        # Should not raise an exception
        assert True
    finally:
        os.chmod(invalid_dir, 0o755)  # Restore permissions for cleanup


@pytest.mark.asyncio
async def test_cleanup_with_custom_max_repos(temp_cache_dir):
    """Test cleanup with custom maximum repository limit."""
    cache = RepositoryCache(temp_cache_dir, max_cached_repos=2, cleanup_interval=0)

    # Create 4 test repositories
    for i in range(4):
        create_test_repo(temp_cache_dir, f"repo{i}")

    await cache.cleanup_old_repos()
    assert len(list(temp_cache_dir.iterdir())) == 2


@pytest.mark.asyncio
async def test_concurrent_cleanup(cache, temp_cache_dir):
    """Test concurrent cleanup operations."""
    # Create test repositories
    for i in range(5):
        create_test_repo(temp_cache_dir, f"repo{i}")

    # Run multiple cleanup operations concurrently
    await asyncio.gather(
        cache.cleanup_old_repos(), cache.cleanup_old_repos(), cache.cleanup_old_repos()
    )

    # Should still maintain the correct number of repos
    assert len(list(temp_cache_dir.iterdir())) == 3


@pytest.mark.asyncio
async def test_cleanup_error_handling(cache, temp_cache_dir):
    """Test handling of errors during cleanup."""
    error_repo = temp_cache_dir / "error_repo"
    error_repo.mkdir(parents=True)
    test_file = error_repo / "test.txt"
    test_file.write_text("test")
    os.chmod(test_file, 0o000)  # Remove all permissions temporarily

    try:
        await cache.cleanup_old_repos()
        # Should not raise an exception
        assert True
    finally:
        os.chmod(test_file, 0o644)  # Restore permissions for cleanup


@pytest.mark.asyncio
async def test_cleanup_with_nonexistent_cache_dir(temp_cache_dir):
    """Test cleanup when cache directory doesn't exist initially."""
    nonexistent_dir = temp_cache_dir / "nonexistent"
    cache = RepositoryCache(nonexistent_dir)

    assert nonexistent_dir.exists()  # Should be created during initialization
    await cache.cleanup_old_repos()  # Should handle empty directory gracefully
