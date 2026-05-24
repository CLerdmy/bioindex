## benchmark_full.py
*COMPRESSED - Gamma*
```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2] PASSED
PM2    | results=9946   | avg=0.006212 sec
VALIDATION [COMPRESSED INDEX :: PVS1] PASSED
PVS1   | results=2160   | avg=0.001601 sec
VALIDATION [COMPRESSED INDEX :: PP3] PASSED
PP3    | results=369    | avg=0.000471 sec
VALIDATION [COMPRESSED INDEX :: BS1] PASSED
BS1    | results=698    | avg=0.000718 sec
VALIDATION [COMPRESSED INDEX :: PS1] PASSED
PS1    | results=19     | avg=0.000024 sec

TOTAL AVG: 0.001805 sec

=== CGAMMA INDEX ===

VALIDATION [CGAMMA INDEX :: PM2] PASSED
PM2    | results=9946   | avg=0.000654 sec
VALIDATION [CGAMMA INDEX :: PVS1] PASSED
PVS1   | results=2160   | avg=0.000209 sec
VALIDATION [CGAMMA INDEX :: PP3] PASSED
PP3    | results=369    | avg=0.000108 sec
VALIDATION [CGAMMA INDEX :: BS1] PASSED
BS1    | results=698    | avg=0.000103 sec
VALIDATION [CGAMMA INDEX :: PS1] PASSED
PS1    | results=19     | avg=0.000063 sec

TOTAL AVG: 0.000227 sec
```

## benchmark_and_queries.py
*COMPRESSED - Gamma*
```text
=== COMPRESSED INDEX ===

VALIDATION [COMPRESSED INDEX :: PM2 AND PVS1] PASSED
PM2 AND PVS1   | results=1898   | avg=0.007633 sec
VALIDATION [COMPRESSED INDEX :: PM2 AND PP3] PASSED
PM2 AND PP3    | results=342    | avg=0.006410 sec
VALIDATION [COMPRESSED INDEX :: BS1 AND PP3] PASSED
BS1 AND PP3    | results=10     | avg=0.000983 sec

TOTAL AVG: 0.005009 sec

=== CGAMMA INDEX ===

VALIDATION [CGAMMA INDEX :: PM2 AND PVS1] PASSED
PM2 AND PVS1   | results=1898   | avg=0.000853 sec
VALIDATION [CGAMMA INDEX :: PM2 AND PP3] PASSED
PM2 AND PP3    | results=342    | avg=0.000657 sec
VALIDATION [CGAMMA INDEX :: BS1 AND PP3] PASSED
BS1 AND PP3    | results=10     | avg=0.000090 sec

TOTAL AVG: 0.000533 sec
```

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

=== GAMMA COMPRESSED INDEX ===WQ    
Size: 21.62 KB
Rules: 25
Classification groups: 3
Total postings: 40290

=== CGAMMA INDEX ===
Size: 22.48 KB
Rules: 25
Classification groups: 3
Total postings: 40290

=== COMPRESSION STATS ===
Delta compression reduction: 32.71%
Gamma compression reduction: 81.76%
CGAMMA compression reduction: 81.04%
```