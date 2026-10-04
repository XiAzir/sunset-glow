import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sunset_glow as app


class PushRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_path = Path(self.temp.name) / "state.json"
        self.config = json.loads((app.BASE_DIR / "config.json").read_text())
        self.now = datetime(2026, 10, 4, 12, 12, tzinfo=app.SHANGHAI_TZ)
        self.today = {"date": "2026-10-04", "quality": 75, "grade": "很棒", "sunset": "18:04", "probability": 90}
        self.tomorrow = {"date": "2026-10-05", "quality": 90, "grade": "绝美", "sunset": "18:03", "probability": 90}
        self.addCleanup(patch.stopall)
        patch.object(app, "log").start()
        patch.object(app, "setup_stdout").start()
        patch.object(app, "STATE_PATH", self.state_path).start()
        patch.object(app, "now_shanghai", return_value=self.now).start()
        patch.object(app, "fetch_forecast", return_value={"stub": True}).start()
        patch.object(app, "fetch_crosscheck", return_value=None).start()
        patch.object(app, "build_markdown", return_value="forecast body").start()
        patch.dict(os.environ, {"PUSHPLUS_TOKEN": "test-only-token"}).start()

    def run_main(self, responses, days=None, args=None):
        with patch.object(app, "extract_days", return_value=days or [self.today]), \
             patch.object(app, "http_post", side_effect=responses), \
             patch("sys.argv", ["sunset_glow.py"] + (args or ["--mode", "digest"])):
            status = app.main()
        return status, json.loads(self.state_path.read_text())

    def test_failure_is_retryable_and_retry_success_is_recorded(self):
        status, state = self.run_main(['{"code":500}'])
        self.assertEqual(status, 1)
        self.assertEqual(state["pushed"], {})
        status, state = self.run_main(['{"code":200}'])
        self.assertEqual(status, 0)
        self.assertEqual(set(state["pushed"]), {"2026-10-04:digest"})
        self.assertTrue(state["pushed"]["2026-10-04:digest"].endswith("+08:00"))
        with patch.object(app, "send_wechat") as send:
            status, _ = self.run_main([])
            self.assertEqual(status, 0)
            send.assert_not_called()

    def test_partial_success_keeps_only_successful_event(self):
        status, state = self.run_main(['{"code":200}', '{"code":500}'], [self.today, self.tomorrow])
        self.assertEqual(status, 1)
        self.assertEqual(set(state["pushed"]), {"2026-10-04:digest"})

    def test_dry_run_never_sends_or_deduplicates(self):
        with patch.object(app, "send_wechat") as send:
            status, state = self.run_main([], args=["--mode", "digest", "--dry-run"])
            self.assertEqual(status, 0)
            self.assertEqual(state["pushed"], {})
            send.assert_not_called()

    def test_test_mode_reports_failure_and_does_not_deduplicate(self):
        status, state = self.run_main(['{"code":500}'], args=["--mode", "test"])
        self.assertEqual(status, 1)
        self.assertEqual(state["pushed"], {})

    def test_missing_token_does_not_deduplicate(self):
        with patch.object(app, "resolve_token", return_value=""):
            status, state = self.run_main([])
        self.assertEqual(status, 1)
        self.assertEqual(state["pushed"], {})

    def test_disabled_channel_does_not_deduplicate(self):
        self.config["channels"]["wechat"]["enabled"] = False
        with patch.object(app, "load_json", side_effect=[self.config, {"pushed": {}}]):
            status, state = self.run_main([])
        self.assertEqual(status, 1)
        self.assertEqual(state["pushed"], {})

    def test_pushplus_requires_exact_structured_success(self):
        for response in ['{"code":2000}', '<html>error</html>', '[]', '{"code":500,"message":"code:200"}']:
            with self.subTest(response=response), patch.object(app, "http_post", return_value=response):
                self.assertFalse(app.send_wechat(self.config, "title", "body"))

    def test_serverchan_success(self):
        self.config["channels"]["wechat"]["provider"] = "serverchan"
        with patch.dict(os.environ, {"SERVERCHAN_TOKEN": "test-only-token"}), \
             patch.object(app, "http_post", return_value='{"code":0}'):
            self.assertTrue(app.send_wechat(self.config, "title", "body"))

    def test_legacy_and_offset_state_can_coexist(self):
        state = {"pushed": {"legacy": "2026-10-03T12:00:00", "aware": "2026-10-03T04:00:00+00:00", "old": "2026-08-01T12:00:00", "invalid": "bad"}}
        result = app.prune_state(state)
        self.assertEqual(set(result["pushed"]), {"legacy", "aware"})
        self.assertTrue(result["pushed"]["legacy"].endswith("+08:00"))

    def test_sunset_window_uses_beijing_time(self):
        events, _ = app.evaluate(self.config, [self.today], self.now, {"pushed": {}}, "digest", False)
        self.assertEqual(len(events), 1)
        late = self.now.replace(hour=17, minute=34)
        events, _ = app.evaluate(self.config, [self.today], late, {"pushed": {}}, "digest", False)
        self.assertEqual(events, [])
        alert_now = self.now.replace(hour=14, minute=7)
        events, _ = app.evaluate(self.config, [self.today], alert_now, {"pushed": {}}, "alert", False)
        self.assertEqual(events[0][1], "alert")


class TimezoneTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(time, "tzset"), "Requires POSIX tzset")
    def test_host_timezone_does_not_change_business_clock(self):
        old_tz = os.environ.get("TZ")
        try:
            for host_tz in ("UTC", "America/Los_Angeles", "Asia/Shanghai"):
                os.environ["TZ"] = host_tz
                time.tzset()
                beijing = app.now_shanghai()
                self.assertEqual(beijing.utcoffset(), timedelta(hours=8))
                self.assertLess(abs((beijing - datetime.now(timezone.utc)).total_seconds()), 1)
                sunset = app.parse_hhmm(beijing.strftime("%Y-%m-%d"), "18:04")
                self.assertEqual(sunset.utcoffset(), timedelta(hours=8))
                self.assertEqual(sunset.hour, 18)
        finally:
            if old_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old_tz
            time.tzset()


if __name__ == "__main__":
    unittest.main()
