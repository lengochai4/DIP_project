"""Local OpenGL meshes, real depth testing and illustrative lighting.

No tracking/provider inputs. Qt owns the context; close() runs with it current.
"""

import ctypes
from functools import lru_cache
import math
import numpy as np
from PySide6.QtGui import QColor

VERTEX = """#version 330
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec3 color;
uniform mat4 projection;
uniform mat3 orientation;
out vec3 n;
out vec3 c;
void main() { gl_Position=projection*vec4(position,1); n=orientation*normal; c=color; }
"""
FRAGMENT = """#version 330
in vec3 n;
in vec3 c;
out vec4 result;
void main() {
    if (length(n)<0.01) { result=vec4(c,1); return; }
    vec3 normal=normalize(n);
    if (!gl_FrontFacing) normal=-normal;
    vec3 light=normalize(vec3(-0.4,0.7,1.0));
    float diffuse=max(dot(normal,light),0.0);
    float specular=pow(max(dot(reflect(-light,normal),vec3(0,0,1)),0.0),28.0);
    result=vec4(c*(0.25+0.75*diffuse)+vec3(0.23*specular),1);
}
"""


@lru_cache(maxsize=1)
def sphere():
    rows = []

    def point(latitude, longitude):
        return (
            math.sin(latitude) * math.cos(longitude),
            math.cos(latitude),
            math.sin(latitude) * math.sin(longitude),
        )

    for i in range(12):
        for j in range(18):
            a, b, c, d = [
                point(lat, lon)
                for lat, lon in (
                    (math.pi * i / 12, 2 * math.pi * j / 18),
                    (math.pi * (i + 1) / 12, 2 * math.pi * j / 18),
                    (math.pi * (i + 1) / 12, 2 * math.pi * (j + 1) / 18),
                    (math.pi * i / 12, 2 * math.pi * (j + 1) / 18),
                )
            ]
            rows.extend((a, c, b, a, d, c))
    return np.array(rows, dtype=np.float32)


def rgb(value):
    color = QColor(value)
    return (color.redF(), color.greenF(), color.blueF())


def mesh(geometry, projection, show_grid):
    triangles, lines = [], []
    for ball in geometry.balls:
        unit = sphere()
        vertices = unit * ball.radius + ball.center
        triangles.append(
            np.column_stack((vertices, unit, np.tile(rgb(ball.color), (len(unit), 1))))
        )
    for face in geometry.faces:
        vertices = np.array((face.a, face.b, face.c))
        normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
        norm = np.linalg.norm(normal)
        if norm > 1e-9:
            triangles.append(
                np.column_stack(
                    (
                        vertices,
                        np.tile(normal / norm, (3, 1)),
                        np.tile(rgb(face.color), (3, 1)),
                    )
                )
            )
    for line in geometry.lines:
        if not show_grid and line.color in {"#283d47", "#42545c"}:
            continue
        if line.width < 4:
            lines.extend(
                (*p, 0.0, 0.0, 0.0, *rgb(line.color)) for p in (line.a, line.b)
            )
            continue
        a, b = np.array(line.a, dtype=float), np.array(line.b, dtype=float)
        axis = b - a
        length = np.linalg.norm(axis)
        if length < 1e-9:
            continue
        axis /= length
        u = np.cross(axis, (0, 0, 1))
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(axis, (0, 1, 0))
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        radius = line.width / (2 * projection.pixels_per_unit)
        rows = []
        for i in range(10):
            n1, n2 = [
                u * math.cos(t) + v * math.sin(t)
                for t in (2 * math.pi * i / 10, 2 * math.pi * (i + 1) / 10)
            ]
            for pos, normal in (
                (a + radius * n1, n1),
                (b + radius * n1, n1),
                (b + radius * n2, n2),
                (a + radius * n1, n1),
                (b + radius * n2, n2),
                (a + radius * n2, n2),
            ):
                rows.append((*pos, *normal, *rgb(line.color)))
        triangles.append(np.array(rows))
    return (
        np.ascontiguousarray(
            np.vstack(triangles) if triangles else np.empty((0, 9)), dtype=np.float32
        ),
        np.ascontiguousarray(np.array(lines).reshape(-1, 9), dtype=np.float32),
    )


class MeshRenderer:
    def __init__(self):
        from OpenGL import GL
        from OpenGL.GL.shaders import compileProgram, compileShader

        self.gl = GL
        self.program = self.vao = self.buffer = None
        try:
            self.program = compileProgram(
                compileShader(VERTEX, GL.GL_VERTEX_SHADER),
                compileShader(FRAGMENT, GL.GL_FRAGMENT_SHADER),
            )
            self.vao = GL.glGenVertexArrays(1)
            self.buffer = GL.glGenBuffers(1)
            GL.glBindVertexArray(self.vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffer)
            for index in range(3):
                GL.glEnableVertexAttribArray(index)
                GL.glVertexAttribPointer(
                    index, 3, GL.GL_FLOAT, False, 36, ctypes.c_void_p(index * 12)
                )
            GL.glBindVertexArray(0)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        except Exception:
            self.close()
            raise

    def draw(self, geometry, projection, size, show_grid):
        GL = self.gl
        triangles, lines = mesh(geometry, projection, show_grid)
        GL.glViewport(0, 0, *size)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glClearDepth(1.0)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glDisable(GL.GL_BLEND)
        GL.glUseProgram(self.program)
        GL.glUniformMatrix4fv(
            GL.glGetUniformLocation(self.program, "projection"),
            1,
            True,
            projection.clip_matrix(),
        )
        GL.glUniformMatrix3fv(
            GL.glGetUniformLocation(self.program, "orientation"),
            1,
            True,
            np.asarray(projection.matrix, dtype=np.float32),
        )
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.buffer)
        try:
            for data, mode in ((triangles, GL.GL_TRIANGLES), (lines, GL.GL_LINES)):
                if len(data):
                    if mode == GL.GL_TRIANGLES:
                        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                        GL.glPolygonOffset(1.0, 1.0)
                    else:
                        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
                    GL.glBufferData(
                        GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STREAM_DRAW
                    )
                    GL.glDrawArrays(mode, 0, len(data))
        finally:
            GL.glBindVertexArray(0)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
            GL.glUseProgram(0)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    def close(self):
        GL = self.gl
        if self.buffer is not None:
            GL.glDeleteBuffers(1, [self.buffer])
            self.buffer = None
        if self.vao is not None:
            GL.glDeleteVertexArrays(1, [self.vao])
            self.vao = None
        if self.program is not None:
            GL.glDeleteProgram(self.program)
            self.program = None
