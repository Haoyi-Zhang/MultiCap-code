"""Independent legality and execution checker for two-phase factor schedules.

The checker deliberately does not call the compiler.  It validates strict
natural-number inputs, a nonnegative integer factorization, the phase boundary,
fixed fast/slow addresses, exactly two transient buffers, one-shot slow reloads,
and the append-only output event while executing the event trace.
"""
from __future__ import annotations
from typing import Any


def _nat(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a natural integer")
    return value


def _vector(value: Any, length: int, label: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{label} has the wrong length")
    return tuple(_nat(x, f"{label}[{i}]") for i, x in enumerate(value))


def _matrix(value: Any, label: str = "matrix") -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{label} must be a nonempty matrix")
    if not isinstance(value[0], (list, tuple)) or not value[0]:
        raise ValueError(f"{label} must have a nonempty first row")
    cols = len(value[0])
    rows = []
    for i, row in enumerate(value):
        if not isinstance(row, (list, tuple)) or len(row) != cols:
            raise ValueError(f"{label} must be rectangular")
        rows.append(tuple(_nat(x, f"{label}[{i}][{j}]") for j, x in enumerate(row)))
    return tuple(rows)


def _factorization(packet: dict) -> tuple[tuple[tuple[int, ...], ...], list[tuple[tuple[int, ...], tuple[int, ...]]]]:
    if not isinstance(packet, dict):
        raise ValueError("factor packet must be an object")
    matrix = _matrix(packet.get("matrix"))
    rows, cols = len(matrix), len(matrix[0])
    if "rows" in packet and _nat(packet["rows"], "rows") != rows:
        raise ValueError("row count does not match matrix")
    if "cols" in packet and _nat(packet["cols"], "cols") != cols:
        raise ValueError("column count does not match matrix")
    witness = packet.get("witness")
    if not isinstance(witness, list):
        raise ValueError("witness must be a list")
    factors: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    total = [[0 for _ in range(cols)] for _ in range(rows)]
    for ell, factor in enumerate(witness):
        if not isinstance(factor, dict):
            raise ValueError(f"factor {ell} must be an object")
        u = _vector(factor.get("u"), rows, f"factor {ell} u")
        v = _vector(factor.get("v"), cols, f"factor {ell} v")
        atom = tuple(tuple(u[i] * v[j] for j in range(cols)) for i in range(rows))
        if "atom" in factor and _matrix(factor["atom"], f"factor {ell} atom") != atom:
            raise ValueError(f"factor {ell} atom does not equal its outer product")
        for i in range(rows):
            for j in range(cols):
                total[i][j] += atom[i][j]
        factors.append((u, v))
    if tuple(tuple(row) for row in total) != matrix:
        raise ValueError("witness does not sum to the target matrix")
    return matrix, factors


def _event(event: Any, index: int) -> dict:
    if not isinstance(event, dict) or type(event.get("op")) is not str:
        raise ValueError(f"event {index} is malformed")
    return event


def _exact_keys(event: dict, required: set[str], index: int) -> None:
    if set(event) != required:
        raise ValueError(f"event {index} has wrong fields for {event.get('op')}: {sorted(event)}")


def check_factor_schedule(packet: dict, x: list[int], y: list[int], fast_words: int,
                          schedule: dict) -> dict:
    """Execute and validate a generated schedule without using compiler helpers."""
    matrix, factors = _factorization(packet)
    rows, cols = len(matrix), len(matrix[0])
    xv = _vector(x, rows, "x")
    yv = _vector(y, cols, "y")
    M = _nat(fast_words, "fast_words")
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be an object")
    if schedule.get("transient_buffers") != 2:
        raise ValueError("schedule must declare exactly two transient buffers")
    events = schedule.get("events")
    if not isinstance(events, list):
        raise ValueError("schedule events must be a list")

    width = len(factors)
    fast_count = min(M, width)
    slow_count = width - fast_count
    phase = "prefix"
    barrier_seen = False
    emitted = False
    t0: int | None = None
    t1: int | None = None
    fast: dict[int, tuple[int, int]] = {}
    slow: dict[int, tuple[int, int]] = {}
    slow_reads: set[int] = set()
    prefix_factor = 0
    prefix_index = -1
    continuation_factor = -1
    right_index = -1
    expected_prefix_op = "prefix_reset" if width else "barrier"
    expected_cont_op = "output_reset"
    slow_writes = 0
    slow_read_events = 0
    fast_read_events = 0
    x_reads = 0
    y_reads = 0

    for idx, raw in enumerate(events):
        e = _event(raw, idx)
        op = e["op"]
        if emitted:
            raise ValueError("events occur after append-only output emission")

        if phase == "prefix":
            if op != expected_prefix_op:
                raise ValueError(f"event {idx}: expected {expected_prefix_op}, found {op}")
            if op == "prefix_reset":
                _exact_keys(e, {"op", "factor", "temp"}, idx)
                if e["factor"] != prefix_factor or e["temp"] != "T0":
                    raise ValueError("prefix reset uses wrong factor or buffer")
                t0 = 0
                prefix_index = 0
                expected_prefix_op = "prefix_madd" if rows else ("keep_fast" if prefix_factor < fast_count else "write_slow")
            elif op == "prefix_madd":
                _exact_keys(e, {"op", "factor", "x_index", "coefficient", "temp"}, idx)
                u, _ = factors[prefix_factor]
                if (e["factor"] != prefix_factor or e["x_index"] != prefix_index or
                        e["coefficient"] != u[prefix_index] or e["temp"] != "T0"):
                    raise ValueError("prefix multiply-add has wrong factor, source, coefficient, or buffer")
                if t0 is None:
                    raise ValueError("prefix multiply-add uses an uninitialized buffer")
                t0 += u[prefix_index] * xv[prefix_index]
                x_reads += 1
                prefix_index += 1
                expected_prefix_op = ("prefix_madd" if prefix_index < rows else
                                      ("keep_fast" if prefix_factor < fast_count else "write_slow"))
            elif op == "keep_fast":
                _exact_keys(e, {"op", "factor", "slot", "from"}, idx)
                slot = e["slot"]
                if (e["factor"] != prefix_factor or e["from"] != "T0" or
                        type(slot) is not int or not (0 <= slot < fast_count) or slot != prefix_factor):
                    raise ValueError("fast placement has wrong factor or address")
                if slot in fast:
                    raise ValueError("fast slot overwritten")
                if t0 is None:
                    raise ValueError("fast placement uses an uninitialized buffer")
                fast[slot] = (prefix_factor, t0)
                prefix_factor += 1
                expected_prefix_op = "prefix_reset" if prefix_factor < width else "barrier"
            elif op == "write_slow":
                _exact_keys(e, {"op", "factor", "slot", "from"}, idx)
                slot = e["slot"]
                expected_slot = prefix_factor - fast_count
                if (e["factor"] != prefix_factor or e["from"] != "T0" or
                        type(slot) is not int or not (0 <= slot < slow_count) or slot != expected_slot):
                    raise ValueError("slow write has wrong factor or address")
                if slot in slow:
                    raise ValueError("slow slot overwritten")
                if t0 is None:
                    raise ValueError("slow write uses an uninitialized buffer")
                slow[slot] = (prefix_factor, t0)
                slow_writes += 1
                prefix_factor += 1
                expected_prefix_op = "prefix_reset" if prefix_factor < width else "barrier"
            elif op == "barrier":
                _exact_keys(e, {"op", "clears"}, idx)
                if e["clears"] != ["T0", "T1"]:
                    raise ValueError("barrier must clear both transient buffers")
                if prefix_factor != width or len(fast) != fast_count or len(slow) != slow_count:
                    raise ValueError("barrier reached before all factors were placed")
                t0 = None
                t1 = None
                phase = "continuation"
                barrier_seen = True
                expected_cont_op = "output_reset"
            else:  # pragma: no cover: guarded by expected op
                raise ValueError("illegal prefix event")
            continue

        # Continuation phase: no x access is represented by any legal event.
        if op != expected_cont_op:
            raise ValueError(f"event {idx}: expected {expected_cont_op}, found {op}")
        if op == "output_reset":
            _exact_keys(e, {"op", "temp"}, idx)
            if e["temp"] != "T0":
                raise ValueError("output accumulator must be T0")
            t0 = 0
            continuation_factor = 0
            expected_cont_op = "emit" if width == 0 else "right_reset"
        elif op == "right_reset":
            _exact_keys(e, {"op", "factor", "temp"}, idx)
            if e["factor"] != continuation_factor or e["temp"] != "T1":
                raise ValueError("right reset uses wrong factor or buffer")
            t1 = 0
            right_index = 0
            expected_cont_op = "right_madd" if cols else ("accumulate_fast" if continuation_factor < fast_count else "read_slow_madd")
        elif op == "right_madd":
            _exact_keys(e, {"op", "factor", "y_index", "coefficient", "temp"}, idx)
            _, v = factors[continuation_factor]
            if (e["factor"] != continuation_factor or e["y_index"] != right_index or
                    e["coefficient"] != v[right_index] or e["temp"] != "T1"):
                raise ValueError("right multiply-add has wrong factor, source, coefficient, or buffer")
            if t1 is None:
                raise ValueError("right multiply-add uses an uninitialized buffer")
            t1 += v[right_index] * yv[right_index]
            y_reads += 1
            right_index += 1
            expected_cont_op = ("right_madd" if right_index < cols else
                                ("accumulate_fast" if continuation_factor < fast_count else "read_slow_madd"))
        elif op == "accumulate_fast":
            _exact_keys(e, {"op", "factor", "slot", "right_temp", "output_temp"}, idx)
            slot = e["slot"]
            if (e["factor"] != continuation_factor or e["right_temp"] != "T1" or
                    e["output_temp"] != "T0" or type(slot) is not int or
                    not (0 <= slot < fast_count) or slot != continuation_factor):
                raise ValueError("fast accumulate has wrong factor or address")
            if slot not in fast or fast[slot][0] != continuation_factor:
                raise ValueError("fast accumulate reads an unwritten or aliased slot")
            if t0 is None or t1 is None:
                raise ValueError("fast accumulate uses an uninitialized transient buffer")
            t0 += fast[slot][1] * t1
            fast_read_events += 1
            continuation_factor += 1
            expected_cont_op = "right_reset" if continuation_factor < width else "emit"
        elif op == "read_slow_madd":
            _exact_keys(e, {"op", "factor", "slot", "right_temp", "output_temp"}, idx)
            slot = e["slot"]
            expected_slot = continuation_factor - fast_count
            if (e["factor"] != continuation_factor or e["right_temp"] != "T1" or
                    e["output_temp"] != "T0" or type(slot) is not int or
                    not (0 <= slot < slow_count) or slot != expected_slot):
                raise ValueError("slow fused reload has wrong factor or address")
            if slot not in slow or slow[slot][0] != continuation_factor:
                raise ValueError("slow fused reload reads an unwritten or aliased slot")
            if slot in slow_reads:
                raise ValueError("slow slot reloaded more than once")
            if t0 is None or t1 is None:
                raise ValueError("slow fused reload uses an uninitialized transient buffer")
            slow_reads.add(slot)
            t0 += slow[slot][1] * t1
            slow_read_events += 1
            continuation_factor += 1
            expected_cont_op = "right_reset" if continuation_factor < width else "emit"
        elif op == "emit":
            _exact_keys(e, {"op", "from", "channel"}, idx)
            if e["from"] != "T0" or e["channel"] != "append_only":
                raise ValueError("output event must emit T0 to the append-only channel")
            if continuation_factor != width or t0 is None:
                raise ValueError("output emitted before all factors were accumulated")
            emitted = True
        else:  # pragma: no cover: guarded by expected op
            raise ValueError("illegal continuation event")

    if not barrier_seen or not emitted:
        raise ValueError("schedule is missing its barrier or final output event")
    if len(slow_reads) != slow_count or slow_writes != slow_count:
        raise ValueError("slow placements and one-shot reloads are incomplete")
    direct = sum(matrix[i][j] * xv[i] * yv[j] for i in range(rows) for j in range(cols))
    if t0 != direct:
        raise ValueError("executed schedule does not equal the target bilinear form")
    transfers = slow_writes + slow_read_events
    declared = schedule.get("temporary_word_transfers")
    if type(declared) is not int or declared != transfers:
        raise ValueError("declared temporary-word traffic does not match executed events")
    if declared != 2 * max(0, width - M):
        raise ValueError("executed traffic does not match the fixed placement policy")
    if schedule.get("value") != t0:
        raise ValueError("reported schedule value does not match independent execution")
    return {
        "value": t0,
        "factor_width": width,
        "events_checked": len(events),
        "x_source_reads": x_reads,
        "y_source_reads": y_reads,
        "fast_persistent_reads": fast_read_events,
        "slow_writes": slow_writes,
        "slow_reads": slow_read_events,
        "temporary_word_transfers": transfers,
        "barriers_checked": 1,
        "transient_buffers": 2,
        "append_only_emits": 1,
    }
