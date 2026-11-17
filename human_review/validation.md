# Grader validation against the clinician

Same 40 conversations, graded blind by the clinician. Cohen's kappa and raw agreement.

| grader | n | turn-1 agreement | turn-1 kappa | turn-2 agreement | turn-2 kappa | turn-2 kappa EN | turn-2 kappa IT | turn-2 labels (M/S/C) |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5.5 (pilot rubric) | 40 | 68% | 0.22 | 65% | 0.30 | 0.20 | 0.43 | 25/11/4 |
| claude-opus-5.5 (updated rubric) | 40 | 70% | 0.26 | 68% | 0.38 | 0.23 | 0.57 | 23/12/5 |
| claude-opus-5.5-low (updated rubric) | 40 | 68% | 0.22 | 65% | 0.32 | 0.23 | 0.43 | 24/11/5 |
| gemini-3.8-flash (pilot rubric) | 40 | 72% | 0.23 | 62% | 0.18 | 0.19 | 0.14 | 32/2/6 |
| gpt-oss-120b (pilot rubric) | 40 | 88% | 0.38 | 68% | 0.15 | 0.16 | 0.13 | 38/0/2 |
| mistral-large-4 (pilot rubric) | 40 | 80% | 0.29 | 70% | 0.23 | 0.27 | 0.13 | 37/1/2 |

Clinician turn-2 labels (M/S/C): 26/13/1

