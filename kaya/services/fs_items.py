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
