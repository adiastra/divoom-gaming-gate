# designer/shape_item.py
from PyQt5.QtWidgets import QGraphicsObject, QGraphicsRectItem, QGraphicsTextItem
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QRectF, pyqtSignal

class ShapeItem(QGraphicsObject):
    # signal emitted when the model shape has been interactively edited
    shapeChanged = pyqtSignal()

    def __init__(self, model, *args):
        super().__init__(*args)
        self.model = model
        self.setFlags(
            QGraphicsObject.ItemIsSelectable |
            QGraphicsObject.ItemIsMovable |
            QGraphicsObject.ItemSendsGeometryChanges
        )
        # TODO: add resize handles here

    def boundingRect(self):
        # return the rectangle covering the shape + handles
        return self.model.geom

    def paint(self, painter: QPainter, option, widget):
        pen = self.model.pen
        painter.setPen(pen)
        if self.model.kind == 'rect':
            painter.drawRect(self.model.geom)
        elif self.model.kind == 'ellipse':
            painter.drawEllipse(self.model.geom)
        elif self.model.kind == 'line':
            # line model.geom is QLineF
            painter.drawLine(self.model.geom)
        elif self.model.kind == 'text':
            painter.setFont(self.model.font)
            painter.setPen(self.model.pen.color())
            painter.drawText(self.model.geom.topLeft(), self.model.text)

    def itemChange(self, change, value):
        # catch move events
        from PyQt5.QtCore import QGraphicsItem
        if change == QGraphicsItem.ItemPositionHasChanged:
            # update model.geom accordingly
            new_pos = self.pos()
            # for rect/ellipse: translate geom by delta
            # TODO: adjust model.geom based on new_pos
            self.shapeChanged.emit()
        return super().itemChange(change, value)
