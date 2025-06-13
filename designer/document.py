# designer/document.py

from .shape_model import ShapeModel

class Frame:
    def __init__(self):
        self.shapes = []  # list of ShapeModel

class DesignerDocument:
    def __init__(self):
        self.frames = [Frame()]
        self.current = 0

    @property
    def current_frame(self):
        return self.frames[self.current]

    def add_blank_frame(self):
        """Insert an empty frame after the current one and advance to it."""
        self.frames.insert(self.current + 1, Frame())
        self.current += 1

    def clone_frame(self):
        """
        Create a new frame by cloning each ShapeModel from the current frame
        using its clone() method, avoiding deepcopy on Qt objects.
        """
        src = self.current
        new_frame = Frame()
        for shape in self.frames[src].shapes:
            new_frame.shapes.append(shape.clone())
        self.frames.insert(src + 1, new_frame)
        self.current += 1

    def goto_frame(self, idx):
        if 0 <= idx < len(self.frames):
            self.current = idx
