"""Optional Pygame/OpenGL renderer for the STEM 3D extension."""

from __future__ import annotations

import math
from typing import Any

from .scene_state import SceneTransform


class OpenGLStemRenderer:
    """Render a minimal coordinate-frame cube using Pygame/OpenGL."""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        target_fps: int,
        title: str = "DIP Touchless STEM 3D",
    ) -> None:
        self._require_positive_integer(
            width,
            name="width",
        )
        self._require_positive_integer(
            height,
            name="height",
        )
        self._require_positive_integer(
            target_fps,
            name="target_fps",
        )

        self._width = width
        self._height = height
        self._target_fps = target_fps
        self._title = title

        self._pygame: Any | None = None
        self._gl: Any | None = None
        self._glu: Any | None = None
        self._clock: Any | None = None

        self._opened = False

    @property
    def opened(self) -> bool:
        return self._opened

    def open(self) -> None:
        """Create the renderer window and OpenGL context."""

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
                (
                    self._width,
                    self._height,
                ),
                pygame.DOUBLEBUF
                | pygame.OPENGL,
            )

            pygame.display.set_caption(
                self._title
            )

            GL.glViewport(
                0,
                0,
                self._width,
                self._height,
            )

            GL.glEnable(
                GL.GL_DEPTH_TEST
            )

            GL.glClearColor(
                0.05,
                0.05,
                0.08,
                1.0,
            )

            GL.glMatrixMode(
                GL.GL_PROJECTION
            )

            GL.glLoadIdentity()

            GLU.gluPerspective(
                45.0,
                self._width
                / self._height,
                0.1,
                100.0,
            )

            GL.glMatrixMode(
                GL.GL_MODELVIEW
            )

            self._clock = (
                pygame.time.Clock()
            )

            self._opened = True

        except Exception:
            pygame.quit()

            self._pygame = None
            self._gl = None
            self._glu = None
            self._clock = None

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
                event.type
                == pygame.KEYDOWN
                and event.key
                == pygame.K_ESCAPE
            ):
                return True

        return False

    def render(
        self,
        transform: SceneTransform,
    ) -> None:
        """Render one scene transform."""

        self._require_open()
        self._validate_transform(
            transform
        )

        pygame = self._pygame
        gl = self._gl

        assert pygame is not None
        assert gl is not None
        assert self._clock is not None

        gl.glClear(
            gl.GL_COLOR_BUFFER_BIT
            | gl.GL_DEPTH_BUFFER_BIT
        )

        gl.glLoadIdentity()

        gl.glTranslatef(
            0.0,
            0.0,
            -5.0,
        )

        gl.glRotatef(
            math.degrees(
                transform.pitch_rad
            ),
            1.0,
            0.0,
            0.0,
        )

        gl.glRotatef(
            math.degrees(
                transform.yaw_rad
            ),
            0.0,
            1.0,
            0.0,
        )

        gl.glScalef(
            transform.scale,
            transform.scale,
            transform.scale,
        )

        self._draw_axes()
        self._draw_cube()

        pygame.display.flip()

        self._clock.tick(
            self._target_fps
        )

    def close(self) -> None:
        """Release renderer resources."""

        if self._pygame is not None:
            self._pygame.quit()

        self._pygame = None
        self._gl = None
        self._glu = None
        self._clock = None

        self._opened = False

    def _draw_axes(self) -> None:
        gl = self._gl
        assert gl is not None

        gl.glBegin(
            gl.GL_LINES
        )

        gl.glColor3f(
            1.0,
            0.2,
            0.2,
        )
        gl.glVertex3f(
            0.0,
            0.0,
            0.0,
        )
        gl.glVertex3f(
            1.5,
            0.0,
            0.0,
        )

        gl.glColor3f(
            0.2,
            1.0,
            0.2,
        )
        gl.glVertex3f(
            0.0,
            0.0,
            0.0,
        )
        gl.glVertex3f(
            0.0,
            1.5,
            0.0,
        )

        gl.glColor3f(
            0.2,
            0.4,
            1.0,
        )
        gl.glVertex3f(
            0.0,
            0.0,
            0.0,
        )
        gl.glVertex3f(
            0.0,
            0.0,
            1.5,
        )

        gl.glEnd()

    def _draw_cube(self) -> None:
        gl = self._gl
        assert gl is not None

        vertices = (
            (-0.5, -0.5, -0.5),
            (0.5, -0.5, -0.5),
            (0.5, 0.5, -0.5),
            (-0.5, 0.5, -0.5),
            (-0.5, -0.5, 0.5),
            (0.5, -0.5, 0.5),
            (0.5, 0.5, 0.5),
            (-0.5, 0.5, 0.5),
        )

        edges = (
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        )

        gl.glColor3f(
            0.9,
            0.9,
            0.9,
        )

        gl.glBegin(
            gl.GL_LINES
        )

        for start, end in edges:
            gl.glVertex3f(
                *vertices[start]
            )
            gl.glVertex3f(
                *vertices[end]
            )

        gl.glEnd()

    def _require_open(self) -> None:
        if not self._opened:
            raise RuntimeError(
                "renderer is not open"
            )

    @staticmethod
    def _validate_transform(
        transform: SceneTransform,
    ) -> None:
        values = (
            transform.yaw_rad,
            transform.pitch_rad,
            transform.scale,
        )

        if not all(
            isinstance(
                value,
                (int, float),
            )
            and not isinstance(
                value,
                bool,
            )
            and math.isfinite(value)
            for value in values
        ):
            raise ValueError(
                "scene transform values "
                "must be finite"
            )

        if transform.scale <= 0.0:
            raise ValueError(
                "scene scale must be positive"
            )

    @staticmethod
    def _require_positive_integer(
        value: int,
        *,
        name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a positive integer"
            )