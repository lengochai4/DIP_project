"""Small context-owned overlays; moving glyphs never upload the whole window."""
from collections import OrderedDict
import pygame
from OpenGL import GL as gl


class ScreenSprites:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = OrderedDict()
        self.versions = {}

    def close(self):
        if self.items:
            gl.glDeleteTextures([item[0] for item in self.items.values()])
        self.items.clear()
        self.versions.clear()

    @staticmethod
    def begin(size):
        w,h=size
        gl.glViewport(0,0,w,h)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,w,h,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()

    def draw(self, key, surface, position, version=None):
        if key in self.items and surface is not None and surface.get_size()!=self.items[key][1]:
            gl.glDeleteTextures([self.items.pop(key)[0]])
            self.versions.pop(key,None)
        if key not in self.items:
            texture = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
            size = surface.get_size()
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, *size, 0, gl.GL_RGBA,
                            gl.GL_UNSIGNED_BYTE, pygame.image.tobytes(surface, 'RGBA', False))
            self.items[key] = (texture, size)
            self.versions[key] = version
            if len(self.items) > self.capacity:
                old, item = self.items.popitem(last=False)
                gl.glDeleteTextures([item[0]])
                self.versions.pop(old,None)
        elif version is not None and self.versions.get(key)!=version:
            texture,size=self.items[key]
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
            gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,*size,gl.GL_RGBA,gl.GL_UNSIGNED_BYTE,
                               pygame.image.tobytes(surface,'RGBA',False))
            self.versions[key]=version
        texture, (w, h) = self.items[key]
        self.items.move_to_end(key)
        x, y = position
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glColor4f(1, 1, 1, 1); gl.glBegin(gl.GL_QUADS)
        for (u, v), point in zip(((0, 0), (1, 0), (1, 1), (0, 1)),
                                 ((x, y), (x+w, y), (x+w, y+h), (x, y+h))):
            gl.glTexCoord2f(u, v); gl.glVertex2f(*point)
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D); gl.glDisable(gl.GL_BLEND)
