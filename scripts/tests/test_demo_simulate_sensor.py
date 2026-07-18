import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parent.parent / "demo-simulate-sensor.py"
_spec = importlib.util.spec_from_file_location("demo_simulate_sensor", MODULE_PATH)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


class TestListDevices(unittest.TestCase):
    def test_list_devices_prints_known_devices_and_returns_0(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = demo.main(["--list-devices"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("lht65-frigo-positif", output)
        self.assertIn("lht65-congelateur", output)
        self.assertIn("lht65-stockage-sec", output)


if __name__ == "__main__":
    unittest.main()
