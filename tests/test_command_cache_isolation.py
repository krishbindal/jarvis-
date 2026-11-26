"""Parsing caches must never let one command corrupt the next command."""
import unittest
from core.command_cache import CommandCache


class CommandCacheIsolationTests(unittest.TestCase):
    def test_mutated_original_is_not_copied_into_cache(self):
        cache = CommandCache()
        payload = {"action": "open_dynamic", "extra": {"app": "firefox", "flags": [1]}}
        cache.put("open browser", payload)
        payload["extra"]["flags"].append(999)
        self.assertEqual(cache.get("open browser")["extra"]["flags"], [1])

    def test_mutated_return_does_not_poison_next_lookup(self):
        cache = CommandCache()
        cache.put("open browser", {"action": "open_dynamic", "extra": {"app": "firefox"}})
        first = cache.get("open browser")
        first["extra"]["app"] = "malicious"
        self.assertEqual(cache.get("open browser")["extra"]["app"], "firefox")

    def test_cache_hit_miss_stats_still_work(self):
        cache = CommandCache()
        self.assertIsNone(cache.get("unknown"))
        cache.put("hello", {"action": "chat"})
        self.assertEqual(cache.get("hello")["action"], "chat")
        self.assertEqual(cache.stats["hits"], 1)
        self.assertEqual(cache.stats["misses"], 1)


if __name__ == "__main__":
    unittest.main()
