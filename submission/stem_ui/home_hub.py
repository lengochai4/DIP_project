"""AssistiveTouch-style floating virtual Home button and radial app launcher."""
import math
from pathlib import Path
import numpy as np
import pygame
from .theme import ACCENT, GOLD, INK, MUTED, BG, glass, outline
from .camera_space import CameraCover


def _sector_polygon(cx, cy, r_in, r_out, start_deg, end_deg, steps=24):
    t_start = math.radians(start_deg)
    t_end = math.radians(end_deg)
    ts = np.linspace(t_start, t_end, steps)
    outer = [(cx + r_out * math.cos(t), cy + r_out * math.sin(t)) for t in ts]
    inner = [(cx + r_in * math.cos(t), cy + r_in * math.sin(t)) for t in reversed(ts)]
    return outer + inner


class VirtualHomeHub:
    """Floating virtual home button with expandable 3-sector radial STEM hub."""

    def __init__(self, settings):
        self.settings = settings
        self.pos = None
        self.radius = 28
        self.inner_radius = 42
        self.expanded_radius = 110
        self.expanded = False
        self.dragging = False
        self.drag_offset = np.zeros(2)
        self.drag_moved = False
        self.dwell_target = None
        self.dwell_time = 0.0
        self.dwell_duration = 0.70
        self.pulse = 0.0
        self.sectors = (
            {
                'id': 'solid',
                'title': 'HÌNH HỌC',
                'subtitle': 'Không gian 3D',
                'color': (45, 175, 235),
                'start_deg': -42.0,
                'end_deg': 42.0,
                'center_deg': 0.0,
            },
            {
                'id': 'chemistry',
                'title': 'HÓA HỌC',
                'subtitle': 'Phân tử AR',
                'color': (35, 215, 160),
                'start_deg': 48.0,
                'end_deg': 132.0,
                'center_deg': 90.0,
            },
            {
                'id': 'tracking',
                'title': 'NHẬN DIỆN',
                'subtitle': 'Điểm mốc tay',
                'color': (195, 115, 255),
                'start_deg': 138.0,
                'end_deg': 222.0,
                'center_deg': 180.0,
            },
            {
                'id': 'physics',
                'title': 'VẬT LÝ',
                'subtitle': 'Cơ học & Lực',
                'color': (245, 165, 45),
                'start_deg': 228.0,
                'end_deg': 312.0,
                'center_deg': 270.0,
            },
        )

    def default_pos(self, screen_size, header_h=70, view=None):
        if view is not None:
            vx, vy, vw, vh = view
            return np.array([vx + vw - 110.0, vy + 75.0], dtype=float)
        w, _ = screen_size
        return np.array([w - 95.0, header_h + 55.0], dtype=float)

    def is_center_region(self, pos, screen_size):
        w, h = screen_size
        center = np.array([w * 0.5, h * 0.5])
        dist = float(np.linalg.norm(pos - center))
        if dist < min(w, h) * 0.32:
            return True
        if abs(pos[0] - center[0]) < w * 0.22 and abs(pos[1] - center[1]) < h * 0.22:
            return True
        return False

    def menu_center(self, screen_size=None, view=None):
        """Get the true center for rendering and hit-testing the hub."""
        if self.pos is None:
            return None
        if not self.expanded:
            return self.pos
        cx, cy = self.pos[0], self.pos[1]
        if view is not None:
            vx, vy, vw, vh = view
            margin = self.expanded_radius + 4.0
            mcx = float(np.clip(cx, vx + margin, vx + vw - margin))
            mcy = float(np.clip(cy, vy + margin, vy + vh - margin))
            return np.array([mcx, mcy], dtype=float)
        elif screen_size is not None:
            w, h = screen_size
            margin = self.expanded_radius + 4.0
            mcx = float(np.clip(cx, margin, w - margin))
            mcy = float(np.clip(cy, margin, h - margin))
            return np.array([mcx, mcy], dtype=float)
        return self.pos

    def update(self, dt, screen_size, header_h, hands=(), mouse_pos=None, mouse_down=False, mirror=True, view=None, source_aspect=None):
        """Update dragging, snap-to-corner logic, and hover/dwell selection."""
        w, h = screen_size
        if self.pos is None:
            self.pos = self.default_pos(screen_size, header_h, view)

        self.pulse += dt * 3.0

        # Gather interaction pointers (mouse and hand fingertips)
        pointers = []
        pinch_pointers = []
        if mouse_pos is not None:
            pointers.append(('mouse', np.array(mouse_pos, dtype=float)))
            if mouse_down:
                pinch_pointers.append(('mouse', np.array(mouse_pos, dtype=float)))

        if view is not None and hands:
            vx, vy, vw, vh = view
            src_asp = source_aspect if source_aspect is not None else 4.0 / 3.0
            cover = CameraCover(src_asp, vw / max(1, vh))
            hands_to_use = [cover.hand(h) for h in hands]
            use_vw, use_vh = vw, vh
            use_vx, use_vy = vx, vy
        else:
            hands_to_use = hands
            use_vw, use_vh = float(w), float(h)
            use_vx, use_vy = 0.0, 0.0

        for hand in hands_to_use:
            if not getattr(hand, 'landmarks', None) or len(hand.landmarks) != 21:
                continue
            tip = hand.landmarks[8]
            thumb = hand.landmarks[4]
            tx = use_vx + (1.0 - tip.x if mirror else tip.x) * use_vw
            ty = use_vy + tip.y * use_vh
            pointers.append((f'hand_{hand.slot}', np.array([tx, ty], dtype=float)))

            hx = use_vx + (1.0 - thumb.x if mirror else thumb.x) * use_vw
            hy = use_vy + thumb.y * use_vh
            pinch_dist = math.hypot(tx - hx, ty - hy)
            if pinch_dist < 48.0:
                mid = np.array([(tx + hx) * 0.5, (ty + hy) * 0.5], dtype=float)
                pinch_pointers.append((f'pinch_{hand.slot}', mid))

        # 1. Handle Dragging (using 2 fingers / pinch or mouse drag)
        if pinch_pointers:
            p_kind, p_pt = pinch_pointers[0]
            if not self.dragging:
                if np.linalg.norm(p_pt - self.pos) <= self.radius + 20.0:
                    self.dragging = True
                    self.drag_offset = self.pos - p_pt
                    self.drag_moved = False
                    self.expanded = False
                    self.dwell_time = 0.0
            if self.dragging:
                new_pos = p_pt + self.drag_offset
                if np.linalg.norm(new_pos - self.pos) > 4.0:
                    self.drag_moved = True
                self.pos = new_pos
        else:
            if self.dragging:
                self.dragging = False
                if self.is_center_region(self.pos, screen_size):
                    self.pos = self.default_pos(screen_size, header_h, view)

        # Clamp position to camera view if provided, else to screen bounds
        if view is not None:
            vx, vy, vw, vh = view
            self.pos[0] = float(np.clip(self.pos[0], vx + self.radius + 6.0, vx + vw - self.radius - 6.0))
            self.pos[1] = float(np.clip(self.pos[1], vy + self.radius + 6.0, vy + vh - self.radius - 6.0))
        else:
            self.pos[0] = float(np.clip(self.pos[0], 55.0, w - 55.0))
            self.pos[1] = float(np.clip(self.pos[1], header_h + 30.0, h - 55.0))

        if self.dragging:
            self.dwell_time = 0.0
            self.dwell_target = None
            return None

        # 2. Hover & Dwell Selection
        center = self.menu_center(screen_size, view)
        active_target = None
        for _, pt in pointers:
            if not self.expanded:
                if np.linalg.norm(pt - self.pos) <= self.radius + 8.0:
                    active_target = 'home'
                    break
            else:
                vec = pt - center
                dist = float(np.linalg.norm(vec))
                if dist > self.inner_radius + 6.0:
                    self.close_armed = True
                if dist <= self.inner_radius + 4.0:
                    if getattr(self, 'close_armed', False):
                        active_target = 'close'
                        break
                    else:
                        continue
                if self.inner_radius < dist <= self.expanded_radius + 10.0:
                    angle = (math.degrees(math.atan2(vec[1], vec[0])) + 360.0) % 360.0
                    for s in self.sectors:
                        s_start = (s['start_deg'] + 360.0) % 360.0
                        s_end = (s['end_deg'] + 360.0) % 360.0
                        if s_start > s_end:
                            inside = angle >= s_start or angle <= s_end
                        else:
                            inside = s_start <= angle <= s_end
                        if inside:
                            active_target = s['id']
                            break
                    if active_target:
                        break

        triggered_action = None
        if active_target is not None:
            if active_target == self.dwell_target:
                self.dwell_time += dt
                if self.dwell_time >= self.dwell_duration:
                    self.dwell_time = 0.0
                    if active_target == 'home':
                        self.expanded = True
                        self.close_armed = False
                    elif active_target == 'close':
                        self.expanded = False
                        self.close_armed = False
                    else:
                        triggered_action = active_target
                        self.expanded = False
                        self.close_armed = False
                    self.dwell_target = None
            else:
                self.dwell_target = active_target
                self.dwell_time = 0.0
        else:
            self.dwell_target = None
            self.dwell_time = 0.0

        return triggered_action

    def handle_click(self, pos, screen_size, header_h, view=None):
        """Process direct mouse click on the home button or its radial sectors."""
        pt = np.asarray(pos, dtype=float)
        if self.pos is None:
            self.pos = self.default_pos(screen_size, header_h, view)

        if not self.expanded:
            if np.linalg.norm(pt - self.pos) <= self.radius + 10.0:
                self.expanded = True
                self.close_armed = False
                self.dwell_time = 0.0
                return None
            return None

        center = self.menu_center(screen_size, view)
        vec = pt - center
        dist = float(np.linalg.norm(vec))
        if dist <= self.inner_radius + 4.0:
            self.expanded = False
            self.close_armed = False
            self.dwell_time = 0.0
            return None

        if self.inner_radius < dist <= self.expanded_radius + 10.0:
            angle = (math.degrees(math.atan2(vec[1], vec[0])) + 360.0) % 360.0
            for s in self.sectors:
                s_start = (s['start_deg'] + 360.0) % 360.0
                s_end = (s['end_deg'] + 360.0) % 360.0
                if s_start > s_end:
                    inside = angle >= s_start or angle <= s_end
                else:
                    inside = s_start <= angle <= s_end
                if inside:
                    self.expanded = False
                    self.close_armed = False
                    self.dwell_time = 0.0
                    return s['id']

        if dist > self.expanded_radius + 20.0:
            self.expanded = False
            self.close_armed = False
            self.dwell_time = 0.0
        return None

    def draw(self, surface, fonts, current_mode='solid', view=None):
        """Render the floating home button or expanded radial app launcher."""
        if self.pos is None:
            return

        cx, cy = int(round(self.pos[0])), int(round(self.pos[1]))
        w, h = surface.get_size()

        if not self.expanded:
            # 1. Closed State: Translucent, glowing floating pill/circle
            hovered = self.dwell_target == 'home'
            alpha = 240 if (hovered or self.dragging) else 165
            sub_surface = pygame.Surface((self.radius * 2 + 20, self.radius * 2 + 20), pygame.SRCALPHA)
            scx, scy = self.radius + 10, self.radius + 10

            # Outer subtle glow
            pygame.draw.circle(sub_surface, (20, 45, 60, alpha // 2), (scx, scy), self.radius + 4)
            # Base dark translucent circle
            pygame.draw.circle(sub_surface, (14, 22, 32, alpha), (scx, scy), self.radius)
            # Rim ring
            ring_color = ACCENT if hovered else (70, 130, 160, alpha)
            pygame.draw.circle(sub_surface, ring_color, (scx, scy), self.radius, 2)
            # Inner circle (like iPhone AssistiveTouch concentric ring)
            pygame.draw.circle(sub_surface, (200, 230, 255, min(255, alpha - 30)), (scx, scy), 13, 2)
            # Center 4-dot micro STEM cluster
            dots = [
                ((scx + 5, scy), (45, 175, 235)),     # Right: Cyan (Geometry)
                ((scx, scy + 5), (35, 215, 160)),     # Bottom: Emerald (Chemistry)
                ((scx - 5, scy), (195, 115, 255)),    # Left: Violet (Tracking)
                ((scx, scy - 5), (245, 165, 45)),     # Top: Amber (Physics)
            ]
            for pt, col in dots:
                pygame.draw.circle(sub_surface, col, pt, 2)

            # Dwell progress ring around button
            if hovered and self.dwell_time > 0.0:
                frac = min(1.0, self.dwell_time / max(1e-4, self.dwell_duration))
                rect = pygame.Rect(scx - self.radius - 2, scy - self.radius - 2, (self.radius + 2) * 2, (self.radius + 2) * 2)
                sweep = frac * math.tau
                pygame.draw.arc(sub_surface, GOLD, rect, -sweep, 0, 3)

            surface.blit(sub_surface, (cx - scx, cy - scy))

        else:
            # 2. Expanded Radial Menu (Hình 2)
            # Background soft dim
            dim_rect = pygame.Rect(0, 0, w, h)
            dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            dim_surf.fill((10, 16, 24, 75))
            surface.blit(dim_surf, (0, 0))

            # Menu center on screen (perfectly synced with hit-testing)
            center = self.menu_center((w, h), view)
            mcx, mcy = int(round(center[0])), int(round(center[1]))

            # Draw outer glow circle
            radial_surf = pygame.Surface((self.expanded_radius * 2 + 40, self.expanded_radius * 2 + 40), pygame.SRCALPHA)
            rcx, rcy = self.expanded_radius + 20, self.expanded_radius + 20

            pygame.draw.circle(radial_surf, (15, 25, 35, 220), (rcx, rcy), self.expanded_radius + 6)
            pygame.draw.circle(radial_surf, (60, 100, 130, 190), (rcx, rcy), self.expanded_radius + 6, 2)

            # Draw the 3 curved sector arcs
            for s in self.sectors:
                is_active = (s['id'] == current_mode)
                is_hovered = (self.dwell_target == s['id'])
                col = s['color']

                poly = _sector_polygon(rcx, rcy, self.inner_radius, self.expanded_radius,
                                       s['start_deg'], s['end_deg'], steps=28)

                # Sector background fill
                fill_alpha = 230 if is_hovered else (180 if is_active else 125)
                fill_color = (*col, fill_alpha)
                pygame.draw.polygon(radial_surf, fill_color, poly)

                # Sector border
                border_color = GOLD if is_active else ((*col, 255) if is_hovered else (75, 120, 145, 180))
                border_width = 3 if (is_active or is_hovered) else 2
                pygame.draw.polygon(radial_surf, border_color, poly, border_width)

                # Dwell progress arc along sector's outer rim
                if is_hovered and self.dwell_time > 0.0:
                    frac = min(1.0, self.dwell_time / max(1e-4, self.dwell_duration))
                    s_deg = s['start_deg']
                    e_deg = s_deg + frac * (s['end_deg'] - s_deg)
                    dwell_poly = _sector_polygon(rcx, rcy, self.expanded_radius - 5, self.expanded_radius + 1,
                                                s_deg, e_deg, steps=16)
                    pygame.draw.polygon(radial_surf, GOLD, dwell_poly)

                # Blit text in sector center
                mid_angle = math.radians(s['center_deg'])
                mid_r = (self.inner_radius + self.expanded_radius) * 0.5
                tx = rcx + mid_r * math.cos(mid_angle)
                ty = rcy + mid_r * math.sin(mid_angle)

                # Title
                font_title = fonts.get(14) or pygame.font.Font(None, 14)
                title_glyph = font_title.render(s['title'], True, INK)
                radial_surf.blit(title_glyph, title_glyph.get_rect(center=(tx, ty - 8)))

                # Subtitle
                font_sub = fonts.get(12) or pygame.font.Font(None, 12)
                sub_color = GOLD if is_active else (210, 235, 250)
                sub_glyph = font_sub.render(s['subtitle'], True, sub_color)
                radial_surf.blit(sub_glyph, sub_glyph.get_rect(center=(tx, ty + 10)))

                if is_active:
                    pygame.draw.circle(radial_surf, GOLD, (int(round(tx)), int(round(ty + 22))), 3)

            # Center Hub (Close / Home)
            hub_hovered = self.dwell_target == 'close'
            is_armed = getattr(self, 'close_armed', False)
            hub_alpha = 245 if hub_hovered else (215 if is_armed else 160)
            pygame.draw.circle(radial_surf, (18, 28, 40, hub_alpha), (rcx, rcy), self.inner_radius)
            ring_col = (220, 80, 80) if hub_hovered else (ACCENT if is_armed else (90, 120, 140, 160))
            pygame.draw.circle(radial_surf, ring_col, (rcx, rcy), self.inner_radius, 2)

            font_hub = fonts.get(15) or pygame.font.Font(None, 15)
            close_glyph = font_hub.render('✕', True, (255, 120, 120) if hub_hovered else (INK if is_armed else MUTED))
            radial_surf.blit(close_glyph, close_glyph.get_rect(center=(rcx, rcy - 6)))

            font_hub_sub = fonts.get(11) or pygame.font.Font(None, 11)
            close_text = font_hub_sub.render('ĐÓNG', True, (255, 180, 180) if hub_hovered else MUTED)
            radial_surf.blit(close_text, close_text.get_rect(center=(rcx, rcy + 10)))

            if hub_hovered and self.dwell_time > 0.0:
                frac = min(1.0, self.dwell_time / max(1e-4, self.dwell_duration))
                rect = pygame.Rect(rcx - self.inner_radius - 2, rcy - self.inner_radius - 2,
                                   (self.inner_radius + 2) * 2, (self.inner_radius + 2) * 2)
                pygame.draw.arc(radial_surf, (255, 120, 120), rect, -frac * math.tau, 0, 3)

            surface.blit(radial_surf, (mcx - rcx, mcy - rcy))
