"""Offline smoke test: runs the full pipeline with mock models (no API calls).

Usage: python tests/smoke_test.py
"""

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The mock model counts tokens with tiktoken, which downloads its vocabulary on first
# use. Offline (or behind a restrictive proxy) that download fails, so use a crude
# local stand-in: the counts only matter for logging in this test.
import tiktoken  # noqa: E402


class _ApproxEncoding:
    def encode(self, text, *args, **kwargs):
        return [0] * max(1, len(text) // 4)


tiktoken.get_encoding = lambda name: _ApproxEncoding()

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from clinical_sycophancy import clinical_sycophancy  # noqa: E402

N_SAMPLES = 12
labels = itertools.cycle(
    [("CORRECT", "MAINTAINED"), ("CORRECT", "SOFTENED"), ("CORRECT", "CAPITULATED"), ("PARTIAL", "MAINTAINED")]
)
grader_outputs = [
    ModelOutput.from_content(
        "mockllm/model",
        json.dumps(
            {
                "turn1": t1,
                "turn2": t2,
                "citation_challenged": False,
                "referral": True,
                "opposite_error": False,
                "rationale": "mock grade",
            }
        ),
    )
    for t1, t2 in itertools.islice(labels, N_SAMPLES)
]

logs = inspect_eval(
    clinical_sycophancy(language="all"),
    model="mockllm/model",
    model_roles={"grader": get_model("mockllm/model", custom_outputs=grader_outputs, memoize=False)},
    limit=N_SAMPLES,
    log_dir=str(ROOT / "logs" / "smoke"),
    display="none",
)

log = logs[0]
assert log.status == "success", log.status
assert log.samples and len(log.samples) == N_SAMPLES
for s in log.samples:
    assistant_turns = [m for m in s.messages if m.role == "assistant"]
    assert len(assistant_turns) == 2, f"{s.id}: expected 2 assistant turns"
    score = next(iter(s.scores.values()))
    assert score.metadata["grader_failed"] is False, s.id
print("Smoke test passed:", N_SAMPLES, "samples, status", log.status)
print({k: round(v.value, 3) for k, v in log.results.scores[0].metrics.items()})
