"""Optics computation engine for reflection, refraction, lenses, and prisms.

All mathematical computations are exact analytical geometric optics (SI / standard units).
Zero UI dependencies for pure testability and performance.
"""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple


OPTICS_MATERIALS = {
    'air': {'name': 'Không khí', 'n': 1.0003, 'dispersion': (1.000, 1.001)},
    'water': {'name': 'Nước', 'n': 1.333, 'dispersion': (1.331, 1.344)},
    'alcohol': {'name': 'Rượu Ethanol', 'n': 1.361, 'dispersion': (1.358, 1.372)},
    'crown_glass': {'name': 'Thủy tinh Crown', 'n': 1.517, 'dispersion': (1.514, 1.528)},
    'flint_glass': {'name': 'Thủy tinh Flint', 'n': 1.620, 'dispersion': (1.615, 1.663)},
    'diamond': {'name': 'Kim cương', 'n': 2.417, 'dispersion': (2.408, 2.465)},
}

# 7 classic visible spectral colors (wavelength nm, label, RGB)
SPECTRAL_COLORS = [
    {'name': 'Đỏ', 'en': 'Red', 'wl': 700, 'rgb': (255, 60, 60), 'n_factor': 0.0},
    {'name': 'Cam', 'en': 'Orange', 'wl': 620, 'rgb': (255, 140, 20), 'n_factor': 0.16},
    {'name': 'Vàng', 'en': 'Yellow', 'wl': 580, 'rgb': (255, 230, 40), 'n_factor': 0.33},
    {'name': 'Lục', 'en': 'Green', 'wl': 530, 'rgb': (40, 235, 90), 'n_factor': 0.50},
    {'name': 'Lam', 'en': 'Cyan', 'wl': 490, 'rgb': (30, 210, 255), 'n_factor': 0.67},
    {'name': 'Chàm', 'en': 'Indigo', 'wl': 450, 'rgb': (75, 100, 255), 'n_factor': 0.83},
    {'name': 'Tím', 'en': 'Violet', 'wl': 400, 'rgb': (190, 70, 255), 'n_factor': 1.0},
]


@dataclass
class RefractionResult:
    n1: float
    n2: float
    i_deg: float
    r_deg: Optional[float]
    critical_angle_deg: Optional[float]
    is_tir: bool
    reflectance: float
    transmittance: float
    # Geometry for visualization: (start, end) tuples
    incident_ray: Tuple[Tuple[float, float], Tuple[float, float]]
    reflected_ray: Tuple[Tuple[float, float], Tuple[float, float]]
    refracted_ray: Optional[Tuple[Tuple[float, float], Tuple[float, float]]]
    summary: str


def compute_refraction(n1: float, n2: float, i_deg: float,
                       origin: Tuple[float, float] = (0.0, 0.0),
                       ray_len: float = 240.0) -> RefractionResult:
    """Compute Snell's refraction and total internal reflection at a flat boundary.
    
    Origin (0, 0) is at the boundary. Medium 1 is above (y < 0 or incoming),
    medium 2 is below (y > 0).
    """
    n1 = max(1.0, float(n1))
    n2 = max(1.0, float(n2))
    i_deg = max(0.0, min(89.5, float(i_deg)))
    i_rad = math.radians(i_deg)

    # Critical angle when going from denser to rarer medium (n1 > n2)
    crit_deg = None
    if n1 > n2:
        sin_crit = n2 / n1
        crit_deg = math.degrees(math.asin(sin_crit))

    sin_i = math.sin(i_rad)
    sin_r = (n1 / n2) * sin_i
    ox, oy = origin

    # Incident ray (comes from medium 1 towards origin)
    # Incident angle i is measured with the normal (vertical Y axis)
    inc_start = (ox - ray_len * math.sin(i_rad), oy - ray_len * math.cos(i_rad))
    inc_end = (ox, oy)

    # Reflected ray (always exists, angle i' = i in medium 1)
    ref_start = (ox, oy)
    ref_end = (ox + ray_len * math.sin(i_rad), oy - ray_len * math.cos(i_rad))

    if sin_r > 1.0:
        # Total Internal Reflection (TIR)
        is_tir = True
        r_deg = None
        refr_ray = None
        reflectance = 1.0
        transmittance = 0.0
        summary = (f"Phản xạ toàn phần! Góc tới i={i_deg:.1f}° > i_gh={crit_deg:.1f}°. "
                   f"Toàn bộ 100% ánh sáng bị phản xạ trở lại.")
    else:
        is_tir = False
        r_rad = math.asin(sin_r)
        r_deg = math.degrees(r_rad)
        refr_start = (ox, oy)
        refr_end = (ox + ray_len * math.sin(r_rad), oy + ray_len * math.cos(r_rad))
        refr_ray = (refr_start, refr_end)

        # Fresnel reflection coefficient (average of s- and p-polarization)
        cos_i = math.cos(i_rad)
        cos_r = math.cos(r_rad)
        if cos_i + cos_r > 1e-6:
            rs = ((n1 * cos_i - n2 * cos_r) / (n1 * cos_i + n2 * cos_r)) ** 2
            rp = ((n2 * cos_i - n1 * cos_r) / (n2 * cos_i + n1 * cos_r)) ** 2
            reflectance = min(1.0, max(0.0, 0.5 * (rs + rp)))
        else:
            reflectance = 1.0
        transmittance = 1.0 - reflectance

        gh_str = f" • Góc giới hạn i_gh={crit_deg:.1f}°" if crit_deg else ""
        summary = (f"Khúc xạ ánh sáng: i={i_deg:.1f}° → r={r_deg:.1f}°{gh_str}. "
                   f"Phản xạ: {reflectance*100:.1f}%, Khúc xạ: {transmittance*100:.1f}%.")

    return RefractionResult(
        n1=n1, n2=n2, i_deg=i_deg, r_deg=r_deg,
        critical_angle_deg=crit_deg, is_tir=is_tir,
        reflectance=reflectance, transmittance=transmittance,
        incident_ray=(inc_start, inc_end),
        reflected_ray=(ref_start, ref_end),
        refracted_ray=refr_ray,
        summary=summary
    )


@dataclass
class ThinLensResult:
    f: float
    d: float
    h: float
    d_prime: Optional[float]
    h_prime: Optional[float]
    k: Optional[float]
    is_converging: bool
    is_real: bool
    is_virtual: bool
    is_infinity: bool
    # Coordinates of key entities for rendering:
    lens_center: Tuple[float, float]
    focal_f: Tuple[float, float]
    focal_f_prime: Tuple[float, float]
    object_base: Tuple[float, float]
    object_tip: Tuple[float, float]
    image_base: Optional[Tuple[float, float]]
    image_tip: Optional[Tuple[float, float]]
    # 3 Principal Rays: List of line segments [(p1, p2), ...]
    ray1_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    ray2_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    ray3_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]
    summary: str


def compute_thin_lens(f: float, d: float, h: float = 4.0,
                      center: Tuple[float, float] = (0.0, 0.0),
                      scale_px: float = 6.0) -> ThinLensResult:
    """Compute thin lens imaging equation: 1/f = 1/d + 1/d'.
    
    f > 0: converging (hội tụ), f < 0: diverging (phân kì).
    d > 0: object distance in front of lens (cm).
    h > 0: object height (cm).
    scale_px: screen pixels per cm.
    """
    f = float(f)
    if abs(f) < 0.1: f = 0.1 if f >= 0 else -0.1
    d = max(1.0, float(d))
    h = max(0.5, float(h))
    is_converging = (f > 0)
    cx, cy = center

    # 1/f = 1/d + 1/d' => d' = (d * f) / (d - f)
    denom = d - f
    is_inf = abs(denom) < 1e-4

    # Lens positions in pixels:
    # Object is to the left of the lens: x = cx - d * scale_px
    obj_x = cx - d * scale_px
    obj_base = (obj_x, cy)
    obj_tip = (obj_x, cy - h * scale_px)

    # Focal points in pixels:
    # For converging (f > 0): F is on left (cx - f), F' is on right (cx + f)
    # For diverging (f < 0): F is on right (cx - f = cx + |f|), F' is on left (cx - |f|)
    f_x = cx - f * scale_px
    f_prime_x = cx + f * scale_px
    focal_f = (f_x, cy)
    focal_f_prime = (f_prime_x, cy)

    ray1_segs = []
    ray2_segs = []
    ray3_segs = []

    if is_inf:
        d_prime = None
        h_prime = None
        k = None
        is_real = False
        is_virtual = False
        img_base = None
        img_tip = None
        summary = f"Vật tại tiêu điểm d = f = {f:.1f} cm! Chùm tia ló song song, ảnh ở vô cực (∞)."
        # Ray 1: parallel to axis, hits lens at (cx, obj_tip[1]), goes through F'
        lens_hit = (cx, obj_tip[1])
        ray1_segs.append((obj_tip, lens_hit))
        # through F' extended
        dx = f_prime_x - cx
        dy = cy - obj_tip[1]
        far_x = cx + 400
        far_y = lens_hit[1] + (far_x - cx) * (dy / dx)
        ray1_segs.append((lens_hit, (far_x, far_y)))

        # Ray 2: through center O
        dx2 = cx - obj_tip[0]
        dy2 = cy - obj_tip[1]
        ray2_segs.append((obj_tip, (cx + 400, cy + (400 / dx2) * dy2)))
    else:
        d_prime = (d * f) / denom
        k = -d_prime / d
        h_prime = k * h
        is_real = (d_prime > 0)
        is_virtual = (d_prime < 0)

        img_x = cx + d_prime * scale_px
        img_y = cy - h_prime * scale_px
        img_base = (img_x, cy)
        img_tip = (img_x, img_y)

        # Ray 1: From object tip parallel to principal axis -> hits lens -> passes through F'
        hit1 = (cx, obj_tip[1])
        ray1_segs.append((obj_tip, hit1))
        if is_real:
            ray1_segs.append((hit1, img_tip))
            # Extend a bit further
            ext_x = img_x + 60
            ext_y = hit1[1] + (ext_x - cx) * ((img_y - hit1[1]) / max(1e-4, img_x - cx))
            ray1_segs.append((img_tip, (ext_x, ext_y)))
        else:
            # Virtual image: refracted ray goes to right, virtual backward extension goes to img_tip
            right_x = cx + 300
            slope = (cy - hit1[1]) / (f_prime_x - cx)
            right_y = hit1[1] + (right_x - cx) * slope
            ray1_segs.append((hit1, (right_x, right_y)))
            # Virtual dotted extension back to image tip
            ray1_segs.append((hit1, img_tip))

        # Ray 2: From object tip straight through optical center O (cx, cy)
        ray2_segs.append((obj_tip, (cx, cy)))
        if is_real:
            ray2_segs.append(((cx, cy), img_tip))
        else:
            right_x = cx + 300
            slope2 = (cy - obj_tip[1]) / (cx - obj_tip[0])
            right_y = cy + 300 * slope2
            ray2_segs.append(((cx, cy), (right_x, right_y)))
            # Backwards to img_tip
            ray2_segs.append(((cx, cy), img_tip))

        # Ray 3: Direction through focal point F -> exits parallel to axis
        if is_converging and d != f:
            hit3 = (cx, cy - h_prime * scale_px)
            ray3_segs.append((obj_tip, hit3))
            ray3_segs.append((hit3, img_tip))
        else:
            # Diverging or simple fallback
            ray3_segs.append((obj_tip, (cx, cy)))

        real_str = "Ảnh THẬT, ngược chiều" if is_real else "Ảnh ẢO, cùng chiều"
        summary = (f"{'Thấu kính hội tụ' if is_converging else 'Thấu kính phân kì'}: "
                   f"f={f:.1f} cm, d={d:.1f} cm → d'={d_prime:.1f} cm (k={k:.2f}). "
                   f"{real_str}, cao |h'|={abs(h_prime):.1f} cm.")

    return ThinLensResult(
        f=f, d=d, h=h, d_prime=d_prime, h_prime=h_prime, k=k,
        is_converging=is_converging, is_real=is_real, is_virtual=is_virtual,
        is_infinity=is_inf, lens_center=center,
        focal_f=focal_f, focal_f_prime=focal_f_prime,
        object_base=obj_base, object_tip=obj_tip,
        image_base=img_base, image_tip=img_tip,
        ray1_segments=ray1_segs, ray2_segments=ray2_segs, ray3_segments=ray3_segs,
        summary=summary
    )


@dataclass
class PrismColorRay:
    color_info: dict
    n: float
    r1_deg: float
    r2_deg: float
    i2_deg: Optional[float]
    deviation_deg: Optional[float]
    is_tir: bool
    path: List[Tuple[float, float]]


@dataclass
class PrismDispersionResult:
    apex_angle_deg: float
    i1_deg: float
    material_key: str
    material_name: str
    color_rays: List[PrismColorRay]
    angular_spread_deg: float
    has_tir_colors: bool
    prism_vertices: List[Tuple[float, float]]
    summary: str


def compute_prism_dispersion(apex_deg: float = 60.0,
                             i1_deg: float = 48.0,
                             material: str = 'flint_glass',
                             center: Tuple[float, float] = (0.0, 0.0),
                             size: float = 160.0) -> PrismDispersionResult:
    """Compute chromatic dispersion of light through a triangular prism.
    
    A: prism apex angle (góc chiết quang)
    i1: angle of incidence on face 1
    Prism is oriented with apex at top, base at bottom.
    """
    apex_deg = max(30.0, min(75.0, float(apex_deg)))
    i1_deg = max(10.0, min(80.0, float(i1_deg)))
    mat_info = OPTICS_MATERIALS.get(material, OPTICS_MATERIALS['flint_glass'])
    n_base = mat_info['n']
    n_min, n_max = mat_info['dispersion']

    A_rad = math.radians(apex_deg)
    i1_rad = math.radians(i1_deg)
    cx, cy = center

    # Triangular prism vertices (Apex T, Bottom-Left B1, Bottom-Right B2)
    # Side length S = size. Height H = S * cos(A/2). Half-width = S * sin(A/2).
    half_w = size * math.sin(A_rad / 2)
    h_prism = size * math.cos(A_rad / 2)
    v_top = (cx, cy - h_prism * 0.55)
    v_left = (cx - half_w, cy + h_prism * 0.45)
    v_right = (cx + half_w, cy + h_prism * 0.45)
    prism_vertices = [v_top, v_left, v_right]

    # Face 1 is line (v_top -> v_left).
    # Normal to Face 1 points up-left.
    face1_angle = math.atan2(v_left[1] - v_top[1], v_left[0] - v_top[0])
    normal1_angle = face1_angle - math.pi / 2

    # Incident point on Face 1: mid-point of upper face 1
    p1 = (v_top[0] * 0.45 + v_left[0] * 0.55, v_top[1] * 0.45 + v_left[1] * 0.55)
    # Incoming white beam hits p1 at angle i1 relative to normal1
    beam_in_angle = normal1_angle - i1_rad
    p_source = (p1[0] - 180.0 * math.cos(beam_in_angle),
                p1[1] - 180.0 * math.sin(beam_in_angle))

    color_rays = []
    has_tir = False
    valid_devs = []

    for c in SPECTRAL_COLORS:
        # Cauchy dispersion approximation for refractive index per wavelength:
        n_c = n_min + c['n_factor'] * (n_max - n_min)

        # 1. Refraction at Face 1: sin(i1) = n * sin(r1)
        sin_r1 = math.sin(i1_rad) / n_c
        r1_rad = math.asin(sin_r1)
        r1_deg = math.degrees(r1_rad)

        # Ray direction inside prism
        ray_inside_angle = normal1_angle - r1_rad

        # 2. Geometry inside prism: r2 = A - r1
        r2_rad = A_rad - r1_rad
        r2_deg = math.degrees(r2_rad)

        # Intersection with Face 2 (line v_top -> v_right)
        # Face 2 parameterization: P(t) = v_top + t * (v_right - v_top)
        # Ray inside: R(s) = p1 + s * (cos(theta), sin(theta))
        dx_f = v_right[0] - v_top[0]; dy_f = v_right[1] - v_top[1]
        dx_r = math.cos(ray_inside_angle); dy_r = math.sin(ray_inside_angle)
        det = dx_r * dy_f - dy_r * dx_f

        if abs(det) > 1e-6:
            s_val = ((v_top[0] - p1[0]) * dy_f - (v_top[1] - p1[1]) * dx_f) / det
            p2 = (p1[0] + s_val * dx_r, p1[1] + s_val * dy_r)
        else:
            p2 = (cx + half_w * 0.5, cy)

        # 3. Refraction or TIR at Face 2: n * sin(r2) = sin(i2)
        sin_i2 = n_c * math.sin(r2_rad)
        face2_angle = math.atan2(v_right[1] - v_top[1], v_right[0] - v_top[0])
        normal2_angle = face2_angle + math.pi / 2

        if sin_i2 > 1.0 or r2_rad < 0:
            is_tir_c = True
            has_tir = True
            i2_deg = None
            dev_deg = None
            # Internal reflection inside prism
            refl_angle = normal2_angle + (math.pi - r2_rad)
            p3 = (p2[0] + 100.0 * math.cos(refl_angle), p2[1] + 100.0 * math.sin(refl_angle))
            path = [p_source, p1, p2, p3]
        else:
            is_tir_c = False
            i2_rad = math.asin(sin_i2)
            i2_deg = math.degrees(i2_rad)
            dev_deg = math.degrees(i1_rad + i2_rad - A_rad)
            valid_devs.append(dev_deg)

            ray_out_angle = normal2_angle + i2_rad
            p3 = (p2[0] + 200.0 * math.cos(ray_out_angle),
                  p2[1] + 200.0 * math.sin(ray_out_angle))
            path = [p_source, p1, p2, p3]

        color_rays.append(PrismColorRay(
            color_info=c, n=n_c, r1_deg=r1_deg, r2_deg=r2_deg,
            i2_deg=i2_deg, deviation_deg=dev_deg,
            is_tir=is_tir_c, path=path
        ))

    angular_spread = (max(valid_devs) - min(valid_devs)) if len(valid_devs) >= 2 else 0.0
    d_red_str = f"D_đỏ={valid_devs[0]:.1f}°" if valid_devs else "TIR"
    d_vio_str = f"D_tím={valid_devs[-1]:.1f}°" if valid_devs else "TIR"
    summary = (f"Lăng kính {mat_info['name']} (A={apex_deg:.0f}°), góc tới i₁={i1_deg:.1f}°: "
               f"{d_red_str}, {d_vio_str}. Độ rộng dải tán sắc: ΔD={angular_spread:.2f}°.")

    return PrismDispersionResult(
        apex_angle_deg=apex_deg, i1_deg=i1_deg,
        material_key=material, material_name=mat_info['name'],
        color_rays=color_rays, angular_spread_deg=angular_spread,
        has_tir_colors=has_tir, prism_vertices=prism_vertices,
        summary=summary
    )
