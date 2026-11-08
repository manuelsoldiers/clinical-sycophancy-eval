"""Run the eval for every target model in config/models.json, one after the other.

All targets get exactly the same samples (same shuffle seed) and the same graders.

Usage:
  python scripts/run_eval.py --limit 20                      # trial: 20 conversations per model
  python scripts/run_eval.py                                 # full run: 720 per model
  python scripts/run_eval.py --models gpt-oss-20b --language it

OpenRouter key: read from OPENROUTER_API_KEY. In a session where a network proxy
injects the key, any placeholder value works (the script sets one if unset).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from inspect_ai import eval as inspect_eval  # noqa: E402

from clinical_sycophancy import clinical_sycophancy  # noqa: E402

CONFIG = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=list(CONFIG["targets"]), help="target keys")
    parser.add_argument("--graders", nargs="*", default=list(CONFIG["graders"]), help="grader keys")
    parser.add_argument("--language", default="all", choices=["en", "it", "all"])
    parser.add_argument("--limit", type=int, default=None, help="samples per model (default: all)")
    parser.add_argument("--seed", type=int, default=2026, help="shuffle seed, shared by all models")
    parser.add_argument("--log-dir", default=str(ROOT / "logs" / "runs"))
    parser.add_argument("--max-connections", type=int, default=8)
    args = parser.parse_args()

    os.environ.setdefault("OPENROUTER_API_KEY", "proxy-injected")

    for key in args.models:
        spec = CONFIG["targets"][key]
        print(f"\n=== {key} ({spec['model']}, provider {spec['provider']['order']}) ===")
        logs = inspect_eval(
            clinical_sycophancy(language=args.language, graders=args.graders),
            model=spec["model"],
            model_args={"provider": spec["provider"]},
            limit=args.limit,
            sample_shuffle=args.seed,
            log_dir=args.log_dir,
            max_connections=args.max_connections,
            tags=[key],
            metadata={"target_key": key, "graders": args.graders, "seed": args.seed},
            display="plain",
        )
        log = logs[0]
        print(f"status: {log.status}")
        if log.results and log.results.scores:
            for s in log.results.scores:
                print("  " + ", ".join(f"{s.name}.{m}={v.value:.3f}" for m, v in s.metrics.items()))


if __name__ == "__main__":
    main()
