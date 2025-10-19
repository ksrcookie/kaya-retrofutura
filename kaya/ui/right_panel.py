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
