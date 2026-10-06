#!/usr/bin/env python3
"""Fail-closed consistency and reproducibility checks for the artifact."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(name: str, command: list[str], logs: Path, timeout: int = 150) -> dict:
    started = time.monotonic()
    raw_log = logs / (name + ".log")
    command = [command[0], "-B", *command[1:]]
    with raw_log.open("x", encoding="utf-8") as handle:
        try:
            proc = subprocess.run(command, cwd=ROOT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "LC_ALL": "C.UTF-8"},
                stdout=handle, stderr=subprocess.STDOUT, timeout=timeout)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            handle.write(f"\nCommand exceeded {timeout} seconds.\n")
            returncode = 124
        except OSError as error:
            handle.write(f"\nCommand could not start: {error}\n")
            returncode = 127
    return {
        "name": name,
        "command": command,
        "returncode": returncode,
        "seconds": round(time.monotonic() - started, 3),
        "raw_log": str(raw_log),
        "output_tail": raw_log.read_text(encoding="utf-8", errors="replace")[-4000:],
    }


def normalized_json(path: Path) -> object:
    value = json.loads(path.read_text(encoding="utf-8"))
    # Only the documented measured fields in these three result types vary.
    ignored = {"summary.json": ("cpu_seconds", "wall_seconds", "peak_rss_kib", "seconds"),
               "pilot.json": ("cpu_seconds", "max_rss_kib")}.get(path.name, ())
    if isinstance(value, dict):
        for key in ignored:
            value.pop(key, None)
    return value


def directory_bytes_equal(left: Path, right: Path) -> tuple[bool, str]:
    if not left.is_dir() or not right.is_dir():
        return False, "comparison directory missing"
    left_files = sorted(p.relative_to(left) for p in left.rglob("*") if p.is_file())
    right_files = sorted(p.relative_to(right) for p in right.rglob("*") if p.is_file())
    if left_files != right_files:
        return False, f"file sets differ: expected={left_files}, generated={right_files}"
    for relative in left_files:
        if (left / relative).read_bytes() != (right / relative).read_bytes():
            return False, f"bytes differ: {relative}"
    return True, f"matched {len(left_files)} files"


def compare_results(retained: Path, reproduced: Path) -> tuple[bool, str]:
    primary = [Path(name) for name in ("semantic.csv", "cache.csv", "integer_rank.csv",
        "residual.csv", "capability_separations.csv", "negative_controls.json",
        "rectangle_negative.json", "pilot.json", "summary.json")]
    certificates = sorted(Path("certificates") / p.name for p in (retained / "certificates").glob("*.json"))
    expected = sorted(primary + certificates)
    generated = sorted(p.relative_to(reproduced) for p in reproduced.rglob("*") if p.is_file())
    if not certificates or generated != expected:
        return False, "reproduced result file set differs from retained primary results"
    for relative in expected:
        left, right = retained / relative, reproduced / relative
        if not left.is_file():return False, f"retained result missing: {relative}"
        if relative in (Path("summary.json"), Path("pilot.json")):
            same = normalized_json(left) == normalized_json(right)
        else:
            same = left.read_bytes() == right.read_bytes()
        if not same:return False, f"reproduced result differs: {relative}"
    return True, f"matched {len(expected)} primary files; only documented timing/RSS fields excluded"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="skip the full campaign reproduction")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--work-dir", type=Path, help="fresh persistent output directory outside the repository")
    args = parser.parse_args()
    # Retain attempts and complete raw outputs, including failures; never clean
    # the source tree or delete the experiment directory as part of validation.
    if args.work_dir:
        temp = args.work_dir.resolve()
        if temp == ROOT or ROOT in temp.parents:parser.error("work directory must be outside the repository")
        temp.mkdir(parents=True, exist_ok=False)
    else:
        temp = Path(tempfile.mkdtemp(prefix="rs-artifact-check-"))
    logs = temp / "logs"
    logs.mkdir()
    def execute(name, command):return run(name, command, logs)
    checks: list[dict] = []
    checks.append(execute("audit", [sys.executable, "audit.py"]))
    checks.append(execute("run_check", [sys.executable, "run.py", "check"]))
    checks.append(execute("unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]))
    checks.append(execute("formal", [sys.executable, "formal/check.py"]))

    independent = temp / "independent.json"
    structured = temp / "structured"
    generated_inputs = temp / "inputs"
    reproduced = temp / "reproduced"
    checks.append(execute("independent_finite_checks",
        [sys.executable, "validation/independent_finite_checks.py", "--root", ".", "--out", str(independent)]))
    checks.append(execute("structured_cases",
        [sys.executable, "validation/structured_cases.py", "--out-dir", str(structured)]))
    retained_structured = ROOT / "results" / "validation" / "structured-cases"
    structured_same = (
        retained_structured.joinpath("instances.csv").is_file()
        and structured.joinpath("instances.csv").is_file()
        and retained_structured.joinpath("instances.csv").read_bytes()
        == structured.joinpath("instances.csv").read_bytes()
        and retained_structured.joinpath("summary.json").is_file()
        and structured.joinpath("summary.json").is_file()
        and normalized_json(retained_structured / "summary.json")
        == normalized_json(structured / "summary.json"))
    checks.append({"name": "structured_cases_retained_comparison",
        "returncode": 0 if structured_same else 1, "seconds": 0, "output_tail": f"equal={structured_same}"})

    checks.append(execute("generate_inputs", [sys.executable, "src/generate_inputs.py", "--out", str(generated_inputs)]))
    inputs_same, inputs_detail = directory_bytes_equal(ROOT / "inputs", generated_inputs / "inputs")
    checks.append({"name": "generated_input_comparison", "returncode": 0 if inputs_same else 1,
                   "seconds": 0, "output_tail": inputs_detail})
    checks.append(execute("pilot", [sys.executable, "src/pilot.py"]))
    if not args.quick:
        checks.append(execute("reproduce", [sys.executable, "run.py", "reproduce", "--out", str(reproduced)]))
        same, detail = compare_results(ROOT / "results", reproduced)
        checks.append({"name": "reproduced_result_comparison", "returncode": 0 if same else 1,
                       "seconds": 0, "output_tail": detail})

    checks.append(execute("package_clean", [sys.executable, "audit.py", "--package-clean"]))

    failed = [check["name"] for check in checks if check.get("returncode") != 0]
    report = {
        "schema": "artifact-check-v1",
        "status": "PASS" if not failed else "FAIL",
        "failed": failed,
        "checks": checks,
        "work_directory": str(temp),
        "scope": "quick checks without reproduction" if args.quick else "full bounded reproduction and comparison",
        "boundary": (
            "Internal consistency and reproducibility check; not external peer review, "
            "a novelty proof, full proof-assistant mechanization, or an acceptance guarantee."
        ),
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    (temp / "report.json").write_text(text + "\n", encoding="utf-8", newline="\n")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
