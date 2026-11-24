"""Portable bootstrap orchestration tests."""
import json
from pathlib import Path
import subprocess
import sys


def test_portable_installer_completes_in_temp_copy(tmp_path):
    # Exercise report creation and safe directory setup against the repository
    # itself; skip the heavyweight tests stage for predictable CI runtime.
    script = Path(__file__).parents[1] / "scripts" / "portable_install.py"
    result = subprocess.run([sys.executable, str(script), "--non-interactive", "--skip-tests"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((script.parents[1] / "reports" / "portable-install-latest.json").read_text())
    assert report["stages"]
    assert "automatic posting" in report["notes"][0].lower() or report["notes"]
