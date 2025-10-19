# kaya/ui/database_page.py
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from .db_service import DBService
from .person_card import PersonCard

# --- Modül tipleri (ana hub) ---
TYPE_ORDER = [
    ("people", "People"),
    ("events", "Events"),
    ("orgs",   "Orgs"),
    ("places", "Places"),
    ("media",  "Media"),
    ("systems","Systems"),
]

TYPE_ICONS = {
    "people":  "👤",
    "events":  "✦",
    "orgs":    "⛭",
    "places":  "🗺",
    "media":   "▶",
    "systems": "⚙",
}

# --- Retro mini kart (FlowLayout yok; painter’lı kompakt kutu) ---
class HubTile(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)

    def __init__(self, type_key: str, label: str, parent=None):
        super().__init__(parent)
        self.type_key = type_key
        self.label = label
        self.setObjectName("hubtile")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(200, 120)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.type_key)
        super().mouseReleaseEvent(e)

    def paintEvent(self, e: QtGui.QPaintEvent):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        r = self.rect().adjusted(6, 6, -6, -6)

        accent = QtGui.QColor("#00C48A")  # tema ile override edilir
        p.setPen(QtGui.QPen(accent, 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRect(r)

        # Başlık bandı
        band = QtCore.QRect(r.left()+8, r.top()+8, 112, 18)
        p.fillRect(band, QtGui.QColor(0, 0, 0, 60))
        f = p.font(); f.setBold(True); p.setFont(f)
        p.setPen(accent)
        p.drawText(band, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.label)

        # İkon kutusu
        icon_box = QtCore.QRect(r.left()+16, r.top()+38, r.width()-32, r.height()-54)
        shadow = icon_box.adjusted(2, 2, 2, 2)
        p.fillRect(shadow, QtGui.QColor(0, 0, 0, 80))
        p.fillRect(icon_box, QtGui.QColor(0, 40, 30, 180))
        p.setPen(QtGui.QPen(accent, 1))
        p.drawRect(icon_box)

        # Sembol
        sym = TYPE_ICONS.get(self.type_key, "□")
        p.setPen(QtGui.QPen(accent, 1))
        f = p.font(); f.setPointSizeF(f.pointSizeF() + 4); p.setFont(f)
        p.drawText(icon_box, QtCore.Qt.AlignCenter, sym)


class DatabasePage(QtWidgets.QWidget):
    def __init__(self, fs, parent=None):
        super().__init__(parent)
        self.fs = fs

        # DB konumu (workspace/database/kaya.db)
        base_dir = (self.fs.p.files_dir.parent / "database")
        base_dir.mkdir(parents=True, exist_ok=True)
        self.db = DBService(base_dir / "kaya.db")

        # ---------- Ana iskelet: üst bar + içerik stack ----------
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        top = QtWidgets.QHBoxLayout()

        # ← Back butonu (HUB’dayken gizli, liste görünümünde görünür)
        self.btn_back = QtWidgets.QToolButton(text="← Back")
        self.btn_back.setObjectName("navbtn")
        self.btn_back.setToolTip("Back to Database Hub (Esc)")
        self.btn_back.clicked.connect(self._back_to_hub)
        self.btn_back.hide()  # başlangıçta HUB’dayız

        self.scopeL = QtWidgets.QLabel("Database")
        self.search = QtWidgets.QLineEdit(placeholderText="Search (Ctrl+K)")
        self.search.setClearButtonEnabled(True)
        self.btn_new = QtWidgets.QToolButton(text="New");    self.btn_new.setObjectName("navbtn")
        self.btn_del = QtWidgets.QToolButton(text="Delete"); self.btn_del.setObjectName("navbtn")

        top.addWidget(self.btn_back)          # <<<< eklendi
        top.addWidget(self.scopeL)
        top.addSpacing(8)
        top.addWidget(self.search, 1)
        top.addSpacing(8)
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_del)
        outer.addLayout(top)

        # İçerik stack: 0) HUB  1) LİSTE/DETAY
        self.stack = QtWidgets.QStackedWidget()
        outer.addWidget(self.stack, 1)

        # 0) HUB SAYFASI (QGridLayout + reflow)
        self.hub_page = QtWidgets.QWidget()
        self.hub_grid = QtWidgets.QGridLayout(self.hub_page)
        self.hub_grid.setContentsMargins(24, 12, 24, 24)
        self.hub_grid.setHorizontalSpacing(24)
        self.hub_grid.setVerticalSpacing(20)

        self._tiles: list[HubTile] = []
        for key, label in TYPE_ORDER:
            t = HubTile(key, label, self.hub_page)
            t.clicked.connect(self._open_type)
            self._tiles.append(t)
        self._reflow_hub()
        self.stack.addWidget(self.hub_page)

        # 1) LİSTE/DETAY SAYFASI (sol liste + sağ detay)
        self.page = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.list = QtWidgets.QListWidget(objectName="dblist")
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list.setUniformItemSizes(True)
        self.list.setAlternatingRowColors(True)
        self.list.setFocusPolicy(QtCore.Qt.NoFocus)

        self.detail = QtWidgets.QStackedWidget()
        self.placeholder = QtWidgets.QLabel("Select an item…")
        self.placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self.person_card = PersonCard(self.db)
        self.detail.addWidget(self.placeholder)
        self.detail.addWidget(self.person_card)

        self.page.addWidget(self.list)
        self.page.addWidget(self.detail)
        self.page.setStretchFactor(0, 35)
        self.page.setStretchFactor(1, 65)
        self.stack.addWidget(self.page)

        # Sinyaller
        self.search.textChanged.connect(self._reload)
        self.btn_new.clicked.connect(self._new)
        self.btn_del.clicked.connect(self._delete)
        self.list.itemSelectionChanged.connect(self._open_selected)

        # Varsayılan görünüm
        self.current_type: str | None = None
        self.stack.setCurrentIndex(0)  # HUB

        # Kısayollar
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+K"), self, self.search.setFocus)
        QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, self._back_to_hub)
        QtGui.QShortcut(QtGui.QKeySequence("Alt+Left"), self, self._back_to_hub)

    # --------- HUB yerleşimi: pencere genişliğine göre dinamik kolon ---------
    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        if self.stack.currentIndex() == 0:
            self._reflow_hub()

    def _reflow_hub(self):
        # grid'i temizle
        while self.hub_grid.count():
            it = self.hub_grid.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(self.hub_page)

        # mevcut genişliğe göre kolon sayısı
        if not self.hub_page.width():
            cols = 4
        else:
            tile_w = self._tiles[0].width() + self.hub_grid.horizontalSpacing()
            avail = max(1, self.hub_page.width() - (self.hub_grid.contentsMargins().left()
                                                    + self.hub_grid.contentsMargins().right()))
            cols = max(1, min(len(self._tiles), avail // tile_w))

        # yeniden yerleştir
        for i, tile in enumerate(self._tiles):
            r, c = divmod(i, cols)
            self.hub_grid.addWidget(tile, r, c, QtCore.Qt.AlignTop)

    # --------- Tür aç/kapat ---------
    def _open_type(self, t: str):
        self.current_type = t
        self.scopeL.setText(t.title())
        self.stack.setCurrentIndex(1)
        self.btn_back.show()               # <<<< listeye girince göster
        self._reload()

    def _back_to_hub(self):
        # Zaten HUB’taysa bir şey yapma
        if self.stack.currentIndex() == 0:
            return
        self.stack.setCurrentIndex(0)
        self.scopeL.setText("Database")
        self.list.clear()
        self.detail.setCurrentIndex(0)
        self.search.clear()
        self.current_type = None
        self.btn_back.hide()               # <<<< HUB’dayken gizle

    # --------- Liste doldurma / seçim / CRUD ---------
    def _reload(self):
        if self.stack.currentIndex() != 1 or not self.current_type:
            return
        q = (self.search.text() or "").strip()
        self.list.blockSignals(True)
        self.list.clear()

        if self.current_type == "people":
            rows = self.db.list_people(q)
            for r in rows:
                it = QtWidgets.QListWidgetItem(f"{r['name']}  ·  {r.get('country','')}")
                it.setData(QtCore.Qt.UserRole, r["id"])
                self.list.addItem(it)
        else:
            pass  # diğer türler geldiğinde eklenecek

        self.list.blockSignals(False)
        self.detail.setCurrentIndex(0)
        self.list.clearSelection()

    def _open_selected(self):
        if self.stack.currentIndex() != 1:
            return
        it = self.list.currentItem()
        if not it:
            self.detail.setCurrentIndex(0)
            return
        rec_id = it.data(QtCore.Qt.UserRole)
        if self.current_type == "people":
            self.person_card.load_person(rec_id)
            self.detail.setCurrentIndex(1)

    def _new(self):
        if self.stack.currentIndex() != 1 or not self.current_type:
            return
        if self.current_type == "people":
            pid = self.db.create_person({"name": "New Person"})
            self._reload()
            for i in range(self.list.count()):
                if self.list.item(i).data(QtCore.Qt.UserRole) == pid:
                    self.list.setCurrentRow(i)
                    break

    def _delete(self):
        if self.stack.currentIndex() != 1 or not self.current_type:
            return
        it = self.list.currentItem()
        if not it:
            return
        if QtWidgets.QMessageBox.question(self, "Delete", "Delete selected record?") != QtWidgets.QMessageBox.Yes:
            return
        rec_id = it.data(QtCore.Qt.UserRole)
        if self.current_type == "people":
            self.db.delete_person(rec_id)
            self._reload()
