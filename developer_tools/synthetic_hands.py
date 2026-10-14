"""Synthetic hand geometry for developer QA, never physical acceptance evidence."""

from dip_touchless.core import Landmark, CoordinateSpace


def landmarks(extended, center=0.5, slope=0.0, *, tip_depths=None):
    xy = [
        (0.5, 0.85),
        (0.44, 0.77),
        (0.34, 0.69),
        (0.25, 0.62),
        (0.17, 0.55),
        (0.4, 0.62),
        (0.4, 0.42),
        (0.4, 0.30),
        (0.4, 0.20),
        (0.5, 0.60),
        (0.5, 0.37),
        (0.5, 0.24),
        (0.5, 0.12),
        (0.6, 0.62),
        (0.6, 0.40),
        (0.6, 0.27),
        (0.6, 0.18),
        (0.7, 0.66),
        (0.7, 0.49),
        (0.7, 0.39),
        (0.7, 0.30),
    ]
    if 0 not in extended:
        xy[1:5] = [(0.44, 0.77), (0.4, 0.69), (0.46, 0.75), (0.48, 0.79)]
    for i, base in enumerate((5, 9, 13, 17), 1):
        if i not in extended:
            x, y = xy[base]
            xy[base + 1 : base + 4] = [
                (x + 0.02, y - 0.08),
                (x + 0.03, y + 0.04),
                (x + 0.03, y + 0.12),
            ]
    depths = {i: slope * (y - 0.6) for i, (_, y) in enumerate(xy)}
    if tip_depths is not None:
        for target, chain in zip(
            tip_depths,
            (
                (1, 2, 3, 4),
                (5, 6, 7, 8),
                (9, 10, 11, 12),
                (13, 14, 15, 16),
                (17, 18, 19, 20),
            ),
        ):
            start, end = xy[chain[0]][1], xy[chain[-1]][1]
            for i in chain:
                depths[i] = target * (xy[i][1] - start) / (end - start)
    return tuple(
        Landmark(
            i,
            center + (x - 0.5) * 0.45,
            0.55 + (y - 0.6) * 0.5,
            depths[i],
            CoordinateSpace.FRAME_NORMALIZED,
        )
        for i, (x, y) in enumerate(xy)
    )
