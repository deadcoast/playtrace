"""Compare full duplicate detection with a saved baseline resolver module.

Example (from the repository root):
    git show 609ce2a~1:playtrace/classify/resolver.py > /tmp/baseline_resolver.py
    uv run python tools/benchmark_duplicate_detection.py --baseline /tmp/baseline_resolver.py

Synthetic workloads are reproducible, not a substitute for live-data profiling.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import random
from statistics import median
import string
import sys
from time import perf_counter

# Also support direct execution from an uninstalled source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playtrace.classify.resolver import ResolvedTitle, TitleResolver
from playtrace.models.enums import Classification, ConfidenceLevel


def measure(resolver_type: type, titles: list[ResolvedTitle], repeats: int) -> dict:
    class CountingResolver(resolver_type):
        calls = 0

        def _duplicate_reasons(self, left, right):
            self.calls += 1
            return super()._duplicate_reasons(left, right)

    times = []
    for _ in range(repeats):
        resolver = CountingResolver()
        start = perf_counter()
        result = resolver._duplicate_candidates(titles)
        times.append(perf_counter() - start)
    return {"median_seconds": round(median(times), 6), "verification_calls": resolver.calls,
            "groups": len(result)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--sizes", type=int, nargs="+", default=[200, 500, 1000])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("baseline_resolver", args.baseline)
    assert spec and spec.loader
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    rows = []
    for size in args.sizes:
        rng = random.Random(42)
        titles = [ResolvedTitle(
            title_id=f"title:{index}", title="".join(rng.choices(string.ascii_lowercase, k=24)),
            classification=Classification.GAME, classification_confidence=ConfidenceLevel.HIGH,
            title_confidence=ConfidenceLevel.HIGH, launcher=None, primary_exe_id=f"exe:{index}",
        ) for index in range(size)]
        old = measure(baseline.TitleResolver, titles, args.repeats)
        new = measure(TitleResolver, titles, args.repeats)
        assert old["groups"] == new["groups"] == 0
        rows.append({"titles": size, "baseline": old, "optimized": new,
                     "speedup": round(old["median_seconds"] / new["median_seconds"], 2)})
    print(json.dumps({"python": sys.version.split()[0], "seed": 42, "repeats": args.repeats,
                      "workload": "Independent 24-character lowercase synthetic titles, no launcher",
                      "results": rows}, indent=2))


if __name__ == "__main__":
    main()
