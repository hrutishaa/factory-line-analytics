# Shift Handoff — Line Health Report

Source: AI4I 2020, 10,000 cycles, 20 shifts of 500 cycles. Baseline failure rate p̄ = 3.39%.

## Status board

| Shift | Status | Failure rate | Yield | OEE (modelled) |
|---|---|---|---|---|
| 1 | GREEN | 3.2% | 96.8% | 44.4% |
| 2 | GREEN | 1.4% | 98.6% | 58.3% |
| 3 | GREEN | 3.8% | 96.2% | 40.2% |
| 4 | GREEN | 2.0% | 98.0% | 54.1% |
| 5 | GREEN | 2.4% | 97.6% | 50.7% |
| 6 | GREEN | 2.0% | 98.0% | 57.2% |
| 7 | GREEN | 1.8% | 98.2% | 55.6% |
| 8 | GREEN | 3.6% | 96.4% | 44.0% |
| 9 | RED | 15.2% | 84.8% | 20.4% |
| 10 | RED | 11.6% | 88.4% | 26.3% |
| 11 | GREEN | 2.4% | 97.6% | 48.0% |
| 12 | GREEN | 1.6% | 98.4% | 55.8% |
| 13 | GREEN | 2.6% | 97.4% | 51.0% |
| 14 | GREEN | 2.0% | 98.0% | 51.9% |
| 15 | GREEN | 1.2% | 98.8% | 59.3% |
| 16 | GREEN | 3.2% | 96.8% | 46.5% |
| 17 | GREEN | 2.0% | 98.0% | 54.9% |
| 18 | AMBER | 1.4% | 98.6% | 59.0% |
| 19 | AMBER | 1.8% | 98.2% | 56.2% |
| 20 | AMBER | 2.6% | 97.4% | 49.3% |

## Open alerts

### [RED] Shift 9 — WE1: point beyond 3σ
- Failure rate 15.2% vs UCL 5.8%; yield 84.8%; OEE 20.4%
- Failure modes: heat dissipation 61 (10.61× avg shift), power 10 (2.11× avg shift), overstrain 6 (1.22× avg shift), tool wear 4 (1.74× avg shift)
- By product type: H 4, L 55, M 22
- Next action: inspect **heat dissipation** failures first (largest contributor).

### [RED] Shift 10 — WE1: point beyond 3σ, WE2: 2 of 3 beyond +2σ
- Failure rate 11.6% vs UCL 5.8%; yield 88.4%; OEE 26.3%
- Failure modes: heat dissipation 47 (8.17× avg shift), overstrain 6 (1.22× avg shift), power 5 (1.05× avg shift), tool wear 2 (0.87× avg shift)
- By product type: H 3, L 43, M 14
- Next action: inspect **heat dissipation** failures first (largest contributor).

### [AMBER] Shift 18 — WE4: 8 in a row below center (improvement)
- Failure rate 1.4% vs UCL 5.8%; yield 98.6%; OEE 59.0%
- Failure modes: overstrain 3 (0.61× avg shift), tool wear 3 (1.3× avg shift), power 2 (0.42× avg shift)
- By product type: L 3, M 5
- Next action: sustained run below baseline — confirm what changed and whether to re-baseline limits.

### [AMBER] Shift 19 — WE4: 8 in a row below center (improvement)
- Failure rate 1.8% vs UCL 5.8%; yield 98.2%; OEE 56.2%
- Failure modes: overstrain 5 (1.02× avg shift), power 2 (0.42× avg shift), tool wear 2 (0.87× avg shift)
- By product type: L 8, M 1
- Next action: sustained run below baseline — confirm what changed and whether to re-baseline limits.

### [AMBER] Shift 20 — WE4: 8 in a row below center (improvement)
- Failure rate 2.6% vs UCL 5.8%; yield 97.4%; OEE 49.3%
- Failure modes: overstrain 9 (1.84× avg shift), power 3 (0.63× avg shift), tool wear 2 (0.87× avg shift)
- By product type: L 14
- Next action: sustained run below baseline — confirm what changed and whether to re-baseline limits.

