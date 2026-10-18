"""Observed, modal shape selection; no changes to object manipulation or Core."""
import math
import numpy as np
import pygame
from .chemistry_controls import PointPinch
from .dwell import DwellSelector
from .manipulation import pinch_ratio
from .physics_shortcuts import PhysicsShortcuts

KINDS = ('cube', 'tetra', 'octa', 'sphere')
NAMES = ('Lập phương', 'Tứ diện', 'Bát diện', 'Hình cầu')


class SolidPalette:
    def __init__(self, settings):
        self.cfg = settings
        # Reuse the tested source-pose recognizer with an isolated config copy.
        cfg = dict(settings)
        for name in settings:
            if name.startswith(('solid_quick_', 'solid_shortcut_')):
                cfg['physics_' + name[len('solid_'):]] = settings[name]
        self.shortcut = PhysicsShortcuts(cfg)
        self.tap = PointPinch(settings)
        self.dwell = DwellSelector(settings['solid_dwell_s'], settings['chemistry_dwell_max_gap_s'],
                                   settings['chemistry_dwell_rearm_distance'], settings['chemistry_dwell_motion_radius'])
        self.open = False
        self.edge = 'right'
        self.previous = None
        self.hands = {}
        self.anchors = {}
        self.blocked = set()
        self.pointers = {}
        self.hover = {}
        self.rect = pygame.Rect(0, 0, 1, 1)
        self.targets = []

    def layout(self, view):
        x, y, w, h = view
        width = min(self.cfg['solid_quick_width_px'], w-24)
        height = min(self.cfg['solid_quick_height_px'], h-24)
        self.rect = pygame.Rect(x+12 if self.edge == 'left' else x+w-width-12,
                                y+(h-height)//2, width, height)
        body = self.rect.inflate(-24, -82)
        body.y = self.rect.y+42
        gap = 8
        tw, th = (body.w-gap)//2, (body.h-gap)//2
        self.targets = [(pygame.Rect(body.x+(i % 2)*(tw+gap), body.y+(i//2)*(th+gap), tw, th), kind)
                        for i, kind in enumerate(KINDS)]
        self.targets.append((pygame.Rect(self.rect.right-34, self.rect.y+8, 26, 26), 'close'))

    def point(self, hand):
        p = hand.landmarks[8]
        return np.array((1-p.x if self.cfg['mirror'] else p.x, p.y))

    def transition(self, opened):
        self.open = opened
        self.tap.reset(); self.dwell.reset()
        self.pointers.clear(); self.hover.clear()
        self.shortcut.progress = None
        if opened:
            self.anchors = {k: (h.generation, self.point(h)) for k, h in self.hands.items()}
        else:
            self.blocked.update(self.hands)
            self.anchors.clear()

    def suspend(self):
        self.transition(False)
        self.shortcut.reset()
        self.previous = None
        self.hands = {}

    def grab_hands(self, hands, aspect):
        """A menu pinch stays consumed across loss/generation until observed open."""
        for h in hands:
            if h.slot in self.blocked and pinch_ratio(h, aspect) >= self.cfg['grip_release_ratio']:
                self.blocked.remove(h.slot)
        return tuple(h for h in hands if h.slot not in self.blocked)

    def hit(self, point, view):
        x, y, w, h = view
        pixel = (x+point[0]*w, y+point[1]*h)
        return next((action for rect, action in self.targets if rect.collidepoint(pixel)), None)

    def diagnostics(self):
        return {'open': self.open, 'edge': self.edge, 'reaim_slots': sorted(self.anchors),
                'consumed_slots': sorted(self.blocked), 'hover': dict(self.hover),
                'summon_progress': self.shortcut.progress}

    def update(self, hands, t, source_aspect, view, busy=False):
        if not math.isfinite(t): self.suspend(); return None
        available = {h.slot: h for h in hands if len(h.landmarks) == 21
                     and tuple(p.index for p in h.landmarks) == tuple(range(21))
                     and len(h.raw_landmarks or h.landmarks) == 21
                     and tuple(p.index for p in (h.raw_landmarks or h.landmarks)) == tuple(range(21))
                     and all(math.isfinite(v) for points in (h.landmarks, h.raw_landmarks or h.landmarks)
                             for p in points for v in (p.x, p.y, p.z))}
        previous = self.hands; self.hands = available
        if self.previous is not None and (t <= self.previous or t-self.previous > self.cfg['chemistry_dwell_max_gap_s']):
            self.suspend(); self.hands = available; self.blocked.update(available)
            self.previous = t
            return None
        self.previous = t
        self.layout(view)
        aspect = view[2]/view[3]
        if not self.open:
            result = self.shortcut.update(available, available, t, aspect, source_aspect,
                {k: k not in self.blocked for k in available}, not busy, False)
            if result:
                self.edge = result[1]; self.layout(view); self.transition(True)
            return None
        self.tap.retain(available); self.dwell.retain(available)
        self.pointers = {}; self.hover = {}
        for key, hand in sorted(available.items()):
            point = self.point(hand)
            if key not in previous or previous[key].generation != hand.generation:
                self.anchors[key] = (hand.generation, point.copy())
                self.tap.states.pop(key, None); self.dwell.states.pop(key, None)
            if key in self.anchors:
                generation, origin = self.anchors[key]
                self.pointers[key] = tuple(point)
                if (generation == hand.generation and pinch_ratio(hand, source_aspect) >= self.cfg['grip_release_ratio']
                    and np.linalg.norm((point-origin)*np.array((aspect, 1.))) >= self.cfg['solid_quick_reaim_radius']):
                    self.anchors.pop(key)
                continue
            action = self.hit(point, view)
            candidate = ('solid', action) if action else None
            point, chosen = self.tap.update(key, hand, candidate, t, tuple(point), source_aspect)
            self.pointers[key] = point
            state = self.tap.states.get(key)
            self.hover[key] = state.target[1] if state and state.locked else action
            if chosen:
                self.transition(False)
                return chosen[1]
            if state and state.phase in ('press', 'latched'):
                self.dwell.states.pop(key, None)
                continue
            chosen = self.dwell.update(key, hand.generation, candidate, t, point, outside=action is None)
            if chosen:
                self.transition(False)
                return chosen[1]
        return None


def tip_summary(tips, mode):
    """Describe observed geometry without inferring physical depth or extra nodes."""
    counts = [sum(t.hand == slot for t in tips) for slot in (0, 1)]
    count = len(tips)
    kind = ('Chưa có đỉnh' if not count else 'Điểm' if count == 1 else
            'Đoạn' if count == 2 or mode == 'segment' else 'Khối' if mode == 'hull3d' else 'Mặt')
    return f'{kind} · {count} đầu ngón · Tay 1: {counts[0]} | Tay 2: {counts[1]}'
