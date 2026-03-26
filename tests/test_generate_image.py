import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from generate_image import (
    build_output_stem,
    extension_for_mime,
    load_prompt,
    resolve_api_key,
    slugify,
)


class GenerateImageTests(unittest.TestCase):
    def test_slugify_normalizes_text(self):
        self.assertEqual(slugify(" Sunrise Poster Draft "), "sunrise-poster-draft")
        self.assertEqual(slugify("###"), "image")

    def test_load_prompt_reads_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "prompt.txt"
            prompt_file.write_text("  cinematic product shot  \n", encoding="utf-8")
            self.assertEqual(load_prompt(None, prompt_file), "cinematic product shot")

    def test_resolve_api_key_uses_fallbacks(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "token"}, clear=True):
            self.assertEqual(resolve_api_key("GOOGLE_API_KEY"), "token")

    def test_build_output_stem_uses_filename_when_provided(self):
        self.assertEqual(build_output_stem("Launch Poster", "ignored"), "launch-poster")

    def test_extension_for_mime_uses_common_image_suffixes(self):
        self.assertEqual(extension_for_mime("image/png"), ".png")
        self.assertEqual(extension_for_mime("image/jpeg"), ".jpg")


if __name__ == "__main__":
    unittest.main()
