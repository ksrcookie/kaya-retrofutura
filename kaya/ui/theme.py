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
