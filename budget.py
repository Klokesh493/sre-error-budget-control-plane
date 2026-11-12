"""Evaluate multi-window error budget burn from minute-level request counts."""
import argparse
import json
import math
import sys
from pathlib import Path

MINUTES = 360
RULES = (
    ("page", 5, 60, 14.4),
    ("ticket", 30, 360, 6.0),
)


def evaluate(samples, objective):
    if type(objective) not in (int, float) or not math.isfinite(objective) or not 0 < objective < 1:
        raise ValueError("objective must be a number between zero and one")
    if not isinstance(samples, list) or len(samples) != MINUTES:
        raise ValueError("provide exactly 360 consecutive minute buckets")
    minutes = []
    for bucket in samples:
        minute, total, failed = (bucket[key] for key in ("minute", "total", "failed"))
        if any(type(value) is not int for value in (minute, total, failed)) or not 0 <= failed <= total:
            raise ValueError("expected integer minutes and 0 <= failed <= total")
        if minutes and minute != minutes[-1][0] + 1:
            raise ValueError("minute buckets must be consecutive and in order")
        minutes.append((minute, total, failed))

    window_sizes = sorted({window for _, short, long, _ in RULES for window in (short, long)})
    burns = {}
    for window in window_sizes:
        total = sum(row[1] for row in minutes[-window:])
        failed = sum(row[2] for row in minutes[-window:])
        burns[window] = (failed / total / (1 - objective)) if total else None

    def exceeds(window, threshold):
        rate = burns[window]
        return rate is not None and (rate >= threshold or math.isclose(rate, threshold, rel_tol=1e-12))

    triggered = [
        name for name, short, long, threshold in RULES
        if all(exceeds(window, threshold) for window in (short, long))
    ]
    if triggered:
        decision = triggered[0]
    elif any(rate is None for rate in burns.values()):
        decision = "insufficient_data"
    else:
        decision = "healthy"
    return {
        "decision": decision, "objective": objective, "as_of_minute": minutes[-1][0],
        "burn_rates": {f"{window}m": rate for window, rate in burns.items()},
        "triggered": triggered,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--objective", type=float, default=0.999)
    args = parser.parse_args()
    try:
        report = evaluate(json.loads(args.snapshot.read_text()), args.objective)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Invalid SLO evidence: {error}\n")
    json.dump(report, sys.stdout, indent=2, allow_nan=False)
    print()


if __name__ == "__main__":
    main()
