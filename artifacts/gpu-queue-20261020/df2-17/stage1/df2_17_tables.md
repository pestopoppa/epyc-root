# DF2-17 stage1: per-prompt tables (baseline = off_A)


## dflash_n4 (kind dflash, verify width 5): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 34 | 0.035476744174957275 | True | near-tie | <0.1 | 1600/1600 | 1688 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 1603 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 1222 | 0.04019725322723389 | True | near-tie | <0.1 | 1600/1600 | 1567 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 353 | 0.045131683349609375 | True | near-tie | <0.1 | 1600/1600 | 1771 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 1176 | 0.024595260620117188 | True | near-tie | <0.1 | 1600/1600 | 1464 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 247 | 0.10917651653289795 | False | degenerative(non-near-tie) | <0.5 | 1600/1600 | 1486 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 182 | 0.043048858642578125 | True | near-tie | <0.1 | 1600/1600 | 1525 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 882 | 0.06943327188491821 | True | near-tie | <0.1 | 1391/1600 | 1459 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 451 | 0.016910433769226074 | False | degenerative(non-near-tie) | <0.1 | 1600/1600 | 1638 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 479 | 0.030019700527191162 | True | near-tie | <0.1 | 1600/1600 | 1409 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 238 | 0.01956188678741455 | True | near-tie | <0.1 | 1600/1600 | 1656 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 212 | 0.07887840270996094 | True | near-tie | <0.1 | 1600/1600 | 1584 | True |

## dflash_n7 (kind dflash, verify width 8): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 34 | 0.035476744174957275 | True | near-tie | <0.1 | 1600/1600 | 2356 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 2158 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 1222 | 0.04019725322723389 | True | near-tie | <0.1 | 1600/1600 | 2046 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 353 | 0.045131683349609375 | True | near-tie | <0.1 | 1600/1600 | 2642 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 1176 | 0.024595260620117188 | True | near-tie | <0.1 | 1600/1600 | 1812 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 247 | 0.10917651653289795 | False | degenerative(non-near-tie) | <0.5 | 1600/1600 | 1904 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 182 | 0.043048858642578125 | True | near-tie | <0.1 | 1600/1600 | 1942 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 882 | 0.06943327188491821 | True | near-tie | <0.1 | 1391/1600 | 1792 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 451 | 0.016910433769226074 | False | degenerative(non-near-tie) | <0.1 | 1600/1600 | 2230 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 479 | 0.030019700527191162 | True | near-tie | <0.1 | 1600/1600 | 1716 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 238 | 0.01956188678741455 | True | near-tie | <0.1 | 1600/1600 | 2230 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 212 | 0.07887840270996094 | True | near-tie | <0.1 | 1600/1600 | 2155 | True |

## mtp_n1 (kind mtp, verify width 2): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 239 | 0.18194007873535156 | True | near-tie | <0.5 | 1600/1600 | 843 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 828 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 480 | 0.09716796875 | True | near-tie | <0.1 | 1600/1600 | 834 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 268 | 0.024084091186523438 | True | near-tie | <0.1 | 1600/1600 | 867 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 183 | 0.025007247924804688 | True | near-tie | <0.1 | 1600/1600 | 823 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 247 | 0.10917651653289795 | False | degenerative(non-near-tie) | <0.5 | 1600/1600 | 825 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 960 | 0.1198195219039917 | True | near-tie | <0.5 | 1600/1600 | 822 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 397 | 0.0057621002197265625 | True | near-tie | <0.1 | 1391/1600 | 820 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 135 | 0.015899658203125 | True | near-tie | <0.1 | 1600/1600 | 833 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 479 | 0.030019700527191162 | True | near-tie | <0.1 | 1600/1600 | 810 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 238 | 0.01956188678741455 | True | near-tie | <0.1 | 1600/1600 | 836 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 248 | 0.10750389099121094 | True | near-tie | <0.5 | 1600/1600 | 829 | True |

## mtp_n2 (kind mtp, verify width 3): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 64 | 0.04094517230987549 | True | near-tie | <0.1 | 1600/1600 | 1261 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 1164 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 1222 | 0.04019725322723389 | True | near-tie | <0.1 | 1600/1600 | 1172 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 353 | 0.045131683349609375 | True | near-tie | <0.1 | 1600/1600 | 1318 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 183 | 0.025007247924804688 | True | near-tie | <0.1 | 1600/1600 | 1156 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 36 | 0.02966684103012085 | True | near-tie | <0.1 | 1600/1600 | 1197 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 182 | 0.043048858642578125 | True | near-tie | <0.1 | 1600/1600 | 1169 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 397 | 0.0057621002197265625 | True | near-tie | <0.1 | 1391/1600 | 1118 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 56 | 0.07489967346191406 | True | near-tie | <0.1 | 1600/1600 | 1202 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 36 | 0.039604127407073975 | True | near-tie | <0.1 | 1600/1600 | 1113 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 181 | 0.015420854091644287 | True | near-tie | <0.1 | 1600/1600 | 1207 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 250 | 0.0005492568016052246 | True | near-tie | <0.1 | 1600/1600 | 1176 | True |

## mtp_n3 (kind mtp, verify width 4): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 64 | 0.04094517230987549 | True | near-tie | <0.1 | 1600/1600 | 1572 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 1407 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 1222 | 0.04019725322723389 | True | near-tie | <0.1 | 1600/1600 | 1416 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 353 | 0.045131683349609375 | True | near-tie | <0.1 | 1600/1600 | 1666 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 183 | 0.025007247924804688 | True | near-tie | <0.1 | 1600/1600 | 1374 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 36 | 0.02966684103012085 | True | near-tie | <0.1 | 1600/1600 | 1496 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 182 | 0.043048858642578125 | True | near-tie | <0.1 | 1600/1600 | 1434 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 397 | 0.0057621002197265625 | True | near-tie | <0.1 | 1391/1600 | 1315 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 56 | 0.07489967346191406 | True | near-tie | <0.1 | 1600/1600 | 1445 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 36 | 0.039604127407073975 | True | near-tie | <0.1 | 1600/1600 | 1287 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 181 | 0.015420854091644287 | True | near-tie | <0.1 | 1600/1600 | 1449 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 250 | 0.0005492568016052246 | True | near-tie | <0.1 | 1600/1600 | 1400 | True |

## mtp_n5 (kind mtp, verify width 6): PASS 0/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | FAIL | 34 | 0.035476744174957275 | True | near-tie | <0.1 | 1600/1600 | 2019 | True |
| olympiadbench_hard_algebra_1659 | FAIL | 128 | 0.012451171875 | True | near-tie | <0.1 | 1600/1600 | 1985 | True |
| olympiadbench_hard_combinatorics_2230 | FAIL | 1222 | 0.04019725322723389 | True | near-tie | <0.1 | 1600/1600 | 1884 | True |
| olympiadbench_hard_algebra_2171 | FAIL | 353 | 0.045131683349609375 | True | near-tie | <0.1 | 1600/1600 | 2373 | True |
| olympiadbench_hard_combinatorics_2127 | FAIL | 1176 | 0.024595260620117188 | True | near-tie | <0.1 | 1600/1600 | 1730 | True |
| olympiadbench_hard_algebra_1938 | FAIL | 247 | 0.10917651653289795 | False | degenerative(non-near-tie) | <0.5 | 1600/1600 | 1829 | True |
| olympiadbench_hard_number_theory_1869 | FAIL | 182 | 0.043048858642578125 | True | near-tie | <0.1 | 1600/1600 | 1959 | True |
| olympiadbench_hard_algebra_2574 | FAIL | 882 | 0.06943327188491821 | True | near-tie | <0.1 | 1391/1600 | 1670 | False |
| olympiadbench_hard_combinatorics_1818 | FAIL | 451 | 0.016910433769226074 | False | degenerative(non-near-tie) | <0.1 | 1600/1600 | 1910 | True |
| olympiadbench_hard_number_theory_2415 | FAIL | 479 | 0.030019700527191162 | True | near-tie | <0.1 | 1600/1600 | 1605 | True |
| olympiadbench_hard_combinatorics_1664 | FAIL | 238 | 0.01956188678741455 | True | near-tie | <0.1 | 1600/1600 | 2050 | True |
| olympiadbench_hard_combinatorics_1662 | FAIL | 212 | 0.07887840270996094 | True | near-tie | <0.1 | 1600/1600 | 1807 | True |

## off_B (kind none, verify width 1): PASS 12/12, drafted-all=None

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_algebra_1659 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_combinatorics_2230 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_algebra_2171 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_combinatorics_2127 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_algebra_1938 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_number_theory_1869 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_algebra_2574 | PASS | None |  |  |  |  | 1391/1391 | None | False |
| olympiadbench_hard_combinatorics_1818 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_number_theory_2415 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_combinatorics_1664 | PASS | None |  |  |  |  | 1600/1600 | None | True |
| olympiadbench_hard_combinatorics_1662 | PASS | None |  |  |  |  | 1600/1600 | None | True |

## serial_df7 (kind dflash, verify width 8): PASS 12/12, drafted-all=True

| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |
|---|---|---|---|---|---|---|---|---|---|
| olympiadbench_hard_combinatorics_1882 | PASS | None |  |  |  |  | 1600/1600 | 2539 | True |
| olympiadbench_hard_algebra_1659 | PASS | None |  |  |  |  | 1600/1600 | 2056 | True |
| olympiadbench_hard_combinatorics_2230 | PASS | None |  |  |  |  | 1600/1600 | 2122 | True |
| olympiadbench_hard_algebra_2171 | PASS | None |  |  |  |  | 1600/1600 | 2559 | True |
| olympiadbench_hard_combinatorics_2127 | PASS | None |  |  |  |  | 1600/1600 | 1809 | True |
| olympiadbench_hard_algebra_1938 | PASS | None |  |  |  |  | 1600/1600 | 1878 | True |
| olympiadbench_hard_number_theory_1869 | PASS | None |  |  |  |  | 1600/1600 | 1769 | True |
| olympiadbench_hard_algebra_2574 | PASS | None |  |  |  |  | 1391/1391 | 1526 | False |
| olympiadbench_hard_combinatorics_1818 | PASS | None |  |  |  |  | 1600/1600 | 2277 | True |
| olympiadbench_hard_number_theory_2415 | PASS | None |  |  |  |  | 1600/1600 | 1691 | True |
| olympiadbench_hard_combinatorics_1664 | PASS | None |  |  |  |  | 1600/1600 | 2230 | True |
| olympiadbench_hard_combinatorics_1662 | PASS | None |  |  |  |  | 1600/1600 | 2110 | True |
