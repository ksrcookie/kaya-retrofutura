# kaya/ui/commands_palette.py
from PySide6 import QtWidgets, QtCore

class CommandPalette(QtWidgets.QDialog):
    def __init__(self, parent, actions):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.resize(520, 380)
        v = QtWidgets.QVBoxLayout(self)
        self.inp = QtWidgets.QLineEdit()
        self.inp.setPlaceholderText("Type a command…")
        self.list = QtWidgets.QListWidget()
        v.addWidget(self.inp)
        v.addWidget(self.list, 1)
        self.actions = actions
        self._render(self.actions)
        self.inp.textChanged.connect(self._filter)
        self.list.itemActivated.connect(self._run)
        QtWidgets.QShortcut(QtCore.QKeySequence("Escape"), self, self.reject)

    def _render(self, data):
        self.list.clear()
        for title, cb in data:
            it = QtWidgets.QListWidgetItem(title)
            it.setData(32, cb)
            self.list.addItem(it)

    def _filter(self, text):
        t = (text or "").strip().lower()
        if not t:
            self._render(self.actions)
            return
        data = [(a, cb) for (a, cb) in self.actions if t in a.lower()]
        self._render(data)

    def _run(self, item):
        cb = item.data(32)
        try:
            cb()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
        self.accept()


class Toast(QtWidgets.QFrame):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.ToolTip
        )
        l = QtWidgets.QHBoxLayout(self)
        l.setContentsMargins(10, 6, 10, 6)
        l.addWidget(QtWidgets.QLabel(text))
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1800)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)


def show_toast(widget, text):
    t = Toast(widget, text)
    t.adjustSize()

    # widget’ın global sol-üst köşesi:
    top_left_global = widget.mapToGlobal(QtCore.QPoint(0, 0))
    x = top_left_global.x() + widget.width() - t.width() - 24
    y = top_left_global.y() + widget.height() - t.height() - 24

    t.move(x, y)
    t.show()
    t.timer.start()
