# Knowledge-Level predictor - evaluation report

Training data: 156 labelled questions (seed + any user_labeled / feedback files).

## 1. 5-fold cross-validation on the training data

| system | n | exact acc | within ±1 | macro-F1 | wrong | wrong but flagged | flagged % | acc on unflagged |
|---|---|---|---|---|---|---|---|---|
| rules only | 156 | 97.4% | 99.4% | 0.974 | 4 | 2 | 1% | 98.7% |
| ML only | 156 | 84.0% | 88.5% | 0.840 | 25 | 25 | 48% | 100.0% |
| hybrid | 156 | 97.4% | 98.1% | 0.973 | 4 | 2 | 9% | 98.6% |

Hybrid confusion matrix (CV):

| true \ pred | K1 | K2 | K3 | K4 | K5 | K6 |
|---|---|---|---|---|---|---|
| **K1** | 28 | 0 | 0 | 0 | 0 | 0 |
| **K2** | 0 | 29 | 0 | 0 | 0 | 0 |
| **K3** | 0 | 0 | 24 | 0 | 2 | 0 |
| **K4** | 0 | 0 | 0 | 27 | 0 | 0 |
| **K5** | 0 | 0 | 0 | 1 | 22 | 0 |
| **K6** | 0 | 0 | 1 | 0 | 0 | 22 |

## 2. Tricky hold-out set (never trained on, but written while the rules were being tuned - optimistic)

| system | n | exact acc | within ±1 | macro-F1 | wrong | wrong but flagged | flagged % | acc on unflagged |
|---|---|---|---|---|---|---|---|---|
| rules only | 38 | 97.4% | 100.0% | 0.959 | 1 | 1 | 5% | 100.0% |
| ML only | 38 | 65.8% | 78.9% | 0.587 | 13 | 13 | 68% | 100.0% |
| hybrid | 38 | 94.7% | 97.4% | 0.945 | 2 | 2 | 32% | 100.0% |

Hybrid confusion matrix:

| true \ pred | K1 | K2 | K3 | K4 | K5 | K6 |
|---|---|---|---|---|---|---|
| **K1** | 2 | 0 | 1 | 0 | 0 | 0 |
| **K2** | 0 | 10 | 1 | 0 | 0 | 0 |
| **K3** | 0 | 0 | 11 | 0 | 0 | 0 |
| **K4** | 0 | 0 | 0 | 2 | 0 | 0 |
| **K5** | 0 | 0 | 0 | 0 | 8 | 0 |
| **K6** | 0 | 0 | 0 | 0 | 0 | 3 |


_Note: labels in the seed/hold-out files were written by the project author. Use `--test` with questions labelled by your own staff for a fair measurement._
## 3. Blind set (31 new questions on OS/DBMS/networks, written AFTER the rules were frozen)

| system | n | exact acc | within ±1 | macro-F1 | wrong | wrong but flagged | flagged % | acc on unflagged |
|---|---|---|---|---|---|---|---|---|
| rules only | 31 | 96.8% | 100.0% | 0.974 | 1 | 0 | 0% | 96.8% |
| ML only | 31 | 96.8% | 100.0% | 0.974 | 1 | 1 | 23% | 100.0% |
| hybrid | 31 | 96.8% | 100.0% | 0.974 | 1 | 0 | 3% | 96.7% |

Hybrid confusion matrix:

| true \ pred | K1 | K2 | K3 | K4 | K5 | K6 |
|---|---|---|---|---|---|---|
| **K1** | 5 | 0 | 0 | 0 | 0 | 0 |
| **K2** | 0 | 7 | 0 | 0 | 0 | 0 |
| **K3** | 0 | 1 | 5 | 0 | 0 | 0 |
| **K4** | 0 | 0 | 0 | 4 | 0 | 0 |
| **K5** | 0 | 0 | 0 | 0 | 5 | 0 |
| **K6** | 0 | 0 | 0 | 0 | 0 | 4 |


_Note: labels in the seed/hold-out files were written by the project author. Use `--test` with questions labelled by your own staff for a fair measurement._