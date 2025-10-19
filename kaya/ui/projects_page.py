from __future__ import annotations
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
import json, shutil, datetime

# --- Simple FlowLayout (Qt örneklerinden uyarlanmış) ---
class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, hspacing=22, vspacing=16):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self._h = hspacing
        self._v = vspacing

    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._do_layout(QtCore.QRect(0,0,w,0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, False)
    def sizeHint(self): return self.minimumSize()

    def minimumSize(self):
        s = QtCore.QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        s += QtCore.QSize(2*m.left(), 2*m.top())
        return s

    def _do_layout(self, rect, test_only):
        x = rect.x() + self.contentsMargins().left()
        y = rect.y() + self.contentsMargins().top()
        line_height = 0
        right = rect.right() - self.contentsMargins().right()

        for it in self._items:
            w = it.sizeHint().width()
            h = it.sizeHint().height()
            if x + w > right and line_height > 0:
                x = rect.x() + self.contentsMargins().left()
                y += line_height + self._v
                line_height = 0
            if not test_only:
                it.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), it.sizeHint()))
            x += w + self._h
            line_height = max(line_height, h)
        return y + line_height - rect.y()


# ----------------- küçük yardımcılar -----------------
def now_iso(): return datetime.datetime.now().isoformat(timespec="seconds")
def read_json(p: Path, default: dict):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return dict(default)
def write_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

DEFAULT_META = {
    "name": "", "type": "standard", "status": "active",
    "tags": [], "created_at": "", "updated_at": "",
    "color": "", "progress": 0, "pinned": False
}
TYPE_COLORS = {
    "standard":   "#00C2C7",  # cyan
    "engineering":"#D97A00",  # amber
    "edu":        "#5BA3FF",  # azure
    "research":   "#2AB39A",  # teal
    "custom":     "#B38BFA",  # purple
}
TYPE_ORDER = ["standard","engineering","edu","research","custom"]

# ----------------- Proje detay -----------------
class ProjectDetail(QtWidgets.QWidget):
    back_requested = QtCore.Signal()
    def __init__(self, proj_dir: Path, meta: dict, parent=None):
        super().__init__(parent)
        self.proj_dir = proj_dir; self.meta = meta
        outer = QtWidgets.QVBoxLayout(self); outer.setContentsMargins(8,8,8,8); outer.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        back = QtWidgets.QToolButton(text="← Back"); back.setObjectName("navbtn"); back.clicked.connect(self.back_requested.emit)
        title = QtWidgets.QLabel(meta.get("name") or proj_dir.name)
        f = title.font(); f.setBold(True); f.setPointSizeF(f.pointSizeF()+2); title.setFont(f)
        top.addWidget(back); top.addSpacing(8); top.addWidget(title); top.addStretch(1)
        outer.addLayout(top)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.tree = QtWidgets.QTreeView()
        self.model = QtWidgets.QFileSystemModel(self)
        self.model.setRootPath(str(proj_dir)); self.model.setReadOnly(False)
        self.tree.setModel(self.model); self.tree.setRootIndex(self.model.index(str(proj_dir)))
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.tree.setColumnWidth(0, 260)

        self.editor = QtWidgets.QPlainTextEdit(placeholderText="Proje notu… (overview.md)")
        self._tm = QtCore.QTimer(self); self._tm.setInterval(600); self._tm.setSingleShot(True)
        self._tm.timeout.connect(self._save)
        self._note_path = proj_dir/"notes"/"overview.md"
        self._note_path.parent.mkdir(parents=True, exist_ok=True)
        if self._note_path.exists():
            try: self.editor.setPlainText(self._note_path.read_text(encoding="utf-8"))
            except Exception: pass
        self.editor.textChanged.connect(lambda: self._tm.start())

        split.addWidget(self.tree); split.addWidget(self.editor)
        split.setStretchFactor(0, 2); split.setStretchFactor(1, 3)
        outer.addWidget(split, 1)

    def _save(self):
        try: self._note_path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except Exception: pass

# ----------------- Tür klasör karosu (Overview / klasör grid) -----------------
class TypeTile(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)  # type key

    def __init__(self, type_key: str, count: int, parent=None):
        super().__init__(parent)
        self.type_key = type_key
        self.count = count

        # Daha kompakt karo (küçültüldü)
        self._w, self._h = 168, 118
        self.setFixedSize(self._w, self._h)

        # İmleç ok (el yok)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setObjectName("typetile")
        self.setToolTip(type_key.title())

    def sizeHint(self):
        return QtCore.QSize(self._w, self._h)

    def paintEvent(self, e: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)

        r = self.rect().adjusted(10, 8, -10, -10)

        accent   = QtGui.QColor(TYPE_COLORS.get(self.type_key, "#00C2C7"))
        neon     = QtGui.QColor(accent).lighter(155)
        dim      = QtGui.QColor(14, 20, 18)     # koyu iç dolgu
        faint    = QtGui.QColor(0, 0, 0, 90)    # hafif gölge
        labelfg  = QtGui.QColor("#A0D8C8")

        # ---------- Başlık (nefes payı ↑) ----------
        title_rect = QtCore.QRect(r.left(), r.top(), r.width()-36, 18)
        f = self.font(); f.setBold(True); p.setFont(f)
        p.setPen(neon)
        p.drawText(title_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.type_key.title())

        # Sayaç kapsülü
        badge = QtCore.QRect(r.right()-20, r.top()+2, 18, 12)
        p.setPen(QtGui.QPen(accent, 1))
        p.setBrush(accent.darker(235))
        p.drawRoundedRect(badge, 3, 3)
        p.setPen(labelfg)
        p.drawText(badge, QtCore.Qt.AlignCenter, str(self.count))

        # ---------- Minimal 80s-tech klasör ----------
        # İkon alanı başlığın ALTINDAN başlasın (çarpışmasın)
        icon = QtCore.QRect(r.left()+10, r.top()+28, r.width()-20, r.height()-42)

        # Tab: tek çizgisel parça (eğimli, neon hat)
        tab_h = 10
        path_tab = QtGui.QPainterPath()
        path_tab.moveTo(icon.left()+10, icon.top()-tab_h)
        path_tab.lineTo(icon.left()+54, icon.top()-tab_h)
        path_tab.lineTo(icon.left()+44, icon.top())
        path_tab.lineTo(icon.left()+10, icon.top())
        path_tab.closeSubpath()

        # Gövde: ince neon kontur + çok koyu iç
        body = QtCore.QRect(icon.left(), icon.top(), icon.width(), icon.height())
        path_body = QtGui.QPainterPath()
        path_body.addRect(QtCore.QRectF(body))

        # Çok hafif gölge (old-school CRT hissi)
        p.fillPath(path_body.translated(2, 2), faint)

        # İç dolgular
        p.fillPath(path_body, dim)
        p.fillPath(path_tab,  dim.darker(115))

        # Çizgiler (neon)
        p.setPen(QtGui.QPen(accent, 1))
        p.drawPath(path_body)
        p.drawPath(path_tab)

        # Üst hat parıltısı (çok hafif)
        p.setPen(QtGui.QPen(neon, 1))
        p.drawLine(body.left()+1, body.top()+1, body.right()-1, body.top()+1)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.type_key)
        super().mousePressEvent(e)




# ----------------- All listesi (tek satır görünüm) -----------------
class AllList(QtWidgets.QTableWidget):
    activated = QtCore.Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Type", "Status", "Updated"])
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)

        # Sütun davranışı
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)            # Name
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)   # Type
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)   # Status
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)   # Updated

        self.setStyleSheet("""
            QTableWidget {
                alternate-background-color: rgba(0,255,120,18);
            }
            QTableWidget::item:selected { background: rgba(0,255,120,55); }
        """)

        self.itemDoubleClicked.connect(self._open)

    def _mk(self, text: str, align=QtCore.Qt.AlignLeft):
        it = QtWidgets.QTableWidgetItem(text)
        it.setTextAlignment(align | QtCore.Qt.AlignVCenter)
        return it

    def populate(self, items: list[tuple[Path, dict]]):
        self.setRowCount(0)
        # Varsayılan sıralama: Updated desc
        items = sorted(items, key=lambda x: x[1].get("updated_at",""), reverse=True)

        for d, m in items:
            r = self.rowCount()
            self.insertRow(r)
            name = m.get("name") or d.name
            typ  = m.get("type", "standard")
            st   = m.get("status", "active")
            upd  = m.get("updated_at") or m.get("created_at") or ""

            self.setItem(r, 0, self._mk(name, QtCore.Qt.AlignLeft))
            self.setItem(r, 1, self._mk(typ,  QtCore.Qt.AlignCenter))
            self.setItem(r, 2, self._mk(st,   QtCore.Qt.AlignCenter))
            self.setItem(r, 3, self._mk(upd,  QtCore.Qt.AlignRight))

            # path’i ilk hücreye sakla
            self.item(r, 0).setData(QtCore.Qt.UserRole, d)

        # İlk sütuna göre seçim okunaklı olsun
        if self.rowCount():
            self.selectRow(0)

    def _open(self, item: QtWidgets.QTableWidgetItem):
        d = self.item(item.row(), 0).data(QtCore.Qt.UserRole)
        if isinstance(d, Path):
            self.activated.emit(d)


# ----------------- Ana: ProjectsPage (Overview/All + Overview-List) -----------------
class ProjectsPage(QtWidgets.QWidget):
    def __init__(self, projects_dir: Path, fs=None, parent=None):
        super().__init__(parent)
        self.projects_dir = projects_dir; self.fs = fs
        self.templates_dir = (projects_dir.parent / "templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        outer = QtWidgets.QVBoxLayout(self); outer.setContentsMargins(8,8,8,8); outer.setSpacing(8)
        # header
        hdr = QtWidgets.QHBoxLayout()
        self.btn_over = QtWidgets.QToolButton(text="Overview")
        self.btn_all  = QtWidgets.QToolButton(text="All")
        for b in (self.btn_over, self.btn_all):
            b.setCheckable(True); b.setAutoExclusive(True); b.setObjectName("navbtn")
        self.btn_over.setChecked(True)
        self.search = QtWidgets.QLineEdit(placeholderText="Search (Ctrl+K)")
        self.search.setClearButtonEnabled(True)
        self.new_btn = QtWidgets.QToolButton(text="New Project"); self.new_btn.setObjectName("navbtn")
        hdr.addWidget(self.btn_over); hdr.addWidget(self.btn_all); hdr.addSpacing(10)
        hdr.addWidget(self.search, 1); hdr.addSpacing(10); hdr.addWidget(self.new_btn)
        outer.addLayout(hdr)

        # ana stack: Overview / All
        self.stack = QtWidgets.QStackedWidget(); outer.addWidget(self.stack, 1)

        # ---- OVERVIEW STACK ----
        self.over_stack = QtWidgets.QStackedWidget()

        # 0) Klasör grid (overview ana ekran)
        self.page_over_grid = QtWidgets.QScrollArea()
        self.page_over_grid.setWidgetResizable(True)

        self._grid_wrap = QtWidgets.QWidget()
        # Sadece FlowLayout kullan; _grid_wrap'a başka layout koyma
        self._flow = FlowLayout(hspacing=22, vspacing=14)  # yukarıda tanımladığın FlowLayout
        self._grid_wrap.setLayout(self._flow)
        self._grid_wrap.setContentsMargins(24, 10, 24, 20)
        self.page_over_grid.setWidget(self._grid_wrap)

        # 1) Tür listesi (overview içindeki alt sayfa)
        self.page_over_list = QtWidgets.QWidget()
        ovl = QtWidgets.QVBoxLayout(self.page_over_list)
        ovl.setContentsMargins(0, 0, 0, 0)
        ovl.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        self.back_btn = QtWidgets.QToolButton(text="← Back"); self.back_btn.setObjectName("navbtn")
        self.type_title = QtWidgets.QLabel("Type"); f=self.type_title.font(); f.setBold(True); self.type_title.setFont(f)
        top.addWidget(self.back_btn); top.addSpacing(8); top.addWidget(self.type_title); top.addStretch(1)
        ovl.addLayout(top)
        self.type_list = AllList(); ovl.addWidget(self.type_list, 1)

        self.over_stack.addWidget(self.page_over_grid)
        self.over_stack.addWidget(self.page_over_list)



        # ---- ALL tek satır listesi ----
        self.page_all = QtWidgets.QWidget()
        all_l = QtWidgets.QVBoxLayout(self.page_all); all_l.setContentsMargins(0,0,0,0); all_l.setSpacing(6)
        self.all_list = AllList(); all_l.addWidget(self.all_list, 1)

        self.stack.addWidget(self.over_stack)
        self.stack.addWidget(self.page_all)

        # All list ve type list için odak halkasını ve otomatik seçimi kapat
        for view in (self.all_list, self.type_list):
            view.setFocusPolicy(QtCore.Qt.NoFocus)                 # kırmızı/odak konturunu engeller
            sel_model = view.selectionModel()
            if sel_model: sel_model.clear()                        # varsa ilk seçimi temizle

        self.all_list.clearSelection()
        self.type_list.clearSelection()


        # signals
        self.btn_over.clicked.connect(lambda: self._show_overview())
        self.btn_all.clicked.connect(lambda: self._show_all())
        self.new_btn.clicked.connect(self.new_project)
        self.search.textChanged.connect(self._refresh)
        self.back_btn.clicked.connect(lambda: self.over_stack.setCurrentIndex(0))
        self.type_list.activated.connect(self.open_project)
        self.all_list.activated.connect(self.open_project)

        self._refresh()

    # ------------- tarama -------------
    def _scan_projects(self):
        out=[]
        if not self.projects_dir.exists(): return out
        for d in sorted(self.projects_dir.iterdir()):
            if not d.is_dir(): continue
            meta=read_json(d/"project.json", DEFAULT_META)
            if not meta.get("name"): meta["name"]=d.name
            if not meta.get("created_at"): meta["created_at"]=now_iso()
            if not meta.get("updated_at"): meta["updated_at"]=meta["created_at"]
            out.append((d,meta))
        return out

    # ------------- UI yenile -------------
    def _refresh(self):
        # --- Projeleri tara + arama filtresi ---
        projects = self._scan_projects()
        q = (self.search.text() or "").strip().lower()
        if q:
            projects = [
                (d, m) for d, m in projects
                if q in (m.get("name", "") + d.name).lower()
                or q in " ".join(m.get("tags", [])).lower()
            ]

        # --- Sayım ve bucket'lar (türe göre gruplama) ---
        counts  = {t: 0 for t in TYPE_ORDER}
        buckets = {t: [] for t in TYPE_ORDER}
        for d, m in projects:
            t = m.get("type", "standard")
            counts[t] = counts.get(t, 0) + 1
            buckets.setdefault(t, []).append((d, m))

        # --- OVERVIEW / GRID (FlowLayout) temizle + doldur ---
        # (Artık self._grid yok; self._flow kullanıyoruz)
        while self._flow.count():
            it = self._flow.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        for t in TYPE_ORDER:
            tile = TypeTile(t, counts.get(t, 0))
            # tıklayınca overview içindeki liste sayfasına geç
            # (bucket'ı o anki listedeki filtreye göre iletelim)
            tile.clicked.connect(lambda _, tt=t, b=list(buckets.get(t, [])): self._open_type_list(tt, b))
            self._flow.addWidget(tile)

        # --- ALL sekmesi: tek satır liste ---
        self._populate_list(self.all_list, projects)

        # --- Overview 'type list' alt sayfası açık ise ve arama var ise orayı da yenile ---
        if self.over_stack.currentIndex() == 1:
            current_type = self.type_title.text().strip().lower()
            typed = buckets.get(current_type, [])
            if q:
                typed = [
                    (d, m) for d, m in typed
                    if q in (m.get("name", "") + d.name).lower()
                    or q in " ".join(m.get("tags", [])).lower()
                ]
            self._populate_list(self.type_list, typed)


    def _populate_list(self, tbl: AllList, items: list[tuple[Path,dict]]):
        tbl.populate(sorted(items, key=lambda x: x[1].get("updated_at",""), reverse=True))

    def _clear_grid(self, grid: QtWidgets.QGridLayout):
        for i in reversed(range(grid.count())):
            it=grid.itemAt(i); w=it.widget()
            grid.removeItem(it)
            if w: w.setParent(None); w.deleteLater()

    # ------------- görünüm geçişleri -------------
    def _show_overview(self):
        self.btn_over.setChecked(True)
        self.stack.setCurrentIndex(0)           # ana: overview
        self.over_stack.setCurrentIndex(0)      # alt: klasörler
        self._refresh()

    def _show_all(self):
        self.btn_all.setChecked(True)
        self.stack.setCurrentIndex(1)           # ALL her zaman tüm projeleri gösterir
        self._refresh()

    def _open_type_list(self, type_key: str, items: list[tuple[Path,dict]]):
        self.type_title.setText(type_key.title())
        self._populate_list(self.type_list, items)
        self.over_stack.setCurrentIndex(1)

    # ------------- yeni proje -------------
    def new_project(self):
        dlg = NewProjectDialog(self.projects_dir, self.templates_dir, self)
        if dlg.exec()!=QtWidgets.QDialog.Accepted: return
        data=dlg.result_data(); name=data["name"]
        if not name:
            QtWidgets.QMessageBox.warning(self,"New Project","Name is required."); return
        pdir=self.projects_dir/name
        if pdir.exists():
            QtWidgets.QMessageBox.warning(self,"New Project","A project with that name already exists."); return
        use_template=data["use_template"]
        pdir.mkdir(parents=True, exist_ok=True)
        tdir=self.templates_dir/data["type"]
        if use_template and tdir.exists(): self._copy_tree(tdir,pdir)

        meta=dict(DEFAULT_META); meta["name"]=name; meta["type"]=data["type"]
        meta["created_at"]=now_iso(); meta["updated_at"]=meta["created_at"]
        write_json(pdir/"project.json", meta)
        (pdir/"notes").mkdir(exist_ok=True)
        ov=pdir/"notes"/"overview.md"
        if not ov.exists(): ov.write_text(f"# {name}\n\n> Project created {meta['created_at']}\n", encoding="utf-8")
        self._refresh()

    def _copy_tree(self, src: Path, dst: Path):
        for item in src.rglob("*"):
            rel=item.relative_to(src); target=dst/rel
            if item.is_dir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    # ------------- proje aç -------------
    def open_project(self, proj_dir: Path):
        meta=read_json(proj_dir/"project.json", DEFAULT_META)
        detail=ProjectDetail(proj_dir, meta, self)
        dlg=QtWidgets.QDialog(self); dlg.setWindowTitle(meta.get("name") or proj_dir.name)
        lay=QtWidgets.QVBoxLayout(dlg); lay.setContentsMargins(0,0,0,0); lay.addWidget(detail)
        detail.back_requested.connect(dlg.reject)
        dlg.resize(900,600); dlg.exec()
        self._refresh()

# ----------------- Yeni Proje Dialog -----------------
class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, projects_dir: Path, templates_dir: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.projects_dir=projects_dir; self.templates_dir=templates_dir
        v=QtWidgets.QVBoxLayout(self)
        form=QtWidgets.QFormLayout()
        self.name=QtWidgets.QLineEdit(placeholderText="Project name")
        self.type=QtWidgets.QComboBox(); self.type.addItems(TYPE_ORDER)
        self.chk_template=QtWidgets.QCheckBox("Create from template (if available)")
        form.addRow("Name", self.name); form.addRow("Type", self.type); form.addRow("", self.chk_template)
        v.addLayout(form)
        btns=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); v.addWidget(btns)
    def result_data(self):
        return {"name": self.name.text().strip(),
                "type": self.type.currentText(),
                "use_template": self.chk_template.isChecked()}
