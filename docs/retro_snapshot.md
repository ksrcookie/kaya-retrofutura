# KAYA RetroFutura — Code Snapshot
Root: `C:\Users\Faruk\Desktop\KAYAyedek\kayaretrofuturagit`

---

## `data\config\ui.json`

```
{
  "theme": "jarvis_blue"
}
```

## `kaya\__init__.py`

```
__version__='0.7.3'

```

## `kaya\core\__init__.py`

```

```

## `kaya\core\config.py`

```
from pathlib import Path
APP_NAME='K.A.Y.A — Kişisel Akıllı Yardımcı Asistan'
BASE_DIR=Path(__file__).resolve().parents[1]
VAULTS_DIR=BASE_DIR/'vaults'
DEFAULT_VAULT='DefaultVault'
WORK=VAULTS_DIR/DEFAULT_VAULT/'workspace'
FILES=WORK/'files'; PROJECTS=WORK/'projects'; AGENDA=WORK/'agenda'; MEDIA=WORK/'media'
for d in (VAULTS_DIR, WORK, FILES, PROJECTS, AGENDA, MEDIA): d.mkdir(parents=True, exist_ok=True)

```

## `kaya\services\__init__.py`

```

```

## `kaya\services\fs_items.py`

```
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil

@dataclass
class FSPaths:
    files_dir: Path; projects_dir: Path; agenda_dir: Path; media_dir: Path

class FSService:
    def __init__(self, p: FSPaths): self.p=p
    def ensure_note(self, path: Path)->Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): path.write_text('', encoding='utf-8')
        return path
    def day_note(self, ymd:str)->Path: return self.ensure_note(self.p.agenda_dir/f"{ymd}.md")
    def new_note(self, rel:str, body:str='')->Path:
        q=(self.p.files_dir/rel).with_suffix('.md'); q.parent.mkdir(parents=True, exist_ok=True); q.write_text(body,encoding='utf-8'); return q
    def new_folder(self, rel:str)->Path:
        d=self.p.files_dir/rel; d.mkdir(parents=True, exist_ok=True); return d
    def delete(self, path:Path):
        if path.is_dir(): shutil.rmtree(path, ignore_errors=True)
        else: path.unlink(missing_ok=True)
    def new_project(self, name:str)->Path:
        d=self.p.projects_dir/name; d.mkdir(parents=True, exist_ok=True)
        (d/'README.md').write_text(f"# {name}\n\nProject created by K.A.Y.A.", encoding='utf-8')
        return d

```

## `kaya\terminal\__init__.py`

```

```

## `kaya\terminal\commands.py`

```
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any
import json
import shutil
import re

# ===================== DB / People helpers =====================

def _db_for(fs):
    """Return DBService on <workspace>/database/kaya.db"""
    from ..ui.db_service import DBService
    base_dir = Path(fs.p.files_dir).parent / "database"
    base_dir.mkdir(parents=True, exist_ok=True)
    return DBService(base_dir / "kaya.db")

def _resolve_person_id(db, token: str) -> Optional[int]:
    token = (token or "").strip()
    if not token:
        return None
    if token.isdigit():
        return int(token)
    rows = db.list_people(token)
    if not rows:
        return None
    t = token.lower()
    for r in rows:
        if (r.get("name") or "").strip().lower() == t:
            return r["id"]
    return rows[0]["id"]

# ===================== Project helpers =====================

def _projects_root(fs) -> Path:
    return Path(fs.p.projects_dir)

def _meta_path(proj_dir: Path) -> Path:
    return proj_dir / "project.json"

def _load_meta(proj_dir: Path) -> Dict[str, Any]:
    p = _meta_path(proj_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"name": proj_dir.name, "type": "standard", "status": "active", "updated": ""}

def _save_meta(proj_dir: Path, meta: Dict[str, Any]):
    _meta_path(proj_dir).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def _slugify(name: str) -> str:
    s = re.sub(r"\s+", "-", (name or "").strip())
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)
    return s or "untitled"

def _scan_projects(fs):
    root = _projects_root(fs)
    items = []
    if not root.exists():
        return items
    for p in sorted(root.iterdir()):
        if p.is_dir() and _meta_path(p).exists():
            items.append((p, _load_meta(p)))
    return items

def _find_project_by_name(fs, token: str) -> Optional[Path]:
    token = (token or "").strip()
    root = _projects_root(fs)
    if not token:
        return None
    # direct folder hit
    cand = root / token
    if cand.exists() and cand.is_dir():
        return cand
    # exact meta name
    for d, m in _scan_projects(fs):
        if (m.get("name") or "").strip().lower() == token.lower():
            return d
    # partial meta name
    for d, m in _scan_projects(fs):
        nm = (m.get("name") or "").lower()
        if token.lower() in nm:
            return d
    return None

def _ensure_template(fs, proj_dir: Path, proj_type: str):
    """Copy templates/<type> into project if exists; otherwise create minimal skeleton."""
    templates_root = Path(fs.p.projects_dir).parent / "templates" / proj_type
    if templates_root.exists():
        for item in templates_root.iterdir():
            dst = proj_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
    (proj_dir / "notes").mkdir(parents=True, exist_ok=True)

# ===================== Command registration =====================

def register_default_commands(bus, fs, main_window=None):
    """
    Register CLI commands. If main_window is provided, some commands can open UI windows.
    """

    # -------- FILES --------
    def cmd_new(p):
        pos, kv = p.get("pos", []), p.get("kv", {})
        if not pos:
            return 'Usage: new note "rel/path" [body="..."]'
        if pos[0].lower() == "note":
            rel = pos[1] if len(pos) > 1 else "untitled"
            body = kv.get("body", "")
            path = fs.new_note(rel, body)
            return f"Created note at {path}"
        return "Unknown entity"

    def cmd_mkdir(p):
        pos = p.get("pos", [])
        if not pos:
            return 'Usage: mkdir "rel/path"'
        fs.new_folder(pos[0])
        return "Folder created."

    def cmd_rm(p):
        pos = p.get("pos", [])
        if not pos:
            return 'Usage: rm "abs_or_rel"'
        x = Path(pos[0])
        if not x.is_absolute():
            x = fs.p.files_dir / x
        fs.delete(x)
        return "Deleted."

    # -------- PEOPLE --------
    def cmd_people(p):
        """
Usage:
  people search <query>
  people view <id|name>
  people new [name...]
        """.strip()
        pos = [x for x in p.get("pos", []) if x is not None]
        if not pos:
            return cmd_people.__doc__

        sub = pos[0].lower()
        args = pos[1:]
        db = _db_for(fs)

        if sub == "search":
            q = " ".join(args).strip()
            rows = db.list_people(q)
            if not rows:
                return "No results."
            out = [
                "ID  | Name                | Country",
                "-" * 40
            ]
            for r in rows:
                out.append(f"{r['id']:>3} | {(r.get('name') or '')[:18]:18} | {r.get('country','')}")
            return "\n".join(out)

        if sub == "view":
            if not args:
                return "Usage: people view <id|name>"
            token = " ".join(args)
            pid = _resolve_person_id(db, token)
            if not pid:
                return "Person not found."
            from PySide6 import QtWidgets
            from ..ui.person_dialog import PersonDialog
            parent = main_window if isinstance(main_window, QtWidgets.QWidget) else None
            dlg = PersonDialog(db, pid, parent)
            dlg.show()
            return f"Opening dossier for #{pid}..."

        if sub == "new":
            name = " ".join(args).strip() or "New Person"
            pid = db.create_person({"name": name})
            from PySide6 import QtWidgets
            from ..ui.person_dialog import PersonDialog
            parent = main_window if isinstance(main_window, QtWidgets.QWidget) else None
            dlg = PersonDialog(db, pid, parent)
            dlg.show()
            return f"Created person: {name} (#{pid})"

        return f"Unknown subcommand: {sub}\n{cmd_people.__doc__}"

    # -------- PROJECTS (listing) --------
    def cmd_projects(p):
        """
Usage:
  projects list [query] [type=T] [status=active|archived]
  projects types
        """.strip()

        pos = [x for x in p.get("pos", []) if x is not None]
        kv  = p.get("kv", {})

        sub  = pos[0].lower() if pos else "list"
        args = pos[1:] if pos else []

        if sub == "types":
            return "Types: standard, engineering, edu, research, custom"

        # list
        query   = " ".join(args).strip()
        tfilter = (kv.get("type") or "").strip().lower()
        sfilter = (kv.get("status") or "").strip().lower()

        rows = []
        for d, m in _scan_projects(fs):
            nm = m.get("name", d.name)
            if query and (query.lower() not in (nm.lower() + " " + d.name.lower())):
                continue
            if tfilter and m.get("type", "").lower() != tfilter:
                continue
            if sfilter and m.get("status", "").lower() != sfilter:
                continue
            rows.append((d, m))

        if not rows:
            return "No projects."

        out = [
            "Name                         | Type        | Status   | Updated",
            "-" * 72
        ]
        for d, m in rows:
            out.append(f"{(m.get('name', d.name))[:28]:28} | {m.get('type','')[:10]:10} | {m.get('status','')[:8]:8} | {m.get('updated','')}")
        return "\n".join(out)

    # -------- PROJECT (actions) --------
    def cmd_project(p):
        """
Usage:
  project new "<name>" [type=standard]
  project info "<name|folder>"
  project open "<name|folder>"
  project rename "<old>" "<new>"
  project delete "<name|folder>"
  project addnote "<name>" "notes/<file>.md" [body="..."]
        """.strip()

        pos = [x for x in p.get("pos", []) if x is not None]
        kv  = p.get("kv", {})
        if not pos:
            return cmd_project.__doc__

        sub  = pos[0].lower()
        args = pos[1:]

        # new
        if sub == "new":
            if not args:
                return 'Usage: project new "My Project" [type=standard]'
            name   = args[0]
            ptype  = (kv.get("type") or "standard").lower()
            root   = _projects_root(fs)
            folder = root / _slugify(name)
            if folder.exists():
                return f'Already exists: "{folder.name}"'
            folder.mkdir(parents=True, exist_ok=True)
            _ensure_template(fs, folder, ptype)
            meta = _load_meta(folder)
            meta.update({"name": name, "type": ptype, "status": "active"})
            _save_meta(folder, meta)
            return f'Created project "{name}"'

        # remaining actions need a target
        if not args:
            return cmd_project.__doc__
        token  = args[0]
        target = _find_project_by_name(fs, token)
        if not target:
            return "Project not found."

        if sub == "info":
            m = _load_meta(target)
            return "\n".join([
                f"Folder : {target.name}",
                f"Name   : {m.get('name','')}",
                f"Type   : {m.get('type','')}",
                f"Status : {m.get('status','')}",
                f"Updated: {m.get('updated','')}",
                f"Path   : {str(target)}",
            ])

        if sub == "open":
            m = _load_meta(target)
            # UI: non-modal project window if UI hook is registered
            try:
                bus.dispatch("ui.project_open", {"path": str(target)})
                return f'Opening "{m.get("name") or target.name}"...'
            except Exception:
                return f'Project path: {str(target)}'

        if sub == "rename":
            if len(args) < 2:
                return 'Usage: project rename "<old>" "<new>"'
            new_name   = args[1]
            new_folder = target.parent / _slugify(new_name)
            if new_folder.exists():
                return "Target folder already exists."
            target.rename(new_folder)
            m = _load_meta(new_folder)
            m["name"] = new_name
            _save_meta(new_folder, m)
            return f'Renamed to "{new_name}"'

        if sub == "delete":
            shutil.rmtree(target, ignore_errors=True)
            return "Deleted."

        if sub == "addnote":
            if len(args) < 2:
                return 'Usage: project addnote "<name>" "notes/<file>.md" [body="..."]'
            rel  = args[1]
            body = kv.get("body", "")
            dst  = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.suffix:
                dst = dst.with_suffix(".md")
            dst.write_text(body, encoding="utf-8")
            return f'Written: {dst.relative_to(target)}'

        return f"Unknown subcommand: {sub}\n{cmd_project.__doc__}"

    # register
    bus.register("new",      cmd_new)
    bus.register("mkdir",    cmd_mkdir)
    bus.register("rm",       cmd_rm)
    bus.register("people",   cmd_people)
    bus.register("projects", cmd_projects)
    bus.register("project",  cmd_project)

```

## `kaya\terminal\parser.py`

```
import shlex
def parse(line:str):
    t=shlex.split(line); 
    if not t: return None,{}
    cmd=t[0].lower(); pos=[]; kv={}
    for a in t[1:]:
        if '=' in a and not a.startswith('='): k,v=a.split('=',1); kv[k]=v
        else: pos.append(a)
    return cmd, {'pos':pos,'kv':kv,'raw':line}

```

## `kaya\ui\__init__.py`

```

```

## `kaya\ui\agenda_page.py`

```
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

```

## `kaya\ui\commands_palette.py`

```
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

```

## `kaya\ui\database_page.py`

```
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

```

## `kaya\ui\db_service.py`

```
# kaya/ui/db_service.py
from __future__ import annotations
import sqlite3, json
from pathlib import Path
from typing import List, Dict, Any

def _dict_factory(cursor, row):
    d = {}
    for i, col in enumerate(cursor.description):
        d[col[0]] = row[i]
    return d

SCHEMA = """
CREATE TABLE IF NOT EXISTS people(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dob TEXT,
    country TEXT,
    city TEXT,
    education TEXT,
    family TEXT,         -- JSON array
    meta TEXT,           -- JSON blob (freeform)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS trg_people_updated
AFTER UPDATE ON people
BEGIN
  UPDATE people SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""

class DBService:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = _dict_factory
        self._init()

    def _init(self):
        cur = self.conn.cursor()
        cur.executescript(SCHEMA)
        self.conn.commit()

    # -------- PEOPLE ----------
    def list_people(self, q: str='') -> List[Dict[str,Any]]:
        cur = self.conn.cursor()
        if q:
            q = f"%{q.lower()}%"
            cur.execute("""
                SELECT * FROM people
                WHERE lower(name) LIKE ? OR lower(country) LIKE ? OR lower(city) LIKE ?
                ORDER BY updated_at DESC
            """, (q,q,q))
        else:
            cur.execute("SELECT * FROM people ORDER BY updated_at DESC")
        return cur.fetchall()

    def get_person(self, pid: int) -> Dict[str,Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM people WHERE id=?", (pid,))
        return cur.fetchone()

    def create_person(self, data: Dict[str,Any]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO people(name, dob, country, city, education, family, meta)
            VALUES(?,?,?,?,?,?,?)
        """, (
            data.get('name','New Person'),
            data.get('dob',''),
            data.get('country',''),
            data.get('city',''),
            data.get('education',''),
            json.dumps(data.get('family',[]), ensure_ascii=False),
            json.dumps(data.get('meta',{}), ensure_ascii=False),
        ))
        self.conn.commit()
        return int(cur.lastrowid)

    def update_person(self, pid: int, data: Dict[str,Any]):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE people
            SET name=?, dob=?, country=?, city=?, education=?, family=?, meta=?
            WHERE id=?
        """, (
            data.get('name',''),
            data.get('dob',''),
            data.get('country',''),
            data.get('city',''),
            data.get('education',''),
            json.dumps(data.get('family',[]), ensure_ascii=False),
            json.dumps(data.get('meta',{}), ensure_ascii=False),
            pid
        ))
        self.conn.commit()

    def delete_person(self, pid: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM people WHERE id=?", (pid,))
        self.conn.commit()

```

## `kaya\ui\files_page.py`

```
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

```

## `kaya\ui\main.py`

```
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

```

## `kaya\ui\mini_calendar.py`

```
﻿# kaya/ui/mini_calendar.py
from PySide6 import QtWidgets, QtCore, QtGui
import math

class MiniCalendar(QtWidgets.QCalendarWidget):
    """
    Minimal, retro-tech takvim:
      - Sadece oklarla gezinme (tekerlek devre dışı)
      - Ay dışı günler silik
      - Satır yüksekliği: bulunduğun aya göre 5 ya da 6 hafta görünümü için otomatik ayarlanır
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Görünüm
        self.setGridVisible(False)
        self.setFirstDayOfWeek(QtCore.Qt.Monday)
        self.setLocale(QtCore.QLocale(QtCore.QLocale.Turkish, QtCore.QLocale.Turkey))
        self.setVerticalHeaderFormat(QtWidgets.QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QtWidgets.QCalendarWidget.ShortDayNames)
        self.setNavigationBarVisible(True)

        # Küçük, okunaklı
        self.setStyleSheet("QCalendarWidget QAbstractItemView { font-size: 9pt; }")

        # Ok düğmelerini temaya uydur
        QtCore.QTimer.singleShot(0, self._style_nav)

        # Ay değişince yükseklik ve boyamayı güncelle
        self.currentPageChanged.connect(lambda y, m: self._fit_height(y, m))

        # İlk yükseklik ayarı
        d = self.selectedDate()
        self._fit_height(d.year(), d.month())

    # ---- Kullanıcı etkileşimi ----
    def wheelEvent(self, e: QtGui.QWheelEvent):
        # Fare tekerleği ile ay değiştirmeyi kapat
        e.ignore()

    # ---- Silik gün boyama ----
    def paintCell(self, painter: QtGui.QPainter, rect: QtCore.QRect, date: QtCore.QDate):
        super().paintCell(painter, rect, date)
        # Bu ay değilse koyu bir overlay ile silikleştir
        if date.month() != self.selectedDate().month():
            painter.save()
            painter.setBrush(QtGui.QColor(0, 0, 0, 140))  # hafif koyulaştır
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect)
            painter.restore()

    # ---- Özel yardımcılar ----
    def _style_nav(self):
        """Başlıktaki sol/sağ ok düğmelerini temanın kare/retro stiline yaklaştır."""
        # Navigation bar içindeki toolbutton'lar
        btns = self.findChildren(QtWidgets.QToolButton)
        left = right = None
        for b in btns:
            # Qt default objectName'ları platforma göre değişebilir; icon/action text’e bakıyoruz
            if b.toolTip().lower().startswith("önceki") or "previous" in b.toolTip().lower():
                left = b
            elif b.toolTip().lower().startswith("sonraki") or "next" in b.toolTip().lower():
                right = b

        # Yakalayamazsak da sorun değil
        if left:
            left.setText("◁")     # retro ok
            left.setIcon(QtGui.QIcon())  # emoji gibi durmasın
            left.setObjectName("navbtn") # temadaki kare buton stilini alır
            left.setMinimumWidth(22); left.setMinimumHeight(18)
        if right:
            right.setText("▷")
            right.setIcon(QtGui.QIcon())
            right.setObjectName("navbtn")
            right.setMinimumWidth(22); right.setMinimumHeight(18)

    def _fit_height(self, year: int, month: int):
        """Bulunduğun aya göre 5 ya da 6 hafta görünümü için takvimin yüksekliğini ayarla."""
        # Kaç hafta (satır) gerektiğini hesapla
        first = QtCore.QDate(year, month, 1)
        days_in_month = first.daysInMonth()
        # Qt: Monday=1..Sunday=7 -> 0-index’e çevir
        offset = (first.dayOfWeek() - 1)
        weeks = math.ceil((offset + days_in_month) / 7)
        weeks = max(5, min(6, weeks))  # en az 5, en fazla 6 satır

        fm = QtGui.QFontMetrics(self.font())
        cell_h = fm.height() + 10     # gün hücresi tahmini yüksekliği
        header_h = fm.height() + 12   # Pzt-Sal-... satırı
        nav_h = 28                    # ay/yıl ve oklar kısmi yükseklik
        margins = 10

        target = nav_h + header_h + cell_h * weeks + margins
        # çok küçük ekranlarda kesilmesin diye minimumu koru
        target = max(target, 200)

        self.setMinimumHeight(target)
        self.setMaximumHeight(target)

```

## `kaya\ui\person_card.py`

```
# kaya/ui/person_card.py
from PySide6 import QtWidgets, QtCore, QtGui
import json

class PersonCard(QtWidgets.QFrame):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.pid = None

        self.setObjectName('dossier')
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12,12,12,12); v.setSpacing(10)

        # Header bar
        hb = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel('— PERSON DOSSIER —')
        self.title.setObjectName('accent')
        hb.addWidget(self.title); hb.addStretch(1)
        v.addLayout(hb)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12); grid.setVerticalSpacing(8)

        self.e_name = QtWidgets.QLineEdit();    self.e_name.setPlaceholderText('Full name')
        self.e_dob  = QtWidgets.QLineEdit();    self.e_dob.setPlaceholderText('YYYY-MM-DD')
        self.e_country = QtWidgets.QLineEdit(); self.e_country.setPlaceholderText('Country')
        self.e_city    = QtWidgets.QLineEdit(); self.e_city.setPlaceholderText('City')
        self.e_edu     = QtWidgets.QLineEdit(); self.e_edu.setPlaceholderText('Education')
        self.e_family  = QtWidgets.QLineEdit(); self.e_family.setPlaceholderText('Family (comma separated)')

        r=0
        grid.addWidget(QtWidgets.QLabel('NAME'), r,0); grid.addWidget(self.e_name, r,1); r+=1
        grid.addWidget(QtWidgets.QLabel('DOB'), r,0); grid.addWidget(self.e_dob, r,1); r+=1
        grid.addWidget(QtWidgets.QLabel('COUNTRY'), r,0); grid.addWidget(self.e_country, r,1); r+=1
        grid.addWidget(QtWidgets.QLabel('CITY'), r,0); grid.addWidget(self.e_city, r,1); r+=1
        grid.addWidget(QtWidgets.QLabel('EDUCATION'), r,0); grid.addWidget(self.e_edu, r,1); r+=1
        grid.addWidget(QtWidgets.QLabel('FAMILY'), r,0); grid.addWidget(self.e_family, r,1); r+=1

        v.addLayout(grid)

        self.notes = QtWidgets.QPlainTextEdit(placeholderText='Notes...')
        self.notes.setMinimumHeight(120)
        v.addWidget(self.notes, 1)

        # debounce timer
        self._tm = QtCore.QTimer(self)
        self._tm.setInterval(600); self._tm.setSingleShot(True)
        self._tm.timeout.connect(self._save)

        for w in (self.e_name, self.e_dob, self.e_country, self.e_city, self.e_edu, self.e_family):
            w.textChanged.connect(lambda: self._tm.start())
        self.notes.textChanged.connect(lambda: self._tm.start())

    # public
    def load_person(self, pid: int):
        self.pid = pid
        r = self.db.get_person(pid)
        if not r: return
        self.e_name.setText(r.get('name',''))
        self.e_dob.setText(r.get('dob',''))
        self.e_country.setText(r.get('country',''))
        self.e_city.setText(r.get('city',''))
        self.e_edu.setText(r.get('education',''))
        try:
            fam = json.loads(r.get('family') or '[]')
            self.e_family.setText(', '.join(fam))
        except Exception:
            self.e_family.setText('')
        try:
            meta = json.loads(r.get('meta') or '{}')
            self.notes.setPlainText(meta.get('notes',''))
        except Exception:
            self.notes.setPlainText('')

    # private
    def _save(self):
        if not self.pid: return
        data = {
            'name': self.e_name.text().strip(),
            'dob': self.e_dob.text().strip(),
            'country': self.e_country.text().strip(),
            'city': self.e_city.text().strip(),
            'education': self.e_edu.text().strip(),
            'family': [x.strip() for x in self.e_family.text().split(',') if x.strip()],
            'meta': {'notes': self.notes.toPlainText()},
        }
        self.db.update_person(self.pid, data)

```

## `kaya\ui\person_dialog.py`

```
# kaya/ui/person_dialog.py
from PySide6 import QtWidgets, QtCore
from .person_card import PersonCard

class PersonDialog(QtWidgets.QDialog):
    def __init__(self, db, person_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PERSON DOSSIER")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)  # kapanınca bellekten at
        self.setModal(False)  # terminal açık kalsın

        lay = QtWidgets.QVBoxLayout(self)
        # İsteğe bağlı üst şerit
        top = QtWidgets.QHBoxLayout()
        self.b_save = QtWidgets.QToolButton(text="Save")
        self.b_close = QtWidgets.QToolButton(text="Close")
        for b in (self.b_save, self.b_close):
            b.setObjectName("navbtn")
        top.addStretch(1); top.addWidget(self.b_save); top.addWidget(self.b_close)
        lay.addLayout(top)

        # Asıl kart
        self.card = PersonCard(db)
        lay.addWidget(self.card, 1)
        self.card.load_person(person_id)

        # bağlar
        self.b_save.clicked.connect(self._save)
        self.b_close.clicked.connect(self.close)

        self.resize(760, 560)

    def _save(self):
        # PersonCard içinde bir save metodu varsa onu çağır.
        if hasattr(self.card, "save"):
            try:
                self.card.save()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Save error", str(e))

```

## `kaya\ui\projects_page.py`

```
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

```

## `kaya\ui\right_panel.py`

```
# kaya/ui/right_panel.py
from PySide6 import QtWidgets, QtCore
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from pathlib import Path
from .mini_calendar import MiniCalendar
import random

def fmt(ms: int) -> str:
    if not ms or ms <= 0:
        return "00:00"
    s = int(ms // 1000)
    return f"{s//60:02d}:{s%60:02d}"

class RightPanel(QtWidgets.QWidget):
    def __init__(self, fs, parent=None):
        super().__init__(parent)
        self.fs = fs
        self._i = -1
        self._dragging = False

        # ===== UI =====
        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(6,6,6,6); v.setSpacing(8)
        h = QtWidgets.QHBoxLayout()
        brand = QtWidgets.QLabel("K.A.Y.A"); brand.setObjectName("accent")
        self.clock = QtWidgets.QLabel("--:--"); self.clock.setObjectName("accent")
        self.btoday = QtWidgets.QPushButton("Today")
        h.addWidget(brand); h.addStretch(1); h.addWidget(self.clock); h.addWidget(self.btoday); v.addLayout(h)

        self.cal = MiniCalendar(); v.addWidget(self.cal, 0)
        self.plan = QtWidgets.QPlainTextEdit(placeholderText="Plan notu..."); self.plan.setMinimumHeight(130); v.addWidget(self.plan, 0)

        v.addWidget(QtWidgets.QLabel("— PLAYLIST —", objectName="accent"), 0)
        self.list = QtWidgets.QListWidget(objectName="tracklist")
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list.setMinimumHeight(170)
        v.addWidget(self.list, 1)

        row = QtWidgets.QHBoxLayout()
        self.prev = QtWidgets.QToolButton(text="◄")
        self.play = QtWidgets.QToolButton(text="■/▶")
        self.next = QtWidgets.QToolButton(text="►")
        self.shuffle = QtWidgets.QToolButton(text="SHF"); self.shuffle.setCheckable(True)
        self.vol = QtWidgets.QSlider(QtCore.Qt.Horizontal); self.vol.setRange(0,100); self.vol.setValue(60)
        for x in (self.prev,self.play,self.next,self.shuffle): x.setObjectName("navbtn")
        row.addWidget(self.prev); row.addWidget(self.play); row.addWidget(self.next); row.addWidget(self.shuffle); row.addWidget(self.vol)
        v.addLayout(row)

        prow = QtWidgets.QHBoxLayout()
        self.posL = QtWidgets.QLabel("00:00")
        self.pos  = QtWidgets.QSlider(QtCore.Qt.Horizontal, objectName="pos"); self.pos.setRange(0,0)
        self.durL = QtWidgets.QLabel("00:00")
        prow.addWidget(self.posL); prow.addWidget(self.pos,1); prow.addWidget(self.durL); v.addLayout(prow)

        # ===== Timers =====
        self._clk = QtCore.QTimer(self); self._clk.setInterval(1000); self._clk.timeout.connect(self._tick); self._clk.start(); self._tick()
        self._sv = QtCore.QTimer(self); self._sv.setSingleShot(True); self._sv.setInterval(500); self._sv.timeout.connect(self._save)
        self._plan_path=None

        # ===== Media backend =====
        self.audio = None
        self.player = None
        self._build_player()  # ilk player

        # Playlist
        self._pl: list[Path] = []
        media_dir = self.fs.p.media_dir
        exts = {".mp3",".wav",".flac",".ogg",".m4a"}
        if media_dir.exists():
            for p in sorted(media_dir.iterdir()):
                if p.suffix.lower() in exts: self._pl.append(p)
        if not self._pl:
            for n in ["01_Startup_Suite.mp3","02_Arc_Reactor.mp3","03_Journal_Night.mp3"]:
                self._pl.append(media_dir/n)
        for p in self._pl:
            it = QtWidgets.QListWidgetItem(p.name); it.setToolTip(p.name); self.list.addItem(it)

        # ===== Signals =====
        self.btoday.clicked.connect(self.today); self.cal.selectionChanged.connect(self.load_day)
        self.plan.textChanged.connect(lambda: self._sv.start())

        self.list.itemClicked.connect(self._on_single_click)          # tek tık: sadece seç
        self.list.itemDoubleClicked.connect(self._on_double_click)    # çift tık: çal/baştan
        self.list.currentRowChanged.connect(self._on_row_changed)

        self.play.clicked.connect(self._on_play_pause)
        self.prev.clicked.connect(self._on_prev)
        self.next.clicked.connect(self._on_next)
        self.shuffle.toggled.connect(lambda _: None)
        self.vol.valueChanged.connect(self._on_volume)

        self.pos.sliderPressed.connect(lambda: setattr(self, "_dragging", True))
        self.pos.sliderReleased.connect(self._on_seek_release)
        self.pos.sliderMoved.connect(self._on_seek_preview)

        # Başlangıç
        self.today()
        if self._pl:
            self.list.setCurrentRow(0); self._i = 0
        self._sync_play_icon(self.player.playbackState() if self.player else QMediaPlayer.PlaybackState.StoppedState)

    # ===== Player lifecycle =====
    def _build_player(self):
        """Player'ı baştan kur (Windows deadlock'larını önlemek için kaynak değişimlerinde de çağıracağız)."""
        # Eskiyi sök
        if self.player:
            try:
                self.player.stop()
            except Exception:
                pass
            try:
                self.player.positionChanged.disconnect(self._on_position)
                self.player.durationChanged.disconnect(self._on_duration)
                self.player.playbackStateChanged.disconnect(self._sync_play_icon)
                self.player.mediaStatusChanged.disconnect(self._on_status)
                self.player.errorOccurred.disconnect(self._on_error)
            except Exception:
                pass
            self.player.deleteLater()
            self.player = None

        if self.audio:
            try:
                # QAudioOutput'u yeniden kurmak, bazı sistemlerde sessizlik sorununu da çözüyor
                self.audio.deleteLater()
            except Exception:
                pass
            self.audio = None

        # Yeni backend
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(self.vol.value()/100.0)

        # Bağlantılar
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._sync_play_icon)
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.errorOccurred.connect(self._on_error)

    # ===== Basit saat & plan =====
    def _tick(self): self.clock.setText(QtCore.QTime.currentTime().toString("HH:mm"))
    def today(self): self.cal.setSelectedDate(QtCore.QDate.currentDate()); self.load_day()
    def load_day(self):
        d=self.cal.selectedDate(); ymd=f"{d.year():04d}-{d.month():02d}-{d.day():02d}"; p=self.fs.day_note(ymd); self._plan_path=p
        self.plan.blockSignals(True)
        try: self.plan.setPlainText(p.read_text(encoding='utf-8'))
        except Exception: self.plan.setPlainText('')
        self.plan.blockSignals(False)
    def _save(self):
        if self._plan_path:
            try: self._plan_path.write_text(self.plan.toPlainText(), encoding='utf-8')
            except Exception: pass

    # ===== Playlist yardımcıları =====
    def _current_path(self) -> Path|None:
        if not self._pl or self._i<0 or self._i>=len(self._pl): return None
        return self._pl[self._i]

    def _start_track(self, idx: int):
        """Basit ve güvenli: player'ı YENİDEN KUR → kaynak → pozisyon 0 → play."""
        if not self._pl: return
        idx = idx % len(self._pl)
        self._i = idx
        self.list.setCurrentRow(idx)

        p = self._pl[idx]
        # backend'i sıfırla
        self._build_player()

        from PySide6.QtCore import QUrl
        self.player.setSource(QUrl.fromLocalFile(str(p)))
        self.player.setPosition(0)
        self.pos.setValue(0); self.posL.setText("00:00"); self.durL.setText("00:00")
        try:
            self.player.play()
        except Exception:
            pass

    # ===== Kullanıcı davranışı =====
    def _on_single_click(self, it):
        # sadece seç
        self._i = self.list.row(it)

    def _on_double_click(self, it):
        row = self.list.row(it)
        # aynı şarkı çalıyorsa başa sar
        if self.player and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and row == self._i:
            self._start_track(row)   # restart
            return
        # aksi halde seç ve başlat
        self._start_track(row)

    def _on_row_changed(self, row:int):
        if row >= 0: self._i = row

    def _on_play_pause(self):
        if not self._pl: return
        if self._i < 0: self._i = 0; self.list.setCurrentRow(0)
        state = self.player.playbackState() if self.player else QMediaPlayer.PlaybackState.StoppedState
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            # Eğer daha önce kaynak yüklenmediyse veya pause sonrası deadlock oluyorsa güvenli başlat
            if self.player is None or self.player.source().isEmpty():
                self._start_track(self._i)
            else:
                try:
                    self.player.play()
                except Exception:
                    # Her ihtimale karşı yeniden başlat
                    self._start_track(self._i)

    def _on_prev(self):
        if not self._pl: return
        nxt = random.randrange(len(self._pl)) if self.shuffle.isChecked() else (self._i - 1) % len(self._pl)
        self._start_track(nxt)

    def _on_next(self):
        if not self._pl: return
        nxt = random.randrange(len(self._pl)) if self.shuffle.isChecked() else (self._i + 1) % len(self._pl)
        self._start_track(nxt)

    # ===== Player callbacks =====
    def _on_position(self, ms:int):
        if self._dragging: return
        self.posL.setText(fmt(ms))
        self.pos.blockSignals(True); self.pos.setValue(ms); self.pos.blockSignals(False)

    def _on_duration(self, ms:int):
        self.durL.setText(fmt(ms))
        self.pos.setRange(0, ms if ms>0 else 0)

    def _on_status(self, st):
        if st == QMediaPlayer.MediaStatus.EndOfMedia:
            self._on_next()

    def _on_error(self, err):
        # Hata → sonraki parçaya geç (uygulama asla çökmesin)
        self._on_next()

    # ===== Seek & volume =====
    def _on_seek_preview(self, ms:int):
        if self._dragging: self.posL.setText(fmt(ms))

    def _on_seek_release(self):
        self._dragging = False
        if self.player:
            try: self.player.setPosition(self.pos.value())
            except Exception: pass

    def _on_volume(self, v:int):
        if self.audio:
            try: self.audio.setVolume(v/100.0)
            except Exception: pass

    # ===== UI sync =====
    def _sync_play_icon(self, state):
        self.play.setText("■" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

```

## `kaya\ui\terminal_page.py`

```
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

```

## `kaya\ui\theme.py`

```
ACCENTS={'green':{'ACC':'#39FF14','ACCM':'#A4FFB2','BD':'#145c2f'},
         'blue': {'ACC':'#00D1FF','ACCM':'#9CEBFF','BD':'#0b4d63'},
         'red':  {'ACC':'#FF3B3B','ACCM':'#FFB3B3','BD':'#5a1111'}}
_cur='green'
def qss(ac='green'):
    a=ACCENTS.get(ac,ACCENTS['green']); ACC=a['ACC']; ACCM=a['ACCM']; BD=a['BD']
    return f"""
*{{font-family:'Cascadia Mono','JetBrains Mono','Consolas','Courier New',monospace;font-size:12pt;letter-spacing:.2px;}}
QMainWindow,QWidget{{background:#000;color:#E9FFE9;
background-image:radial-gradient(circle at 50% -20%,rgba(0,255,128,.06),rgba(0,0,0,0)40%),
repeating-linear-gradient(to bottom,rgba(0,255,0,.025)0,rgba(0,255,0,.025)1px,rgba(0,0,0,0)1px,rgba(0,0,0,0)3px);}}
QFrame,QListWidget,QTreeView,QTextEdit,QPlainTextEdit,QLineEdit,QCalendarWidget,QTextBrowser,QGroupBox,QMenu{{background:#000;color:#DFFFE0;border:1px solid {BD};border-radius:3px;}}
QPushButton,QToolButton{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #010,stop:1 #000);color:{ACCM};border:1px solid {BD};padding:6px 10px;border-radius:3px;}}
QPushButton:hover,QToolButton:hover{{border-color:{ACC};color:#F2FFF2;}}
QPushButton:checked,QToolButton:checked{{background:#031;border-color:{ACC};}}
.navbtn{{min-height:52px;max-width:80px;font-weight:800;color:{ACCM};}}
.navbtn:hover{{color:#D8FFE0;}} .navbtn:checked{{background:#031;color:#fff;border-color:{ACC};}}
QLabel#accent{{color:{ACC};letter-spacing:.6px;font-weight:900;}}
QSlider::groove:horizontal{{height:3px;background:{BD};border:0;}}
QSlider::handle:horizontal{{width:10px;background:{ACC};border:1px solid {ACCM};margin:-5px 0;}}
QSlider#pos::groove:horizontal{{height:2px;background:{BD};}}
QSlider#pos::handle:horizontal{{width:8px;background:{ACC};border:1px solid {ACCM};margin:-6px 0;}}
QCalendarWidget QToolButton{{background:#000;color:{ACCM};border:1px solid {BD};padding:0 4px;border-radius:3px;min-height:16px;}}
QCalendarWidget QToolButton:hover{{border-color:{ACC};}}
QCalendarWidget QAbstractItemView:enabled{{selection-background-color:#052;selection-color:#fff;font-size:9pt;outline:none;}}
QListWidget#tracklist{{outline:none;background:#000;border:1px solid {BD};
background-image:linear-gradient(to bottom,rgba(0,255,0,.09),rgba(0,255,0,.02)),
repeating-linear-gradient(to bottom,rgba(0,255,0,.04)0,rgba(0,255,0,.04)1px,rgba(0,0,0,0)1px,rgba(0,0,0,0)5px);}}
QListWidget#tracklist::item{{padding:4px 8px;border-bottom:1px dashed {BD};}}
QListWidget#tracklist::item:selected{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #042,stop:1 #063);color:#EAFFEA;border-bottom:1px solid {ACC};}}
#toast{{background:rgba(0,0,0,.88);border:1px solid {ACC};color:#E7FFE7;padding:6px 10px;border-radius:3px;}}
"""
def apply(win,accent='green'): global _cur; _cur=accent; win.setStyleSheet(qss(accent))
def current(): return ACCENTS.get(_cur,ACCENTS['green'])

```

## `kaya\vaults\DefaultVault\workspace\agenda\timeline\2025-10-19.json`

```
[]
```

## `kaya\vaults\DefaultVault\workspace\agenda\timeline\2025\10\2025-10-19.json`

```
[
  {
    "time": "15:00",
    "text": "HFGHFGH"
  }
]
```

## `kaya\vaults\DefaultVault\workspace\agenda\todos\2025-09.json`

```
{
  "2025-09-30": [
    {
      "done": false,
      "tag": "exam",
      "text": "Kimya Sınavı"
    },
    {
      "done": false,
      "tag": "homework",
      "text": "Ödevi yap"
    }
  ]
}
```

## `kaya\vaults\DefaultVault\workspace\agenda\todos\2025-10.json`

```
{
  "2025-10-19": [
    {
      "done": false,
      "tag": "homework",
      "text": "exam: Sınav var"
    },
    {
      "done": false,
      "tag": "homework",
      "text": "ödevim"
    },
    {
      "done": false,
      "tag": "birthday",
      "text": "hkhjk"
    }
  ],
  "2025-10-20": []
}
```

## `kaya\vaults\DefaultVault\workspace\agenda\todos_2025-11-09.json`

```
[]
```

## `run_gui.py`

```
from kaya.ui.main import run
if __name__=='__main__': run()

```

## `tools\snapshot_repo.py`

```
﻿import argparse, pathlib

SKIP_DIRS = {".git", ".venv", "__pycache__", "build", "dist", ".mypy_cache", ".pytest_cache"}

def should_skip(p: pathlib.Path) -> bool:
    parts = set(p.parts)
    return any(s in parts for s in SKIP_DIRS)

def read_text(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"# <read error: {e}>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="docs/retro_snapshot.md")
    ap.add_argument("--exts", default=".py,.qss,.ui,.yaml,.yml,.json", help="Virgülle ayırın")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    exts = {e.strip().lower() for e in args.exts.split(",") if e.strip()}
    files = []
    for p in root.rglob("*"):
        if p.is_dir():
            if should_skip(p):
                continue
            else:
                continue
        if should_skip(p):
            continue
        if p.suffix.lower() in exts:
            files.append(p)

    files = sorted(files, key=lambda x: str(x).lower())

    out = []
    out.append("# KAYA RetroFutura — Code Snapshot")
    out.append(f"Root: `{root}`")
    out.append("")
    out.append("---")
    out.append("")

    for f in files:
        rel = f.relative_to(root)
        out.append(f"## `{rel}`")
        out.append("")
        out.append("```")
        out.append(read_text(f))
        out.append("```")
        out.append("")

    pathlib.Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {args.out} (files: {len(files)})")

if __name__ == "__main__":
    main()

```
