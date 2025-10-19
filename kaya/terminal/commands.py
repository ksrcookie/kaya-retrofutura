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
