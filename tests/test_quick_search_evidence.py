"""A successful search requires actual attributed source URLs."""
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from executor import system_executor as system


class FakeDDGS:
    def __init__(self, items=None, error=None):
        self.items = items if items is not None else []
        self.error = error
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results):
        self.queries.append((query, max_results))
        if self.error:
            raise self.error
        return iter(self.items)


class QuickSearchEvidenceTests(unittest.TestCase):
    def search(self, query, items=None, error=None):
        mock = FakeDDGS(items, error)
        module = ModuleType("duckduckgo_search")
        module.DDGS = lambda: mock
        with patch.dict(sys.modules, {"duckduckgo_search": module}):
            result = system.quick_search(query)
        return result, mock

    def test_valid_sources_are_attributed_not_verified(self):
        result, mock = self.search("physics", [
            {"title": " A source ", "href": "https://example.org/science", "body": "Unverified research summary"},
            {"title": "Second", "href": "https://example.net/physics", "body": "Another short summary"},
        ])
        self.assertTrue(result["success"])
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["status"], "sources_retrieved")
        self.assertIn("NOT been verified", result["message"])
        self.assertIn("URL: https://example.org/science", result["output"])
        self.assertEqual(mock.queries, [("physics", 3)])

    def test_empty_search_never_reports_success(self):
        result, _ = self.search("unknown topic", [])
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "no_attributable_results")
        self.assertEqual(result["source_count"], 0)

    def test_unsafe_urls_and_missing_citations_are_omitted(self):
        result, _ = self.search("test", [
            {"title": "Private", "href": "https://10.0.0.1/secret", "body": "Internal"},
            {"title": "Bad", "href": "javascript:alert(1)", "body": "Code"},
            {"title": "No URL", "body": "Unsourced"},
        ])
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "no_attributable_results")

    def test_provider_error_is_not_a_completed_search(self):
        result, _ = self.search("test", error=RuntimeError("provider unavailable"))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "search_unavailable")

    def test_invalid_query_does_not_contact_external_source(self):
        result, mock = self.search("x" * 301)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_query")
        self.assertEqual(mock.queries, [])

    def test_duplicate_url_is_not_counted_twice(self):
        entry = {"title": "Sample", "href": "https://example.org/source", "body": "Text"}
        result, _ = self.search("sample", [entry, dict(entry)])
        self.assertTrue(result["success"])
        self.assertEqual(result["source_count"], 1)


if __name__ == "__main__":
    unittest.main()
