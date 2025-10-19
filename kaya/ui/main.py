# kaya/ui/main.py
from PySide6 import QtWidgets, QtGui
from ..core.config import APP_NAME, FILES, PROJECTS, AGENDA, MEDIA
from ..services.fs_items import FSPaths, FSService
from ..terminal.commands import register_default_commands

from .files_page import FilesPage
from .agenda_page import AgendaPage
from .projects_page import ProjectsPage
from .right_panel import RightPanel
from .terminal_page import TerminalPage
from .commands_palette import CommandPalette, show_toast
from .database_page import DatabasePage          # Database sayfası
from . import theme


class Kaya(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 860)

        self._open_windows = []   # GC olmasın diye açık diyalogları tut

        paths = FSPaths(FILES, PROJECTS, AGENDA, MEDIA)
        self.fs = FSService(paths)

        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        root = QtWidgets.QHBoxLayout(cw); root.setContentsMargins(8,8,8,8); root.setSpacing(8)

        # ---------------- Left Nav ----------------
        left = QtWidgets.QFrame(); left.setMaximumWidth(100); left.setMinimumWidth(88)
        l = QtWidgets.QVBoxLayout(left); l.setSpacing(6)

        self.grp = QtWidgets.QButtonGroup(self); self.grp.setExclusive(True)

        def nb(txt, tip):
            b = QtWidgets.QPushButton(txt)
            b.setToolTip(tip)
            b.setCheckable(True)
            b.setObjectName('navbtn')
            l.addWidget(b); self.grp.addButton(b)
            return b

        b_cons = nb('>_', 'Konsol')
        b_files = nb('▦', 'Dosyalar')
        b_ag   = nb('⌗', 'Ajanda')
        b_proj = nb('⧉', 'Projeler')
        b_db   = nb('⎇', 'Database')
        l.addStretch(1)

        # ---------------- Center Stack ----------------
        self.stack = QtWidgets.QStackedWidget()

        self.p_cons = TerminalPage(self._bus())
        self.p_files = FilesPage(FILES)
        self.p_ag = AgendaPage(self.fs)
        self.p_proj = ProjectsPage(PROJECTS, self.fs)
        self.p_db = DatabasePage(self.fs)

        for p in (self.p_cons, self.p_files, self.p_ag, self.p_proj, self.p_db):
            self.stack.addWidget(p)

        # ---------------- Right Panel ----------------
        self.right = RightPanel(self.fs)
        self.right.setMinimumWidth(280); self.right.setMaximumWidth(340)

        root.addWidget(left)
        root.addWidget(self.stack, 1)
        root.addWidget(self.right)

        # ---------------- Nav Logic ----------------
        b_cons.clicked.connect(lambda: self.stack.setCurrentWidget(self.p_cons))
        b_files.clicked.connect(lambda: self.stack.setCurrentWidget(self.p_files))
        b_ag.clicked.connect(lambda: self.stack.setCurrentWidget(self.p_ag))
        b_proj.clicked.connect(lambda: self.stack.setCurrentWidget(self.p_proj))
        b_db.clicked.connect(lambda: self.stack.setCurrentWidget(self.p_db))

        b_cons.setChecked(True)
        self.stack.setCurrentWidget(self.p_cons)

        # Ctrl+1..5 kısayolları
        for i, (_k, b) in enumerate([(1, b_cons), (2, b_files), (3, b_ag), (4, b_proj), (5, b_db)], start=1):
            QtGui.QShortcut(QtGui.QKeySequence(f'Ctrl+{i}'), self, b.click)

        # ---------------- Command Palette ----------------
        def open_palette():
            acts = [
                ('Go: Console',  lambda: self.stack.setCurrentWidget(self.p_cons)),
                ('Go: Files',    lambda: self.stack.setCurrentWidget(self.p_files)),
                ('Go: Agenda',   lambda: self.stack.setCurrentWidget(self.p_ag)),
                ('Go: Projects', lambda: self.stack.setCurrentWidget(self.p_proj)),
                ('Go: Database', lambda: self.stack.setCurrentWidget(self.p_db)),
            ]
            CommandPalette(self, acts).exec()

        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+P'), self, open_palette)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+K'), self, open_palette)

        # ---------------- Theme ----------------
        theme.apply(self, 'green')
        # show_toast(self,'RetroFuturistic tema yüklendi')

    def _bus(self):
        class Bus:
            def __init__(self, fs):
                self.h = {}; self.fs = fs
            def register(self, n, f):
                self.h[n] = f
            def dispatch(self, n, p):
                if n not in self.h:
                    raise ValueError(f'Unknown command: {n}')
                return self.h[n](p)

        bus = Bus(self.fs)

        # Komutları kaydet (ana pencere referansı veriyoruz)
        from ..terminal.commands import register_default_commands
        register_default_commands(bus, self.fs, self)




       # ---- UI hook: terminalden proje penceresi aç (merkezi sayfayı değiştirme) ----
        def ui_project_open(payload):
            from pathlib import Path
            from PySide6 import QtCore
            dpath = Path(payload.get("path", ""))

            if not dpath.exists():
                return "Path not found."

            # 1) Tercih: projects_page içindeki ProjectDetail'i doğrudan pencere olarak aç
            try:
                from .projects_page import ProjectDetail
                dlg = ProjectDetail(dpath)
                dlg.setWindowFlag(QtCore.Qt.Window, True)     # bağımsız pencere
                dlg.setWindowModality(QtCore.Qt.NonModal)
                dlg.show()
                # referansı sakla (GC kapanmasın)
                try:
                    self._open_windows.append(dlg)
                except Exception:
                    pass
                return f'Opening "{dpath.name}"…'
            except Exception as e1:
                # 2) Yedek: ayrı ProjectWindow sınıfın varsa onu dene
                try:
                    from .project_window import ProjectWindow
                    dlg = ProjectWindow(dpath, self.fs, self)
                    dlg.setModal(False)
                    dlg.show()
                    try:
                        self._open_windows.append(dlg)
                    except Exception:
                        pass
                    return f'Opening "{dpath.name}"…'
                except Exception as e2:
                    return f"Open failed: {e1} / {e2}"

        bus.register("ui.project_open", ui_project_open)
# ---------------------------------------------------------------------------


        return bus





def run():
    app = QtWidgets.QApplication([])
    w = Kaya()
    w.show()
    app.exec()
