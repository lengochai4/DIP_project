# R3 final application physical smoke — 2026-10-01

**R3: PASS with documented usability limitations.** This was a real webcam run
with the user performing the physical hand actions. It was not a synthetic
replacement. Functional readiness: **READY FOR RELEASE with the limitations
below**, subject to the separate R4 package/release review. R4 has not started.

## Exact identity

Command from the repository root (executed using the existing `.venv` interpreter):

```powershell
python -m extensions.stem3d.live_demo
```

Application revision: `21ab8cddf037c9f21f33ca6f2ec8fb237eaebb72`.
Resolved config hash: `ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08`.
Filter: Raw/F0. Provider: MediaPipe; model checksum:
`fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.

| Run | Frames | Console shutdown |
| --- | ---: | --- |
| `g8-demo-20261001-184630` | 1,197 | `Live demo closed cleanly.` |
| `g8-demo-20261001-184818` (restart once) | 2,666 | `Live demo closed cleanly.` |

Local logs remain ignored under `runs/<run_id>/` (`metadata.json`,
`resolved_config.yaml`, `frames.csv`, `landmarks.csv`, `events.csv`). They are
release-smoke records, not replacement G7 research data. No new webcam images
were saved into the screenshot or frozen-evidence package.

## Checklist and source of confirmation

The user confirmed all twelve requested items worked, with the orientation and
sensitivity complaints below. UI observation was intermittent; the table
distinguishes user confirmation from directly observed/logged results.

| Item | Result | Basis |
| --- | --- | --- |
| Startup and camera preview | PASS | Real preview observed; user confirmed |
| Hand detection / landmarks | PASS | Hand/ROI/landmarks observed in Analysis; real landmark logs |
| Index-motion rotation | PASS | User confirmed visible rotation; non-zero commands logged |
| Pinch scaling | PASS | User confirmed visible scaling; non-zero commands logged |
| Control Space open/close | PASS | Open panel observed; both actions user-confirmed |
| Pointer hover + pinch selection | PASS | Hover highlight observed; pinch selection user-confirmed |
| All three scene switches | PASS | Coordinate/Molecule observed; complete switching user-confirmed |
| Workspace / Analysis / Evidence | PASS | Workspace/Analysis observed; all three user-confirmed |
| Tracking loss and reacquisition | PASS | User confirmed hand-out/in behavior; NO_HAND-to-VALID returns logged |
| Reset | PASS | User confirmed |
| Clean shutdown | PASS | User confirmed; both processes ended normally with clean-close output |
| Restart once | PASS | Second real run launched, preview/landmarks observed and clean shutdown logged |

## Practical limitations and interpretation

User feedback: "ok hết nhưng mà ảnh bị lật và độ nhạy thấp(nên thêm setting tăng
độ nhạy, nhưng để sau), check kỹ lại".

- **Preview orientation:** the user perceived the image as flipped. Current
  preview and pointer mapping explicitly use an unmirrored, full-frame-normalized
  orientation (`mirror_x=False`, `mirror_y=False`). Observed landmarks aligned
  with the hand. This inspection found no newly added flip or established
  coordinate mismatch; it does not determine every camera/driver orientation
  condition. The reported orientation discomfort remains documented.
- **Low sensitivity:** interaction worked but felt insufficiently responsive
  to the user. No threshold, gain, deadzone or gesture semantics were changed.
  A user-adjustable sensitivity setting is deferred to separately approved
  post-v1.0 interaction work, as requested by the user.
- **Tracking/false positives:** NO_HAND and returns to VALID occurred. The first
  run logged 175 NO_HAND / 1,022 VALID frames and four NO_HAND-to-VALID transitions;
  restart logged 631 NO_HAND / 2,035 VALID frames and twelve such transitions.
  Hand withdrawal was part of the test, so these counts do not measure tracking
  reliability or distinguish intentional withdrawal from accidental loss.
  No additional false positives were reported in the user's checklist reply;
  intermittent observation cannot establish their absence. Historical G7
  face/background false positives remain a known limitation.
- **Command evidence:** first run had 684 non-zero rotation frames and 104
  non-zero scale frames; restart had 1,343 and 384 respectively. These recorded
  counts confirm commands, not precision, responsiveness or user-study quality.
- MediaPipe printed feedback-tensor and NORM_RECT/IMAGE_DIMENSIONS warnings.
  Both runs continued and ended cleanly; these warnings were not suppressed.
- Computer Use briefly failed to activate the first window and was later
  stopped by the user's physical Escape key. Remaining manual results were
  supplied by the user; the second process subsequently confirmed clean exit.

## Verification and scope

- `.venv\Scripts\python.exe -m pytest -q`: **555 passed**.
- `.venv\Scripts\python.exe -m compileall extensions/stem3d`: passed.
- `git diff --check`: passed.
- 23 frozen file SHA-256 hashes, G7 tag and existing G9 stash checked unchanged;
  Core/application/config/tests/analysis/research diffs empty before status edits.

Changes are limited to release/status documentation. Interaction behavior,
sensitivity, Core, UI architecture, experiments and G7 report/evidence are
unchanged. R2 images remain honestly labelled synthetic. No stage, commit,
push, tag, R4 work or implementation of the post-v1.0 backlog was performed.
