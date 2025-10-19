# kaya/ui/agenda_page.py
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
from datetime import date, datetime, timedelta
import json, re

# ---- Tagler ve renkleri ----
TAG_COLORS = {
    "exam":      "#E46060",
    "homework":  "#E0C060",
    "birthday":  "#60C070",
    "event":     "#60B0E0",
    "important": "#C080E0",
}
ALL_TAGS = list(TAG_COLORS.keys())

def ymd(d: date) -> str: return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
def monday_of(d: date) -> date: return d - timedelta(days=d.weekday())

def iter_month_grid(y: int, m: int):
    first = date(y, m, 1)
    start = monday_of(first)
    for i in range(42):
        cur = start + timedelta(days=i)
        yield cur, (cur.month == m)

# ────────────────────────────────────────────────────────────────────────────────
# FS katmanı
class AgendaFS:
    """
    Journal:  <agenda_dir>/journal/YYYY/MM/DD.md
    Plan:     fs.day_note(YYYY-MM-DD)           (sağ panel ile aynı)
    Tags:     <agenda_dir>/tags/YYYY-MM-DD.txt  (sadece tag kutusu)
    """
    TAG_LINE = re.compile(
        r"^\s*(?:#(?P<tag1>\w+)|\[(?P<tag2>\w+)\]|(?P<tag3>\w+))[:\s]+\s*(?P<text>.+?)\s*$",
        re.IGNORECASE,
    )

    def __init__(self, fs):
        self.fs = fs
        self.root = Path(fs.p.agenda_dir)
        (self.root / "journal").mkdir(parents=True, exist_ok=True)
        (self.root / "tags").mkdir(parents=True, exist_ok=True)

    # journal
    def journal_path(self, d: date) -> Path:
        return self.root / "journal" / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}.md"
    def read_journal(self, d: date) -> str:
        p = self.journal_path(d)
        try: return p.read_text(encoding="utf-8")
        except: return ""
    def write_journal(self, d: date, txt: str):
        p = self.journal_path(d); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8")

    # plan (sync)
    def plan_path(self, d: date) -> Path:
        return self.fs.day_note(ymd(d))
    def read_plan(self, d: date) -> str:
        p = self.plan_path(d)
        try: return p.read_text(encoding="utf-8")
        except: return ""
    def write_plan(self, d: date, txt: str):
        self.plan_path(d).write_text(txt, encoding="utf-8")

    # tags
    def tags_path(self, d: date) -> Path:
        return self.root / "tags" / f"{ymd(d)}.txt"
    def read_tags_text(self, d: date) -> str:
        p = self.tags_path(d)
        try: return p.read_text(encoding="utf-8")
        except: return ""
    def write_tags_text(self, d: date, txt: str):
        self.tags_path(d).write_text(txt, encoding="utf-8")

    def parse_tags(self, d: date) -> list[tuple[str,str]]:
        """
        Tags kutusundaki satırları [("exam","Sınav var"), ...] döndürür.
        Sadece destekli tag’leri kabul eder.
        """
        out = []
        txt = self.read_tags_text(d)
        for line in txt.splitlines():
            m = self.TAG_LINE.match(line)
            if not m: continue
            tg = (m.group("tag1") or m.group("tag2") or m.group("tag3") or "").lower()
            if tg in ALL_TAGS:
                out.append((tg, m.group("text")))
        return out

    def day_has_any_tag(self, d: date) -> list[str]:
        """Ay görünümü için sadece var olan taglerin isimleri (renk noktaları için)."""
        return [t for t,_ in self.parse_tags(d)]

# ────────────────────────────────────────────────────────────────────────────────
# Ay hücresi
class DayCell(QtWidgets.QFrame):
    clicked = QtCore.Signal(date)
    def __init__(self, d: date, in_month: bool):
        super().__init__(); self.d=d; self.in_month=in_month; self.colors=[]
        self.setFixedHeight(72); self.setObjectName("daycell"); self.setCursor(QtCore.Qt.PointingHandCursor)

    def set_colors(self, cols: list[str]): self.colors = cols; self.update()
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button()==QtCore.Qt.LeftButton: self.clicked.emit(self.d)

    def paintEvent(self, ev: QtGui.QPaintEvent):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        r = self.rect().adjusted(6,4,-6,-6)
        today = (self.d == date.today())

        edge = QtGui.QColor(20,90,70); bg = QtGui.QColor(8,40,32)
        if not self.in_month:
            edge = QtGui.QColor(30,60,50,120); bg = QtGui.QColor(5,24,22)
        p.setPen(QtGui.QPen(edge,1)); p.fillRect(r,bg); p.drawRect(r)

        if today:
            glow = QtGui.QColor(0,255,180,120); p.setPen(QtGui.QPen(glow,2))
            p.drawRect(r.adjusted(-1,-1,1,1))

        f=self.font(); f.setBold(True); p.setFont(f)
        fg = QtGui.QColor("#B8F8D0") if self.in_month else QtGui.QColor(120,200,160,120)
        p.setPen(fg)
        p.drawText(QtCore.QRect(r.left()+4, r.top()+2, r.width()-8, 18),
                   QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, str(self.d.day))

        if self.colors:
            x=r.left()+6; y=r.bottom()-12
            for c in self.colors[:8]:
                p.setBrush(QtGui.QColor(c)); p.setPen(QtCore.Qt.NoPen)
                p.drawEllipse(QtCore.QPointF(x,y),3.2,3.2); x+=9

class MonthView(QtWidgets.QWidget):
    go_day = QtCore.Signal(date)
    def __init__(self, afs: AgendaFS):
        super().__init__(); self.afs=afs; self.cur=date.today().replace(day=1)

        t=QtWidgets.QHBoxLayout()
        self.bprev=QtWidgets.QToolButton(text="◄"); self.bnext=QtWidgets.QToolButton(text="►")
        for b in (self.bprev,self.bnext): b.setObjectName("navbtn")
        self.title=QtWidgets.QLabel("--"); f=self.title.font(); f.setBold(True); self.title.setFont(f)
        t.addWidget(self.bprev); t.addSpacing(6); t.addWidget(self.title); t.addSpacing(6); t.addWidget(self.bnext); t.addStretch(1)

        self.w=QtWidgets.QWidget(); self.g=QtWidgets.QGridLayout(self.w)
        self.g.setHorizontalSpacing(10); self.g.setVerticalSpacing(10); self.g.setContentsMargins(6,4,6,4)

        v=QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        v.addLayout(t); v.addWidget(self.w,1)

        self.bprev.clicked.connect(lambda: self._shift(-1))
        self.bnext.clicked.connect(lambda: self._shift(+1))
        self.rebuild()

    def _shift(self, dm:int):
        y,m = self.cur.year, self.cur.month+dm
        if m<1: y-=1; m=12
        if m>12: y+=1; m=1
        self.cur=date(y,m,1); self.rebuild()

    def rebuild(self):
        self.title.setText(self.cur.strftime("%B %Y"))
        while self.g.count():
            it=self.g.takeAt(0)
            if it and it.widget(): it.widget().deleteLater()
        r=c=0
        for d,in_m in iter_month_grid(self.cur.year, self.cur.month):
            cell=DayCell(d,in_m)
            tags = self.afs.day_has_any_tag(d)
            cell.set_colors([TAG_COLORS[t] for t in tags])
            cell.clicked.connect(self.go_day)
            self.g.addWidget(cell,r,c); c+=1
            if c==7: c=0; r+=1

# ────────────────────────────────────────────────────────────────────────────────
# Hafta görünümü
class WeekView(QtWidgets.QWidget):
    go_day = QtCore.Signal(QtCore.QDate)
    def __init__(self, afs: AgendaFS):
        super().__init__(); self.afs=afs
        self.week_start = QtCore.QDate.currentDate().addDays(-QtCore.QDate.currentDate().dayOfWeek()+1)

        tb=QtWidgets.QHBoxLayout()
        self.bprev=QtWidgets.QToolButton(text="◄"); self.bnext=QtWidgets.QToolButton(text="►"); self.bthis=QtWidgets.QToolButton(text="This Week")
        for b in (self.bprev,self.bnext,self.bthis): b.setObjectName("navbtn")
        self.lbl=QtWidgets.QLabel()
        tb.addWidget(self.bprev); tb.addWidget(self.bnext); tb.addWidget(self.bthis); tb.addSpacing(8); tb.addWidget(self.lbl); tb.addStretch(1)

        grid=QtWidgets.QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(6)
        self.cols=[]
        for i in range(7):
            head=QtWidgets.QToolButton(objectName="weekhead")
            head.clicked.connect(lambda _=False, idx=i: self._goto(idx))
            grid.addWidget(head,0,i)
            box=QtWidgets.QTextBrowser(objectName="weekcol"); box.setReadOnly(True)
            grid.addWidget(box,1,i)
            self.cols.append((head,box))

        v=QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        v.addLayout(tb); v.addLayout(grid,1)

        self.bprev.clicked.connect(lambda: self._shift(-7))
        self.bnext.clicked.connect(lambda: self._shift(+7))
        self.bthis.clicked.connect(lambda: self._set(QtCore.QDate.currentDate()))
        self._refresh()

        self.setStyleSheet("""
        QToolButton#weekhead[today="true"] { color:#00FFB0; font-weight:700; border:1px solid rgba(0,255,160,.45); }
        QTextBrowser#weekcol { border:1px solid rgba(0,255,150,.22); padding:6px; }
        """)

    def _set(self, anyd: QtCore.QDate):
        self.week_start = anyd.addDays(-anyd.dayOfWeek()+1); self._refresh()
    def _shift(self, days:int): self._set(self.week_start.addDays(days))
    def _goto(self, idx:int): self.go_day.emit(self.week_start.addDays(idx))

    def _refresh(self):
        self.lbl.setText(f"Week of {self.week_start.toString('yyyy-MM-dd')}")
        today = QtCore.QDate.currentDate()
        for i,(head,box) in enumerate(self.cols):
            d = self.week_start.addDays(i)
            head.setText(d.toString("ddd dd"))
            head.setProperty("today", "true" if d==today else "false")
            head.style().unpolish(head); head.style().polish(head)

            # Tags kutusundan satırları çek (sadece metin, renkli)
            py = date(d.year(), d.month(), d.day())
            pairs = self.afs.parse_tags(py)
            if not pairs:
                box.setHtml("")   # gereksiz metin yok
                continue
            lines = []
            for tag, text in pairs:
                col = TAG_COLORS.get(tag, "#A0D8C8")
                # sadece METİN; her kayıt yeni satır
                lines.append(f"<span style='color:{col}'>{QtGui.QGuiApplication.translate('', text)}</span>")
            box.setHtml("<br>".join(lines))

# ────────────────────────────────────────────────────────────────────────────────
# Günlük görünümü
class DayView(QtWidgets.QWidget):
    changed = QtCore.Signal()
    def __init__(self, afs: AgendaFS):
        super().__init__(); self.afs=afs; self._d=date.today()
        self._tm = QtCore.QTimer(self); self._tm.setInterval(400); self._tm.setSingleShot(True); self._tm.timeout.connect(self._save_all)

        # toolbar
        tb=QtWidgets.QHBoxLayout()
        self.bm=QtWidgets.QToolButton(text="Month"); self.bw=QtWidgets.QToolButton(text="Week")
        self.bprev=QtWidgets.QToolButton(text="◄"); self.bnext=QtWidgets.QToolButton(text="►"); self.btoday=QtWidgets.QToolButton(text="Today")
        for b in (self.bm,self.bw,self.bprev,self.bnext,self.btoday): b.setObjectName("navbtn")
        self.lbl=QtWidgets.QLabel()
        tb.addWidget(self.bm); tb.addWidget(self.bw); tb.addSpacing(6)
        tb.addWidget(self.bprev); tb.addWidget(self.bnext); tb.addWidget(self.btoday); tb.addSpacing(8); tb.addWidget(self.lbl); tb.addStretch(1)

        v=QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        v.addLayout(tb)

        # Journal (büyük)
        v.addWidget(QtWidgets.QLabel("Journal (Daily notes)"))
        self.journal = QtWidgets.QPlainTextEdit()
        v.addWidget(self.journal, 3)

        # alt: Plan + Tags (küçük kutular)
        row = QtWidgets.QHBoxLayout()
        colL = QtWidgets.QVBoxLayout(); colR = QtWidgets.QVBoxLayout()
        row.addLayout(colL,1); row.addLayout(colR,1)
        v.addLayout(row)

        colL.addWidget(QtWidgets.QLabel("Plan (sync):"))
        self.plan = QtWidgets.QPlainTextEdit()
        colL.addWidget(self.plan,1)

        colR.addWidget(QtWidgets.QLabel("Tags:"))
        self.tags = QtWidgets.QPlainTextEdit(placeholderText="Örn:\n#exam Matematik sınavı\nhomework: ödev 3\n[event] toplantı")
        self.tags.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tags.customContextMenuRequested.connect(self._tags_menu)
        colR.addWidget(self.tags,1)

        # sinyaller
        self.bprev.clicked.connect(lambda: self._set(self._d - timedelta(days=1)))
        self.bnext.clicked.connect(lambda: self._set(self._d + timedelta(days=1)))
        self.btoday.clicked.connect(lambda: self._set(date.today()))
        for w in (self.journal, self.plan, self.tags):
            w.textChanged.connect(self._tm.start)

        self._set(self._d)

    # sağ tık menüsü: tag hızlı ekleme
    def _tags_menu(self, pos):
        m = self.tags.createStandardContextMenu()
        m.addSeparator()
        sub = m.addMenu("Insert tag")
        for t in ALL_TAGS:
            a = sub.addAction(f"#{t} ")
            a.triggered.connect(lambda _, tt=t: self._insert_tag_line(tt))
        m.exec(self.tags.mapToGlobal(pos))

    def _insert_tag_line(self, tag:str):
        c = self.tags.textCursor()
        if not c.atBlockStart(): c.movePosition(QtGui.QTextCursor.EndOfBlock); c.insertBlock()
        c.insertText(f"#{tag} ")

    # state
    def _set(self, d: date):
        self._d = d; self.lbl.setText(f"{ymd(d)} ({d.strftime('%a')})")
        self.journal.blockSignals(True); self.journal.setPlainText(self.afs.read_journal(d)); self.journal.blockSignals(False)
        self.plan.blockSignals(True); self.plan.setPlainText(self.afs.read_plan(d)); self.plan.blockSignals(False)
        self.tags.blockSignals(True); self.tags.setPlainText(self.afs.read_tags_text(d)); self.tags.blockSignals(False)

    def _save_all(self):
        self.afs.write_journal(self._d, self.journal.toPlainText())
        self.afs.write_plan(self._d, self.plan.toPlainText())
        self.afs.write_tags_text(self._d, self.tags.toPlainText())
        self.changed.emit()

# ────────────────────────────────────────────────────────────────────────────────
# Ana Ajanda
class AgendaPage(QtWidgets.QWidget):
    def __init__(self, fs, parent=None):
        super().__init__(parent)
        self.afs = AgendaFS(fs)

        bar=QtWidgets.QHBoxLayout()
        self.bMonth=QtWidgets.QToolButton(text="Month"); self.bWeek=QtWidgets.QToolButton(text="Week"); self.bDay=QtWidgets.QToolButton(text="Day")
        for b in (self.bMonth,self.bWeek,self.bDay): b.setObjectName("navbtn")
        bar.addWidget(self.bMonth); bar.addWidget(self.bWeek); bar.addWidget(self.bDay); bar.addStretch(1)

        self.stack = QtWidgets.QStackedWidget()
        self.vMonth = MonthView(self.afs); self.vWeek = WeekView(self.afs); self.vDay = DayView(self.afs)
        self.stack.addWidget(self.vMonth); self.stack.addWidget(self.vWeek); self.stack.addWidget(self.vDay)

        lay=QtWidgets.QVBoxLayout(self); lay.setContentsMargins(8,8,8,8); lay.setSpacing(8)
        lay.addLayout(bar); lay.addWidget(self.stack,1)

        self.bMonth.clicked.connect(lambda: self.stack.setCurrentWidget(self.vMonth))
        self.bWeek.clicked.connect(lambda: self.stack.setCurrentWidget(self.vWeek))
        self.bDay.clicked.connect(lambda: self.stack.setCurrentWidget(self.vDay))

        self.vMonth.go_day.connect(self._goto_day)
        self.vWeek.go_day.connect(self._goto_day)
        self.vDay.changed.connect(self._refresh_overviews)

        # İSTEK: açılışta Day
        self.stack.setCurrentWidget(self.vDay)

    def _goto_day(self, qd):
        d = date(qd.year(), qd.month(), qd.day()) if isinstance(qd, QtCore.QDate) else qd
        self.vDay._set(d); self.stack.setCurrentWidget(self.vDay)

    def _refresh_overviews(self):
        self.vMonth.rebuild(); self.vWeek._refresh()
