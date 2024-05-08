import numpy as np
from OpenGL.GL import *
from qtpy import QtWidgets
from qtpy.QtOpenGLWidgets import QOpenGLWidget


class GLWidget(QOpenGLWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.data = np.random.randint(0, 256, (256, 256), dtype=np.uint8)

    def initializeGL(self) -> None:
        glEnable(GL_TEXTURE_2D)
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        # Assuming the data is grayscale and should use a single-channel texture format
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_LUMINANCE,
            self.data.shape[1],
            self.data.shape[0],
            0,
            GL_LUMINANCE,
            GL_UNSIGNED_BYTE,
            self.data,
        )

    def paintGL(self) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glBindTexture(GL_TEXTURE_2D, self.texture)

        # Compute scale to maintain aspect ratio
        aspect_ratio = self.data.shape[1] / self.data.shape[0]
        win_aspect_ratio = self.width() / self.height()
        scale_x, scale_y = 1.0, 1.0
        if win_aspect_ratio > aspect_ratio:
            scale_x = aspect_ratio / win_aspect_ratio
        else:
            scale_y = win_aspect_ratio / aspect_ratio

        print(scale_x, scale_y)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(-scale_x, -scale_y)
        glTexCoord2f(1, 0)
        glVertex2f(scale_x, -scale_y)
        glTexCoord2f(1, 1)
        glVertex2f(scale_x, scale_y)
        glTexCoord2f(0, 1)
        glVertex2f(-scale_x, scale_y)
        glEnd()

    def resizeGL(self, width: int, height: int) -> None:
        glViewport(0, 0, width, height)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = GLWidget()
    window.show()
    app.exec()
