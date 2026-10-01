"""Local, cached geometric outline icons. No external assets or fonts."""

from functools import lru_cache

import cv2
import numpy as np
from .theme import THEME

ICON_NAMES = frozenset({
    "workspace", "analysis", "evidence", "geometry", "molecule", "orbit",
    "camera", "roi", "illumination", "enhancement", "tracking", "filter",
    "gesture", "interaction", "control", "reset", "help", "warning",
    "error", "ready", "exit",
})


@lru_cache(maxsize=128)
def icon_mask(name: str, size: int) -> np.ndarray:
    if name not in ICON_NAMES:
        raise ValueError(f"unknown icon: {name}")
    if size < 12:
        raise ValueError("icon size must be at least 12")
    image = np.zeros((size, size), dtype=np.uint8)
    def point(x, y):
        return round(x * (size - 1)), round(y * (size - 1))
    def line(a, b):
        cv2.line(image, point(*a), point(*b), 255, 1, cv2.LINE_AA)
    def circle(center, radius):
        cv2.circle(image, point(*center), round(radius * size), 255, 1,
                   cv2.LINE_AA)
    def box(a=(.15, .2), b=(.85, .8)):
        cv2.rectangle(image, point(*a), point(*b), 255, 1, cv2.LINE_AA)
    if name in {"workspace", "geometry"}:
        for a, b in [((.2,.35),(.5,.15)),((.5,.15),(.8,.35)),
                     ((.8,.35),(.5,.55)),((.5,.55),(.2,.35)),
                     ((.2,.35),(.2,.7)),((.8,.35),(.8,.7)),
                     ((.5,.55),(.5,.9)),((.2,.7),(.5,.9)),
                     ((.5,.9),(.8,.7))]:
            line(a, b)
    elif name in {"molecule", "gesture"}:
        line((.25,.7),(.5,.3)); line((.5,.3),(.8,.65))
        for c in ((.25,.7),(.5,.3),(.8,.65)):
            circle(c, .12)
    elif name in {"orbit", "illumination"}:
        circle((.5,.5), .18)
        cv2.ellipse(image, point(.5,.5), (round(size*.4), round(size*.23)),
                    -30, 0, 360, 255, 1, cv2.LINE_AA)
    elif name in {"analysis", "filter"}:
        line((.12,.8),(.12,.2)); line((.12,.8),(.9,.8))
        for a,b in [((.2,.6),(.4,.4)),((.4,.4),(.6,.55)),
                    ((.6,.55),(.85,.2))]:
            line(a,b)
    elif name == "evidence":
        box((.25,.12),(.8,.88))
        for y in (.35,.5,.65):
            line((.38,y),(.67,y))
    elif name == "camera":
        box(); circle((.5,.5), .17); line((.3,.2),(.4,.1))
    elif name in {"roi", "tracking", "interaction"}:
        for x,y,dx,dy in [( .15,.15,1,1),(.85,.15,-1,1),
                         (.15,.85,1,-1),(.85,.85,-1,-1)]:
            line((x,y),(x+.2*dx,y)); line((x,y),(x,y+.2*dy))
        circle((.5,.5), .09)
    elif name == "enhancement":
        line((.2,.8),(.8,.2)); circle((.3,.3), .12)
        line((.65,.75),(.85,.75)); line((.75,.65),(.75,.85))
    elif name == "control":
        for y in (.25,.5,.75):
            line((.15,y),(.85,y))
            circle((.35 if y == .5 else .65,y), .07)
    elif name == "reset":
        cv2.ellipse(image, point(.5,.5), (round(size*.32),round(size*.32)),
                    0, 35, 310, 255, 1, cv2.LINE_AA)
        line((.22,.25),(.22,.5)); line((.22,.5),(.45,.45))
    elif name == "help":
        circle((.5,.5), .4)
        cv2.putText(image, "?", point(.34,.72), cv2.FONT_HERSHEY_SIMPLEX,
                    size / 35, 255, 1, cv2.LINE_AA)
    elif name == "warning":
        for a,b in [((.5,.1),(.9,.85)),((.9,.85),(.1,.85)),
                    ((.1,.85),(.5,.1))]:
            line(a,b)
        line((.5,.35),(.5,.6)); circle((.5,.73), .025)
    elif name in {"error", "exit"}:
        if name == "error":
            circle((.5,.5), .4)
        line((.3,.3),(.7,.7)); line((.7,.3),(.3,.7))
    else:
        circle((.5,.5), .4)
        line((.25,.5),(.43,.68)); line((.43,.68),(.75,.32))
    image.setflags(write=False)
    return image


def draw_icon(canvas, name, x, y, *, size=THEME.icon_md, color=THEME.accent):
    mask = icon_mask(name, size)
    if x < 0 or y < 0 or x + size > canvas.shape[1] or y + size > canvas.shape[0]:
        return
    region = canvas[y:y+size, x:x+size]
    alpha = mask[..., None].astype(np.float32) / 255
    region[:] = (region * (1-alpha) + np.array(color) * alpha).astype(np.uint8)
