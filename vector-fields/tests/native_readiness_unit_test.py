"""Readiness waits must observe all markers and fail promptly when blocked."""
import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_workspace as workspace


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'engine.log'
        self.process = Mock()
        self.process.poll.return_value = None

    def test_ready_log_returns_observed_state(self):
        self.path.write_text('connected\nplayer state\n', encoding='utf-8')
        self.assertEqual('connected\nplayer state\n', workspace.wait_for_log(self.path, ('connected', 'player state'), [self.process]))

    def test_waits_for_missing_player_state_after_connection(self):
        self.path.write_text('connected\n', encoding='utf-8')
        def deliver(_):
            self.path.write_text('connected\nplayer state\n', encoding='utf-8')
        with patch.object(workspace.time, 'sleep', side_effect=deliver) as wait:
            workspace.wait_for_log(self.path, ('connected', 'player state'), [self.process])
        wait.assert_called_once()

    def test_missing_log_can_arrive_later(self):
        def deliver(_):
            self.path.write_text('connected\n', encoding='utf-8')
        with patch.object(workspace.time, 'sleep', side_effect=deliver):
            self.assertIn('connected', workspace.wait_for_log(self.path, 'connected', [self.process]))

    def test_process_exit_rejects_even_a_stale_ready_log(self):
        self.path.write_text('connected\n', encoding='utf-8')
        self.process.poll.return_value = 3
        with self.assertRaisesRegex(RuntimeError, 'code 3'):
            workspace.wait_for_log(self.path, 'connected', [self.process])

    def test_timeout_names_missing_marker_and_preserves_log(self):
        self.path.write_text('connected\n', encoding='utf-8')
        with patch.object(workspace.time, 'monotonic', side_effect=[0, 0, 2]), patch.object(workspace.time, 'sleep'):
            with self.assertRaisesRegex(TimeoutError, 'player state'):
                workspace.wait_for_log(self.path, ('connected', 'player state'), [self.process], timeout=1)
        self.assertEqual('connected\n', self.path.read_text(encoding='utf-8'))

    def test_empty_readiness_cannot_succeed(self):
        for markers in ((), '', ('connected', '')):
            with self.subTest(markers=markers), self.assertRaises(ValueError):
                workspace.wait_for_log(self.path, markers, [self.process])


if __name__ == '__main__':
    unittest.main()
