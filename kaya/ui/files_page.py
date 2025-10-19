from PySide6 import QtWidgets, QtCore
from pathlib import Path
import shutil
import time

# ---- Basit editör: sağ tıkta "Resim Ekle…" + drag&drop görüntü kopyalama ----
class ImagePlain(QtWidgets.QPlainTextEdit):
    def __init__(self, insert_image_cb, parent=None):
        super().__init__(parent)
        self._insert_image_cb = insert_image_cb
        self.setAcceptDrops(True)

    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        m.addSeparator()
        act = m.addAction("Resim Ekle…")
        act.triggered.connect(self._open_image_dialog)
        m.exec(e.globalPos())

    def _open_image_dialog(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Resim seç", "", "Görseller (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )
        if fn:
            self._insert_image_cb(Path(fn))

    # Drag & drop:
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                p = Path(u.toLocalFile())
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
                    self._insert_image_cb(p)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class FilesPage(QtWidgets.QWidget):
    def __init__(self, root: Path, parent=None):
        super().__init__(parent)
        self.root = root

        outer = QtWidgets.QVBoxLayout(self)

        # Üst araç çubuğu
        tb = QtWidgets.QHBoxLayout()
        self.b_nf = QtWidgets.QToolButton(text='NF')   # New Folder (root)
        self.b_nn = QtWidgets.QToolButton(text='NN')   # New Note (root)
        self.b_op = QtWidgets.QToolButton(text='OP')   # Open selected
        for b in (self.b_nf, self.b_nn, self.b_op):
            b.setObjectName('navbtn')
        [tb.addWidget(b) for b in (self.b_nf, self.b_nn, self.b_op)]
        tb.addStretch(1)
        outer.addLayout(tb)

        # Sol (ağaç) + Sağ (breadcrumb + editör)
        lay = QtWidgets.QHBoxLayout()
        outer.addLayout(lay, 1)

        # Model & tree
        self.tree = QtWidgets.QTreeView()
        self.model = QtWidgets.QFileSystemModel(self)
        self.model.setRootPath(str(root))
        self.model.setReadOnly(False)
        self.model.setNameFilters(['*.md', '*.txt', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.pdf', '*'])
        self.model.setNameFilterDisables(False)

        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(root)))
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.tree.setColumnWidth(0, 320)

        # Sağ taraf
        right = QtWidgets.QVBoxLayout()
        self.bc = QtWidgets.QLabel('—')
        self.bc.setObjectName('accent')

        self.ed = ImagePlain(self._insert_image_into_note)
        # (kritik) placeholder kurucuda değil, property olarak veriyoruz
        self.ed.setPlaceholderText('Not içeriği... (.md düzenlenir)')

        right.addWidget(self.bc)
        right.addWidget(self.ed, 1)

        lay.addWidget(self.tree, 1)
        c = QtWidgets.QWidget(); c.setLayout(right)
        lay.addWidget(c, 2)

        # Bağlantılar
        self.tree.selectionModel().currentChanged.connect(self.on_sel)
        self.ed.textChanged.connect(self._deb)

        self._p = None
        self._tm = QtCore.QTimer(self)
        self._tm.setInterval(600)
        self._tm.setSingleShot(True)
        self._tm.timeout.connect(self._save)

        # Ağaç: sağ tık menüsü (boş alan + öğe)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)

        # Üst butonlar
        self.b_nf.clicked.connect(self.new_folder_root)
        self.b_nn.clicked.connect(self.new_note_root)
        self.b_op.clicked.connect(self.open_sel)

        # Tek tıkla klasör aç/kapa
        self.tree.clicked.connect(self.toggle_dir)

    # ---------- Yardımcılar ----------
    def _assets_dir(self) -> Path:
        d = self.root / "assets"
        d.mkdir(exist_ok=True)
        return d

    def _slug(self, s: str) -> str:
        bad = '<>:"/\\|?*'
        for ch in bad:
            s = s.replace(ch, '_')
        s = s.strip()
        return s or str(int(time.time()))

    # ---------- Klasör toggle ----------
    def toggle_dir(self, idx):
        if self.model.isDir(idx):
            self.tree.setExpanded(idx, not self.tree.isExpanded(idx))

    # ---------- Root butonları ----------
    def new_folder_root(self):
        name, ok = QtWidgets.QInputDialog.getText(self, 'New Folder (ROOT)', 'Name:')
        if ok and name.strip():
            (self.root / self._slug(name)).mkdir(parents=True, exist_ok=True)

    def new_note_root(self):
        name, ok = QtWidgets.QInputDialog.getText(self, 'New Note (ROOT)', 'Name (without .md):')
        if ok and name.strip():
            (self.root / f"{self._slug(name)}.md").write_text('', encoding='utf-8')

    def open_sel(self):
        idx = self.tree.currentIndex()
        if idx.isValid():
            self.on_sel(idx, None)

    # ---------- Ağaç sağ tık menüsü ----------
    def _tree_menu(self, pos: QtCore.QPoint):
        ix = self.tree.indexAt(pos)
        gpos = self.tree.viewport().mapToGlobal(pos)
        m = QtWidgets.QMenu(self)

        if not ix.isValid():
            # Boş alan: root'a oluştur
            m.addAction('Yeni Not (root)', self.new_note_root)
            m.addAction('Yeni Klasör (root)', self.new_folder_root)
            m.exec(gpos)
            return

        p = Path(self.model.filePath(ix))
        is_dir = p.is_dir()

        if is_dir:
            m.addAction('Bu klasörde Yeni Not', lambda: self._create_note_in(p))
            m.addAction('Bu klasörde Yeni Klasör', lambda: self._create_folder_in(p))
            m.addSeparator()

        a_ren = m.addAction('Yeniden adlandır (F2)')
        a_del = m.addAction('Sil')

        act = m.exec(gpos)
        if not act:
            return
        if act == a_ren:
            self.tree.edit(ix)
        elif act == a_del:
            self._delete_path(p)

    def _create_note_in(self, folder: Path):
        name, ok = QtWidgets.QInputDialog.getText(self, 'Yeni Not', 'Name (without .md):')
        if ok and name.strip():
            (folder / f"{self._slug(name)}.md").write_text('', encoding='utf-8')

    def _create_folder_in(self, folder: Path):
        name, ok = QtWidgets.QInputDialog.getText(self, 'Yeni Klasör', 'Name:')
        if ok and name.strip():
            (folder / self._slug(name)).mkdir(parents=True, exist_ok=True)

    def _delete_path(self, p: Path):
        if not p.exists():
            return
        what = "klasör" if p.is_dir() else "dosya"
        if QtWidgets.QMessageBox.question(
            self, "Sil", f"Seçilen {what} silinsin mi?\n{p.name}",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) != QtWidgets.QMessageBox.Yes:
            return
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink(missing_ok=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Silinemedi:\n{e}")

    # ---------- Editor: resim ekleme ----------
    def _insert_image_into_note(self, src: Path):
        try:
            assets = self._assets_dir()
            dst = assets / src.name
            i = 1
            while dst.exists():
                dst = assets / f"{src.stem}_{i}{src.suffix}"
                i += 1
            dst.write_bytes(src.read_bytes())
            cur = self.ed.textCursor()
            cur.insertText(f"![{dst.stem}](assets/{dst.name})\n")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Hata", f"Resim eklenemedi:\n{e}")

    # ---------- Seçim ve kayıt ----------
    def on_sel(self, cur, _):
        p = Path(self.model.filePath(cur))
        try:
            rel = p.relative_to(self.root)
        except Exception:
            rel = p
        self.bc.setText(str(rel))
        self._p = None
        self.ed.blockSignals(True)
        try:
            if p.is_file() and p.suffix.lower() in ('.md', '.txt'):
                self.ed.setPlainText(p.read_text(encoding='utf-8'))
                self._p = p
            else:
                self.ed.setPlainText('')
        except Exception as e:
            self.ed.setPlainText(f'Error: {e}')
        self.ed.blockSignals(False)

    def _deb(self):
        if self._p:
            self._tm.start()

    def _save(self):
        if not self._p:
            return
        try:
            self._p.write_text(self.ed.toPlainText(), encoding='utf-8')
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Save Error', str(e))
