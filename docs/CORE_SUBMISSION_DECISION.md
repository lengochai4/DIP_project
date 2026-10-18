# Core decision — 2026-10-14

The current authorized task ends at the completed Core evidence and editable
Vietnamese report. UI development is postponed by the user.

## Decision and scope

Preserve Core algorithms, configurations and contracts from
`main` / `g7-final`, commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
The new round identifies no verified algorithm defect requiring an upgrade
before the course UI. Freeze this baseline for that step, retain Raw and
canonical Fixed 1-Euro, and document any future algorithm/contract change
before implementing it. Do not interpret this as enterprise certification.

Supplemental tooling commits are `20c363c4fc665909b7a22c63aad1b08892894342`,
`dcf886178fba5e8b5676b9f399bb1517bdc88dcc` and
`957efe5a08117402bccb684fe737a1925411ee42`.
They add collection/validation, fixed input attenuation and supported-hand
collection without changing Core. Main, the G7 release and the older UI
branch are retained.

## Executed evidence

- Fresh research environment: Python 3.12.14, versions locked in
  `experiments/round2/environment.lock.txt`; old Python 3.11 executable absent.
- Unmodified main passed 433 tests; completed tooling suite passed 454.
- Model SHA-256:
  `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.
- A1 supported-wrist supplement: three trials, 241 common frames each.
  F1/F2 decrease radial RMS versus Raw in trials 002/003; trial 001 increases
  slightly. F1/F2 are nearly equal. Initial moving static trials are retained.
- A2: three trials, 241 common frames each; F2 RMSE versus Raw is lower than
  F1 in each. This is neither ground-truth accuracy nor measured latency.
- B normal and simulated: P0=P1 valid rate 1.0 in all three trials of each
  condition, 241 analyzed frames each. P1 CLAHE is inactive on all 723 normal
  frames and active on all 723 simulated frames. No valid-rate improvement.
- Simulated inputs use preregistered gain 0.35, not physical low-light data.
  Two attempted physical low-light recordings remain condition-unverified.

The ROUND2 roots are `runs/round2/ROUND2-20261014-SUBMISSION`,
`runs/round2/ROUND2-20261014-SIM035` and
`runs/round2/ROUND2-20261014-HELD-STATIC`. Analysis indices, manifests,
source sidecars and run metadata provide complete local provenance.
Keep generated evidence local in accordance with AGENTS.md.

## Report and next step

The Word report explicitly reports unfavorable outcomes, different source
roles, simulated-condition limits and the separate G7 history. Personal,
school, adviser and project-code fields are left for the user to fill.

The next product task is a minimal 3D submission interface. Multi-finger or
two-hand rendering behavior is not evidence of changed Core research scope.
No UI completion or user-experience validation is claimed by this decision.
