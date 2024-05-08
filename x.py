import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
from qtpy import QtWidgets
from qtpy.QtOpenGLWidgets import QOpenGLWidget

VERTEX_SHADER = """
#version 120
attribute vec2 position;
attribute vec2 texCoords;
varying vec2 outTexCoords;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    outTexCoords = texCoords;
}
"""

# FRAGMENT_SHADER = """
# #version 120
# varying vec2 outTexCoords;
# uniform sampler2D texture1;
# uniform int isGreen;
# void main() {
#     float intensity = texture2D(texture1, outTexCoords).r;
#     if (isGreen == 1) {
#         gl_FragColor = vec4(0.0, intensity, 0.0, 1.0);
#     } else {
#         gl_FragColor = vec4(intensity, 0.0, intensity, 1.0);  // Magenta
#     }
# }
# """

FRAGMENT_SHADER = """
#version 120
varying vec2 outTexCoords;
uniform sampler2D texture1;
uniform sampler1D colormap;
void main() {
    float intensity = texture2D(texture1, outTexCoords).r;
    gl_FragColor = texture1D(colormap, intensity);
}
"""


def compile_shader(source: str, shader_type: int) -> int:
    """Compiles a shader."""
    shader = shaders.compileShader(source, shader_type)
    # Check shader compilation status
    result = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not result:
        raise RuntimeError(glGetShaderInfoLog(shader).decode())
    return shader


class GLWidget2(QOpenGLWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.images: list[np.ndarray] = [
            np.random.randint(0, 256, (256, 256), dtype=np.uint8),
            np.random.randint(0, 256, (256, 256), dtype=np.uint8),
        ]
        self.program = None

    def initializeGL(self) -> None:
        glEnable(GL_BLEND)
        glBlendFunc(GL_ONE, GL_ONE)  # Additive blending

        # Create and compile shaders
        vertex_shader = compile_shader(VERTEX_SHADER, GL_VERTEX_SHADER)
        fragment_shader = compile_shader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)

        # Create program and attach shaders
        self.program = glCreateProgram()
        glAttachShader(self.program, vertex_shader)
        glAttachShader(self.program, fragment_shader)
        glLinkProgram(self.program)

        # Create textures
        self.textures = []
        for data in self.images:
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                GL_LUMINANCE,
                data.shape[1],
                data.shape[0],
                0,
                GL_LUMINANCE,
                GL_UNSIGNED_BYTE,
                data,
            )
            self.textures.append(texture)

    def paintGL(self) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.program)

        # Aspect Ratio of the texture
        data_aspect = self.images[0].shape[1] / self.images[0].shape[0]
        # Aspect Ratio of the window
        window_aspect_ratio = self.width() / self.height()

        # Determine the scale factors based on comparative aspect ratios
        sx, sy = 1.0, 1.0
        if window_aspect_ratio > data_aspect:
            sx = data_aspect / window_aspect_ratio
        else:
            sy = window_aspect_ratio / data_aspect

        # Coordinates to maintain aspect ratio and fill the viewport
        positions = [(-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)]
        texCoords = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

        # Vertex attribute pointers
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, texCoords)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, positions)
        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)

        # Drawing each texture with blending
        for i, texture in enumerate(self.textures):
            glBindTexture(GL_TEXTURE_2D, texture)
            glUniform1i(glGetUniformLocation(self.program, "isGreen"), int(i == 1))
            glDrawArrays(GL_QUADS, 0, 4)

        glDisableVertexAttribArray(0)
        glDisableVertexAttribArray(1)

    def resizeGL(self, width: int, height: int) -> None:
        print("resizeGL", f"{width=}", f"{height=}")
        glViewport(0, 0, width, height)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = GLWidget2()
    window.show()
    app.exec()
