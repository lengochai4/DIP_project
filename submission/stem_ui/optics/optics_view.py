"""Interactive Pygame UI and Visualizer for Optics Experiments."""

import math
from pathlib import Path
from typing import Any, Optional, Tuple
import pygame

from .optics_engine import (
    RefractionResult,
    ThinLensResult,
    PrismDispersionResult,
    SPECTRAL_COLORS,
    OPTICS_MATERIALS,
)
from .optics_experiments import OpticsLabSession

# Color theme matching STEM UI
BG_COLOR = (10, 18, 28)
STAGE_BG = (14, 25, 38)
PANEL_BG = (18, 34, 50)
PANEL_BORDER = (45, 95, 130)
ACCENT = (95, 221, 245)
GOLD = (244, 202, 126)
INK = (235, 245, 252)
MUTED = (145, 175, 195)
WHITE = (255, 255, 255)
GREEN = (80, 235, 140)
RED_LASER = (255, 65, 65)


def draw_glow_line(surface: pygame.Surface, start: Tuple[float, float],
                   end: Tuple[float, float], color: Tuple[int, int, int],
                   width: int = 2, glow_width: int = 6):
    """Draw a bright laser ray with an outer soft glow."""
    glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    glow_color = (*color[:3], 65)
    p1 = (round(start[0]), round(start[1]))
    p2 = (round(end[0]), round(end[1]))
    pygame.draw.line(glow_surf, glow_color, p1, p2, glow_width)
    surface.blit(glow_surf, (0, 0))
    pygame.draw.line(surface, color, p1, p2, width)
    # Bright inner core
    pygame.draw.line(surface, (255, 255, 255, 180), p1, p2, max(1, width - 1))


class OpticsVisualizer:
    """Renders the optics simulation and interactive controls."""

    def __init__(self, session: Optional[OpticsLabSession] = None):
        self.session = session or OpticsLabSession()
        self.fonts = {}
        self.hover_btn = None
        self.active_slider = None

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self.fonts:
            path = Path('C:/Windows/Fonts/segoeui.ttf')
            self.fonts[size] = pygame.font.Font(str(path) if path.is_file() else None, size)
        return self.fonts[size]

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int, int]):
        """Render full optics canvas and controls onto surface."""
        w, h = surface.get_size()
        surface.fill(BG_COLOR)

        # 1. Header with Tabs
        self._draw_header(surface, w, mouse_pos)

        # 2. Split Stage (Left) and Control Panel (Right)
        panel_w = 380
        stage_w = w - panel_w - 32
        stage_rect = pygame.Rect(16, 85, stage_w, h - 100)
        panel_rect = pygame.Rect(w - panel_w - 16, 85, panel_w, h - 100)

        # Draw Stage Area
        pygame.draw.rect(surface, STAGE_BG, stage_rect, border_radius=14)
        pygame.draw.rect(surface, PANEL_BORDER, stage_rect, 1, border_radius=14)

        # Render Active Experiment onto Stage
        stage_center = (stage_rect.centerx, stage_rect.centery)
        res = self.session.evaluate(center=stage_center, scale_factor=stage_rect.height / 600.0)

        if self.session.current_lab == 'refraction' and isinstance(res, RefractionResult):
            self._render_refraction(surface, stage_rect, res)
        elif self.session.current_lab == 'lens' and isinstance(res, ThinLensResult):
            self._render_lens(surface, stage_rect, res)
        elif self.session.current_lab == 'prism' and isinstance(res, PrismDispersionResult):
            self._render_prism(surface, stage_rect, res)

        # 3. Control Panel on Right
        self._draw_controls(surface, panel_rect, res, mouse_pos)

    def _draw_header(self, surface: pygame.Surface, w: int, mouse_pos: Tuple[int, int]):
        # Title
        f_title = self._font(24)
        t_surf = f_title.render("THÍ NGHIỆM QUANG HỌC STEM", True, ACCENT)
        surface.blit(t_surf, (20, 20))

        # 3 Tabs
        tabs = [
            ('refraction', '1. Khúc xạ & Phản xạ toàn phần'),
            ('lens', '2. Thấu kính mỏng (Hội tụ / Phân kì)'),
            ('prism', '3. Tán sắc qua Lăng kính'),
        ]
        tx = 360
        self.tab_targets = []
        for tid, tname in tabs:
            is_active = (self.session.current_lab == tid)
            tw = self._font(17).size(tname)[0] + 28
            rect = pygame.Rect(tx, 16, tw, 42)
            self.tab_targets.append((rect, tid))

            is_hov = rect.collidepoint(mouse_pos)
            col_bg = (30, 60, 85) if is_active else ((22, 42, 60) if is_hov else (16, 30, 44))
            border_col = ACCENT if is_active else ((100, 160, 190) if is_hov else PANEL_BORDER)

            pygame.draw.rect(surface, col_bg, rect, border_radius=10)
            pygame.draw.rect(surface, border_col, rect, 2 if is_active else 1, border_radius=10)
            lbl_col = GOLD if is_active else (INK if is_hov else MUTED)
            lbl_surf = self._font(17).render(tname, True, lbl_col)
            surface.blit(lbl_surf, lbl_surf.get_rect(center=rect.center))
            tx += tw + 14

    def _render_refraction(self, surface: pygame.Surface, stage_rect: pygame.Rect, res: RefractionResult):
        cx, cy = stage_rect.centerx, stage_rect.centery

        # Medium 2 (bottom) background shading
        m2_rect = pygame.Rect(stage_rect.left, cy, stage_rect.width, stage_rect.bottom - cy)
        m2_alpha = min(90, int(35 + (res.n2 - 1.0) * 45))
        m2_surf = pygame.Surface((m2_rect.width, m2_rect.height), pygame.SRCALPHA)
        m2_surf.fill((30, 120, 180, m2_alpha))
        surface.blit(m2_surf, m2_rect.topleft)

        # Boundary line between media
        pygame.draw.line(surface, ACCENT, (stage_rect.left, cy), (stage_rect.right, cy), 2)

        # Normal line (dashed vertical line)
        for y in range(stage_rect.top + 20, stage_rect.bottom - 20, 14):
            pygame.draw.line(surface, (120, 160, 190), (cx, y), (cx, y + 8), 1)

        # Media labels
        f = self._font(18)
        surface.blit(f.render(f"Môi trường 1 (Trên): n₁ = {res.n1:.3f}", True, INK), (stage_rect.left + 20, cy - 36))
        surface.blit(f.render(f"Môi trường 2 (Dưới): n₂ = {res.n2:.3f}", True, INK), (stage_rect.left + 20, cy + 18))

        # Incident Ray (Laser)
        draw_glow_line(surface, res.incident_ray[0], res.incident_ray[1], RED_LASER, width=3, glow_width=8)
        # Reflected Ray
        refl_color = (255, 100, 100) if res.is_tir else (255, 140, 140)
        refl_w = 3 if res.is_tir else 2
        draw_glow_line(surface, res.reflected_ray[0], res.reflected_ray[1], refl_color, width=refl_w, glow_width=6)

        # Refracted Ray (if not TIR)
        if not res.is_tir and res.refracted_ray:
            draw_glow_line(surface, res.refracted_ray[0], res.refracted_ray[1], (100, 240, 255), width=3, glow_width=8)

        # Status badge on stage
        b_col = (255, 75, 75) if res.is_tir else (50, 200, 120)
        badge_text = "PHẢN XẠ TOÀN PHẦN (TIR)" if res.is_tir else f"KHÚC XẠ: r = {res.r_deg:.1f}°"
        badge_surf = self._font(20).render(badge_text, True, b_col)
        surface.blit(badge_surf, (stage_rect.right - badge_surf.get_width() - 20, stage_rect.top + 20))

    def _render_lens(self, surface: pygame.Surface, stage_rect: pygame.Rect, res: ThinLensResult):
        cx, cy = stage_rect.centerx, stage_rect.centery

        # Principal optical axis (Trục chính)
        pygame.draw.line(surface, (90, 130, 160), (stage_rect.left + 10, cy), (stage_rect.right - 10, cy), 1)

        # Lens vertical line
        lens_h = 240
        pygame.draw.line(surface, ACCENT, (cx, cy - lens_h // 2), (cx, cy + lens_h // 2), 3)

        # Arrows indicating converging vs diverging
        if res.is_converging:
            # Outward arrows (V)
            pygame.draw.lines(surface, ACCENT, False, [(cx - 10, cy - lens_h // 2 + 12), (cx, cy - lens_h // 2), (cx + 10, cy - lens_h // 2 + 12)], 3)
            pygame.draw.lines(surface, ACCENT, False, [(cx - 10, cy + lens_h // 2 - 12), (cx, cy + lens_h // 2), (cx + 10, cy + lens_h // 2 - 12)], 3)
        else:
            # Inward arrows (^)
            pygame.draw.lines(surface, ACCENT, False, [(cx - 10, cy - lens_h // 2), (cx, cy - lens_h // 2 + 12), (cx + 10, cy - lens_h // 2)], 3)
            pygame.draw.lines(surface, ACCENT, False, [(cx - 10, cy + lens_h // 2), (cx, cy + lens_h // 2 - 12), (cx + 10, cy + lens_h // 2)], 3)

        # Optical center O
        pygame.draw.circle(surface, INK, (round(cx), round(cy)), 4)
        surface.blit(self._font(16).render("O", True, INK), (cx - 16, cy + 6))

        # Focal points F and F'
        for pt, lbl in [(res.focal_f, "F"), (res.focal_f_prime, "F'")]:
            if stage_rect.left < pt[0] < stage_rect.right:
                pygame.draw.circle(surface, GOLD, (round(pt[0]), round(pt[1])), 5)
                surface.blit(self._font(16).render(lbl, True, GOLD), (round(pt[0]) - 6, cy + 8))

        # 3 Principal Rays
        ray_colors = [(0, 240, 255), (255, 220, 60), (255, 90, 200)]
        for segs, col in zip([res.ray1_segments, res.ray2_segments, res.ray3_segments], ray_colors):
            for p1, p2 in segs:
                # Clip visually to stage
                draw_glow_line(surface, p1, p2, col, width=2, glow_width=5)

        # Object AB (Glowing Green Arrow)
        pygame.draw.line(surface, GREEN, res.object_base, res.object_tip, 4)
        # Arrowhead
        pygame.draw.polygon(surface, GREEN, [
            res.object_tip,
            (res.object_tip[0] - 6, res.object_tip[1] + 12),
            (res.object_tip[0] + 6, res.object_tip[1] + 12)
        ])
        surface.blit(self._font(16).render("B (Vật)", True, GREEN), (res.object_tip[0] - 24, res.object_tip[1] - 22))

        # Image A'B' (Gold Arrow)
        if res.image_base and res.image_tip and not res.is_infinity:
            img_col = GOLD if res.is_real else (255, 170, 70)
            p_base, p_tip = res.image_base, res.image_tip
            pygame.draw.line(surface, img_col, p_base, p_tip, 4)
            # Arrowhead direction depending on sign of h'
            head_dir = -1 if (p_tip[1] < p_base[1]) else 1
            pygame.draw.polygon(surface, img_col, [
                p_tip,
                (p_tip[0] - 6, p_tip[1] - head_dir * 12),
                (p_tip[0] + 6, p_tip[1] - head_dir * 12)
            ])
            lbl_type = "B' (Ảnh thật)" if res.is_real else "B' (Ảnh ảo)"
            surface.blit(self._font(16).render(lbl_type, True, img_col), (p_tip[0] - 26, p_tip[1] + head_dir * 18))

    def _render_prism(self, surface: pygame.Surface, stage_rect: pygame.Rect, res: PrismDispersionResult):
        # Draw Glass Prism Triangle with transparent sheen
        pts = [(round(p[0]), round(p[1])) for p in res.prism_vertices]
        prism_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(prism_surf, (80, 160, 220, 60), pts)
        pygame.draw.polygon(prism_surf, (160, 225, 255, 180), pts, 2)
        surface.blit(prism_surf, (0, 0))

        # Apex label A
        surface.blit(self._font(18).render(f"A = {res.apex_angle_deg:.0f}°", True, GOLD), (pts[0][0] - 24, pts[0][1] - 28))

        # Draw 7 Rainbow Dispersed Rays
        for ray in res.color_rays:
            rgb = ray.color_info['rgb']
            for i in range(len(ray.path) - 1):
                p1 = ray.path[i]
                p2 = ray.path[i + 1]
                # If first segment (white source light before prism)
                col = (255, 255, 255) if i == 0 else rgb
                draw_glow_line(surface, p1, p2, col, width=2 if i == 0 else 3, glow_width=6)

        # Screen / Spectrum receiver on the right
        screen_x = stage_rect.right - 45
        pygame.draw.line(surface, (200, 220, 240), (screen_x, stage_rect.top + 60), (screen_x, stage_rect.bottom - 60), 4)
        surface.blit(self._font(16).render("Màn hứng", True, MUTED), (screen_x - 30, stage_rect.top + 35))

    def _draw_controls(self, surface: pygame.Surface, rect: pygame.Rect, res: Any, mouse_pos: Tuple[int, int]):
        pygame.draw.rect(surface, PANEL_BG, rect, border_radius=14)
        pygame.draw.rect(surface, PANEL_BORDER, rect, 1, border_radius=14)

        x, y = rect.x + 20, rect.y + 20
        f_head = self._font(20)
        f_body = self._font(16)
        f_sub = self._font(14)

        # 1. Section Title
        surface.blit(f_head.render("THÔNG SỐ & THIẾT LẬP", True, GOLD), (x, y))
        y += 34

        # 2. Sliders / Value Adjusters
        self.btn_targets = []
        cur_lab = self.session.current_lab
        params = self.session.params[cur_lab]

        for p_name, val in params.items():
            if isinstance(val, (int, float)):
                # Row with Label and Value
                p_label = p_name.replace('_', ' ').title()
                val_str = f"{val:.2f}" if isinstance(val, float) else f"{val}"
                surface.blit(f_body.render(f"{p_label}:", True, INK), (x, y))
                v_surf = f_body.render(val_str, True, ACCENT)
                surface.blit(v_surf, (rect.right - v_surf.get_width() - 25, y))
                y += 26

                # Minus & Plus Buttons
                btn_minus = pygame.Rect(x, y, 70, 32)
                btn_plus = pygame.Rect(x + 80, y, 70, 32)
                self.btn_targets.append((btn_minus, f"adj:{p_name}:-"))
                self.btn_targets.append((btn_plus, f"adj:{p_name}:+"))

                for b, txt in [(btn_minus, "− Giảm"), (btn_plus, "+ Tăng")]:
                    hov = b.collidepoint(mouse_pos)
                    pygame.draw.rect(surface, (35, 65, 95) if hov else (24, 45, 65), b, border_radius=8)
                    pygame.draw.rect(surface, ACCENT if hov else PANEL_BORDER, b, 1, border_radius=8)
                    t_b = f_sub.render(txt, True, INK)
                    surface.blit(t_b, t_b.get_rect(center=b.center))
                y += 42
            elif isinstance(val, str) and p_name == 'material':
                surface.blit(f_body.render("Vật liệu lăng kính:", True, INK), (x, y))
                y += 26
                btn_mat = pygame.Rect(x, y, rect.width - 40, 34)
                self.btn_targets.append((btn_mat, "cycle_material"))
                hov = btn_mat.collidepoint(mouse_pos)
                pygame.draw.rect(surface, (35, 65, 95) if hov else (24, 45, 65), btn_mat, border_radius=8)
                pygame.draw.rect(surface, ACCENT if hov else PANEL_BORDER, btn_mat, 1, border_radius=8)
                mat_name = OPTICS_MATERIALS.get(val, {}).get('name', val)
                t_m = f_sub.render(f"❖ {mat_name} (Nhấn để đổi)", True, GOLD)
                surface.blit(t_m, t_m.get_rect(center=btn_mat.center))
                y += 44

        # 3. Presets
        surface.blit(f_head.render("CÁC MẪU THÍ NGHIỆM CHUẨN", True, GOLD), (x, y))
        y += 30
        presets = self.session.PRESETS.get(cur_lab, {})
        for p_key, p_info in presets.items():
            btn_pre = pygame.Rect(x, y, rect.width - 40, 34)
            self.btn_targets.append((btn_pre, f"preset:{p_key}"))
            hov = btn_pre.collidepoint(mouse_pos)
            pygame.draw.rect(surface, (28, 55, 80) if hov else (18, 36, 52), btn_pre, border_radius=8)
            pygame.draw.rect(surface, ACCENT if hov else PANEL_BORDER, btn_pre, 1, border_radius=8)
            lbl = f_sub.render(p_info['name'], True, INK if hov else MUTED)
            surface.blit(lbl, (x + 12, y + 8))
            y += 40

        # 4. Result Summary Box
        y = max(y + 10, rect.bottom - 130)
        box_rect = pygame.Rect(x, y, rect.width - 40, 110)
        pygame.draw.rect(surface, (12, 22, 34), box_rect, border_radius=10)
        pygame.draw.rect(surface, ACCENT, box_rect, 1, border_radius=10)
        surface.blit(f_sub.render("KẾT QUẢ VẬT LÝ:", True, GOLD), (x + 12, y + 10))

        # Wrapped summary text
        sum_text = res.summary if hasattr(res, 'summary') else ""
        lines = []
        words = sum_text.split()
        cur_l = ""
        for w in words:
            test_l = cur_l + (" " if cur_l else "") + w
            if f_sub.size(test_l)[0] < box_rect.width - 24:
                cur_l = test_l
            else:
                lines.append(cur_l)
                cur_l = w
        if cur_l: lines.append(cur_l)

        for li, l_str in enumerate(lines[:3]):
            surface.blit(f_sub.render(l_str, True, INK), (x + 12, y + 34 + li * 22))

    def handle_click(self, pos: Tuple[int, int]):
        """Process mouse clicks on tabs and control buttons."""
        # Check tabs
        for rect, tid in getattr(self, 'tab_targets', []):
            if rect.collidepoint(pos):
                self.session.select_lab(tid)
                return

        # Check buttons
        for rect, act in getattr(self, 'btn_targets', []):
            if rect.collidepoint(pos):
                if act.startswith('adj:'):
                    _, pname, direction = act.split(':')
                    cur_val = self.session.get_param(pname)
                    # Step amounts
                    step_map = {
                        'n1': 0.05, 'n2': 0.05, 'incident_angle': 2.0,
                        'focal_length': 2.0, 'object_distance': 2.0, 'object_height': 0.5,
                        'apex_angle': 2.0
                    }
                    step = step_map.get(pname, 1.0)
                    if direction == '-':
                        new_val = cur_val - step
                    else:
                        new_val = cur_val + step

                    # Bounds clamping
                    bounds = {
                        'n1': (1.0, 2.5), 'n2': (1.0, 2.5), 'incident_angle': (0.0, 85.0),
                        'focal_length': (-30.0, 30.0), 'object_distance': (4.0, 55.0),
                        'object_height': (1.0, 8.0), 'apex_angle': (30.0, 70.0)
                    }
                    if pname in bounds:
                        lo, hi = bounds[pname]
                        new_val = max(lo, min(hi, new_val))
                    self.session.set_param(pname, new_val)
                elif act.startswith('preset:'):
                    preset_key = act.split(':', 1)[1]
                    self.session.apply_preset(preset_key)
                elif act == 'cycle_material':
                    cur_mat = self.session.get_param('material')
                    mats = ['flint_glass', 'crown_glass', 'water', 'diamond']
                    next_idx = (mats.index(cur_mat) + 1) % len(mats) if cur_mat in mats else 0
                    self.session.set_param('material', mats[next_idx])
                return
