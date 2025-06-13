# designer/shape_model.py

from PyQt5.QtCore import QRectF, QPointF, QLineF
from PyQt5.QtGui import QPen, QBrush, QFont

class ShapeModel:
    def __init__(self, kind, geom, pen, text=""):
        """
        kind: 'rect', 'ellipse', 'line', 'text'
        geom: QRectF for rect/ellipse, QLineF for line, QPointF for text position
        pen: QPen instance
        text: string for text content
        """
        self.kind = kind
        self.geom = geom
        self.pen  = pen
        self.text = text
        self.font = QFont() if kind == 'text' else None

    def clone(self):
        # make deep copies of Qt objects explicitly
        new_pen = QPen(self.pen)
        new_brush = QBrush(self.pen.brush()) if self.kind != 'text' else None
        if self.kind in ('rect', 'ellipse'):
            new_geom = QRectF(self.geom)
        elif self.kind == 'line':
            new_geom = QLineF(self.geom)
        else:  # text
            new_geom = QPointF(self.geom)
        new = ShapeModel(self.kind, new_geom, new_pen, text=self.text)
        if self.font:
            new.font = QFont(self.font)
        return new
