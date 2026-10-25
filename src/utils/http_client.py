"""
HTTP utility with retry logic, rate limiting, and caching.
"""

import requests
import time
import hashlib
import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP client with retry, rate-limiting, and disk cache."""

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }

    def __init__(self, cache_dir: str = "data/cache",
                 rate_limit_seconds: float = 1.0,
                 max_retries: int = 1,
                 timeout: int = 10,
                 cache_ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.rate_limit = rate_limit_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.request_count = 0
        self.error_count = 0

        os.makedirs(cache_dir, exist_ok=True)

    def _cache_key(self, url: str, params: Optional[dict] = None) -> str:
        """Generate a cache key from URL and parameters."""
        key_str = url + (json.dumps(params, sort_keys=True) if params else "")
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _check_cache(self, cache_key: str) -> Optional[dict]:
        """Check if a cached response exists and is not expired."""
        cache_path = self._get_cache_path(cache_key)
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            cached_time = datetime.fromisoformat(cached.get('timestamp', ''))
            if datetime.now() - cached_time < self.cache_ttl:
                logger.debug(f"Cache hit for key {cache_key}")
                return cached
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        return None

    def _save_cache(self, cache_key: str, url: str, status_code: int,
                    content: str, headers: dict):
        """Save response to disk cache."""
        cache_path = self._get_cache_path(cache_key)
        try:
            cache_data = {
                'url': url,
                'status_code': status_code,
                'content': content[:500000],  # Limit cached content size
                'headers': dict(headers),
                'timestamp': datetime.now().isoformat()
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)

    def get(self, url: str, params: Optional[dict] = None,
            headers: Optional[dict] = None,
            use_cache: bool = True,
            allow_redirects: bool = True) -> Dict[str, Any]:
        """
        Perform a GET request with retry, rate-limiting, and caching.

        Returns:
            dict with keys: success, status_code, content, url, error, from_cache
        """
        cache_key = self._cache_key(url, params)

        # Check cache first
        if use_cache:
            cached = self._check_cache(cache_key)
            if cached:
                return {
                    'success': True,
                    'status_code': cached['status_code'],
                    'content': cached['content'],
                    'url': cached['url'],
                    'error': None,
                    'from_cache': True
                }

        # Make request with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()
                self.request_count += 1

                req_headers = dict(self.DEFAULT_HEADERS)
                if headers:
                    req_headers.update(headers)

                response = self.session.get(
                    url, params=params, headers=req_headers,
                    timeout=self.timeout, allow_redirects=allow_redirects,
                    verify=True
                )
                self.last_request_time = time.time()

                content = response.text

                # Cache successful responses
                if response.status_code == 200 and use_cache:
                    self._save_cache(cache_key, url, response.status_code,
                                     content, dict(response.headers))

                return {
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'content': content,
                    'url': str(response.url),
                    'error': None if response.status_code == 200 else f"HTTP {response.status_code}",
                    'from_cache': False
                }

            except requests.exceptions.Timeout:
                last_error = f"Timeout after {self.timeout}s"
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)[:200]}"
                logger.warning(f"Connection error on attempt {attempt + 1} for {url}")
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)[:200]}"
                logger.warning(f"Request error on attempt {attempt + 1} for {url}: {e}")

            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait = (2 ** attempt) * self.rate_limit
                logger.debug(f"Retrying in {wait:.1f}s")
                time.sleep(wait)

        self.error_count += 1
        return {
            'success': False,
            'status_code': None,
            'content': None,
            'url': url,
            'error': last_error,
            'from_cache': False
        }

    def download_file(self, url: str, save_path: str,
                      max_size_mb: int = 50) -> Dict[str, Any]:
        """Download a file with size limits."""
        try:
            self._rate_limit_wait()
            self.request_count += 1

            response = self.session.get(
                url, timeout=self.timeout, stream=True, verify=True
            )
            self.last_request_time = time.time()

            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'path': None
                }

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                return {
                    'success': False,
                    'error': f"File too large: {int(content_length) / 1024 / 1024:.1f}MB",
                    'path': None
                }

            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            total_bytes = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    total_bytes += len(chunk)
                    if total_bytes > max_size_mb * 1024 * 1024:
                        return {
                            'success': False,
                            'error': f"File exceeded {max_size_mb}MB limit during download",
                            'path': None
                        }
                    f.write(chunk)

            return {
                'success': True,
                'error': None,
                'path': save_path,
                'size': total_bytes,
                'content_type': response.headers.get('content-type', '')
            }

        except Exception as e:
            self.error_count += 1
            return {
                'success': False,
                'error': str(e)[:200],
                'path': None
            }

    def get_stats(self) -> dict:
        return {
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.request_count)
        }
