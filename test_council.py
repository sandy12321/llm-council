import io
import json
import unittest
from unittest import mock

import council


def _fake_response(payload):
    stream = io.BytesIO(json.dumps(payload).encode())
    ctx = mock.MagicMock()
    ctx.__enter__.return_value = stream
    ctx.__exit__.return_value = False
    return ctx


def _member(name="m1", key_env="COUNCIL_TEST_KEY"):
    return {"name": name, "endpoint": "https://api.example.test/v1",
            "model": "test-model", "key_env": key_env}


class CouncilTests(unittest.TestCase):
    def test_dry_run_needs_no_keys_or_network(self):
        members = [_member("a"), _member("b")]
        with mock.patch.dict("os.environ", {}, clear=False):
            results = council.convene(members, "hi", dry_run=True)
        self.assertEqual([r["name"] for r in results], ["a", "b"])
        self.assertTrue(all(r["ok"] for r in results))

    def test_success_parses_openai_schema(self):
        payload = {"choices": [{"message": {"content": "hello back"}}]}
        with mock.patch.dict("os.environ", {"COUNCIL_TEST_KEY": "sekret"}), \
             mock.patch("urllib.request.urlopen",
                        return_value=_fake_response(payload)) as uo:
            r = council.ask_member(_member(), "hi")
        self.assertTrue(r["ok"])
        self.assertEqual(r["text"], "hello back")
        sent = json.loads(uo.call_args[0][0].data.decode())
        self.assertEqual(sent["model"], "test-model")
        self.assertEqual(sent["messages"], [{"role": "user", "content": "hi"}])
        auth = uo.call_args[0][0].get_header("Authorization")
        self.assertEqual(auth, "Bearer sekret")

    def test_missing_key_is_a_result_not_an_exception(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("COUNCIL_TEST_KEY", None)
            r = council.ask_member(_member(), "hi")
        self.assertFalse(r["ok"])
        self.assertIn("COUNCIL_TEST_KEY", r["text"])

    def test_network_failure_is_a_result(self):
        with mock.patch.dict("os.environ", {"COUNCIL_TEST_KEY": "x"}), \
             mock.patch("urllib.request.urlopen",
                        side_effect=TimeoutError("slow")):
            r = council.ask_member(_member(), "hi")
        self.assertFalse(r["ok"])
        self.assertIn("TimeoutError", r["text"])

    def test_convene_keeps_config_order(self):
        members = [_member(f"m{i}") for i in range(5)]
        results = council.convene(members, "hi", dry_run=True)
        self.assertEqual([r["name"] for r in results],
                         [f"m{i}" for i in range(5)])

    def test_verdict_prompt_contains_everything(self):
        p = council.verdict_prompt("q?", [{"name": "a", "text": "yes"},
                                          {"name": "b", "text": "no"}])
        self.assertIn("q?", p)
        self.assertIn("--- a ---\nyes", p)
        self.assertIn("--- b ---\nno", p)

    def test_load_config(self):
        import tempfile
        cfg = {"members": [_member("solo")]}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump(cfg, fh)
            path = fh.name
        self.assertEqual(council.load_config(path), cfg["members"])


if __name__ == "__main__":
    unittest.main()
