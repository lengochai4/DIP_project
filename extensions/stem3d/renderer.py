"""Optional Pygame/OpenGL renderer for immutable STEM scene frames."""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from .scenes.visuals import SceneFrame, SceneLine, SceneSphere


class OpenGLStemRenderer:
    """Render scene-owned lines and spheres in a shared 3D viewport."""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        target_fps: int,
        title: str = "DIP Touchless STEM 3D",
    ) -> None:
        self._require_positive_integer(width, name="width")
        self._require_positive_integer(height, name="height")
        self._require_positive_integer(target_fps, name="target_fps")

        self._width = width
        self._height = height
        self._target_fps = target_fps
        self._title = title
        self._last_caption: str | None = None

        self._pygame: Any | None = None
        self._gl: Any | None = None
        self._glu: Any | None = None
        self._clock: Any | None = None
        self._quadric: Any | None = None
        self._opened = False

    @property
    def opened(self) -> bool:
        return self._opened

    def open(self) -> None:
        """Create the renderer window, context, and reusable sphere resource."""

        if self._opened:
            return

        try:
            import pygame
            from OpenGL import GL
            from OpenGL import GLU
        except ImportError as exc:
            raise RuntimeError(
                "3D demo dependencies are unavailable; "
                "install the project with the demo3d extra"
            ) from exc

        self._pygame = pygame
        self._gl = GL
        self._glu = GLU
        pygame.init()

        try:
            pygame.display.set_mode(
                (self._width, self._height),
                pygame.DOUBLEBUF | pygame.OPENGL,
            )
            self._set_caption(self._title)
            GL.glViewport(0, 0, self._width, self._height)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glClearColor(0.035, 0.045, 0.065, 1.0)

            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(
                43.0,
                self._width / self._height,
                0.1,
                100.0,
            )
            GL.glMatrixMode(GL.GL_MODELVIEW)

            GL.glEnable(GL.GL_LIGHTING)
            GL.glEnable(GL.GL_LIGHT0)
            GL.glEnable(GL.GL_COLOR_MATERIAL)
            GL.glColorMaterial(
                GL.GL_FRONT_AND_BACK,
                GL.GL_AMBIENT_AND_DIFFUSE,
            )
            GL.glEnable(GL.GL_NORMALIZE)
            GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (4.0, 6.0, 8.0, 1.0))
            GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (0.23, 0.23, 0.26, 1.0))
            GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (0.92, 0.92, 0.95, 1.0))

            self._quadric = GLU.gluNewQuadric()
            if self._quadric is None:
                raise RuntimeError("OpenGL could not allocate a sphere renderer")
            GLU.gluQuadricNormals(self._quadric, GLU.GLU_SMOOTH)
            self._clock = pygame.time.Clock()
            self._opened = True
        except Exception:
            self._release_resources()
            raise

    def close_requested(self) -> bool:
        """Return whether the user requested renderer shutdown."""

        self._require_open()
        pygame = self._pygame
        assert pygame is not None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_ESCAPE
            ):
                return True
        return False

    def render(self, frame: SceneFrame) -> None:
        """Render one immutable scene frame."""

        self._require_open()
        self._validate_frame(frame)

        pygame = self._pygame
        gl = self._gl
        assert pygame is not None
        assert gl is not None
        assert self._glu is not None
        assert self._clock is not None
        assert self._quadric is not None

        caption = f"{self._title} - {frame.title} - {frame.subtitle}"
        self._set_caption(caption)

        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        gl.glTranslatef(0.0, 0.0, -5.6)
        gl.glRotatef(math.degrees(frame.transform.pitch_rad), 1.0, 0.0, 0.0)
        gl.glRotatef(math.degrees(frame.transform.yaw_rad), 0.0, 1.0, 0.0)
        gl.glScalef(
            frame.transform.scale,
            frame.transform.scale,
            frame.transform.scale,
        )

        gl.glDisable(gl.GL_LIGHTING)
        self._draw_lines(frame.lines)
        gl.glEnable(gl.GL_LIGHTING)
        self._draw_spheres(frame.spheres)

        pygame.display.flip()
        self._clock.tick(self._target_fps)

    def close(self) -> None:
        """Release the reusable GLU quadric and Pygame display resources."""

        self._release_resources()

    def _draw_lines(self, lines: tuple[SceneLine, ...]) -> None:
        gl = self._gl
        assert gl is not None
        grouped: dict[float, list[SceneLine]] = defaultdict(list)
        for line in lines:
            grouped[float(line.width)].append(line)

        for width, group in grouped.items():
            gl.glLineWidth(width)
            gl.glBegin(gl.GL_LINES)
            for line in group:
                gl.glColor3f(*line.color)
                gl.glVertex3f(*line.start)
                gl.glVertex3f(*line.end)
            gl.glEnd()
        gl.glLineWidth(1.0)

    def _draw_spheres(self, spheres: tuple[SceneSphere, ...]) -> None:
        gl = self._gl
        glu = self._glu
        assert gl is not None
        assert glu is not None
        assert self._quadric is not None

        for sphere in spheres:
            gl.glPushMatrix()
            gl.glTranslatef(*sphere.center)
            gl.glColor3f(*sphere.color)
            glu.gluSphere(self._quadric, sphere.radius, 20, 14)
            gl.glPopMatrix()

    def _set_caption(self, caption: str) -> None:
        if caption == self._last_caption:
            return
        if self._pygame is not None:
            self._pygame.display.set_caption(caption)
        self._last_caption = caption

    def _release_resources(self) -> None:
        glu = self._glu
        pygame = self._pygame
        quadric = self._quadric
        try:
            if glu is not None and quadric is not None:
                glu.gluDeleteQuadric(quadric)
        finally:
            if pygame is not None:
                pygame.quit()
            self._pygame = None
            self._gl = None
            self._glu = None
            self._clock = None
            self._quadric = None
            self._opened = False
            self._last_caption = None

    def _require_open(self) -> None:
        if not self._opened:
            raise RuntimeError("renderer is not open")

    @staticmethod
    def _validate_frame(frame: SceneFrame) -> None:
        if not isinstance(frame, SceneFrame):
            raise TypeError("renderer requires a SceneFrame")
        transform = frame.transform
        values = (transform.yaw_rad, transform.pitch_rad, transform.scale)
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in values
        ):
            raise ValueError("scene transform values must be finite")
        if transform.scale <= 0.0:
            raise ValueError("scene scale must be positive")

    @staticmethod
    def _require_positive_integer(value: int, *, name: str) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(f"{name} must be a positive integer")
