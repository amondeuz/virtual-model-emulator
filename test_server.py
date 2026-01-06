"""Unit tests for Virtual Model Emulator server"""
import unittest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock litellm before importing server
import sys
sys.modules['litellm'] = MagicMock()

from server import (
    AccountEncryption,
    get_provider_by_id,
    find_api_key_for_provider,
    _sanitize_error,
    RateLimiter,
    should_retry,
    ModelCache
)


class TestAccountEncryption(unittest.TestCase):
    """Test API key encryption/decryption"""

    def test_encrypt_decrypt_roundtrip(self):
        """Verify encryption is reversible"""
        enc = AccountEncryption()
        plaintext = "sk-1234567890abcdef"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)
        self.assertEqual(plaintext, decrypted)
        self.assertNotEqual(plaintext, encrypted)

    def test_decrypt_invalid_returns_none(self):
        """Verify invalid ciphertext returns None"""
        enc = AccountEncryption()
        result = enc.decrypt("not-valid-ciphertext")
        self.assertIsNone(result)


class TestProviderLookup(unittest.TestCase):
    """Test provider search functions"""

    def test_get_provider_valid_id(self):
        """Find provider by valid ID"""
        provider = get_provider_by_id('groq')
        self.assertIsNotNone(provider)
        self.assertEqual(provider['name'], 'Groq')

    def test_get_provider_invalid_id(self):
        """Return None for invalid provider ID"""
        provider = get_provider_by_id('invalid_provider')
        self.assertIsNone(provider)

    def test_get_provider_none_input(self):
        """Handle None input gracefully"""
        provider = get_provider_by_id(None)
        self.assertIsNone(provider)


class TestErrorSanitization(unittest.TestCase):
    """Test sensitive data removal from error messages"""

    def test_remove_api_key(self):
        """Sanitize API keys from errors"""
        error = "Failed: api_key='sk-1234567890'"
        clean = _sanitize_error(error)
        self.assertNotIn('sk-', clean)

    def test_remove_bearer_token(self):
        """Sanitize bearer tokens"""
        error = "Authorization failed: Bearer token_abc123"
        clean = _sanitize_error(error)
        self.assertNotIn('token_abc123', clean)

    def test_keep_safe_errors(self):
        """Don't sanitize safe error messages"""
        error = "Provider not found"
        clean = _sanitize_error(error)
        self.assertEqual(clean, error)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting"""

    def test_rate_limit_enforced(self):
        """Reject requests exceeding limit"""
        limiter = RateLimiter(requests_per_second=3)
        ip = "192.168.1.1"

        self.assertTrue(limiter.is_allowed(ip))
        self.assertTrue(limiter.is_allowed(ip))
        self.assertTrue(limiter.is_allowed(ip))
        self.assertFalse(limiter.is_allowed(ip))

    def test_different_ips_independent(self):
        """Different IPs have separate limits"""
        limiter = RateLimiter(requests_per_second=2)
        self.assertTrue(limiter.is_allowed("192.168.1.1"))
        self.assertTrue(limiter.is_allowed("192.168.1.1"))
        self.assertTrue(limiter.is_allowed("192.168.1.2"))
        self.assertTrue(limiter.is_allowed("192.168.1.2"))


class TestRetryLogic(unittest.TestCase):
    """Test transient error detection"""

    def test_should_retry_timeout(self):
        """Recognize timeout as transient"""
        error = Exception("Connection timeout")
        self.assertTrue(should_retry(error))

    def test_should_retry_503(self):
        """Recognize 503 as transient"""
        error = Exception("503 Service Unavailable")
        self.assertTrue(should_retry(error))

    def test_should_not_retry_syntax_error(self):
        """Don't retry permanent errors"""
        error = Exception("SyntaxError in request")
        self.assertFalse(should_retry(error))


class TestModelCache(unittest.TestCase):
    """Test model list caching"""

    def test_cache_hit(self):
        """Verify cache stores and retrieves"""
        cache = ModelCache(ttl_seconds=60)
        models = [{"id": "gpt-4", "label": "gpt-4"}]

        cache.set("openai", models)
        retrieved = cache.get("openai")

        self.assertEqual(retrieved, models)

    def test_cache_expiration(self):
        """Verify TTL expiration"""
        cache = ModelCache(ttl_seconds=1)
        models = [{"id": "gpt-4"}]

        cache.set("openai", models)
        time.sleep(1.1)
        retrieved = cache.get("openai")

        self.assertIsNone(retrieved)

    def test_cache_invalidate(self):
        """Verify cache invalidation"""
        cache = ModelCache(ttl_seconds=60)
        cache.set("openai", [{"id": "gpt-4"}])
        cache.set("groq", [{"id": "llama-3.3-70b"}])

        cache.invalidate("openai")

        self.assertIsNone(cache.get("openai"))
        self.assertIsNotNone(cache.get("groq"))


if __name__ == '__main__':
    unittest.main()
