"""DwellTracker: frame-level hover timer for touchless dwell-activation.

Tracks one target at a time.  A different target_id resets the timer.
Returns a DwellEvent when the dwell threshold is reached, and again on
every tick while the target is held (HOLD), and once on EXIT.

No Core imports; product-layer utility only.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DwellEvent:
    target_id: object  # any hashable identifier (str, int, tuple …)
    state: str         # "ENTER" | "HOLD" | "EXIT"
    elapsed_s: float   # how long the pointer has been on this target


class DwellTracker:
    """Single-target dwell timer.

    Parameters
    ----------
    threshold_s : float
        Seconds of continuous hover before ENTER fires.
    hysteresis_s : float
        Extra seconds beyond threshold before HOLD events fire (ignored
        for the initial ENTER).
    """

    def __init__(self, threshold_s: float = 1.1, hysteresis_s: float = 0.0):
        if threshold_s <= 0:
            raise ValueError("threshold_s must be positive")
        self._threshold = threshold_s
        self._hysteresis = max(0.0, hysteresis_s)
        self._target: object = None
        self._elapsed: float = 0.0
        self._fired: bool = False      # ENTER has been emitted
        self._exited: bool = False     # EXIT has been emitted for this target

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def active_target(self) -> object:
        """The target currently being tracked (or None)."""
        return self._target

    @property
    def elapsed(self) -> float:
        """Seconds spent on the current target."""
        return self._elapsed

    @property
    def fraction(self) -> float:
        """Progress toward threshold in [0, 1]."""
        if self._threshold <= 0:
            return 1.0
        return min(1.0, self._elapsed / self._threshold)

    def reset(self) -> None:
        """Discard current tracking state (e.g. on context change)."""
        self._target = None
        self._elapsed = 0.0
        self._fired = False
        self._exited = False

    def update(
        self,
        target_id: Optional[object],
        dt: float,
        *,
        inside: bool = True,
    ) -> Optional[DwellEvent]:
        """Advance the tracker by one frame.

        Parameters
        ----------
        target_id : hashable or None
            Identifier of the region the pointer is currently inside, or
            None if no region is hovered.
        dt : float
            Elapsed time in seconds since the last call.
        inside : bool
            Whether the pointer is inside *target_id*'s hit region.  Pass
            False when the pointer is above the target area but outside the
            specific sub-region.

        Returns
        -------
        DwellEvent or None
            ENTER  – first time threshold is reached.
            HOLD   – every tick while still held past threshold.
            EXIT   – first tick after the pointer leaves.
            None   – still accumulating or already exited.
        """
        if not (0.0 <= dt <= 5.0):
            dt = min(5.0, max(0.0, dt)) if dt == dt else 0.0

        no_target = target_id is None or not inside

        if no_target:
            if self._target is not None and not self._exited:
                # Pointer left without reaching threshold or after firing.
                self._exited = True
                ev = DwellEvent(self._target, "EXIT", self._elapsed)
                self._target = None
                self._elapsed = 0.0
                self._fired = False
                return ev
            # Already exited or was never started.
            self._target = None
            self._elapsed = 0.0
            self._fired = False
            self._exited = False
            return None

        # Pointer is on a target.
        if self._target != target_id:
            # New target: reset without firing EXIT (no previous target).
            self._target = target_id
            self._elapsed = 0.0
            self._fired = False
            self._exited = False

        self._elapsed += dt

        if self._elapsed >= self._threshold:
            if not self._fired:
                self._fired = True
                return DwellEvent(target_id, "ENTER", self._elapsed)
            # Hysteresis guard to avoid flooding HOLD events.
            # Always emit on the frame that fires, then let caller decide.
            return DwellEvent(target_id, "HOLD", self._elapsed)

        return None
