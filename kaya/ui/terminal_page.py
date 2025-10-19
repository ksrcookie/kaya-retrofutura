from PySide6 import QtWidgets, QtGui
from ..terminal import parser as tparser
from .. import __version__
WELCOME=f"""╔══════════════════════════════════════════════════════╗
║  K.A.Y.A  —  Kişisel Akıllı Yardımcı Asistan {__version__:<8}║
╚══════════════════════════════════════════════════════╝


"""
class TerminalPage(QtWidgets.QWidget):
    def __init__(self,bus,parent=None):
        super().__init__(parent); self.bus=bus
        v=QtWidgets.QVBoxLayout(self)
        self.out=QtWidgets.QPlainTextEdit(readOnly=True); self.out.setPlainText(WELCOME)
        self.inp=QtWidgets.QLineEdit(placeholderText='kaya> Komut...  örn: new note "ideas/todo" body="..." | mkdir "projects/ego"')
        self.inp.setMinimumHeight(44)
        v.addWidget(self.out); v.addWidget(self.inp)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+Return'), self, self.execute); self.inp.returnPressed.connect(self.execute)
    def log(self,t): self.out.appendPlainText(t)
    def execute(self):
        line=self.inp.text().strip(); 
        if not line: return
        self.log(f'> {line}')
        cmd,p=tparser.parse(line)
        try: 
            res=self.bus.dispatch(cmd,p or {})
            if res: self.log(str(res))
        except Exception as e: self.log(f'Error: {e}')
        finally: self.inp.clear()
