"""Offline contract tests: no provider requests or credentials required."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gen_ai_audio


class Response:
    headers = {"Content-Type": "audio/mpeg"}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        return b"ID3-test-audio"


class AudioAdapterTests(unittest.TestCase):
    def test_sound_effect_request_and_file(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
            out = Path(tmp) / "sfx.mp3"
            with mock.patch.object(gen_ai_audio.urllib.request, "urlopen", return_value=Response()) as request:
                self.assertEqual(gen_ai_audio.main(["sfx", "--prompt", "laser", "--duration", "1",
                                                    "--loop", "--out", str(out)]), 0)
                req = request.call_args.args[0]
                self.assertEqual(req.full_url, "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128")
                body = json.loads(req.data)
                self.assertEqual(body["text"], "laser")
                self.assertEqual(body["duration_seconds"], 1)
                self.assertTrue(body["loop"])
                self.assertEqual(body["model_id"], "eleven_text_to_sound_v3")
                self.assertEqual(out.read_bytes(), b"ID3-test-audio")
                self.assertEqual(gen_ai_audio.main(["sfx", "--prompt", "laser", "--out", str(out)]), 1)
                self.assertEqual(request.call_count, 1)

    def test_music_request_contract_and_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "music.mp3")
            with mock.patch.object(gen_ai_audio.urllib.request, "urlopen") as request:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(gen_ai_audio.main(["music", "--prompt", "cosmic", "--duration", "12",
                                                       "--instrumental", "--out", out, "--dry-run"]), 0)
                info = json.loads(output.getvalue())
                self.assertEqual(info["body"]["music_length_ms"], 12000)
                self.assertTrue(info["body"]["force_instrumental"])
                self.assertTrue(info["url"].endswith("/music?output_format=mp3_44100_128"))
                request.assert_not_called()
                self.assertFalse(Path(out).exists())

    def test_missing_key_bad_duration_and_server_errors_leave_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "audio.mp3"
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(gen_ai_audio.main(["sfx", "--prompt", "x", "--out", str(out)]), 2)
                self.assertEqual(gen_ai_audio.main(["sfx", "--prompt", "x", "--duration", "40",
                                                    "--out", str(out)]), 1)
            with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}):
                with mock.patch.object(gen_ai_audio.urllib.request, "urlopen",
                                       side_effect=gen_ai_audio.urllib.error.URLError("offline")) as request:
                    self.assertEqual(gen_ai_audio.main(["music", "--prompt", "x", "--out", str(out)]), 1)
                    self.assertEqual(request.call_count, 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
