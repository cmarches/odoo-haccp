"""Tests unitaires pour le mode OCA du bridge (sans instance Odoo réelle)."""
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("ODOO_KEY", "test")
os.environ["ODOO_QUALITY_BACKEND"] = "oca"

import bridge  # noqa: E402


class TestCreateQualityCheckOca(unittest.TestCase):

    @staticmethod
    def _side_effect_factory(tol_min, tol_max):
        def side_effect(db, uid, key, model, method, args, kwargs=None):
            if model == "quality.check" and method == "create":
                return 42
            if model == "quality.point" and method == "read":
                return [{"tolerance_min": tol_min, "tolerance_max": tol_max}]
            if model == "quality.check" and method == "write":
                return True
            if model == "quality.alert" and method == "create":
                return 99
            return None
        return side_effect

    def _make_mock(self, tol_min, tol_max):
        m = MagicMock()
        m.execute_kw.side_effect = self._side_effect_factory(tol_min, tol_max)
        return m

    def test_pass_within_tolerance(self):
        with patch.object(bridge, "odoo_connect", return_value=(1, self._make_mock(-30.0, 4.0))), \
             patch.object(bridge, "send_sms") as sms_mock:
            check_id, result = bridge._create_quality_check_oca(1, 2.5, "Frigo")
        self.assertEqual(result, "pass")
        self.assertEqual(check_id, 42)
        sms_mock.assert_not_called()

    def test_fail_above_tolerance(self):
        with patch.object(bridge, "odoo_connect", return_value=(1, self._make_mock(-30.0, 4.0))), \
             patch.object(bridge, "send_sms") as sms_mock:
            check_id, result = bridge._create_quality_check_oca(1, 7.0, "Frigo")
        self.assertEqual(result, "fail")
        sms_mock.assert_called_once_with("Frigo", 7.0, -30.0, 4.0)

    def test_fail_creates_alert(self):
        mock = self._make_mock(-30.0, 4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, mock)), \
             patch.object(bridge, "send_sms"):
            bridge._create_quality_check_oca(1, 7.0, "Frigo")
        alert_calls = [c for c in mock.execute_kw.call_args_list
                       if c.args[3] == "quality.alert" and c.args[4] == "create"]
        self.assertEqual(len(alert_calls), 1)

    def test_pass_no_alert(self):
        mock = self._make_mock(-30.0, 4.0)
        with patch.object(bridge, "odoo_connect", return_value=(1, mock)), \
             patch.object(bridge, "send_sms"):
            bridge._create_quality_check_oca(1, 2.5, "Frigo")
        alert_calls = [c for c in mock.execute_kw.call_args_list
                       if c.args[3] == "quality.alert"]
        self.assertEqual(len(alert_calls), 0)

    def test_dispatcher_routes_to_oca(self):
        with patch.object(bridge, "_create_quality_check_oca", return_value=(42, "pass")) as oca, \
             patch.object(bridge, "_create_quality_check_ee") as ee:
            bridge.create_quality_check(1, 2.5, "Frigo")
        oca.assert_called_once_with(1, 2.5, "Frigo")
        ee.assert_not_called()


if __name__ == "__main__":
    unittest.main()
