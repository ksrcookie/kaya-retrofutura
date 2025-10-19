from pathlib import Path
APP_NAME='K.A.Y.A — Kişisel Akıllı Yardımcı Asistan'
BASE_DIR=Path(__file__).resolve().parents[1]
VAULTS_DIR=BASE_DIR/'vaults'
DEFAULT_VAULT='DefaultVault'
WORK=VAULTS_DIR/DEFAULT_VAULT/'workspace'
FILES=WORK/'files'; PROJECTS=WORK/'projects'; AGENDA=WORK/'agenda'; MEDIA=WORK/'media'
for d in (VAULTS_DIR, WORK, FILES, PROJECTS, AGENDA, MEDIA): d.mkdir(parents=True, exist_ok=True)
