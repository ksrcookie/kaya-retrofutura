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
