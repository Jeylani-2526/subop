"""CDC latency KPI runs and report (M8W29T4), per kickoff notes Part B item 4a."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.cdc.latency_store import TABLE, LatencyStore
from services.connectors.errors import ConnectorError

KPI_MS = 30_000
COUNTED = 30
WARM_UP = 1
EVENT_TABLE = "cdc_demo.orders"
EVENT_OP = "insert"
HOP_ORDER = ("e2e", "capture", "publish", "consumer", "warehouse")


def report_sql(table: str = TABLE) -> str:
    # The query the record cites. Window = ids first..last inclusive; the first
    # WARM_UP rows are reported apart and never counted.
    return f"""
WITH w AS (
    SELECT id, t0_ms, t1_ms, t2_ms, t3_ms, t4_ms
    FROM {table}
    WHERE id BETWEEN %(first)s AND %(last)s
      AND table_name = %(table_name)s AND op = %(op)s
    ORDER BY id
    OFFSET %(skip)s
), h AS (
    SELECT 'e2e' AS hop, t4_ms - t0_ms AS ms FROM w
    UNION ALL SELECT 'capture',   t1_ms - t0_ms FROM w
    UNION ALL SELECT 'publish',   t2_ms - t1_ms FROM w
    UNION ALL SELECT 'consumer',  t3_ms - t2_ms FROM w
    UNION ALL SELECT 'warehouse', t4_ms - t3_ms FROM w
)
SELECT hop,
       count(*) AS n,
       min(ms) AS min_ms,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY ms) AS median_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS p95_ms,
       max(ms) AS max_ms,
       count(*) FILTER (WHERE ms > {KPI_MS}) AS over_30s
FROM h
GROUP BY hop
""".strip()


@dataclass
class Window:
    first_id: int
    last_id: int


# -- clock ------------------------------------------------------------------


def clock_samples(
    db_ms: Callable[[], int], now_ms: Callable[[], int], n: int = 5
) -> List[Tuple[int, int]]:
    """(skew, uncertainty) per sample: database clock minus this host's clock,
    taken at the midpoint of the round trip, +/- half the round trip."""
    samples = []
    for _ in range(n):
        before = now_ms()
        db = db_ms()
        after = now_ms()
        samples.append((db - (before + after) // 2, (after - before + 1) // 2))
    return samples


# -- runs -----------------------------------------------------------------------


def wait_for_new_event(
    latest: Callable[[int], Optional[int]],
    after_id: int,
    timeout_s: float,
    sleep: Callable[[float], None],
    now: Callable[[], float],
    poll_s: float = 0.5,
) -> Optional[int]:
    deadline = now() + timeout_s
    while now() < deadline:
        found = latest(after_id)
        if found is not None:
            return found
        sleep(poll_s)
    return None


def run_idle(
    make_change: Callable[[], Any],
    latest: Callable[[int], Optional[int]],
    current_max: Callable[[], int],
    count: int,
    pause_s: float,
    timeout_s: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> Window:
    """One change at a time: the next is made only after the previous event's
    t4 is recorded, plus pause_s."""
    last = current_max()
    first = None
    for i in range(count):
        make_change()
        found = wait_for_new_event(latest, last, timeout_s, sleep, now)
        if found is None:
            raise TimeoutError(
                f"event {i + 1} of {count} not recorded within {timeout_s:.0f} s"
            )
        first = found if first is None else first
        last = found
        print(f"  event {i + 1}/{count} recorded (id {found})", flush=True)
        if i + 1 < count:
            sleep(pause_s)
    return Window(first, last)


def run_active(
    start_load: Callable[[], Any],
    stop_load: Callable[[Any], None],
    latest: Callable[[int], Optional[int]],
    current_max: Callable[[], int],
    count: int,
    timeout_s: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> Window:
    """Background load running; collect the next `count` events it produces."""
    last = current_max()
    first = None
    load = start_load()
    try:
        for i in range(count):
            found = wait_for_new_event(latest, last, timeout_s, sleep, now)
            if found is None:
                raise TimeoutError(
                    f"event {i + 1} of {count} not recorded within {timeout_s:.0f} s"
                )
            first = found if first is None else first
            last = found
            print(f"  event {i + 1}/{count} recorded (id {found})", flush=True)
    finally:
        stop_load(load)
    return Window(first, last)


# -- report -------------------------------------------------------------------


def report(layer: Any, window: Window, table: str = TABLE) -> Dict[str, Any]:
    params = {
        "first": window.first_id,
        "last": window.last_id,
        "table_name": EVENT_TABLE,
        "op": EVENT_OP,
    }
    warm = layer.execute_query(
        f"SELECT id, t4_ms - t0_ms AS e2e_ms FROM {table} "
        f"WHERE id BETWEEN %(first)s AND %(last)s "
        f"AND table_name = %(table_name)s AND op = %(op)s ORDER BY id LIMIT {WARM_UP}",
        params,
    )
    rows = layer.execute_query(report_sql(table), {**params, "skip": WARM_UP})
    hops = {r["hop"]: dict(r) for r in rows}
    e2e = hops.get("e2e")
    if e2e is None or e2e["n"] != COUNTED:
        verdict = f"INCOMPLETE ({0 if e2e is None else e2e['n']} of {COUNTED} counted)"
    elif e2e["p95_ms"] < KPI_MS:
        verdict = "MET"
    else:
        verdict = "NOT MET"
    return {
        "window": window,
        "warm_up": [dict(r) for r in warm],
        "hops": [hops[h] for h in HOP_ORDER if h in hops],
        "verdict": verdict,
    }


def _fmt(value: Any) -> str:
    # percentile_cont over whole milliseconds at 0.5 / 0.95 of 30 values is
    # exact to two decimals, so this strips float noise only, never data.
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def print_report(label: str, result: Dict[str, Any]) -> None:
    w = result["window"]
    print(f"\n{label}: ids {w.first_id}..{w.last_id}")
    for row in result["warm_up"]:
        print(f"  warm-up (not counted): id {row['id']}, e2e {row['e2e_ms']} ms")
    columns = ("hop", "n", "min_ms", "median_ms", "p95_ms", "max_ms", "over_30s")
    print("  " + "  ".join(f"{c:>10}" for c in columns))
    for h in result["hops"]:
        print("  " + "  ".join(f"{_fmt(h[c]):>10}" for c in columns))
    print(f"  KPI (p95 of e2e < {KPI_MS} ms): {result['verdict']}")


# -- command line -----------------------------------------------------------


def _layer():
    from services.etl_engine.connection_resolver import resolve_connection

    layer, _ = resolve_connection(
        "postgresql", os.environ.get("CDC_STATE_REF", "dw-main")
    )
    # Idempotent, as the API does: a run before the consumer's first event
    # waits for rows instead of failing on a missing table.
    LatencyStore(layer).ensure_schema()
    return layer


def _latest(layer: Any) -> Callable[[int], Optional[int]]:
    def latest(after_id: int) -> Optional[int]:
        rows = layer.execute_query(
            f"SELECT min(id) AS id FROM {TABLE} WHERE id > %s "
            f"AND table_name = %s AND op = %s",
            (after_id, EVENT_TABLE, EVENT_OP),
        )
        return rows[0]["id"]

    return latest


def _current_max(layer: Any) -> Callable[[], int]:
    def current_max() -> int:
        return layer.execute_query(f"SELECT coalesce(max(id), 0) AS id FROM {TABLE}")[
            0
        ]["id"]

    return current_max


def _print_clock(layer: Any) -> None:
    def db_ms() -> int:
        return layer.execute_query(
            "SELECT (extract(epoch FROM clock_timestamp()) * 1000)::bigint AS ms"
        )[0]["ms"]

    samples = clock_samples(db_ms, lambda: int(time.time() * 1000))
    print("clock: Postgres container minus this host (ms), +/- half round trip")
    for skew, err in samples:
        print(f"  {skew:+d} +/- {err}")
    worst = max(abs(s) + e for s, e in samples)
    print(f"  worst case |skew| <= {worst} ms")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CDC latency KPI (M8W29T4).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("clock", help="measure container-vs-host clock skew")
    idle = sub.add_parser("idle", help="idle condition: one change at a time")
    idle.add_argument("--count", type=int, default=WARM_UP + COUNTED)
    idle.add_argument("--pause", type=float, default=5.0)
    idle.add_argument("--timeout", type=float, default=300.0)
    active = sub.add_parser("active", help="active condition: background load")
    active.add_argument("--count", type=int, default=WARM_UP + COUNTED)
    active.add_argument("--interval", type=float, default=2.0)
    active.add_argument("--timeout", type=float, default=300.0)
    rep = sub.add_parser("report", help="report an id window again")
    rep.add_argument("first_id", type=int)
    rep.add_argument("last_id", type=int)
    sub.add_parser("sql", help="print the report SQL")
    args = parser.parse_args(argv)

    if args.command == "sql":
        print(report_sql())
        return 0

    from services.cdc.cdc_demo_changes import _load_dotenv

    _load_dotenv()
    try:
        return _run(args)
    except ConnectorError as exc:
        print(f"Run failed: {exc.error_code}: {exc.message}", file=sys.stderr)
        return 4


def _run(args: argparse.Namespace) -> int:
    layer = _layer()
    if args.command == "clock":
        _print_clock(layer)
        return 0
    if args.command == "report":
        print_report("report", report(layer, Window(args.first_id, args.last_id)))
        return 0

    _print_clock(layer)
    try:
        if args.command == "idle":
            from services.cdc.cdc_demo_changes import connect, insert_order

            conn = connect()
            try:
                window = run_idle(
                    lambda: insert_order(conn),
                    _latest(layer),
                    _current_max(layer),
                    args.count,
                    args.pause,
                    args.timeout,
                )
            finally:
                conn.close()
        else:
            command = [
                sys.executable,
                "-m",
                "services.cdc.cdc_demo_changes",
                "--insert",
                "--loop",
                "0",
                "--interval",
                str(args.interval),
            ]
            window = run_active(
                lambda: subprocess.Popen(command),
                lambda proc: (proc.terminate(), proc.wait(timeout=30)),
                _latest(layer),
                _current_max(layer),
                args.count,
                args.timeout,
            )
    except TimeoutError as exc:
        print(f"Run stopped: {exc}", file=sys.stderr)
        return 3
    print_report(args.command, report(layer, window))
    return 0


if __name__ == "__main__":
    sys.exit(main())
