import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge


class GoogleAnswers(unittest.TestCase):
    @patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"})
    def test_full_question_and_direct_answer(self):
        with patch("bridge.serp_request", return_value={
            "answer_box": {"answer": "Naypyidaw", "snippet": "Unrelated detail"},
        }) as request:
            record = bridge.lookup("What is the capital of Myanmar?", "en")
        request.assert_called_once_with("test-key", engine="google",
            q="What is the capital of Myanmar?", hl="en", gl="us")
        self.assertEqual(record["text"], "Naypyidaw")
        self.assertEqual(record["provider"], "google")

    @patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"})
    def test_overview_token_and_source(self):
        with patch("bridge.serp_request", side_effect=[
            {"ai_overview": {"page_token": "page123"}},
            {"ai_overview": {"text_blocks": [{"type": "paragraph", "snippet": "It has two moons."}],
                             "references": [{"link": "https://science.nasa.gov/mars/"}]}},
        ]) as request:
            record = bridge.lookup("Quantas luas Marte tem?", "pt")
        self.assertEqual(request.call_args.kwargs, {"engine": "google_ai_overview", "page_token": "page123"})
        self.assertEqual(record["text"], "It has two moons.")
        self.assertEqual(record["url"], "https://science.nasa.gov/mars/")

    @patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"})
    def test_regular_search_snippets_are_not_answers(self):
        with patch("bridge.serp_request", return_value={"organic_results": [{"snippet": "Mars is a planet."}]}):
            self.assertIsNone(bridge.lookup("How many moons does Mars have?"))

    def test_auto_search_and_saved_answer_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            record = {"question": "2+2?", "title": "Google direct answer", "text": "4",
                      "url": "https://www.google.com/search?q=2%2B2", "date": "2026-11-25",
                      "provider": "google"}
            with patch("bridge.lookup", return_value=record) as search:
                memory = bridge.Memory(data, search)
                answer, pending = memory.execute("2+2?", None)
                self.assertIn("\n4\n", answer)
                self.assertIn("Saved locally.", memory.execute("/SAVE", pending)[0])
            with patch("bridge.lookup", side_effect=bridge.SearchError("offline")) as search:
                memory = bridge.Memory(data, search)
                self.assertIn("MEMORY:", memory.execute("2+2?", None)[0])
                search.assert_not_called()
                self.assertEqual(memory.execute("2-2?", None)[0], "offline")

    def test_legacy_summary_remains_available_but_does_not_override_google(self):
        with tempfile.TemporaryDirectory() as directory:
            source = {"question": "Mars?", "title": "Mars", "text": "A planet.",
                      "url": "https://en.wikipedia.org/wiki/Mars", "date": "2026-11-24"}
            with patch("bridge.lookup", return_value=None) as search:
                memory = bridge.Memory(Path(directory), search)
                memory.save(source)
                self.assertIn("A planet.", memory.execute("/FIND Mars", None)[0])
                self.assertIn("no direct answer", memory.execute("Mars", None)[0])
                search.assert_called_once_with("Mars", "en")


if __name__ == "__main__":
    unittest.main()
