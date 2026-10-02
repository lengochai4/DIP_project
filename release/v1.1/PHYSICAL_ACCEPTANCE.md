# Complete application practical smoke - pending

Decision: do the three simple controls work comfortably in this complete app?
Run `python -m extensions.stem3d.app`. SIMPLE, mirrored preview and two-hand
capability are enabled by default. Enter starts. No K/PINCH calibration is needed.
Use normal lighting, whole palms visible, and keep the window focused.

1. Extend only the index; move left/right/up/down three times. Record intended
   rotations that worked/missed and any unintended rotation.
2. Open one palm and hold briefly. Control Space opens. Move the palm cursor;
   hover over Molecule, Orbital, Analysis, Evidence and Workspace for 1.2 seconds
   to choose. Selection has a progress bar; a stationary hand cannot select at
   menu entry. Move off a selected button before selecting it again. Choose Close.
3. Open both palms, hold briefly, then move apart/together three times to scale.
   Remove one hand; no old pair scale may survive. Pair controls cannot select
   or manipulate the scene while Control Space is open.
4. Move hands out/in, briefly occlude, then resume. Returned gestures need fresh
   dwell/anchors; no carried command is allowed. R resets. Try Settings, Help,
   sensitivity/mirror, keyboard and right-drag/wheel fallback.
5. Q closes. Restart once, choose Legacy in Settings and verify old index rotation
   and pinch scale. Q closes again.

Report attempts/successes per action, false/duplicate activations, tracking loss,
stuck output, usability difficulty, shutdown/restart and skipped items. Local
run IDs, source/profile hashes and selected command/hover diagnostics live under
`runs/application-v1.1/`; these are never frozen G7 evidence.

This is a functional smoke, not a measured false-activation rate or broad
reliability claim. Later engineering targets remain >=90% intended success,
>=95% release/rearm, <=0.1 false activation per valid tracked minute, zero stuck
or safety violations and exact legacy shadow parity. Interpret rates only with
confirmed labels and sufficient exposure: 20 intended cycles and at least 10
valid tracked minutes of non-intent activity per tested profile/user. Synthetic
tests and this short smoke do not establish those targets. No skin-contact
classification test is required. Do not tune parameters during collection.

Experimental PINCH remains an optional lab mode; its physical gate has not passed.
It does not gate SIMPLE navigation, rotation or two-hand scale. Its projected-palm
reference can require recalibration; it is not the default product path.
