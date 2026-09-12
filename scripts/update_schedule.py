"""Convenience entry point: python scripts/update_schedule.py."""

import runpy, sys
from pathlib import Path

sys.argv = ["maintain.py", "update-schedule"]
runpy.run_path(str(Path(__file__).with_name("maintain.py")), run_name="__main__")
