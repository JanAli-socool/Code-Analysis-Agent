"""
Caching layer for analysis results with TTL and invalidation.
"""
import hashlib
import json
import os
import pickle
import time
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, asdict
from threading import Lock


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    ttl_seconds: int
    file_hashes: Dict[str, str]

    def is_valid(self, current_hashes: Dict[str, str]) -> bool:
        if time.time() - self.created_at > self.ttl_seconds:
            return False
        return self.file_hashes == current_hashes


class AnalysisCache:
    def __init__(self, cache_dir: str, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        self._lock = Lock()
        self._memory_cache: Dict[str, CacheEntry] = {}

    def _compute_file_hashes(self, file_contents: Dict[str, str]) -> Dict[str, str]:
        return {path: hashlib.sha256(content.encode()).hexdigest()[:16] 
                for path, content in file_contents.items()}

    def _make_key(self, repo_path: str, skill_name: str, config_hash: str) -> str:
        content = f"{repo_path}:{skill_name}:{config_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _get_config_hash(self, config: Dict) -> str:
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]

    def get(self, repo_path: str, skill_name: str, config: Dict, 
            file_contents: Dict[str, str]) -> Optional[Any]:
        config_hash = self._get_config_hash(config)
        key = self._make_key(repo_path, skill_name, config_hash)
        current_hashes = self._compute_file_hashes(file_contents)

        # Check memory cache first
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if entry.is_valid(current_hashes):
                    return entry.value

        # Check disk cache
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                if entry.is_valid(current_hashes):
                    with self._lock:
                        self._memory_cache[key] = entry
                    return entry.value
            except Exception:
                pass

        return None

    def set(self, repo_path: str, skill_name: str, config: Dict,
            file_contents: Dict[str, str], value: Any) -> None:
        config_hash = self._get_config_hash(config)
        key = self._make_key(repo_path, skill_name, config_hash)
        current_hashes = self._compute_file_hashes(file_contents)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl_seconds=self.ttl_seconds,
            file_hashes=current_hashes
        )

        with self._lock:
            self._memory_cache[key] = entry

        # Write to disk
        cache_file = self.cache_dir / f"{key}.cache"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception:
            pass

    def invalidate(self, repo_path: str = None, skill_name: str = None) -> int:
        """Invalidate cache entries. Returns count of removed entries."""
        removed = 0
        with self._lock:
            keys_to_remove = []
            for key, entry in self._memory_cache.items():
                if repo_path and repo_path not in entry.key:
                    continue
                if skill_name and skill_name not in entry.key:
                    continue
                keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._memory_cache[key]
                removed += 1

        # Also clean disk cache
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                if repo_path and repo_path not in entry.key:
                    continue
                if skill_name and skill_name not in entry.key:
                    continue
                cache_file.unlink()
                removed += 1
            except Exception:
                pass

        return removed

    def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._memory_cache)
            self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        disk_count = len(list(self.cache_dir.glob("*.cache")))
        disk_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": disk_count,
            "disk_size_mb": round(disk_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }