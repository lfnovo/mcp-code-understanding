import pytest
import time
from pathlib import Path
import shutil
import asyncio
import os
import json

from code_understanding.repository.cache import RepositoryCache, RepositoryMetadata


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


def create_test_repo(cache_dir: Path, name: str) -> Path:
    """Helper to create a test repository directory with github/org structure."""
    repo_dir = cache_dir / "github" / "testorg" / name
    repo_dir.mkdir(parents=True)
    return repo_dir


@pytest.mark.asyncio
async def test_cache_initialization(temp_cache_dir):
    """Test cache initialization."""
    cache = RepositoryCache(temp_cache_dir)
    assert cache.cache_dir == temp_cache_dir
    assert cache.max_cached_repos == 50  # Default value
    assert cache.cleanup_interval == 86400  # Default value
    assert temp_cache_dir.exists()
    assert (
        temp_cache_dir / "metadata.json"
    ).exists() == False  # Created only when needed
    assert (temp_cache_dir / "cache.lock").exists()  # Lock file should be created


@pytest.mark.asyncio
async def test_metadata_creation_and_sync(cache, temp_cache_dir):
    """Test metadata creation and synchronization."""
    # Create test repositories
    repo1 = create_test_repo(temp_cache_dir, "repo1")
    repo2 = create_test_repo(temp_cache_dir, "repo2")

    # Add repos to cache
    await cache.add_repo(str(repo1), "https://github.com/testorg/repo1")
    await cache.add_repo(str(repo2), "https://github.com/testorg/repo2")

    # Verify metadata file exists and contains correct data
    metadata_file = temp_cache_dir / "metadata.json"
    assert metadata_file.exists()

    data = json.loads(metadata_file.read_text())
    assert str(repo1) in data
    assert str(repo2) in data
    assert data[str(repo1)]["url"] == "https://github.com/testorg/repo1"

    # Test metadata sync when repo is deleted from disk
    shutil.rmtree(repo1)
    metadata = cache._sync_metadata()
    assert str(repo1) not in metadata
    assert str(repo2) in metadata


@pytest.mark.asyncio
async def test_prepare_for_clone(cache, temp_cache_dir):
    """Test prepare_for_clone functionality."""
    # Create max_cached_repos + 1 repositories
    repos = []
    for i in range(4):  # max is 3
        repo = create_test_repo(temp_cache_dir, f"repo{i}")
        await cache.add_repo(str(repo), f"https://github.com/testorg/repo{i}")
        repos.append(repo)

    # Try to prepare for another clone
    new_path = str(temp_cache_dir / "github" / "testorg" / "new-repo")
    result = await cache.prepare_for_clone(new_path)
    assert result == True

    # Verify oldest repo was removed
    assert not repos[0].exists()
    metadata = cache._read_metadata()
    assert str(repos[0]) not in metadata


@pytest.mark.asyncio
async def test_update_access(cache, temp_cache_dir):
    """Test access time updates in metadata."""
    repo = create_test_repo(temp_cache_dir, "repo1")
    await cache.add_repo(str(repo), "https://github.com/testorg/repo1")

    # Get initial access time
    metadata = cache._read_metadata()
    initial_time = metadata[str(repo)].last_access

    # Wait briefly and update access
    time.sleep(0.1)
    await cache.update_access(str(repo))

    # Verify access time was updated
    metadata = cache._read_metadata()
    assert metadata[str(repo)].last_access > initial_time


@pytest.mark.asyncio
async def test_cleanup_old_repos(cache, temp_cache_dir):
    """Test cleanup of old repositories using metadata."""
    # Create test repositories with different access times
    repos = []
    for i in range(5):
        repo = create_test_repo(temp_cache_dir, f"repo{i}")
        await cache.add_repo(str(repo), f"https://github.com/testorg/repo{i}")
        repos.append(repo)

    # Update access times for repos 1-3, leaving 0 and 4 as oldest
    for i in range(1, 4):
        time.sleep(0.1)  # Ensure different timestamps
        await cache.update_access(str(repos[i]))

    await cache.cleanup_old_repos()

    # Should keep only the 3 newest repos (max_cached_repos=3)
    metadata = cache._read_metadata()
    assert len(metadata) == 3

    # Verify the oldest repos were removed (repo0 and repo4)
    assert not repos[0].exists()  # Oldest (never updated)
    assert not repos[4].exists()  # Never updated

    # Verify repos 1-3 were kept (most recently accessed)
    for i in range(1, 4):
        assert repos[i].exists()
        assert str(repos[i]) in metadata


@pytest.mark.asyncio
async def test_concurrent_operations(cache, temp_cache_dir):
    """Test concurrent operations with file locking."""
    repo = create_test_repo(temp_cache_dir, "repo1")

    # Run multiple operations concurrently
    await asyncio.gather(
        cache.add_repo(str(repo), "url1"),
        cache.update_access(str(repo)),
        cache.cleanup_old_repos(),
    )

    # Verify metadata is consistent
    metadata = cache._read_metadata()
    assert str(repo) in metadata
    assert metadata[str(repo)].url == "url1"


@pytest.mark.asyncio
async def test_atomic_metadata_writes(cache, temp_cache_dir):
    """Test atomic metadata writes with temp files."""
    repo = create_test_repo(temp_cache_dir, "repo1")
    await cache.add_repo(str(repo), "test_url")

    # Verify temp file is cleaned up
    temp_file = temp_cache_dir / "metadata.json.tmp"
    assert not temp_file.exists()

    # Verify metadata file exists and is valid
    metadata_file = temp_cache_dir / "metadata.json"
    assert metadata_file.exists()
    data = json.loads(metadata_file.read_text())
    assert str(repo) in data


@pytest.mark.asyncio
async def test_remove_repo(cache, temp_cache_dir):
    """Test repository removal."""
    repo = create_test_repo(temp_cache_dir, "repo1")
    await cache.add_repo(str(repo), "test_url")

    # Remove repository
    await cache.remove_repo(str(repo))

    # Verify removal
    assert not repo.exists()
    metadata = cache._read_metadata()
    assert str(repo) not in metadata
