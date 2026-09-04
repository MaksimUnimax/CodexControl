import unittest

from codex_control.config import parse_server_configuration
from codex_control.domain import CodexProfile, CodexSelection
from codex_control.sessions import bind_dialogue, capture_turn


class FoundationTests(unittest.TestCase):
    def test_configuration_is_server_agnostic(self):
        config = parse_server_configuration({"server": {"server_id": "server-N", "display_name": "SERVER-N"}, "profiles": [{"profile_id": "alpha", "codex_home": "/safe/home", "display_name": "Alpha"}]})
        self.assertEqual(config.identity.server_id, "server-N")
        self.assertEqual(config.profiles[0].profile_id, "alpha")

    def test_running_turn_snapshot_is_not_retargeted(self):
        first = CodexSelection(CodexProfile("one", "/profile-one", "One"), "model-a", "high")
        binding = bind_dialogue("server-N", first, "thread-1")
        snapshot = capture_turn(binding)
        later = CodexSelection(CodexProfile("two", "/profile-two", "Two"), "model-b", "low")
        self.assertNotEqual(snapshot.binding.profile_id, later.profile.profile_id)
        self.assertEqual(snapshot.binding.thread_id, "thread-1")
        self.assertEqual(tuple(snapshot.binding.__dataclass_fields__), ("server_id", "profile_id", "thread_id"))

    def test_profile_repr_redacts_home(self):
        self.assertNotIn("/private", repr(CodexProfile("p", "/private", "Profile")))

    def test_duplicate_profile_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_server_configuration({"server": {"server_id": "x", "display_name": "X"}, "profiles": [{"profile_id": "p", "codex_home": "/a", "display_name": "A"}, {"profile_id": "p", "codex_home": "/b", "display_name": "B"}]})


if __name__ == "__main__":
    unittest.main()
