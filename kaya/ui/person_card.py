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
