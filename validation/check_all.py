#!/usr/bin/env python3
"""Fail-closed consistency and reproducibility checks for the artifact."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(name: str, command: list[str], timeout: int = 7200) -> dict:
    started = time.time()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "output_tail": (proc.stdout or "")[-4000:],
    }


def normalized_json(path: Path) -> object:
    value = json.loads(path.read_text())
    if isinstance(value, dict):
        for key in (
            "seconds",
            "cpu_seconds",
            "wall_seconds",
            "elapsed_seconds",
            "peak_rss_kb",
            "max_rss_kib",
            "generated_at",
            "timestamp",
        ):
            value.pop(key, None)
    return value


def directory_bytes_equal(left: Path, right: Path) -> tuple[bool, str]:
    left_files = sorted(p.relative_to(left) for p in left.rglob("*") if p.is_file())
    right_files = sorted(p.relative_to(right) for p in right.rglob("*") if p.is_file())
    if left_files != right_files:
        return False, f"file sets differ: expected={left_files}, generated={right_files}"
    for relative in left_files:
        if (left / relative).read_bytes() != (right / relative).read_bytes():
            return False, f"bytes differ: {relative}"
    return True, f"matched {len(left_files)} files"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="skip the full campaign reproduction")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    checks: list[dict] = []
    checks.append(run("audit", [sys.executable, "audit.py"]))
    checks.append(run("run_check", [sys.executable, "run.py", "check"]))
    checks.append(run("unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]))
    checks.append(run("formal", [sys.executable, "formal/check.py"]))

    with tempfile.TemporaryDirectory(prefix="rs-artifact-check-") as raw:
        temp = Path(raw)
        independent = temp / "independent.json"
        structured = temp / "structured"
        generated_inputs = temp / "inputs"
        reproduced = temp / "reproduced"

        checks.append(
            run(
                "independent_finite_checks",
                [sys.executable, "validation/independent_finite_checks.py", "--root", ".", "--out", str(independent)],
            )
        )
        checks.append(
            run(
                "structured_cases",
                [sys.executable, "validation/structured_cases.py", "--out-dir", str(structured)],
            )
        )
        retained_structured = ROOT / "results" / "validation" / "structured-cases"
        structured_same = (
            retained_structured.joinpath("instances.csv").is_file()
            and retained_structured.joinpath("instances.csv").read_bytes()
            == structured.joinpath("instances.csv").read_bytes()
            and retained_structured.joinpath("summary.json").is_file()
            and normalized_json(retained_structured / "summary.json")
            == normalized_json(structured / "summary.json")
        )
        checks.append(
            {
                "name": "structured_cases_retained_comparison",
                "returncode": 0 if structured_same else 1,
                "seconds": 0,
                "output_tail": f"equal={structured_same}",
            }
        )

        checks.append(run("generate_inputs", [sys.executable, "src/generate_inputs.py", "--out", str(generated_inputs)]))
        inputs_same, inputs_detail = directory_bytes_equal(ROOT / "inputs", generated_inputs / "inputs")
        checks.append(
            {
                "name": "generated_input_comparison",
                "returncode": 0 if inputs_same else 1,
                "seconds": 0,
                "output_tail": inputs_detail,
            }
        )
        checks.append(run("pilot", [sys.executable, "src/pilot.py"]))
        if not args.quick:
            checks.append(run("reproduce", [sys.executable, "run.py", "reproduce", "--out", str(reproduced)]))

    for path in ROOT.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob("*.pyc"):
        try:
            path.unlink()
        except OSError:
            pass
    checks.append(run("package_clean", [sys.executable, "audit.py", "--package-clean"]))

    failed = [check["name"] for check in checks if check.get("returncode") != 0]
    report = {
        "schema": "artifact-check-v1",
        "status": "PASS" if not failed else "FAIL",
        "failed": failed,
        "checks": checks,
        "boundary": (
            "Internal consistency and reproducibility check; not external peer review, "
            "a novelty proof, full proof-assistant mechanization, or an acceptance guarantee."
        ),
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
