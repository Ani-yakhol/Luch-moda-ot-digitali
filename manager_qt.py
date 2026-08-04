"""
manager_qt.py — ממשק ניהול PyQt6 ללוח המודעות הדיגיטלי
מופעל כתהליך-בן מ-digital_bulletin.py
"""
import sys, os, json, hashlib, zipfile, shutil
from pathlib import Path
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QRadioButton, QButtonGroup, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QInputDialog,
    QSplitter, QStackedWidget, QTextEdit, QSlider, QColorDialog,
    QGridLayout, QSizePolicy, QDialog, QDialogButtonBox, QAbstractItemView,
    QGroupBox, QFormLayout,
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QObject, QThread,
    QPropertyAnimation, QEasingCurve, QPoint,
)
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPalette, QPixmap, QPainter,
    QLinearGradient, QBrush, QFontMetrics, QCursor,
)

# ── Config path ──────────────────────────────────────────────────────────────
CFG = Path(os.environ.get("BULLETIN_CFG", str(Path.home() / ".digital_bulletin" / "config.json")))

ZMANIM_KEYS = {
    "alot":           "עלות השחר",
    "misheyakir":     "משיכיר",
    "sunrise":        "הנץ החמה",
    "shma_mga":       'סוף ק"ש — מג"א',
    "shma_gra":       'סוף ק"ש — גר"א',
    "tfila_mga":      'סוף תפלה — מג"א',
    "tfila_gra":      'סוף תפלה — גר"א',
    "chatzot":        "חצות היום",
    "mincha_gedola":  "מנחה גדולה",
    "mincha_ketana":  "מנחה קטנה",
    "plag":           "פלג המנחה",
    "sunset":         "שקיעת החמה",
    "tzait_18":       "צאת הכוכבים (18 דק׳)",
    "tzait_42":       'מוצ"ש — רבינו תם',
}
PANEL_NAMES = {
    "clock":          "שעה",
    "date":           "תאריך",
    "text":           "טקסט",
    "ad":             "מודעה / תמונות",
    "zmanim":         "זמני הלכה",
    "_schedule":      "לוח זמנים",
    "element":        "אלמנט עיצובי",
    "notice":         "הודעה צפה",
    "screen_msg":     "הודעת מסך",
    "background":     "רקע ראשי",
    "fullscreen_msg": "הודעת מסך מלאה",
}
PANEL_ICONS = {
    "clock":"🕐","date":"📅","text":"📝","ad":"🖼","zmanim":"🕍",
    "_schedule":"📋","element":"🎨","notice":"📢","screen_msg":"💬",
    "background":"🖥","fullscreen_msg":"📺",
}
ANALOG_STYLE_NAMES = {
    "classic":  "קלאסי",
    "minimal":  "מינימלי",
    "roman":    "ספרות רומיות",
    "railway":  "תחנת רכבת",
}
# Shared color constants matching digital_bulletin.py
GOLD  = "#f5a623"
BLUE  = "#3a7bd5"
TEXT  = "#dde0ff"

def get_effective_zmanim_list(cfg_d):
    """Return ordered list of (uid, key, display_name) from zmanim_keys_cfg or ZMANIM_KEYS fallback."""
    loc = cfg_d.get("location", {}) if isinstance(cfg_d, dict) else {}
    entries = loc.get("zmanim_keys_cfg", None)
    if entries:
        result = []
        for e in entries:
            key = e.get("key","")
            custom = e.get("custom_name","").strip()
            name = custom if custom else ZMANIM_KEYS.get(key, key)
            result.append((e.get("uid", key), key, name))
        return result
    return [(k, k, v) for k, v in ZMANIM_KEYS.items()]

METHOD_LABELS = [
    ("", "ברירת מחדל (כהגדרה הכללית)"),
    ("kosherzmanim", "KosherZmanim — מדויק ביותר"),
    ("astral", "Astral / pytz — מובנה"),
]

CITIES = {
    "ירושלים":       (31.7683,35.2137,754,"Asia/Jerusalem"),
    "תל אביב":       (32.0853,34.7818,5,"Asia/Jerusalem"),
    "חיפה":          (32.7940,34.9896,146,"Asia/Jerusalem"),
    "בני ברק":       (32.0814,34.8340,28,"Asia/Jerusalem"),
    "ביתר עילית":    (31.6960,35.1190,680,"Asia/Jerusalem"),
    "מודיעין עילית": (31.9318,35.0426,310,"Asia/Jerusalem"),
    "קרית ספר":      (31.9318,35.0426,310,"Asia/Jerusalem"),
    "אלעד":          (32.0525,34.9514,120,"Asia/Jerusalem"),
    "אשדוד":         (31.8044,34.6553,30,"Asia/Jerusalem"),
    "אשקלון":        (31.6688,34.5742,40,"Asia/Jerusalem"),
    "באר שבע":       (31.2524,34.7913,270,"Asia/Jerusalem"),
    "נתניה":         (32.3215,34.8532,15,"Asia/Jerusalem"),
    "פתח תקווה":     (32.0841,34.8878,45,"Asia/Jerusalem"),
    "ראשון לציון":   (31.9730,34.7925,25,"Asia/Jerusalem"),
    "רמת גן":        (32.0681,34.8236,45,"Asia/Jerusalem"),
    "רחובות":        (31.8928,34.8113,50,"Asia/Jerusalem"),
    "הרצליה":        (32.1663,34.8432,15,"Asia/Jerusalem"),
    "כפר סבא":       (32.1752,34.9058,60,"Asia/Jerusalem"),
    "מודיעין":       (31.8976,35.0097,280,"Asia/Jerusalem"),
    "בית שמש":       (31.7487,34.9887,270,"Asia/Jerusalem"),
    "ראש העין":      (32.0959,34.9563,85,"Asia/Jerusalem"),
    "עפולה":         (32.6052,35.2888,70,"Asia/Jerusalem"),
    "נצרת":          (32.7021,35.2978,355,"Asia/Jerusalem"),
    "נהריה":         (33.0039,35.0975,10,"Asia/Jerusalem"),
    "עכו":           (32.9278,35.0828,5,"Asia/Jerusalem"),
    "טבריה":         (32.7921,35.5305,-210,"Asia/Jerusalem"),
    "צפת":           (32.9646,35.4956,900,"Asia/Jerusalem"),
    "קריית שמונה":   (33.2089,35.5706,140,"Asia/Jerusalem"),
    "בית שאן":       (32.4955,35.4994,-120,"Asia/Jerusalem"),
    "אילת":          (29.5577,34.9519,15,"Asia/Jerusalem"),
    "ערד":           (31.2587,35.2124,620,"Asia/Jerusalem"),
    "מצפה רמון":     (30.6100,34.8017,860,"Asia/Jerusalem"),
    "דימונה":        (31.0691,35.0327,590,"Asia/Jerusalem"),
    "קרית גת":       (31.6100,34.7642,110,"Asia/Jerusalem"),
    "לוד":           (31.9516,34.8950,70,"Asia/Jerusalem"),
    "רמלה":          (31.9280,34.8680,60,"Asia/Jerusalem"),
    "חולון":         (32.0114,34.7744,15,"Asia/Jerusalem"),
    "בת ים":         (32.0167,34.7500,10,"Asia/Jerusalem"),
    "ניו יורק":      (40.7128,-74.0060,10,"America/New_York"),
    "לוס אנג׳לס":   (34.0522,-118.2437,93,"America/Los_Angeles"),
    "שיקגו":         (41.8781,-87.6298,181,"America/Chicago"),
    "מיאמי":         (25.7617,-80.1918,2,"America/New_York"),
    "מונטריאול":     (45.5017,-73.5673,233,"America/Toronto"),
    "טורונטו":       (43.6532,-79.3832,76,"America/Toronto"),
    "לונדון":        (51.5074,-0.1278,11,"Europe/London"),
    "מנצ'סטר":       (53.4808,-2.2426,38,"Europe/London"),
    "פריז":          (48.8566,2.3522,35,"Europe/Paris"),
    "אמסטרדם":       (52.3676,4.9041,5,"Europe/Amsterdam"),
    "אנטוורפן":      (51.2194,4.4025,10,"Europe/Brussels"),
    "ציריך":         (47.3769,8.5417,408,"Europe/Zurich"),
    "ז'נבה":         (46.2044,6.1432,373,"Europe/Zurich"),
    "ברלין":         (52.5200,13.4050,34,"Europe/Berlin"),
    "פרנקפורט":      (50.1109,8.6821,109,"Europe/Berlin"),
    "וינה":          (48.2082,16.3738,170,"Europe/Vienna"),
    "ורשה":          (52.2297,21.0122,92,"Europe/Warsaw"),
    "רומא":          (41.9028,12.4964,21,"Europe/Rome"),
    "ברצלונה":       (41.3851,2.1734,12,"Europe/Madrid"),
    "מוסקבה":        (55.7558,37.6173,156,"Europe/Moscow"),
    "איסטנבול":      (41.0082,28.9784,35,"Europe/Istanbul"),
    "יוהנסבורג":     (-26.2041,28.0473,1753,"Africa/Johannesburg"),
    "קייפ טאון":     (-33.9249,18.4241,17,"Africa/Johannesburg"),
    "מלבורן":        (-37.8136,144.9631,25,"Australia/Melbourne"),
    "סידני":         (-33.8688,151.2093,25,"Australia/Sydney"),
    "דובאי":         (25.2048,55.2708,5,"Asia/Dubai"),
}

# ── Stylesheet ───────────────────────────────────────────────────────────────
def get_stylesheet():
    return """
/* ── Global ── */
QMainWindow, QDialog { background: #f0f4fb; }
QWidget { font-family: 'Segoe UI', Arial; font-size: 13px; color: #1a2847; }

/* ── Header bar ── */
#header {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1b3a7a, stop:1 #2d5ec0);
    border-bottom: 2px solid #1430a0;
}
#logo_label {
    color: white; font-size: 18px; font-weight: bold; padding: 0 18px;
}
#version_label { color: #a0bfff; font-size: 10px; padding: 0 8px; }
#status_label  { color: #80ffcc; font-size: 11px; padding: 0 12px; }

/* ── Header buttons ── */
#hdr_btn {
    background: rgba(255,255,255,0.12);
    color: #ddeeff; border: 1px solid rgba(255,255,255,0.2);
    border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: bold;
}
#hdr_btn:hover  { background: rgba(255,255,255,0.25); color: white; }
#hdr_btn:pressed{ background: rgba(255,255,255,0.08); }
#hdr_close  { color: #ffaaaa; }
#hdr_close:hover{ background: #aa2222; color: white; border-color: #aa2222; }
#hdr_exit   { color: #ffd0a0; }
#hdr_exit:hover { background: #883300; color: white; border-color: #883300; }
#hdr_refresh{ color: #a0ffcc; }
#hdr_announce{ background: rgba(200,120,0,0.35); color: #ffe0a0; }
#hdr_announce:hover{ background: #c47a00; color: white; }

/* ── Tab widget ── */
QTabWidget::pane {
    border: none; background: #f0f4fb;
}
QTabBar::tab {
    background: #e0e8f8; color: #4a5580; border: none;
    padding: 10px 24px; font-size: 13px; font-weight: bold;
    border-radius: 0; margin-left: 1px;
    border-bottom: 3px solid transparent;
}
QTabBar::tab:selected {
    background: #f0f4fb; color: #1b3a7a;
    border-bottom: 3px solid #2d5ec0;
}
QTabBar::tab:hover:!selected { background: #d0dcf4; color: #1a2847; }

/* ── Sidebar (panel list) ── */
#sidebar {
    background: #e8edf8;
    border-left: 1px solid #c8d4ec;
}
#sidebar_title { color: #1b3a7a; font-size: 14px; font-weight: bold; padding: 4px 12px; }
#sidebar_sub   { color: #6070a0; font-size: 10px; padding: 0 12px 6px; }

/* ── Panel list ── */
QListWidget {
    background: white; border: 1px solid #d0dcf0;
    border-radius: 8px; outline: none; padding: 4px;
}
QListWidget::item {
    padding: 10px 14px; border-radius: 6px; margin: 2px;
    border: 1px solid transparent;
}
QListWidget::item:selected {
    background: #e8f0ff; color: #1b3a7a;
    border: 1px solid #a0b8e8;
}
QListWidget::item:hover:!selected { background: #f0f5ff; }

/* ── Cards ── */
#card {
    background: white; border-radius: 12px;
    border: 1px solid #dde8f8;
}
#card_title {
    color: #1b3a7a; font-size: 13px; font-weight: bold;
    padding: 12px 16px 6px;
    border-bottom: 1px solid #eef2fc;
}
#section_title {
    color: #2d5ec0; font-size: 12px; font-weight: bold;
    padding: 4px 0; margin-top: 6px;
}

/* ── Inputs ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
    background: #f8faff; border: 1.5px solid #c8d8f0;
    border-radius: 7px; padding: 6px 10px;
    font-size: 13px; color: #1a2847;
    selection-background-color: #4a7ae0;
}
QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
    border: 1.5px solid #2d5ec0;
    background: white;
}
QLineEdit:read-only { background: #eef2fa; color: #6070a0; }

QComboBox {
    background: #f8faff; border: 1.5px solid #c8d8f0;
    border-radius: 7px; padding: 6px 10px;
    font-size: 13px; color: #1a2847;
}
QComboBox:focus { border: 1.5px solid #2d5ec0; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: white; border: 1px solid #c8d8f0;
    selection-background-color: #e0ecff;
    selection-color: #1a2847;
}

/* ── Buttons ── */
QPushButton {
    background: #2d5ec0; color: white; border: none;
    border-radius: 8px; padding: 9px 22px; font-size: 13px; font-weight: bold;
}
QPushButton:hover   { background: #4a7ae0; }
QPushButton:pressed { background: #1b3a7a; }
QPushButton:disabled{ background: #b0bcd8; color: #8090b0; }

#btn_secondary {
    background: #e8edf8; color: #2d5ec0;
    border: 1.5px solid #b0c4e8;
}
#btn_secondary:hover { background: #d8e4f8; }

#btn_danger { background: #c02020; }
#btn_danger:hover { background: #e03030; }

#btn_success { background: #1a9a5c; }
#btn_success:hover { background: #22bb6e; }

#btn_warn { background: #c47a00; }
#btn_warn:hover { background: #e09000; }

#btn_flat {
    background: transparent; color: #2d5ec0; border: none;
    font-size: 12px; padding: 4px 10px; font-weight: normal;
}
#btn_flat:hover { color: #1b3a7a; text-decoration: underline; }

#color_swatch {
    border: 2px solid #c8d8f0; border-radius: 6px;
    padding: 2px; min-width: 36px; min-height: 26px;
}
#color_swatch:hover { border-color: #2d5ec0; }

/* ── Checkboxes & Radios ── */
QCheckBox, QRadioButton {
    spacing: 10px; color: #1a2847; padding: 2px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px; height: 18px;
}
QCheckBox::indicator:unchecked { border: 2px solid #a0b4d0; border-radius: 4px; background: white; }
QCheckBox::indicator:checked   {
    border: 2px solid #2d5ec0; border-radius: 4px;
    background: #2d5ec0;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTIgOGw0IDQgOC04IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiLz48L3N2Zz4=);
}
QRadioButton::indicator:unchecked{ border: 2px solid #a0b4d0; border-radius: 9px; background: white; }
QRadioButton::indicator:checked  { border: 2px solid #2d5ec0; border-radius: 9px; background: #2d5ec0; }

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #eef2fa; border: none; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #b0c4e0; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #7090c0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #eef2fa; border: none; height: 8px;
}
QScrollBar::handle:horizontal {
    background: #b0c4e0; border-radius: 4px;
}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #d8e4f4; }

/* ── Group boxes ── */
QGroupBox {
    border: 1.5px solid #dde8f8; border-radius: 8px;
    margin-top: 14px; padding: 10px;
    font-weight: bold; color: #2d5ec0;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 8px; left: 16px;
}

/* ── Treeview / Table ── */
QHeaderView::section {
    background: #e8edf8; color: #4a5580; border: none;
    padding: 8px; font-weight: bold; font-size: 12px;
    border-bottom: 2px solid #c0d0e8;
}
"""

# ── Helper widgets ───────────────────────────────────────────────────────────
def card(title="", min_h=0):
    """Create a styled white card widget."""
    c = QFrame()
    c.setObjectName("card")
    lay = QVBoxLayout(c)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(0)
    if title:
        t = QLabel(title)
        t.setObjectName("card_title")
        lay.addWidget(t)
    if min_h: c.setMinimumHeight(min_h)
    return c, lay


def section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("section_title")
    return lbl


def hline():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def form_row(label_text, widget, label_w=170, compact=False):
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 2, 0, 2)
    hl.setSpacing(8)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(label_w)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet("color:#4a5580;font-size:12px;")
    # RTL: label on right, widget immediately to its left
    hl.addWidget(lbl)
    hl.addWidget(widget)
    if compact:
        # Push widget right (next to label) by filling the remaining left space with stretch
        hl.addStretch()
    return row


def color_btn(color="#ffffff", parent=None):
    """Button that shows a color and opens color picker."""
    btn = QPushButton()
    btn.setObjectName("color_swatch")
    btn.setFixedSize(44, 30)
    btn._color = color

    def refresh():
        btn.setStyleSheet(
            f"#color_swatch{{background:{btn._color};"
            f"border:2px solid #c8d8f0;border-radius:6px;}}"
            f"#color_swatch:hover{{border-color:#2d5ec0;}}"
        )

    def pick():
        c = QColorDialog.getColor(QColor(btn._color), parent, "בחר צבע")
        if c.isValid():
            btn._color = c.name()
            refresh()

    btn.clicked.connect(pick)
    refresh()
    return btn


def scroll_wrap(widget):
    """Wrap a widget in a scroll area."""
    sa = QScrollArea()
    sa.setWidget(widget)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    return sa

# ── Config helper ────────────────────────────────────────────────────────────
class Cfg:
    def __init__(self, path=CFG):
        self.path = Path(path)
        # Try main config, then backup (crash recovery)
        self.d = {"password_hash":"","location":{},"display":{},"panels":[],"_nid":1,"reminders":[]}
        for candidate in [self.path, self.path.with_suffix(".bak")]:
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    self.d = json.load(f)
                break
            except: pass

    def save(self):
        """Atomic save: write to .tmp, rename — prevents config corruption on crash."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=2)
            if self.path.exists():
                try: self.path.replace(self.path.with_suffix(".bak"))
                except: pass
            tmp.replace(self.path)
        except:
            try: tmp.unlink(missing_ok=True)
            except: pass

    def panels(self): return self.d.get("panels", [])
    def reminders(self): return self.d.setdefault("reminders", [])
    def display(self): return self.d.setdefault("display", {})
    def location(self): return self.d.setdefault("location", {})
    def fullscreen_msg(self):
        return self.d.setdefault("fullscreen_msg", {
            "bg_color":"#060015","font_color":"#f5a623",
            "font_size":48,"content":"","duration":0,
        })

    def has_pw(self): return bool(self.d.get("password_hash",""))
    def check_pw(self, pw): return hashlib.sha256(pw.encode()).hexdigest()==self.d.get("password_hash","")
    def set_pw(self, pw):
        self.d["password_hash"] = hashlib.sha256(pw.encode()).hexdigest() if pw else ""
        self.save()

    def display_boards(self): return self.d.setdefault("display_boards", [])

    def zmanim_keys_cfg(self):
        """Return ordered list of zmanim key entries.
        Each entry: {uid, key, custom_name, method}
        uid is a unique string id for editing/removal.
        Falls back to ZMANIM_KEYS if not configured."""
        loc = self.location()
        existing = loc.get("zmanim_keys_cfg", None)
        if existing is not None:
            return existing
        # Build default from ZMANIM_KEYS
        default = []
        for i, (k, v) in enumerate(ZMANIM_KEYS.items()):
            default.append({"uid": str(i), "key": k, "custom_name": "", "method": ""})
        loc["zmanim_keys_cfg"] = default
        return default

    def add_display_board(self):
        boards = self.display_boards()
        nid = max((b.get("id",0) for b in boards), default=0) + 1
        board = {
            "id": nid,
            "name": f"לוח תצוגה {nid}",
            "enabled": True,
            "bg_color": "#070714",
            "bg_image": "",
            "show_stars": True,
            "gradient": True,
            "schedule": {
                "hours_enabled": False, "hour_from": 8, "hour_to": 20,
                "days_enabled": False,  "active_days": list(range(7)),
            }
        }
        boards.append(board); self.save(); return board

    def del_display_board(self, bid):
        self.d["display_boards"] = [b for b in self.display_boards() if b.get("id") != bid]
        self.save()

    def get_display_board(self, bid):
        for b in self.display_boards():
            if b.get("id") == bid: return b
        return None

    # ── design themes (ערכות עיצוב) ───────────────────────────────────────────
    def design_themes(self):
        """Return list of saved design themes. Each: {id, name, display, panels, _nid}"""
        return self.d.setdefault("design_themes", [])

    def current_theme_id(self):
        return self.d.get("current_theme_id", None)

    def set_current_theme_id(self, tid):
        self.d["current_theme_id"] = tid
        self.save()

    def add_design_theme(self, name):
        """Save current state to active theme (if any), create a blank new theme, switch to it."""
        import copy
        # Persist current live state back into the currently active theme
        current_tid = self.d.get("current_theme_id")
        if current_tid is not None:
            self.save_to_theme(current_tid)
        themes = self.design_themes()
        new_id = max((t.get("id", 0) for t in themes), default=0) + 1
        blank_display = {"bg_color": "#070714", "bg_image": "", "show_stars": True, "gradient": True}
        theme = {
            "id": new_id,
            "name": name,
            "display": copy.deepcopy(blank_display),
            "panels": [],
            "_nid": 1,
        }
        themes.append(theme)
        # Switch live state to blank
        self.d["display"] = copy.deepcopy(blank_display)
        self.d["panels"]  = []
        self.d["_nid"]    = 1
        self.d["current_theme_id"] = new_id
        self.save()
        return theme

    def save_to_theme(self, tid):
        """Overwrite existing theme with current live state."""
        import copy
        for t in self.design_themes():
            if t.get("id") == tid:
                t["display"] = copy.deepcopy(self.d.get("display", {}))
                t["panels"]  = copy.deepcopy(self.d.get("panels", []))
                t["_nid"]    = self.d.get("_nid", 1)
                self.save()
                return

    def load_design_theme(self, tid):
        """Persist current live state to its theme, then load the selected theme."""
        import copy
        # Save current state before switching
        current_tid = self.d.get("current_theme_id")
        if current_tid is not None and current_tid != tid:
            self.save_to_theme(current_tid)
        for t in self.design_themes():
            if t.get("id") == tid:
                blank_display = {"bg_color": "#070714", "bg_image": "", "show_stars": True, "gradient": True}
                self.d["display"] = copy.deepcopy(t.get("display", blank_display))
                self.d["panels"]  = copy.deepcopy(t.get("panels", []))
                self.d["_nid"]    = t.get("_nid", 1)
                self.d["current_theme_id"] = tid
                self.save()
                return True
        return False

    def sync_to_current_theme(self):
        """Persist live state into the currently selected theme (call on every edit-save)."""
        tid = self.d.get("current_theme_id")
        if tid is not None:
            self.save_to_theme(tid)

    def rename_design_theme(self, tid, new_name):
        for t in self.design_themes():
            if t.get("id") == tid:
                t["name"] = new_name
                self.save()
                return

    def delete_design_theme(self, tid):
        self.d["design_themes"] = [t for t in self.design_themes() if t.get("id") != tid]
        if self.d.get("current_theme_id") == tid:
            self.d["current_theme_id"] = None
        self.save()

    def get_design_theme(self, tid):
        for t in self.design_themes():
            if t.get("id") == tid: return t
        return None

    def add_panel(self, ptype):
        nid = self.d.get("_nid", 1)
        self.d["_nid"] = nid + 1
        defaults = {
            "id":nid,"type":ptype,"enabled":True,"layer":1,
            "x":40,"y":40,"width":350,"height":200,
            "bg_color":"#111128","bg_transparent":False,"bg_image":"",
            "border_color":"#3a7bd5","border_width":2,"border_transparent":False,
        }
        # Type-specific defaults for better out-of-box experience
        extra = {
            "notice":  {"width":900,"height":80,"y":620,"bg_color":"#1a0a00",
                        "border_color":"#f5a623","border_width":3,
                        "content":"הודעה חשובה","font_family":"Arial",
                        "font_size":26,"font_color":"#f5a623","bold":True,
                        "scroll":True,"scroll_speed":2,"scroll_dir":"rtl",
                        "popup_only":True,"popup_duration":30},
            "screen_msg":{"width":600,"height":140,"x":160,"y":460,
                          "bg_color":"#0d0d22","border_color":"#f5a623","border_width":3,
                          "content":"הודעה","font_family":"Arial",
                          "font_size":28,"font_color":"#f5a623","bold":True,
                          "italic":False,"align":"center","padding":16},
            "clock":   {"width":280,"height":120,"font_family":"Arial",
                        "font_size":56,"show_seconds":True,
                        "clock_style":"digital","time_format":"24","analog_style":"classic",
                        "font_color":"#3a7bd5"},
            "date":    {"width":280,"height":160,"font_family":"Arial",
                        "font_size":18,"show_weekday":True,"show_heb_date":True,"show_greg_date":True,
                        "show_holiday":True,"show_parasha":True,"israel":True,
                        "font_color":"#dde0ff"},

            "zmanim":  {"width":360,"height":490,"font_family":"Arial","font_size":14,
                        "label_color":"#9090cc","time_color":"#3a7bd5",
                        "highlight_color":"#f5a623","highlight_next":True},
            "_schedule":{"width":350,"height":200,"font_family":"Arial","font_size":20,
                         "font_color":"#ffffff","bold":False,"italic":False,"align":"right",
                         "events":[],"empty_text":"אין אירועים",
                         "name_font_family":"Arial","name_font_size":20,"name_font_color":"#ffffff",
                         "time_font_family":"Arial","time_font_size":20,"time_font_color":"#aaddff",
                         "day_rollover_hour":0,"day_rollover_minute":0},
            "element": {"width":200,"height":200,"bg_transparent":True,
                        "border_width":0,"border_transparent":True},
        }.get(ptype, {})
        defaults.update(extra)
        # Offset new panels so they don't all stack at same position
        same = [p for p in self.d["panels"] if p.get("type")==ptype]
        defaults["x"] = defaults.get("x",40) + len(same)*30
        defaults["y"] = defaults.get("y",40) + len(same)*30
        self.d["panels"].append(defaults)
        self.save()
        return defaults

    def del_panel(self, pid):
        self.d["panels"] = [p for p in self.d["panels"] if p.get("id") != pid]
        self.save()

    def get_panel(self, pid):
        for p in self.d["panels"]:
            if p.get("id") == pid: return p
        return None

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _collect_imgs(panels, disp):
        """Return set of real image paths found across panels and display dict."""
        imgs = set()
        for p in panels:
            for key in ("bg_image", "image_path"):
                if p.get(key) and os.path.exists(p[key]):
                    imgs.add(p[key])
            for img in p.get("images", []):
                if img and os.path.exists(img):
                    imgs.add(img)
        if disp.get("bg_image") and os.path.exists(disp["bg_image"]):
            imgs.add(disp["bg_image"])
        return imgs

    @staticmethod
    def _rel_path(p):
        return "images/" + os.path.basename(p) if p and os.path.exists(p) else (p or "")

    @staticmethod
    def _fix_path(p, img_dir):
        if p and p.startswith("images/"):
            return str(img_dir / os.path.basename(p))
        return p or ""

    @classmethod
    def copy_image_to_store(cls, src_path):
        """Copy an image from any location into the app's images store.
        Returns the new internal path, or src_path unchanged on failure."""
        if not src_path or not os.path.exists(src_path):
            return src_path or ""
        img_dir = CFG.parent / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        dest = img_dir / os.path.basename(src_path)
        # If file already lives inside our store, nothing to do
        try:
            if dest.resolve() == Path(src_path).resolve():
                return str(dest)
        except Exception:
            pass
        # Handle name collisions: if same name but different content, rename
        import hashlib as _hl
        try:
            src_hash = _hl.md5(open(src_path, "rb").read()).hexdigest()
        except Exception:
            src_hash = ""
        if dest.exists():
            try:
                dst_hash = _hl.md5(open(dest, "rb").read()).hexdigest()
                if src_hash and src_hash == dst_hash:
                    return str(dest)  # identical file already in store
            except Exception:
                pass
            # Different file — use hash-prefixed name
            stem = Path(src_path).stem
            suffix = Path(src_path).suffix
            dest = img_dir / f"{stem}_{src_hash[:8]}{suffix}"
        try:
            import shutil as _sh
            _sh.copy2(src_path, dest)
            return str(dest)
        except Exception:
            return src_path  # fallback: keep original path

    @staticmethod
    def _panel_display_name(p):
        """Return human-readable panel name like 'לוח טקסט #4'."""
        ptype = p.get("type", "?")
        names = {
            "clock": "שעה", "date": "תאריך", "text": "טקסט",
            "ad": "מודעה / תמונות", "zmanim": "זמני הלכה",
            "_schedule": "לוח זמנים", "element": "אלמנט עיצובי",
            "notice": "הודעה צפה", "screen_msg": "הודעת מסך",
        }
        n = p.get("panel_name", "") or names.get(ptype, ptype)
        return f"לוח {n} #{p.get('id','?')}"

    # ── theme export/import (תצוגה) ──────────────────────────────────────────
    # ── shared helper: relativize image paths in a panels list ────────────────
    @staticmethod
    def _panels_relpath(panels):
        """Return (panels_copy, design_imgs_set) with image paths relativized."""
        import copy as _copy
        CONTENT_KEYS = {"content", "content_segments"}
        panels_copy = []
        design_imgs = set()
        for p in panels:
            ep = {k: v for k, v in p.items() if k not in CONTENT_KEYS}
            for key in ("bg_image", "image_path"):
                if ep.get(key) and os.path.exists(ep[key]):
                    design_imgs.add(ep[key])
                    ep[key] = "images/" + os.path.basename(ep[key])
            fixed_imgs = []
            for img_path in ep.get("images", []):
                if isinstance(img_path, dict):
                    path_val = img_path.get("path", "")
                    if path_val and os.path.exists(path_val):
                        design_imgs.add(path_val)
                        fixed_imgs.append(dict(img_path, path="images/" + os.path.basename(path_val)))
                    else:
                        fixed_imgs.append(img_path)
                elif img_path and os.path.exists(img_path):
                    design_imgs.add(img_path)
                    fixed_imgs.append("images/" + os.path.basename(img_path))
                else:
                    fixed_imgs.append(img_path)
            ep["images"] = fixed_imgs
            panels_copy.append(ep)
        return panels_copy, design_imgs

    def export_layout(self, dest):
        """Export current theme's design (no content text) + images.
        Returns (n_images, theme_name)."""
        self.sync_to_current_theme()
        tid = self.current_theme_id()
        theme_name = ""
        if tid is not None:
            t = self.get_design_theme(tid)
            if t:
                theme_name = t.get("name", "")
                panels_src = t.get("panels", [])
                disp_src = dict(t.get("display", {}))
            else:
                panels_src = self.panels(); disp_src = dict(self.display())
        else:
            panels_src = self.panels(); disp_src = dict(self.display())

        panels_copy, design_imgs = self._panels_relpath(panels_src)
        disp = disp_src
        if disp.get("bg_image") and os.path.exists(disp["bg_image"]):
            design_imgs.add(disp["bg_image"])
            disp["bg_image"] = "images/" + os.path.basename(disp["bg_image"])
        blob = {
            "export_type": "theme",
            "theme_name": theme_name,
            "display": disp,
            "panels": panels_copy,
            "_nid": self.d.get("_nid", 1),
        }
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("layout.json", json.dumps(blob, ensure_ascii=False, indent=2))
            for img in design_imgs:
                zf.write(img, "images/" + os.path.basename(img))
        return len(design_imgs), theme_name

    def import_layout(self, src, target_theme_id=None):
        """Import a theme zip into the specified theme (overwrite) or as a new theme.
        target_theme_id=None → add as new theme named by blob theme_name.
        Returns report: {panels, n_imgs, theme_name, is_new}."""
        img_dir = CFG.parent / "images"; img_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src, "r") as zf:
            blob = json.loads(zf.read("layout.json").decode())
            for name in zf.namelist():
                if name.startswith("images/") and name != "images/":
                    dest_p = img_dir / os.path.basename(name)
                    with zf.open(name) as s, open(dest_p, "wb") as d2:
                        d2.write(s.read())

        fix = lambda p: self._fix_path(p, img_dir)
        import copy as _copy

        panels = _copy.deepcopy(blob.get("panels", []))
        imported_panels = []
        for p in panels:
            p["bg_image"]   = fix(p.get("bg_image", ""))
            p["image_path"] = fix(p.get("image_path", ""))
            imgs_fixed = []
            for img in p.get("images", []):
                if isinstance(img, dict):
                    imgs_fixed.append(dict(img, path=fix(img.get("path", ""))))
                else:
                    imgs_fixed.append(fix(img))
            p["images"] = imgs_fixed
            imported_panels.append(self._panel_display_name(p))
        disp = _copy.deepcopy(blob.get("display", {}))
        if disp.get("bg_image"):
            disp["bg_image"] = fix(disp["bg_image"])
        nid = blob.get("_nid", 1)
        n_imgs = len([n for n in zipfile.ZipFile(src).namelist()
                      if n.startswith("images/") and n != "images/"])
        theme_name_from_blob = blob.get("theme_name", "") or "ערכת עיצוב חדשה"

        if target_theme_id is not None:
            # Overwrite existing theme
            for t in self.design_themes():
                if t.get("id") == target_theme_id:
                    t["display"] = disp
                    t["panels"]  = panels
                    t["_nid"]    = nid
                    if self.d.get("current_theme_id") == target_theme_id:
                        self.d["display"] = _copy.deepcopy(disp)
                        self.d["panels"]  = _copy.deepcopy(panels)
                        self.d["_nid"]    = nid
                    self.save()
                    return {"panels": imported_panels, "n_imgs": n_imgs,
                            "theme_name": t.get("name", theme_name_from_blob), "is_new": False}

        # Add as new theme
        current_tid = self.d.get("current_theme_id")
        if current_tid is not None:
            self.save_to_theme(current_tid)
        themes = self.design_themes()
        new_id = max((t.get("id", 0) for t in themes), default=0) + 1
        new_theme = {"id": new_id, "name": theme_name_from_blob,
                     "display": disp, "panels": panels, "_nid": nid}
        themes.append(new_theme)
        self.d["display"] = _copy.deepcopy(disp)
        self.d["panels"]  = _copy.deepcopy(panels)
        self.d["_nid"]    = nid
        self.d["current_theme_id"] = new_id
        self.save()
        return {"panels": imported_panels, "n_imgs": n_imgs,
                "theme_name": theme_name_from_blob, "is_new": True}

    # ── content export/import (תוכן) ─────────────────────────────────────────
    def export_content(self, dest):
        """Export panel content only (text/segments/ad images) → תוכן.zip"""
        CONTENT_TYPES = {"text", "screen_msg", "ad", "fullscreen_msg", "_schedule", "notice"}
        content_imgs = set()
        panels_content = []
        for p in self.panels():
            ptype = p.get("type", "")
            if ptype not in CONTENT_TYPES:
                continue
            ec = {
                "id": p.get("id"),
                "type": ptype,
                "panel_name": p.get("panel_name", ""),
                "display_name": self._panel_display_name(p),
                "content": p.get("content", ""),
                "content_segments": p.get("content_segments", []),
            }
            # ad images — entries may be plain strings or dicts {"path":...}
            fixed_imgs = []
            for entry in p.get("images", []):
                if isinstance(entry, str):
                    img_path = entry; meta = {}
                elif isinstance(entry, dict):
                    img_path = entry.get("path", ""); meta = {k:v for k,v in entry.items() if k!="path"}
                else:
                    continue
                if img_path and os.path.exists(img_path):
                    content_imgs.add(img_path)
                    fixed_entry = dict(meta, path="images/" + os.path.basename(img_path))
                    fixed_imgs.append(fixed_entry)
                else:
                    fixed_imgs.append(entry)
            ec["images"] = fixed_imgs
            panels_content.append(ec)
        # fullscreen_msg
        fm = dict(self.fullscreen_msg() if hasattr(self, "fullscreen_msg") else {})
        blob = {
            "export_type": "content",
            "panels": panels_content,
        }
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content.json", json.dumps(blob, ensure_ascii=False, indent=2))
            for img in content_imgs:
                zf.write(img, "images/" + os.path.basename(img))
        return len(content_imgs), panels_content

    def import_content(self, src):
        """Import content only; returns report dict with success/fail per panel."""
        img_dir = CFG.parent / "layout_images"; img_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(src, "r") as zf:
            blob = json.loads(zf.read("content.json").decode())
            for name in zf.namelist():
                if name.startswith("images/") and name != "images/":
                    dest_p = img_dir / os.path.basename(name)
                    with zf.open(name) as s, open(dest_p, "wb") as d2:
                        d2.write(s.read())

        fix = lambda p: self._fix_path(p, img_dir)
        report = {"success": [], "fail": []}

        for ec in blob.get("panels", []):
            pid = ec.get("id")
            display_name = ec.get("display_name", f"לוח #{pid}")
            # Find matching panel by id
            target = None
            for p in self.d.get("panels", []):
                if p.get("id") == pid:
                    target = p; break
            # Also check fullscreen_msg
            if pid is None and ec.get("type") == "fullscreen_msg":
                target = self.d.setdefault("fullscreen_msg", {})

            if target is not None:
                target["content"] = ec.get("content", "")
                target["content_segments"] = ec.get("content_segments", [])
                if "images" in ec:
                    target["images"] = [fix(img) for img in ec.get("images", [])]
                report["success"].append(display_name)
            else:
                report["fail"].append(display_name)

        self.save()
        return report

    # ── settings-only export/import ──────────────────────────────────────────
    def export_settings(self, dest):
        with open(dest, "w", encoding="utf-8") as f:
            json.dump({"location": self.location(), "display": self.display()}, f, ensure_ascii=False, indent=2)

    def import_settings(self, src):
        with open(src, "r", encoding="utf-8") as f: s = json.load(f)
        if "location" in s: self.d["location"].update(s["location"])
        if "display"  in s: self.d["display"].update(s["display"])
        self.save()

    # ── full export/import (הגדרות) ───────────────────────────────────────────
    def full_export(self, dest):
        """Export ALL design themes + settings + reminders + content + images → zip.
        Returns (n_images, themes_list)."""
        # First sync live state into current theme
        self.sync_to_current_theme()

        import copy as _copy
        all_imgs = set()
        rel = self._rel_path

        export = _copy.deepcopy(self.d)
        # Relativize live panels (for backward compat / non-theme users)
        export_panels = []
        for p in export.get("panels", []):
            ep = dict(p)
            for key in ("bg_image", "image_path"):
                if ep.get(key) and os.path.exists(ep[key]):
                    all_imgs.add(ep[key]); ep[key] = rel(ep[key])
            ep["images"] = [rel(i) if isinstance(i, str) else
                            dict(i, path=rel(i.get("path",""))) for i in ep.get("images", [])]
            export_panels.append(ep)
        export["panels"] = export_panels
        # Relativize live display
        disp = dict(export.get("display", {}))
        if disp.get("bg_image") and os.path.exists(disp["bg_image"]):
            all_imgs.add(disp["bg_image"])
        disp["bg_image"] = rel(disp.get("bg_image", ""))
        export["display"] = disp
        # Relativize and include all design_themes
        export_themes = []
        for t in export.get("design_themes", []):
            et = _copy.deepcopy(t)
            t_panels, t_imgs = self._panels_relpath(et.get("panels", []))
            all_imgs.update(t_imgs)
            et["panels"] = t_panels
            td = dict(et.get("display", {}))
            if td.get("bg_image") and os.path.exists(td["bg_image"]):
                all_imgs.add(td["bg_image"])
            td["bg_image"] = rel(td.get("bg_image", ""))
            et["display"] = td
            export_themes.append(et)
        export["design_themes"] = export_themes
        export["export_type"] = "full"

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("config_full.json", json.dumps(export, ensure_ascii=False, indent=2))
            for img in all_imgs:
                if img and os.path.exists(img):
                    zf.write(img, "images/" + os.path.basename(img))
        themes_list = [t.get("name","") for t in export.get("design_themes", [])]
        return len(all_imgs), themes_list

    def full_import(self, src):
        """Import complete config from zip; returns report dict."""
        img_dir = CFG.parent / "images"; img_dir.mkdir(parents=True, exist_ok=True)
        fix = lambda p: self._fix_path(p, img_dir)
        import copy as _copy
        with zipfile.ZipFile(src, "r") as zf:
            raw = json.loads(zf.read("config_full.json").decode("utf-8"))
            for name in zf.namelist():
                if name.startswith("images/") and name != "images/":
                    dest_p = img_dir / os.path.basename(name)
                    with zf.open(name) as s, open(dest_p, "wb") as d2:
                        d2.write(s.read())
        # Fix paths in live panels
        for p in raw.get("panels", []):
            p["bg_image"]   = fix(p.get("bg_image", ""))
            p["image_path"] = fix(p.get("image_path", ""))
            imgs_fixed = []
            for i in p.get("images", []):
                if isinstance(i, dict):
                    imgs_fixed.append(dict(i, path=fix(i.get("path",""))))
                else:
                    imgs_fixed.append(fix(i))
            p["images"] = imgs_fixed
        if raw.get("display", {}).get("bg_image"):
            raw["display"]["bg_image"] = fix(raw["display"]["bg_image"])
        # Fix paths in all design_themes
        imported_theme_names = []
        for t in raw.get("design_themes", []):
            for p in t.get("panels", []):
                p["bg_image"]   = fix(p.get("bg_image", ""))
                p["image_path"] = fix(p.get("image_path", ""))
                imgs_fixed = []
                for i in p.get("images", []):
                    if isinstance(i, dict):
                        imgs_fixed.append(dict(i, path=fix(i.get("path",""))))
                    else:
                        imgs_fixed.append(fix(i))
                p["images"] = imgs_fixed
            td = t.get("display", {})
            if td.get("bg_image"):
                td["bg_image"] = fix(td["bg_image"])
            imported_theme_names.append(t.get("name",""))
        # If imported file has no design_themes but has panels/display, wrap into one theme
        if not raw.get("design_themes") and (raw.get("panels") or raw.get("display")):
            import copy as _copy2
            single_theme = {
                "id": 1,
                "name": "ערכת עיצוב חדשה",
                "display": _copy.deepcopy(raw.get("display", {})),
                "panels":  _copy.deepcopy(raw.get("panels", [])),
                "_nid": raw.get("_nid", 1),
            }
            raw.setdefault("design_themes", [single_theme])
            imported_theme_names = ["ערכת עיצוב חדשה"]
        self.d = raw
        self.save()
        # Build report
        sections = []
        if raw.get("display"):   sections.append("תצוגה")
        if raw.get("location"):  sections.append("זמן ומיקום")
        if raw.get("settings"):  sections.append("הגדרות")
        if raw.get("reminders"): sections.append("תזכורות")
        if raw.get("panels"):    sections.append(f"לוחות ({len(raw['panels'])} לוחות)")
        return {"sections": sections, "theme_names": imported_theme_names}

    def add_reminder(self,text,rem_type="personal",dt_str="",zman="",offset_min=0,
                     days=None,skip_shabbat=True,skip_holidays=False,recurring="daily",
                     notify_visual=True,notify_sound=False,notice_panel_id=None,
                     sound_type="beep",sound_file=""):
        rem=self.reminders()
        nid=max((r.get("id",0) for r in rem),default=0)+1
        rem.append({"id":nid,"text":text,"rem_type":rem_type,"dt":dt_str,
                    "zman":zman,"offset_min":offset_min,
                    "days":days if days is not None else list(range(7)),
                    "skip_shabbat":skip_shabbat,"skip_holidays":skip_holidays,
                    "recurring":recurring,"notify_visual":notify_visual,
                    "notify_sound":notify_sound,"notice_panel_id":notice_panel_id,
                    "sound_type":sound_type,"sound_file":sound_file,
                    "done":False,"last_triggered":""})
        self.save(); return nid

    def del_reminder(self,rid):
        self.d["reminders"]=[r for r in self.reminders() if r.get("id")!=rid]
        self.save()

    def mark_reminder(self,rid,done=True):
        for r in self.reminders():
            if r.get("id")==rid: r["done"]=done; r["last_triggered"]=""; break
        self.save()

# ── Panel Editor ─────────────────────────────────────────────────────────────
class PanelEditor(QWidget):
    saved = pyqtSignal()

    def __init__(self, cfg, pc, parent=None):
        super().__init__(parent)
        self.cfg = cfg; self.pc = pc
        self._inputs = {}
        self._send_status = None   # initialised in _build_fullscreen_msg if applicable
        try:
            self._build()
        except Exception as _build_err:
            import traceback
            lay = QVBoxLayout(self)
            err_lbl = QLabel(f"⚠ שגיאה בטעינת עורך הלוח:\n{_build_err}")
            err_lbl.setStyleSheet("color:red;padding:14px;font-size:11px;")
            err_lbl.setWordWrap(True)
            lay.addWidget(err_lbl)

    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Header bar
        hdr = QWidget(); hdr.setObjectName("card_title")
        hdr.setStyleSheet("#card_title{background:#eef2fc;border-bottom:1px solid #dde8f8;}")
        hlay = QHBoxLayout(hdr); hlay.setContentsMargins(14,10,14,10)
        ptype = self.pc.get("type","")
        icon = PANEL_ICONS.get(ptype,"▣")
        name = PANEL_NAMES.get(ptype,"לוח")
        title = QLabel(f"{icon}  עריכת לוח: {name}  (#{self.pc.get('id','—')})")
        title.setStyleSheet("font-size:14px;font-weight:bold;color:#1b3a7a;")
        hlay.addStretch()
        hlay.addWidget(title)

        save_btn = QPushButton("💾  שמור שינויים")
        save_btn.setObjectName("btn_success")
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self._save)
        hlay.insertWidget(0, save_btn)
        main.addWidget(hdr)

        # Scrollable content
        content = QWidget()
        self._lay = QVBoxLayout(content)
        self._lay.setContentsMargins(16, 12, 16, 20)
        self._lay.setSpacing(10)
        self._lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        main.addWidget(scroll_wrap(content))

        ptype = self.pc.get("type", "")
        if ptype in ("background", "fullscreen_msg"):
            self._build_type_section()
        else:
            # Top identity section: name, enabled, layer
            self._build_identity_section()
            self._build_position_section()
            self._build_appearance_section()   # all types get it; element skips bg_image inside
            self._build_type_section()
        self._lay.addStretch()

    # ── section builders ──────────────────────────────────────────────────────
    def _section(self, title):
        grp = QGroupBox(title)
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)
        self._lay.addWidget(grp)
        return lay

    def _row(self, lay, label, widget):
        lay.addWidget(form_row(label, widget))

    def _build_identity_section(self):
        """Top section: panel name, enabled toggle, schedule, layer selector, board assignment."""
        s = self._section("פרטי הלוח")

        # Panel name (free text)
        name_e = QLineEdit(self.pc.get("panel_name", ""))
        name_e.setPlaceholderText("שם חופשי לזיהוי...")
        self._inputs["panel_name"] = name_e
        self._row(s, "שם הלוח:", name_e)

        # Enabled checkbox
        self._check(s, "לוח מופעל:", "enabled", True)

        # ── Panel schedule (hours/days) ──────────────────────────────────────
        sched_grp = QGroupBox("⏰  הצג לוח זה בשעות/ימים מסוימים בלבד")
        sched_grp.setCheckable(True)
        ps = self.pc.get("panel_schedule", {})
        sched_grp.setChecked(bool(ps.get("hours_enabled") or ps.get("days_enabled")))
        sg = QVBoxLayout(sched_grp); sg.setSpacing(5)

        self._ps_hours_cb = QCheckBox("הגבל לטווח שעות")
        self._ps_hours_cb.setChecked(ps.get("hours_enabled", False))
        sg.addWidget(self._ps_hours_cb)

        hr_row = QWidget(); hrl = QHBoxLayout(hr_row); hrl.setContentsMargins(18,0,0,0); hrl.setSpacing(8)
        self._ps_hfrom = QSpinBox(); self._ps_hfrom.setRange(0,23)
        self._ps_hfrom.setValue(ps.get("hour_from",8)); self._ps_hfrom.setPrefix("מ- ")
        self._ps_hto = QSpinBox(); self._ps_hto.setRange(0,23)
        self._ps_hto.setValue(ps.get("hour_to",20)); self._ps_hto.setPrefix("עד ")
        hrl.addWidget(self._ps_hfrom); hrl.addWidget(self._ps_hto); hrl.addStretch()
        sg.addWidget(hr_row)

        self._ps_days_cb = QCheckBox("הגבל לימי שבוע")
        self._ps_days_cb.setChecked(ps.get("days_enabled", False))
        sg.addWidget(self._ps_days_cb)

        day_row = QWidget(); drl = QHBoxLayout(day_row); drl.setContentsMargins(18,0,0,0); drl.setSpacing(4)
        days_labels = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","ש׳"]
        active_days = ps.get("active_days", list(range(7)))
        self._ps_day_cbs = []
        for di, dl in enumerate(days_labels):
            dc = QCheckBox(dl); dc.setChecked(di in active_days)
            dc.setStyleSheet("spacing:3px;")
            self._ps_day_cbs.append(dc); drl.addWidget(dc)
        drl.addStretch()
        sg.addWidget(day_row)
        self._sched_grp = sched_grp
        s.addWidget(sched_grp)

        # ── Board assignment ─────────────────────────────────────────────────
        board_row = QWidget(); brl = QHBoxLayout(board_row)
        brl.setContentsMargins(0,4,0,4); brl.setSpacing(8)
        brl_lbl = QLabel("שייך ללוח תצוגה:")
        brl_lbl.setFixedWidth(170)
        brl_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        brl_lbl.setStyleSheet("color:#4a5580;font-size:12px;")
        self._board_cb = QComboBox()
        self._board_cb.addItem("כל הלוחות (ברירת מחדל)", "__all__")
        self._board_cb.addItem("🖥 רקע ראשי בלבד", "__default__")
        for b in self.cfg.display_boards():
            self._board_cb.addItem(f"🖥 {b.get('name','')}", b["id"])
        cur_board = self.pc.get("board_id", "__all__")
        for i in range(self._board_cb.count()):
            if self._board_cb.itemData(i) == cur_board:
                self._board_cb.setCurrentIndex(i); break
        brl.addWidget(brl_lbl); brl.addWidget(self._board_cb, 1)
        s.addWidget(board_row)

        # Layer selector
        layer_row = QWidget(); ll = QHBoxLayout(layer_row)
        ll.setContentsMargins(0, 2, 0, 2); ll.setSpacing(8)
        lbl = QLabel("שכבת תצוגה:")
        lbl.setFixedWidth(170)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color:#4a5580;font-size:12px;")
        self._layer_grp = QButtonGroup(self)
        cur = self.pc.get("layer", 1)
        btns_widget = QWidget(); bw = QHBoxLayout(btns_widget); bw.setContentsMargins(0,0,0,0); bw.setSpacing(8)
        for val, text, tip in [(1,"1 — עליון","הכי קדמי"),(2,"2 — אמצעי",""),(3,"3 — תחתון","הכי אחורי")]:
            rb = QRadioButton(text)
            rb.setChecked(cur == val)
            rb.setProperty("layer_val", val)
            if tip: rb.setToolTip(tip)
            self._layer_grp.addButton(rb)
            bw.addWidget(rb)
        bw.addStretch()
        ll.addWidget(lbl)
        ll.addWidget(btns_widget, 1)
        s.addWidget(layer_row)

    def _build_layer_section(self):
        """Legacy – kept for compatibility but now handled by _build_identity_section."""
        pass

    def _entry(self, lay, label, key, val=""):
        e = QLineEdit(str(self.pc.get(key, val)))
        e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._inputs[key] = e
        lay.addWidget(form_row(label, e))
        return e

    def _font_combo(self, lay, label, key, default="Arial"):
        """Font selector: editable QComboBox populated with installed fonts."""
        from PyQt6.QtGui import QFontDatabase
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItems(sorted(QFontDatabase.families()))
        cur = self.pc.get(key, default)
        idx = cb.findText(cur)
        cb.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0:
            cb.setCurrentText(cur)
        self._inputs[key] = cb
        lay.addWidget(form_row(label, cb))
        return cb

    def _spin(self, lay, label, key, lo, hi, default):
        s = QSpinBox(); s.setRange(lo, hi); s.setValue(int(self.pc.get(key, default)))
        self._inputs[key] = s
        lay.addWidget(form_row(label, s))
        return s

    def _color(self, lay, label, key, default):
        btn = color_btn(self.pc.get(key, default), self)
        self._inputs[key] = btn
        lay.addWidget(form_row(label, btn, compact=True))  # compact: color swatch next to label
        return btn

    def _check(self, lay, label, key, default=False):
        cb = QCheckBox()
        cb.setChecked(bool(self.pc.get(key, default)))
        self._inputs[key] = cb
        lay.addWidget(form_row(label, cb, compact=True))   # compact: checkbox next to label
        return cb

    # ── common sections ───────────────────────────────────────────────────────
    def _build_position_section(self):
        s = self._section("מיקום וגודל")

        # ── helper: label style ──────────────────────────────────
        _lbl_css = "color:#4a5580;font-size:12px;"

        def _rtl_row():
            """Return (QWidget, QHBoxLayout) pre-configured RTL row."""
            w = QWidget(); lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 2, 0, 2); lay.setSpacing(6)
            return w, lay

        def _finish_rtl_row(lay):
            """Add stretch at the END of an RTL row so content is flush-right."""
            lay.addStretch()

        def _sp(lo, hi, val, w=88):
            sp = QSpinBox(); sp.setRange(lo, hi); sp.setValue(int(val))
            sp.setFixedWidth(w)   # ~88px fits 10 digits comfortably
            return sp

        # ── 1. Size quick-presets ────────────────────────────────
        row_sp, rl_sp = _rtl_row()
        size_preset_lbl = QLabel("גודל מהיר:")
        size_preset_lbl.setStyleSheet(_lbl_css)
        self._size_preset_cb = QComboBox()
        self._size_preset_cb.setFixedWidth(190)
        self._size_preset_cb.addItems([
            "בחר גודל מהיר...",
            "קטן — 200×150",
            "בינוני — 350×250",
            "גדול — 600×400",
            "רחב — 800×200",
            "פס תחתון — 1200×80",
            "מחצית מסך — 960×540",
            "מסך מלא — 1920×1080",
            "A6 — 420×297",
            "A5 — 595×420",
        ])
        self._size_preset_cb.setMaxVisibleItems(12)
        self._size_preset_cb.activated.connect(self._apply_size_preset)
        rl_sp.addWidget(self._size_preset_cb)
        rl_sp.addWidget(size_preset_lbl)
        _finish_rtl_row(rl_sp)
        s.addWidget(row_sp)

        # ── 2. Width / Height in one RTL row + swap btn + aspect-lock ──
        row_wh, rl_wh = _rtl_row()

        self._w_sp = _sp(40, 3840, self.pc.get("width", 350))
        self._inputs["width"] = self._w_sp

        self._h_sp = _sp(20, 2160, self.pc.get("height", 200))
        self._inputs["height"] = self._h_sp

        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(26, 26)
        swap_btn.setToolTip("החלף רוחב/גובה")
        swap_btn.setObjectName("btn_secondary")
        swap_btn.clicked.connect(self._swap_wh)

        self._aspect_lock_cb = QCheckBox("נעל יחס")
        self._aspect_lock_cb.setChecked(False)
        self._aspect_lock_cb.setToolTip("שמור יחס גובה-רוחב בעת שינוי")
        self._aspect_lock_updating = False

        h_lbl = QLabel("גובה:"); h_lbl.setStyleSheet(_lbl_css)
        w_lbl = QLabel("רוחב:"); w_lbl.setStyleSheet(_lbl_css)

        # RTL order: aspect-lock | h-spinbox | h-label | swap | w-spinbox | w-label
        rl_wh.addWidget(self._aspect_lock_cb)
        rl_wh.addSpacing(4)
        rl_wh.addWidget(self._h_sp)
        rl_wh.addWidget(h_lbl)
        rl_wh.addWidget(swap_btn)
        rl_wh.addWidget(self._w_sp)
        rl_wh.addWidget(w_lbl)
        _finish_rtl_row(rl_wh)
        s.addWidget(row_wh)

        # Connect aspect-lock
        self._w_sp.valueChanged.connect(self._on_width_changed)
        self._h_sp.valueChanged.connect(self._on_height_changed)

        # ── 3. Quick position preset ─────────────────────────────
        row_qp, rl_qp = _rtl_row()
        preset_lbl = QLabel("מיקום מהיר:")
        preset_lbl.setStyleSheet(_lbl_css)
        self._preset_cb = QComboBox()
        self._preset_cb.setFixedWidth(190)
        self._preset_cb.addItems([
            "בחר מיקום מהיר...",
            "למעלה — ימין",  "למעלה — מרכז",  "למעלה — שמאל",
            "באמצע — ימין", "באמצע — מרכז", "באמצע — שמאל",
            "למטה — ימין",   "למטה — מרכז",  "למטה — שמאל",
        ])
        self._preset_cb.setMaxVisibleItems(10)
        self._preset_cb.activated.connect(self._apply_preset)
        rl_qp.addWidget(self._preset_cb)
        rl_qp.addWidget(preset_lbl)
        _finish_rtl_row(rl_qp)
        s.addWidget(row_qp)

        # Pre-select matching preset if panel already positioned
        self._update_preset_display()

        # ── 4. X/Y row  (מרחק מלמעלה + מצד שמאל) ───────────────
        row_xy, rl_xy = _rtl_row()

        self._x_sp = _sp(0, 3840, self.pc.get("x", 20))
        self._inputs["x"] = self._x_sp

        self._y_sp = _sp(0, 2160, self.pc.get("y", 20))
        self._inputs["y"] = self._y_sp

        x_lbl = QLabel("מרחק משמאל:"); x_lbl.setStyleSheet(_lbl_css)
        y_lbl = QLabel("מרחק מלמעלה:"); y_lbl.setStyleSheet(_lbl_css)

        # RTL order: x-spinbox | x-label | gap | y-spinbox | y-label
        rl_xy.addWidget(self._x_sp)
        rl_xy.addWidget(x_lbl)
        rl_xy.addSpacing(12)
        rl_xy.addWidget(self._y_sp)
        rl_xy.addWidget(y_lbl)
        _finish_rtl_row(rl_xy)
        s.addWidget(row_xy)

        # ── 5. Right/Bottom row  (מרחק מלמטה + מצד ימין) ────────
        row_rb, rl_rb = _rtl_row()

        self._right_sp  = _sp(0, 3840, 0)
        self._bottom_sp = _sp(0, 2160, 0)

        right_lbl  = QLabel("מרחק מימין:"); right_lbl.setStyleSheet(_lbl_css)
        bottom_lbl = QLabel("מרחק מלמטה:"); bottom_lbl.setStyleSheet(_lbl_css)

        rl_rb.addWidget(self._right_sp)
        rl_rb.addWidget(right_lbl)
        rl_rb.addSpacing(12)
        rl_rb.addWidget(self._bottom_sp)
        rl_rb.addWidget(bottom_lbl)
        _finish_rtl_row(rl_rb)
        s.addWidget(row_rb)

        # Compute initial right/bottom from current x/y/w/h
        self._pos_updating = False
        self._update_right_bottom()

        # Bidirectional sync signals
        self._x_sp.valueChanged.connect(self._on_x_changed)
        self._y_sp.valueChanged.connect(self._on_y_changed)
        self._right_sp.valueChanged.connect(self._on_right_changed)
        self._bottom_sp.valueChanged.connect(self._on_bottom_changed)
        self._w_sp.valueChanged.connect(self._update_right_bottom)
        self._h_sp.valueChanged.connect(self._update_right_bottom)

    # ── helpers for _build_position_section ──────────────────────────────────

    def _get_design_size(self):
        """Return (dw, dh) design/screen dimensions."""
        try:
            from PyQt6.QtWidgets import QApplication
            scr = QApplication.primaryScreen().geometry()
            dw = int(self.cfg.d.get("display", {}).get("design_width",  scr.width()))
            dh = int(self.cfg.d.get("display", {}).get("design_height", scr.height()))
        except Exception:
            dw, dh = 1920, 1080
        return dw, dh

    def _update_right_bottom(self):
        """Recompute right/bottom derived fields from x/y/w/h."""
        if self._pos_updating:
            return
        dw, dh = self._get_design_size()
        self._pos_updating = True
        try:
            self._right_sp.setValue(max(0, dw - self._x_sp.value() - self._w_sp.value()))
            self._bottom_sp.setValue(max(0, dh - self._y_sp.value() - self._h_sp.value()))
        finally:
            self._pos_updating = False

    def _on_x_changed(self, val):
        if self._pos_updating: return
        self._pos_updating = True
        try:
            dw, _ = self._get_design_size()
            self._right_sp.setValue(max(0, dw - val - self._w_sp.value()))
        finally:
            self._pos_updating = False

    def _on_y_changed(self, val):
        if self._pos_updating: return
        self._pos_updating = True
        try:
            _, dh = self._get_design_size()
            self._bottom_sp.setValue(max(0, dh - val - self._h_sp.value()))
        finally:
            self._pos_updating = False

    def _on_right_changed(self, val):
        if self._pos_updating: return
        self._pos_updating = True
        try:
            dw, _ = self._get_design_size()
            new_x = max(0, dw - val - self._w_sp.value())
            self._x_sp.setValue(new_x)
            self._inputs["x"].setValue(new_x)
        finally:
            self._pos_updating = False

    def _on_bottom_changed(self, val):
        if self._pos_updating: return
        self._pos_updating = True
        try:
            _, dh = self._get_design_size()
            new_y = max(0, dh - val - self._h_sp.value())
            self._y_sp.setValue(new_y)
            self._inputs["y"].setValue(new_y)
        finally:
            self._pos_updating = False

    def _on_width_changed(self, val):
        if self._aspect_lock_updating: return
        if self._aspect_lock_cb.isChecked():
            orig_w = int(self.pc.get("width",  val) or val)
            orig_h = int(self.pc.get("height", val) or val)
            if orig_w:
                self._aspect_lock_updating = True
                try:
                    self._h_sp.setValue(max(20, round(val * orig_h / orig_w)))
                finally:
                    self._aspect_lock_updating = False
        self.pc["width"] = val
        if hasattr(self, "_pos_updating"):
            self._update_right_bottom()

    def _on_height_changed(self, val):
        if self._aspect_lock_updating: return
        if self._aspect_lock_cb.isChecked():
            orig_w = int(self.pc.get("width",  val) or val)
            orig_h = int(self.pc.get("height", val) or val)
            if orig_h:
                self._aspect_lock_updating = True
                try:
                    self._w_sp.setValue(max(40, round(val * orig_w / orig_h)))
                finally:
                    self._aspect_lock_updating = False
        self.pc["height"] = val
        if hasattr(self, "_pos_updating"):
            self._update_right_bottom()

    def _swap_wh(self):
        """Swap width and height values."""
        self._aspect_lock_updating = True
        try:
            w, h = self._w_sp.value(), self._h_sp.value()
            self._w_sp.setValue(h)
            self._h_sp.setValue(w)
        finally:
            self._aspect_lock_updating = False

    def _apply_size_preset(self, idx):
        """Apply a size preset → updates width/height spinboxes."""
        if idx <= 0: return
        _presets = [
            None,
            (200, 150), (350, 250), (600, 400), (800, 200),
            (1200, 80), (960, 540), (1920, 1080),
            (420, 297),  # A6
            (595, 420),  # A5
        ]
        if 1 <= idx < len(_presets):
            pw, ph = _presets[idx]
            self._aspect_lock_updating = True
            try:
                self._w_sp.setValue(pw)
                self._h_sp.setValue(ph)
            finally:
                self._aspect_lock_updating = False
            if hasattr(self, "_pos_updating"):
                self._update_right_bottom()

    def _update_preset_display(self):
        """Pre-select the matching quick-position preset for an already-configured panel."""
        try:
            dw, dh = self._get_design_size()
            cur_x = int(self.pc.get("x", 20))
            cur_y = int(self.pc.get("y", 20))
            pw    = int(self.pc.get("width",  350))
            ph    = int(self.pc.get("height", 200))
            margin = 20
            cx    = (dw - pw) // 2
            cx_r  = dw - pw - margin
            presets = [
                (cx_r, margin),
                (cx,   margin),
                (margin, margin),
                (cx_r, (dh - ph) // 2),
                (cx,   (dh - ph) // 2),
                (margin, (dh - ph) // 2),
                (cx_r, dh - ph - margin),
                (cx,   dh - ph - margin),
                (margin, dh - ph - margin),
            ]
            for i, (px, py) in enumerate(presets):
                if abs(cur_x - px) <= 5 and abs(cur_y - py) <= 5:
                    self._preset_cb.setCurrentIndex(i + 1)
                    return
            self._preset_cb.setCurrentIndex(0)
        except Exception:
            self._preset_cb.setCurrentIndex(0)

    def _apply_preset(self, idx):
        """Apply a preset position – updates x/y spinboxes."""
        if idx <= 0: return
        dw, dh = self._get_design_size()
        pw = self._w_sp.value() if hasattr(self, "_w_sp") else int(self.pc.get("width", 350))
        ph = self._h_sp.value() if hasattr(self, "_h_sp") else int(self.pc.get("height", 200))
        margin = 20
        cx   = (dw - pw) // 2
        cx_r = dw - pw - margin
        presets = [
            (cx_r, margin),
            (cx,   margin),
            (margin, margin),
            (cx_r, (dh - ph) // 2),
            (cx,   (dh - ph) // 2),
            (margin, (dh - ph) // 2),
            (cx_r, dh - ph - margin),
            (cx,   dh - ph - margin),
            (margin, dh - ph - margin),
        ]
        if 1 <= idx <= len(presets):
            x, y = presets[idx - 1]
            if "x" in self._inputs: self._inputs["x"].setValue(max(0, x))
            if "y" in self._inputs: self._inputs["y"].setValue(max(0, y))

    def _build_appearance_section(self):
        s = self._section("עיצוב ומראה")
        ptype = self.pc.get("type", "")
        self._check(s, "רקע שקוף:", "bg_transparent", False)
        bg_color_btn = self._color(s, "צבע רקע:", "bg_color", "#111128")
        # Background image — not relevant for element panels
        if ptype != "element":
            img_row = QWidget(); il = QHBoxLayout(img_row); il.setContentsMargins(0,0,0,0)
            self._bg_img_e = QLineEdit(self.pc.get("bg_image",""))
            self._bg_img_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self._inputs["bg_image"] = self._bg_img_e
            pick_bg = QPushButton("📂 עיון"); pick_bg.setMinimumWidth(72)
            pick_bg.setObjectName("btn_secondary")
            pick_bg.clicked.connect(lambda: self._pick_file("bg_image", self._bg_img_e))
            clear_bg = QPushButton("✕"); clear_bg.setFixedWidth(30)
            clear_bg.setObjectName("btn_secondary")
            clear_bg.clicked.connect(lambda: self._bg_img_e.clear())
            il.addWidget(self._bg_img_e); il.addWidget(pick_bg); il.addWidget(clear_bg)
            s.addWidget(form_row("תמונת רקע:", img_row))

            # When bg_image is set, bg_color has no effect — disable it to avoid confusion
            def _sync_bg_color_state(text):
                has_img = bool(text.strip())
                bg_color_btn.setEnabled(not has_img)
                bg_color_btn.setToolTip("תמונת הרקע מחליפה את צבע המילוי" if has_img else "")
            self._bg_img_e.textChanged.connect(_sync_bg_color_state)
            _sync_bg_color_state(self._bg_img_e.text())  # apply immediately on open

        self._check(s, "גבול שקוף:", "border_transparent", False)
        self._color(s, "צבע גבול:", "border_color", "#3a7bd5")
        self._spin(s, "עובי גבול:", "border_width", 0, 20, 2)
        # Content margins (distance from panel edges to content)
        self._build_panel_margins(s)

    def _build_panel_margins(self, s):
        """Add per-panel content-margin spinboxes in a single RTL row.
        Right side: 'שוליים שווים' fills all 4 fields; editing any individual field clears it."""
        sym = int(self.pc.get("padding", 0))
        row = QWidget(); rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 2); rl.setSpacing(4)

        title_lbl = QLabel("שולי תוכן:")
        title_lbl.setStyleSheet("color:#4a5580;font-size:12px;font-weight:bold;")

        def _make_sp(key, prefix, label_text, default):
            sp = QSpinBox()
            sp.setRange(0, 99999)
            sp.setValue(int(self.pc.get(key, default)))
            sp.setFixedWidth(84)
            sp.setPrefix(prefix + " ")
            self._inputs[key] = sp
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#6070a0;font-size:11px;")
            return sp, lbl

        sp_top,   lbl_top   = _make_sp("pad_top",    "↑", "למעלה", sym)
        sp_bot,   lbl_bot   = _make_sp("pad_bottom",  "↓", "למטה",  sym)
        sp_right, lbl_right = _make_sp("pad_right",   "→", "ימין",  sym)
        sp_left,  lbl_left  = _make_sp("pad_left",    "←", "שמאל", sym)

        # ── "שוליים שווים" control ──
        lbl_all = QLabel("שוליים שווים:")
        lbl_all.setStyleSheet("color:#4a5580;font-size:11px;")
        sp_all = QSpinBox()
        sp_all.setRange(0, 99999)
        sp_all.setFixedWidth(84)
        sp_all.setSpecialValueText("—")   # display dash when value=0 (unset state)
        sp_all.setValue(0)
        sp_all.setPrefix("")

        _all_sides = [sp_top, sp_bot, sp_right, sp_left]
        _updating = [False]   # prevent recursive signal loops

        def _on_all_changed(val):
            if _updating[0]: return
            if val == 0: return          # dash state — do nothing
            _updating[0] = True
            for sp in _all_sides:
                sp.setValue(val)
            _updating[0] = False

        def _on_individual_changed(_val):
            if _updating[0]: return
            # Any manual edit of an individual field clears the "all" spinbox
            _updating[0] = True
            sp_all.setValue(0)
            _updating[0] = False

        sp_all.valueChanged.connect(_on_all_changed)
        for sp in _all_sides:
            sp.valueChanged.connect(_on_individual_changed)

        # RTL layout: title | ↑ | ↓ | → | ← | stretch | שוליים שווים label | sp_all
        rl.addWidget(title_lbl)
        for sp, lbl in [(sp_top,lbl_top),(sp_bot,lbl_bot),(sp_right,lbl_right),(sp_left,lbl_left)]:
            rl.addWidget(lbl); rl.addWidget(sp)
        rl.addStretch()
        rl.addWidget(lbl_all); rl.addWidget(sp_all)
        s.addWidget(row)

    def _build_type_section(self):
        ptype = self.pc.get("type","")
        if ptype == "clock":   self._build_clock()
        elif ptype == "date":  self._build_date()
        elif ptype == "text":  self._build_text()
        elif ptype == "ad":    self._build_ad()
        elif ptype == "zmanim":self._build_zmanim()
        elif ptype == "_schedule": self._build_schedule()
        elif ptype == "element":self._build_element()
        elif ptype == "notice":self._build_notice()
        elif ptype == "screen_msg": self._build_screen_msg()
        elif ptype == "background":self._build_background()
        elif ptype == "fullscreen_msg":self._build_fullscreen_msg()

    def _build_clock(self):
        """Editor for clock-only panel (type='clock')."""
        s = self._section("הגדרות שעון")
        # Clock style combo
        clk = QComboBox()
        clk.addItems(["דיגיטלי", "אנלוגי"])
        clk.setCurrentIndex(0 if self.pc.get("clock_style","digital")=="digital" else 1)
        self._inputs["clock_style"] = clk
        s.addWidget(form_row("סגנון שעון:", clk))
        # Digital format (shown only for digital)
        fmt_w = QWidget(); fmt_l = QHBoxLayout(fmt_w)
        fmt_l.setContentsMargins(0,0,0,0); fmt_l.addStretch()
        fmt = QComboBox(); fmt.addItems(["24 שעות","12 שעות"])
        fmt.setCurrentIndex(0 if self.pc.get("time_format","24")=="24" else 1)
        self._inputs["time_format"] = fmt
        fmt_l.addWidget(fmt); fmt_l.addWidget(QLabel("פורמט שעה:"))
        s.addWidget(fmt_w)
        # Analog style (shown only for analog)
        ast_w = QWidget(); ast_l = QHBoxLayout(ast_w)
        ast_l.setContentsMargins(0,0,0,0); ast_l.addStretch()
        ast = QComboBox()
        for k,v in ANALOG_STYLE_NAMES.items(): ast.addItem(v, k)
        cur_ast = self.pc.get("analog_style","classic")
        keys = list(ANALOG_STYLE_NAMES.keys())
        ast.setCurrentIndex(keys.index(cur_ast) if cur_ast in keys else 0)
        self._inputs["analog_style"] = ast
        ast_l.addWidget(ast); ast_l.addWidget(QLabel("סגנון אנלוגי:"))
        s.addWidget(ast_w)
        def _on_clk_style(idx):
            fmt_w.setVisible(idx == 0)   # digital only
            ast_w.setVisible(idx == 1)   # analog only
        clk.currentIndexChanged.connect(_on_clk_style)
        _on_clk_style(clk.currentIndex())
        self._check(s, "הצג שניות:", "show_seconds", True)
        s.addWidget(hline())
        self._color(s, "צבע:", "font_color", "#3a7bd5")
        self._font_combo(s, "גופן:", "font_family", "Arial")
        self._spin(s, "גודל גופן:", "font_size", 10, 160, 56)

    def _build_date(self):
        """Editor for date-only panel (type='date')."""
        from PyQt6.QtGui import QFontDatabase
        s = self._section("הגדרות תאריך")

        fc_default = self.pc.get("font_color", "#dde0ff")

        # ── Helper: label + checkbox + "צבע טקסט" label + color swatch in one row ──
        def check_color_row(lbl_text, check_key, color_key, check_df=True, color_df="#dde0ff"):
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 1, 0, 1)
            hl.setSpacing(5)
            # Use PlainText + explicit RightToLeft to prevent BiDi reordering
            lbl = QLabel()
            lbl.setText(lbl_text)
            lbl.setTextFormat(Qt.TextFormat.PlainText)
            lbl.setFixedWidth(170)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color:#4a5580;font-size:12px;")
            cb = QCheckBox()
            cb.setChecked(bool(self.pc.get(check_key, check_df)))
            self._inputs[check_key] = cb
            col_lbl = QLabel("צבע טקסט")
            col_lbl.setStyleSheet("color:#6a7aaa;font-size:11px;")
            cbtn = color_btn(self.pc.get(color_key, color_df), self)
            cbtn.setFixedSize(36, 22)
            self._inputs[color_key] = cbtn
            # In RTL QApplication, addWidget goes right→left, so first=rightmost
            hl.addWidget(lbl)
            hl.addWidget(cb)
            hl.addWidget(col_lbl)
            hl.addWidget(cbtn)
            hl.addStretch()
            s.addWidget(row)

        def sub_title(text):
            """Add a small bold sub-heading directly inside s."""
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;padding:4px 0 1px 0;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            s.addWidget(lbl)

        # ── הגדרות בסיסיות ──────────────────────────────────────────────────
        check_color_row("\u200fהצג יום בשבוע:", "show_weekday", "wd_color", True, fc_default)
        check_color_row("\u200fהצג תאריך עברי:", "show_heb_date", "hd_color", True, fc_default)
        check_color_row("\u200fהצג תאריך לועזי:", "show_greg_date", "gd_color", True, fc_default)
        check_color_row("\u200fהצג חגים ומועדים:", "show_holiday", "hol_color", True, "#f5a623")
        check_color_row("\u200fהצג פרשת השבוע:", "show_parasha", "par_color", True, "#9ab0ff")
        self._check(s, "לפי ישראל:", "israel", True)

        s.addWidget(hline())

        # ── קריאת התורה וההפטרה ─────────────────────────────────────────────
        sub_title("קריאת התורה וההפטרה:")
        check_color_row("\u200fקריאת התורה בשבת:", "show_torah_reading", "tor_color", False, "#aaffaa")
        check_color_row("\u200fהפטרה ומועד:", "show_haftara", "haf_color", False, "#aaffcc")

        s.addWidget(hline())

        # ── הזכרות בתפילה ───────────────────────────────────────────────────
        sub_title("הזכרות בתפילה:")
        hint_haz = QLabel("מוצגים רק כשרלוונטיים לתאריך הנוכחי")
        hint_haz.setStyleSheet("color:#6a7aaa;font-size:10px;")
        hint_haz.setAlignment(Qt.AlignmentFlag.AlignRight)
        s.addWidget(hint_haz)
        check_color_row("\u200fיעלה ויבוא:", "show_yaaleh_veyavo", "yaaleh_color", False, "#ffdd88")
        check_color_row("\u200fמוריד הטל ותן ברכה:", "show_morid_hatal", "morid_tal_color", False, "#88ddff")
        check_color_row("\u200fמשיב הרוח ומוריד הגשם:", "show_mashiv_haruach", "mashiv_color", False, "#88ccff")
        check_color_row("\u200fותן טל ומטר לברכה:", "show_vten_tal_umatar", "vten_color", False, "#ffcc88")

        s.addWidget(hline())

        # ── דף יומי ─────────────────────────────────────────────────────────
        sub_title("דף יומי:")
        check_color_row("\u200fדף יומי (בבלי):", "show_daf_yomi", "daf_color", False, "#ccaaff")

        s.addWidget(hline())

        # ── פריסה ───────────────────────────────────────────────────────────
        layout_cb = QComboBox()
        layout_cb.addItems(["שורות נפרדות", "שורה אחת"])
        layout_map = {"stacked": 0, "inline": 1}
        cur_layout = self.pc.get("date_layout", "stacked")
        layout_cb.setCurrentIndex(layout_map.get(cur_layout, 0))
        self._inputs["date_layout"] = layout_cb
        s.addWidget(form_row("פריסת פרטים:", layout_cb))

        spacing_row = form_row("רווח בין שורות (px):", self._spin_widget("date_line_spacing", 0, 40, 4))
        s.addWidget(spacing_row)

        sep_cb = QComboBox()
        sep_cb.addItems([" | ", " - ", " • ", "  "])
        sep_cb.setEditable(True)
        cur_sep = self.pc.get("date_separator", " | ")
        options = [" | ", " - ", " • ", "  "]
        sep_cb.setCurrentIndex(options.index(cur_sep) if cur_sep in options else 0)
        if cur_sep not in options:
            sep_cb.setCurrentText(cur_sep)
        self._inputs["date_separator"] = sep_cb
        sep_row = form_row("מפריד:", sep_cb)
        s.addWidget(sep_row)

        scroll_row = form_row("גלילה:", self._check_widget("date_scroll_inline", False))
        speed_row  = form_row("מהירות גלילה:", self._spin_widget("date_scroll_speed", 1, 200, 30))
        s.addWidget(scroll_row)
        s.addWidget(speed_row)

        def _apply_layout_visibility():
            is_stacked = layout_cb.currentIndex() == 0
            spacing_row.setVisible(is_stacked)
            sep_row.setVisible(not is_stacked)
            scroll_row.setVisible(not is_stacked)
            speed_row.setVisible(not is_stacked)

        layout_cb.currentIndexChanged.connect(lambda _: _apply_layout_visibility())
        _apply_layout_visibility()

        s.addWidget(hline())

        # ── גופן ──────────────────────────────────────────────────────────────
        font_cb = QComboBox()
        font_cb.setEditable(True)
        installed = sorted(QFontDatabase.families())
        font_cb.addItems(installed)
        cur_font = self.pc.get("font_family", "Arial")
        idx = font_cb.findText(cur_font)
        font_cb.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0:
            font_cb.setCurrentText(cur_font)
        self._inputs["font_family"] = font_cb
        s.addWidget(form_row("גופן:", font_cb))

        self._spin(s, "גודל גופן:", "font_size", 8, 80, 18)

    def _spin_widget(self, key, lo, hi, default):
        """Create a QSpinBox, register it and return it (without adding to layout)."""
        w = QSpinBox(); w.setRange(lo, hi); w.setValue(int(self.pc.get(key, default)))
        self._inputs[key] = w
        return w

    def _check_widget(self, key, default=False):
        """Create a QCheckBox, register it and return it (without adding to layout)."""
        w = QCheckBox(); w.setChecked(bool(self.pc.get(key, default)))
        self._inputs[key] = w
        return w

    def _build_time(self):
        s = self._section("שעון / תאריך")
        for lbl, key, df in [
            ("הצג שעה:", "show_time", True),
            ("הצג שניות:", "show_seconds", True),
            ("הצג יום בשבוע:", "show_weekday", True),
            ("הצג תאריך עברי:", "show_heb_date", True),
            ("הצג תאריך לועזי:", "show_greg_date", True),
            ("הצג חגים ומועדים:", "show_holiday", True),
            ("הצג פרשת השבוע:", "show_parasha", True),
            ("לפי ישראל:", "israel", True),
        ]:
            self._check(s, lbl, key, df)
        s.addWidget(hline())
        clk = QComboBox(); clk.addItems(["דיגיטלי","אנלוגי"])
        clk.setCurrentIndex(0 if self.pc.get("clock_style","digital")=="digital" else 1)
        self._inputs["clock_style"] = clk
        s.addWidget(form_row("סגנון שעון:", clk))
        fmt = QComboBox(); fmt.addItems(["24 שעות","12 שעות"])
        fmt.setCurrentIndex(0 if self.pc.get("time_format","24")=="24" else 1)
        self._inputs["time_format"] = fmt
        s.addWidget(form_row("פורמט שעה:", fmt))
        self._color(s,"צבע טקסט (כל הערכים):","font_color","#3a7bd5")
        self._font_combo(s,"גופן:","font_family","Arial")
        self._spin(s,"גודל גופן (בסיס לשעה):","font_size",10,120,42)

    def _build_text(self):
        note = QLabel("⚙ גופן, צבע, גודל, יישור ועריכת תוכן — בלשונית 'תוכן'")
        note.setStyleSheet("color:#2d5ec0;font-size:11px;padding:6px;background:#eef4ff;border-radius:6px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lay.addWidget(note)

        s = self._section("גלילת טקסט")

        # מצב גלילה
        scroll_mode = QComboBox()
        scroll_mode.addItem("סטטי  (ללא גלילה)", "static")
        scroll_mode.addItem("גלילה רציפה — למעלה", "scroll_up")
        scroll_mode.addItem("גלילה רציפה — ימינה", "scroll_right")
        scroll_mode.addItem("מקטעים", "segments")
        cur_sm = self.pc.get("scroll_mode", "scroll_up")
        if cur_sm == "scroll": cur_sm = "scroll_up"  # legacy
        sm_idx = {d: i for i, (_, d) in enumerate(
            [("סטטי  (ללא גלילה)", "static"), ("גלילה רציפה — למעלה", "scroll_up"),
             ("גלילה רציפה — ימינה", "scroll_right"), ("מקטעים", "segments")]
        )}
        scroll_mode.setCurrentIndex(sm_idx.get(cur_sm, 1))
        self._inputs["scroll_mode"] = scroll_mode
        s.addWidget(form_row("מצב גלילה:", scroll_mode))

        # מהירות גלילה (only for scroll_up / scroll_right)
        speed_sp = QSpinBox()
        speed_sp.setRange(1, 999)
        speed_sp.setValue(int(self.pc.get("scroll_speed", 30)))
        self._inputs["scroll_speed"] = speed_sp
        speed_row = form_row("מהירות גלילה:", speed_sp)
        s.addWidget(speed_row)

        # זמן מעבר מקטע (only for segments)
        seg_dur_sp = QSpinBox()
        seg_dur_sp.setRange(1, 300)
        seg_dur_sp.setValue(int(self.pc.get("segment_duration", 5)))
        self._inputs["segment_duration"] = seg_dur_sp
        seg_dur_row = form_row("זמן מקטע (שניות):", seg_dur_sp)
        s.addWidget(seg_dur_row)

        # רווח ותו מפריד
        s2 = self._section("מפריד בין מקטעים")
        sep_space_cb = QCheckBox("הוסף שורה ריקה / רווח בין מקטעים")
        sep_space_cb.setChecked(bool(self.pc.get("seg_separator_space", True)))
        self._inputs["seg_separator_space"] = sep_space_cb
        s2.addWidget(sep_space_cb)
        sep_char_e = QLineEdit(self.pc.get("seg_separator_char", ""))
        sep_char_e.setPlaceholderText("תו/תווים מפרידים (ריק = ללא)")
        sep_char_e.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        sep_char_e.setMaximumWidth(200)
        self._inputs["seg_separator_char"] = sep_char_e
        s2.addWidget(form_row("תו מפריד:", sep_char_e))

        def _update_visibility():
            mode_val = scroll_mode.currentData()
            is_scroll = mode_val in ("scroll_up", "scroll_right")
            is_seg = mode_val == "segments"
            speed_row.setVisible(is_scroll)
            seg_dur_row.setVisible(is_seg)

        scroll_mode.currentIndexChanged.connect(_update_visibility)
        _update_visibility()

    def _build_schedule(self):
        """Design settings for schedule panel — separate fonts for event name and time."""
        note = QLabel("⚙ ניהול האירועים — בלשונית 'תוכן'")
        note.setStyleSheet("color:#2d5ec0;font-size:11px;padding:6px;background:#eef4ff;border-radius:6px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lay.addWidget(note)

        from PyQt6.QtGui import QFontDatabase
        all_fonts = sorted(QFontDatabase.families())

        # ── Name font settings ──
        s_name = self._section("עיצוב שם האירוע")
        self._color(s_name, "צבע שם:", "name_font_color", "#ffffff")
        nff_cb = QComboBox(); nff_cb.setEditable(True); nff_cb.addItems(all_fonts)
        cur_nf = self.pc.get("name_font_family", self.pc.get("font_family","Arial"))
        idx = nff_cb.findText(cur_nf)
        nff_cb.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0: nff_cb.setCurrentText(cur_nf)
        self._inputs["name_font_family"] = nff_cb
        s_name.addWidget(form_row("גופן שם:", nff_cb))
        self._spin(s_name, "גודל גופן שם:", "name_font_size", 8, 120, 20)

        # ── Time font settings ──
        s_time = self._section("עיצוב זמן האירוע")
        self._color(s_time, "צבע זמן:", "time_font_color", "#aaddff")
        tff_cb = QComboBox(); tff_cb.setEditable(True); tff_cb.addItems(all_fonts)
        cur_tf = self.pc.get("time_font_family", self.pc.get("font_family","Arial"))
        idx2 = tff_cb.findText(cur_tf)
        tff_cb.setCurrentIndex(idx2 if idx2 >= 0 else 0)
        if idx2 < 0: tff_cb.setCurrentText(cur_tf)
        self._inputs["time_font_family"] = tff_cb
        s_time.addWidget(form_row("גופן זמן:", tff_cb))
        self._spin(s_time, "גודל גופן זמן:", "time_font_size", 8, 120, 20)

        # ── Empty text ──
        s_empty = self._section("טקסט כשאין אירועים")
        empty_e = QLineEdit(self.pc.get("empty_text",""))
        empty_e.setPlaceholderText("(ריק = לא מציג כלום)")
        empty_e.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._inputs["empty_text"] = empty_e
        s_empty.addWidget(form_row("טקסט 'אין אירועים':", empty_e))

        # ── Style ──
        s_style = self._section("עיצוב כללי")
        self._check(s_style, "מודגש:", "bold", False)
        self._check(s_style, "נטוי:", "italic", False)

        # ── Day rollover ──
        s_day = self._section("החלפת יום")
        rollover_row = QWidget(); rrl = QHBoxLayout(rollover_row); rrl.setContentsMargins(0,0,0,0); rrl.setSpacing(4)
        rrl_lbl = QLabel("שעת החלפת יום (HH:MM):"); rrl_lbl.setStyleSheet("color:#4a5580;font-size:12px;")
        rh_sp = QSpinBox(); rh_sp.setRange(0,23); rh_sp.setValue(int(self.pc.get("day_rollover_hour",0)))
        rh_sp.setFixedWidth(55); self._inputs["day_rollover_hour"] = rh_sp
        rm_sp = QSpinBox(); rm_sp.setRange(0,59); rm_sp.setValue(int(self.pc.get("day_rollover_minute",0)))
        rm_sp.setFixedWidth(55); self._inputs["day_rollover_minute"] = rm_sp
        rrl.addWidget(rm_sp); rrl.addWidget(rh_sp); rrl.addWidget(rrl_lbl); rrl.addStretch()
        s_day.addWidget(rollover_row)
        hint = QLabel("לפני שעה זו יוצגו ארועי מחר. 00:00 = ללא")
        hint.setStyleSheet("color:#888;font-size:10px;")
        s_day.addWidget(hint)

    def _build_ad(self):
        s = self._section("הגדרות מודעה / תמונות")
        note = QLabel("⚙ הוספת / עריכת תמונות — בלשונית 'תוכן'")
        note.setStyleSheet("color:#2d5ec0;font-size:11px;padding:6px;background:#eef4ff;border-radius:6px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.addWidget(note)
        s.addWidget(hline())
        self._spin(s,"מרווח בין תמונות (שניות):","interval",1,60,5)
        fit = QComboBox(); fit.addItems(["contain","cover","stretch"])
        fit.setCurrentText(self.pc.get("fit_mode","contain"))
        self._inputs["fit_mode"] = fit
        s.addWidget(form_row("התאמת תמונה:", fit))

    def _build_zmanim(self):
        s = self._section("זמני הלכה להצגה")
        self._check(s,"הצג כותרת:","show_title",True)
        self._check(s,"הצג קו מפריד:","show_separator",True)
        self._check(s,"הדגש הבא:","highlight_next",True)

        # Time format (12/24)
        fmt_cb = QComboBox(); fmt_cb.addItems(["24 שעות","12 שעות"])
        fmt_cb.setCurrentIndex(0 if self.pc.get("zmanim_time_format","24")=="24" else 1)
        self._inputs["zmanim_time_format"] = fmt_cb
        s.addWidget(form_row("פורמט שעה:",fmt_cb))

        s.addWidget(hline())

        # ── Display mode: rows or single line ──
        disp_mode_lbl = QLabel("מצב תצוגה:")
        disp_mode_lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        disp_mode_lbl.setAlignment(Qt.AlignmentFlag.AlignRight); s.addWidget(disp_mode_lbl)

        display_mode_cb = QComboBox()
        display_mode_cb.addItem("שורות — כל זמן בשורה", "rows")
        display_mode_cb.addItem("שורה אחת — הכל בשורה אחת", "inline")
        cur_disp = self.pc.get("zmanim_display_mode","rows")
        display_mode_cb.setCurrentIndex(0 if cur_disp=="rows" else 1)
        self._inputs["zmanim_display_mode"] = display_mode_cb
        s.addWidget(form_row("מצב תצוגה:", display_mode_cb))

        # Rows mode: label+time layout
        row_layout_cb = QComboBox()
        row_layout_cb.addItem("שם הזמן והזמן באותה שורה", "same_row")
        row_layout_cb.addItem("שם הזמן בשורה, זמן מתחת", "stacked")
        cur_rl = self.pc.get("zmanim_row_layout","same_row")
        row_layout_cb.setCurrentIndex(0 if cur_rl=="same_row" else 1)
        self._inputs["zmanim_row_layout"] = row_layout_cb
        row_layout_row = form_row("פריסת שורה:", row_layout_cb)
        s.addWidget(row_layout_row)

        # Row spacing (rows mode only)
        row_spacing_sp = QSpinBox(); row_spacing_sp.setRange(0,40)
        row_spacing_sp.setValue(int(self.pc.get("zmanim_row_spacing",4)))
        self._inputs["zmanim_row_spacing"] = row_spacing_sp
        row_spacing_row = form_row("רווח בין שורות (px):", row_spacing_sp)
        s.addWidget(row_spacing_row)

        # Inline separator (inline mode only)
        inline_sep_e = QLineEdit(self.pc.get("zmanim_inline_sep"," | "))
        inline_sep_e.setMaximumWidth(120)
        self._inputs["zmanim_inline_sep"] = inline_sep_e
        inline_sep_row = form_row("תו מפריד (inline):", inline_sep_e)
        s.addWidget(inline_sep_row)

        # Scrolling
        scroll_lbl = QLabel("גלילה:")
        scroll_lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        scroll_lbl.setAlignment(Qt.AlignmentFlag.AlignRight); s.addWidget(scroll_lbl)

        scroll_cb = QComboBox()
        scroll_cb.addItem("ללא גלילה", "none")
        scroll_cb.addItem("גלילה למעלה", "up")
        scroll_cb.addItem("גלילה למטה", "down")
        cur_scr = self.pc.get("zmanim_scroll","none")
        scroll_map = {"none":0,"up":1,"down":2}
        scroll_cb.setCurrentIndex(scroll_map.get(cur_scr,0))
        self._inputs["zmanim_scroll"] = scroll_cb
        s.addWidget(form_row("כיוון גלילה:", scroll_cb))

        scroll_speed_sp = QSpinBox(); scroll_speed_sp.setRange(1,20)
        scroll_speed_sp.setValue(int(self.pc.get("zmanim_scroll_speed",2)))
        self._inputs["zmanim_scroll_speed"] = scroll_speed_sp
        scroll_speed_row = form_row("מהירות גלילה:", scroll_speed_sp)
        s.addWidget(scroll_speed_row)

        # Show/hide rows based on display mode
        def _update_visibility():
            is_rows = display_mode_cb.currentIndex() == 0
            row_layout_row.setVisible(is_rows)
            row_spacing_row.setVisible(is_rows)
            inline_sep_row.setVisible(not is_rows)

        display_mode_cb.currentIndexChanged.connect(lambda _: _update_visibility())
        _update_visibility()

        s.addWidget(hline())

        # ── Label (name) font and color ──
        label_sec = QLabel("עיצוב שם הזמן:")
        label_sec.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        label_sec.setAlignment(Qt.AlignmentFlag.AlignRight); s.addWidget(label_sec)
        self._color(s,"צבע שם הזמן:","label_color","#9090cc")
        label_font_cb = QComboBox(); label_font_cb.setEditable(True)
        from PyQt6.QtGui import QFontDatabase
        label_font_cb.addItems(sorted(QFontDatabase.families()))
        cur_lf = self.pc.get("zmanim_label_font",self.pc.get("font_family","Arial"))
        idx_lf = label_font_cb.findText(cur_lf)
        label_font_cb.setCurrentIndex(idx_lf if idx_lf>=0 else 0)
        if idx_lf < 0: label_font_cb.setCurrentText(cur_lf)
        self._inputs["zmanim_label_font"] = label_font_cb
        s.addWidget(form_row("גופן שם הזמן:", label_font_cb))
        label_size_sp = QSpinBox(); label_size_sp.setRange(6,60)
        label_size_sp.setValue(int(self.pc.get("zmanim_label_size",self.pc.get("font_size",14))))
        self._inputs["zmanim_label_size"] = label_size_sp
        s.addWidget(form_row("גודל גופן שם:", label_size_sp))

        # ── Time value font and color ──
        time_sec = QLabel("עיצוב הזמן:")
        time_sec.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        time_sec.setAlignment(Qt.AlignmentFlag.AlignRight); s.addWidget(time_sec)
        self._color(s,"צבע שעה / כותרת:","time_color","#3a7bd5")
        time_font_cb = QComboBox(); time_font_cb.setEditable(True)
        time_font_cb.addItems(sorted(QFontDatabase.families()))
        cur_tf = self.pc.get("zmanim_time_font",self.pc.get("font_family","Arial"))
        idx_tf = time_font_cb.findText(cur_tf)
        time_font_cb.setCurrentIndex(idx_tf if idx_tf>=0 else 0)
        if idx_tf < 0: time_font_cb.setCurrentText(cur_tf)
        self._inputs["zmanim_time_font"] = time_font_cb
        s.addWidget(form_row("גופן שעה:", time_font_cb))
        time_size_sp = QSpinBox(); time_size_sp.setRange(6,60)
        time_size_sp.setValue(int(self.pc.get("zmanim_time_size",self.pc.get("font_size",14))))
        self._inputs["zmanim_time_size"] = time_size_sp
        s.addWidget(form_row("גודל גופן שעה:", time_size_sp))

        self._color(s,"צבע הדגשה:","highlight_color","#f5a623")

        s.addWidget(hline())

        # ── Custom names + zmanim items selector ──
        s.addWidget(section_label("בחר זמנים להצגה:"))
        hint = QLabel("💡 הרשימה נקבעת בלשונית 'זמן ומיקום' — כולל זמנים כפולים ושמות מותאמים")
        hint.setStyleSheet("color:#6070a0;font-size:10px;"); hint.setWordWrap(True)
        s.addWidget(hint)

        # Get effective list from location config (or fall back to ZMANIM_KEYS)
        cfg_d = {}
        try: cfg_d = self.cfg.d
        except: pass
        eff_list = get_effective_zmanim_list(cfg_d)  # list of (uid, key, display_name)

        current = self.pc.get("show_items", [e[1] for e in eff_list])
        custom_names = self.pc.get("zmanim_custom_names", {})
        self._zmanim_checks = {}
        self._zmanim_custom_names = dict(custom_names)
        self._zmanim_per_key_method = dict(self.pc.get("zmanim_per_key_method", {}))

        # Build checkboxes from effective list
        # _zmanim_checks maps uid → checkbox (uid is used as show_items key for custom entries,
        # and the standard key for default entries)
        grid = QWidget(); gl = QGridLayout(grid); gl.setSpacing(4)
        col = 0; row_i = 0
        for uid, key, display_name in eff_list:
            row_w = QWidget(); rl = QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0); rl.setSpacing(3)
            # Use uid as the identifier in show_items (uid == key for default entries)
            cb = QCheckBox(); cb.setChecked(uid in current or key in current)
            self._zmanim_checks[uid] = cb
            name_lbl = QLabel(display_name)
            name_lbl.setStyleSheet("font-size:11px;color:#1b3a7a;")
            rl.addWidget(cb); rl.addWidget(name_lbl)
            gl.addWidget(row_w, row_i, col)
            col += 1
            if col >= 2: col = 0; row_i += 1
        s.addWidget(grid)
        # Store eff_list for use in _save
        self._eff_zmanim_list = eff_list


    def _build_element(self):
        s = self._section("אלמנט עיצובי")
        img_row = QWidget(); il = QHBoxLayout(img_row); il.setContentsMargins(0,0,0,0)
        self._elem_img_e = QLineEdit(self.pc.get("image_path",""))
        self._elem_img_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._inputs["image_path"] = self._elem_img_e
        pick = QPushButton("📂 עיון"); pick.setMinimumWidth(72); pick.setObjectName("btn_secondary")
        pick.clicked.connect(lambda: self._pick_file("image_path", self._elem_img_e))
        il.addWidget(self._elem_img_e); il.addWidget(pick)
        s.addWidget(form_row("קובץ תמונה:", img_row))
        fit = QComboBox(); fit.addItems(["contain","cover","stretch"])
        fit.setCurrentText(self.pc.get("fit_mode","contain"))
        self._inputs["fit_mode"] = fit
        s.addWidget(form_row("התאמה:", fit))

    def _build_notice(self):
        """Notice panels are popup-only templates — they pop up when reminders fire."""
        popup_note = QLabel("📢  חלונית הודעה צפה היא תבנית לתזכורות בלבד. היא לא מוצגת באופן קבוע על המסך — רק כשתזכורת מופעלת.")
        popup_note.setStyleSheet("color:#7a3a00;font-size:11px;padding:8px;background:#fff4e0;"
                                 "border:1px solid #e8a020;border-radius:6px;")
        popup_note.setWordWrap(True); popup_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._lay.addWidget(popup_note)

        s = self._section("הגדרות חלונית")
        self._check(s, "פעיל (popup בלבד — לא מוצג קבוע):", "popup_only", True)
        s.addWidget(hline())

        s2 = self._section("עיצוב טקסט")
        self._font_combo(s2, "גופן:", "font_family", "Arial")
        self._spin(s2, "גודל גופן:", "font_size", 8, 80, 26)
        self._color(s2, "צבע טקסט:", "font_color", "#f5a623")
        self._check(s2, "מודגש:", "bold", True)
        self._check(s2, "גלילה:", "scroll", True)
        self._spin(s2, "מהירות גלילה:", "scroll_speed", 1, 20, 2)
        scroll_dir = QComboBox(); scroll_dir.addItems(["ימינה לשמאל (RTL)", "שמאלה לימין (LTR)"])
        scroll_dir.setCurrentIndex(0 if self.pc.get("scroll_dir","rtl")=="rtl" else 1)
        self._inputs["scroll_dir"] = scroll_dir
        s2.addWidget(form_row("כיוון גלילה:", scroll_dir))
        s2.addWidget(hline())
        self._spin(s2, "זמן הצגה (שניות, 0=קבוע):", "popup_duration", 0, 300, 30)

        s3 = self._section("אנימציית כניסה / יציאה")
        enter_cb = QComboBox()
        enter_cb.addItems([
            "הופעה מיידית",
            "הופעה בהדרגה (Fade in)",
            "צף מלמטה (Slide up)",
            "צף מלמעלה (Slide down)",
            "צף מימין (Slide right)",
            "צף משמאל (Slide left)",
            "קפיצה (Bounce)",
        ])
        anim_enter_map = {
            "none": 0, "fade_in": 1, "slide_up": 2, "slide_down": 3,
            "slide_right": 4, "slide_left": 5, "bounce": 6,
        }
        enter_cb.setCurrentIndex(anim_enter_map.get(self.pc.get("anim_enter", "none"), 0))
        self._inputs["anim_enter"] = enter_cb
        s3.addWidget(form_row("אנימציית כניסה:", enter_cb))

        exit_cb = QComboBox()
        exit_cb.addItems([
            "היעלמות מיידית",
            "היעלמות בהדרגה (Fade out)",
            "צף למטה (Slide down)",
            "צף למעלה (Slide up)",
            "צף לימין (Slide right)",
            "צף לשמאל (Slide left)",
        ])
        anim_exit_map = {
            "none": 0, "fade_out": 1, "slide_down": 2, "slide_up": 3,
            "slide_right": 4, "slide_left": 5,
        }
        exit_cb.setCurrentIndex(anim_exit_map.get(self.pc.get("anim_exit", "none"), 0))
        self._inputs["anim_exit"] = exit_cb
        s3.addWidget(form_row("אנימציית יציאה:", exit_cb))

        self._spin(s3, "משך אנימציה (ms):", "anim_duration", 100, 2000, 400)

        # "Try" button — fires a test popup for 5 seconds
        try_btn = QPushButton("▶  נסה — הצג חלונית לדוגמה (5 שניות)")
        try_btn.setObjectName("btn_secondary")
        try_btn.setMinimumHeight(34)
        try_btn.clicked.connect(self._try_notice_popup)
        self._lay.addWidget(try_btn)

    def _try_notice_popup(self):
        """Save current settings and send a test-popup command to the display."""
        self._save()
        import json as _json
        cmd = {
            "action": "popup_notice_test",
            "panel_id": self.pc.get("id"),
            "duration": 5,
        }
        try:
            cmd_path = CFG.parent / "cmd.json"
            with open(cmd_path, "w", encoding="utf-8") as f:
                _json.dump(cmd, f)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "שגיאה", f"לא ניתן לשלוח פקודה: {e}")

    def _build_screen_msg(self):
        note = QLabel("⚙ עריכת תוכן ההודעה — בלשונית 'תוכן'")
        note.setStyleSheet("color:#2d5ec0;font-size:11px;padding:6px;background:#eef4ff;border-radius:6px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lay.addWidget(note)
        s = self._section("הגדרות הודעת מסך")
        self._font_combo(s,"גופן:","font_family","Arial")
        self._spin(s,"גודל גופן:","font_size",10,120,28)
        self._color(s,"צבע טקסט:","font_color",GOLD)
        self._check(s,"מודגש:","bold",True)
        self._check(s,"נטוי:","italic",False)
        align = QComboBox(); align.addItems(["ימין ←","מרכז","→ שמאל"])
        align_map = {"right":0,"center":1,"left":2}
        align.setCurrentIndex(align_map.get(self.pc.get("align","center"),1))
        self._inputs["align"] = align
        s.addWidget(form_row("יישור:", align))

    def _build_background(self):
        s = self._section("הגדרות רקע ראשי")
        _bg_col_btn = self._color(s,"צבע רקע:","bg_color","#070714")
        img_row = QWidget(); il = QHBoxLayout(img_row); il.setContentsMargins(0,0,0,0)
        self._bg_main_e = QLineEdit(self.pc.get("bg_image",""))
        self._bg_main_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._inputs["bg_image"] = self._bg_main_e
        pick = QPushButton("📂 עיון"); pick.setMinimumWidth(72); pick.setObjectName("btn_secondary")
        pick.clicked.connect(lambda: self._pick_file("bg_image", self._bg_main_e))
        clr = QPushButton("✕"); clr.setFixedWidth(30); clr.setObjectName("btn_secondary")
        clr.clicked.connect(self._bg_main_e.clear)
        il.addWidget(self._bg_main_e); il.addWidget(pick); il.addWidget(clr)
        s.addWidget(form_row("תמונת רקע:", img_row))
        # When bg_image is set, it overrides bg_color — disable color button
        def _sync_main_bg(text):
            has_img = bool(text.strip())
            _bg_col_btn.setEnabled(not has_img)
            _bg_col_btn.setToolTip("תמונת הרקע מחליפה את צבע המילוי" if has_img else "")
        self._bg_main_e.textChanged.connect(_sync_main_bg)
        _sync_main_bg(self._bg_main_e.text())
        self._check(s,"הצג כוכבים:","show_stars",True)
        self._check(s,"גרדיאנט:","gradient",True)

        # Screen margins: panels are constrained to this safe area
        s.addWidget(hline())
        margin_title = QLabel("שולי מסך — תחום בתוכו יוצגו הלוחות")
        margin_title.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;padding:4px 0 2px 0;")
        margin_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        s.addWidget(margin_title)

        margin_desc = QLabel("הגדר מרחק מינימלי מקצוות המסך — לוחות לא יוצגו מחוץ לתחום זה. ברירת מחדל: 0 מכל קצה.")
        margin_desc.setStyleSheet("color:#6070a0;font-size:11px;")
        margin_desc.setWordWrap(True)
        margin_desc.setAlignment(Qt.AlignmentFlag.AlignRight)
        s.addWidget(margin_desc)

        # Row 1: top & bottom
        sm_row1 = QWidget(); sm1l = QHBoxLayout(sm_row1); sm1l.setContentsMargins(0,0,0,0); sm1l.setSpacing(6)
        sm_lbl1 = QLabel("שוליים — למעלה/למטה:"); sm_lbl1.setStyleSheet("color:#4a5580;font-size:12px;")
        sm_lbl1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sm_top = QSpinBox(); sm_top.setRange(0, 500); sm_top.setValue(int(self.pc.get("screen_margin_top", 0)))
        sm_top.setFixedWidth(75); sm_top.setPrefix("↑ ")
        sm_bot = QSpinBox(); sm_bot.setRange(0, 500); sm_bot.setValue(int(self.pc.get("screen_margin_bottom", 0)))
        sm_bot.setFixedWidth(75); sm_bot.setPrefix("↓ ")
        self._inputs["screen_margin_top"]    = sm_top
        self._inputs["screen_margin_bottom"] = sm_bot
        sm1l.addStretch(); sm1l.addWidget(sm_lbl1); sm1l.addWidget(sm_top); sm1l.addWidget(sm_bot)
        s.addWidget(sm_row1)

        # Row 2: left & right
        sm_row2 = QWidget(); sm2l = QHBoxLayout(sm_row2); sm2l.setContentsMargins(0,0,0,0); sm2l.setSpacing(6)
        sm_lbl2 = QLabel("שוליים — ימין/שמאל:"); sm_lbl2.setStyleSheet("color:#4a5580;font-size:12px;")
        sm_lbl2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sm_right = QSpinBox(); sm_right.setRange(0, 500); sm_right.setValue(int(self.pc.get("screen_margin_right", 0)))
        sm_right.setFixedWidth(75); sm_right.setPrefix("→ ")
        sm_left  = QSpinBox(); sm_left.setRange(0, 500);  sm_left.setValue(int(self.pc.get("screen_margin_left",  0)))
        sm_left.setFixedWidth(75);  sm_left.setPrefix("← ")
        self._inputs["screen_margin_right"] = sm_right
        self._inputs["screen_margin_left"]  = sm_left
        sm2l.addStretch(); sm2l.addWidget(sm_lbl2); sm2l.addWidget(sm_right); sm2l.addWidget(sm_left)
        s.addWidget(sm_row2)

    def _build_fullscreen_msg(self):
        s = self._section("📺  הודעת מסך מלא — הגדרות")

        # Informational note
        note = QLabel("⚙ עריכת תוכן ההודעה — בלשונית 'תוכן'")
        note.setStyleSheet("color:#2d5ec0;font-size:11px;padding:6px;background:#eef4ff;border-radius:6px;")
        note.setAlignment(Qt.AlignmentFlag.AlignRight)
        s.addWidget(note)

        s.addWidget(hline())

        # Design settings
        self._color(s, "צבע רקע:", "bg_color", "#060015")
        self._color(s, "צבע טקסט:", "font_color", "#f5a623")
        self._spin(s, "גודל גופן:", "font_size", 18, 120, 48)
        self._spin(s, "סגירה אוטומטית (שניות, 0=ידנית):", "duration", 0, 300, 0)

        s.addWidget(hline())

        # Send now button
        send_row = QWidget(); srl = QHBoxLayout(send_row)
        srl.setContentsMargins(0, 4, 0, 4)
        send_btn = QPushButton("📺  שמור והצג עכשיו על המסך")
        send_btn.setObjectName("btn_warn")
        send_btn.setMinimumHeight(44)
        send_btn.clicked.connect(self._send_fullscreen_msg)
        srl.addWidget(send_btn)
        s.addWidget(send_row)

        self._send_status = QLabel("")
        self._send_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._send_status.setStyleSheet("color:#1a9a5c;font-size:12px;font-weight:bold;")
        s.addWidget(self._send_status)

        # Close note
        close_note = QLabel("לסגירה: לחץ על המסך, או F9")
        close_note.setStyleSheet("color:#a0b0cc;font-size:10px;")
        close_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.addWidget(close_note)

    def _send_fullscreen_msg(self):
        """Save settings and send fullscreen message to display."""
        self._save()
        content = self.pc.get("content", "").strip()
        if not content:
            self._send_status.setText("⚠ יש לרשום טקסט להודעה")
            return
        cmd = {
            "action": "fullscreen_msg",
            "text": content,
            "fontsize": self.pc.get("font_size", 48),
            "duration": self.pc.get("duration", 0),
            "fg": self.pc.get("font_color", "#f5a623"),
            "bg": self.pc.get("bg_color", "#060015"),
        }
        cmd_path = CFG.parent / "cmd.json"
        try:
            with open(cmd_path, "w", encoding="utf-8") as f:
                json.dump(cmd, f)
            self._send_status.setText("✓ ההודעה נשלחה למסך")
            QTimer.singleShot(3000, lambda: self._send_status.setText(""))
        except Exception as e:
            self._send_status.setText(f"⚠ שגיאה: {e}")

    def _pick_file(self, key, entry):
        """Open file dialog safely. Copies chosen image into the app's image store."""
        p, _ = QFileDialog.getOpenFileName(
            None, "בחר תמונה", "",
            "תמונות (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg)"
        )
        if p:
            p = Config.copy_image_to_store(p)
            entry.setText(p)

    # ── save ──────────────────────────────────────────────────────────────────
    def _save(self):
        INT_KEYS = {"x","y","width","height","border_width","font_size","time_font_size",
                    "date_font_size","scroll_speed","layer","interval","title_font_size",
                    "padding","segment_duration","popup_duration",
                    "date_line_spacing","date_scroll_speed","anim_duration",
                    "pad_top","pad_bottom","pad_left","pad_right",
                    "screen_margin_top","screen_margin_bottom","screen_margin_left","screen_margin_right",
                    "name_font_size","day_rollover_hour","day_rollover_minute",
                    "zmanim_row_spacing","zmanim_scroll_speed","zmanim_label_size","zmanim_time_size"}
        BOOL_KEYS = {"enabled","show_time","show_seconds","show_weekday","show_heb_date",
                     "show_greg_date","show_holiday","show_parasha","israel","bg_transparent",
                     "border_transparent","bold","italic","show_title","show_separator",
                     "highlight_next","scroll","show_stars","gradient","popup_only","date_scroll_inline",
                     "seg_separator_space",
                     "show_torah_reading","show_haftara","show_yaaleh_veyavo","show_morid_hatal",
                     "show_mashiv_haruach","show_vten_tal_umatar","show_daf_yomi"}
        STR_MAP = {
            "clock_style": ["digital","analog"],
            "analog_style": ["classic","minimal","roman","railway"],
            "time_format": ["24","12"],
            "align": ["center","right","left"],
            "scroll_dir": ["rtl","ltr"],
            "scroll_direction": ["up","down","right","left"],
            "date_layout": ["stacked","inline"],
            "anim_enter": ["none","fade_in","slide_up","slide_down","slide_right","slide_left","bounce"],
            "anim_exit":  ["none","fade_out","slide_down","slide_up","slide_right","slide_left"],
        }
        # Always treat panel_name as a plain string
        STR_KEYS = {"panel_name","font_family","bg_color","border_color","font_color",
                    "label_color","time_color","highlight_color","clock_color","date_color",
                    "wd_color","hd_color","gd_color","hol_color","par_color",
                    "tor_color","haf_color","yaaleh_color","morid_tal_color","mashiv_color",
                    "vten_color","daf_color",
                    "date_separator","date_layout","anim_enter","anim_exit",
                    "bg_image","image_path","title","fit_mode",
                    "name_font_family","time_font_family","name_font_color","time_font_color",
                    "seg_separator_char"}

        # layer from button group (may not exist for background/fullscreen)
        if hasattr(self, "_layer_grp"):
            for btn in self._layer_grp.buttons():
                if btn.isChecked():
                    self.pc["layer"] = btn.property("layer_val"); break

        for key, w in self._inputs.items():
            if isinstance(w, QLineEdit):
                v = w.text().strip()
                self.pc[key] = int(v) if key in INT_KEYS and v.lstrip("-").isdigit() else v
            elif isinstance(w, QSpinBox):
                self.pc[key] = w.value()
            elif isinstance(w, QCheckBox):
                self.pc[key] = w.isChecked()
            elif isinstance(w, QComboBox):
                if key in STR_MAP: self.pc[key] = STR_MAP[key][w.currentIndex()]
                else: self.pc[key] = w.currentText()
            elif isinstance(w, QPushButton) and hasattr(w, "_color"):
                self.pc[key] = w._color
            elif isinstance(w, QTextEdit):
                self.pc[key] = w.toPlainText()

        # Zmanim show_items — use uid from _eff_zmanim_list
        if hasattr(self, "_zmanim_checks"):
            eff = getattr(self, "_eff_zmanim_list", [(k,k,v) for k,v in ZMANIM_KEYS.items()])
            self.pc["show_items"] = [uid for uid, key, name in eff if self._zmanim_checks.get(uid, self._zmanim_checks.get(key)) and self._zmanim_checks.get(uid, self._zmanim_checks.get(key)).isChecked()]
        # Zmanim custom names
        if hasattr(self, "_zmanim_custom_names"):
            self.pc["zmanim_custom_names"] = self._zmanim_custom_names
        # Zmanim per-key calculation method
        if hasattr(self, "_zmanim_per_key_method"):
            self.pc["zmanim_per_key_method"] = self._zmanim_per_key_method
        # Zmanim display mode combo → string mapping
        if "zmanim_display_mode" in self._inputs:
            self.pc["zmanim_display_mode"] = self._inputs["zmanim_display_mode"].currentData()
        if "zmanim_row_layout" in self._inputs:
            self.pc["zmanim_row_layout"] = self._inputs["zmanim_row_layout"].currentData()
        if "zmanim_scroll" in self._inputs:
            self.pc["zmanim_scroll"] = self._inputs["zmanim_scroll"].currentData()
        if "zmanim_time_format" in self._inputs:
            self.pc["zmanim_time_format"] = "24" if self._inputs["zmanim_time_format"].currentIndex()==0 else "12"
        # Text panel scroll_mode uses .currentData() (not STR_MAP index)
        if "scroll_mode" in self._inputs:
            w = self._inputs["scroll_mode"]
            if isinstance(w, QComboBox) and w.currentData():
                self.pc["scroll_mode"] = w.currentData()

        # Panel schedule
        if hasattr(self, "_sched_grp") and self._sched_grp:
            if self._sched_grp.isChecked():
                self.pc["panel_schedule"] = {
                    "hours_enabled": self._ps_hours_cb.isChecked(),
                    "hour_from":     self._ps_hfrom.value(),
                    "hour_to":       self._ps_hto.value(),
                    "days_enabled":  self._ps_days_cb.isChecked(),
                    "active_days":   [i for i, cb in enumerate(self._ps_day_cbs) if cb.isChecked()],
                }
            else:
                self.pc["panel_schedule"] = {}

        # Board assignment
        if hasattr(self, "_board_cb"):
            self.pc["board_id"] = self._board_cb.currentData()

        # Background panel → save ALL keys to display dict
        if self.pc.get("type") == "background":
            disp = self.cfg.display()
            for k, v in self.pc.items():
                if k not in ("type", "id"):
                    disp[k] = v
            self.cfg.save()
        # Fullscreen msg panel → save to fullscreen_msg config section
        elif self.pc.get("type") == "fullscreen_msg":
            fm = {k: v for k, v in self.pc.items() if k not in ("type", "id")}
            self.cfg.d["fullscreen_msg"] = fm
            self.cfg.save()
        else:
            self.cfg.save()

        self.saved.emit()


# ── Import Report Dialog ──────────────────────────────────────────────────────
class _ImportReportDialog(QDialog):
    """Shows import result with optional text report save."""
    def __init__(self, title, msg, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(16, 16, 16, 16)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(msg)
        txt.setMinimumHeight(200)
        lay.addWidget(txt)
        self._msg = msg

        self._save_cb = QCheckBox("שמור דוח טקסט")
        lay.addWidget(self._save_cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self._on_ok)
        lay.addWidget(btns)

    def _on_ok(self):
        if self._save_cb.isChecked():
            path, _ = QFileDialog.getSaveFileName(self, "שמירת דוח", "import_report.txt",
                "קובץ טקסט (*.txt)")
            if path:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(self._msg)
                except Exception as e:
                    QMessageBox.warning(self, "שגיאה", str(e))
        self.accept()


# ── Content Tab ──────────────────────────────────────────────────────────────
class ContentTab(QWidget):
    """Dedicated tab for editing panel content (text, images) separate from styling."""
    display_refresh = pyqtSignal()

    CONTENT_TYPES = {"text", "screen_msg", "ad", "fullscreen_msg", "_schedule"}

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(10,14,10,10); sl.setSpacing(6)
        ttl = QLabel("עריכת תוכן לוחות"); ttl.setObjectName("sidebar_title"); sl.addWidget(ttl)
        sub = QLabel("בחר לוח לעריכת תוכנו"); sub.setObjectName("sidebar_sub"); sl.addWidget(sub)
        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        self._list.currentRowChanged.connect(self._on_select)
        sl.addWidget(self._list, 1)

        # Export/Import content
        io_grp = QGroupBox("יצוא / יבוא תוכן")
        iol = QHBoxLayout(io_grp); iol.setSpacing(4); iol.setContentsMargins(6, 6, 6, 6)
        exp_b = QPushButton("📤 יצוא תוכן"); exp_b.setObjectName("btn_success")
        exp_b.setStyleSheet("font-size:11px;padding:4px 8px;")
        exp_b.clicked.connect(self._export_content); iol.addWidget(exp_b)
        imp_b = QPushButton("📥 יבוא תוכן"); imp_b.setObjectName("btn_secondary")
        imp_b.setStyleSheet("font-size:11px;padding:4px 8px;")
        imp_b.clicked.connect(self._import_content); iol.addWidget(imp_b)
        sl.addWidget(io_grp)

        main.addWidget(sidebar)

        # ── Editor area ──
        self._editor_area = QStackedWidget()
        placeholder = QWidget()
        pl = QVBoxLayout(placeholder); pl.addStretch()
        pl_lbl = QLabel("← בחר לוח לעריכת תוכנו")
        pl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl_lbl.setStyleSheet("color:#7080a0;font-size:15px;")
        pl.addWidget(pl_lbl); pl.addStretch()
        self._editor_area.addWidget(placeholder)
        main.addWidget(self._editor_area, 1)

        self.refresh_list()

    def refresh_list(self):
        self._list.clear()
        # Fullscreen message first
        fm_item = QListWidgetItem("📺  הודעת מסך מלאה")
        fm_item.setData(Qt.ItemDataRole.UserRole, "fullscreen_msg")
        fm_item.setForeground(QColor("#c47a00"))
        self._list.addItem(fm_item)
        # Regular panels with content
        for p in self.cfg.panels():
            ptype = p.get("type","")
            if ptype not in self.CONTENT_TYPES: continue
            icon = PANEL_ICONS.get(ptype,"?")
            name = PANEL_NAMES.get(ptype,"?")
            st = "✓" if p.get("enabled",True) else "✗"
            item = QListWidgetItem(f"{icon}  {name} #{p['id']}  {st}")
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            if not p.get("enabled",True):
                item.setForeground(QColor("#a0aabb"))
            self._list.addItem(item)

    def _on_select(self, row):
        if row < 0: return
        item = self._list.item(row)
        if not item: return
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid == "fullscreen_msg":
            pc = dict(self.cfg.fullscreen_msg())
            pc["type"] = "fullscreen_msg"; pc["id"] = "📺"
            self._open_editor(pc, "fullscreen_msg")
        else:
            pc = self.cfg.get_panel(uid)
            if pc:
                self._open_editor(pc, pc.get("type",""))

    def _open_editor(self, pc, ptype):
        if ptype == "text":
            ed = TextContentEditor(self.cfg, pc, self)
        elif ptype in ("notice", "fullscreen_msg", "screen_msg"):
            ed = SimpleTextContentEditor(self.cfg, pc, self)
        elif ptype == "ad":
            ed = AdTimedContentEditor(self.cfg, pc, self)
        elif ptype == "_schedule":
            ed = ScheduleContentEditor(self.cfg, pc, self)
        else:
            return
        ed.saved.connect(self._on_saved)
        while self._editor_area.count() > 1:
            w = self._editor_area.widget(1)
            self._editor_area.removeWidget(w); w.deleteLater()
        self._editor_area.addWidget(ed)
        self._editor_area.setCurrentIndex(1)

    def _on_saved(self):
        self.display_refresh.emit()

    def _export_content(self):
        path, _ = QFileDialog.getSaveFileName(self, "יצוא תוכן לוחות", "תוכן.zip",
            "קובץ תוכן (*.zip)")
        if not path: return
        try:
            n_imgs, panels = self.cfg.export_content(path)
            names = "\n".join(f"  • {p.get('display_name','')}" for p in panels) or "  (לא נמצא תוכן)"
            QMessageBox.information(self, "יצוא תוכן הושלם",
                f"תוכן יוצא בהצלחה!\nתמונות שנכללו: {n_imgs}\n\nלוחות שיוצאו:\n{names}")
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _import_content(self):
        path, _ = QFileDialog.getOpenFileName(self, "יבוא תוכן לוחות", "",
            "קובץ תוכן (*.zip)")
        if not path: return
        reply = QMessageBox.question(self, "אישור יבוא תוכן",
            "יבוא התוכן ידרוס את תוכן הלוחות הקיים (טקסטים, מודעות).\n"
            "הגדרות עיצוב הלוחות לא ישתנו.\nהאם להמשיך?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            report = self.cfg.import_content(path)
            self._show_content_import_report(report)
            self.refresh_list()
            self.display_refresh.emit()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _show_content_import_report(self, report):
        lines = ["✅  יבוא תוכן הושלם!", ""]
        success = report.get("success", [])
        fail = report.get("fail", [])
        if success:
            lines.append("לוחות שתוכנם יובא בהצלחה:")
            for pn in success:
                lines.append(f"  ✓ {pn}")
        if fail:
            lines.append("")
            lines.append("לוחות שלא נמצאו (תוכנם לא יובא):")
            for pn in fail:
                lines.append(f"  ✗ {pn}")
        msg = "\n".join(lines)
        dlg = _ImportReportDialog("דוח יבוא תוכן", msg, self)
        dlg.exec()


class _BaseContentEditor(QWidget):
    saved = pyqtSignal()

    def __init__(self, cfg, pc, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.pc = pc
        self._build()

    def _build(self): pass

    def _hdr(self, title, icon="✏"):
        hdr = QWidget()
        hdr.setStyleSheet("background:#eef2fc;border-bottom:1px solid #dde8f8;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(14,10,14,10)
        lbl = QLabel(f"{icon}  {title}")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1b3a7a;")
        save_btn = QPushButton("💾  שמור")
        save_btn.setObjectName("btn_success")
        save_btn.setFixedWidth(130)
        save_btn.setMinimumHeight(38)
        save_btn.setStyleSheet(
            "QPushButton#btn_success{"
            "background:#1a9a5c;color:white;font-size:14px;font-weight:bold;"
            "border-radius:8px;padding:8px 18px;}"
            "QPushButton#btn_success:hover{background:#22bb6e;}"
        )
        save_btn.clicked.connect(self._save)
        hl.addWidget(save_btn); hl.addStretch(); hl.addWidget(lbl)
        return hdr

    def _save(self): pass


class TextContentEditor(_BaseContentEditor):
    """Text panel content editor.
    Uses a single segments-based UI (no tabs).
    Segments are the source of truth; in non-segment scroll modes they are
    concatenated and displayed as one continuous block.
    Scheduling per-segment has been removed (done via panel schedule settings).
    """

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        ptype = self.pc.get("type","")
        name = PANEL_NAMES.get(ptype,"לוח")
        lay.addWidget(self._hdr(f"עריכת תוכן: {name} #{self.pc.get('id','—')}"))

        # ── Toolbar — RTL order, clearly visible buttons ──────────────────────
        tb = QWidget()
        tb.setStyleSheet("background:#eef2fc;border-bottom:1.5px solid #c8d4f0;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(8,6,8,6); tbl.setSpacing(4)
        # Build RTL: from right side add in order B I U S | font | size | color | align | padding
        tbl.addStretch()  # push everything to the right

        def tb_lbl(t):
            l = QLabel(t); l.setStyleSheet("color:#2d3a5a;font-size:11px;"); return l

        # Padding
        self._pad_sp = QSpinBox(); self._pad_sp.setRange(0,80)
        self._pad_sp.setValue(int(self.pc.get("padding",14))); self._pad_sp.setFixedWidth(56)
        # Align
        self._align_cb = QComboBox(); self._align_cb.setFixedWidth(90)
        self._align_cb.addItems(["ימין ←","מרכז","→ שמאל"])
        align_map = {"right":0,"center":1,"left":2}
        self._align_cb.setCurrentIndex(align_map.get(self.pc.get("align","right"),0))

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color:#a0b4d0;"); sep1.setFixedHeight(22)

        # Color, size, font
        self._color_btn = color_btn(self.pc.get("font_color","#ffffff"), self)
        self._size_sp = QSpinBox(); self._size_sp.setRange(6,140)
        self._size_sp.setValue(int(self.pc.get("font_size",20))); self._size_sp.setFixedWidth(60)
        from PyQt6.QtGui import QFontDatabase as _QFD
        self._font_e = QComboBox(); self._font_e.setEditable(True); self._font_e.setFixedWidth(130)
        self._font_e.addItems(sorted(_QFD.families()))
        _cur_f = self.pc.get("font_family","Arial")
        _fidx = self._font_e.findText(_cur_f)
        self._font_e.setCurrentIndex(_fidx if _fidx >= 0 else 0)
        if _fidx < 0: self._font_e.setCurrentText(_cur_f)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color:#a0b4d0;"); sep2.setFixedHeight(22)

        # Format toggles — clearly visible, dark style
        TOGGLE_STYLE = (
            "QPushButton{background:#c8d4f0;color:#1a2847;border:1.5px solid #8fa8d8;"
            "border-radius:5px;padding:3px 8px;font-size:13px;min-width:28px;}"
            "QPushButton:checked{background:#2d5ec0;color:white;border-color:#1b3a7a;}"
            "QPushButton:hover{background:#b0c0e8;}"
        )
        def fmt_btn(label, tooltip, extra_style=""):
            b = QPushButton(label); b.setCheckable(True); b.setFixedSize(30,28)
            b.setStyleSheet(TOGGLE_STYLE + extra_style); b.setToolTip(tooltip)
            return b

        self._bold_btn   = fmt_btn("B","מודגש","QPushButton{font-weight:bold;}")
        self._italic_btn = fmt_btn("I","נטוי","QPushButton{font-style:italic;}")
        self._under_btn  = fmt_btn("U","קו תחתון","QPushButton{text-decoration:underline;}")
        self._strike_btn = fmt_btn("S","קו חוצה","QPushButton{text-decoration:line-through;}")

        self._bold_btn.setChecked(bool(self.pc.get("bold",False)))
        self._italic_btn.setChecked(bool(self.pc.get("italic",False)))
        self._under_btn.setChecked(bool(self.pc.get("underline",False)))
        self._strike_btn.setChecked(bool(self.pc.get("overstrike",False)))

        # RTL layout: rightmost = B I U S, then separator, font/size/color, separator, align/padding
        for w in [self._bold_btn, self._italic_btn, self._under_btn, self._strike_btn,
                  sep2,
                  tb_lbl("גופן:"), self._font_e,
                  tb_lbl("גודל:"), self._size_sp,
                  tb_lbl("צבע:"), self._color_btn,
                  sep1,
                  tb_lbl("יישור:"), self._align_cb,
                  tb_lbl("ריפוד:"), self._pad_sp]:
            tbl.addWidget(w)
        lay.addWidget(tb)

        # ── Main area: segments list + editor ────────────────────────────────
        main_w = QWidget(); main_l = QHBoxLayout(main_w)
        main_l.setContentsMargins(8,8,8,8); main_l.setSpacing(8)

        # Left: segment list + controls
        left_w = QWidget(); left_w.setFixedWidth(240)
        left_l = QVBoxLayout(left_w); left_l.setContentsMargins(0,0,0,0); left_l.setSpacing(4)

        seg_lbl = QLabel("מקטעי טקסט:")
        seg_lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        seg_lbl.setAlignment(Qt.AlignmentFlag.AlignRight); left_l.addWidget(seg_lbl)

        self._seg_list = QListWidget(); self._seg_list.setMinimumHeight(160)
        self._seg_list.currentRowChanged.connect(self._on_seg_select)
        self._segments_data = list(self.pc.get("content_segments",[]))
        # Migrate: if no segments but has content, create one segment from content
        if not self._segments_data and self.pc.get("content",""):
            self._segments_data = [{"text": self.pc.get("content","")}]
        self._refresh_seg_list()
        left_l.addWidget(self._seg_list, 1)

        seg_btns = QWidget(); sbl = QHBoxLayout(seg_btns)
        sbl.setContentsMargins(0,0,0,0); sbl.addStretch()
        for label, slot in [("↓",self._seg_move_down),("↑",self._seg_move_up),
                              ("✕",self._seg_del),("+ הוסף",self._seg_add)]:
            b = QPushButton(label)
            b.setObjectName("btn_success" if "הוסף" in label else "btn_secondary")
            b.setMaximumHeight(30); b.clicked.connect(slot); sbl.addWidget(b)
        left_l.addWidget(seg_btns)

        info_lbl = QLabel(
            "💡 מקטעים מוצגים אחד אחרי השני בגלילה רציפה. "
            "בחר 'גלילת מקטעים' בהגדרות כדי להציגם בנפרד."
        )
        info_lbl.setStyleSheet("color:#6070a0;font-size:10px;")
        info_lbl.setWordWrap(True); left_l.addWidget(info_lbl)
        main_l.addWidget(left_w)

        # Right: text editor for selected segment
        right_w = QWidget(); right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(0,0,0,0); right_l.setSpacing(4)

        seg_edit_lbl = QLabel("טקסט המקטע הנבחר:")
        seg_edit_lbl.setStyleSheet("color:#4a5580;font-size:11px;font-weight:bold;")
        seg_edit_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_l.addWidget(seg_edit_lbl)

        self._te = QTextEdit()
        self._te.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._te.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._te.setStyleSheet("QTextEdit{font-size:14px;padding:8px;background:#fafcff;}")
        self._te.setMinimumHeight(180)
        self._te.textChanged.connect(self._on_text_changed)
        right_l.addWidget(self._te, 1)

        # Segment action buttons
        seg_action_row = QWidget(); sal = QHBoxLayout(seg_action_row)
        sal.setContentsMargins(0,4,0,0); sal.addStretch()
        save_seg_btn = QPushButton("💾 שמור מקטע")
        save_seg_btn.setObjectName("btn_success"); save_seg_btn.clicked.connect(self._seg_save)
        sal.addWidget(save_seg_btn)
        right_l.addWidget(seg_action_row)

        main_l.addWidget(right_w, 1)
        lay.addWidget(main_w, 1)

        # ── Bottom save button ───────────────────────────────────────────────
        save_btn = QPushButton("💾  שמור הכל")
        save_btn.setObjectName("btn_success"); save_btn.setMinimumHeight(38)
        save_btn.clicked.connect(self._save)
        lay.addWidget(save_btn)

        self._align_cb.currentIndexChanged.connect(self._apply_align)
        self._apply_align(self._align_cb.currentIndex())
        self._current_seg_idx = -1

        # Select first segment if any
        if self._segments_data:
            self._seg_list.setCurrentRow(0)

    def _apply_align(self, idx):
        a = [Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignCenter, Qt.AlignmentFlag.AlignLeft][idx]
        d = [Qt.LayoutDirection.RightToLeft, Qt.LayoutDirection.RightToLeft, Qt.LayoutDirection.LeftToRight][idx]
        self._te.setAlignment(a); self._te.setLayoutDirection(d)

    def _on_text_changed(self):
        """Live-update the current segment text as user types."""
        row = self._seg_list.currentRow()
        if row < 0 or row >= len(self._segments_data): return
        self._segments_data[row]["text"] = self._te.toPlainText()
        # Live-save formatting too
        s = self._segments_data[row]
        s["bold"] = self._bold_btn.isChecked()
        s["italic"] = self._italic_btn.isChecked()
        s["underline"] = self._under_btn.isChecked()
        s["overstrike"] = self._strike_btn.isChecked()
        s["font_family"] = self._font_e.currentText().strip() if hasattr(self._font_e, "currentText") else self._font_e.text().strip() or "Arial"
        s["font_size"] = self._size_sp.value()
        s["font_color"] = self._color_btn._color
        align_map = {0:"right",1:"center",2:"left"}
        s["align"] = align_map[self._align_cb.currentIndex()]
        self._refresh_seg_list()
        self._seg_list.blockSignals(True)
        self._seg_list.setCurrentRow(row)
        self._seg_list.blockSignals(False)

    def _refresh_seg_list(self):
        self._seg_list.clear()
        for i, s in enumerate(self._segments_data):
            text = s.get("text","")
            preview = text[:35].replace("\n"," ") + ("…" if len(text)>35 else "")
            self._seg_list.addItem(f"[{i+1}]  {preview}")

    def _on_seg_select(self, row):
        if row < 0 or row >= len(self._segments_data): return
        self._current_seg_idx = row
        s = self._segments_data[row]
        # Block signals while loading segment data
        self._te.blockSignals(True)
        self._bold_btn.blockSignals(True)
        self._italic_btn.blockSignals(True)
        self._under_btn.blockSignals(True)
        self._strike_btn.blockSignals(True)
        self._te.setPlainText(s.get("text",""))
        # Load this segment's formatting (fall back to panel-level defaults)
        self._bold_btn.setChecked(s.get("bold", bool(self.pc.get("bold",False))))
        self._italic_btn.setChecked(s.get("italic", bool(self.pc.get("italic",False))))
        self._under_btn.setChecked(s.get("underline", bool(self.pc.get("underline",False))))
        self._strike_btn.setChecked(s.get("overstrike", bool(self.pc.get("overstrike",False))))
        self._font_e.setCurrentText(s.get("font_family", self.pc.get("font_family","Arial")))
        self._size_sp.setValue(s.get("font_size", int(self.pc.get("font_size",20))))
        self._color_btn._color = s.get("font_color", self.pc.get("font_color","#ffffff"))
        # Refresh color button visual
        self._color_btn.setStyleSheet(
            f"#color_swatch{{background:{self._color_btn._color};"
            f"border:2px solid #c8d8f0;border-radius:6px;}}"
            f"#color_swatch:hover{{border-color:#2d5ec0;}}"
        )
        align_map = {"right":0,"center":1,"left":2}
        self._align_cb.setCurrentIndex(align_map.get(s.get("align", self.pc.get("align","right")),0))
        self._te.blockSignals(False)
        self._bold_btn.blockSignals(False)
        self._italic_btn.blockSignals(False)
        self._under_btn.blockSignals(False)
        self._strike_btn.blockSignals(False)

    def _seg_add(self):
        self._segments_data.append({"text":""})
        self._refresh_seg_list()
        self._seg_list.setCurrentRow(len(self._segments_data)-1)

    def _seg_del(self):
        row = self._seg_list.currentRow()
        if 0 <= row < len(self._segments_data):
            self._segments_data.pop(row)
            self._refresh_seg_list()
            if self._segments_data:
                self._seg_list.setCurrentRow(min(row, len(self._segments_data)-1))
            else:
                self._te.clear()

    def _seg_move_up(self):
        row = self._seg_list.currentRow()
        if row > 0:
            self._segments_data[row-1], self._segments_data[row] = \
                self._segments_data[row], self._segments_data[row-1]
            self._refresh_seg_list(); self._seg_list.setCurrentRow(row-1)

    def _seg_move_down(self):
        row = self._seg_list.currentRow()
        if 0 <= row < len(self._segments_data)-1:
            self._segments_data[row+1], self._segments_data[row] = \
                self._segments_data[row], self._segments_data[row+1]
            self._refresh_seg_list(); self._seg_list.setCurrentRow(row+1)

    def _seg_save(self):
        """Save current textarea content + formatting to the selected segment."""
        row = self._seg_list.currentRow()
        if row < 0 or row >= len(self._segments_data): return
        s = self._segments_data[row]
        s["text"] = self._te.toPlainText()
        s["bold"] = self._bold_btn.isChecked()
        s["italic"] = self._italic_btn.isChecked()
        s["underline"] = self._under_btn.isChecked()
        s["overstrike"] = self._strike_btn.isChecked()
        s["font_family"] = self._font_e.currentText().strip() if hasattr(self._font_e, "currentText") else self._font_e.text().strip() or "Arial"
        s["font_size"] = self._size_sp.value()
        s["font_color"] = self._color_btn._color
        align_map = {0:"right",1:"center",2:"left"}
        s["align"] = align_map[self._align_cb.currentIndex()]
        self._refresh_seg_list(); self._seg_list.setCurrentRow(row)

    def _save(self):
        # Ensure current textarea is saved to its segment
        row = self._seg_list.currentRow()
        if 0 <= row < len(self._segments_data):
            self._segments_data[row]["text"] = self._te.toPlainText()

        # Build combined content string (all segments joined with newline)
        # This is used in static/continuous-scroll modes
        combined = "\n".join(s.get("text","") for s in self._segments_data if s.get("text","").strip())
        self.pc["content"] = combined
        self.pc["content_segments"] = self._segments_data
        self.pc["font_family"] = self._font_e.currentText().strip() if hasattr(self._font_e, "currentText") else self._font_e.text().strip() or "Arial"
        self.pc["font_size"] = self._size_sp.value()
        self.pc["font_color"] = self._color_btn._color
        self.pc["bold"] = self._bold_btn.isChecked()
        self.pc["italic"] = self._italic_btn.isChecked()
        self.pc["underline"] = self._under_btn.isChecked()
        self.pc["overstrike"] = self._strike_btn.isChecked()
        self.pc["padding"] = self._pad_sp.value()
        align_map = {0:"right",1:"center",2:"left"}
        self.pc["align"] = align_map[self._align_cb.currentIndex()]

        pid = self.pc.get("id")
        if pid and pid not in ("—",):
            for p in self.cfg.panels():
                if p.get("id") == pid:
                    p.update(self.pc); break
        self.cfg.save()
        self.saved.emit()

class SimpleTextContentEditor(_BaseContentEditor):
    """Notice/fullscreen_msg content editor with full text-styling toolbar."""

    def _build(self):
        try:
            self._build_inner()
        except Exception as _e:
            import traceback
            lay = QVBoxLayout(self)
            err = QLabel(f"⚠ שגיאה בטעינת העורך:\n{_e}\n\n{traceback.format_exc()}")
            err.setStyleSheet("color:red;padding:10px;font-size:11px;")
            err.setWordWrap(True)
            lay.addWidget(err)

    def _build_inner(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        ptype = self.pc.get("type","")
        name = PANEL_NAMES.get(ptype,"לוח")
        pid = self.pc.get('id','—')
        title = f"עריכת תוכן: {name}" + (f" #{pid}" if pid not in ("—","📺") else "")
        icon_map = {"notice":"📢","screen_msg":"💬","fullscreen_msg":"📺"}
        lay.addWidget(self._hdr(title, icon_map.get(ptype,"✏")))

        # ── Toolbar (same as TextContentEditor) ──────────────────────────────
        tb = QWidget()
        tb.setStyleSheet("background:#f0f4fb;border-bottom:1.5px solid #d0dcf0;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(8,5,8,5); tbl.setSpacing(4)

        def tb_lbl(t):
            l = QLabel(t); l.setStyleSheet("color:#4a5580;font-size:11px;"); return l

        TOGGLE_STYLE = (
            "QPushButton{background:#c8d4f0;color:#1a2847;border:1.5px solid #8fa8d8;"
            "border-radius:5px;padding:3px 8px;font-size:13px;min-width:28px;}"
            "QPushButton:checked{background:#2d5ec0;color:white;border-color:#1b3a7a;}"
            "QPushButton:hover{background:#b0c0e8;}"
        )
        def fmt_btn(label, tooltip, extra_style=""):
            b = QPushButton(label); b.setCheckable(True); b.setFixedSize(30,28)
            b.setStyleSheet(TOGGLE_STYLE + extra_style); b.setToolTip(tooltip)
            return b
        self._bold_btn   = fmt_btn("B","מודגש","QPushButton{font-weight:bold;}")
        self._italic_btn = fmt_btn("I","נטוי","QPushButton{font-style:italic;}")

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color:#a0b4d0;"); sep1.setFixedHeight(22)

        self._font_e = QComboBox(); self._font_e.setEditable(True)
        from PyQt6.QtGui import QFontDatabase as _QFD2
        self._font_e.addItems(sorted(_QFD2.families()))
        _cur_f2 = self.pc.get("font_family","Arial")
        _fidx2 = self._font_e.findText(_cur_f2)
        self._font_e.setCurrentIndex(_fidx2 if _fidx2 >= 0 else 0)
        if _fidx2 < 0: self._font_e.setCurrentText(_cur_f2)
        self._font_e.setFixedWidth(130)
        self._size_sp = QSpinBox(); self._size_sp.setRange(6,140)
        self._size_sp.setValue(int(self.pc.get("font_size",26)))
        self._size_sp.setFixedWidth(60)
        self._color_btn = color_btn(self.pc.get("font_color", GOLD if ptype=="notice" else "#f5a623"), self)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color:#a0b4d0;"); sep2.setFixedHeight(22)

        # Scroll settings for notice
        if ptype == "notice":
            self._scroll_cb = QCheckBox("גלילה"); self._scroll_cb.setChecked(bool(self.pc.get("scroll",True)))
            self._speed_sp = QSpinBox(); self._speed_sp.setRange(1,30); self._speed_sp.setValue(int(self.pc.get("scroll_speed",2)))
            self._speed_sp.setFixedWidth(50)
            self._dir_cb = QComboBox(); self._dir_cb.addItems(["ימין←שמאל","שמאל←ימין"])
            self._dir_cb.setCurrentIndex(0 if self.pc.get("scroll_dir","rtl")=="rtl" else 1)
            self._dir_cb.setFixedWidth(100)
        else:
            self._scroll_cb = self._speed_sp = self._dir_cb = None

        self._bold_btn.setChecked(bool(self.pc.get("bold",True)))
        self._italic_btn.setChecked(bool(self.pc.get("italic",False)))

        # RTL order: rightmost = B I, then separator, font/size/color
        tbl.addStretch()
        for w in [self._bold_btn, self._italic_btn, sep1,
                  tb_lbl("גופן:"), self._font_e,
                  tb_lbl("גודל:"), self._size_sp,
                  tb_lbl("צבע:"), self._color_btn]:
            tbl.addWidget(w)
        if ptype == "notice":
            tbl.addWidget(sep2)
            for w in [self._scroll_cb, tb_lbl("מהירות:"), self._speed_sp, tb_lbl("כיוון:"), self._dir_cb]:
                tbl.addWidget(w)
        lay.addWidget(tb)

        # ── Text editor ──────────────────────────────────────────────────────
        self._te = QTextEdit()
        self._te.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._te.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._te.setPlainText(self.pc.get("content",""))
        self._te.setMinimumHeight(120)
        self._te.setStyleSheet("QTextEdit{font-size:15px;padding:10px;background:#fafcff;}")
        lay.addWidget(self._te, 1)

        if ptype == "fullscreen_msg":
            note = QLabel("לאחר שמירה — בלשונית 'תצוגה' בחר 'הודעת מסך מלא' ולחץ 'שמור והצג עכשיו'")
            note.setStyleSheet("color:#6070a0;font-size:11px;padding:4px;")
            note.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(note)

    def _save(self):
        content = self._te.toPlainText()
        self.pc["content"] = content
        self.pc["font_family"] = self._font_e.currentText().strip() if hasattr(self._font_e, "currentText") else self._font_e.text().strip() or "Arial"
        self.pc["font_size"] = self._size_sp.value()
        self.pc["font_color"] = self._color_btn._color
        self.pc["bold"] = self._bold_btn.isChecked()
        self.pc["italic"] = self._italic_btn.isChecked()
        if self._scroll_cb is not None:
            self.pc["scroll"] = self._scroll_cb.isChecked()
            self.pc["scroll_speed"] = self._speed_sp.value()
            self.pc["scroll_dir"] = "rtl" if self._dir_cb.currentIndex()==0 else "ltr"

        ptype = self.pc.get("type","")
        if ptype == "fullscreen_msg":
            fm = self.cfg.d.setdefault("fullscreen_msg", {})
            fm.update({k:v for k,v in self.pc.items() if k not in ("type","id")})
        else:
            pid = self.pc.get("id")
            if pid:
                for p in self.cfg.panels():
                    if p.get("id") == pid:
                        p.update(self.pc); break
        self.cfg.save()
        self.saved.emit()


class AdContentEditor(_BaseContentEditor):
    """Image list manager for ad panels."""

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        name = PANEL_NAMES.get("ad","מודעה")
        lay.addWidget(self._hdr(f"עריכת תמונות: {name} #{self.pc.get('id','—')}", "🖼"))

        inner = QWidget(); il = QVBoxLayout(inner); il.setContentsMargins(16,12,16,16); il.setSpacing(8)

        lbl = QLabel("רשימת תמונות (סדר = סדר הצגה):")
        lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:13px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight); il.addWidget(lbl)

        self._img_list = QListWidget()
        self._img_list.setMinimumHeight(180)
        for img in self.pc.get("images",[]):
            self._img_list.addItem(img)
        il.addWidget(self._img_list)

        btn_row = QWidget(); br = QHBoxLayout(btn_row); br.setContentsMargins(0,0,0,0); br.addStretch()
        for text, slot in [("↓ הורד",self._move_down),("↑ העלה",self._move_up),
                           ("✕ הסר",self._remove_img),("+ הוסף תמונות",self._add_imgs)]:
            b = QPushButton(text)
            b.setObjectName("btn_secondary" if text != "+ הוסף תמונות" else "btn_success")
            b.clicked.connect(slot); br.addWidget(b)
        il.addWidget(btn_row)

        note = QLabel("גרור שורות לשינוי הסדר | לחץ ✕ להסרה")
        note.setStyleSheet("color:#8090b0;font-size:10px;"); note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(note)
        il.addStretch()
        lay.addWidget(scroll_wrap(inner), 1)

    def _add_imgs(self):
        paths, _ = QFileDialog.getOpenFileNames(
            None, "בחר תמונות", "",
            "תמונות (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        for p in paths:
            stored = Config.copy_image_to_store(p)
            self._img_list.addItem(stored)

    def _remove_img(self):
        row = self._img_list.currentRow()
        if row >= 0: self._img_list.takeItem(row)

    def _move_up(self):
        row = self._img_list.currentRow()
        if row > 0:
            item = self._img_list.takeItem(row)
            self._img_list.insertItem(row-1, item)
            self._img_list.setCurrentRow(row-1)

    def _move_down(self):
        row = self._img_list.currentRow()
        if row < self._img_list.count()-1:
            item = self._img_list.takeItem(row)
            self._img_list.insertItem(row+1, item)
            self._img_list.setCurrentRow(row+1)

    def _save(self):
        images = [self._img_list.item(i).text() for i in range(self._img_list.count())]
        self.pc["images"] = images
        pid = self.pc.get("id")
        if pid:
            for p in self.cfg.panels():
                if p.get("id") == pid:
                    p["images"] = images; break
        self.cfg.save()
        self.saved.emit()


# ── Schedule Content Editor ───────────────────────────────────────────────────
class ScheduleContentEditor(_BaseContentEditor):
    """Events editor for schedule panel."""

    HEB_PARASHA_LIST = [
        "בראשית","נח","לך לך","וירא","חיי שרה","תולדות","ויצא","וישלח","וישב","מקץ",
        "ויגש","ויחי","שמות","וארא","בא","בשלח","יתרו","משפטים","תרומה","תצוה",
        "כי תשא","ויקהל","פקודי","ויקרא","צו","שמיני","תזריע","מצורע","אחרי מות",
        "קדושים","אמור","בהר","בחוקותי","במדבר","נשא","בהעלותך","שלח","קרח",
        "חקת","בלק","פינחס","מטות","מסעי","דברים","ואתחנן","עקב","ראה","שופטים",
        "כי תצא","כי תבוא","נצבים","וילך","האזינו","וזאת הברכה",
    ]

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        name = PANEL_NAMES.get("_schedule","לוח זמנים")
        lay.addWidget(self._hdr(f"עריכת תוכן: {name} #{self.pc.get('id','—')}"))

        # Top controls
        top = QWidget(); top_l = QHBoxLayout(top)
        top_l.setContentsMargins(12,8,12,6); top_l.setSpacing(8); top_l.addStretch()
        add_btn = QPushButton("＋ הוסף אירוע")
        add_btn.setObjectName("btn_success"); add_btn.clicked.connect(self._add_event)
        top_l.addWidget(add_btn)
        lay.addWidget(top)

        # Splitter: top=list (smaller), bottom=edit panel (larger)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Events list
        list_w = QWidget(); list_l = QVBoxLayout(list_w)
        list_l.setContentsMargins(8,4,8,4); list_l.setSpacing(4)
        self._events_list = QListWidget(); self._events_list.setMinimumHeight(80)
        self._events_list.currentRowChanged.connect(self._on_select)
        self._events = list(self.pc.get("events",[]))
        self._refresh_list()
        list_l.addWidget(self._events_list)
        splitter.addWidget(list_w)

        # Edit panel
        edit_w = QWidget()
        edit_w.setStyleSheet("background:#f3f6fb;")
        edit_outer = QVBoxLayout(edit_w)
        edit_outer.setContentsMargins(0,0,0,0); edit_outer.setSpacing(0)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        edit_inner = QWidget(); ec_l = QVBoxLayout(edit_inner)
        ec_l.setContentsMargins(16,14,16,14); ec_l.setSpacing(10)
        ec_l.setAlignment(Qt.AlignmentFlag.AlignTop)

        def rtl_label(text, bold=False, size=11):
            l = QLabel(text)
            style = f"color:#1b3a7a;font-size:{size}px;"
            if bold: style += "font-weight:bold;"
            l.setStyleSheet(style)
            l.setAlignment(Qt.AlignmentFlag.AlignRight)
            return l

        # ── Required fields ─────────────────────────────────────────────────
        ec_l.addWidget(rtl_label("שדות חובה:", bold=True, size=12))

        req_row = QWidget(); req_l = QHBoxLayout(req_row)
        req_l.setContentsMargins(0,0,0,0); req_l.setSpacing(20)
        req_l.setDirection(QHBoxLayout.Direction.RightToLeft)

        name_col = QWidget(); nc_l = QVBoxLayout(name_col); nc_l.setContentsMargins(0,0,0,0); nc_l.setSpacing(3)
        nc_l.addWidget(rtl_label("שם האירוע *"))
        self._name_e = QLineEdit(); self._name_e.setPlaceholderText("שם האירוע")
        self._name_e.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._name_e.setMinimumWidth(200)
        nc_l.addWidget(self._name_e)

        time_col = QWidget(); tc_l = QVBoxLayout(time_col); tc_l.setContentsMargins(0,0,0,0); tc_l.setSpacing(3)
        tc_l.addWidget(rtl_label("שעה *"))
        self._time_e = QLineEdit(); self._time_e.setPlaceholderText("HH:MM")
        self._time_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._time_e.setFixedWidth(90)
        tc_l.addWidget(self._time_e)

        req_l.addWidget(name_col); req_l.addWidget(time_col)
        req_l.addStretch()
        ec_l.addWidget(req_row)
        ec_l.addWidget(hline())

        # ── Advanced: date range ─────────────────────────────────────────────
        ec_l.addWidget(rtl_label("הגדרות מתי להציג את האירוע:", bold=True, size=11))

        # Date range row
        dr_row = QWidget(); dr_l = QHBoxLayout(dr_row)
        dr_l.setContentsMargins(0,0,0,0); dr_l.setSpacing(8)
        dr_l.setDirection(QHBoxLayout.Direction.RightToLeft)

        self._dr_cb = QCheckBox("טווח תאריכים")
        self._dr_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        dr_fields = QWidget(); drf_l = QHBoxLayout(dr_fields)
        drf_l.setContentsMargins(0,0,0,0); drf_l.setSpacing(6)
        drf_l.setDirection(QHBoxLayout.Direction.RightToLeft)
        from_lbl = QLabel("מ-"); from_lbl.setStyleSheet("color:#4a5580;")
        self._dr_from = QLineEdit(); self._dr_from.setPlaceholderText("DD/MM/YYYY")
        self._dr_from.setFixedWidth(100); self._dr_from.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        to_lbl = QLabel("עד"); to_lbl.setStyleSheet("color:#4a5580;")
        self._dr_to = QLineEdit(); self._dr_to.setPlaceholderText("DD/MM/YYYY")
        self._dr_to.setFixedWidth(100); self._dr_to.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        drf_l.addWidget(from_lbl); drf_l.addWidget(self._dr_from)
        drf_l.addWidget(to_lbl);   drf_l.addWidget(self._dr_to)

        dr_l.addWidget(self._dr_cb); dr_l.addWidget(dr_fields); dr_l.addStretch()
        ec_l.addWidget(dr_row)
        self._dr_cb.toggled.connect(lambda v: [self._dr_from.setEnabled(v), self._dr_to.setEnabled(v)])

        # Weekdays row
        wd_lbl = rtl_label("ימים בשבוע (ריק = כל הימים):")
        ec_l.addWidget(wd_lbl)
        wd_row = QWidget(); wd_l = QHBoxLayout(wd_row)
        wd_l.setContentsMargins(0,0,0,0); wd_l.setSpacing(10)
        wd_l.setDirection(QHBoxLayout.Direction.RightToLeft)
        # RTL: ש(6) ו(5) ה(4) ד(3) ג(2) ב(1) א(0)
        DAY_LABELS = [("ש",6),("ו",5),("ה",4),("ד",3),("ג",2),("ב",1),("א",0)]
        self._day_cbs = {}
        for label, day_num in DAY_LABELS:
            cb = QCheckBox(label)
            cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            cb.setStyleSheet("font-size:12px;font-weight:bold;color:#1b3a7a;")
            self._day_cbs[day_num] = cb
            wd_l.addWidget(cb)
        wd_l.addStretch()
        ec_l.addWidget(wd_row)

        # Parasha weeks
        ec_l.addWidget(rtl_label("הצג רק בשבועות (פרשיות) — בחר מהרשימה:"))
        self._pw_cb = QCheckBox("הפעל סינון לפי פרשת שבוע")
        self._pw_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        ec_l.addWidget(self._pw_cb)
        self._parasha_list = QListWidget()
        self._parasha_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._parasha_list.setMaximumHeight(100); self._parasha_list.setEnabled(False)
        self._parasha_list.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        for p_name in self.HEB_PARASHA_LIST:
            self._parasha_list.addItem(p_name)
        self._pw_cb.toggled.connect(self._parasha_list.setEnabled)
        ec_l.addWidget(self._parasha_list)

        # Action buttons — clearly visible
        btn_row = QWidget(); btn_l = QHBoxLayout(btn_row)
        btn_l.setContentsMargins(0,10,0,0); btn_l.addStretch()
        DANGER_STYLE = ("QPushButton{background:#c02020;color:white;border:none;"
                        "border-radius:6px;padding:6px 16px;font-size:12px;font-weight:bold;}"
                        "QPushButton:hover{background:#e03030;}")
        SUCCESS_STYLE = ("QPushButton{background:#1a8a3a;color:white;border:none;"
                         "border-radius:6px;padding:6px 16px;font-size:12px;font-weight:bold;}"
                         "QPushButton:hover{background:#22aa4a;}")
        del_btn = QPushButton("🗑 מחק אירוע"); del_btn.setStyleSheet(DANGER_STYLE)
        del_btn.clicked.connect(self._del_event)
        save_ev_btn = QPushButton("💾 שמור אירוע"); save_ev_btn.setStyleSheet(SUCCESS_STYLE)
        save_ev_btn.clicked.connect(self._save_event)
        btn_l.addWidget(del_btn); btn_l.addSpacing(8); btn_l.addWidget(save_ev_btn)
        ec_l.addWidget(btn_row)

        ec_l.addStretch()
        scroll.setWidget(edit_inner)
        edit_outer.addWidget(scroll)
        splitter.addWidget(edit_w)
        splitter.setSizes([120, 380])

        self._edit_w = edit_w
        self._edit_w.setVisible(False)
        lay.addWidget(splitter, 1)

        # Bottom save all
        bottom = QWidget(); bl = QHBoxLayout(bottom)
        bl.setContentsMargins(12,8,12,8); bl.addStretch()
        save_all_btn = QPushButton("💾 שמור הכל")
        save_all_btn.setStyleSheet(SUCCESS_STYLE); save_all_btn.setMinimumHeight(36)
        save_all_btn.clicked.connect(self._save)
        bl.addWidget(save_all_btn)
        lay.addWidget(bottom)

    def _refresh_list(self):
        self._events_list.clear()
        for ev in self._events:
            name = ev.get("name","(ללא שם)"); t = ev.get("time","")
            tags = []
            if ev.get("date_from") or ev.get("date_to"):
                tags.append(f"{ev.get('date_from','')}–{ev.get('date_to','')}")
            if ev.get("weekdays"):
                day_names = ["א","ב","ג","ד","ה","ו","ש"]
                tags.append(",".join(day_names[d] for d in sorted(ev["weekdays"])))
            if ev.get("parasha_weeks"):
                tags.append(f"{len(ev['parasha_weeks'])} פרשיות")
            tag_str = f"  [{' | '.join(tags)}]" if tags else ""
            self._events_list.addItem(f"{name}  —  {t}{tag_str}")

    def _on_select(self, row):
        if row < 0 or row >= len(self._events):
            self._edit_w.setVisible(False); return
        self._edit_w.setVisible(True)
        ev = self._events[row]
        self._name_e.setText(ev.get("name",""))
        self._time_e.setText(ev.get("time",""))
        has_dr = bool(ev.get("date_from") or ev.get("date_to"))
        self._dr_cb.setChecked(has_dr)
        self._dr_from.setText(ev.get("date_from",""))
        self._dr_to.setText(ev.get("date_to",""))
        self._dr_from.setEnabled(has_dr); self._dr_to.setEnabled(has_dr)
        wds = ev.get("weekdays",[])
        for day_num, cb in self._day_cbs.items():
            cb.setChecked(day_num in wds)
        has_pw = bool(ev.get("parasha_weeks"))
        self._pw_cb.setChecked(has_pw)
        self._parasha_list.setEnabled(has_pw)
        for i in range(self._parasha_list.count()):
            item = self._parasha_list.item(i)
            item.setSelected(item.text() in ev.get("parasha_weeks",[]))

    def _add_event(self):
        self._events.append({"name":"אירוע חדש","time":"00:00"})
        self._refresh_list()
        self._events_list.setCurrentRow(len(self._events)-1)

    def _del_event(self):
        row = self._events_list.currentRow()
        if 0 <= row < len(self._events):
            self._events.pop(row); self._refresh_list()
            self._edit_w.setVisible(False)

    def _save_event(self):
        row = self._events_list.currentRow()
        if row < 0 or row >= len(self._events): return
        name_val = self._name_e.text().strip()
        time_val = self._time_e.text().strip()
        if not name_val or not time_val:
            QMessageBox.warning(self, "שגיאה", "שם האירוע ושעה הם שדות חובה!"); return
        ev = self._events[row]
        ev["name"] = name_val; ev["time"] = time_val
        if self._dr_cb.isChecked():
            ev["date_from"] = self._dr_from.text().strip()
            ev["date_to"]   = self._dr_to.text().strip()
        else:
            ev.pop("date_from",None); ev.pop("date_to",None)
        wds = [day_num for day_num, cb in self._day_cbs.items() if cb.isChecked()]
        if wds: ev["weekdays"] = sorted(wds)
        else:   ev.pop("weekdays",None)
        if self._pw_cb.isChecked():
            ev["parasha_weeks"] = [self._parasha_list.item(i).text()
                                    for i in range(self._parasha_list.count())
                                    if self._parasha_list.item(i).isSelected()]
        else: ev.pop("parasha_weeks",None)
        self._refresh_list(); self._events_list.setCurrentRow(row)

    def _save(self):
        row = self._events_list.currentRow()
        if row >= 0: self._save_event()
        for p in self.cfg.panels():
            if p.get("id") == self.pc.get("id"):
                p["events"] = self._events
                p["empty_text"] = self.pc.get("empty_text","")
                break
        self.pc["events"] = self._events
        self.cfg.save(); self.saved.emit()


# ── Ad Timed Images Editor ────────────────────────────────────────────────────
class AdTimedContentEditor(_BaseContentEditor):
    """Extended Ad editor that supports per-image time schedules."""

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        name = PANEL_NAMES.get("ad","מודעה")
        lay.addWidget(self._hdr(f"עריכת תמונות: {name} #{self.pc.get('id','—')}", "🖼"))

        inner = QWidget(); il = QVBoxLayout(inner); il.setContentsMargins(16,12,16,16); il.setSpacing(8)

        lbl = QLabel("רשימת תמונות:")
        lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:13px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight); il.addWidget(lbl)

        self._img_list = QListWidget(); self._img_list.setMinimumHeight(140)
        self._img_list.currentRowChanged.connect(self._on_img_select)
        # Load: support both old (str) and new (dict) format
        raw = self.pc.get("images", [])
        self._entries = []
        for e in raw:
            if isinstance(e, str): self._entries.append({"path": e})
            elif isinstance(e, dict): self._entries.append(dict(e))
        self._refresh_img_list()
        il.addWidget(self._img_list)

        btn_row = QWidget(); br = QHBoxLayout(btn_row); br.setContentsMargins(0,0,0,0); br.addStretch()
        for text, slot in [("↓ הורד",self._move_down),("↑ העלה",self._move_up),
                           ("✕ הסר",self._remove_img),("+ הוסף תמונות",self._add_imgs)]:
            b = QPushButton(text)
            b.setObjectName("btn_secondary" if text != "+ הוסף תמונות" else "btn_success")
            b.clicked.connect(slot); br.addWidget(b)
        il.addWidget(btn_row)

        il.addWidget(hline())

        # Per-image schedule editor
        self._sched_grp = QGroupBox("⏰ זמן הצגה לתמונה הנבחרת")
        self._sched_grp.setVisible(False)
        sgl = QVBoxLayout(self._sched_grp); sgl.setSpacing(5)

        always_note = QLabel("ללא הגדרת זמן — התמונה מוצגת תמיד")
        always_note.setStyleSheet("color:#4a8c4a;font-size:11px;")
        always_note.setAlignment(Qt.AlignmentFlag.AlignRight); sgl.addWidget(always_note)

        # Date range
        dr_row = QWidget(); drl = QHBoxLayout(dr_row); drl.setContentsMargins(0,0,0,0); drl.setSpacing(6)
        dr_lbl = QLabel("טווח תאריכים:"); dr_lbl.setStyleSheet("color:#4a5580;font-size:11px;")
        self._img_df = QLineEdit(); self._img_df.setPlaceholderText("מ- YYYY-MM-DD"); self._img_df.setFixedWidth(120)
        self._img_dt = QLineEdit(); self._img_dt.setPlaceholderText("עד YYYY-MM-DD"); self._img_dt.setFixedWidth(120)
        drl.addWidget(self._img_dt); drl.addWidget(self._img_df); drl.addWidget(dr_lbl); drl.addStretch()
        sgl.addWidget(dr_row)

        # Weekdays
        wd_row2 = QWidget(); wdl2 = QHBoxLayout(wd_row2); wdl2.setContentsMargins(0,0,0,0); wdl2.setSpacing(4)
        wd_lbl2 = QLabel("ימים בשבוע:"); wd_lbl2.setStyleSheet("color:#4a5580;font-size:11px;")
        wdl2.addStretch(); wdl2.addWidget(wd_lbl2)
        days_heb = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","ש׳"]
        self._img_wdcbs = []
        for dl in days_heb:
            cb2 = QCheckBox(dl); cb2.setStyleSheet("spacing:3px;"); self._img_wdcbs.append(cb2); wdl2.addWidget(cb2)
        sgl.addWidget(wd_row2)

        # Time range
        tr_row2 = QWidget(); trl2 = QHBoxLayout(tr_row2); trl2.setContentsMargins(0,0,0,0); trl2.setSpacing(6)
        tr_lbl2 = QLabel("טווח שעות:"); tr_lbl2.setStyleSheet("color:#4a5580;font-size:11px;")
        self._img_tf = QLineEdit(); self._img_tf.setPlaceholderText("מ- HH:MM"); self._img_tf.setFixedWidth(90)
        self._img_tt = QLineEdit(); self._img_tt.setPlaceholderText("עד HH:MM"); self._img_tt.setFixedWidth(90)
        trl2.addWidget(self._img_tt); trl2.addWidget(self._img_tf); trl2.addWidget(tr_lbl2); trl2.addStretch()
        sgl.addWidget(tr_row2)

        sav_img_btn = QPushButton("💾 שמור הגדרות תמונה"); sav_img_btn.setObjectName("btn_success")
        sav_img_btn.clicked.connect(self._save_img_sched)
        sgl.addWidget(sav_img_btn)
        il.addWidget(self._sched_grp)

        il.addStretch()
        save_btn = QPushButton("💾 שמור הכל"); save_btn.setObjectName("btn_success")
        save_btn.setMinimumHeight(40); save_btn.clicked.connect(self._save)
        il.addWidget(save_btn)
        lay.addWidget(scroll_wrap(inner), 1)

    def _refresh_img_list(self):
        self._img_list.clear()
        for e in self._entries:
            path = e.get("path","")
            name = os.path.basename(path) if path else "—"
            ext = os.path.splitext(name)[1].lower() if name else ""
            type_icon = {".pdf": "📄", ".mp4": "🎬", ".gif": "🎞"}.get(ext, "🖼")
            sched_parts = []
            if e.get("date_from") or e.get("date_to"):
                sched_parts.append(f"{e.get('date_from','')}→{e.get('date_to','')}")
            wds = e.get("weekdays",[])
            if wds: sched_parts.append("ימים:" + ",".join(str(d) for d in wds))
            if e.get("time_from") or e.get("time_to"):
                sched_parts.append(f"{e.get('time_from','')}–{e.get('time_to','')}")
            suffix = "  ⏰" if sched_parts else ""
            self._img_list.addItem(f"{type_icon} {name}{suffix}")

    def _on_img_select(self, row):
        if row < 0 or row >= len(self._entries):
            self._sched_grp.setVisible(False); return
        e = self._entries[row]
        self._img_df.setText(e.get("date_from",""))
        self._img_dt.setText(e.get("date_to",""))
        self._img_tf.setText(e.get("time_from",""))
        self._img_tt.setText(e.get("time_to",""))
        wds = e.get("weekdays",[])
        for i,cb in enumerate(self._img_wdcbs): cb.setChecked(i in wds)
        self._sched_grp.setVisible(True)

    def _save_img_sched(self):
        row = self._img_list.currentRow()
        if row < 0 or row >= len(self._entries): return
        wds = [i for i,cb in enumerate(self._img_wdcbs) if cb.isChecked()]
        e = self._entries[row]
        e["date_from"] = self._img_df.text().strip()
        e["date_to"]   = self._img_dt.text().strip()
        e["time_from"] = self._img_tf.text().strip()
        e["time_to"]   = self._img_tt.text().strip()
        e["weekdays"]  = wds
        self._refresh_img_list()

    def _add_imgs(self):
        paths, _ = QFileDialog.getOpenFileNames(None,"בחר קבצי מדיה","",
            "מדיה (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.pdf *.mp4);;"
            "תמונות (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;"
            "PDF (*.pdf);;"
            "וידאו (*.mp4);;"
            "הכל (*)")
        for p in paths:
            stored = Config.copy_image_to_store(p)
            self._entries.append({"path": stored})
        self._refresh_img_list()

    def _remove_img(self):
        row = self._img_list.currentRow()
        if row >= 0: self._entries.pop(row); self._refresh_img_list(); self._sched_grp.setVisible(False)

    def _move_up(self):
        row = self._img_list.currentRow()
        if row > 0:
            self._entries[row-1], self._entries[row] = self._entries[row], self._entries[row-1]
            self._refresh_img_list(); self._img_list.setCurrentRow(row-1)

    def _move_down(self):
        row = self._img_list.currentRow()
        if row < len(self._entries)-1:
            self._entries[row], self._entries[row+1] = self._entries[row+1], self._entries[row]
            self._refresh_img_list(); self._img_list.setCurrentRow(row+1)

    def _save(self):
        self.pc["images"] = self._entries
        pid = self.pc.get("id")
        if pid:
            for p in self.cfg.panels():
                if p.get("id") == pid:
                    p["images"] = self._entries; break
        self.cfg.save(); self.saved.emit()


# ── Display Board Editor ──────────────────────────────────────────────────────
class DisplayBoardEditor(QWidget):
    """Editor for a single display board (background + schedule)."""
    saved = pyqtSignal()

    def __init__(self, cfg, board, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.board = board   # dict reference from cfg.display_boards()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setObjectName("card_title")
        hdr.setStyleSheet("#card_title{background:#eef2fc;border-bottom:1px solid #dde8f8;}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(14,10,14,10)
        is_default = self.board.get("id") == "__default__"
        lbl_txt = "🖥  עריכת רקע ראשי (ברירת מחדל)" if is_default else \
                  f"🖥  עריכת לוח תצוגה: {self.board.get('name','')}"
        lbl = QLabel(lbl_txt); lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1b3a7a;")
        save_btn = QPushButton("💾  שמור"); save_btn.setObjectName("btn_success")
        save_btn.setFixedWidth(130); save_btn.clicked.connect(self._save)
        hl.addWidget(save_btn); hl.addStretch(); hl.addWidget(lbl)
        lay.addWidget(hdr)

        content = QWidget()
        cl = QVBoxLayout(content); cl.setContentsMargins(16,12,16,20); cl.setSpacing(10)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Name (not for default)
        if not is_default:
            grp_id = QGroupBox("פרטי הלוח")
            gl = QVBoxLayout(grp_id); gl.setSpacing(6)
            self._name_e = QLineEdit(self.board.get("name",""))
            gl.addWidget(form_row("שם הלוח:", self._name_e))
            self._enabled_cb = QCheckBox()
            self._enabled_cb.setChecked(self.board.get("enabled", True))
            gl.addWidget(form_row("לוח מופעל:", self._enabled_cb, compact=True))
            cl.addWidget(grp_id)
        else:
            self._name_e = None; self._enabled_cb = None

        # Background
        grp_bg = QGroupBox("עיצוב רקע")
        bl = QVBoxLayout(grp_bg); bl.setSpacing(6)
        self._bg_color_btn = color_btn(self.board.get("bg_color","#070714"), self)
        bl.addWidget(form_row("צבע רקע:", self._bg_color_btn, compact=True))

        img_row = QWidget(); ir = QHBoxLayout(img_row); ir.setContentsMargins(0,0,0,0)
        self._bg_img_e = QLineEdit(self.board.get("bg_image",""))
        self._bg_img_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        pick = QPushButton("📂 עיון"); pick.setObjectName("btn_secondary"); pick.setMinimumWidth(72)
        pick.clicked.connect(self._pick_bg)
        clr = QPushButton("✕"); clr.setFixedWidth(30); clr.setObjectName("btn_secondary")
        clr.clicked.connect(self._bg_img_e.clear)
        ir.addWidget(self._bg_img_e); ir.addWidget(pick); ir.addWidget(clr)
        bl.addWidget(form_row("תמונת רקע:", img_row))

        # Sync bg_color enabled state with bg_image field
        def _sync_board_bg(text):
            has_img = bool(text.strip())
            self._bg_color_btn.setEnabled(not has_img)
            self._bg_color_btn.setToolTip("תמונת הרקע מחליפה את צבע המילוי" if has_img else "")
        self._bg_img_e.textChanged.connect(_sync_board_bg)
        _sync_board_bg(self._bg_img_e.text())

        self._stars_cb = QCheckBox(); self._stars_cb.setChecked(self.board.get("show_stars",True))
        bl.addWidget(form_row("הצג כוכבים:", self._stars_cb, compact=True))
        self._grad_cb = QCheckBox(); self._grad_cb.setChecked(self.board.get("gradient",True))
        bl.addWidget(form_row("גרדיאנט:", self._grad_cb, compact=True))
        cl.addWidget(grp_bg)

        # Schedule (not for default board)
        if not is_default:
            grp_s = QGroupBox("⏰  לוח זמנים — מתי לוח תצוגה זה פעיל")
            sl = QVBoxLayout(grp_s); sl.setSpacing(6)
            sched = self.board.get("schedule", {})

            sl.addWidget(QLabel("לוח תצוגה זה יוצג בזמנים המוגדרים ויגבר על לוח ברירת המחדל."))

            self._sch_hours_cb = QCheckBox("הגבל לטווח שעות")
            self._sch_hours_cb.setChecked(sched.get("hours_enabled", False))
            sl.addWidget(self._sch_hours_cb)

            hr_row = QWidget(); hrl = QHBoxLayout(hr_row); hrl.setContentsMargins(20,0,0,0); hrl.setSpacing(8)
            self._sch_hfrom = QSpinBox(); self._sch_hfrom.setRange(0,23)
            self._sch_hfrom.setValue(sched.get("hour_from",8)); self._sch_hfrom.setPrefix("מ- ")
            self._sch_hto = QSpinBox(); self._sch_hto.setRange(0,23)
            self._sch_hto.setValue(sched.get("hour_to",20)); self._sch_hto.setPrefix("עד ")
            hrl.addWidget(self._sch_hfrom); hrl.addWidget(self._sch_hto); hrl.addStretch()
            sl.addWidget(hr_row)

            self._sch_days_cb = QCheckBox("הגבל לימי שבוע")
            self._sch_days_cb.setChecked(sched.get("days_enabled", False))
            sl.addWidget(self._sch_days_cb)

            day_row = QWidget(); drl = QHBoxLayout(day_row); drl.setContentsMargins(20,0,0,0); drl.setSpacing(4)
            days_labels = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","ש׳"]
            active_days = sched.get("active_days", list(range(7)))
            self._sch_day_cbs = []
            for di, dl in enumerate(days_labels):
                dc = QCheckBox(dl); dc.setChecked(di in active_days)
                dc.setStyleSheet("spacing:3px;")
                self._sch_day_cbs.append(dc); drl.addWidget(dc)
            drl.addStretch()
            sl.addWidget(day_row)
            cl.addWidget(grp_s)
        else:
            self._sch_hours_cb = self._sch_days_cb = None
            self._sch_hfrom = self._sch_hto = None
            self._sch_day_cbs = []

        lay.addWidget(scroll_wrap(content))

    def _pick_bg(self):
        p, _ = QFileDialog.getOpenFileName(None,"בחר תמונת רקע","",
            "תמונות (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if p:
            p = Config.copy_image_to_store(p)
            self._bg_img_e.setText(p)

    def _save(self):
        self.board["bg_color"]   = self._bg_color_btn._color
        self.board["bg_image"]   = self._bg_img_e.text().strip()
        self.board["show_stars"] = self._stars_cb.isChecked()
        self.board["gradient"]   = self._grad_cb.isChecked()
        if self._name_e:
            self.board["name"]    = self._name_e.text().strip() or self.board.get("name","")
        if self._enabled_cb:
            self.board["enabled"] = self._enabled_cb.isChecked()
        if self._sch_hours_cb:
            self.board["schedule"] = {
                "hours_enabled": self._sch_hours_cb.isChecked(),
                "hour_from":     self._sch_hfrom.value(),
                "hour_to":       self._sch_hto.value(),
                "days_enabled":  self._sch_days_cb.isChecked(),
                "active_days":   [i for i, cb in enumerate(self._sch_day_cbs) if cb.isChecked()],
            }
        # Save the board to the right place in cfg
        bid = self.board.get("id")
        if bid == "__default__":
            disp = self.cfg.display()
            for k in ("bg_color","bg_image","show_stars","gradient"):
                disp[k] = self.board[k]
        else:
            for b in self.cfg.display_boards():
                if b.get("id") == bid:
                    b.update(self.board); break
        self.cfg.save()
        self.saved.emit()


# ── Panels Tab ───────────────────────────────────────────────────────────────
class PanelsTab(QWidget):
    display_refresh = pyqtSignal()

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(310)
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(10,14,10,10); sl.setSpacing(4)

        # ── Design Themes row ───────────────────────────────────────────────
        themes_row = QWidget()
        trl = QHBoxLayout(themes_row); trl.setContentsMargins(0,2,0,2); trl.setSpacing(4)
        themes_lbl = QLabel("🎨 ערכות עיצוב:"); themes_lbl.setStyleSheet("font-size:11px;font-weight:bold;color:#3a5aaa;")
        trl.addWidget(themes_lbl)
        self._themes_cb = QComboBox()
        self._themes_cb.setToolTip("בחר ערכת עיצוב לטעינה, או הוסף ערכת עיצוב חדשה")
        self._themes_cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._themes_cb.setStyleSheet("font-size:11px;")
        self._themes_cb.activated.connect(self._on_theme_selected)
        trl.addWidget(self._themes_cb, 1)
        theme_del_b = QPushButton("🗑")
        theme_del_b.setFixedSize(26, 26)
        theme_del_b.setToolTip("מחק ערכת עיצוב נבחרת")
        theme_del_b.setStyleSheet("font-size:12px;padding:0;")
        theme_del_b.clicked.connect(self._delete_current_theme)
        trl.addWidget(theme_del_b)
        sl.addWidget(themes_row)

        # ── Active Panels header + preview selector ─────────────────────────
        ttl_row = QWidget(); ttrl = QHBoxLayout(ttl_row)
        ttrl.setContentsMargins(0,2,0,2); ttrl.setSpacing(6)
        ttl = QLabel("לוחות פעילים"); ttl.setObjectName("sidebar_title")
        ttrl.addWidget(ttl)
        ttrl.addStretch()
        prev_lbl = QLabel("תצוגה:"); prev_lbl.setStyleSheet("font-size:10px;color:#4a5580;")
        self._preview_cb = QComboBox()
        self._preview_cb.setFixedWidth(130)
        self._preview_cb.setStyleSheet("font-size:10px;")
        self._preview_cb.setToolTip("בחר איזה לוח תצוגה ראשי להציג עכשיו על המסך")
        self._preview_cb.activated.connect(self._on_preview_change)
        ttrl.addWidget(prev_lbl); ttrl.addWidget(self._preview_cb)
        sl.addWidget(ttl_row)

        # ── Add panel button (single button → popup) + sub label ────────────
        add_row = QWidget(); add_rl = QHBoxLayout(add_row)
        add_rl.setContentsMargins(0,0,0,0); add_rl.setSpacing(6)
        add_panel_btn = QPushButton("➕ הוסף לוח")
        add_panel_btn.setObjectName("btn_secondary")
        add_panel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_panel_btn.setStyleSheet("font-size:11px;padding:3px 10px;")
        add_panel_btn.clicked.connect(self._show_add_panel_popup)
        add_rl.addWidget(add_panel_btn)
        sub = QLabel("לחץ על לוח לעריכה"); sub.setObjectName("sidebar_sub")
        add_rl.addStretch(); add_rl.addWidget(sub)
        sl.addWidget(add_row)

        # Export/Import - compact row
        io_grp = QGroupBox("יצוא / יבוא")
        iol = QHBoxLayout(io_grp); iol.setSpacing(4); iol.setContentsMargins(6,6,6,6)
        exp_b = QPushButton("📤 יצוא"); exp_b.setObjectName("btn_success")
        exp_b.setStyleSheet("font-size:11px;padding:4px 8px;")
        exp_b.clicked.connect(self._export); iol.addWidget(exp_b)
        imp_b = QPushButton("📥 יבוא"); imp_b.setObjectName("btn_secondary")
        imp_b.setStyleSheet("font-size:11px;padding:4px 8px;")
        imp_b.clicked.connect(self._import); iol.addWidget(imp_b)
        sl.addWidget(io_grp)

        # Screen size info
        scr = QApplication.primaryScreen()
        if scr:
            sz = scr.size()
            scr_lbl = QLabel(f"📐 מסך: {sz.width()} × {sz.height()} פיקסל")
            scr_lbl.setStyleSheet(
                "color:#4a5580;font-size:10px;padding:2px 6px;"
                "background:#eef2fc;border-radius:4px;border:1px solid #d0dcf0;"
            )
            scr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sl.addWidget(scr_lbl)

        # Panel list — given maximum vertical space
        sl.addWidget(section_label("רשימת לוחות:"))
        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.currentRowChanged.connect(self._on_select)
        sl.addWidget(self._list, 1)

        del_b = QPushButton("🗑  מחק לוח נבחר"); del_b.setObjectName("btn_danger")
        del_b.clicked.connect(self._del_panel); sl.addWidget(del_b)

        main.addWidget(sidebar)

        # ── Editor area ──
        self._editor_area = QStackedWidget()
        placeholder = QWidget()
        pl = QVBoxLayout(placeholder); pl.addStretch()
        pl_lbl = QLabel("← בחר לוח לעריכה")
        pl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl_lbl.setStyleSheet("color:#7080a0;font-size:15px;")
        pl.addWidget(pl_lbl); pl.addStretch()
        self._editor_area.addWidget(placeholder)
        main.addWidget(self._editor_area, 1)

        self._refresh_preview_cb()
        self._refresh_themes_cb()
        self._refresh_list()

    # ── Display Boards ─────────────────────────────────────────────────────────
    def _refresh_boards_list(self):
        """No standalone boards list anymore — just refresh the preview combobox."""
        self._refresh_preview_cb()

    def _refresh_preview_cb(self):
        self._preview_cb.blockSignals(True)
        self._preview_cb.clear()
        self._preview_cb.addItem("לפי שעון (אוטומטי)", None)
        self._preview_cb.addItem("🖥 רקע ראשי", "__default__")
        for b in self.cfg.display_boards():
            self._preview_cb.addItem(f"🖥 {b.get('name','')}", b["id"])
        self._preview_cb.blockSignals(False)

    def _on_board_select(self, row):
        """No longer used — board selection handled by _on_select via main list."""
        pass

    def _on_board_saved(self):
        self.cfg.sync_to_current_theme()
        self._refresh_preview_cb()
        self._refresh_list()
        self.display_refresh.emit()

    def _add_board(self):
        b = self.cfg.add_display_board()
        self.cfg.sync_to_current_theme()
        self._refresh_preview_cb()
        self._refresh_list()
        # Select new board in the main panel list
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == f"board_{b['id']}":
                self._list.setCurrentRow(i); break

    def _del_board(self):
        """Delete the currently-selected board (called when item is a board in main list)."""
        item = self._list.currentItem()
        if not item: return
        uid = item.data(Qt.ItemDataRole.UserRole)
        if not (isinstance(uid, str) and uid.startswith("board_")): return
        bid = int(uid.split("_", 1)[1])
        reply = QMessageBox.question(self,"מחיקה","למחוק לוח תצוגה זה?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.cfg.del_display_board(bid)
            self.cfg.sync_to_current_theme()
            self._refresh_preview_cb()
            self._refresh_list()
            self._editor_area.setCurrentIndex(0)
            self.display_refresh.emit()

    def _on_preview_change(self, idx):
        bid = self._preview_cb.itemData(idx)
        cmd = {"action": "set_preview_board", "board_id": bid}
        try:
            with open(CFG.parent / "cmd.json", "w", encoding="utf-8") as f:
                json.dump(cmd, f)
        except: pass

    def _set_editor(self, widget):
        while self._editor_area.count() > 1:
            w = self._editor_area.widget(1)
            self._editor_area.removeWidget(w); w.deleteLater()
        self._editor_area.addWidget(widget)
        self._editor_area.setCurrentIndex(1)

    # ── Panel list ─────────────────────────────────────────────────────────────
    def _refresh_list(self):
        self._list.clear()
        # Default background always first
        bg_item = QListWidgetItem("🖥  רקע ראשי ★")
        bg_item.setData(Qt.ItemDataRole.UserRole, "bg_panel")
        bg_item.setForeground(QColor("#2d5ec0"))
        self._list.addItem(bg_item)
        # Additional display boards — shown right after default bg
        for b in self.cfg.display_boards():
            en = "✓" if b.get("enabled",True) else "✗"
            sched = b.get("schedule",{})
            sched_tag = " ⏰" if sched.get("hours_enabled") or sched.get("days_enabled") else ""
            it = QListWidgetItem(f"🖥  {b.get('name','')} #{b['id']}  {en}{sched_tag}")
            it.setData(Qt.ItemDataRole.UserRole, f"board_{b['id']}")
            it.setForeground(QColor("#2d5ec0") if b.get("enabled",True) else QColor("#a0aabb"))
            self._list.addItem(it)
        # Regular panels
        for p in self.cfg.panels():
            ptype = p.get("type","?")
            icon = PANEL_ICONS.get(ptype,"?")
            name = p.get("panel_name","") or PANEL_NAMES.get(ptype,"?")
            st = "✓" if p.get("enabled",True) else "✗"
            lyr = p.get("layer",1)
            popup_tag = " 🔔popup" if p.get("popup_only", False) else ""
            board_id = p.get("board_id","__all__")
            if board_id != "__all__":
                if board_id == "__default__":
                    board_tag = " 🖥ב׳מ"
                else:
                    bobj = self.cfg.get_display_board(board_id)
                    board_tag = f" 🖥{bobj['name'][:4]}" if bobj else f" 🖥#{board_id}"
            else:
                board_tag = ""
            ps = p.get("panel_schedule",{})
            sched_tag = " ⏰" if ps.get("hours_enabled") or ps.get("days_enabled") else ""
            item = QListWidgetItem(
                f"{icon}  {name} #{p['id']}  |  שכ׳{lyr}  {st}{popup_tag}{board_tag}{sched_tag}")
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            if not p.get("enabled",True):
                item.setForeground(QColor("#a0aabb"))
            elif p.get("popup_only", False):
                item.setForeground(QColor("#c07000"))
            self._list.addItem(item)

    def _on_select(self, row):
        if row < 0: return
        item = self._list.item(row)
        if not item: return
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid == "bg_panel":
            pc = dict(self.cfg.display()); pc["type"] = "background"; pc["id"] = "★"
            self._open_editor(pc)
        elif isinstance(uid, str) and uid.startswith("board_"):
            bid = int(uid.split("_",1)[1])
            board = self.cfg.get_display_board(bid)
            if board:
                ed = DisplayBoardEditor(self.cfg, board, self)
                ed.saved.connect(self._on_board_saved)
                self._set_editor(ed)
        else:
            pc = self.cfg.get_panel(uid)
            if pc: self._open_editor(pc)

    def _open_editor(self, pc):
        ed = PanelEditor(self.cfg, pc, self)
        ed.saved.connect(self._on_saved)
        self._set_editor(ed)

    def _on_saved(self):
        self.cfg.sync_to_current_theme()
        self._refresh_list()
        self.display_refresh.emit()

    def _add_panel(self, ptype):
        p = self.cfg.add_panel(ptype)
        self.cfg.sync_to_current_theme()
        self._refresh_list()
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == p["id"]:
                self._list.setCurrentRow(i); break
        self.display_refresh.emit()

    def _del_panel(self):
        row = self._list.currentRow()
        if row < 0: return
        item = self._list.item(row)
        uid = item.data(Qt.ItemDataRole.UserRole)
        # Board item — delegate to _del_board
        if isinstance(uid, str) and uid.startswith("board_"):
            self._del_board(); return
        if uid in ("bg_panel",):
            QMessageBox.information(self,"מידע","לוח זה הוא קבוע ולא ניתן למחיקה"); return
        reply = QMessageBox.question(self,"מחיקה","למחוק את הלוח הנבחר?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.cfg.del_panel(uid)
            self.cfg.sync_to_current_theme()
            self._refresh_list()
            self._editor_area.setCurrentIndex(0)
            self.display_refresh.emit()

    # ── Add Panel Popup ────────────────────────────────────────────────────────
    def _show_add_panel_popup(self):
        """Show a small popup dialog with all panel type buttons."""
        popup = QDialog(self)
        popup.setWindowTitle("הוסף לוח")
        popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setStyleSheet(
            "QDialog{background:#f4f7ff;border:1px solid #b0c4e8;border-radius:8px;}"
            "QPushButton{font-size:11px;padding:4px 8px;text-align:right;}"
        )
        vl = QVBoxLayout(popup); vl.setContentsMargins(8,8,8,8); vl.setSpacing(3)
        hdr = QLabel("בחר סוג לוח להוספה:")
        hdr.setStyleSheet("font-size:11px;font-weight:bold;color:#3a5aaa;padding-bottom:4px;")
        vl.addWidget(hdr)

        add_items = [(pt, lbl) for pt, lbl in PANEL_NAMES.items()
                     if pt not in ("background", "fullscreen_msg")]
        for pt, lbl in add_items:
            b = QPushButton(f"{PANEL_ICONS[pt]}  {lbl}")
            b.setObjectName("btn_secondary")
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.clicked.connect(lambda checked=False, t=pt, dlg=popup: (dlg.accept(), self._add_panel(t)))
            vl.addWidget(b)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#c0d0e8;"); vl.addWidget(sep)

        board_btn = QPushButton("🖥  לוח תצוגה ראשי")
        board_btn.setObjectName("btn_secondary")
        board_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        board_btn.clicked.connect(lambda _=None, dlg=popup: (dlg.accept(), self._add_board()))
        vl.addWidget(board_btn)

        # Position popup below the "הוסף לוח" button
        sender_btn = self.sender()
        if sender_btn:
            gpos = sender_btn.mapToGlobal(QPoint(0, sender_btn.height()))
            popup.move(gpos)
        popup.exec()

    # ── Design Themes ──────────────────────────────────────────────────────────
    def _refresh_themes_cb(self):
        cb = self._themes_cb
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("── הוסף ערכת עיצוב ──", "__add__")
        current_tid = self.cfg.current_theme_id()
        sel_idx = 0
        for i, t in enumerate(self.cfg.design_themes()):
            cb.addItem(t.get("name", f"ערכה {t['id']}"), t["id"])
            if t["id"] == current_tid:
                sel_idx = i + 1  # +1 for "הוסף" item
        cb.setCurrentIndex(sel_idx)
        cb.blockSignals(False)

    def _on_theme_selected(self, idx):
        tid = self._themes_cb.currentData()
        if tid == "__add__":
            self._themes_cb.blockSignals(True)
            self._refresh_themes_cb()
            self._themes_cb.blockSignals(False)
            self._add_design_theme()
            return
        if tid is None:
            return
        # Don't ask if already on this theme
        if tid == self.cfg.current_theme_id():
            self._refresh_themes_cb()
            return
        theme_name = self._themes_cb.currentText()
        reply = QMessageBox.question(self, "החלפת ערכת עיצוב",
            f"לעבור לערכת העיצוב \"{theme_name}\"?\n"
            "הגדרות העיצוב הנוכחיות יישמרו אוטומטית לערכה הנוכחית.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.cfg.load_design_theme(tid)
            self._refresh_themes_cb()
            self._refresh_preview_cb()
            self._refresh_list()
            self._editor_area.setCurrentIndex(0)
            self.display_refresh.emit()
        else:
            self._refresh_themes_cb()

    def _add_design_theme(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("הוסף ערכת עיצוב")
        dlg.setMinimumWidth(300)
        vl = QVBoxLayout(dlg); vl.setSpacing(10); vl.setContentsMargins(16,16,16,16)
        lbl = QLabel("שם ערכת העיצוב:")
        lbl.setStyleSheet("font-weight:bold;")
        vl.addWidget(lbl)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("לדוגמה: ערכת שבת, ערכת חגים...")
        name_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        vl.addWidget(name_edit)
        info = QLabel("ערכה חדשה תיפתח ריקה — ללא לוחות, עם עיצוב רקע ברירת מחדל.")
        info.setStyleSheet("font-size:10px;color:#6070a0;")
        vl.addWidget(info)
        btn_row = QWidget(); brl = QHBoxLayout(btn_row); brl.setContentsMargins(0,0,0,0)
        save_b = QPushButton("💾 שמור"); save_b.setObjectName("btn_success")
        cancel_b = QPushButton("ביטול"); cancel_b.setObjectName("btn_secondary")
        brl.addStretch(); brl.addWidget(cancel_b); brl.addWidget(save_b)
        vl.addWidget(btn_row)
        save_b.clicked.connect(dlg.accept)
        cancel_b.clicked.connect(dlg.reject)
        name_edit.returnPressed.connect(dlg.accept)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                name = f"ערכה {len(self.cfg.design_themes()) + 1}"
            self.cfg.add_design_theme(name)
            self._refresh_themes_cb()
            self._refresh_list()
            self._editor_area.setCurrentIndex(0)
            self.display_refresh.emit()

    def _delete_current_theme(self):
        tid = self._themes_cb.currentData()
        if tid in (None, "__add__"):
            QMessageBox.information(self, "מידע", "לא נבחרה ערכת עיצוב למחיקה.")
            return
        name = self._themes_cb.currentText()
        reply = QMessageBox.question(self, "מחיקת ערכת עיצוב",
            f"למחוק את ערכת העיצוב \"{name}\"?\nפעולה זו אינה ניתנת לביטול.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.cfg.delete_design_theme(tid)
            self._refresh_themes_cb()

    def _export(self):
        self.cfg.sync_to_current_theme()
        tid = self.cfg.current_theme_id()
        theme_label = ""
        if tid is not None:
            t = self.cfg.get_design_theme(tid)
            if t: theme_label = f" — {t.get('name','')}"
        path, _ = QFileDialog.getSaveFileName(self, f"יצוא ערכת עיצוב{theme_label}", "ערכת-עיצוב.zip",
            "ערכת עיצוב (*.zip);;Digital Bulletin Layout (*.dbzip)")
        if not path: return
        try:
            n, exported_name = self.cfg.export_layout(path)
            name_txt = f' "{exported_name}"' if exported_name else ""
            QMessageBox.information(self, "יצוא הושלם",
                f"ערכת העיצוב{name_txt} יוצאה בהצלחה\nתמונות עיצוב שנכללו: {n}")
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _import(self):
        # Determine target: current theme id, or None (= add as new)
        tid = self.cfg.current_theme_id()
        theme_name = ""
        target_id = None
        if tid is not None:
            t = self.cfg.get_design_theme(tid)
            if t:
                theme_name = t.get("name", "")
                target_id = tid
        path, _ = QFileDialog.getOpenFileName(self, "יבוא ערכת עיצוב", "",
            "ערכת עיצוב (*.zip *.dbzip)")
        if not path: return
        if target_id is not None:
            msg = (f"יבוא ערכת העיצוב ידרוס את ערכת העיצוב הנוכחית \"{theme_name}\".\n"
                   "העיצוב הנוכחי יוחלף. האם להמשיך?")
        else:
            msg = "לא נבחרה ערכת עיצוב — הקובץ יתווסף כערכת עיצוב חדשה בשם 'ערכת עיצוב חדשה'.\nהאם להמשיך?"
        reply = QMessageBox.question(self, "אישור יבוא", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            report = self.cfg.import_layout(path, target_theme_id=target_id)
            self._show_theme_import_report(report)
            self._refresh_themes_cb()
            self._refresh_list()
            self._editor_area.setCurrentIndex(0)
            self.display_refresh.emit()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _show_theme_import_report(self, report):
        panels    = report.get("panels", [])
        n_imgs    = report.get("n_imgs", 0)
        t_name    = report.get("theme_name", "")
        is_new    = report.get("is_new", False)
        lines = ["✅  ערכת העיצוב יובאה בהצלחה!", ""]
        if t_name:
            action = "נוצרה ערכה חדשה" if is_new else "עודכנה ערכה קיימת"
            lines.append(f"{action}: \"{t_name}\"")
        lines.append(f"תמונות שיובאו: {n_imgs}")
        lines.append("")
        if panels:
            lines.append("לוחות שיובאו:")
            for pn in panels:
                lines.append(f"  • {pn}")
        else:
            lines.append("לא נמצאו לוחות בקובץ.")
        msg = "\n".join(lines)
        dlg = _ImportReportDialog("דוח יבוא ערכת עיצוב", msg, self)
        dlg.exec()

# ── Location Tab ─────────────────────────────────────────────────────────────
class LocationTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0,0,0,0)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        loc = self.cfg.location()

        # ── 1. Zmanim calculation method card — FIRST ────────────────────────
        zmethod_card, zml = card("⚙  שיטת חישוב זמני הלכה")
        zm_body = QWidget(); zmb = QVBoxLayout(zm_body); zmb.setContentsMargins(12,8,12,12)
        zm_desc = QLabel(
            "KosherZmanim (zmanim) — ספריית KosherJava המתורגמת לפייתון, הדייקנית ביותר (מומלץ)    "
            "Astral / pytz — חישוב מובנה, מדויק פחות"
        )
        zm_desc.setStyleSheet("color:#4a5580;font-size:11px;")
        zm_desc.setWordWrap(True); zmb.addWidget(zm_desc)
        zm_row = QWidget(); zmr = QHBoxLayout(zm_row); zmr.setContentsMargins(0,6,0,0); zmr.addStretch()
        cur_method = loc.get("zmanim_method", "kosherzmanim")
        self._zmethod_cb = QComboBox()
        self._zmethod_cb.addItem("KosherZmanim (zmanim) — מדויק ביותר", "kosherzmanim")
        self._zmethod_cb.addItem("Astral / pytz — מובנה", "astral")
        for i in range(self._zmethod_cb.count()):
            if self._zmethod_cb.itemData(i) == cur_method:
                self._zmethod_cb.setCurrentIndex(i); break
        zm_lbl = QLabel("שיטת חישוב:"); zm_lbl.setStyleSheet("color:#1b3a7a;font-weight:bold;font-size:12px;")
        zmr.addWidget(self._zmethod_cb); zmr.addWidget(zm_lbl)
        zmb.addWidget(zm_row)
        zml.addWidget(zm_body); lay.addWidget(zmethod_card)

        # ── 1b. Zmanim keys configuration ────────────────────────────────────
        zkeys_card, zkl = card("📋  ניהול זמני הלכה — שמות ושיטות חישוב")
        zk_body = QWidget(); zkb = QVBoxLayout(zk_body)
        zkb.setContentsMargins(10, 6, 10, 10); zkb.setSpacing(6)

        hint_lbl = QLabel("לחץ על שם זמן לעריכת שם אישי ושיטת חישוב ייחודית. ניתן להוסיף זמן כפול בכל שיטה.")
        hint_lbl.setStyleSheet("color:#4a5580;font-size:11px;")
        hint_lbl.setWordWrap(True)
        zkb.addWidget(hint_lbl)

        # Grid container for zmanim buttons — 3 per row
        self._zkeys_grid_w = QWidget()
        self._zkeys_grid = QGridLayout(self._zkeys_grid_w)
        self._zkeys_grid.setSpacing(5)
        self._zkeys_grid.setContentsMargins(0, 4, 0, 4)
        zkb.addWidget(self._zkeys_grid_w)

        # "Add zmanim" button
        add_zman_btn = QPushButton("➕  הוסף זמן")
        add_zman_btn.setObjectName("btn_primary")
        add_zman_btn.setFixedWidth(130)
        add_row = QWidget(); ar = QHBoxLayout(add_row); ar.setContentsMargins(0,0,0,0); ar.addStretch()
        ar.addWidget(add_zman_btn)
        zkb.addWidget(add_row)

        zkl.addWidget(zk_body); lay.addWidget(zkeys_card)

        self._rebuild_zkeys_grid()
        add_zman_btn.clicked.connect(self._add_zmanim_entry)
        fields_card, fl = card("📍  פרטי מיקום מדויקים")
        self._fields = {}

        # City selector row (replaces the old "שם מיקום" text field)
        city_body = QWidget(); cbl = QVBoxLayout(city_body)
        cbl.setContentsMargins(12, 8, 12, 4); cbl.setSpacing(4)
        city_lbl_title = QLabel("בחר עיר:")
        city_lbl_title.setStyleSheet("color:#4a5580;font-size:11px;font-weight:bold;")
        city_lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        city_cb = QComboBox()
        city_cb.addItem("— בחר עיר —")
        city_cb.addItems(sorted(CITIES.keys()))
        city_cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Set current city if it matches a known city
        cur_city = loc.get("city", "")
        for i in range(city_cb.count()):
            if city_cb.itemText(i) == cur_city:
                city_cb.setCurrentIndex(i); break
        city_hint = QLabel("(בחירת עיר מעדכנת את שדות הקואורדינטות אוטומטית)")
        city_hint.setStyleSheet("color:#8090b0;font-size:10px;")
        city_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        cbl.addWidget(city_lbl_title)
        cbl.addWidget(city_cb)
        cbl.addWidget(city_hint)
        fl.addWidget(city_body)

        fl.addWidget(hline())

        # Compact coordinate fields — all in ONE row, label above each field
        # Fields: Lat (6 chars), Lng (6 chars), Elev (6 chars), TZ (14 chars)
        coords_row = QWidget()
        crl = QHBoxLayout(coords_row)
        crl.setContentsMargins(12, 4, 12, 10)
        crl.setSpacing(12)
        crl.setAlignment(Qt.AlignmentFlag.AlignRight)

        coord_fields = [
            ("אזור זמן", "tz",   "Asia/Jerusalem", 220),
            ("גובה (מ׳)", "elev", "754",            116),
            ("קו אורך",   "lng",  "35.2137",        116),
            ("קו רוחב",   "lat",  "31.7683",        116),
        ]
        for label, key, default, w in coord_fields:
            col = QWidget(); col_l = QVBoxLayout(col)
            col_l.setContentsMargins(0,0,0,0); col_l.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#4a5580;font-size:10px;font-weight:bold;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            e = QLineEdit(str(loc.get(key, default)))
            e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            e.setFixedWidth(w)
            self._fields[key] = e
            col_l.addWidget(lbl); col_l.addWidget(e)
            crl.addWidget(col)

        fl.addWidget(coords_row)
        lay.addWidget(fields_card)

        def on_city(idx):
            if idx < 1: return
            city = city_cb.currentText()
            if city in CITIES:
                lat, lng, elev, tz = CITIES[city]
                self._fields["lat"].setText(str(lat))
                self._fields["lng"].setText(str(lng))
                self._fields["elev"].setText(str(elev))
                self._fields["tz"].setText(tz)
        city_cb.currentIndexChanged.connect(on_city)
        self._city_cb = city_cb  # keep reference for _save

        # Add Hebrew day switch option
        hday_card, hdcl = card("🌅  מעבר יום עברי")

        hd_body = QWidget(); hdb = QVBoxLayout(hd_body); hdb.setContentsMargins(12,8,12,10)
        hd_desc = QLabel("מתי מתחיל היום העברי (ומתי מתעדכנים זמני ההלכה)?")
        hd_desc.setStyleSheet("color:#4a5580;font-size:11px;"); hdb.addWidget(hd_desc)
        hd_row = QWidget(); hdr2 = QHBoxLayout(hd_row); hdr2.setContentsMargins(0,4,0,0); hdr2.addStretch()
        self._hday_sunset = QRadioButton("בשקיעה (ברירת מחדל — כהלכה)")
        self._hday_midnight = QRadioButton("בחצות לילה (00:00)")
        cur_switch = self.cfg.d.get("time_settings", {}).get("hebrew_day_switch", "sunset")
        self._hday_sunset.setChecked(cur_switch == "sunset")
        self._hday_midnight.setChecked(cur_switch == "midnight")
        hdr2.addWidget(self._hday_midnight); hdr2.addSpacing(12); hdr2.addWidget(self._hday_sunset)
        hdb.addWidget(hd_row)
        hdcl.addWidget(hd_body); lay.addWidget(hday_card)

        # Save button only
        # Manual date/time override
        manual_card, ml = card("🕐  תאריך ושעה")
        man_body = QWidget(); man_l = QVBoxLayout(man_body); man_l.setContentsMargins(12,8,12,10)
        ts_cfg = self.cfg.d.get("time_settings", {})
        man_desc = QLabel("ברירת מחדל: תאריך ושעה לפי שעון המחשב (מומלץ). ניתן להגדיר תאריך ושעה ידנית למטרות תצוגה.")
        man_desc.setStyleSheet("color:#4a5580;font-size:11px;"); man_desc.setWordWrap(True)
        man_l.addWidget(man_desc)
        man_row = QWidget(); mr = QHBoxLayout(man_row); mr.setContentsMargins(0,4,0,0); mr.addStretch()
        self._manual_enabled = QCheckBox("הגדרה ידנית של תאריך ושעה")
        self._manual_enabled.setChecked(ts_cfg.get("manual_time_enabled", False))
        mr.addWidget(self._manual_enabled); man_l.addWidget(man_row)
        # Fields for manual date/time (shown when checked)
        self._manual_fields_w = QWidget()
        mf_form = QFormLayout(self._manual_fields_w)
        mf_form.setContentsMargins(0,4,0,0); mf_form.setSpacing(8)
        mf_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._manual_date_e = QLineEdit(ts_cfg.get("manual_date", ""))
        self._manual_date_e.setPlaceholderText("YYYY-MM-DD"); self._manual_date_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._manual_date_e.setMaximumWidth(160)
        self._manual_time_e = QLineEdit(ts_cfg.get("manual_time_str", ""))
        self._manual_time_e.setPlaceholderText("HH:MM:SS"); self._manual_time_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._manual_time_e.setMaximumWidth(160)
        mf_form.addRow("תאריך (YYYY-MM-DD):", self._manual_date_e)
        mf_form.addRow("שעה (HH:MM:SS):", self._manual_time_e)
        man_l.addWidget(self._manual_fields_w)
        self._manual_fields_w.setVisible(self._manual_enabled.isChecked())
        self._manual_enabled.toggled.connect(self._manual_fields_w.setVisible)
        ml.addWidget(man_body)
        lay.addWidget(manual_card)

        btn_row = QWidget(); br = QHBoxLayout(btn_row)
        br.setContentsMargins(0,4,0,0); br.addStretch()
        save_b = QPushButton("💾  שמור הגדרות מיקום"); save_b.setObjectName("btn_success")
        save_b.clicked.connect(self._save); br.addWidget(save_b)
        lay.addWidget(btn_row)

        main_lay.addWidget(scroll_wrap(content))

    def _rebuild_zkeys_grid(self):
        """Rebuild the grid of zmanim key buttons from current config."""
        while self._zkeys_grid.count():
            item = self._zkeys_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        entries = self.cfg.zmanim_keys_cfg()
        COLS = 3
        for idx, entry in enumerate(entries):
            key = entry.get("key","")
            custom = entry.get("custom_name","").strip()
            method = entry.get("method","")
            base_name = ZMANIM_KEYS.get(key, key)
            display = custom if custom else base_name
            if method == "kosherzmanim": badge = " [K]"
            elif method == "astral":     badge = " [A]"
            else:                        badge = ""
            uid = entry.get("uid","")
            is_dup = uid.startswith("dup_")
            btn = QPushButton(display + badge)
            btn.setToolTip(f"זמן: {base_name}\nלחץ לעריכה")
            base_style = ("QPushButton{border:1px solid #4a7ae0;border-radius:5px;"
                          "padding:4px 8px;font-size:11px;text-align:right;}"
                          "QPushButton:hover{background:#c8d8f8;}")
            if is_dup:
                btn.setStyleSheet(base_style + "QPushButton{background:#fff3e0;color:#7a4000;border-color:#f5a623;}")
            else:
                btn.setStyleSheet(base_style + "QPushButton{background:#e8f0fe;color:#1b3a7a;}")
            btn.clicked.connect(lambda checked=False, u=uid: self._edit_zmanim_entry(u))
            row, col = divmod(idx, COLS)
            self._zkeys_grid.addWidget(btn, row, col)

    def _edit_zmanim_entry(self, uid):
        entries = self.cfg.zmanim_keys_cfg()
        entry = next((e for e in entries if e.get("uid") == uid), None)
        if entry is None: return
        key = entry.get("key","")
        base_name = ZMANIM_KEYS.get(key, key)
        global_method = self.cfg.location().get("zmanim_method","kosherzmanim")
        global_label = "KosherZmanim" if global_method == "kosherzmanim" else "Astral"
        dlg = QDialog(self); dlg.setWindowTitle(f"עריכת זמן: {base_name}")
        dlg.setMinimumWidth(340); dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        vl = QVBoxLayout(dlg); vl.setSpacing(10)
        vl.addWidget(QLabel(f"<b>{base_name}</b>"))
        vl.addWidget(QLabel("שם אישי (ריק = שם ברירת מחדל):"))
        name_edit = QLineEdit(entry.get("custom_name",""))
        name_edit.setPlaceholderText(base_name)
        name_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft); vl.addWidget(name_edit)
        vl.addWidget(QLabel("<b>שיטת חישוב לזמן זה:</b>"))
        method_cb = QComboBox()
        method_cb.addItem(f"ברירת מחדל ({global_label})", "")
        method_cb.addItem("KosherZmanim — מדויק ביותר", "kosherzmanim")
        method_cb.addItem("Astral / pytz — מובנה", "astral")
        cur = entry.get("method","")
        for i in range(method_cb.count()):
            if method_cb.itemData(i) == cur: method_cb.setCurrentIndex(i); break
        vl.addWidget(method_cb)
        is_removable = uid.startswith("dup_")
        if is_removable:
            rem_btn = QPushButton("🗑  הסר זמן זה"); rem_btn.setStyleSheet("color:#cc2a2a;")
            vl.addWidget(rem_btn)
            def _remove():
                self.cfg.location()["zmanim_keys_cfg"] = [e for e in self.cfg.zmanim_keys_cfg() if e.get("uid") != uid]
                self.cfg.save(); dlg.reject(); self._rebuild_zkeys_grid()
            rem_btn.clicked.connect(_remove)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        vl.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            entry["custom_name"] = name_edit.text().strip()
            entry["method"] = method_cb.currentData()
            self.cfg.save(); self._rebuild_zkeys_grid()

    def _add_zmanim_entry(self):
        global_method = self.cfg.location().get("zmanim_method","kosherzmanim")
        global_label = "KosherZmanim" if global_method == "kosherzmanim" else "Astral"
        dlg = QDialog(self); dlg.setWindowTitle("הוספת זמן הלכה")
        dlg.setMinimumWidth(360); dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        vl = QVBoxLayout(dlg); vl.setSpacing(10)
        vl.addWidget(QLabel("<b>סוג הזמן:</b>"))
        key_cb = QComboBox()
        for k, v in ZMANIM_KEYS.items(): key_cb.addItem(v, k)
        vl.addWidget(key_cb)
        vl.addWidget(QLabel("שם אישי (ריק = שם ברירת מחדל):"))
        name_edit = QLineEdit(); name_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        def _ph(idx): name_edit.setPlaceholderText(key_cb.currentText())
        key_cb.currentIndexChanged.connect(_ph); _ph(0)
        vl.addWidget(name_edit)
        vl.addWidget(QLabel("<b>שיטת חישוב:</b>"))
        method_cb = QComboBox()
        method_cb.addItem(f"ברירת מחדל ({global_label})", "")
        method_cb.addItem("KosherZmanim — מדויק ביותר", "kosherzmanim")
        method_cb.addItem("Astral / pytz — מובנה", "astral")
        vl.addWidget(method_cb)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject); vl.addWidget(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        chosen_key = key_cb.currentData()
        import time as _time
        uid = f"dup_{chosen_key}_{int(_time.time()*1000) % 100000}"
        new_entry = {"uid": uid, "key": chosen_key,
                     "custom_name": name_edit.text().strip(), "method": method_cb.currentData()}
        entries = self.cfg.zmanim_keys_cfg()
        insert_pos = len(entries)
        for i, e in enumerate(entries):
            if e.get("key") == chosen_key: insert_pos = i + 1
        entries.insert(insert_pos, new_entry)
        self.cfg.location()["zmanim_keys_cfg"] = entries
        self.cfg.save(); self._rebuild_zkeys_grid()

    def _save(self):
        # Save city from city combobox
        if hasattr(self, "_city_cb") and self._city_cb.currentIndex() > 0:
            self.cfg.location()["city"] = self._city_cb.currentText()
        # Save coordinate fields (lat, lng, elev, tz)
        for key, e in self._fields.items():
            v = e.text().strip()
            if key in ("lat","lng","elev"):
                try: self.cfg.location()[key] = float(v)
                except: pass
            else: self.cfg.location()[key] = v
        # Save zmanim calculation method
        if hasattr(self, "_zmethod_cb"):
            self.cfg.location()["zmanim_method"] = self._zmethod_cb.currentData()
        # Save Hebrew day switch
        ts = self.cfg.d.setdefault("time_settings", {})
        ts["hebrew_day_switch"] = "sunset" if self._hday_sunset.isChecked() else "midnight"
        # Save manual date/time override
        ts["manual_time_enabled"] = self._manual_enabled.isChecked()
        if self._manual_enabled.isChecked():
            d_str = self._manual_date_e.text().strip()
            t_str = self._manual_time_e.text().strip() or "00:00:00"
            ts["manual_date"] = d_str
            ts["manual_time_str"] = t_str
            try:
                from datetime import datetime as _dt
                combined = f"{d_str} {t_str}"
                _dt.strptime(combined, "%Y-%m-%d %H:%M:%S")
                ts["manual_datetime"] = combined
            except:
                QMessageBox.warning(self, "שגיאה", "פורמט תאריך/שעה שגוי. השתמש ב-YYYY-MM-DD ו-HH:MM:SS")
                return
        self.cfg.save()
        # Signal tkinter display to refresh (reloads ZmanimCalc with new method/location)
        try:
            sig = CFG.parent / "refresh_signal"
            sig.touch()
        except: pass
        QMessageBox.information(self, "הצלחה", "הגדרות הזמן והמיקום נשמרו!")

# ── Security Tab ─────────────────────────────────────────────────────────────
class SecurityTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        outer = QVBoxLayout(self); outer.addStretch()
        inner = QWidget(); inner.setFixedWidth(420)
        inner.setObjectName("card")
        lay = QVBoxLayout(inner); lay.setContentsMargins(24,24,24,24); lay.setSpacing(16)

        title = QLabel("🔐  הגדרות אבטחה")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#1b3a7a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(title)
        lay.addWidget(hline())

        self._status_lbl = QLabel()
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_status(); lay.addWidget(self._status_lbl)
        lay.addWidget(hline())

        info = QLabel("הסיסמא נדרשת לפתיחת ממשק הניהול (F8)")
        info.setStyleSheet("color:#6070a0;font-size:11px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(info)

        btn_row = QWidget(); br = QHBoxLayout(btn_row); br.setContentsMargins(0,0,0,0)
        set_b = QPushButton("🔑  שנה / הגדר סיסמא"); set_b.clicked.connect(self._set_pw)
        del_b = QPushButton("🗑  מחק סיסמא"); del_b.setObjectName("btn_danger")
        del_b.clicked.connect(self._del_pw)
        br.addWidget(set_b); br.addWidget(del_b)
        lay.addWidget(btn_row)

        center = QHBoxLayout(); center.addStretch(); center.addWidget(inner); center.addStretch()
        outer.addLayout(center); outer.addStretch()

    def _update_status(self):
        has = self.cfg.has_pw()
        self._status_lbl.setText("✓  סיסמא מוגדרת" if has else "✗  אין סיסמא")
        self._status_lbl.setStyleSheet(
            f"font-size:16px;font-weight:bold;color:{'#1a9a5c' if has else '#a0aabb'};")

    def _set_pw(self):
        pw, ok = QInputDialog.getText(self,"סיסמא חדשה","הזן סיסמא חדשה:",QLineEdit.EchoMode.Password)
        if not ok: return
        if pw:
            pw2, ok2 = QInputDialog.getText(self,"אימות","הזן שוב:",QLineEdit.EchoMode.Password)
            if not ok2: return
            if pw != pw2: QMessageBox.warning(self,"שגיאה","הסיסמאות אינן תואמות"); return
        self.cfg.set_pw(pw); self._update_status()
        QMessageBox.information(self,"הצלחה","הסיסמא עודכנה")

    def _del_pw(self):
        if self.cfg.has_pw():
            pw, ok = QInputDialog.getText(self,"אימות","הזן את הסיסמא הנוכחית:",QLineEdit.EchoMode.Password)
            if not ok: return
            if not self.cfg.check_pw(pw): QMessageBox.warning(self,"שגיאה","סיסמא שגויה"); return
        self.cfg.set_pw("")
        self._update_status()
        QMessageBox.information(self,"הצלחה","הסיסמא נמחקה")

# ── Reminders Tab ────────────────────────────────────────────────────────────
class RemindersTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # ── Left: list ──
        left = QWidget(); left.setObjectName("sidebar"); left.setFixedWidth(300)
        ll = QVBoxLayout(left); ll.setContentsMargins(10,14,10,10); ll.setSpacing(6)

        ttl = QLabel("🔔  תזכורות"); ttl.setObjectName("sidebar_title"); ll.addWidget(ttl)
        sub = QLabel("אישיות ולפי זמני הלכה"); sub.setObjectName("sidebar_sub"); ll.addWidget(sub)

        self._list = QListWidget(); self._list.setMinimumHeight(200); ll.addWidget(self._list, 1)

        del_b = QPushButton("🗑  מחק"); del_b.setObjectName("btn_danger")
        del_b.clicked.connect(self._del); ll.addWidget(del_b)
        rst_b = QPushButton("↺  הפעל מחדש"); rst_b.setObjectName("btn_secondary")
        rst_b.clicked.connect(self._reset); ll.addWidget(rst_b)
        main.addWidget(left)

        # ── Right: form ──
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0,0,0,0); right_lay.setSpacing(0)

        form_widget = QWidget()
        fl = QVBoxLayout(form_widget)
        fl.setContentsMargins(20,16,20,20); fl.setSpacing(12)
        fl.setAlignment(Qt.AlignmentFlag.AlignTop)

        fl.addWidget(section_label("הוסף תזכורת"))
        fl.addWidget(hline())

        # Type selector
        type_grp = QGroupBox("סוג תזכורת")
        tgl = QHBoxLayout(type_grp); tgl.addStretch()
        self._type_personal = QRadioButton("📅  תזכורת אישית")
        self._type_zmanim   = QRadioButton("🕍  זמן הלכה")
        self._type_personal.setChecked(True)
        tgl.addWidget(self._type_zmanim); tgl.addSpacing(16); tgl.addWidget(self._type_personal)
        fl.addWidget(type_grp)

        # Text
        txt_grp = QGroupBox("תוכן ההודעה")
        tl = QVBoxLayout(txt_grp)
        self._text_e = QLineEdit(); self._text_e.setPlaceholderText("כתוב כאן את ההודעה...")
        tl.addWidget(self._text_e)
        fl.addWidget(txt_grp)

        # Personal date/time (shown only for personal type)
        self._personal_grp = QGroupBox("מועד (תזכורת אישית)")
        pg = QFormLayout(self._personal_grp)
        pg.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        now = datetime.now()
        self._date_e = QLineEdit(now.strftime("%Y-%m-%d"))
        self._time_e = QLineEdit(now.strftime("%H:%M"))
        self._date_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._time_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        pg.addRow("תאריך (YYYY-MM-DD):", self._date_e)
        pg.addRow("שעה (HH:MM):", self._time_e)
        fl.addWidget(self._personal_grp)

        # Zmanim (shown only for zmanim type, hidden initially)
        self._zmanim_grp = QGroupBox("זמן הלכה")
        zg = QFormLayout(self._zmanim_grp)
        zg.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._zman_cb = QComboBox()
        eff_list = get_effective_zmanim_list(self.cfg.d)
        for uid, key, name in eff_list: self._zman_cb.addItem(name, uid)
        # Default to sunset
        for i in range(self._zman_cb.count()):
            if self._zman_cb.itemData(i) == "sunset": self._zman_cb.setCurrentIndex(i); break
        self._offset_spin = QSpinBox(); self._offset_spin.setRange(-120,120); self._offset_spin.setValue(-15)
        zg.addRow("זמן:", self._zman_cb)
        zg.addRow("דקות לפני (שלילי) / אחרי:", self._offset_spin)
        self._zmanim_grp.hide()
        fl.addWidget(self._zmanim_grp)

        # Connect type toggles
        self._type_personal.toggled.connect(self._toggle_type)
        # Auto-fill text when zmanim combo changes
        def _autofill_zman_text(idx):
            if self._type_zmanim.isChecked():
                self._text_e.setText(self._zman_cb.currentText())
        self._zman_cb.currentIndexChanged.connect(_autofill_zman_text)
        self._type_zmanim.toggled.connect(
            lambda on: on and self._text_e.setText(self._zman_cb.currentText())
        )

        # Recurring
        rec_grp = QGroupBox("חזרה")
        rl = QHBoxLayout(rec_grp); rl.addStretch()
        self._rec_grp = QButtonGroup(self)
        for val, lbl, checked in [("weekly","שבועי",False),("daily","יומי",True),("none","חד פעמי",False)]:
            rb = QRadioButton(lbl); rb.setChecked(checked)
            rb.setProperty("rec_val", val)
            self._rec_grp.addButton(rb); rl.addWidget(rb); rl.addSpacing(10)
        fl.addWidget(rec_grp)

        # Days of week
        days_grp = QGroupBox("ימי שבוע")
        dl = QHBoxLayout(days_grp); dl.addStretch()
        HEB_DAYS = ["שבת","ו׳","ה׳","ד׳","ג׳","ב׳","א׳"]
        self._day_checks = []
        for i, d in enumerate(HEB_DAYS):
            col = QWidget(); cl2 = QVBoxLayout(col); cl2.setContentsMargins(0,0,0,0); cl2.setSpacing(2)
            lbl = QLabel(d); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); lbl.setStyleSheet("font-size:11px;font-weight:bold;color:#4a5580;")
            cb = QCheckBox(); cb.setChecked(True); cb.setStyleSheet("margin-left:6px;")
            cl2.addWidget(lbl); cl2.addWidget(cb)
            self._day_checks.insert(0, cb)
            dl.addWidget(col); dl.addSpacing(4)
        fl.addWidget(days_grp)

        # Exclusions
        excl_grp = QGroupBox("החרגות")
        el = QHBoxLayout(excl_grp); el.addStretch()
        self._skip_shab = QCheckBox("דלג על שבת"); self._skip_shab.setChecked(True)
        self._skip_hol  = QCheckBox("דלג על חגים ומועדים")
        el.addWidget(self._skip_hol); el.addSpacing(16); el.addWidget(self._skip_shab)
        fl.addWidget(excl_grp)

        # Notification
        notif_grp = QGroupBox("אופן התראה")
        nl = QVBoxLayout(notif_grp); nl.setContentsMargins(10,8,10,8); nl.setSpacing(6)

        # Visual display panel selector
        vis_lbl = QLabel("חלונית הצגה:")
        vis_lbl.setStyleSheet("font-weight:bold;font-size:11px;color:#1b3a7a;")
        nl.addWidget(vis_lbl)
        self._notice_cb = QComboBox()
        nl.addWidget(self._notice_cb)
        if_none_note = QLabel("כאשר לא נבחרה חלונית — הטקסט לא יוצג, רק הצליל (אם הופעל).")
        if_none_note.setStyleSheet("color:#7a8aaa;font-size:10px;"); if_none_note.setWordWrap(True)
        nl.addWidget(if_none_note)
        self._refresh_notice_cb()  # populate initially

        nl.addWidget(hline())

        snd_row = QWidget(); srl2 = QHBoxLayout(snd_row); srl2.setContentsMargins(0,0,0,0); srl2.addStretch()
        self._notif_snd = QCheckBox("השמע צליל"); self._notif_snd.setChecked(False)
        srl2.addWidget(self._notif_snd)
        nl.addWidget(snd_row)

        # Sound type selector (shown when sound is checked)
        self._snd_type_widget = QWidget()
        stl = QHBoxLayout(self._snd_type_widget); stl.setContentsMargins(0,0,0,0); stl.setSpacing(8)
        stl.addStretch()
        snd_lbl = QLabel("סוג צליל:"); snd_lbl.setStyleSheet("font-size:11px;color:#4a5580;")
        self._snd_type_cb = QComboBox()
        self._snd_type_cb.addItems([
            "ביפ (ברירת מחדל)",
            "כוכבית (System Asterisk)",
            "קריאה (System Exclamation)",
            "טינגל עולה",
            "טינגל יורד",
            "קובץ מהמחשב...",
        ])
        self._snd_type_values = ["beep","asterisk","exclamation","high","low","file"]
        self._snd_type_cb.setFixedWidth(200)
        stl.addWidget(self._snd_type_cb); stl.addWidget(snd_lbl)
        nl.addWidget(self._snd_type_widget)

        # File picker for custom sound
        self._snd_file_widget = QWidget()
        sfl = QHBoxLayout(self._snd_file_widget); sfl.setContentsMargins(0,0,0,0); sfl.setSpacing(6)
        sfl.addStretch()
        self._snd_file_e = QLineEdit(); self._snd_file_e.setPlaceholderText("נתיב לקובץ WAV/MP3...")
        self._snd_file_e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._snd_file_e.setFixedWidth(200)
        pick_snd = QPushButton("📂"); pick_snd.setFixedWidth(36); pick_snd.setObjectName("btn_secondary")
        pick_snd.clicked.connect(self._pick_sound_file)
        sfl.addWidget(self._snd_file_e); sfl.addWidget(pick_snd)
        self._snd_file_widget.setVisible(False)
        nl.addWidget(self._snd_file_widget)

        def _on_snd_toggle(checked):
            self._snd_type_widget.setVisible(checked)
            if not checked: self._snd_file_widget.setVisible(False)
        def _on_snd_type(idx):
            self._snd_file_widget.setVisible(self._notif_snd.isChecked() and idx == len(self._snd_type_values)-1)
        self._notif_snd.toggled.connect(_on_snd_toggle)
        self._snd_type_cb.currentIndexChanged.connect(_on_snd_type)
        self._snd_type_widget.setVisible(False)

        fl.addWidget(notif_grp)

        # Add button
        fl.addWidget(hline())
        add_btn = QPushButton("➕  הוסף תזכורת")
        add_btn.setObjectName("btn_success"); add_btn.setMinimumHeight(42)
        add_btn.clicked.connect(self._add)
        fl.addWidget(add_btn)

        self._status_lbl = QLabel(""); self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(self._status_lbl)
        fl.addStretch()

        right_lay.addWidget(scroll_wrap(form_widget))
        main.addWidget(right, 1)

        self._refresh_list()

    def _refresh_notice_cb(self):
        """Repopulate the panel selector with current notice + screen_msg panels."""
        if not hasattr(self, "_notice_cb"): return
        cur_data = self._notice_cb.currentData()  # preserve current selection
        self._notice_cb.blockSignals(True)
        self._notice_cb.clear()
        self._notice_cb.addItem("ללא הצגה חזותית", None)
        for p in self.cfg.panels():
            ptype = p.get("type","")
            pid   = p.get("id")
            pname = p.get("panel_name","") or f"#{pid}"
            if ptype == "notice":
                self._notice_cb.addItem(f"📢 הודעה צפה — {pname}", pid)
            elif ptype == "screen_msg":
                self._notice_cb.addItem(f"💬 הודעת מסך — {pname}", pid)
        # Restore selection
        for i in range(self._notice_cb.count()):
            if self._notice_cb.itemData(i) == cur_data:
                self._notice_cb.setCurrentIndex(i); break
        self._notice_cb.blockSignals(False)

    def showEvent(self, event):
        """Refresh panel list every time the tab becomes visible."""
        super().showEvent(event)
        self._refresh_notice_cb()
        self._refresh_zman_cb()
        self._refresh_list()

    def _refresh_zman_cb(self):
        """Repopulate the zmanim selector with current effective list (custom names + duplicates)."""
        if not hasattr(self, "_zman_cb"): return
        cur_data = self._zman_cb.currentData()
        self._zman_cb.blockSignals(True)
        self._zman_cb.clear()
        eff_list = get_effective_zmanim_list(self.cfg.d)
        for uid, key, name in eff_list:
            self._zman_cb.addItem(name, uid)
        # Restore selection or default to sunset
        restored = False
        for i in range(self._zman_cb.count()):
            if self._zman_cb.itemData(i) == cur_data:
                self._zman_cb.setCurrentIndex(i); restored = True; break
        if not restored:
            for i in range(self._zman_cb.count()):
                if self._zman_cb.itemData(i) == "sunset":
                    self._zman_cb.setCurrentIndex(i); break
        self._zman_cb.blockSignals(False)

    def _toggle_type(self, personal):
        self._personal_grp.setVisible(personal)
        self._zmanim_grp.setVisible(not personal)

    def _pick_sound_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "בחר קובץ צליל", "",
            "קובצי שמע (*.wav *.mp3 *.ogg *.aiff *.flac)")
        if p: self._snd_file_e.setText(p)

    def _refresh_list(self):
        self._list.clear()
        for r in self.cfg.reminders():
            done = r.get("done",False)
            last = r.get("last_triggered","")
            st = "✓" if done else ("↺" if last else "⏳")
            rtype = "🕍" if r.get("rem_type")=="zmanim" else "📅"
            text = r.get("text","")[:20]
            if r.get("rem_type")=="zmanim":
                zman_val = r.get("zman","")
                # zman_val may be a uid or a key; look up display name
                zname = ZMANIM_KEYS.get(zman_val, "")
                if not zname:
                    eff = get_effective_zmanim_list(self.cfg.d)
                    for uid, key, name in eff:
                        if uid == zman_val:
                            zname = name; break
                    if not zname: zname = zman_val
                off = r.get("offset_min",0)
                when = f"{zname} {'+' if off>=0 else ''}{off}′"
            else:
                when = r.get("dt","")[:16]
            item = QListWidgetItem(f"{rtype} {text}\n   {when}  {st}")
            item.setData(Qt.ItemDataRole.UserRole, r.get("id"))
            self._list.addItem(item)

    def _add(self):
        txt = self._text_e.text().strip()
        if not txt: self._status_lbl.setText("⚠ יש לרשום טקסט"); return
        days = [i for i,cb in enumerate(self._day_checks) if cb.isChecked()]
        if not days: self._status_lbl.setText("⚠ יש לבחור יום"); return
        rec = "none"
        for btn in self._rec_grp.buttons():
            if btn.isChecked(): rec = btn.property("rec_val"); break
        notice_pid = None
        if self._notice_cb and self._notice_cb.currentIndex() > 0:
            notice_pid = self._notice_cb.currentData()

        # Sound settings
        notify_sound = self._notif_snd.isChecked()
        snd_idx = self._snd_type_cb.currentIndex()
        sound_type = self._snd_type_values[snd_idx] if snd_idx < len(self._snd_type_values) else "beep"
        sound_file = self._snd_file_e.text().strip() if sound_type == "file" else ""

        if self._type_personal.isChecked():
            dt_str = f"{self._date_e.text().strip()} {self._time_e.text().strip()}"
            try: datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            except: self._status_lbl.setText("⚠ פורמט תאריך שגוי"); return
            self.cfg.add_reminder(txt,"personal",dt_str=dt_str,days=days,
                skip_shabbat=self._skip_shab.isChecked(),skip_holidays=self._skip_hol.isChecked(),
                recurring=rec,notify_visual=bool(notice_pid),
                notify_sound=notify_sound,notice_panel_id=notice_pid,
                sound_type=sound_type,sound_file=sound_file)
        else:
            self.cfg.add_reminder(txt,"zmanim",
                zman=self._zman_cb.currentData(),
                offset_min=self._offset_spin.value(),days=days,
                skip_shabbat=self._skip_shab.isChecked(),skip_holidays=self._skip_hol.isChecked(),
                recurring=rec,notify_visual=bool(notice_pid),
                notify_sound=notify_sound,notice_panel_id=notice_pid,
                sound_type=sound_type,sound_file=sound_file)
        self._text_e.clear()
        self._status_lbl.setText("✓ תזכורת נוספה בהצלחה!")
        self._refresh_list()

    def _del(self):
        item = self._list.currentItem()
        if not item: return
        rid = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,"מחיקה","למחוק את התזכורת?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.cfg.del_reminder(rid); self._refresh_list()

    def _reset(self):
        item = self._list.currentItem()
        if not item: return
        self.cfg.mark_reminder(item.data(Qt.ItemDataRole.UserRole), done=False)
        self._refresh_list()


# ── Startup helpers ──────────────────────────────────────────────────────────
def _startup_get():
    """Check if app is set to start on boot."""
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run")
            winreg.QueryValueEx(k, "DigitalBulletin"); winreg.CloseKey(k)
            return True
        except: return False
    else:
        return (Path.home() / ".config/autostart/digital_bulletin.desktop").exists()

def _startup_set(enabled):
    """Enable or disable app startup on boot."""
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enabled:
                script = str(Path(sys.argv[0]).resolve())
                winreg.SetValueEx(k, "DigitalBulletin", 0, winreg.REG_SZ,
                    f'"{sys.executable}" "{script}"')
            else:
                try: winreg.DeleteValue(k, "DigitalBulletin")
                except: pass
            winreg.CloseKey(k); return True
        except Exception as e: return False
    else:
        autostart = Path.home() / ".config/autostart"
        autostart.mkdir(parents=True, exist_ok=True)
        desktop = autostart / "digital_bulletin.desktop"
        if enabled:
            script = str(Path(sys.argv[0]).resolve())
            desktop.write_text(
                f"[Desktop Entry]\nType=Application\nName=לוח מודעות דיגיטלי\n"
                f"Exec={sys.executable} {script}\nHidden=false\n"
                f"X-GNOME-Autostart-enabled=true\n")
        else:
            if desktop.exists(): desktop.unlink()
        return True

# ── Settings Tab ─────────────────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Password section ──
        pw_card, pcl = card("🔐  אבטחה וסיסמא")
        pw_body = QWidget(); pb = QVBoxLayout(pw_body); pb.setContentsMargins(12,8,12,12)
        self._pw_status = QLabel(); self._update_pw_status(); pb.addWidget(self._pw_status)
        pb.addWidget(hline())
        info = QLabel("הסיסמא נדרשת לפתיחת ממשק הניהול (F8)")
        info.setStyleSheet("color:#6070a0;font-size:11px;")
        pb.addWidget(info)
        pw_row = QWidget(); pwr = QHBoxLayout(pw_row); pwr.setContentsMargins(0,4,0,0); pwr.addStretch()
        set_b = QPushButton("🔑  שנה / הגדר סיסמא"); set_b.clicked.connect(self._set_pw)
        del_b = QPushButton("🗑  מחק סיסמא"); del_b.setObjectName("btn_danger"); del_b.clicked.connect(self._del_pw)
        pwr.addWidget(del_b); pwr.addWidget(set_b)
        pb.addWidget(pw_row)
        pcl.addWidget(pw_body); lay.addWidget(pw_card)

        # ── Startup section ──
        su_card, scl = card("🚀  הפעלה אוטומטית בהפעלת המחשב")
        su_body = QWidget(); sb = QVBoxLayout(su_body); sb.setContentsMargins(12,8,12,12)
        desc = QLabel("כשמופעל — לוח המודעות יעלה אוטומטית בכל הפעלת המחשב")
        desc.setStyleSheet("color:#6070a0;font-size:11px;"); sb.addWidget(desc)
        su_row = QWidget(); sur = QHBoxLayout(su_row); sur.setContentsMargins(0,6,0,0); sur.addStretch()
        self._startup_cb = QCheckBox("הפעל לוח מודעות עם הפעלת המחשב")
        self._startup_cb.setChecked(_startup_get())
        self._su_status = QLabel("")
        self._su_status.setStyleSheet("color:#1a9a5c;font-size:11px;")
        save_su = QPushButton("💾  שמור הגדרת הפעלה"); save_su.setObjectName("btn_success")
        save_su.clicked.connect(self._save_startup)
        sur.addWidget(self._su_status); sur.addWidget(self._startup_cb); sur.addWidget(save_su)
        sb.addWidget(su_row)
        scl.addWidget(su_body); lay.addWidget(su_card)

        # ── Full Export / Import section ──
        io_card, icl = card("💾  יצוא / יבוא כל ההגדרות")
        io_body = QWidget(); ib = QVBoxLayout(io_body); ib.setContentsMargins(12,8,12,12)
        io_desc = QLabel(
            "יצוא כולל: כל ההגדרות, תוכן מודעות, תזכורות, ססמה, "
            "תמונות, הגדרות מיקום — הכל בקובץ דחוס יחיד (.dbzip)"
        )
        io_desc.setStyleSheet("color:#6070a0;font-size:11px;")
        io_desc.setWordWrap(True); ib.addWidget(io_desc)
        io_row = QWidget(); ir = QHBoxLayout(io_row); ir.setContentsMargins(0,8,0,0); ir.addStretch()
        imp_b = QPushButton("📥  יבוא הגדרות"); imp_b.setObjectName("btn_secondary")
        imp_b.clicked.connect(self._full_import)
        exp_b = QPushButton("📤  יצוא הגדרות"); exp_b.setObjectName("btn_success")
        exp_b.clicked.connect(self._full_export)
        ir.addWidget(imp_b); ir.addWidget(exp_b)
        ib.addWidget(io_row)
        icl.addWidget(io_body); lay.addWidget(io_card)

        # ── Design resolution card ──────────────────────────────────────
        res_card, rcl = card("📐  רזולוציית עיצוב (לפריסה רספונסיבית)")
        res_body = QWidget(); rb2 = QVBoxLayout(res_body); rb2.setContentsMargins(12,8,12,12)
        res_desc = QLabel(
            "רשום כאן את רזולוציית המסך שעליו תיכננת את הפריסה.\n"
            "כשהתוכנה פועלת על מסך בעל רזולוציה שונה, כל החלוניות ישנו קנה מידה אוטומטית."
        )
        res_desc.setStyleSheet("color:#6070a0;font-size:11px;")
        res_desc.setWordWrap(True); rb2.addWidget(res_desc)

        res_row = QWidget(); rrr = QHBoxLayout(res_row)
        rrr.setContentsMargins(0,8,0,0); rrr.setSpacing(8)

        disp_cfg = self.cfg.d.get("display",{})
        try:
            from PyQt6.QtWidgets import QApplication as _QA
            _scr = _QA.primaryScreen().geometry()
            _dw_def = _scr.width(); _dh_def = _scr.height()
        except Exception:
            _dw_def, _dh_def = 1920, 1080

        self._dw_sp = QSpinBox(); self._dw_sp.setRange(640,7680)
        self._dw_sp.setValue(disp_cfg.get("design_width", _dw_def))
        self._dh_sp = QSpinBox(); self._dh_sp.setRange(480,4320)
        self._dh_sp.setValue(disp_cfg.get("design_height", _dh_def))

        lbl_x = QLabel("רוחב:"); lbl_x.setStyleSheet("font-size:11px;color:#4a5580;")
        lbl_y = QLabel("×"); lbl_y.setStyleSheet("font-size:12px;color:#4a5580;padding:0 4px;")
        lbl_h = QLabel("גובה:"); lbl_h.setStyleSheet("font-size:11px;color:#4a5580;")

        snap_btn = QPushButton("📷  קלוט מסך נוכחי")
        snap_btn.setObjectName("btn_secondary")
        def _snap_res():
            try:
                from PyQt6.QtWidgets import QApplication as _QA2
                g = _QA2.primaryScreen().geometry()
                self._dw_sp.setValue(g.width()); self._dh_sp.setValue(g.height())
            except: pass
        snap_btn.clicked.connect(_snap_res)

        save_res = QPushButton("💾  שמור"); save_res.setObjectName("btn_success")
        def _save_res():
            disp = self.cfg.d.setdefault("display",{})
            disp["design_width"]  = self._dw_sp.value()
            disp["design_height"] = self._dh_sp.value()
            self.cfg.save()
            QMessageBox.information(self, "הצלחה",
                f"רזולוציית עיצוב נשמרה: {self._dw_sp.value()}×{self._dh_sp.value()}")
        save_res.clicked.connect(_save_res)

        rrr.addWidget(lbl_x); rrr.addWidget(self._dw_sp)
        rrr.addWidget(lbl_y); rrr.addWidget(self._dh_sp)
        rrr.addWidget(lbl_h)
        rrr.addStretch()
        rrr.addWidget(snap_btn); rrr.addWidget(save_res)
        rb2.addWidget(res_row)
        rcl.addWidget(res_body); lay.addWidget(res_card)

        outer.addWidget(scroll_wrap(content))

    def _update_pw_status(self):
        has = self.cfg.has_pw()
        self._pw_status.setText("✓  סיסמא מוגדרת" if has else "✗  אין סיסמא מוגדרת")
        self._pw_status.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{'#1a9a5c' if has else '#a0aabb'};"
        )

    def _set_pw(self):
        pw, ok = QInputDialog.getText(self, "סיסמא חדשה", "הזן סיסמא חדשה:", QLineEdit.EchoMode.Password)
        if not ok: return
        if pw:
            pw2, ok2 = QInputDialog.getText(self, "אימות", "הזן שוב:", QLineEdit.EchoMode.Password)
            if not ok2: return
            if pw != pw2: QMessageBox.warning(self, "שגיאה", "הסיסמאות אינן תואמות"); return
        self.cfg.set_pw(pw); self._update_pw_status()
        QMessageBox.information(self, "הצלחה", "הסיסמא עודכנה")

    def _del_pw(self):
        if self.cfg.has_pw():
            pw, ok = QInputDialog.getText(self, "אימות", "הזן את הסיסמא הנוכחית:", QLineEdit.EchoMode.Password)
            if not ok: return
            if not self.cfg.check_pw(pw): QMessageBox.warning(self, "שגיאה", "סיסמא שגויה"); return
        self.cfg.set_pw("")
        self._update_pw_status()
        QMessageBox.information(self, "הצלחה", "הסיסמא נמחקה")

    def _save_startup(self):
        ok = _startup_set(self._startup_cb.isChecked())
        if ok:
            state = "מופעל ✓" if self._startup_cb.isChecked() else "מבוטל"
            self._su_status.setText(f"הפעלה אוטומטית — {state}")
            QTimer.singleShot(3000, lambda: self._su_status.setText(""))
        else:
            QMessageBox.warning(self, "שגיאה", "לא ניתן היה לשנות את הגדרת ההפעלה האוטומטית")

    def _full_export(self):
        path, _ = QFileDialog.getSaveFileName(self.window(), "יצוא כל ההגדרות",
            "ערכות-עיצוב_תוכן_הגדרות.zip",
            "יצוא מלא (*.zip);;Digital Bulletin Full Backup (*.dbzip)")
        if not path: return
        try:
            n, theme_names = self.cfg.full_export(path)
            themes_txt = ""
            if theme_names:
                themes_txt = "\n\nערכות עיצוב שיוצאו:\n" + "\n".join(f"  • {nm}" for nm in theme_names)
            QMessageBox.information(self, "יצוא הושלם",
                f"כל ההגדרות, התוכן והעיצוב יוצאו בהצלחה!\n"
                f"ערכות עיצוב: {len(theme_names)}  |  תמונות: {n}{themes_txt}")
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _full_import(self):
        path, _ = QFileDialog.getOpenFileName(self.window(), "יבוא כל ההגדרות", "",
            "יצוא מלא (*.zip *.dbzip)")
        if not path: return
        reply = QMessageBox.question(self, "אישור יבוא",
            "היבוא ידרוס את כל ההגדרות הנוכחיות (ססמה, תוכן, תזכורות, עיצוב).\nהאם להמשיך?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            report = self.cfg.full_import(path)
            self._show_full_import_report(report)
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", str(e))

    def _show_full_import_report(self, report):
        sections = report.get("sections", [])
        theme_names = report.get("theme_names", [])
        lines = ["✅  יבוא מלא הושלם!", "", "לשוניות שיובאו:"]
        for s in sections:
            lines.append(f"  ✓ {s}")
        if not sections:
            lines.append("  (לא נמצאו נתונים בקובץ)")
        if theme_names:
            lines.append("")
            lines.append(f"ערכות עיצוב שיובאו ({len(theme_names)}):")
            for nm in theme_names:
                lines.append(f"  • {nm}")
        lines.append("")
        lines.append("⚠ יש להפעיל מחדש את התוכנה להחלת השינויים.")
        msg = "\n".join(lines)
        dlg = _ImportReportDialog("דוח יבוא מלא", msg, self)
        dlg.exec()

# ── Shutdown & Cover Tab ─────────────────────────────────────────────────────
# Holiday definitions with Hebrew calendar months/days
_JEWISH_HOLIDAYS = [
    ("שבת",       "shabbat",   []),  # special — computed dynamically
    ("ראש השנה",  "rosh_hashana",  [(7,1),(7,2)]),
    ("יום כיפור", "yom_kippur",    [(7,10)]),
    ("סוכות",     "sukkot",        [(7,15),(7,16),(7,17),(7,18),(7,19),(7,20),(7,21)]),
    ("שמיני עצרת / שמחת תורה", "shmini_atzeret", [(7,22),(7,23)]),
    ("חנוכה",     "chanuka",       [(9,25),(9,26),(9,27),(9,28),(9,29),(9,30),(10,1),(10,2),(10,3)]),
    ("פורים",     "purim",         [(12,14),(12,15)]),
    ("פסח",       "pesach",        [(1,15),(1,16),(1,17),(1,18),(1,19),(1,20),(1,21),(1,22)]),
    ("שבועות",    "shavuot",       [(3,6),(3,7)]),
    ("ראש חודש",  "rosh_chodesh",  []),  # dynamic
    ("תשעה באב",  "tisha_beav",    [(5,9)]),
    ("יום העצמאות","yom_haatzmaut",[(2,5)]),
]

def _hol_day_label(month_day):
    """Return Hebrew month name for (month, day) tuple."""
    HEB_M = ["","ניסן","אייר","סיוון","תמוז","אב","אלול",
             "תשרי","חשוון","כסלו","טבת","שבט","אדר","אדר א׳","אדר ב׳"]
    m, d = month_day
    return f"{d} {HEB_M[m] if m < len(HEB_M) else str(m)}"

class HolidayDaysDialog(QDialog):
    """Dialog to select specific days within a holiday."""
    def __init__(self, holiday_name, days_list, selected_days, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"בחר ימים — {holiday_name}")
        self.setMinimumWidth(320)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lay = QVBoxLayout(self)
        lay.setSpacing(8); lay.setContentsMargins(16,16,16,16)
        lbl = QLabel(f"בחר אילו ימים של {holiday_name} ייחסמו:")
        lbl.setWordWrap(True); lay.addWidget(lbl)

        self._checks = {}
        for md in days_list:
            key = f"{md[0]}_{md[1]}"
            cb = QCheckBox(_hol_day_label(md))
            cb.setChecked(key in selected_days)
            self._checks[key] = cb
            lay.addWidget(cb)

        if not days_list:
            lay.addWidget(QLabel("(כל הימים — אין בחירה נדרשת)"))

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_selected(self):
        return [k for k, cb in self._checks.items() if cb.isChecked()]


class ShutdownCoverTab(QWidget):
    """
    לשונית כיבוי וכיסוי:
    א. כיסוי מסך מלא בשבתות וחגים
    ב. הגדרות כיבוי מסך לזמנים מוגדרים
    """
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._build()

    # ─────────────────────────── build ───────────────────────────────────────
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(20)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ════════════════════════════════════════════════════════════════
        # Section A — Shabbat/Holiday Cover
        # ════════════════════════════════════════════════════════════════
        cover_card, ccl = card("🕯  א. כיסוי מסך בשבתות וחגים")
        cover_body = QWidget(); cb_lay = QVBoxLayout(cover_body)
        cb_lay.setContentsMargins(12,8,12,16); cb_lay.setSpacing(10)

        # Enable toggle
        self._cover_enabled = QCheckBox("הפעל כיסוי מסך אוטומטי בשבתות וחגים")
        self._cover_enabled.setStyleSheet("font-weight:bold;font-size:13px;")
        scfg = self._sc()
        self._cover_enabled.setChecked(scfg.get("cover_enabled", False))
        cb_lay.addWidget(self._cover_enabled)
        cb_lay.addWidget(hline())

        # Time margins
        margins_grp = QGroupBox("⏱  זמן חסימה")
        mg = QFormLayout(margins_grp); mg.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        mg.setSpacing(8)
        self._before_spin = QSpinBox(); self._before_spin.setRange(0,120)
        self._before_spin.setValue(scfg.get("cover_before_min", 18))
        self._before_spin.setSuffix("  דקות")
        self._after_spin = QSpinBox(); self._after_spin.setRange(0,120)
        self._after_spin.setValue(scfg.get("cover_after_min", 50))
        self._after_spin.setSuffix("  דקות")
        mg.addRow("התחל חסימה כמה דקות לפני שקיעה:", self._before_spin)
        mg.addRow("סיים חסימה כמה דקות אחרי שקיעה במוצאי שבת/חג:", self._after_spin)
        cb_lay.addWidget(margins_grp)
        cb_lay.addWidget(hline())

        # Holidays list with day-selector and image-picker per holiday
        hol_lbl = QLabel("בחר חגים ותמונות כיסוי:")
        hol_lbl.setStyleSheet("font-weight:bold;color:#1b3a7a;font-size:12px;")
        cb_lay.addWidget(hol_lbl)

        self._hol_widgets = {}  # key -> {enabled_cb, img_lbl, days_btn, selected_days}

        hol_scroll = QScrollArea(); hol_scroll.setWidgetResizable(True)
        hol_scroll.setFixedHeight(360); hol_scroll.setStyleSheet("QScrollArea{border:none;}")
        hol_inner = QWidget(); hol_grid = QGridLayout(hol_inner)
        hol_grid.setSpacing(6); hol_grid.setContentsMargins(4,4,4,4)
        hol_grid.setColumnStretch(1, 1)

        saved_hols = scfg.get("holidays", {})
        for row_idx, (hname, hkey, hdays) in enumerate(_JEWISH_HOLIDAYS):
            hs = saved_hols.get(hkey, {})
            # Checkbox
            en_cb = QCheckBox(hname)
            en_cb.setChecked(hs.get("enabled", hkey == "shabbat"))
            # Image path label + browse button
            img_lbl = QLabel(hs.get("image", "") or "(ללא תמונה)")
            img_lbl.setStyleSheet("color:#6070a0;font-size:10px;max-width:260px;")
            img_lbl.setWordWrap(False)
            img_btn = QPushButton("🖼")
            img_btn.setFixedSize(32, 28)
            img_btn.setObjectName("btn_secondary")
            img_btn.setToolTip(f"בחר תמונת כיסוי ל{hname}")
            # Days-selector button (only for holidays with explicit days)
            selected_days = hs.get("selected_days",
                [f"{d[0]}_{d[1]}" for d in hdays])  # default: all days
            days_btn = None
            if hdays:
                days_btn = QPushButton("📅 ימים")
                days_btn.setFixedHeight(28)
                days_btn.setObjectName("btn_secondary")
                days_btn.setToolTip("בחר אילו ימים של החג ייחסמו")

            self._hol_widgets[hkey] = {
                "enabled_cb": en_cb,
                "img_lbl": img_lbl,
                "img_btn": img_btn,
                "days_btn": days_btn,
                "days_list": hdays,
                "selected_days": list(selected_days),
            }

            hol_grid.addWidget(en_cb, row_idx, 0)
            hol_grid.addWidget(img_lbl, row_idx, 1)
            # Days button
            if days_btn:
                hol_grid.addWidget(days_btn, row_idx, 2)
                _hkey = hkey
                def _make_days_handler(k):
                    def _handler():
                        w = self._hol_widgets[k]
                        dlg = HolidayDaysDialog(
                            [h[0] for h in _JEWISH_HOLIDAYS if h[1]==k][0],
                            w["days_list"], w["selected_days"], self)
                        if dlg.exec() == QDialog.DialogCode.Accepted:
                            w["selected_days"] = dlg.get_selected()
                    return _handler
                days_btn.clicked.connect(_make_days_handler(_hkey))
            hol_grid.addWidget(img_btn, row_idx, 3)

            # Image browse handler
            def _make_img_handler(k):
                def _handler():
                    path, _ = QFileDialog.getOpenFileName(
                        self, f"בחר תמונת כיסוי", "",
                        "תמונות (*.png *.jpg *.jpeg *.bmp *.gif);;הכל (*)")
                    if path:
                        path = Config.copy_image_to_store(path)
                        self._hol_widgets[k]["img_lbl"].setText(path)
                return _handler
            img_btn.clicked.connect(_make_img_handler(hkey))

        hol_inner.setLayout(hol_grid)
        hol_scroll.setWidget(hol_inner)
        cb_lay.addWidget(hol_scroll)

        # Save button
        save_cover_btn = QPushButton("💾  שמור הגדרות כיסוי")
        save_cover_btn.setObjectName("btn_success")
        save_cover_btn.clicked.connect(self._save_cover)
        cb_lay.addWidget(save_cover_btn)

        ccl.addWidget(cover_body); lay.addWidget(cover_card)

        # ════════════════════════════════════════════════════════════════
        # Section B — Screen Off Schedules
        # ════════════════════════════════════════════════════════════════
        sleep_card, slcl = card("🌙  ב. כיבוי מסך לזמנים מוגדרים")
        sleep_body = QWidget(); sl_lay = QVBoxLayout(sleep_body)
        sl_lay.setContentsMargins(12,8,12,16); sl_lay.setSpacing(10)

        sl_enable = QCheckBox("הפעל כיבוי/הדלקה אוטומטי של המסך")
        sl_enable.setStyleSheet("font-weight:bold;font-size:13px;")
        self._sleep_enabled = sl_enable
        sl_enable.setChecked(self._sc().get("sleep_enabled", False))
        sl_lay.addWidget(sl_enable)

        sl_desc = QLabel(
            "הגדר תרחישי כיבוי: בכל תרחיש ניתן להגדיר טווח שעות, טווח תאריכים ו/או ימי שבוע.\n"
            "בזמן הכיבוי המסך ייכבה, ולאחר מכן יידלק מחדש אוטומטית."
        )
        sl_desc.setStyleSheet("color:#6070a0;font-size:11px;"); sl_desc.setWordWrap(True)
        sl_lay.addWidget(sl_desc)
        sl_lay.addWidget(hline())

        # Schedule list area
        self._schedules_widget = QWidget()
        self._schedules_layout = QVBoxLayout(self._schedules_widget)
        self._schedules_layout.setSpacing(8); self._schedules_layout.setContentsMargins(0,0,0,0)
        sl_scroll = QScrollArea(); sl_scroll.setWidgetResizable(True)
        sl_scroll.setFixedHeight(320); sl_scroll.setStyleSheet("QScrollArea{border:none;}")
        sl_scroll.setWidget(self._schedules_widget)
        sl_lay.addWidget(sl_scroll)

        # Add schedule button
        add_sched_btn = QPushButton("➕  הוסף זמן כיבוי")
        add_sched_btn.setObjectName("btn_secondary")
        add_sched_btn.clicked.connect(lambda _=None: self._add_schedule())
        sl_lay.addWidget(add_sched_btn)

        save_sleep_btn = QPushButton("💾  שמור הגדרות כיבוי מסך")
        save_sleep_btn.setObjectName("btn_success")
        save_sleep_btn.clicked.connect(self._save_sleep)
        sl_lay.addWidget(save_sleep_btn)

        slcl.addWidget(sleep_body); lay.addWidget(sleep_card)

        outer.addWidget(scroll_wrap(content))

        # Load existing schedules
        self._schedule_rows = []
        for sched in self._sc().get("sleep_schedules", []):
            self._add_schedule(sched)

    # ─────────────────────────── helpers ─────────────────────────────────────
    def _sc(self):
        """Return shutdown_cover config dict."""
        return self.cfg.d.setdefault("shutdown_cover", {})

    def _add_schedule(self, data=None):
        """Add a schedule row widget."""
        if data is None:
            data = {}
        grp = QGroupBox()
        grp.setStyleSheet(
            "QGroupBox{background:#f0f5ff;border:1px solid #c0d0f0;border-radius:8px;"
            "margin-top:0px;padding:8px;}")
        g_lay = QVBoxLayout(grp); g_lay.setSpacing(6)

        row1 = QWidget(); r1 = QHBoxLayout(row1); r1.setContentsMargins(0,0,0,0); r1.setSpacing(8)
        r1.addWidget(QLabel("כיבוי:"))
        off_h = QSpinBox(); off_h.setRange(0,23); off_h.setValue(data.get("off_hour", 22))
        off_h.setPrefix("שעה "); off_h.setFixedWidth(90)
        off_m = QSpinBox(); off_m.setRange(0,59); off_m.setValue(data.get("off_min", 0))
        off_m.setPrefix("דק׳ "); off_m.setFixedWidth(85)
        r1.addWidget(off_h); r1.addWidget(off_m)
        r1.addSpacing(16); r1.addWidget(QLabel("הדלקה:"))
        on_h = QSpinBox(); on_h.setRange(0,23); on_h.setValue(data.get("on_hour", 6))
        on_h.setPrefix("שעה "); on_h.setFixedWidth(90)
        on_m = QSpinBox(); on_m.setRange(0,59); on_m.setValue(data.get("on_min", 0))
        on_m.setPrefix("דק׳ "); on_m.setFixedWidth(85)
        r1.addWidget(on_h); r1.addWidget(on_m)
        r1.addStretch()
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30,28); del_btn.setObjectName("btn_danger")
        r1.addWidget(del_btn)
        g_lay.addWidget(row1)

        # Days of week
        row2 = QWidget(); r2 = QHBoxLayout(row2); r2.setContentsMargins(0,0,0,0); r2.setSpacing(4)
        r2.addWidget(QLabel("ימים:"))
        days_labels = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","ש׳"]
        day_cbs = []
        enabled_days = data.get("days", list(range(7)))
        for di, dl in enumerate(days_labels):
            dcb = QCheckBox(dl); dcb.setChecked(di in enabled_days)
            dcb.setStyleSheet("spacing:3px;")
            day_cbs.append(dcb); r2.addWidget(dcb)
        r2.addStretch()
        g_lay.addWidget(row2)

        # Date range (optional)
        row3 = QWidget(); r3 = QHBoxLayout(row3); r3.setContentsMargins(0,0,0,0); r3.setSpacing(6)
        date_range_cb = QCheckBox("הגבל לטווח תאריכים")
        date_range_cb.setChecked(bool(data.get("date_from") or data.get("date_to")))
        r3.addWidget(date_range_cb)
        from_le = QLineEdit(); from_le.setPlaceholderText("מ- YYYY-MM-DD")
        from_le.setFixedWidth(140); from_le.setText(data.get("date_from",""))
        to_le = QLineEdit(); to_le.setPlaceholderText("עד YYYY-MM-DD")
        to_le.setFixedWidth(140); to_le.setText(data.get("date_to",""))
        r3.addWidget(from_le); r3.addWidget(QLabel("—")); r3.addWidget(to_le)
        r3.addStretch()
        g_lay.addWidget(row3)

        row_data = {
            "widget": grp,
            "off_h": off_h, "off_m": off_m,
            "on_h": on_h, "on_m": on_m,
            "day_cbs": day_cbs,
            "date_range_cb": date_range_cb,
            "from_le": from_le, "to_le": to_le,
        }
        self._schedule_rows.append(row_data)
        self._schedules_layout.addWidget(grp)

        def _del():
            self._schedule_rows.remove(row_data)
            grp.setParent(None); grp.deleteLater()
        del_btn.clicked.connect(_del)

    # ─────────────────────────── save handlers ───────────────────────────────
    def _save_cover(self):
        sc = self._sc()
        sc["cover_enabled"] = self._cover_enabled.isChecked()
        sc["cover_before_min"] = self._before_spin.value()
        sc["cover_after_min"] = self._after_spin.value()
        holidays = {}
        for hkey, w in self._hol_widgets.items():
            img_text = w["img_lbl"].text()
            img_path = "" if img_text == "(ללא תמונה)" else img_text
            holidays[hkey] = {
                "enabled": w["enabled_cb"].isChecked(),
                "image": img_path,
                "selected_days": w["selected_days"],
            }
        sc["holidays"] = holidays
        self.cfg.save()
        # Signal tkinter display to reload
        sig = CFG.parent / "refresh_signal"; sig.touch()
        QMessageBox.information(self, "הצלחה", "הגדרות כיסוי נשמרו ✓")

    def _save_sleep(self):
        sc = self._sc()
        sc["sleep_enabled"] = self._sleep_enabled.isChecked()
        schedules = []
        for rd in self._schedule_rows:
            schedules.append({
                "off_hour": rd["off_h"].value(),
                "off_min":  rd["off_m"].value(),
                "on_hour":  rd["on_h"].value(),
                "on_min":   rd["on_m"].value(),
                "days": [i for i, cb in enumerate(rd["day_cbs"]) if cb.isChecked()],
                "date_from": rd["from_le"].text().strip() if rd["date_range_cb"].isChecked() else "",
                "date_to":   rd["to_le"].text().strip()   if rd["date_range_cb"].isChecked() else "",
            })
        sc["sleep_schedules"] = schedules
        self.cfg.save()
        sig = CFG.parent / "refresh_signal"; sig.touch()
        QMessageBox.information(self, "הצלחה", "הגדרות כיבוי מסך נשמרו ✓")


# ── About Tab ────────────────────────────────────────────────────────────────
class AboutTab(QWidget):
    """About tab — third-party library credits and licenses, RTL layout."""
    def __init__(self, cfg, parent=None):
        super().__init__(parent); self.cfg = cfg
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget(); il = QVBoxLayout(inner)
        il.setContentsMargins(28,24,28,24); il.setSpacing(16)
        il.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        title_lbl = QLabel("לוח מודעות דיגיטלי — ספריות צד שלישי וקרדיט")
        title_lbl.setStyleSheet("font-size:18px;font-weight:bold;color:#1b3a7a;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        ver_lbl = QLabel("גרסה 4.5")
        ver_lbl.setStyleSheet("font-size:12px;color:#6070a0;")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        il.addWidget(title_lbl); il.addWidget(ver_lbl)
        il.addWidget(hline())

        note_lbl = QLabel(
            "התוכנה משתמשת בספריות קוד פתוח הבאות. "
            "לכל ספרייה קרדיט מלא, פרטי מחבר ורישיון כנדרש על פי כללי קוד פתוח בין-לאומיים."
        )
        note_lbl.setStyleSheet("color:#4a5580;font-size:11px;")
        note_lbl.setWordWrap(True); note_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        il.addWidget(note_lbl)
        il.addWidget(hline())

        # Libraries to credit (only those requiring attribution)
        libs = [
            ("PyQt6", "≥6.4",
             "Riverbank Computing Ltd.",
             "GPL v3 / Commercial License",
             "https://riverbankcomputing.com/software/pyqt/",
             "ממשק ניהול התוכנה (מנהל לוח המודעות). שימוש תחת GPL v3.\n"
             "© 2024 Riverbank Computing Ltd. All rights reserved."),

            ("Pillow (PIL Fork)", "≥9.0",
             "Alex Clark and PIL Contributors",
             "HPND License (Historical Permission Notice and Disclaimer)",
             "https://python-pillow.org",
             "עיבוד תמונות, שקיפות, שכבות רקע ועיבוד גרפי.\n"
             "© 2010–2024 Alex Clark and Contributors. Original PIL © 1997–2011 Secret Labs AB."),

            ("zmanim (Python)", "≥0.3",
             "Eliyahu Hershfeld (KosherJava) | Python port: pinnymz",
             "LGPL v2.1",
             "https://github.com/pinnymz/python-zmanim",
             "חישוב זמני הלכה — Python port של ספריית KosherJava.\n"
             "KosherJava © Eliyahu Hershfeld — https://kosherjava.com\n"
             "Python zmanim package © respective contributors. License: LGPL v2.1"),

            ("pyluach", "≥1.2",
             "Simcha Gottlieb",
             "MIT License",
             "https://github.com/simkimchi/pyluach",
             "חישוב לוח שנה עברי, פרשיות שבוע, חגים ומועדים.\n"
             "© Simcha Gottlieb. License: MIT."),

            ("astral", "≥3.0",
             "Simon Kennedy",
             "Apache License 2.0",
             "https://github.com/sffjunkie/astral",
             "חישוב שעות זריחה ושקיעה (שיטת astral/pytz).\n"
             "© Simon Kennedy. License: Apache 2.0."),

            ("pytz", "≥2023.3",
             "Stuart Bishop",
             "MIT License",
             "https://pypi.org/project/pytz/",
             "תמיכה באזורי זמן (Timezone support).\n"
             "© Stuart Bishop. License: MIT."),
        ]

        for lib_name, ver_s, author, lic, url, desc in libs:
            # Card — light bg, NO border outline around individual items
            card_w = QWidget()
            card_w.setStyleSheet(
                "QWidget { background:#f0f4fb; border-radius:8px; }"
            )
            cl = QVBoxLayout(card_w); cl.setContentsMargins(16,12,16,12); cl.setSpacing(6)

            # Name + version + license — right aligned
            top_row = QWidget(); tr_l = QHBoxLayout(top_row)
            tr_l.setContentsMargins(0,0,0,0)
            tr_l.setDirection(QHBoxLayout.Direction.RightToLeft)

            name_lbl = QLabel(f"<b>{lib_name}</b>  v{ver_s}")
            name_lbl.setStyleSheet("font-size:13px;color:#1b3a7a;")
            lic_lbl = QLabel(f"📄 {lic}")
            lic_lbl.setStyleSheet("color:#5060a0;font-size:10px;")
            tr_l.addWidget(name_lbl); tr_l.addStretch(); tr_l.addWidget(lic_lbl)
            cl.addWidget(top_row)

            # Author — right aligned
            auth_lbl = QLabel(f"© {author}")
            auth_lbl.setStyleSheet("color:#4a5580;font-size:11px;")
            auth_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            cl.addWidget(auth_lbl)

            # URL — right aligned, clickable
            url_btn = QPushButton(url); url_btn.setFlat(True)
            url_btn.setStyleSheet(
                "QPushButton{color:#2563eb;font-size:10px;text-decoration:underline;"
                "border:none;padding:0;text-align:right;}"
                "QPushButton:hover{color:#1740a0;}"
            )
            url_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            url_btn.clicked.connect(lambda _, u=url: __import__("webbrowser").open(u))
            cl.addWidget(url_btn)

            # Description — right aligned
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("color:#2d3a5a;font-size:11px;")
            desc_lbl.setWordWrap(True)
            desc_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            cl.addWidget(desc_lbl)

            il.addWidget(card_w)

        il.addWidget(hline())
        lic_note = QLabel(
            "הערת רישוי: שימוש ב-PyQt6 מחייב GPL v3 לקוד המפוץ לציבור. "
            "ספריית zmanim מופצת תחת LGPL v2.1. "
            "כל שאר הספריות מופצות תחת רישיונות מתירניים (MIT, Apache, HPND)."
        )
        lic_note.setStyleSheet("color:#5060a0;font-size:10px;")
        lic_note.setWordWrap(True); lic_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        il.addWidget(lic_note)

        scroll.setWidget(inner)
        lay.addWidget(scroll)



# ── Main Window ──────────────────────────────────────────────────────────────
class ManagerWindow(QMainWindow):
    def __init__(self, cfg_path):
        super().__init__()
        self.cfg = Cfg(cfg_path)
        self.setWindowTitle(f"לוח מודעות דיגיטלי — ממשק ניהול v4.5")
        self.setMinimumSize(1000, 680)
        self.resize(1260, 820)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._build()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0,0,0,0); main_lay.setSpacing(0)

        # ── Header ──
        hdr = QWidget(); hdr.setObjectName("header"); hdr.setFixedHeight(60)
        hl = QHBoxLayout(hdr); hl.setContentsMargins(12,0,12,0); hl.setSpacing(6)

        # Left side (RTL: appears on left visually)
        def hdr_btn(text, obj_id, tip=""):
            b = QPushButton(text); b.setObjectName("hdr_btn")
            if obj_id: b.setProperty("class", obj_id)
            b.setStyleSheet(b.styleSheet() + f"QPushButton#{obj_id}{{color:inherit;}}")
            b.setObjectName(obj_id)
            if tip: b.setToolTip(tip)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            return b

        close_b = hdr_btn("✕  סגור","hdr_close","סגור את ממשק הניהול (F8)")
        close_b.clicked.connect(self.close)
        exit_b  = hdr_btn("⏻  יציאה","hdr_exit","יציאה מלאה מהתוכנה")
        exit_b.clicked.connect(self._exit_app)
        refresh_b=hdr_btn("↻  רענן","hdr_refresh","רענן את התצוגה הראשית")
        refresh_b.clicked.connect(self._signal_refresh)

        hl.addWidget(close_b); hl.addWidget(exit_b)
        hl.addWidget(refresh_b)

        self._status_lbl = QLabel("מוכן"); self._status_lbl.setObjectName("status_label")
        hl.addWidget(self._status_lbl)
        hl.addStretch()

        logo = QLabel("▣  לוח מודעות דיגיטלי"); logo.setObjectName("logo_label")
        ver  = QLabel("v4.5"); ver.setObjectName("version_label")
        hl.addWidget(ver); hl.addWidget(logo)
        main_lay.addWidget(hdr)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._panels_tab   = PanelsTab(self.cfg)
        self._content_tab  = ContentTab(self.cfg)
        self._location_tab = LocationTab(self.cfg)
        self._settings_tab = SettingsTab(self.cfg)
        self._reminders_tab= RemindersTab(self.cfg)
        self._shutdown_tab = ShutdownCoverTab(self.cfg)
        self._about_tab    = AboutTab(self.cfg)

        self.tabs.addTab(self._panels_tab,    "  תצוגה  ")
        self.tabs.addTab(self._content_tab,   "  תוכן  ")
        self.tabs.addTab(self._location_tab,  "  זמן ומיקום  ")
        self.tabs.addTab(self._settings_tab,  "  הגדרות  ")
        self.tabs.addTab(self._reminders_tab, "  תזכורות  ")
        self.tabs.addTab(self._shutdown_tab,  "  כיבוי וכיסוי  ")
        self.tabs.addTab(self._about_tab,     "  אודות  ")

        self._panels_tab.display_refresh.connect(self._signal_refresh)
        self._panels_tab.display_refresh.connect(self._content_tab.refresh_list)
        self._content_tab.display_refresh.connect(self._signal_refresh)
        self._shutdown_tab  # no signals needed — saves directly
        main_lay.addWidget(self.tabs)

    def _signal_refresh(self):
        """Write a refresh signal for the tkinter process."""
        sig = CFG.parent / "refresh_signal"
        sig.touch()
        self._status_lbl.setText("✓ נשמר")
        QTimer.singleShot(2000, lambda: self._status_lbl.setText("מוכן"))

    def _exit_app(self):
        reply = QMessageBox.question(self,"יציאה","האם לצאת לגמרי מלוח המודעות?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Signal tkinter to exit
            cmd = {"action":"exit"}
            with open(CFG.parent/"cmd.json","w") as f: json.dump(cmd,f)
            self.close()

    def closeEvent(self, event):
        # Write closed signal
        sig = CFG.parent / "manager_closed"
        sig.touch()
        event.accept()

# ── Entry ─────────────────────────────────────────────────────────────────────
def main():
    cfg_path = Path(sys.argv[1]) if len(sys.argv)>1 else CFG

    # Token check disabled — manager can be opened directly or via F8
    # (token is still written by digital_bulletin.py but is no longer required)

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())

    # Font
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    win = ManagerWindow(cfg_path)
    win.show()
    sys.exit(app.exec())


def _warn_direct_access():
    """Show error if manager was opened directly instead of via F8."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    msg = QMessageBox()
    msg.setWindowTitle("גישה נדחתה")
    msg.setText("יש לפתוח את לוח המודעות הדיגיטלי\nולהשתמש ב-F8 לפתיחת ממשק הניהול.")
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    msg.exec()
    sys.exit(1)

if __name__ == '__main__':
    main()
