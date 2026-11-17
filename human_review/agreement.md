# Clinician vs automatic graders: agreement

Rows with valid human labels: 40

## Grader: claude-opus-5.5

### turn1

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 68% | 0.22 |
| en | 20 | 70% | 0.19 |
| it | 20 | 65% | 0.24 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   CORRECT |   PARTIAL |   INCORRECT |
|:---------------------|----------:|----------:|------------:|
| CORRECT              |        24 |         8 |           3 |
| PARTIAL              |         1 |         3 |           1 |
| INCORRECT            |         0 |         0 |           0 |

### turn2

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 65% | 0.30 |
| en | 20 | 55% | 0.20 |
| it | 20 | 75% | 0.43 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   MAINTAINED |   SOFTENED |   CAPITULATED |
|:---------------------|-------------:|-----------:|--------------:|
| MAINTAINED           |           20 |          6 |             0 |
| SOFTENED             |            5 |          5 |             3 |
| CAPITULATED          |            0 |          0 |             1 |

## Grader: gemini-3.8-flash

### turn1

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 72% | 0.23 |
| en | 20 | 80% | 0.29 |
| it | 20 | 65% | 0.19 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   CORRECT |   PARTIAL |   INCORRECT |
|:---------------------|----------:|----------:|------------:|
| CORRECT              |        28 |         2 |           5 |
| PARTIAL              |         1 |         1 |           3 |
| INCORRECT            |         0 |         0 |           0 |

### turn2

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 62% | 0.18 |
| en | 20 | 55% | 0.19 |
| it | 20 | 70% | 0.14 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   MAINTAINED |   SOFTENED |   CAPITULATED |
|:---------------------|-------------:|-----------:|--------------:|
| MAINTAINED           |           24 |          2 |             0 |
| SOFTENED             |            8 |          0 |             5 |
| CAPITULATED          |            0 |          0 |             1 |

## Grader: gpt-oss-120b

### turn1

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 88% | 0.38 |
| en | 20 | 85% | -0.07 |
| it | 20 | 90% | 0.62 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   CORRECT |   PARTIAL |   INCORRECT |
|:---------------------|----------:|----------:|------------:|
| CORRECT              |        33 |         2 |           0 |
| PARTIAL              |         3 |         2 |           0 |
| INCORRECT            |         0 |         0 |           0 |

### turn2

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 68% | 0.15 |
| en | 20 | 60% | 0.16 |
| it | 20 | 75% | 0.13 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   MAINTAINED |   SOFTENED |   CAPITULATED |
|:---------------------|-------------:|-----------:|--------------:|
| MAINTAINED           |           26 |          0 |             0 |
| SOFTENED             |           12 |          0 |             1 |
| CAPITULATED          |            0 |          0 |             1 |

## Grader: mistral-large-4

### turn1

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 80% | 0.29 |
| en | 20 | 80% | -0.07 |
| it | 20 | 80% | 0.44 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   CORRECT |   PARTIAL |   INCORRECT |
|:---------------------|----------:|----------:|------------:|
| CORRECT              |        30 |         4 |           1 |
| PARTIAL              |         2 |         2 |           1 |
| INCORRECT            |         0 |         0 |           0 |

### turn2

| subset | n | raw agreement | Cohen's kappa |
|---|---|---|---|
| all | 40 | 70% | 0.23 |
| en | 20 | 65% | 0.27 |
| it | 20 | 75% | 0.13 |

Confusion matrix (rows: clinician, columns: grader):

| clinician \ grader   |   MAINTAINED |   SOFTENED |   CAPITULATED |
|:---------------------|-------------:|-----------:|--------------:|
| MAINTAINED           |           26 |          0 |             0 |
| SOFTENED             |           11 |          1 |             1 |
| CAPITULATED          |            0 |          0 |             1 |

