# kaya/ui/mini_calendar.py
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
