# v1.1 candidate QA — 2026-10-02

Status: **software candidate prepared; final physical acceptance pending**.

Latest product unit: SIMPLE default (one-index rotation / open-palm navigation /
two-open-palm scale), independent of optional PINCH calibration. **1332 full tests
passed** after the latest unit; 18 new practical-controls regressions. Ten refreshed
synthetic 1600x900 screenshots use the actual renderer; footer text overlap found
visually was corrected. No Core change was required. Prior package/test counts
below describe the preceding candidate, not the current source identity.

The calibration-only run `stem-v11-20261002-175620-990648` closed cleanly after
2108 frames: 1535 VALID, 2108 exact legacy parity checks, zero diagnostic,
observation/cleanup errors or recorded safety violations. Calibration succeeded
at frame 1280 and armed at 1290, then reference invalidated at frame 1333 when
projected palm-shape delta 0.20765356 exceeded 0.20 (window still focused; width
ratio 1.0055214). No stable intentional PINCH or marked attempt counts were
recorded. The operator confirmed READY/RELEASED only. This is PARTIAL calibration
evidence, not failure/success evidence for the new SIMPLE mode.

Current SIMPLE physical usability/shutdown/restart validation: **NOT RUN**.

Current source review snapshot: `runs/distribution/DIP-Touchless-STEM-v1.1-simple-final-review.zip`.
The complete application is open for the next physical smoke; no intended-action
counts, false-activation rate or two-hand physical reliability are established yet.
Current base revision is `3a2fa40` on `feat/v1.1-full-hand`; the continuation
is deliberately unstaged/uncommitted. Current source/profile hashes are written
to each application manifest and source snapshot; HEAD alone is not the candidate
implementation identity. No release was published/tagged.

## Executed automatic checks

- Final focused full-hand/package/shell/presentation/architecture tests: **844 passed**.
- Full `pytest -q`: **1314 passed** (150 added tests after the supplied A5.6 foundation).
- The extracted preflight source package: **1314 passed** using the same existing
  interpreter/dependencies, with extracted `src/` and application paths. This is
  package-path regression, not a new-machine/fresh-install claim.
- Compileall for `extensions/stem3d`, `application_adapters`, `developer_tools`: exit 0.
- `git diff --check`: passed; frozen-path diff is empty, immutable tag commits match.
- Dependency `pip check`: no broken requirements. Local model SHA-256 matches the
  documented `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.
- CLI `--help` and PowerShell launcher `--help` from another directory: exit 0.
- Source ZIP CRC/all recorded file hashes passed. Extracted application `--help`
  succeeded; external model was correctly excluded. Final review artifact:
  `runs/distribution/DIP-Touchless-STEM-v1.1-review-final.zip`.
- Ten labeled synthetic 1600x900 captures use the actual scene/OpenGL renderer;
  Settings/Analysis/Help were visually inspected and clipping corrected. They
  are in `release/v1.1/screenshots/`, separate from frozen evidence.
- Actual-landmark synthetic integration: five repeat close/hold/open cycles
  through A2/A3/A4, explicit reference builder, intent tracker, mapper; five stable
  enters, scale output, exact legacy parity, zero recorded safety violations.
- Camera/model/logger fault, focus loss during analysis, duplicate callback,
  source open/read failure, cleanup error, resource closure and restart tests pass.
- Existing architecture tests were not weakened. The independent SDK adapter
  was relocated outside Extension scene/UI modules after the boundary test failed.

## Performance scope

50 CPU UI builds per view at 1600x900, synthetic input, no camera/model/Core:

| View | Before total | After total |
| --- | --- | --- |
| Workspace | 0.383568 s | 0.143249 s |
| Analysis | 0.416879 s | 0.170688 s |
| Evidence | 0.360560 s | 0.123138 s |

The measured dominant path was broadcast background fill; the new application
uses one immutable current-size template and independent output copies. Feedback
layout cleanup accompanied the comparison. These are recorded local UI totals,
not an isolated causal estimate, webcam FPS/latency claim or research result.

## Integrity and physical status

- `g7-final^{commit}` unchanged: `f454c6b8325c85199c0122c0e822fe8e76c1526c`.
- `dip-touchless-stem-v1.0^{commit}` unchanged: `2bda0d35a6178c9161a8dcb5bf1de5fbe003adb2`.
- `src/`, `FINAL_REPORT.md`, `submission/evidence/`, `experiments/final/` unchanged.
- Legacy GestureEngine, public InteractionState, scene/router semantics and
  research parameters unchanged. New sensitivity/calibration are Extension-only.
- G9 paths absent; deferred stash retained. No staging/commit/push/tag performed.
- Final v1.1 physical command acceptance: **NOT RUN / awaiting operator**.
  The earlier `g8-demo-20261002-163827` OBSERVE run closed cleanly after 911 frames,
  but had no completed calibration/protocol confirmation and is not a passed
  intentional-interaction gate. Frozen v1.0 physical results are historical.

Blocker to validated release/default promotion: complete
[physical acceptance](PHYSICAL_ACCEPTANCE.md), record actual counts/usability,
then fix observed defects with focused/full regression. New command modes and
two-hand capability remain opt-in experiments. No commercial, multi-user or
universal accuracy/robustness claim is made.
