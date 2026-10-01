"""Compose the existing STEM renderer and BGR UI in one OpenGL window.

No native-window embedding: the shell is a local texture around the same
scene drawing code. UI pixels use top-left coordinates; GL viewport y is
explicitly converted to bottom-left coordinates.
"""

from collections.abc import Callable

import numpy as np

from .renderer import OpenGLStemRenderer
from .ui.layout import Rect
from .scenes.visuals import SceneFrame


def shell_pixels(canvas: np.ndarray, viewport: Rect | None,
                 overlays: tuple[Rect, ...] = ()) -> np.ndarray:
    """Copy BGR to BGRA, making only the live scene viewport transparent."""
    if canvas.ndim != 3 or canvas.shape[2] != 3 or canvas.dtype != np.uint8:
        raise ValueError("shell requires a uint8 BGR image")
    pixels = np.empty((*canvas.shape[:2], 4), dtype=np.uint8)
    pixels[..., :3] = canvas
    pixels[..., 3] = 255
    if viewport is not None:
        pixels[viewport.y:viewport.bottom, viewport.x:viewport.right, 3] = 0
    for rect in overlays:
        pixels[rect.y:rect.bottom, rect.x:rect.right, 3] = 255
    return pixels


class ApplicationShellRenderer(OpenGLStemRenderer):
    """One window, one event queue, one context, existing scene ownership."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._resizable = True
        self._scene_frame: SceneFrame | None = None
        self._texture: int | None = None
        self._texture_size: tuple[int, int] | None = None
        self._canvas_size = (self._width, self._height)
        self._pointer_consumer: Callable[[int, int, bool], None] | None = None

    @property
    def window_size(self) -> tuple[int, int]:
        return self._width, self._height

    def set_pointer_consumer(self, consumer) -> None:
        self._pointer_consumer = consumer

    def render(self, frame: SceneFrame) -> None:
        # The presentation callback composites exactly once per runtime
        # frame, after the interaction callback has updated the scene.
        self._require_open()
        self._validate_frame(frame)
        self._scene_frame = frame

    def close_requested(self) -> bool:
        self._require_open()
        pygame = self._pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.VIDEORESIZE:
                self._width, self._height = max(1, event.w), max(1, event.h)
            elif event.type in {pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED}:
                # Pygame 2 / SDL may emit these instead of VIDEORESIZE.
                self._width, self._height = pygame.display.get_window_size()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                character = "?" if event.key == pygame.K_F1 else event.unicode
                if not character and event.key == pygame.K_RETURN:
                    character = "\r"
                if len(character) == 1 and self._key_consumer is not None:
                    self._key_consumer(character)
            elif event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP}:
                clicked = event.type == pygame.MOUSEBUTTONUP
                if clicked and event.button != 1:
                    continue
                if self._pointer_consumer is not None:
                    x, y = event.pos
                    self._pointer_consumer(
                        round(x * self._canvas_size[0] / self._width),
                        round(y * self._canvas_size[1] / self._height), clicked,
                    )
        return False

    def present_shell(self, canvas, viewport=None, overlays=()) -> None:
        self._require_open()
        gl, glu, pygame = self._gl, self._glu, self._pygame
        self._canvas_size = (canvas.shape[1], canvas.shape[0])
        sx, sy = self._width / canvas.shape[1], self._height / canvas.shape[0]
        gl.glViewport(0, 0, self._width, self._height)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if viewport is not None and self._scene_frame is not None:
            target = Rect(round(viewport.x*sx), round(viewport.y*sy),
                          max(1, round(viewport.width*sx)),
                          max(1, round(viewport.height*sy)))
            gl.glViewport(target.x, self._height-target.bottom,
                          target.width, target.height)
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glLoadIdentity()
            glu.gluPerspective(43.0, target.width/target.height, .1, 100.0)
            gl.glMatrixMode(gl.GL_MODELVIEW)
            self._draw_scene_frame(self._scene_frame)
        self._draw_shell_texture(shell_pixels(canvas, viewport, overlays))
        pygame.display.flip()
        self._clock.tick(self._target_fps)

    def _draw_shell_texture(self, pixels) -> None:
        gl = self._gl
        gl.glViewport(0, 0, self._width, self._height)
        gl.glPushAttrib(gl.GL_ALL_ATTRIB_BITS)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_TEXTURE_2D)
        if self._texture is None:
            self._texture = int(gl.glGenTextures(1))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self._texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        size = (pixels.shape[1], pixels.shape[0])
        if size != self._texture_size:
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, *size, 0,
                            gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, pixels)
            self._texture_size = size
        else:
            gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, *size,
                               gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, pixels)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, self._width, self._height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glColor4f(1, 1, 1, 1)
        gl.glBegin(gl.GL_QUADS)
        for u,v,x,y in [(0,0,0,0),(1,0,self._width,0),
                        (1,1,self._width,self._height),(0,1,0,self._height)]:
            gl.glTexCoord2f(u,v)
            gl.glVertex2f(x,y)
        gl.glEnd()
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopAttrib()

    def close(self) -> None:
        try:
            if self._texture is not None and self._gl is not None:
                self._gl.glDeleteTextures([self._texture])
        finally:
            self._texture = None
            self._texture_size = None
            self._scene_frame = None
            super().close()
