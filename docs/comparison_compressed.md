## check_index_files.py
```text
=== INVERTED INDEX ===
Size: 118.58 KB
Rules: 25
Classification groups: 3
Total postings: 40290

=== DELTA COMPRESSED INDEX ===
Size: 79.79 KB
Rules: 25
Classification groups: 3
Total postings: 40290

=== GAMMA COMPRESSED INDEX ===
Size: 21.62 KB
Rules: 25
Classification groups: 3
Total postings: 40290

=== COMPRESSION STATS ===
Delta compression reduction: 32.71%
Gamma compression reduction: 81.76%
```


## benchmark_full.py

*Delta*:

```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2] PASSED
PM2    | results=9946   | avg=0.000800 sec
VALIDATION [COMPRESSED INDEX :: PVS1] PASSED
PVS1   | results=2160   | avg=0.000173 sec
VALIDATION [COMPRESSED INDEX :: PP3] PASSED
PP3    | results=369    | avg=0.000036 sec
VALIDATION [COMPRESSED INDEX :: BS1] PASSED
BS1    | results=698    | avg=0.000063 sec
VALIDATION [COMPRESSED INDEX :: PS1] PASSED
PS1    | results=19     | avg=0.000003 sec

TOTAL AVG: 0.000215 sec
```

*Gamma*:

```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2] PASSED
PM2    | results=9946   | avg=0.006409 sec
VALIDATION [COMPRESSED INDEX :: PVS1] PASSED
PVS1   | results=2160   | avg=0.001823 sec
VALIDATION [COMPRESSED INDEX :: PP3] PASSED
PP3    | results=369    | avg=0.000380 sec
VALIDATION [COMPRESSED INDEX :: BS1] PASSED
BS1    | results=698    | avg=0.000743 sec
VALIDATION [COMPRESSED INDEX :: PS1] PASSED
PS1    | results=19     | avg=0.000030 sec

TOTAL AVG: 0.001877 sec
```

## benchmark_and_queries.py

*Delta*:

```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2 AND PVS1] PASSED
PM2 AND PVS1   | results=1898   | avg=0.001295 sec
VALIDATION [COMPRESSED INDEX :: PM2 AND PP3] PASSED
PM2 AND PP3    | results=342    | avg=0.000880 sec
VALIDATION [COMPRESSED INDEX :: BS1 AND PP3] PASSED
BS1 AND PP3    | results=10     | avg=0.000122 sec

TOTAL AVG: 0.000766 sec
```

*Gamma*:

```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2 AND PVS1] PASSED
PM2 AND PVS1   | results=1898   | avg=0.007964 sec
VALIDATION [COMPRESSED INDEX :: PM2 AND PP3] PASSED
PM2 AND PP3    | results=342    | avg=0.006665 sec
VALIDATION [COMPRESSED INDEX :: BS1 AND PP3] PASSED
BS1 AND PP3    | results=10     | avg=0.001079 sec

TOTAL AVG: 0.005236 sec
```