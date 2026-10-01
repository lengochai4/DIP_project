# Final application walkthrough and screenshot checklist

Use [submission setup](README.md) first. Run from the repository root:

```powershell
python -m extensions.stem3d.live_demo
```

## Short application walkthrough

1. **Welcome → Workspace:** press S or Enter, allow initialization, then press D.
   Introduce the single-camera DIP pipeline and the separate STEM Extension.
   Show one hand, move the index finger to rotate and use thumb/index pinch
   distance to scale. R resets the active scene. Use the existing interaction;
   Space is only a welcome-start shortcut, not a grab clutch.
2. **Analysis:** press A. Explain the displayed image/ROI processing, tracking,
   illumination, CLAHE state, filter state and actual interaction output. Point
   out run/frame identity and Core compute timing. The live path is Raw/F0;
   the displayed compute time is not end-to-end latency or a benchmark.
3. **Evidence:** press E and use [ / ] or Previous/Next: Overview → A1 Static
   → A2 Dynamic → B Normal → B Low-light → RQ3 / Demo. Show the frozen A1 chart,
   explicitly describe A2 as unavailable, and explain that B's P1 did not
   activate CLAHE. Keep provenance and limitations visible. This is recorded
   G7 evidence, not measurements produced by today's webcam.
4. **STEM scenes:** press D, then 1 for Coordinate Geometry, 2 for Molecule,
   H/C for Water/Methane, and 3 for Orbital System. Briefly describe geometry,
   molecular shape and the educational orbit. Demonstrate reset once. P opens
   Control Space; release an existing pinch before pinching once to select.
   Keyboard selection is the fallback when tracking is unavailable.
5. **Shutdown:** Q / Escape or window close. Verify the process returns to the
   terminal and the webcam indicator turns off. Restart once if doing a physical
   smoke. Record any failure instead of changing thresholds during the walkthrough.

F1 / ? opens Help. Keep the application window focused for keyboard controls.
If camera/model/graphics initialization fails, show the reported component,
dismiss, correct the setup and retry. Do not describe a renderer-only synthetic
smoke as live tracking validation.

## Final screenshot checklist

Capture readable full-window images at the actual presentation resolution.
Use one coherent run where practical. Record source commit, resolution,
capture date, run/frame identity when present, and whether input was live or
synthetic. Label synthetic captures explicitly. Avoid private background details.
Save new presentation images separately (for example in a local
`runs/submission-screenshots/` folder); never overwrite `submission/evidence/`.
Curate a separate screenshot attachment at handoff, if required.

- [x] Welcome / ready screen and Help with current controls (synthetic).
- [x] Workspace with Coordinate Geometry, readable Live Vision and status (synthetic).
- [x] Analysis showing ROI/processing, tracking, filter, interaction output and run identity (fixtures).
- [x] Evidence Overview with available findings and limitations (synthetic viewer capture).
- [x] A1 Static chart and provenance (original G7 content in synthetic viewer capture).
- [x] A2 Dynamic with the unavailable finding readable (synthetic viewer capture).
- [x] B Normal and B Low-light with the inactive-CLAHE qualification readable (synthetic viewer capture).
- [x] RQ3 / Demo with historical provenance and known limitations (synthetic viewer capture).
- [x] Molecule: Water and Methane with their displayed geometry values (synthetic).
- [x] Orbital scene with educational context (synthetic).
- [x] Control Space open, without hiding the selected scene unnecessarily (synthetic).
- [x] No Hand state; describe how keyboard fallback remains usable (supplied synthetic state).
- [ ] Physical start → interaction → exit → restart result recorded separately,
      or explicitly marked NOT RUN.

R2 now has 15 curated 1600 × 900 synthetic application captures in
[`screenshots/`](screenshots/README.md), plus a contact sheet and provenance/hash
manifest. The image index explains fixture diagnostics and original G7 content.
These are presentation captures, not webcam/research evidence or R3 validation.
Earlier ignored QA renders remain separate; the final set above was rendered
specifically for R2 using unchanged application code.

## Honest closing statement

The final desktop application is complete; research results remain the limited frozen
G7 observations. Final physical webcam validation is NOT RUN in this preparation.
Tracking can be affected by lighting/background; A2 remains unavailable and B
does not isolate active CLAHE. G9 interaction work remains deferred. No claim
of production readiness or new quantitative performance is supported here.

## Remaining release work

R1 terminology/docs alignment and R2 synthetic final screenshots are complete.
R3 records the final application's startup, existing interaction, exit
and restart smoke (currently NOT RUN); R4 prepares the reviewed source package
and application release tag `dip-touchless-stem-v1.0`. Only R2 synthetic captures
were produced; R3 physical smoke and R4 release/tag were not started. Advanced interaction remains
after v1.0. This guide's existing filename and the technical `live_demo`/`demo`
module names are retained for compatibility.
