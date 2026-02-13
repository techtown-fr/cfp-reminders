import json
import time
from pathlib import Path

from cfp_reminders.cache import Cache


def test_read_returns_none_when_no_cache(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    assert cache.read() is None


def test_write_and_read_within_ttl(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    assert cache.read() == data


def test_read_returns_none_when_expired(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=0)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    time.sleep(0.01)
    assert cache.read() is None


def test_read_expired_returns_data_when_allow_stale(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=0)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    time.sleep(0.01)
    assert cache.read(allow_stale=True) == data


def test_cache_creates_directory(tmp_path):
    cache_dir = tmp_path / "nested" / "dir"
    cache = Cache(cache_dir=cache_dir, ttl_seconds=3600)
    cache.write([{"test": True}])
    assert cache_dir.exists()


def test_read_returns_none_when_meta_corrupted(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    cache.write([{"conf": {"name": "Test"}}])
    cache._meta_path.write_text("invalid json {{{")
    assert cache.read() is None


def test_read_returns_none_when_data_not_list(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    cache.write([{"conf": {"name": "Test"}}])
    cache._data_path.write_text('{"not": "a list"}')
    assert cache.read() is None
