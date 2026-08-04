#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════╗
║     לוח מודעות דיגיטלי  v4.5            ║
║     Digital Bulletin Board               ║
║     F8 = פתיחת ממשק ניהול               ║
╚══════════════════════════════════════════╝
"""
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog
from tkinter import font as tkFont
import json, os, sys, hashlib, math, time, copy, zipfile, shutil, tempfile
from datetime import datetime, date, timedelta
from pathlib import Path

PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    pass

PYLUACH_OK = False
try:
    from pyluach import dates as pyl_dates
    PYLUACH_OK = True
except ImportError:
    pass

ASTRAL_OK = False
try:
    from astral import LocationInfo
    from astral.sun import sun as astral_sun
    import pytz
    ASTRAL_OK = True
except ImportError:
    pass

ZMANIM_PKG_OK = False
try:
    from zmanim.zmanim_calendar import ZmanimCalendar
    from zmanim.util.geo_location import GeoLocation as ZmanimGeoLocation
    ZMANIM_PKG_OK = True
except ImportError:
    pass

APP  = "לוח מודעות דיגיטלי"
VER  = "4.5"
DATA = Path.home() / ".digital_bulletin"
CFG  = DATA / "config.json"
DATA.mkdir(exist_ok=True)

HEB_WDAYS  = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
# pyluach uses Nisan-first numbering: 1=ניסן … 7=תשרי … 12=אדר 13=אדר ב׳ (leap)
HEB_MONTHS = ["",
               "ניסן","אייר","סיוון","תמוז","אב","אלול",
               "תשרי","חשוון","כסלו","טבת","שבט","אדר",
               "אדר א\u05f3","אדר ב\u05f3"]

ZMANIM_KEYS = {
    "alot":           "עלות השחר",
    "misheyakir":     "משיכיר",
    "sunrise":        "הנץ החמה",
    "shma_mga":       "סוף ק\"ש — מג\"א",
    "shma_gra":       "סוף ק\"ש — גר\"א",
    "tfila_mga":      "סוף תפלה — מג\"א",
    "tfila_gra":      "סוף תפלה — גר\"א",
    "chatzot":        "חצות היום",
    "mincha_gedola":  "מנחה גדולה",
    "mincha_ketana":  "מנחה קטנה",
    "plag":           "פלג המנחה",
    "sunset":         "שקיעת החמה",
    "tzait_18":       "צאת הכוכבים (18 דק\u05f3)",
    "tzait_42":       "מוצ\"ש — רבינו תם",
}

def get_effective_zmanim_entries(cfg_d):
    """Return ordered list of (uid, key, display_name, method_override) from
    location.zmanim_keys_cfg, or fall back to ZMANIM_KEYS.
    uid is used as the identifier in show_items.
    method_override is "" (use global) or a specific method string."""
    loc = cfg_d.get("location", {}) if isinstance(cfg_d, dict) else {}
    entries = loc.get("zmanim_keys_cfg", None)
    if entries:
        result = []
        for e in entries:
            key = e.get("key", "")
            custom = e.get("custom_name", "").strip()
            name = custom if custom else ZMANIM_KEYS.get(key, key)
            result.append((e.get("uid", key), key, name, e.get("method", "")))
        return result
    # Fallback: default list, uid == key
    return [(k, k, v, "") for k, v in ZMANIM_KEYS.items()]

PANEL_NAMES = {
    "clock":      "שעה",
    "date":       "תאריך",
    "text":       "טקסט",
    "ad":         "מודעה / תמונות",
    "zmanim":     "זמני הלכה",
    "element":    "אלמנט עיצובי",
    "notice":     "הודעה צפה",
    "screen_msg": "הודעת מסך",
    "background": "רקע ראשי",
}

ANALOG_STYLES = ["classic", "minimal", "roman", "railway"]
ANALOG_STYLE_NAMES = {
    "classic":  "קלאסי",
    "minimal":  "מינימלי",
    "roman":    "ספרות רומיות",
    "railway":  "תחנת רכבת",
}

BG    = "#070714"
BG2   = "#0d0d22"
BG3   = "#13132e"
PNL   = "#111128"
BLUE  = "#3a7bd5"
LBLUE = "#5a9bf5"
GOLD  = "#f5a623"
GREEN = "#2ecc71"
RED   = "#e74c3c"
TEXT  = "#dde0ff"
TEXT2 = "#8888bb"
BTN   = "#1c2844"
BTN2  = "#263560"
INP   = "#181830"
SEP   = "#252545"

def _blend_tk(color, alpha, bg="#000000"):
    """Blend `color` with `bg` at the given alpha (0-255) and return a #RRGGBB
    string safe for Tkinter (which does NOT support 8-character hex colors)."""
    try:
        c = color.lstrip("#"); b = bg.lstrip("#")
        if len(c) < 6: c = c.ljust(6, "0")
        if len(b) < 6: b = b.ljust(6, "0")
        a = alpha / 255.0
        r = int(int(c[0:2],16)*a + int(b[0:2],16)*(1-a))
        g = int(int(c[2:4],16)*a + int(b[2:4],16)*(1-a))
        bv= int(int(c[4:6],16)*a + int(b[4:6],16)*(1-a))
        return f"#{r:02x}{g:02x}{bv:02x}"
    except:
        return "#" + color.lstrip("#")[:6]

# ── ערכת צבעים בהירה לממשק ניהול ─────────────────────────────────────────────
M_BG    = "#f2f5ff"   # light background
M_BG2   = "#e4e9f8"   # slightly darker
M_BG3   = "#d8dff2"   # panel bg
M_HDR   = "#1b2a6b"   # dark header
M_CARD  = "#ffffff"   # card / input bg
M_TEXT  = "#151c3a"   # main text
M_TEXT2 = "#4a5580"   # secondary text
M_BTN   = "#cdd5f0"   # button bg
M_BTN2  = "#b8c2e8"   # hovered button
M_INP   = "#ffffff"   # input field
M_SEP   = "#c2ccec"   # separator
M_BLUE  = "#2d5ec0"   # accent blue
M_LBLUE = "#4a7ae0"   # lighter blue
M_GREEN = "#1a9a5c"
M_RED   = "#cc2a2a"
M_GOLD  = "#c47a00"

# ── גימטריה ─────────────────────────────────────────────────────────────────
_GEM = {400:"ת",300:"ש",200:"ר",100:"ק",90:"צ",80:"פ",70:"ע",60:"ס",
        50:"נ",40:"מ",30:"ל",20:"כ",10:"י",9:"ט",8:"ח",7:"ז",6:"ו",
        5:"ה",4:"ד",3:"ג",2:"ב",1:"א"}

def _n2h(n):
    if n == 15: return "ט״ו"
    if n == 16: return "ט״ז"
    s = ""
    for v in sorted(_GEM, reverse=True):
        while n >= v: s += _GEM[v]; n -= v
    return (s[:-1]+"״"+s[-1]) if len(s)>1 else s+"׳"

def _y2h(y):
    r = y % 1000; s = ""
    for v in sorted(_GEM, reverse=True):
        while r >= v: s += _GEM[v]; r -= v
    return (s[:-1]+"״"+s[-1]) if len(s)>1 else s+"׳"

def get_heb_date(cfg_d=None):
    """Return Hebrew date tuple (y,m,d). Switches at sunset if configured."""
    if not PYLUACH_OK: return None
    try:
        today = get_today(cfg_d)
        switch = "sunset"
        if cfg_d:
            switch = cfg_d.get("time_settings", {}).get("hebrew_day_switch", "sunset")
        if switch == "sunset" and ASTRAL_OK and cfg_d:
            try:
                loc = cfg_d.get("location", {})
                tz_name = loc.get("tz", "Asia/Jerusalem")
                li = LocationInfo("loc","c",tz_name,
                                  loc.get("lat",31.7683), loc.get("lng",35.2137))
                tz_obj = pytz.timezone(tz_name)
                s = astral_sun(li.observer, date=today, tzinfo=tz_obj)
                sunset_local = s["sunset"].replace(tzinfo=None)
                if datetime.now() >= sunset_local:
                    today = today + timedelta(days=1)
            except: pass
        d = pyl_dates.HebrewDate.from_pydate(today)
        return (d.year, d.month, d.day)
    except: return None

def fmt_heb_date(y, m, d):
    mn = HEB_MONTHS[m] if 0 < m < len(HEB_MONTHS) else str(m)
    return f"{_n2h(d)} {mn} {_y2h(y)}"

def get_now(cfg_d=None):
    """Return current datetime, using manual override if configured in cfg_d."""
    if cfg_d:
        ts = cfg_d.get("time_settings", {})
        if ts.get("manual_time_enabled", False):
            try:
                from datetime import datetime as _dt
                dt_str = ts.get("manual_datetime", "")
                if dt_str:
                    return _dt.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except: pass
    return datetime.now()

def get_today(cfg_d=None):
    """Return current date, using manual override if configured in cfg_d."""
    return get_now(cfg_d).date()

def get_weekday_heb(cfg_d=None):
    idx = (get_today(cfg_d).weekday()+1) % 7
    return "יום " + HEB_WDAYS[idx]

def get_parasha(israel=True):
    """Return parasha name for current or next Shabbat, Hebrew string."""
    if not PYLUACH_OK: return ""
    try:
        from pyluach import parshios
        today = pyl_dates.HebrewDate.today()
        # Search up to 7 days forward for Shabbat parasha
        for i in range(7):
            d = today + i
            p = parshios.getparsha_string(d, israel=israel, hebrew=True)
            if p:
                return p
    except: pass
    return ""

def get_today_holiday(israel=True):
    """Return today's holiday name in Hebrew, or empty string."""
    if not PYLUACH_OK: return ""
    try:
        today = pyl_dates.HebrewDate.today()
        h = today.holiday(hebrew=True, israel=israel)
        return h if h else ""
    except: return ""

# ── הזכרות והוספות בתפילה ───────────────────────────────────────────────────
def get_prayer_additions(cfg_d=None):
    """Return dict of currently-relevant prayer additions (הזכרות).
    Keys: 'yaaleh_veyavo', 'morid_hatal', 'mashiv_haruach', 'vten_tal_umatar'
    Values: Hebrew label string if active, '' if not.
    """
    if not PYLUACH_OK:
        return {"yaaleh_veyavo":"","morid_hatal":"","mashiv_haruach":"","vten_tal_umatar":""}
    try:
        today = pyl_dates.HebrewDate.today()
        month = today.month   # pyluach Nisan-first: 7=Tishri, 1=Nisan
        day   = today.day

        # ── יעלה ויבוא: ראש חודש, יו"ט, חול המועד ──
        yaaleh = ""
        try:
            hol = today.holiday(hebrew=True, israel=True)
            if hol:
                yaaleh = "יעלה ויבוא"
        except: pass
        # גם ראש חודש (1 לכל חודש, ואין חג מסוים)
        if not yaaleh and day == 1:
            yaaleh = "יעלה ויבוא"
        # ל' תשרי = ב' ר"ח חשוון
        if not yaaleh and month == 7 and day == 30:
            yaaleh = "יעלה ויבוא"

        # ── גשם/טל ──
        # משיב הרוח ומוריד הגשם: מוסף של שמיני עצרת (22 תשרי) עד מוסף פסח (15 ניסן)
        # מוריד הטל: מוסף פסח עד שמיני עצרת
        # month 7=תשרי, 1=ניסן
        in_rain_period = (
            (month == 7 and day >= 22) or
            (month in (8, 9, 10, 11, 12)) or  # חשוון–אדר
            (month == 13) or  # אדר א׳
            (month == 1 and day < 15)   # ניסן לפני פסח
        )
        mashiv = "משיב הרוח ומוריד הגשם" if in_rain_period else ""
        morid_tal = "מוריד הטל" if not in_rain_period else ""

        # ── ותן טל ומטר לברכה: ז׳ חשוון (ישראל) עד ליל פסח ──
        # בישראל: מז' חשוון (month=8 day>=7) עד ט"ו ניסן (month=1 day<15)
        in_matar_period = (
            (month == 8 and day >= 7) or
            (month in (9, 10, 11, 12)) or
            (month == 13) or
            (month == 1 and day < 15)
        )
        vten_matar = "ותן טל ומטר לברכה" if in_matar_period else "ותן ברכה"

        return {
            "yaaleh_veyavo": yaaleh,
            "morid_hatal":   morid_tal,
            "mashiv_haruach": mashiv,
            "vten_tal_umatar": vten_matar,
        }
    except:
        return {"yaaleh_veyavo":"","morid_hatal":"","mashiv_haruach":"","vten_tal_umatar":""}


def get_torah_reading(israel=True):
    """Return (parasha_label, haftara_label) for today if there's a Torah reading, else ('','')."""
    if not PYLUACH_OK: return ("", "")
    try:
        from pyluach import parshios
        today = pyl_dates.HebrewDate.today()
        # Check if today is Shabbat (weekday 7 in pyluach)
        wd = today.weekday()  # 1=Sunday … 7=Shabbat
        # Search: if today is Shabbat check today; else find upcoming Shabbat's reading
        check_d = today if wd == 7 else None
        # Also check Yom Tov readings (holiday today)
        hol = today.holiday(hebrew=True, israel=israel)
        if hol:
            par = parshios.getparsha_string(today, israel=israel, hebrew=True)
            if par:
                return (f"קריאת התורה: {par}", f"מועד: {hol}")
        if check_d:
            par = parshios.getparsha_string(check_d, israel=israel, hebrew=True)
            if par:
                return (f"קריאת השבוע: {par}", "")
        return ("", "")
    except:
        return ("", "")


def get_daf_yomi():
    """Return current Daf Yomi (Bavli) as Hebrew string, e.g. 'ברכות ב'."""
    try:
        # Daf Yomi cycle: cycle 14 started 5 Jan 2020 (Julian day number)
        import math as _math
        epoch = date(2020, 1, 5)  # Daf 1 of cycle 14 = Niddah 73 (actually Berachot 2)
        # Use a fixed epoch: 5 Jan 2020 = Berachot 2 (daf index 0)
        today_d = date.today()
        delta = (today_d - epoch).days % 2711  # 2711 = total daf in cycle
        if delta < 0: delta += 2711

        # Tractate list with daf counts (starting from daf 2, so pages = amudim/2 rounded up)
        TRACTATES = [
            ("ברכות", 63), ("שבת", 156), ("עירובין", 104), ("פסחים", 120),
            ("שקלים", 21), ("יומא", 87), ("סוכה", 55), ("ביצה", 39),
            ("ראש השנה", 34), ("תענית", 30), ("מגילה", 31), ("מועד קטן", 28),
            ("חגיגה", 26), ("יבמות", 121), ("כתובות", 111), ("נדרים", 90),
            ("נזיר", 65), ("סוטה", 48), ("גיטין", 89), ("קידושין", 81),
            ("בבא קמא", 118), ("בבא מציעא", 118), ("בבא בתרא", 175),
            ("סנהדרין", 112), ("מכות", 23), ("שבועות", 48), ("עבודה זרה", 75),
            ("הוריות", 13), ("זבחים", 119), ("מנחות", 109), ("חולין", 141),
            ("בכורות", 60), ("ערכין", 33), ("תמורה", 33), ("כריתות", 27),
            ("מעילה", 21), ("קינים", 3), ("תמיד", 9), ("מידות", 4),
            ("נדה", 72),
        ]
        # Map delta → tractate + daf
        # Daf 2 = index 0 in each tractate; pages per masechet = (last_daf - 1)
        HEB_NUMS = ["","א","ב","ג","ד","ה","ו","ז","ח","ט","י","יא","יב","יג","יד","טו",
                    "טז","יז","יח","יט","כ","כא","כב","כג","כד","כה","כו","כז","כח","כט","ל",
                    "לא","לב","לג","לד","לה","לו","לז","לח","לט","מ","מא","מב","מג","מד","מה",
                    "מו","מז","מח","מט","נ","נא","נב","נג","נד","נה","נו","נז","נח","נט","ס",
                    "סא","סב","סג","סד","סה","סו","סז","סח","סט","ע","עא","עב","עג","עד","עה",
                    "עו","עז","עח","עט","פ","פא","פב","פג","פד","פה","פו","פז","פח","פט","צ",
                    "צא","צב","צג","צד","צה","צו","צז","צח","צט","ק","קא","קב","קג","קד","קה",
                    "קו","קז","קח","קט","קי","קיא","קיב","קיג","קיד","קטו","קטז","קיז","קיח",
                    "קיט","קכ","קכא","קכב","קכג","קכד","קכה","קכו","קכז","קכח","קכט","קל",
                    "קלא","קלב","קלג","קלד","קלה","קלו","קלז","קלח","קלט","קמ","קמא","קמב",
                    "קמג","קמד","קמה","קמו","קמז","קמח","קמט","קנ","קנא","קנב","קנג","קנד",
                    "קנה","קנו","קנז","קנח","קנט","קס","קסא","קסב","קסג","קסד","קסה","קסו",
                    "קסז","קסח","קסט","קע","קעא","קעב","קעג","קעד","קעה"]
        remaining = delta
        for name, pages in TRACTATES:
            if remaining < pages:
                daf_num = remaining + 2  # daf 2-based
                daf_heb = HEB_NUMS[daf_num] if daf_num < len(HEB_NUMS) else str(daf_num)
                return f"דף יומי: {name} {daf_heb}"
            remaining -= pages
        return ""
    except:
        return ""

# ── חישוב זמני הלכה ─────────────────────────────────────────────────────────
class ZmanimCalc:
    """Calculates halachic times. Supports two methods:
    - 'kosherzmanim': uses the zmanim Python package (most accurate, recommended)
    - 'astral': uses astral/pytz (built-in fallback)
    The method is selected via cfg_d['location']['zmanim_method'] or passed directly.
    """
    def __init__(self, lat, lng, elev=0, tz="Asia/Jerusalem", method=None):
        self.lat=lat; self.lng=lng; self.elev=elev; self.tz=tz
        # method: 'kosherzmanim' or 'astral'
        self.method = method  # None = auto-select best available

    def calc(self, d=None):
        if d is None: d = date.today()
        method = self.method
        if method is None:
            method = "kosherzmanim" if ZMANIM_PKG_OK else ("astral" if ASTRAL_OK else "manual")
        if method == "kosherzmanim" and ZMANIM_PKG_OK:
            result = self._kosherzmanim(d)
            if result: return result
        if method != "manual" and ASTRAL_OK:
            return self._astral(d)
        return self._manual(d)

    def _kosherzmanim(self, d):
        """Calculate using the zmanim Python package (KosherJava port — most accurate)."""
        try:
            geo = ZmanimGeoLocation("loc", self.lat, self.lng,
                                    time_zone=self.tz, elevation=self.elev)
            cal = ZmanimCalendar(geo_location=geo, date=d)
            def _dt(t):
                """Convert zmanim result to naive local datetime."""
                if t is None: return None
                import pytz as _pytz
                tz_obj = _pytz.timezone(self.tz)
                if hasattr(t, 'tzinfo') and t.tzinfo:
                    return t.astimezone(tz_obj).replace(tzinfo=None)
                return t
            sr = _dt(cal.sunrise())
            ss = _dt(cal.sunset())
            if sr is None or ss is None: return None
            return {
                "alot":          _dt(cal.alos_72()),
                "misheyakir":    _dt(cal.alos()) or (sr - timedelta(minutes=36)),
                "sunrise":       sr,
                "shma_gra":      _dt(cal.sof_zman_shma_gra()),
                "shma_mga":      _dt(cal.sof_zman_shma_mga()),
                "tfila_gra":     _dt(cal.sof_zman_tfila_gra()),
                "tfila_mga":     _dt(cal.sof_zman_tfila_mga()),
                "chatzot":       _dt(cal.chatzos()),
                "mincha_gedola": _dt(cal.mincha_gedola()),
                "mincha_ketana": _dt(cal.mincha_ketana()),
                "plag":          _dt(cal.plag_hamincha()),
                "sunset":        ss,
                "tzait_18":      ss + timedelta(minutes=18),
                "tzait_42":      _dt(cal.tzais_72()),
            }
        except Exception as _e:
            import traceback; traceback.print_exc()
            return None

    def _astral(self, d):
        try:
            tz_obj = pytz.timezone(self.tz)
            loc = LocationInfo("loc","c",self.tz,self.lat,self.lng)
            s = astral_sun(loc.observer, date=d, tzinfo=tz_obj)
            sr = s["sunrise"]; ss = s["sunset"]
            day_sec = (ss-sr).total_seconds()
            sha_gra  = day_sec / 12
            alot     = sr - timedelta(minutes=72)
            sha_mga  = (ss-alot).total_seconds() / 12
            return {
                "alot":          alot,
                "misheyakir":    sr - timedelta(minutes=36),
                "sunrise":       sr,
                "shma_gra":      sr   + timedelta(seconds=sha_gra*3),
                "shma_mga":      alot + timedelta(seconds=sha_mga*3),
                "tfila_gra":     sr   + timedelta(seconds=sha_gra*4),
                "tfila_mga":     alot + timedelta(seconds=sha_mga*4),
                "chatzot":       sr   + timedelta(seconds=sha_gra*6),
                "mincha_gedola": sr   + timedelta(seconds=sha_gra*6.5),
                "mincha_ketana": sr   + timedelta(seconds=sha_gra*9.5),
                "plag":          sr   + timedelta(seconds=sha_gra*10.75),
                "sunset":        ss,
                "tzait_18":      ss   + timedelta(minutes=18),
                "tzait_42":      ss   + timedelta(minutes=42),
            }
        except: return self._manual(d)

    def _manual(self, d):
        doy=d.timetuple().tm_yday
        decl=math.radians(23.45*math.sin(math.radians(360/365*(doy-80))))
        lr=math.radians(self.lat)
        csh=-math.tan(lr)*math.tan(decl)
        if abs(csh)>1: return {}
        ha=math.degrees(math.acos(csh))
        B=math.radians(360/365*(doy-81))
        eot=(9.87*math.sin(2*B)-7.53*math.cos(B)-1.5*math.sin(B))/60
        noon_utc=12-self.lng/15-eot
        utc_off=3 if 3<d.month<11 else 2
        base=datetime(d.year,d.month,d.day)
        sr=base+timedelta(hours=noon_utc-ha/15+utc_off)
        ss=base+timedelta(hours=noon_utc+ha/15+utc_off)
        day_sec=(ss-sr).total_seconds(); sha=day_sec/12
        alot=sr-timedelta(minutes=72)
        sha_mga=(ss-alot).total_seconds()/12
        return {
            "alot":alot, "misheyakir":sr-timedelta(minutes=36),
            "sunrise":sr,
            "shma_gra":      sr+timedelta(seconds=sha*3),
            "shma_mga":      alot+timedelta(seconds=sha_mga*3),
            "tfila_gra":     sr+timedelta(seconds=sha*4),
            "tfila_mga":     alot+timedelta(seconds=sha_mga*4),
            "chatzot":       sr+timedelta(seconds=sha*6),
            "mincha_gedola": sr+timedelta(seconds=sha*6.5),
            "mincha_ketana": sr+timedelta(seconds=sha*9.5),
            "plag":          sr+timedelta(seconds=sha*10.75),
            "sunset":        ss,
            "tzait_18":      ss+timedelta(minutes=18),
            "tzait_42":      ss+timedelta(minutes=42),
        }

def _make_zmanim_calc(cfg_d):
    """Create ZmanimCalc from config, respecting zmanim_method setting."""
    loc = cfg_d.get("location", {})
    method = cfg_d.get("location", {}).get("zmanim_method", None)
    return ZmanimCalc(loc.get("lat",31.7683), loc.get("lng",35.2137),
                      loc.get("elev",0), loc.get("tz","Asia/Jerusalem"),
                      method=method)


# ── ברירות מחדל לתצורת לוחות ────────────────────────────────────────────────
_BASE = dict(
    enabled=True, x=20, y=20, width=350, height=180,
    bg_color=PNL, bg_transparent=False, bg_image="",
    border_color=BLUE, border_width=2, border_transparent=False,
    layer=1,
    pad_top=0, pad_bottom=0, pad_left=0, pad_right=0,
)
_DEFS = {
  "clock":  {**_BASE,"type":"clock","width":280,"height":120,
             "show_seconds":True,"clock_style":"digital","time_format":"24",
             "analog_style":"classic",
             "font_color":BLUE,"font_family":"Arial","font_size":56},
  "date":   {**_BASE,"type":"date","width":280,"height":160,
             "show_heb_date":True,"show_greg_date":True,
             "show_holiday":True,"show_parasha":True,"israel":True,
             "font_color":TEXT,"font_family":"Arial","font_size":18},
  "time":   {**_BASE,"type":"time","width":420,"height":240,
             "show_time":True,"show_seconds":True,
             "show_weekday":True,"show_heb_date":True,"show_greg_date":True,
             "show_holiday":True,"show_parasha":True,"israel":True,
             "clock_style":"digital","time_format":"24",
             "clock_color":BLUE,"date_color":TEXT,
             "font_family":"Arial","time_font_size":56,"date_font_size":18},
  "text":   {**_BASE,"type":"text","height":180,
             "content":"לוח מודעות דיגיטלי\nהוסף את הטקסט שלך כאן",
             "font_family":"Arial","font_size":20,"font_color":"#ffffff",
             "bold":False,"italic":False,"align":"right","padding":14,
             "scroll_mode":"scroll_up","scroll_speed":30,"segment_duration":5,
             "seg_separator_space":True,"seg_separator_char":""},
  "ad":     {**_BASE,"type":"ad","width":380,"height":280,
             "images":[],"interval":5,"fit_mode":"contain"},
  "zmanim": {**_BASE,"type":"zmanim","width":360,"height":490,
             "show_items":["alot","sunrise","shma_mga","shma_gra","tfila_mga","tfila_gra",
                           "chatzot","mincha_gedola","mincha_ketana","plag",
                           "sunset","tzait_18","tzait_42"],
             "title":"זמני היום","show_title":True,
             "font_family":"Arial","font_size":14,
             "label_color":"#9090cc","time_color":BLUE,
             "highlight_color":GOLD,"highlight_next":True},
  "element":{**_BASE,"type":"element","width":200,"height":200,
             "bg_transparent":True,"border_width":0,"border_transparent":True,
             "image_path":"","fit_mode":"contain"},
  "notice": {**_BASE,"type":"notice","width":900,"height":80,
             "y":620,"bg_color":"#1a0a00","border_color":GOLD,"border_width":3,
             "content":"הודעה חשובה — ניתן לערוך טקסט זה בממשק הניהול",
             "font_family":"Arial","font_size":26,"font_color":GOLD,
             "bold":True,"scroll":True,"scroll_speed":2,"scroll_dir":"rtl",
             "popup_only":True,"popup_duration":30},
  "screen_msg":{**_BASE,"type":"screen_msg","width":600,"height":140,
             "x":160,"y":460,"bg_color":"#0d0d22","border_color":GOLD,"border_width":3,
             "content":"הודעה — ניתן לערוך בממשק הניהול",
             "font_family":"Arial","font_size":28,"font_color":GOLD,
             "bold":True,"italic":False,"align":"center","padding":16,
             "scroll_mode":"static"},
  "_schedule":{**_BASE,"type":"_schedule","width":350,"height":200,
             "events":[],"empty_text":"אין אירועים",
             "font_family":"Arial","font_size":20,"font_color":"#ffffff",
             "bold":False,"italic":False,"align":"right","padding":14,
             "name_font_family":"Arial","name_font_size":20,"name_font_color":"#ffffff",
             "time_font_family":"Arial","time_font_size":20,"time_font_color":"#aaddff",
             "day_rollover_hour":0,"day_rollover_minute":0},
}

# The background panel is a singleton stored under "display" — not in panels list
_DEF_DISPLAY = {
    "type":"background","id":0,"enabled":True,"layer":3,
    "bg_color":BG,"bg_image":"",
    "show_stars":True,"gradient":True,
    "screen_margin_top":0,"screen_margin_bottom":0,
    "screen_margin_left":0,"screen_margin_right":0,
}

_DEF_CFG = {
    "password_hash":"",
    "location":{"city":"ירושלים",
                "lat":31.7683,"lng":35.2137,"elev":754,"tz":"Asia/Jerusalem",
                "zmanim_method":"kosherzmanim"},
    "display":{**_DEF_DISPLAY},
    "display_boards":[],   # additional background boards; each is a display-like dict with schedule
    "panels":[], "_nid":1,
    "reminders":[],
    "fullscreen_msg":{
        "bg_color":"#060015","font_color":GOLD,
        "font_size":48,"content":"","duration":0,
    },
}

# ── ניהול תצורה ─────────────────────────────────────────────────────────────
class Config:
    def __init__(self): self.d = self._load()

    def _load(self):
        # Try main config, then backup
        for path in [CFG, CFG.with_suffix(".bak")]:
            if path.exists():
                try:
                    with open(path,"r",encoding="utf-8") as f: raw=json.load(f)
                    base=copy.deepcopy(_DEF_CFG); self._merge(base,raw); return base
                except: pass
        return copy.deepcopy(_DEF_CFG)

    def _merge(self,b,o):
        for k,v in o.items():
            if k in b and isinstance(b[k],dict) and isinstance(v,dict):
                self._merge(b[k],v)
            else: b[k]=v

    def save(self):
        """Atomic save: write to .tmp, keep .bak of last good save, then rename."""
        tmp = CFG.with_suffix(".tmp")
        try:
            with open(tmp,"w",encoding="utf-8") as f:
                json.dump(self.d,f,ensure_ascii=False,indent=2)
            # Keep previous good config as backup
            if CFG.exists():
                try: CFG.replace(CFG.with_suffix(".bak"))
                except: pass
            tmp.replace(CFG)
        except Exception as e:
            try: tmp.unlink(missing_ok=True)
            except: pass

    def check_pw(self,pw):
        h=self.d.get("password_hash","")
        return (not h) or hashlib.sha256(pw.encode()).hexdigest()==h

    def has_pw(self): return bool(self.d.get("password_hash",""))

    def set_pw(self,pw):
        self.d["password_hash"]=hashlib.sha256(pw.encode()).hexdigest() if pw else ""
        self.save()

    def new_id(self):
        i=self.d.get("_nid",1); self.d["_nid"]=i+1; return i

    def add_panel(self,pt):
        p=copy.deepcopy(_DEFS.get(pt,{**_BASE,"type":pt}))
        p["id"]=self.new_id(); p["type"]=pt
        same=[x for x in self.d["panels"] if x.get("type")==pt]
        p["x"]=20+len(same)*30; p["y"]=20+len(same)*30
        self.d["panels"].append(p); self.save(); return p

    def del_panel(self,pid):
        self.d["panels"]=[p for p in self.d["panels"] if p.get("id")!=pid]
        self.save()

    def upd_panel(self,pid,data):
        for i,p in enumerate(self.d["panels"]):
            if p.get("id")==pid:
                self.d["panels"][i].update(data); self.save(); return

    def get_panel(self,pid):
        for p in self.d["panels"]:
            if p.get("id")==pid: return p
        return None

    def reminders(self): return self.d.setdefault("reminders",[])

    def add_reminder(self,text,rem_type="personal",dt_str="",
                     zman="",offset_min=0,days=None,skip_shabbat=True,
                     skip_holidays=False,recurring="none",
                     notify_visual=True,notify_sound=False,notice_panel_id=None,
                     sound_type="beep",sound_file=""):
        rem=self.reminders()
        nid=max((r.get("id",0) for r in rem),default=0)+1
        rem.append({
            "id":nid,"text":text,"rem_type":rem_type,
            "dt":dt_str,"zman":zman,"offset_min":offset_min,
            "days":days if days is not None else list(range(7)),
            "skip_shabbat":skip_shabbat,"skip_holidays":skip_holidays,
            "recurring":recurring,
            "notify_visual":notify_visual,"notify_sound":notify_sound,
            "notice_panel_id":notice_panel_id,
            "sound_type":sound_type,"sound_file":sound_file,
            "done":False,"last_triggered":"",
        })
        self.save(); return nid

    def del_reminder(self,rid):
        self.d["reminders"]=[r for r in self.reminders() if r.get("id")!=rid]
        self.save()

    def mark_reminder(self,rid,done=True):
        for r in self.reminders():
            if r.get("id")==rid: r["done"]=done; break
        self.save()

    # ── יצוא/יבוא פריסה ────────────────────────────────────────────────────
    def export_layout_zip(self,dest_path):
        """Export layout (ALL design settings + design images) to ZIP file.
        Excludes only: content text and ad image lists (those are content, not design).
        Ad images themselves are exported if they exist."""
        export_panels=[]
        design_imgs=set()
        # Keys that are "content" (excluded from layout export)
        CONTENT_KEYS = {"content"}

        for p in self.d.get("panels",[]):
            ep={k:v for k,v in p.items() if k not in CONTENT_KEYS}
            # Handle single-file design image paths
            for img_key in ("bg_image","image_path"):
                if ep.get(img_key) and os.path.exists(ep[img_key]):
                    design_imgs.add(ep[img_key])
                    ep[img_key]="images/"+os.path.basename(ep[img_key])
            # Handle ad images list — export files, rewrite paths
            fixed_imgs=[]
            for entry in ep.get("images",[]):
                if isinstance(entry,str):
                    img_path=entry; meta={}
                elif isinstance(entry,dict):
                    img_path=entry.get("path",""); meta={k:v for k,v in entry.items() if k!="path"}
                else: continue
                if img_path and os.path.exists(img_path):
                    design_imgs.add(img_path)
                    fixed_imgs.append(dict(meta,path="images/"+os.path.basename(img_path)))
                else:
                    fixed_imgs.append(entry)
            ep["images"]=fixed_imgs
            export_panels.append(ep)

        disp=dict(self.d["display"])
        if disp.get("bg_image") and os.path.exists(disp["bg_image"]):
            design_imgs.add(disp["bg_image"])
            disp["bg_image"]="images/"+os.path.basename(disp["bg_image"])

        export_cfg={"display":disp,"panels":export_panels,"_nid":self.d.get("_nid",1)}

        with zipfile.ZipFile(dest_path,"w",zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("layout.json",json.dumps(export_cfg,ensure_ascii=False,indent=2))
            for img_path in design_imgs:
                zf.write(img_path,"images/"+os.path.basename(img_path))
        return len(design_imgs)

    def import_layout_zip(self,zip_path):
        """Import layout from ZIP. Images are extracted to DATA dir."""
        img_dir=DATA/"layout_images"; img_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path,"r") as zf:
            cfg_str=zf.read("layout.json").decode("utf-8")
            layout=json.loads(cfg_str)
            # Extract images
            for name in zf.namelist():
                if name.startswith("images/") and name!="images/":
                    dest=img_dir/os.path.basename(name)
                    with zf.open(name) as src, open(dest,"wb") as dst:
                        dst.write(src.read())
        # Rewrite image paths to local
        def fix_path(p):
            if p and p.startswith("images/"):
                return str(img_dir/os.path.basename(p))
            return p
        for p in layout.get("panels",[]):
            for k in ("bg_image","image_path"):
                if p.get(k): p[k]=fix_path(p[k])
            # Fix images list paths (ad panels) — entries may be dicts or strings
            fixed=[]
            for entry in p.get("images",[]):
                if isinstance(entry,str):
                    fixed.append(fix_path(entry))
                elif isinstance(entry,dict):
                    fixed.append(dict(entry,path=fix_path(entry.get("path",""))))
                else:
                    fixed.append(entry)
            p["images"]=fixed
        if layout.get("display",{}).get("bg_image"):
            layout["display"]["bg_image"]=fix_path(layout["display"]["bg_image"])
        # Merge into current config (keep location/password/reminders)
        self.d["display"].update(layout.get("display",{}))
        self.d["panels"]=layout.get("panels",[])
        self.d["_nid"]=layout.get("_nid",1)
        self.save()

    def export_settings(self,dest_path):
        """Export location + display settings (no password hash) to JSON."""
        s={"location":self.d["location"],"display":self.d["display"]}
        with open(dest_path,"w",encoding="utf-8") as f:
            json.dump(s,f,ensure_ascii=False,indent=2)

    def import_settings(self,src_path):
        """Import location + display settings from JSON."""
        with open(src_path,"r",encoding="utf-8") as f:
            s=json.load(f)
        if "location" in s: self.d["location"].update(s["location"])
        if "display" in s: self.d["display"].update(s["display"])
        self.save()

_JEWISH_HOLIDAYS = [
    ("שבת",       "shabbat",   []),
    ("ראש השנה",  "rosh_hashana",  [(7,1),(7,2)]),
    ("יום כיפור", "yom_kippur",    [(7,10)]),
    ("סוכות",     "sukkot",        [(7,15),(7,16),(7,17),(7,18),(7,19),(7,20),(7,21)]),
    ("שמיני עצרת / שמחת תורה", "shmini_atzeret", [(7,22),(7,23)]),
    ("חנוכה",     "chanuka",       [(9,25),(9,26),(9,27),(9,28),(9,29),(9,30),(10,1),(10,2),(10,3)]),
    ("פורים",     "purim",         [(12,14),(12,15)]),
    ("פסח",       "pesach",        [(1,15),(1,16),(1,17),(1,18),(1,19),(1,20),(1,21),(1,22)]),
    ("שבועות",    "shavuot",       [(3,6),(3,7)]),
    ("ראש חודש",  "rosh_chodesh",  []),
    ("תשעה באב",  "tisha_beav",    [(5,9)]),
    ("יום העצמאות","yom_haatzmaut",[(2,5)]),
]

def _schedule_active(sched_cfg, now=None):
    """Return True if the given schedule dict says the item is active right now.
    sched_cfg keys: hours_enabled, hour_from, hour_to, days_enabled, active_days (list 0-6).
    Returns True when no schedule is defined (i.e. always active)."""
    if not sched_cfg:
        return True
    if now is None:
        now = datetime.now()
    # Days check
    if sched_cfg.get("days_enabled", False):
        active_days = sched_cfg.get("active_days", list(range(7)))
        if now.weekday() not in active_days:
            return False
    # Hours check
    if sched_cfg.get("hours_enabled", False):
        h_from = sched_cfg.get("hour_from", 0)
        h_to   = sched_cfg.get("hour_to",  23)
        cur    = now.hour * 60 + now.minute
        f_min  = h_from * 60
        t_min  = h_to   * 60
        if f_min <= t_min:
            if not (f_min <= cur <= t_min):
                return False
        else:
            # overnight range
            if not (cur >= f_min or cur <= t_min):
                return False
    return True


def _get_pads(p, default=0):
    """Return (pad_top, pad_bottom, pad_left, pad_right) for a panel config.
    Uses directional keys pad_top/bottom/left/right if set (>=0), else falls
    back to the legacy symmetric 'padding' key, then to *default*."""
    sym = p.get("padding", default)
    pt = int(p.get("pad_top",    sym))
    pb = int(p.get("pad_bottom", sym))
    pl = int(p.get("pad_left",   sym))
    pr = int(p.get("pad_right",  sym))
    return pt, pb, pl, pr


def _get_active_display(cfg_d, preview_board_id=None):
    """Return the effective display-board config dict to use right now.
    If preview_board_id is set, return that board (for live preview in manager).
    Otherwise, pick the first board whose schedule is active, falling back to 'display'."""
    boards = cfg_d.get("display_boards", [])
    if preview_board_id is not None:
        if preview_board_id == "__default__":
            return cfg_d.get("display", {})
        for b in boards:
            if b.get("id") == preview_board_id:
                return b
        return cfg_d.get("display", {})
    now = datetime.now()
    for b in boards:
        if not b.get("enabled", True):
            continue
        sched = b.get("schedule", {})
        if _schedule_active(sched, now):
            return b
    return cfg_d.get("display", {})


# ── חלון תצוגה ──────────────────────────────────────────────────────────────
class DisplayWin:
    def __init__(self, app):
        self.app=app; self.cfg=app.cfg; self.panels={}
        self._preview_board_id=None   # set by manager for live preview
        self.root=tk.Tk()
        self.root.title(APP)
        self.root.attributes("-fullscreen",True)
        self.root.attributes("-topmost",True)
        _disp = _get_active_display(self.cfg.d)
        self.root.configure(bg=_disp.get("bg_color",BG))
        self.root.bind_all("<F8>", lambda e: self.app.open_mgr())
        self.root.bind_all("<F9>", lambda e: None)
        self.root.protocol("WM_DELETE_WINDOW", lambda:None)
        self.W=self.root.winfo_screenwidth()
        self.H=self.root.winfo_screenheight()
        self.bg_canvas=tk.Canvas(self.root,width=self.W,height=self.H,
                                  bg=_disp.get("bg_color",BG),
                                  highlightthickness=0)
        self.bg_canvas.place(x=0,y=0)
        self._bg_ref=None
        self._draw_bg()
        self._setup_panels()
        self._tick()

    def _draw_bg(self):
        disp=_get_active_display(self.cfg.d, self._preview_board_id)
        bgc=disp.get("bg_color",BG)
        self.root.configure(bg=bgc)
        self.bg_canvas.configure(bg=bgc)
        self.bg_canvas.delete("bg_layer")

        # Parse bg_color for gradient use
        try:
            _hx=bgc.lstrip("#")
            bg_r=int(_hx[0:2],16); bg_g=int(_hx[2:4],16); bg_b=int(_hx[4:6],16)
        except: bg_r,bg_g,bg_b=7,7,20

        if disp.get("gradient",True):
            steps=50
            for i in range(steps):
                t=i/steps
                # Gradient from bg_color (top) → slightly darker/deeper version (bottom)
                r=max(0,int(bg_r*(1-t*0.35)))
                g=max(0,int(bg_g*(1-t*0.35)))
                b=min(255,int(bg_b+(255-bg_b)*t*0.12))
                c=f"#{r:02x}{g:02x}{b:02x}"
                y0=int(t*self.H); y1=int((t+1/steps)*self.H+2)
                self.bg_canvas.create_rectangle(0,y0,self.W,y1,fill=c,outline="",tags="bg_layer")
        else:
            self.bg_canvas.create_rectangle(0,0,self.W,self.H,fill=bgc,outline="",tags="bg_layer")

        if disp.get("show_stars",True):
            import random; random.seed(42)
            for _ in range(120):
                x=random.randint(0,self.W); y=random.randint(0,self.H)
                br=random.randint(80,180); s=random.randint(1,2)
                c=f"#{br:02x}{br:02x}{min(255,br+40):02x}"
                self.bg_canvas.create_oval(x-s,y-s,x+s,y+s,fill=c,outline="",tags="bg_layer")

        bg_img=disp.get("bg_image","")
        if bg_img and os.path.exists(bg_img) and PIL_AVAILABLE:
            try:
                img=Image.open(bg_img).resize((self.W,self.H),Image.LANCZOS)
                self._bg_ref=ImageTk.PhotoImage(img)
                self.bg_canvas.create_image(0,0,anchor="nw",image=self._bg_ref,tags="bg_layer")
            except: pass

        # Lower all bg items so panels stay on top
        self.bg_canvas.tag_lower("bg_layer")
        # Render background to PIL for transparent-panel compositing
        self._render_bg_to_pil()
        # ── Version watermark — always on top of bg, below panels ──
        self._draw_version_watermark()

    def _draw_version_watermark(self):
        """Draw app name + version at bottom-center, white text with dark outline.
        Uses RLM + LRM to ensure: Hebrew name first, then version number (left-to-right)."""
        self.bg_canvas.delete("version_watermark")
        # \u200f = RLM (sets base direction RTL for Hebrew), \u200e = LRM (forces version number LTR after)
        lbl = f"\u200fלוח מודעות דיגיטלי \u200e{VER}"
        cx = self.W // 2
        cy = self.H - 14
        fs = 11
        # Dark outline: draw text shifted in 4 cardinal directions
        for dx, dy in [(0,-1),(1,0),(0,1),(-1,0)]:
            self.bg_canvas.create_text(cx+dx, cy+dy, text=lbl,
                font=("Arial", fs), fill="#000000",
                anchor="s", tags="version_watermark")
        # White foreground text
        self.bg_canvas.create_text(cx, cy, text=lbl,
            font=("Arial", fs), fill="#ffffff",
            anchor="s", tags="version_watermark")
        # Raise watermark to the very top (above all panels)
        self.bg_canvas.tag_raise("version_watermark")

    def _setup_panels(self):
        # Preserve active popup reminder panels before clearing (they survive refresh)
        active_popup_cids = set(cid for _, _, cid in getattr(self, "_active_popups", {}).values())

        # Destroy old panel widgets and canvas windows (but not popup reminder panels)
        # Also delete any direct-canvas items from transparent panels
        for wid in getattr(self,"_panel_cids",{}).values():
            if wid in active_popup_cids: continue  # keep popup
            try: self.bg_canvas.delete(wid)
            except: pass
        # Delete direct-canvas tag groups for transparent panels
        for pid in list(getattr(self, "_direct_canvas_ids", {})):
            try: self.bg_canvas.delete(f"dpanel_{pid}")
            except: pass
        for pw in self.panels.values():
            try: pw.destroy()
            except: pass
        self.panels.clear()
        self._panel_cids={}
        self._panel_dims={}
        self._direct_canvas_ids = {}   # pid → set of canvas item ids (for direct-rendered panels)

        # Determine active board id
        active_board = _get_active_display(self.cfg.d, self._preview_board_id)
        active_board_id = active_board.get("id", "__default__")   # "__default__" = main display

        # Sort panels: layer 3 (bottom) first → layer 1 (top) last
        sorted_panels=sorted(
            self.cfg.d.get("panels",[]),
            key=lambda p: -(p.get("layer",1))
        )

        # Compute responsive scale factors if design resolution differs from current screen
        disp_cfg = self.cfg.d.get("display",{})
        dw = disp_cfg.get("design_width", 0)
        dh = disp_cfg.get("design_height", 0)
        if dw > 0 and dh > 0 and (dw != self.W or dh != self.H):
            sx = self.W / dw; sy = self.H / dh
        else:
            sx = sy = 1.0

        # Screen margins: panels are clamped to this safe area
        _sm_top    = int(disp_cfg.get("screen_margin_top",    0))
        _sm_bottom = int(disp_cfg.get("screen_margin_bottom", 0))
        _sm_left   = int(disp_cfg.get("screen_margin_left",   0))
        _sm_right  = int(disp_cfg.get("screen_margin_right",  0))

        # Store popup-only panel configs (notice panels used only for reminder popups)
        self._popup_configs = {
            pc["id"]: pc for pc in sorted_panels
            if pc.get("type") == "notice" and pc.get("popup_only", False)
        }

        now = datetime.now()
        for pc in sorted_panels:
            if not pc.get("enabled",True): continue
            # Skip popup-only notice panels — they are shown only when reminders fire
            if pc.get("type") == "notice" and pc.get("popup_only", False): continue
            # Filter by board assignment (panels with no assignment show on all boards)
            panel_board = pc.get("board_id", "__all__")
            if panel_board not in ("__all__", active_board_id):
                continue
            # Filter by panel schedule
            if not _schedule_active(pc.get("panel_schedule", {}), now):
                continue
            # Apply responsive scaling (non-destructive – original config untouched)
            if sx != 1.0 or sy != 1.0:
                rpc = dict(pc)
                rpc["x"]      = int(pc.get("x",0)      * sx)
                rpc["y"]      = int(pc.get("y",0)      * sy)
                rpc["width"]  = int(pc.get("width",300) * sx)
                rpc["height"] = int(pc.get("height",200)* sy)
                rpc["font_size"]       = max(8, int(pc.get("font_size",14)       * min(sx,sy)))
                rpc["time_font_size"]  = max(8, int(pc.get("time_font_size",42)  * min(sx,sy)))
                rpc["date_font_size"]  = max(6, int(pc.get("date_font_size",18)  * min(sx,sy)))
            else:
                rpc = pc

            pid = pc["id"]
            px = rpc.get("x",10); py = rpc.get("y",10)
            pw_ = rpc.get("width",300); ph_ = rpc.get("height",200)

            # Clamp to screen safe area defined by screen margins
            max_x = self.W - _sm_right  - pw_
            max_y = self.H - _sm_bottom - ph_
            px = max(_sm_left, min(px, max_x))
            py = max(_sm_top,  min(py, max_y))

            # Transparent panels: draw directly on bg_canvas (true transparency)
            # EXCEPTION: text/screen_msg panels with transparent bg use CanvasBackedPanel
            # (widget-based) so their content is clipped naturally without stencil interference.
            # bg_image panels (non-transparent): also use DirectCanvasPanel (image covers bg_color)
            is_transparent = rpc.get("bg_transparent", False)
            has_bg_img = (not is_transparent and bool(rpc.get("bg_image","")) and
                          os.path.exists(rpc.get("bg_image","") or "") and PIL_AVAILABLE)
            use_direct = is_transparent or has_bg_img
            # Text panels with transparent/image bg → widget path (TransparentTextPW)
            # Ad panels with transparent bg → widget path (TransparentAdPW)
            if use_direct and rpc.get("type") in ("text", "screen_msg", "ad") and is_transparent:
                use_direct = False

            if use_direct:
                dcp = self._mk_direct(rpc, px, py, pw_, ph_)
                if dcp:
                    self.panels[pid] = dcp
                    self._panel_cids[pid] = f"dpanel_{pid}"
                    self._panel_dims[pid] = (pw_, ph_, px, py)
                    self._direct_canvas_ids[pid] = dcp
                    # Bake this panel's visual result into _bg_pil so panels drawn
                    # after it (higher in z-order = lower layer number) can composite
                    # correctly against it. This applies to ALL panel types —
                    # including transparent element panels that still draw a visible shape.
                    self._bake_panel_into_bg_pil(rpc, px, py, pw_, ph_)
            else:
                w = self._mk(rpc)
                if w:
                    self.panels[pid] = w
                    cid = self.bg_canvas.create_window(
                        px, py, anchor="nw", window=w, width=pw_, height=ph_
                    )
                    self._panel_cids[pid] = cid
                    self._panel_dims[pid] = (pw_, ph_, px, py)
                    # Opaque widget panels also baked into _bg_pil so transparent panels above see them
                    self._bake_panel_into_bg_pil(rpc, px, py, pw_, ph_)

    def _mk_direct(self, pc, px, py, pw_, ph_):
        """Create a DirectCanvasPanel that draws directly on bg_canvas at (px,py).
        This gives true transparency — the panel sees everything already drawn on
        bg_canvas beneath it (other panels, background) with no Widget boundary."""
        t = pc.get("type")
        is_transparent = pc.get("bg_transparent", False)
        has_bg_img = (not is_transparent and bool(pc.get("bg_image","")) and
                      os.path.exists(pc.get("bg_image","") or "") and PIL_AVAILABLE)
        # Border: drawn on bg_canvas around the panel region
        if not pc.get("border_transparent", False):
            bw = pc.get("border_width", 2)
            bc = pc.get("border_color", BLUE)
            if bw > 0:
                self.bg_canvas.create_rectangle(
                    px, py, px+pw_-1, py+ph_-1,
                    outline=bc, width=bw,
                    tags=f"dpanel_{pc['id']}")
        # Background fill for bg_image panels
        if has_bg_img:
            try:
                img = Image.open(pc["bg_image"]).resize((pw_, ph_), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                iid = self.bg_canvas.create_image(px, py, anchor="nw", image=photo,
                                                   tags=f"dpanel_{pc['id']}")
                # Store photo ref on canvas to prevent GC
                if not hasattr(self.bg_canvas, "_img_refs"):
                    self.bg_canvas._img_refs = {}
                self.bg_canvas._img_refs[pc["id"]] = photo
            except: pass

        # Create and return the appropriate DirectCanvasPanel
        if t == "clock":    return DirectClockPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "date":     return DirectDatePanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "time":     return DirectTimePanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "text":     return DirectTextPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "zmanim":   return DirectZmanimPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "notice":   return DirectNoticePanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "_schedule": return DirectSchedulePanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "screen_msg": return DirectTextPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "ad":       return DirectAdPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        if t == "element":  return DirectElemPanel(self.bg_canvas, pc, self, px, py, pw_, ph_)
        return None

    def _mk(self, pc):
        """Create a standard panel widget embedded via create_window."""
        t = pc.get("type")
        is_transparent = pc.get("bg_transparent", False)
        has_bg_img = (not is_transparent and bool(pc.get("bg_image","")) and
                      os.path.exists(pc.get("bg_image","") or "") and PIL_AVAILABLE)
        use_trans_widget = is_transparent or has_bg_img
        if t=="clock":
            return (TransparentClockPW(self.root,pc,self) if use_trans_widget else ClockPW(self.root,pc,self))
        if t=="date":
            return (TransparentDatePW(self.root,pc,self) if use_trans_widget else DatePW(self.root,pc,self))
        if t in ("text","screen_msg"):
            return (TransparentTextPW(self.root,pc,self) if use_trans_widget else TextPW(self.root,pc,self))
        if t=="time":       return TimePW(self.root,pc,self)
        if t=="ad":         return (TransparentAdPW(self.root,pc,self) if use_trans_widget else AdPW(self.root,pc,self))
        if t=="zmanim":     return ZmanimPW(self.root,pc,self)
        if t=="element":    return ElemPW(self.root,pc,self)
        if t=="notice":     return NoticePW(self.root,pc,self)
        if t=="_schedule": return SchedulePW(self.root,pc,self)
        return None

    def _bake_panel_into_bg_pil(self, pc, px, py, pw_, ph_):
        """Composite this panel's visual appearance into _bg_pil in-place.
        Called after each panel is placed (in render order: bottom first).
        The next panel above can then use _bg_pil as accurate composite of everything beneath.
        Handles: element images (with RGBA alpha), bg_image fills, opaque colour fills.
        Transparent non-element panels (clock, text, zmanim) add nothing visible to _bg_pil
        since their canvas items are text-only — correctly left unchanged."""
        if not PIL_AVAILABLE or not getattr(self, "_bg_pil", None):
            return
        try:
            bg = self._bg_pil
            x0 = max(0, px); y0 = max(0, py)
            x1 = min(self.W, px+pw_); y1 = min(self.H, py+ph_)
            if x0 >= x1 or y0 >= y1: return

            # ── Element panel (type="element"): paste the element image with RGBA alpha ──
            img_path = pc.get("image_path","")
            if img_path and os.path.exists(img_path) and pc.get("type") == "element":
                try:
                    elem = Image.open(img_path).convert("RGBA")
                    fit = pc.get("fit_mode","contain")
                    if fit == "contain":
                        elem.thumbnail((pw_, ph_), Image.LANCZOS)
                    elif fit == "stretch":
                        elem = elem.resize((pw_, ph_), Image.LANCZOS)
                    else:
                        ratio = max(pw_/elem.width, ph_/elem.height)
                        elem = elem.resize((int(elem.width*ratio), int(elem.height*ratio)), Image.LANCZOS)
                    ox = (pw_ - elem.width)//2; oy_ = (ph_ - elem.height)//2
                    # Crop the current _bg_pil region, composite element onto it
                    region = bg.crop((x0, y0, x1, y1)).convert("RGBA")
                    # elem paste offset within the clipped region
                    ex = ox - (x0 - px); ey = oy_ - (y0 - py)
                    region.paste(elem, (ex, ey), elem)
                    bg.paste(region.convert("RGB"), (x0, y0))
                    return
                except: pass

            # ── bg_image panel: paste the background image ──
            bg_img_path = pc.get("bg_image","")
            if bg_img_path and os.path.exists(bg_img_path) and not pc.get("bg_transparent", False):
                try:
                    img = Image.open(bg_img_path).resize((pw_, ph_), Image.LANCZOS).convert("RGBA")
                    crop = img.crop((x0-px, y0-py, x1-px, y1-py))
                    region = bg.crop((x0, y0, x1, y1)).convert("RGBA")
                    region.paste(crop, (0, 0), crop)
                    bg.paste(region.convert("RGB"), (x0, y0))
                    return
                except: pass

            # ── Opaque solid-colour panel: paint bg_color ──
            if not pc.get("bg_transparent", False):
                try:
                    bgc = pc.get("bg_color", PNL).lstrip("#")
                    rgb = tuple(int(bgc[i:i+2], 16) for i in (0,2,4))
                    patch = Image.new("RGB", (x1-x0, y1-y0), rgb)
                    bg.paste(patch, (x0, y0))
                except: pass
            # Transparent non-element panels (clock, text, zmanim, date) draw only
            # canvas text items — they add nothing to _bg_pil, which is correct.
        except: pass

    def _get_bg_at_y(self, y):
        """Compute approximate gradient background color at given Y position."""
        disp = self.cfg.d["display"]
        bgc = disp.get("bg_color", BG)
        if disp.get("gradient", True):
            try:
                _hx=bgc.lstrip("#"); bg_r=int(_hx[0:2],16); bg_g=int(_hx[2:4],16); bg_b=int(_hx[4:6],16)
            except: bg_r,bg_g,bg_b=7,7,20
            t = min(1.0, max(0.0, y / max(1, self.H)))
            r=max(0,int(bg_r*(1-t*0.35)))
            g=max(0,int(bg_g*(1-t*0.35)))
            b=min(255,int(bg_b+(255-bg_b)*t*0.12))
            return f"#{r:02x}{g:02x}{b:02x}"
        return bgc

    def _render_bg_to_pil(self):
        """Render full background (gradient + stars + image) to PIL Image for transparency."""
        if not PIL_AVAILABLE: self._bg_pil = None; return
        try:
            from PIL import ImageDraw as _PID
            disp = _get_active_display(self.cfg.d, self._preview_board_id)
            bgc = disp.get("bg_color", BG)
            try:
                _hx=bgc.lstrip("#"); bg_r=int(_hx[0:2],16); bg_g=int(_hx[2:4],16); bg_b=int(_hx[4:6],16)
            except: bg_r,bg_g,bg_b=7,7,20
            img = Image.new("RGB", (self.W, self.H), (bg_r,bg_g,bg_b))
            draw = _PID.Draw(img)
            if disp.get("gradient", True):
                steps = 50
                for i in range(steps):
                    t = i / steps
                    r=max(0,int(bg_r*(1-t*0.35)))
                    g=max(0,int(bg_g*(1-t*0.35)))
                    b=min(255,int(bg_b+(255-bg_b)*t*0.12))
                    y0 = int(i*self.H/steps); y1 = int((i+1)*self.H/steps)+1
                    draw.rectangle([0, y0, self.W-1, y1], fill=(r, g, b))
            else:
                draw.rectangle([0, 0, self.W-1, self.H-1], fill=(bg_r,bg_g,bg_b))
            if disp.get("show_stars", True):
                import random; random.seed(42)
                for _ in range(120):
                    sx=random.randint(0,self.W-1); sy=random.randint(0,self.H-1)
                    br=random.randint(80,180); ss=random.randint(1,2)
                    draw.ellipse([sx-ss,sy-ss,sx+ss,sy+ss], fill=(br,br,min(255,br+40)))
            bg_img = disp.get("bg_image","")
            if bg_img and os.path.exists(bg_img):
                try:
                    bg = Image.open(bg_img).resize((self.W,self.H),Image.LANCZOS).convert("RGB")
                    img = bg
                except: pass
            self._bg_pil = img
        except: self._bg_pil = None

    def _get_bg_crop_photo(self, x, y, w, h):
        """Return a PhotoImage of the background region at (x,y,w,h)."""
        if not PIL_AVAILABLE or not getattr(self, "_bg_pil", None): return None
        try:
            region = self._bg_pil.crop((max(0,x), max(0,y),
                                        min(self.W,x+w), min(self.H,y+h)))
            if region.size != (w, h):
                region = region.resize((w, h), Image.LANCZOS)
            return ImageTk.PhotoImage(region)
        except: return None

    def _composite_bg(self, scaled_pc, this_id=None):
        """PIL-only compositing: main background + lower-layer panel backgrounds.
        Uses _panel_dims for accurate scaled positions of other panels.
        No screen capture — no artifacts from overlapping windows.
        A transparent panel shows whatever is visually beneath it:
        panels with higher layer numbers (further back) AND same-layer panels
        that were rendered earlier (lower index in sorted list = further back)."""
        if not PIL_AVAILABLE or not getattr(self, "_bg_pil", None): return None
        try:
            x0, y0 = scaled_pc.get("x",0), scaled_pc.get("y",0)
            W, H = scaled_pc.get("width",300), scaled_pc.get("height",200)
            this_layer = scaled_pc.get("layer", 1)
            if this_id is None: this_id = scaled_pc.get("id")

            # Build render order: layer 3 first (bottom), layer 1 last (top)
            # Same-layer panels keep their original list order (stable sort)
            all_panels = self.cfg.d.get("panels", [])
            render_order = sorted(all_panels, key=lambda p: -(p.get("layer", 1)))
            # Index of this panel in render order (panels before it are visually beneath)
            this_render_idx = next((i for i, p in enumerate(render_order)
                                    if p.get("id") == this_id), len(render_order))

            # Crop main background
            region = self._bg_pil.crop((max(0,x0), max(0,y0),
                                        min(self.W,x0+W), min(self.H,y0+H)))
            if region.size != (W, H):
                region = region.resize((W, H), Image.LANCZOS)
            comp = region.convert("RGBA")

            # Composite panels that are BELOW this one:
            # - higher layer number (further back), OR
            # - same layer but earlier in render order (rendered before = visually beneath)
            for render_idx, other_pc in enumerate(render_order):
                if not other_pc.get("enabled", True): continue
                other_id = other_pc.get("id")
                if other_id == this_id: continue
                other_layer = other_pc.get("layer", 1)
                # Skip panels that are visually ON TOP of this panel
                if other_layer < this_layer: continue          # smaller layer = further front
                if other_layer == this_layer and render_idx >= this_render_idx: continue
                if other_pc.get("bg_transparent", False): continue

                # Use scaled dims from _panel_dims if available (populated during _setup_panels)
                odims = self._panel_dims.get(other_id)
                if odims:
                    ow, oh, ox, oy = odims
                else:
                    ox, oy = other_pc.get("x",0), other_pc.get("y",0)
                    ow, oh = other_pc.get("width",300), other_pc.get("height",200)

                # Compute overlap
                ix0 = max(x0, ox); iy0 = max(y0, oy)
                ix1 = min(x0+W, ox+ow); iy1 = min(y0+H, oy+oh)
                if ix0 >= ix1 or iy0 >= iy1: continue

                lx0 = ix0 - x0; ly0 = iy0 - y0
                rw = ix1 - ix0; rh = iy1 - iy0

                other_bg_img = other_pc.get("bg_image","")
                if other_bg_img and os.path.exists(other_bg_img):
                    try:
                        bg_img = Image.open(other_bg_img).convert("RGBA")
                        crop_x = ix0 - ox; crop_y = iy0 - oy
                        bg_crop = bg_img.crop((crop_x, crop_y, crop_x+rw, crop_y+rh))
                        comp.paste(bg_crop, (lx0, ly0), bg_crop)
                        continue
                    except: pass
                try:
                    bgc = other_pc.get("bg_color","#111128").lstrip("#")
                    rgb = tuple(int(bgc[i:i+2], 16) for i in (0, 2, 4))
                    patch = Image.new("RGBA", (rw, rh), rgb+(255,))
                    comp.paste(patch, (lx0, ly0))
                except: pass

            return ImageTk.PhotoImage(comp.convert("RGB"))
        except: return None

    # Keep old name as alias for backward compat with CanvasBackedPanel.__init__ calls
    def _get_composite_bg_photo(self, pc):
        return self._composite_bg(pc)

    def refresh(self):
        self._draw_bg()
        self._setup_panels()
        # Ensure version watermark stays on top of all panels
        try: self.bg_canvas.tag_raise("version_watermark")
        except: pass

    def _update_transparent_bgs(self):
        """After all panels are placed, recompute transparent panel backgrounds
        using PIL compositing with correct scaled dimensions from _panel_dims.
        No ImageGrab — no artifacts from overlapping windows.
        Process bottom-to-top so an upper transparent panel correctly sees
        whatever is visually beneath it — including other transparent panels
        that have already been resolved."""
        if not PIL_AVAILABLE or not getattr(self, "_bg_pil", None):
            return
        # Build strict render order (bottom first):
        # layer 3 → layer 2 → layer 1; within same layer preserve list order.
        all_panels = self.cfg.d.get("panels", [])
        render_order = sorted(enumerate(all_panels),
                              key=lambda iv: -(iv[1].get("layer", 1)))
        trans_list = [
            pc for _, pc in render_order
            if pc.get("enabled", True) and pc.get("bg_transparent", False)
            and not (bool(pc.get("bg_image","")) and os.path.exists(pc.get("bg_image","") or ""))
            and pc.get("id") in self._panel_dims
            and isinstance(self.panels.get(pc.get("id")), CanvasBackedPanel)
        ]
        for pc in trans_list:
            pid = pc["id"]
            pw = self.panels.get(pid)
            if not pw: continue
            dims = self._panel_dims.get(pid)
            if not dims: continue
            pw_w, pw_h, px, py = dims
            scaled_pc = dict(pc)
            scaled_pc.update({"x": px, "y": py, "width": pw_w, "height": pw_h})
            photo = self._composite_bg(scaled_pc, this_id=pid)
            if photo:
                pw._bg_photo = photo
                pw.delete("cbp_bg")
                pw.create_image(0, 0, anchor="nw", image=photo, tags="cbp_bg")
                pw.tag_lower("cbp_bg")

    def show_fullscreen_msg(self,text,duration=0,bg="#0a0000",fg=GOLD,fontsize=48,on_close=None):
        """Show a full-screen overlay announcement."""
        ov=tk.Toplevel(self.root)
        ov.attributes("-fullscreen",True)
        ov.attributes("-topmost",True)
        ov.configure(bg=bg)
        ov.lift()
        cv=tk.Canvas(ov,bg=bg,highlightthickness=0)
        cv.place(x=0,y=0,relwidth=1,relheight=1)
        # Dim overlay
        W=self.W; H=self.H
        cv.create_rectangle(0,0,W,H,fill=bg,outline="")
        # Decorative border frame
        cv.create_rectangle(30,30,W-30,H-30,outline=fg,width=3)
        # Inner thin border — compute semi-transparent version of fg by blending with bg
        fg_dim = _blend_tk(fg, 0x55, bg)
        cv.create_rectangle(40,40,W-40,H-40,outline=fg_dim,width=1)
        # Text — word-wrap by inserting newlines
        words=text.split(); lines=[]; line=""
        max_chars=int(W//(fontsize*0.55))
        for w in words:
            if len(line)+len(w)+1<=max_chars: line=(line+" "+w).strip()
            else: lines.append(line); line=w
        if line: lines.append(line)
        wrapped="\n".join(lines)
        cv.create_text(W//2,H//2-30,text=wrapped,font=("Arial",fontsize,"bold"),
                       fill=fg,justify="center",width=W-160)
        # Close instruction — slightly dimmed text
        fg_soft = _blend_tk(fg, 0xbb, bg)
        cv.create_text(W//2,H-60,text="לחץ על המסך או על F9 לסגירה",
                       font=("Arial",16),fill=fg_soft,justify="center")
        def close(*_):
            ov.destroy()
            if on_close: on_close()
        ov.bind("<Button-1>",close)
        ov.bind("<F9>",close)
        self.root.bind("<F9>",close)
        if duration>0:
            ov.after(duration*1000,close)

    def _tick(self):
        for pw in self.panels.values():
            try: pw.tick()
            except: pass
        # Tick active popup reminder panels
        for pw, _, _cid in list(getattr(self, "_active_popups", {}).values()):
            try: pw.tick()
            except: pass
        # ── check reminders ──
        self._check_reminders()
        self.root.after(1000, self._tick)

    def _check_reminders(self):
        now=datetime.now(); today=now.date()
        # weekday: 0=Sun … 6=Sat (matching HEB_WDAYS)
        today_wd=(today.weekday()+1)%7

        # Lazy-cache today's zmanim (global + per-uid with method overrides)
        try:
            zc = _make_zmanim_calc(self.cfg.d)
            self._today_zmanim=zc.calc(today)
        except: self._today_zmanim={}
        # Build per-uid zmanim map (respects per-entry method overrides)
        try:
            eff = get_effective_zmanim_entries(self.cfg.d)
            loc = self.cfg.d.get("location", {})
            self._today_zmanim_uid = {}
            for uid, key, name, method_override in eff:
                if method_override:
                    try:
                        alt_calc = ZmanimCalc(loc.get("lat",31.7683), loc.get("lng",35.2137),
                                             loc.get("elev",0), loc.get("tz","Asia/Jerusalem"),
                                             method=method_override)
                        alt_data = alt_calc.calc(today)
                        self._today_zmanim_uid[uid] = alt_data.get(key)
                    except:
                        self._today_zmanim_uid[uid] = self._today_zmanim.get(key)
                else:
                    self._today_zmanim_uid[uid] = self._today_zmanim.get(key)
        except: self._today_zmanim_uid = {}
        self._zmanim_date=today

        today_holiday=get_today_holiday()

        for r in self.cfg.reminders():
            # Skip if non-recurring reminder was already done
            if r.get("done") and r.get("recurring","none")=="none": continue
            # Skip if already triggered today (for recurring)
            if r.get("last_triggered","")==str(today): continue

            # Day-of-week filter
            days=r.get("days",list(range(7)))
            if today_wd not in days: continue
            # Shabbat skip
            if r.get("skip_shabbat",True) and today_wd==6: continue
            # Holiday skip
            if r.get("skip_holidays",False) and today_holiday: continue

            # Compute trigger time
            rem_type=r.get("rem_type","personal")
            if rem_type=="personal":
                try: dt=datetime.strptime(r.get("dt",""),"%Y-%m-%d %H:%M")
                except: continue
                if dt.date()!=today and r.get("recurring","none")=="none": continue
                if r.get("recurring","none")=="daily":
                    dt=datetime.combine(today,dt.time())
                elif r.get("recurring","none")=="weekly" and dt.weekday()!=today.weekday():
                    continue
            elif rem_type=="zmanim":
                zman=r.get("zman","sunset")
                # Try uid lookup first (per-method), then fall back to key lookup
                base = self._today_zmanim_uid.get(zman) or self._today_zmanim.get(zman)
                if base is None: continue
                if not isinstance(base,datetime): continue
                dt=base+timedelta(minutes=r.get("offset_min",0))
                # Normalize to today's date
                dt=datetime.combine(today,dt.time()) if dt.date()==today else dt
                if dt.date()!=today: continue
            else: continue

            if not (dt<=now<=dt+timedelta(seconds=59)): continue

            # Trigger!
            r["last_triggered"]=str(today)
            if r.get("recurring","none")=="none": r["done"]=True
            self.cfg.save()

            text=r.get("text","")

            # For zmanim reminders — enrich display text
            if rem_type == "zmanim":
                zman_key = r.get("zman","sunset")
                zman_name = ZMANIM_KEYS.get(zman_key, zman_key)
                zman_exact = self._today_zmanim.get(zman_key)
                now_dt = datetime.now()
                try:
                    zn = zman_exact.replace(tzinfo=None) if (hasattr(zman_exact,"tzinfo") and zman_exact.tzinfo) else zman_exact
                    delta_min = int((zn - now_dt).total_seconds() / 60)
                    exact_str = zn.strftime("%H:%M")
                    if delta_min > 0:
                        countdown_str = f"עוד {delta_min} דקות"
                    elif delta_min == 0:
                        countdown_str = "עכשיו!"
                    else:
                        countdown_str = f"לפני {abs(delta_min)} דקות"
                    text = f"{zman_name}\n{countdown_str} | {exact_str}"
                    if r.get("text","") and r.get("text","") != zman_name:
                        text = r.get("text","") + f"\n{zman_name} — {countdown_str} | {exact_str}"
                except:
                    pass

            # Visual notification — display text in the chosen panel
            npid = r.get("notice_panel_id")
            if npid:
                pc = self.cfg.get_panel(npid)
                if pc and pc.get("type") == "notice" and pc.get("popup_only", False):
                    # Popup-only notice panel: temporarily show it
                    dur = pc.get("popup_duration", 30)
                    self._show_popup_reminder(npid, text, duration=dur)
                elif npid in self.panels:
                    # Permanent panel already on screen: update its content
                    try:
                        pw = self.panels[npid]
                        pw.pc["content"] = text
                        pw.build_content_override(text)
                    except: pass

            # Sound notification
            if r.get("notify_sound",False):
                sound_type = r.get("sound_type","beep")
                sound_file = r.get("sound_file","")
                self._play_sound(sound_type, sound_file)

    def _show_popup_reminder(self, pid, text, duration=30, _pc_override=None):
        """Temporarily show a popup-only notice panel with reminder text.
        Hides it after `duration` seconds (0 = stays until next reminder)."""
        if _pc_override:
            pc = _pc_override
        else:
            pc = getattr(self, "_popup_configs", {}).get(pid)
            if not pc:
                pc = self.cfg.get_panel(pid)
        if not pc: return

        if not hasattr(self, "_active_popups"):
            self._active_popups = {}
        popups = self._active_popups

        # If a popup for this panel already exists, just update text
        if pid in popups:
            try:
                pw, after_id, cid = popups[pid]  # always 3-tuple
                pw.build_content_override(text)
                if after_id:
                    try: self.root.after_cancel(after_id)
                    except: pass
                popups[pid] = (pw, None, cid)
            except:
                popups.pop(pid, None)

        if pid not in popups:
            try:
                ppc = dict(pc); ppc["content"] = text
                pw = NoticePW(self.root, ppc, self)
                cid = self.bg_canvas.create_window(
                    ppc.get("x", 10), ppc.get("y", 10),
                    anchor="nw", window=pw,
                    width=ppc.get("width", 900), height=ppc.get("height", 80)
                )
                pw._canvas_cid = cid  # allow slide animations to reposition
                popups[pid] = (pw, None, cid)
            except: return

        if duration > 0:
            def _hide(pid=pid):
                self._hide_popup_reminder(pid)
            after_id = self.root.after(int(duration * 1000), _hide)
            if pid in popups:
                pw, _, cid = popups[pid]
                popups[pid] = (pw, after_id, cid)

    def _hide_popup_reminder(self, pid):
        """Remove an active reminder popup from the display."""
        popups = getattr(self, "_active_popups", {})
        if pid not in popups: return
        try:
            pw, after_id, cid = popups[pid]
            if after_id:
                try: self.root.after_cancel(after_id)
                except: pass
            # Run exit animation then destroy
            def _do_destroy():
                try: self.bg_canvas.delete(cid)
                except: pass
                try: pw.destroy()
                except: pass
                popups.pop(pid, None)
            try:
                pw.start_exit_anim(on_done=_do_destroy)
            except:
                _do_destroy()
        except: pass
        popups.pop(pid, None)

    def _play_sound(self, sound_type="beep", sound_file=""):
        """Play a notification sound in a background thread."""
        import threading
        def _do_play():
            try:
                if sound_type == "file" and sound_file and os.path.exists(sound_file):
                    if sys.platform == "win32":
                        import winsound
                        winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                    elif sys.platform == "darwin":
                        import subprocess; subprocess.call(["afplay", sound_file])
                    else:
                        import subprocess; subprocess.call(["aplay", sound_file])
                elif sys.platform == "win32":
                    import winsound
                    _alias = {"asterisk":"SystemAsterisk","exclamation":"SystemExclamation",
                              "question":"SystemQuestion","hand":"SystemHand"}
                    if sound_type in _alias:
                        winsound.PlaySound(_alias[sound_type], winsound.SND_ALIAS)
                    elif sound_type == "high":
                        for f in [880,1100,1320]: winsound.Beep(f,200)
                    elif sound_type == "low":
                        for f in [440,550,660]: winsound.Beep(f,300)
                    else:  # default "beep"
                        winsound.Beep(880,200); winsound.Beep(1100,300)
                else:
                    # Linux/Mac fallback via subprocess
                    import subprocess
                    if sound_type == "high":
                        subprocess.call(["python3","-c",
                            "import os;[os.system('echo -e \"\\a\"') for _ in range(3)]"])
                    else:
                        subprocess.call(["python3","-c","import os;os.system('echo -e \"\\a\"')"])
            except: pass
        threading.Thread(target=_do_play, daemon=True).start()

    # ── Cover overlay (Shabbat/Holidays) ─────────────────────────────────────
    def show_cover(self, image_path=""):
        """Show fullscreen cover image/overlay for Shabbat or holiday."""
        if getattr(self, "_cover_visible", False):
            # Already shown — update image if changed
            if image_path != getattr(self, "_cover_image_path", None):
                self._cover_image_path = image_path
                self._render_cover_image(image_path)
            return
        self._cover_visible = True
        self._cover_image_path = image_path
        # Create fullscreen cover frame on top of everything
        self._cover_frame = tk.Frame(self.root, bg="#0a0010")
        self._cover_frame.place(x=0, y=0, width=self.W, height=self.H)
        self._cover_frame.lift()
        self._cover_canvas = tk.Canvas(
            self._cover_frame, width=self.W, height=self.H,
            bg="#0a0010", highlightthickness=0)
        self._cover_canvas.pack(fill="both", expand=True)
        self._cover_img_ref = None
        self._render_cover_image(image_path)

    def _render_cover_image(self, image_path):
        """Draw cover image (or dark fallback) on cover canvas."""
        c = getattr(self, "_cover_canvas", None)
        if not c: return
        c.delete("all")
        c.configure(bg="#0a0010")
        if image_path and os.path.exists(image_path) and PIL_AVAILABLE:
            try:
                img = Image.open(image_path).resize((self.W, self.H), Image.LANCZOS)
                self._cover_img_ref = ImageTk.PhotoImage(img)
                c.create_image(0, 0, anchor="nw", image=self._cover_img_ref)
                return
            except: pass
        # Fallback: dark screen with candle emoji text
        c.create_text(self.W//2, self.H//2, text="🕯", font=("Arial", 120), fill="#ffcc66")

    def hide_cover(self):
        """Remove cover overlay if shown."""
        if not getattr(self, "_cover_visible", False):
            return
        self._cover_visible = False
        if hasattr(self, "_cover_frame"):
            try: self._cover_frame.destroy()
            except: pass
            del self._cover_frame
        self._cover_img_ref = None

    def run(self): self.root.mainloop()

# ── בסיס חלוניות ────────────────────────────────────────────────────────────
class PW(tk.Frame):
    def __init__(self,parent,pc,dsp):
        self.pc=pc; self.dsp=dsp
        bg=self._bg()
        bw=0 if pc.get("border_transparent",False) else pc.get("border_width",2)
        bc=pc.get("border_color",BLUE)
        super().__init__(parent,bg=bg,
                         highlightthickness=bw,
                         highlightbackground=bc,
                         highlightcolor=bc)
        self._load_bg_img()

        # Inner content frame — respects per-panel content margins (pad_top/bottom/left/right).
        # All build() methods place their widgets into self._content.
        # Default fallback = 0 so existing panels without margins are unchanged.
        # IMPORTANT: bg stays as outer frame — _content is transparent (same bg color),
        # so rounding/background is unaffected. Only the content widgets move inward.
        _pt = int(pc.get("pad_top",    0))
        _pb = int(pc.get("pad_bottom", 0))
        _pl = int(pc.get("pad_left",   0))
        _pr = int(pc.get("pad_right",  0))
        _pw = int(pc.get("width",  300))
        _ph = int(pc.get("height", 200))
        _cw = max(1, _pw - _pl - _pr)
        _ch = max(1, _ph - _pt - _pb)
        self._content = tk.Frame(self, bg=bg, bd=0, highlightthickness=0,
                                 width=_cw, height=_ch)
        self._content.place(x=_pl, y=_pt, width=_cw, height=_ch)
        self._content.pack_propagate(False)   # keep explicit size when children pack into it
        self.build()

    def _has_bg_image(self):
        """Returns True if a valid bg_image is configured (and not transparent)."""
        if self.pc.get("bg_transparent", False):
            return False
        p = self.pc.get("bg_image", "")
        return bool(p and os.path.exists(p) and PIL_AVAILABLE)

    def _bg(self):
        if self.pc.get("bg_transparent", False):
            # Match gradient color at panel's Y position for best visual transparency
            return self.dsp._get_bg_at_y(self.pc.get("y", 0))
        return self.pc.get("bg_color", PNL)

    def _load_bg_img(self):
        """Load bg_image. When bg_image is set (non-transparent), bg_color is ignored.
        The image is placed behind all children via a lowered Canvas."""
        p = self.pc.get("bg_image", "")
        if not (p and os.path.exists(p) and PIL_AVAILABLE):
            return
        if self.pc.get("bg_transparent", False):
            return  # transparent panels handle bg via CanvasBackedPanel
        try:
            w = self.pc.get("width", 300); h = self.pc.get("height", 200)
            img = Image.open(p).resize((w, h), Image.LANCZOS)
            self._bgref = ImageTk.PhotoImage(img)
            # Place image label to fill frame, then lower it below child widgets.
            lbl = tk.Label(self, image=self._bgref, bd=0)
            lbl.place(x=0, y=0, width=w, height=h)
            lbl.lower()
            self._bg_lbl = lbl
        except:
            pass

    def build(self): pass
    def tick(self): pass

# ── חלונית שעה בלבד ───────────────────────────────────────────────────────────
def _draw_analog_clock(cv, p, now, W, H, transparent_bg=False, tag=None):
    """Draw analog clock on canvas cv. If transparent_bg, skip face fill.
    If tag is given, all items are tagged with it (for selective deletion)."""
    import math as _math
    cx = W // 2; cy = H // 2
    r = min(cx, cy) - 6
    if r < 10: r = 10
    cc = p.get("font_color", p.get("clock_color", "#3a7bd5"))
    style = p.get("analog_style", "classic")
    bg_fill = "" if transparent_bg else p.get("bg_color", "#111128")

    # Helper: create items with optional tag
    _t = (tag,) if tag else ()

    # Outer glow ring (classic/railway only)
    if style in ("classic", "railway"):
        cv.create_oval(cx-r-3, cy-r-3, cx+r+3, cy+r+3, fill="", outline="#1a2a6a", width=6, tags=_t)

    # Clock face
    face_outline = cc
    face_fill = bg_fill
    cv.create_oval(cx-r, cy-r, cx+r, cy+r, fill=face_fill, outline=face_outline,
                   width=2 if style=="minimal" else 3, tags=_t)

    # Inner decorative ring (classic only)
    if style == "classic":
        cv.create_oval(cx-r+7, cy-r+7, cx+r-7, cy+r-7, fill="", outline="#1a2a5a", width=1, tags=_t)

    # Hour markers and labels
    for i in range(60):
        angle = _math.radians(i * 6 - 90)
        cos_a = _math.cos(angle); sin_a = _math.sin(angle)
        if i % 5 == 0:
            if style == "railway":
                x1 = cx + (r - 2) * cos_a; y1 = cy + (r - 2) * sin_a
                x2 = cx + (r - 18) * cos_a; y2 = cy + (r - 18) * sin_a
                cv.create_line(x1, y1, x2, y2, fill=cc, width=4, tags=_t)
            elif style == "minimal":
                x1 = cx + (r - 4) * cos_a; y1 = cy + (r - 4) * sin_a
                x2 = cx + (r - 14) * cos_a; y2 = cy + (r - 14) * sin_a
                cv.create_line(x1, y1, x2, y2, fill=cc, width=2, tags=_t)
            else:  # classic / roman
                x1 = cx + (r - 4) * cos_a; y1 = cy + (r - 4) * sin_a
                x2 = cx + (r - 16) * cos_a; y2 = cy + (r - 16) * sin_a
                cv.create_line(x1, y1, x2, y2, fill=cc, width=2, tags=_t)

            if style not in ("minimal", "railway"):
                nx = cx + (r - 28) * cos_a; ny = cy + (r - 28) * sin_a
                hn = i // 5 or 12
                if style == "roman":
                    _rom = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",
                            7:"VII",8:"VIII",9:"IX",10:"X",11:"XI",12:"XII"}
                    label = _rom.get(hn, str(hn))
                else:
                    label = str(hn)
                fsize = max(7, r // 14)
                cv.create_text(nx, ny, text=label, fill="#aabbdd", font=("Arial", fsize), tags=_t)
        else:
            if style != "minimal":
                x1 = cx + (r - 4) * cos_a; y1 = cy + (r - 4) * sin_a
                x2 = cx + (r - 9) * cos_a; y2 = cy + (r - 9) * sin_a
                cv.create_line(x1, y1, x2, y2, fill="#5566aa", width=1, tags=_t)

    def hand(deg, L, color, w, back=False):
        a = _math.radians(deg - 90)
        hx = cx + L * _math.cos(a); hy = cy + L * _math.sin(a)
        if back:
            ba = _math.radians(deg - 90 + 180)
            bx = cx + r * 0.18 * _math.cos(ba); by = cy + r * 0.18 * _math.sin(ba)
            cv.create_line(cx, cy, bx, by, fill=color, width=w, tags=_t)
        cv.create_line(cx, cy, hx, hy, fill=color, width=w, capstyle="round", tags=_t)

    ha = (now.hour % 12 + now.minute / 60) * 30
    ma = (now.minute + now.second / 60) * 6
    sa = now.second * 6

    hand(ha, r * 0.53, "#ffffff", 5 if style in ("classic","roman") else 4)
    hand(ma, r * 0.76, cc, 3)
    if p.get("show_seconds", True):
        hand(sa, r * 0.87, "#f5a623", 1, back=True)
    # Center dot
    cv.create_oval(cx-6, cy-6, cx+6, cy+6, fill=cc, outline="#070714", width=2, tags=_t)


class ClockPW(PW):
    """Clock-only panel (type='clock'). Shows time, no date info."""
    def build(self):
        p = self.pc; bg = self._bg()
        ff = p.get("font_family", "Arial")
        cc = p.get("font_color", p.get("clock_color", BLUE))
        if p.get("clock_style", "digital") == "analog":
            self._build_analog(bg, ff, cc)
        else:
            self._build_digital(bg, ff, cc)

    def _build_digital(self, bg, ff, cc):
        p = self.pc
        fs = p.get("font_size", p.get("time_font_size", 56))
        # Use pack(expand=True) so centering works before widget is rendered
        wrap = tk.Frame(self._content, bg=bg)
        wrap.pack(expand=True)
        self.t_var = tk.StringVar()
        tk.Label(wrap, textvariable=self.t_var, font=(ff, fs, "bold"),
                 fg=cc, bg=bg).pack(pady=(6, 2))
        self.tick()

    def _build_analog(self, bg, ff, cc):
        p = self.pc
        pt = int(p.get("pad_top",0)); pb = int(p.get("pad_bottom",0))
        pl = int(p.get("pad_left",0)); pr = int(p.get("pad_right",0))
        w = p.get("width", 280) - 8 - pl - pr
        h = p.get("height", 280) - 8 - pt - pb
        cs = max(10, min(w, h) - 4)
        self.cv = tk.Canvas(self._content, width=cs, height=cs, bg=bg, highlightthickness=0)
        # pack(expand=True) centers the canvas inside _content without needing winfo_width
        self.cv.pack(expand=True)
        self.tick()

    def tick(self):
        now = get_now(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
        p = self.pc
        if p.get("clock_style", "digital") == "analog":
            if not hasattr(self, "cv"): return
            self.cv.delete("all")
            cw = self.cv.winfo_width(); ch = self.cv.winfo_height()
            if cw < 10: cw = ch = min(p.get("width",280), p.get("height",280)) - 12
            _draw_analog_clock(self.cv, p, now, cw, ch, transparent_bg=False)
        else:
            if hasattr(self, "t_var"):
                sec = ":%S" if p.get("show_seconds", True) else ""
                fmt = f"%I:%M{sec} %p" if p.get("time_format","24") == "12" else f"%H:%M{sec}"
                self.t_var.set(now.strftime(fmt))


class DatePW(PW):
    """Date-only panel (type='date'). Shows weekday, Hebrew/Gregorian date, holidays, parasha."""

    def build(self):
        p = self.pc; bg = self._bg()
        self._ff = p.get("font_family", "Arial")
        self._fs = p.get("font_size", p.get("date_font_size", 18))
        self._bg_color = bg
        self._layout_mode = p.get("date_layout", "stacked")  # "stacked" or "inline"
        self._sep = p.get("date_separator", " | ")
        self._line_spacing = p.get("date_line_spacing", 4)
        self._scroll_inline = p.get("date_scroll_inline", False)
        self._scroll_speed = p.get("date_scroll_speed", 30)

        # Pre-compute current values for first render
        self._hol_cache = ""
        self._par_cache = ""
        self._par_last = None
        self._extra_last = None
        self._prayer_cache = {}
        self._torah_cache  = ("", "")
        self._daf_cache    = ""

        if self._layout_mode == "inline":
            self._build_inline(bg)
        else:
            self._build_stacked(bg)
        self.tick()

    def _item_color(self, key, default):
        """Get per-item color from config, falling back to default."""
        p = self.pc
        fc = p.get("font_color", p.get("date_color", TEXT))
        return p.get(key, fc if key not in ("hol_color", "par_color") else default)

    def _build_stacked(self, bg):
        """Build stacked (one item per row) layout."""
        p = self.pc
        ff = self._ff; fs = self._fs; sp = self._line_spacing
        wd_color  = self._item_color("wd_color",  TEXT)
        hd_color  = self._item_color("hd_color",  TEXT)
        gd_color  = self._item_color("gd_color",  TEXT)
        hol_color = self._item_color("hol_color", GOLD)
        par_color = self._item_color("par_color", LBLUE)
        tor_color = p.get("tor_color", "#aaffaa")
        haf_color = p.get("haf_color", "#aaffcc")
        yaaleh_color   = p.get("yaaleh_color",   "#ffdd88")
        morid_tal_color= p.get("morid_tal_color","#88ddff")
        mashiv_color   = p.get("mashiv_color",   "#88ccff")
        vten_color     = p.get("vten_color",     "#ffcc88")
        daf_color      = p.get("daf_color",      "#ccaaff")

        self._wrap = tk.Frame(self._content, bg=bg)
        self._wrap.pack(expand=True)

        if p.get("show_weekday", True):
            self.wd_var = tk.StringVar()
            tk.Label(self._wrap, textvariable=self.wd_var, font=(ff, fs, "bold"),
                     fg=wd_color, bg=bg).pack(pady=sp)

        if p.get("show_heb_date", True):
            self.hd_var = tk.StringVar()
            tk.Label(self._wrap, textvariable=self.hd_var, font=(ff, fs),
                     fg=hd_color, bg=bg).pack(pady=sp)

        if p.get("show_greg_date", True):
            self.gd_var = tk.StringVar()
            tk.Label(self._wrap, textvariable=self.gd_var, font=(ff, fs),
                     fg=gd_color, bg=bg).pack(pady=sp)

        # Holiday: only add label if there's actually a holiday (dynamic hide/show)
        if p.get("show_holiday", True):
            self.hol_var = tk.StringVar()
            self._hol_lbl = tk.Label(self._wrap, textvariable=self.hol_var,
                                      font=(ff, fs, "bold"), fg=hol_color, bg=bg)
            # Don't pack yet — only pack when there's a holiday

        if p.get("show_parasha", True):
            self.par_var = tk.StringVar()
            self._par_lbl = tk.Label(self._wrap, textvariable=self.par_var,
                                      font=(ff, fs), fg=par_color, bg=bg)
            self._par_lbl.pack(pady=sp)

        # ── שדות חדשים ──
        if p.get("show_torah_reading", False):
            self.tor_var = tk.StringVar()
            self._tor_lbl = tk.Label(self._wrap, textvariable=self.tor_var,
                                     font=(ff, fs), fg=tor_color, bg=bg)

        if p.get("show_haftara", False):
            self.haf_var = tk.StringVar()
            self._haf_lbl = tk.Label(self._wrap, textvariable=self.haf_var,
                                     font=(ff, fs), fg=haf_color, bg=bg)

        if p.get("show_yaaleh_veyavo", False):
            self.yaaleh_var = tk.StringVar()
            self._yaaleh_lbl = tk.Label(self._wrap, textvariable=self.yaaleh_var,
                                        font=(ff, fs), fg=yaaleh_color, bg=bg)

        if p.get("show_morid_hatal", False):
            self.morid_tal_var = tk.StringVar()
            self._morid_tal_lbl = tk.Label(self._wrap, textvariable=self.morid_tal_var,
                                           font=(ff, fs), fg=morid_tal_color, bg=bg)

        if p.get("show_mashiv_haruach", False):
            self.mashiv_var = tk.StringVar()
            self._mashiv_lbl = tk.Label(self._wrap, textvariable=self.mashiv_var,
                                        font=(ff, fs), fg=mashiv_color, bg=bg)

        if p.get("show_vten_tal_umatar", False):
            self.vten_var = tk.StringVar()
            self._vten_lbl = tk.Label(self._wrap, textvariable=self.vten_var,
                                      font=(ff, fs), fg=vten_color, bg=bg)

        if p.get("show_daf_yomi", False):
            self.daf_var = tk.StringVar()
            self._daf_lbl = tk.Label(self._wrap, textvariable=self.daf_var,
                                     font=(ff, fs), fg=daf_color, bg=bg)
            self._daf_lbl.pack(pady=sp)

    def _build_inline(self, bg):
        """Build inline layout: items flow left-to-right, wrap to next line.
        Uses a Canvas so each item can have its own color."""
        p = self.pc
        ff = self._ff; fs = self._fs
        w = p.get("width", 280)

        self._inline_bg = bg
        self._inline_panel_w = w

        if self._scroll_inline:
            fc = p.get("font_color", p.get("date_color", TEXT))
            self._inline_fc = fc
            self._canvas = tk.Canvas(self._content, bg=bg, highlightthickness=0,
                                     width=w, height=fs + 20)
            self._canvas.pack(expand=True)
            self._scroll_text_id = self._canvas.create_text(
                w, (fs + 20) // 2, text="", font=(ff, fs), fill=fc, anchor="w")
            self._scroll_x = float(w)
            self._scroll_running = True
        else:
            # Canvas for multi-line multi-color rendering
            self._inline_canvas = tk.Canvas(self._content, bg=bg,
                                            highlightthickness=0,
                                            width=w, height=fs + 8)
            self._inline_canvas.pack(expand=True, fill="both")
            self._inline_item_ids = []   # canvas text item ids

    def _rebuild_inline_lines(self, parts):
        """Lay out (text, color) parts into wrapped lines on _inline_canvas.
        Each part stays whole; separator is omitted at line start.
        Canvas height is adjusted to fit all lines."""
        if not hasattr(self, "_inline_canvas"):
            return
        p = self.pc
        ff = self._ff; fs = self._fs
        bg = self._inline_bg
        sep = self._sep
        max_w = max(40, p.get("width", 280) - 10)

        try:
            import tkinter.font as _tkF
            _fo = _tkF.Font(family=ff, size=fs)
            def _meas(t): return _fo.measure(t)
        except Exception:
            def _meas(t): return int(len(t) * fs * 0.6)

        sep_w = _meas(sep)

        # Build lines: list of list of (text, color)
        lines = []
        cur_line = []; cur_w = 0.0
        for txt, col in parts:
            iw = _meas(txt)
            if not cur_line:
                cur_line.append((txt, col)); cur_w = iw
            elif cur_w + sep_w + iw <= max_w:
                cur_line.append((txt, col)); cur_w += sep_w + iw
            else:
                lines.append(cur_line)
                cur_line = [(txt, col)]; cur_w = iw
        if cur_line:
            lines.append(cur_line)

        # Resize canvas height to fit all lines
        line_h = fs + 6
        total_h = max(line_h, len(lines) * line_h)
        try:
            self._inline_canvas.config(height=total_h)
        except tk.TclError:
            return

        # Remove old items
        for iid in self._inline_item_ids:
            try: self._inline_canvas.delete(iid)
            except: pass
        self._inline_item_ids = []

        # Draw each item individually so it gets its own color
        # Layout: RTL — each line starts from right edge, items placed right-to-left
        right_edge = max_w + 5
        for li, line_items in enumerate(lines):
            cy = li * line_h + line_h // 2
            # Measure total line width to right-align
            total_line_w = sum(_meas(t) for t, c in line_items) + sep_w * (len(line_items) - 1)
            # Start x = right edge minus total width (right-aligned)
            x = right_edge - total_line_w
            for idx, (txt, col) in enumerate(line_items):
                iw = _meas(txt)
                cx = x + iw // 2
                iid = self._inline_canvas.create_text(
                    cx, cy, text=txt, font=(ff, fs), fill=col, anchor="center")
                self._inline_item_ids.append(iid)
                x += iw
                if idx < len(line_items) - 1:
                    # Draw separator
                    sw = sep_w
                    sx = x + sw // 2
                    sep_color = p.get("font_color", p.get("date_color", TEXT))
                    iid2 = self._inline_canvas.create_text(
                        sx, cy, text=sep, font=(ff, fs), fill=sep_color, anchor="center")
                    self._inline_item_ids.append(iid2)
                    x += sep_w

    def _get_inline_parts(self, now, p):
        """Return list of (text, color) tuples for active items."""
        fc = p.get("font_color", p.get("date_color", TEXT))
        def c(key, default): return p.get(key, fc if key not in ("hol_color","par_color") else default)
        parts = []
        if p.get("show_weekday", True):
            parts.append((get_weekday_heb(), c("wd_color", fc)))
        if p.get("show_heb_date", True):
            hd = get_heb_date(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
            if hd: parts.append((fmt_heb_date(*hd), c("hd_color", fc)))
        if p.get("show_greg_date", True):
            parts.append((now.strftime("%d/%m/%Y"), c("gd_color", fc)))
        if p.get("show_holiday", True) and self._hol_cache:
            parts.append((f"🕍 {self._hol_cache}", c("hol_color", GOLD)))
        if p.get("show_parasha", True) and self._par_cache:
            parts.append((f"פרשת {self._par_cache}", c("par_color", LBLUE)))
        tor, haf = self._torah_cache
        if p.get("show_torah_reading", False) and tor:
            parts.append((tor, p.get("tor_color", "#aaffaa")))
        if p.get("show_haftara", False) and haf:
            parts.append((haf, p.get("haf_color", "#aaffcc")))
        pr = self._prayer_cache
        if p.get("show_yaaleh_veyavo", False) and pr.get("yaaleh_veyavo"):
            parts.append((pr["yaaleh_veyavo"], p.get("yaaleh_color", "#ffdd88")))
        if p.get("show_morid_hatal", False) and pr.get("morid_hatal"):
            parts.append((pr["morid_hatal"], p.get("morid_tal_color", "#88ddff")))
        if p.get("show_mashiv_haruach", False) and pr.get("mashiv_haruach"):
            parts.append((pr["mashiv_haruach"], p.get("mashiv_color", "#88ccff")))
        if p.get("show_vten_tal_umatar", False) and pr.get("vten_tal_umatar"):
            parts.append((pr["vten_tal_umatar"], p.get("vten_color", "#ffcc88")))
        if p.get("show_daf_yomi", False) and self._daf_cache:
            parts.append((self._daf_cache, p.get("daf_color", "#ccaaff")))
        return parts

    def _get_inline_text(self, now, p):
        """Build flat text string (used for scroll mode)."""
        sep = self._sep
        return sep.join(t for t, c in self._get_inline_parts(now, p))

    def tick(self):
        now = get_now(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
        p = self.pc

        # Update caches
        if p.get("show_holiday", True):
            self._hol_cache = get_today_holiday(israel=p.get("israel", True)) or ""
        if p.get("show_parasha", True):
            if self._par_last != now.date():
                self._par_cache = get_parasha(israel=p.get("israel", True)) or ""
                self._par_last = now.date()

        # New fields — update once per minute
        needs_new = not hasattr(self, "_extra_last") or self._extra_last != now.date()
        if needs_new:
            self._extra_last = now.date()
            self._prayer_cache   = get_prayer_additions()
            self._torah_cache    = get_torah_reading(israel=p.get("israel", True))
            self._daf_cache      = get_daf_yomi()

        if self._layout_mode == "inline":
            self._tick_inline(now, p)
        else:
            self._tick_stacked(now, p)

    def _tick_stacked(self, now, p):
        if hasattr(self, "wd_var"):
            self.wd_var.set(get_weekday_heb() if p.get("show_weekday", True) else "")
        if hasattr(self, "hd_var"):
            hd = get_heb_date(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
            self.hd_var.set(fmt_heb_date(*hd) if hd else "")
        if hasattr(self, "gd_var"):
            self.gd_var.set(now.strftime("%d/%m/%Y"))

        sp = self._line_spacing

        # Holiday: show/hide label dynamically (no gap when empty)
        if hasattr(self, "hol_var") and hasattr(self, "_hol_lbl"):
            hol = self._hol_cache
            if hol:
                self.hol_var.set(f"🕍 {hol}")
                # Pack holiday before parasha if not already packed
                if not self._hol_lbl.winfo_ismapped():
                    if hasattr(self, "_par_lbl"):
                        self._hol_lbl.pack(before=self._par_lbl, pady=sp)
                    else:
                        self._hol_lbl.pack(pady=sp)
            else:
                self.hol_var.set("")
                if self._hol_lbl.winfo_ismapped():
                    self._hol_lbl.pack_forget()

        if hasattr(self, "par_var"):
            par = self._par_cache
            self.par_var.set(f"פרשת {par}" if par else "")

        # ── שדות חדשים — dynamic show/hide ──
        def _dyn_lbl(has_var, has_lbl, text, lbl_attr):
            """Show label when text is non-empty, hide when empty."""
            if not hasattr(self, has_var): return
            lbl = getattr(self, lbl_attr, None)
            if lbl is None: return
            if text:
                getattr(self, has_var).set(text)
                if not lbl.winfo_ismapped():
                    lbl.pack(pady=sp)
            else:
                getattr(self, has_var).set("")
                if lbl.winfo_ismapped():
                    lbl.pack_forget()

        if p.get("show_torah_reading", False):
            tor_text, _ = self._torah_cache
            _dyn_lbl("tor_var", "_tor_lbl", tor_text, "_tor_lbl")

        if p.get("show_haftara", False):
            _, haf_text = self._torah_cache
            _dyn_lbl("haf_var", "_haf_lbl", haf_text, "_haf_lbl")

        pr = self._prayer_cache
        if p.get("show_yaaleh_veyavo", False):
            _dyn_lbl("yaaleh_var", "_yaaleh_lbl", pr.get("yaaleh_veyavo",""), "_yaaleh_lbl")
        if p.get("show_morid_hatal", False):
            _dyn_lbl("morid_tal_var", "_morid_tal_lbl", pr.get("morid_hatal",""), "_morid_tal_lbl")
        if p.get("show_mashiv_haruach", False):
            _dyn_lbl("mashiv_var", "_mashiv_lbl", pr.get("mashiv_haruach",""), "_mashiv_lbl")
        if p.get("show_vten_tal_umatar", False):
            _dyn_lbl("vten_var", "_vten_lbl", pr.get("vten_tal_umatar",""), "_vten_lbl")
        if p.get("show_daf_yomi", False):
            if hasattr(self, "daf_var"):
                self.daf_var.set(self._daf_cache)

    def _tick_inline(self, now, p):
        if self._scroll_inline and hasattr(self, "_canvas"):
            text = self._get_inline_text(now, p)
            self._canvas.itemconfig(self._scroll_text_id, text=text)
            self._do_scroll()
        else:
            parts = self._get_inline_parts(now, p)
            self._rebuild_inline_lines(parts)

    def _do_scroll(self):
        if not hasattr(self, "_canvas") or not self._scroll_running:
            return
        try:
            p = self.pc
            w = p.get("width", 280)
            speed = max(1, self._scroll_speed)
            self._scroll_x -= speed / 10.0
            # Get text width and reset when off screen
            bbox = self._canvas.bbox(self._scroll_text_id)
            if bbox and bbox[2] < 0:
                self._scroll_x = float(w)
            self._canvas.coords(self._scroll_text_id,
                                  self._scroll_x, (self._fs + 20) // 2)
        except tk.TclError:
            pass


# ── חלונית שעון ──────────────────────────────────────────────────────────────
class TimePW(PW):
    def build(self):
        bg=self._bg(); p=self.pc
        ff=p.get("font_family","Arial")
        # Support unified font_color (new) or separate clock_color/date_color (legacy)
        fc=p.get("font_color",None)
        cc=fc if fc else p.get("clock_color",BLUE)
        dc=fc if fc else p.get("date_color",TEXT)
        if p.get("clock_style","digital")=="analog":
            self._build_analog(bg,ff,cc,dc)
        else:
            self._build_digital(bg,ff,cc,dc)

    def _build_digital(self,bg,ff,cc,dc):
        p=self.pc
        wrap=tk.Frame(self._content,bg=bg)
        wrap.pack(expand=True)
        # Unified font_size: clock uses it directly, date elements use ~40% of it
        fs_base=p.get("font_size",p.get("time_font_size",42))
        fs_date=max(10,int(fs_base*0.38))
        if p.get("show_time",True):
            self.t_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.t_var,
                font=(ff,fs_base,"bold"),
                fg=cc,bg=bg).pack(pady=(8,2))
        if p.get("show_weekday",True):
            self.wd_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.wd_var,
                font=(ff,fs_date),fg=dc,bg=bg).pack(pady=1)
        if p.get("show_heb_date",True):
            self.hd_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.hd_var,
                font=(ff,fs_date),fg=dc,bg=bg).pack(pady=1)
        if p.get("show_greg_date",True):
            self.gd_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.gd_var,
                font=(ff,fs_date),fg=dc,bg=bg).pack(pady=1)
        if p.get("show_holiday",True):
            self.hol_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.hol_var,
                font=(ff,fs_date,"bold"),fg=GOLD,bg=bg).pack(pady=1)
        if p.get("show_parasha",True):
            self.par_var=tk.StringVar()
            tk.Label(wrap,textvariable=self.par_var,
                font=(ff,fs_date),fg=LBLUE,bg=bg).pack(pady=1)
        self.tick()

    def _build_analog(self,bg,ff,cc,dc):
        p=self.pc
        pt = int(p.get("pad_top",0)); pb = int(p.get("pad_bottom",0))
        pl = int(p.get("pad_left",0)); pr = int(p.get("pad_right",0))
        w=max(10, p.get("width",280) - pl - pr)
        h=max(10, p.get("height",280) - pt - pb)
        has_date = p.get("show_heb_date",True) or p.get("show_greg_date",True)
        cvh = h if not has_date else max(40, int(h*0.82))
        self.cv=tk.Canvas(self._content,width=w,height=cvh,bg=bg,highlightthickness=0)
        self.cv.pack()
        if has_date:
            self.dt_var=tk.StringVar()
            tk.Label(self._content,textvariable=self.dt_var,font=(ff,max(10,int(h*0.07))),
                     fg=dc,bg=bg).pack()
        self.tick()

    def tick(self):
        now=datetime.now(); p=self.pc
        if p.get("clock_style","digital")=="analog":
            self._draw_analog(now)
        else:
            self._upd_digital(now)

    def _upd_digital(self,now):
        p=self.pc
        if hasattr(self,"t_var"):
            sec=":%S" if p.get("show_seconds",True) else ""
            fmt=f"%I:%M{sec} %p" if p.get("time_format","24")=="12" else f"%H:%M{sec}"
            self.t_var.set(now.strftime(fmt))
        if hasattr(self,"wd_var"):  self.wd_var.set(get_weekday_heb())
        if hasattr(self,"hd_var"):
            hd=get_heb_date(self.dsp.cfg.d)
            self.hd_var.set(fmt_heb_date(*hd) if hd else "")
        if hasattr(self,"gd_var"): self.gd_var.set(now.strftime("%d/%m/%Y"))
        if hasattr(self,"hol_var"):
            hol=get_today_holiday(israel=p.get("israel",True))
            self.hol_var.set(f"🕍 {hol}" if hol else "")
        if hasattr(self,"par_var"):
            # Update parasha only once per minute to save CPU
            if not hasattr(self,"_par_cache") or self._par_last!=now.date():
                self._par_cache=get_parasha(israel=p.get("israel",True))
                self._par_last=now.date()
            par=self._par_cache
            self.par_var.set(f"פרשת {par}" if par else "")

    def _draw_analog(self,now):
        if not hasattr(self,"cv"): return
        self.cv.delete("all")
        cw=self.cv.winfo_width(); ch=self.cv.winfo_height()
        p=self.pc
        if cw<10:
            cw=p.get("width",280); ch=int(p.get("height",280)*0.82)
        _draw_analog_clock(self.cv, p, now, cw, ch, transparent_bg=False)
        if hasattr(self,"dt_var"):
            parts=[]
            if p.get("show_heb_date",True):
                hd=get_heb_date(self.dsp.cfg.d)
                if hd: parts.append(fmt_heb_date(*hd))
            if p.get("show_greg_date",True): parts.append(now.strftime("%d/%m/%Y"))
            self.dt_var.set(" | ".join(parts))

# ── חלונית טקסט ──────────────────────────────────────────────────────────────
class TextPW(PW):
    """Text panel (widget-based, opaque bg-color panels).
    The panel owns a Canvas widget that provides natural clipping to panel bounds.
    Seamless loop: two copies of text placed back-to-back.
    Per-segment styling: each segment is a separate canvas text item.
    """
    _RLM = "\u200f"

    def _fix_bidi(self, text):
        if not text: return text
        lines = []
        for line in text.split("\n"):
            has_heb = any('\u0590' <= ch <= '\u05FF' or '\uFB1D' <= ch <= '\uFB4F' for ch in line)
            lines.append(self._RLM + line if (has_heb and line) else line)
        return "\n".join(lines)

    def _get_active_content_segments(self):
        p = self.pc
        segs = p.get("content_segments", [])
        if not segs: return None
        result = []
        for s in segs:
            text = s.get("text","")
            if not text.strip(): continue
            dur = max(2, int(s.get("duration", p.get("segment_duration", 5))))
            result.append((text, dur))
        return result if result else None

    def _font_spec(self, p):
        ff = p.get("font_family","Arial"); fs = p.get("font_size",20)
        wt = "bold"   if p.get("bold",False)   else "normal"
        sl = "italic" if p.get("italic",False)  else "roman"
        return (ff, fs, wt, sl)

    def _seg_font_spec(self, p, sd):
        ff = sd.get("font_family", p.get("font_family","Arial"))
        fs = sd.get("font_size",   p.get("font_size",20))
        wt = "bold"   if sd.get("bold",   p.get("bold",False))   else "normal"
        sl = "italic" if sd.get("italic", p.get("italic",False))  else "roman"
        fc = sd.get("font_color",  p.get("font_color","#ffffff"))
        return (ff, fs, wt, sl), fc

    def _build_seg_items(self, p, horiz=False):
        """Return list of (text, font_tuple, color) with separator items between segments."""
        sep_space = p.get("seg_separator_space", True)
        sep_char  = (p.get("seg_separator_char","") or "").strip()
        def_font  = self._font_spec(p)
        def_fc    = p.get("font_color","#ffffff")

        segs = p.get("content_segments",[])
        raw_items = []
        if segs:
            for sd in segs:
                t = sd.get("text","")
                if not t.strip(): continue
                if horiz: t = t.replace("\n"," ").strip()
                font, fc = self._seg_font_spec(p, sd)
                raw_items.append((self._fix_bidi(t), font, fc))
        else:
            raw = p.get("content","")
            if horiz: raw = raw.replace("\n"," ").strip()
            if raw.strip():
                raw_items.append((self._fix_bidi(raw), def_font, def_fc))
        if not raw_items: return []
        if len(raw_items) == 1: return raw_items

        result = []
        for i, item in enumerate(raw_items):
            result.append(item)
            if i < len(raw_items) - 1:
                if horiz:
                    sep_txt = ("  " if sep_space else "") + (sep_char or "") + ("  " if sep_space else "")
                    result.append((sep_txt or "   ", def_font, def_fc))
                else:
                    sep_lines = []
                    if sep_space: sep_lines.append("")
                    if sep_char:  sep_lines.append(sep_char)
                    if sep_space and sep_char: sep_lines.append("")
                    if sep_lines:
                        result.append((self._fix_bidi("\n".join(sep_lines)), def_font, def_fc))
        return result

    def _compute_segments(self, text, ff, fs, wt, sl, justify, wrap, H):
        tmp = tk.Canvas(self._content, width=1, height=1)
        tid = tmp.create_text(0, 0, text=text, font=(ff,fs,wt,sl), width=wrap, anchor="nw")
        tmp.update_idletasks()
        bb = tmp.bbox(tid); tmp.destroy()
        if not bb: return [text]
        if bb[3]-bb[1] <= H: return [text]
        lines = text.split("\n"); segments = []; buf = []
        for line in lines:
            buf.append(line)
            if len(buf) * int(fs * 1.5) >= H:
                segments.append("\n".join(buf[:-1]) if len(buf) > 1 else "\n".join(buf))
                buf = [line]
        if buf: segments.append("\n".join(buf))
        return segments if segments else [text]

    def _draw_segment(self):
        if not getattr(self,"_segments",None): return
        p = self.pc; W = p.get("width",350); H = p.get("height",180)
        pt2, pb2, pl2, pr2 = _get_pads(p, 14)
        content_w = max(4, W - pl2 - pr2); content_h = max(4, H - pt2 - pb2)
        align = p.get("align","right")
        j = {"right":"right","left":"left","center":"center"}.get(align,"right")
        self._cv.delete("all")
        seg_idx = self._seg_idx % len(self._segments)
        segs_cfg = p.get("content_segments",[])
        if segs_cfg and seg_idx < len(segs_cfg):
            sf, sfc = self._seg_font_spec(p, segs_cfg[seg_idx])
        else:
            sf = self._font_spec(p); sfc = p.get("font_color","#ffffff")
        seg_text = self._segments[seg_idx]
        cx2 = pl2 + content_w // 2; cy2 = pt2 + content_h // 2
        self._cv.create_text(cx2, cy2, text=seg_text, font=sf, fill=sfc, justify=j,
                             width=content_w, anchor="center")

    def build(self):
        bg = self._bg(); p = self.pc
        raw_mode = p.get("scroll_mode","scroll_up")
        if raw_mode == "scroll": raw_mode = "scroll_up"
        self._mode = raw_mode

        pt, pb, pl, pr = _get_pads(p, 14)
        align = p.get("align","right")
        j = {"right":"right","left":"left","center":"center"}.get(align,"right")
        W = p.get("width",350); H = p.get("height",180)
        content_w = max(4, W - pl - pr)
        content_h = max(4, H - pt - pb)
        cx = pl + content_w // 2

        self._cv = tk.Canvas(self._content, bg=bg, highlightthickness=0, width=W, height=H)
        self._cv.pack(fill="both", expand=True)
        self._scroll_tids = []; self._tid = None; self._needs_scroll = False

        horiz = (raw_mode == "scroll_right")
        seg_items = self._build_seg_items(p, horiz=horiz)
        if not seg_items:
            seg_items = [(self._fix_bidi(p.get("content","")), self._font_spec(p), p.get("font_color","#ffffff"))]
        self._seg_items_cache = seg_items
        cs = self._get_active_content_segments()

        if raw_mode == "static":
            cy_now = pt + 4
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self._cv.create_text(cx, cy_now, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n")
                self._cv.update_idletasks()
                bb = self._cv.bbox(tid)
                cy_now += ((bb[3]-bb[1]) if bb else seg_font[1]+4) + 4

        elif raw_mode == "scroll_up":
            GAP = 30
            heights = []
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self._cv.create_text(cx, H + 9000, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n")
                self._cv.update_idletasks()
                bb = self._cv.bbox(tid)
                heights.append((bb[3]-bb[1]) if bb else seg_font[1]+4)
                self._cv.delete(tid)
            offsets = []; cur_dy = 0
            for h in heights: offsets.append(cur_dy); cur_dy += h + 4
            total_h = cur_dy
            stride = total_h + GAP
            self._th = total_h; self._loop_stride = stride
            self._needs_scroll = total_h > content_h

            start_y = float(H)
            self._anchor_y = start_y
            self._scroll_tids = []
            for copy_num in range(2):
                copy_base_dy = copy_num * stride
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dy = copy_base_dy + offsets[i]
                    tid = self._cv.create_text(cx, start_y + dy, text=seg_text,
                        font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n")
                    self._scroll_tids.append((tid, dy))

        elif raw_mode == "scroll_right":
            # "גלילה ימינה" = text moves rightward: enters from left, exits right.
            GAP = 60
            mid_y = pt + content_h // 2
            widths = []
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self._cv.create_text(W + 9000, mid_y, text=seg_text,
                    font=seg_font, fill=seg_fc, anchor="w")
                self._cv.update_idletasks()
                bb = self._cv.bbox(tid)
                widths.append((bb[2]-bb[0]) if bb else 80)
                self._cv.delete(tid)
            offsets_x = []; cur_dx = 0
            for w in widths: offsets_x.append(cur_dx); cur_dx += w
            total_w = cur_dx; stride_x = total_w + GAP
            self._th = total_w; self._loop_stride_x = stride_x
            self._needs_scroll = total_w > content_w
            # Start: first copy starts just off the LEFT edge of the canvas (negative x)
            start_x = float(-total_w - GAP)
            self._anchor_x = start_x
            self._scroll_tids = []
            for copy_num in range(2):
                copy_base_dx = copy_num * stride_x
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dx = copy_base_dx + offsets_x[i]
                    tid = self._cv.create_text(start_x + dx, mid_y,
                        text=seg_text, font=seg_font, fill=seg_fc, anchor="w")
                    self._scroll_tids.append((tid, dx))

        elif raw_mode == "segments":
            self._seg_idx = 0; self._seg_last = time.time()
            segs_cfg = p.get("content_segments",[])
            if cs is not None:
                self._content_segs = cs
                self._segments = [self._fix_bidi(t) for t, _ in cs]
                self._seg_durations = [d for _, d in cs]
            else:
                self._content_segs = None
                raw = p.get("content","")
                ff,fs,wt,sl = self._font_spec(p)
                self._segments = self._compute_segments(raw, ff, fs, wt, sl, j, content_w, content_h)
                self._seg_durations = [max(2, p.get("segment_duration",5))] * len(self._segments)
            self._draw_segment()

    def tick(self):
        p = self.pc
        mode = p.get("scroll_mode","scroll_up")
        if mode == "scroll": mode = "scroll_up"

        if mode == "static":
            return

        elif mode == "scroll_up":
            if not self._scroll_tids: return
            try:
                W = p.get("width",350); H = p.get("height",180)
                pt, pb, pl, pr = _get_pads(p, 14)
                cx2 = pl + (W - pl - pr) // 2
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_y -= spd
                stride = getattr(self, "_loop_stride", self._th + 30)
                if self._anchor_y < -stride:
                    self._anchor_y += stride
                for tid, dy in self._scroll_tids:
                    self._cv.coords(tid, cx2, self._anchor_y + dy)
            except: pass

        elif mode == "scroll_right":
            if not self._scroll_tids: return
            try:
                W2 = p.get("width",350); H2 = p.get("height",180)
                pt, pb, pl, pr = _get_pads(p, 14)
                mid_y = pt + (H2 - pt - pb) // 2
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_x += spd  # text moves rightward
                stride = getattr(self, "_loop_stride_x", self._th + 60)
                W2 = p.get("width", 350)
                if self._anchor_x > W2 + stride:
                    self._anchor_x -= stride
                for tid, dx in self._scroll_tids:
                    self._cv.coords(tid, self._anchor_x + dx, mid_y)
            except: pass

        elif mode == "segments":
            if not hasattr(self,"_cv"): return
            now = time.time()
            seg_durs = getattr(self,"_seg_durations",[max(2,p.get("segment_duration",5))])
            dur = seg_durs[self._seg_idx % max(1,len(seg_durs))]
            cs = self._get_active_content_segments()
            if cs is not None and hasattr(self,"_content_segs"):
                new_texts = [self._fix_bidi(t) for t,_ in cs]
                new_durs  = [d for _,d in cs]
                if new_texts != getattr(self,"_segments",[]) or new_durs != seg_durs:
                    self._segments = new_texts; self._seg_durations = new_durs
                    self._content_segs = cs; self._seg_idx = 0
                    self._draw_segment(); self._seg_last = now; return
            if now - self._seg_last >= dur:
                self._seg_idx = (self._seg_idx + 1) % max(1, len(getattr(self,"_segments",[])))
                self._draw_segment(); self._seg_last = now


# ── חלונית מודעה ──────────────────────────────────────────────────────────────
class AdPW(PW):
    def build(self):
        bg=self._bg(); p=self.pc
        self._imgs=[]; self._img_meta=[]; self._cur=0; self._last=0.0
        self.lbl=tk.Label(self._content,bg=bg,bd=0)
        self.lbl.pack(fill="both",expand=True)
        self._load(); self._show()

    def _load(self):
        if not PIL_AVAILABLE: return
        p=self.pc; w=p.get("width",380); h=p.get("height",280)
        self._imgs=[]; self._img_meta=[]
        self._gif_mode=False; self._gif_frame_idx=0; self._gif_delays=[]; self._gif_last=0.0
        raw_images=p.get("images",[])

        def _fit(img_rgba):
            fit=p.get("fit_mode","contain")
            if fit=="contain":
                img_rgba.thumbnail((w,h),Image.LANCZOS)
                try:
                    _bgc=p.get("bg_color","#000000").lstrip("#")
                    _bgrgb=tuple(int(_bgc[i:i+2],16) for i in (0,2,4))
                except: _bgrgb=(0,0,0)
                bg_im=Image.new("RGB",(w,h),_bgrgb)
                ox=(w-img_rgba.width)//2; oy=(h-img_rgba.height)//2
                bg_im.paste(img_rgba.convert("RGBA"),(ox,oy),img_rgba.convert("RGBA"))
                return bg_im
            elif fit=="cover":
                ratio=max(w/img_rgba.width,h/img_rgba.height)
                img_rgba=img_rgba.resize((int(img_rgba.width*ratio),int(img_rgba.height*ratio)),Image.LANCZOS)
                x2=(img_rgba.width-w)//2; y2=(img_rgba.height-h)//2
                return img_rgba.crop((x2,y2,x2+w,y2+h)).convert("RGB")
            else:
                return img_rgba.resize((w,h),Image.LANCZOS).convert("RGB")

        for entry in raw_images:
            if isinstance(entry,str): path=entry; meta={}
            elif isinstance(entry,dict): path=entry.get("path",""); meta=entry
            else: continue
            if not path or not os.path.exists(path): continue
            ext=os.path.splitext(path)[1].lower()
            try:
                if ext==".gif":
                    gif=Image.open(path)
                    frame_count=getattr(gif,"n_frames",1)
                    if frame_count>1 and len(raw_images)==1:
                        # Single animated GIF: animate frame-by-frame
                        self._gif_mode=True
                        while True:
                            try:
                                dur=gif.info.get("duration",100)
                                self._gif_delays.append(max(50,int(dur)))
                                self._imgs.append(ImageTk.PhotoImage(_fit(gif.convert("RGBA"))))
                                self._img_meta.append(meta)
                                gif.seek(gif.tell()+1)
                            except EOFError: break
                    else:
                        self._imgs.append(ImageTk.PhotoImage(_fit(gif.convert("RGBA"))))
                        self._img_meta.append(meta)
                elif ext==".pdf":
                    try:
                        from pdf2image import convert_from_path
                        pages=convert_from_path(path,dpi=150)
                        for page in pages:
                            self._imgs.append(ImageTk.PhotoImage(_fit(page.convert("RGBA"))))
                            self._img_meta.append(meta)
                    except Exception: pass
                elif ext==".mp4":
                    try:
                        import cv2
                        cap=cv2.VideoCapture(path)
                        total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        step=max(1,total//30); idx=0
                        while len(self._imgs)<len(raw_images)*30:
                            cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
                            ret,frame=cap.read()
                            if not ret: break
                            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                            self._imgs.append(ImageTk.PhotoImage(_fit(Image.fromarray(rgb).convert("RGBA"))))
                            self._img_meta.append(meta)
                            idx+=step
                            if idx>=total: break
                        cap.release()
                    except Exception: pass
                else:
                    img=Image.open(path).convert("RGBA")
                    self._imgs.append(ImageTk.PhotoImage(_fit(img)))
                    self._img_meta.append(meta)
            except: pass

    def _active_indices(self):
        now=datetime.now(); today=now.date()
        cur_t=now.hour*60+now.minute; active=[]
        for i,meta in enumerate(self._img_meta):
            if not meta: active.append(i); continue
            df=meta.get("date_from",""); dt=meta.get("date_to","")
            if df:
                try:
                    from datetime import date as _d
                    if today<_d.fromisoformat(df): continue
                except: pass
            if dt:
                try:
                    from datetime import date as _d
                    if today>_d.fromisoformat(dt): continue
                except: pass
            wds=meta.get("weekdays",[])
            if wds and today.weekday() not in wds: continue
            tf=meta.get("time_from",""); tt=meta.get("time_to","")
            if tf:
                try:
                    hh,mm=map(int,tf.split(":")); 
                    if cur_t<hh*60+mm: continue
                except: pass
            if tt:
                try:
                    hh,mm=map(int,tt.split(":"))
                    if cur_t>hh*60+mm: continue
                except: pass
            active.append(i)
        return active

    def _show(self):
        active=self._active_indices()
        if active:
            idx=active[self._cur%len(active)]
            self.lbl.configure(image=self._imgs[idx],text="",bg=self._bg())
        else:
            bg=self._bg()
            self.lbl.configure(image="",text="\U0001f4f7\n\u05d0\u05d9\u05df \u05ea\u05de\u05d5\u05e0\u05d5\u05ea\n\u05d4\u05d5\u05e1\u05e3 \u05d1\u05d4\u05d2\u05d3\u05e8\u05d5\u05ea",
                fg=TEXT2,bg=bg,font=("Arial",13),justify="center")

    def tick(self):
        now=time.time()
        if getattr(self,"_gif_mode",False) and self._imgs:
            delay_sec=(self._gif_delays[self._gif_frame_idx] if self._gif_delays else 100)/1000.0
            if now-self._gif_last>=delay_sec:
                self._gif_last=now
                self._gif_frame_idx=(self._gif_frame_idx+1)%len(self._imgs)
                try: self.lbl.configure(image=self._imgs[self._gif_frame_idx],text="",bg=self._bg())
                except: pass
        else:
            iv=self.pc.get("interval",5)
            if now-self._last>=iv:
                active=self._active_indices()
                if active: self._cur=(self._cur+1)%len(active)
                self._show(); self._last=now


# ── חלונית זמני הלכה ─────────────────────────────────────────────────────────
class ZmanimPW(PW):
    def __init__(self,parent,pc,dsp):
        self._zcalc = _make_zmanim_calc(dsp.cfg.d)
        self._zdata={}; self._zdate=None; self._tvars={}; self._ttime_labels={}
        self._scroll_y = 0; self._scroll_after = None
        super().__init__(parent,pc,dsp)

    def _fmt_time(self, z):
        """Format a zmanim datetime per 12/24 setting."""
        p = self.pc
        try:
            if hasattr(z,"tzinfo") and z.tzinfo:
                try:
                    import pytz as _pytz
                    ltz = _pytz.timezone(self.dsp.cfg.d["location"].get("tz","Asia/Jerusalem"))
                    z = z.astimezone(ltz)
                except: pass
            fmt = "%I:%M %p" if p.get("zmanim_time_format","24") == "12" else "%H:%M"
            return z.strftime(fmt).lstrip("0") if fmt.startswith("%I") else z.strftime(fmt)
        except: return "--:--"

    def _label_for(self, k, uid=None):
        """Get display name for a zmanim key, checking effective list first."""
        # If uid given, look up in effective entries
        if uid and uid != k:
            eff = get_effective_zmanim_entries(self.dsp.cfg.d)
            for e_uid, e_key, e_name, e_method in eff:
                if e_uid == uid: return e_name
        custom = self.pc.get("zmanim_custom_names", {})
        return custom.get(k, ZMANIM_KEYS.get(k, k))

    def _get_show_entries(self):
        """Return list of (uid, key, label) to display, in config order."""
        p = self.pc
        eff = get_effective_zmanim_entries(self.dsp.cfg.d)
        show_items = p.get("show_items", [e[0] for e in eff])
        # Build uid→entry map
        uid_map = {e[0]: e for e in eff}
        key_map = {e[1]: e for e in eff}  # fallback for legacy key-based show_items
        result = []
        for uid in show_items:
            if uid in uid_map:
                e_uid, e_key, e_name, e_method = uid_map[uid]
                result.append((e_uid, e_key, e_name))
            elif uid in key_map:  # legacy key
                e_uid, e_key, e_name, e_method = key_map[uid]
                result.append((e_uid, e_key, e_name))
        return result

    def build(self):
        bg=self._bg(); p=self.pc
        # Per-element fonts
        lf  = p.get("zmanim_label_font",  p.get("font_family","Arial"))
        ls  = p.get("zmanim_label_size",  p.get("font_size",14))
        tf  = p.get("zmanim_time_font",   p.get("font_family","Arial"))
        ts  = p.get("zmanim_time_size",   p.get("font_size",14))
        lc  = p.get("label_color", p.get("font_color","#9090cc"))
        tc  = p.get("time_color",  p.get("title_color",BLUE))
        disp_mode  = p.get("zmanim_display_mode","rows")   # "rows" or "inline"
        row_layout = p.get("zmanim_row_layout","same_row") # "same_row" or "stacked"
        row_sp     = int(p.get("zmanim_row_spacing",4))
        scroll_dir = p.get("zmanim_scroll","none")         # "none","up","down"

        if p.get("show_title",True):
            tk.Label(self._content,text=p.get("title","זמני היום"),
                font=(tf,ts+4,"bold"),fg=tc,bg=bg).pack(pady=(4,2))
            if p.get("show_separator",True):
                tk.Frame(self._content,bg=p.get("border_color",BLUE),height=1).pack(fill="x",padx=0,pady=2)

        show_entries = self._get_show_entries()  # list of (uid, key, label)
        self._tvars={}; self._ttime_labels={}

        # ── Inline mode: Canvas with scrolling text ──
        if disp_mode == "inline":
            sep = p.get("zmanim_inline_sep"," | ")
            self._inline_sep = sep
            W = p.get("width",360); H = p.get("height",490) - (ts+8 if p.get("show_title",True) else 0)
            if scroll_dir != "none":
                self._inline_cv = tk.Canvas(self._content,bg=bg,highlightthickness=0,width=W,height=max(20,ts+8))
                self._inline_cv.pack(fill="both",expand=True)
                self._inline_x = float(W)
                self._inline_id = self._inline_cv.create_text(W, (ts+8)//2, text="", font=(tf,ts), fill=tc, anchor="w")
                self._inline_scroll_dir = scroll_dir
            else:
                self._inline_var = tk.StringVar()
                tk.Label(self._content,textvariable=self._inline_var,font=(tf,ts),fg=tc,bg=bg,
                         wraplength=W-10).pack(expand=True)
            self._calc_zmanim()
            return

        # ── Rows mode ──
        if scroll_dir != "none":
            self._scroll_cv = tk.Canvas(self._content,bg=bg,highlightthickness=0)
            self._scroll_cv.pack(fill="both",expand=True)
            self._scroll_inner = tk.Frame(self._scroll_cv,bg=bg)
            self._scroll_win = self._scroll_cv.create_window(0,0,anchor="nw",window=self._scroll_inner)
            self._scroll_inner.bind("<Configure>",lambda e: self._scroll_cv.configure(scrollregion=self._scroll_cv.bbox("all")))
            container = self._scroll_inner
            self._scroll_dir = scroll_dir
            self._scroll_offset = 0.0
            self._scroll_speed = max(1, int(p.get("zmanim_scroll_speed",2)))
        else:
            container = tk.Frame(self._content,bg=bg)
            container.pack(fill="both",expand=True)

        for uid, key, label_text in show_entries:
            tv = tk.StringVar(value="--:--")
            self._tvars[uid] = tv

            if row_layout == "stacked":
                outer = tk.Frame(container,bg=bg,pady=row_sp//2)
                outer.pack(fill="x")
                tk.Label(outer,text=label_text,font=(lf,ls),fg=lc,bg=bg,anchor="e").pack(fill="x",padx=2)
                tl = tk.Label(outer,textvariable=tv,font=(tf,ts,"bold"),fg=tc,bg=bg,anchor="e")
                tl.pack(fill="x",padx=2)
            else:
                row = tk.Frame(container,bg=bg,pady=row_sp//2)
                row.pack(fill="x")
                tl = tk.Label(row,textvariable=tv,font=(tf,ts,"bold"),fg=tc,bg=bg,width=6,anchor="w")
                tl.pack(side="left",padx=(2,1))
                tk.Label(row,text=label_text,font=(lf,ls),fg=lc,bg=bg,anchor="e").pack(side="right",fill="x",expand=True,padx=(0,2))
            self._ttime_labels[uid] = tl

        self._calc_zmanim()

    def _calc_zmanim(self):
        today=date.today()
        try: self._zcalc = _make_zmanim_calc(self.dsp.cfg.d)
        except: pass
        global_zdata = self._zcalc.calc(today)
        self._zdate = today
        # Build per-uid zdata: supports per-key method overrides and duplicate entries
        eff = get_effective_zmanim_entries(self.dsp.cfg.d)
        loc = self.dsp.cfg.d.get("location", {})
        self._zdata_uid = {}  # uid → datetime value
        for uid, key, name, method_override in eff:
            if method_override:
                try:
                    alt_calc = ZmanimCalc(loc.get("lat",31.7683), loc.get("lng",35.2137),
                                         loc.get("elev",0), loc.get("tz","Asia/Jerusalem"),
                                         method=method_override)
                    alt_data = alt_calc.calc(today)
                    self._zdata_uid[uid] = alt_data.get(key)
                except:
                    self._zdata_uid[uid] = global_zdata.get(key)
            else:
                self._zdata_uid[uid] = global_zdata.get(key)
        self._zdata = global_zdata  # keep for highlight_next logic
        self._update_labels()

    def _update_labels(self):
        p = self.pc
        disp_mode = p.get("zmanim_display_mode","rows")
        tc = p.get("time_color",BLUE)
        tf = p.get("zmanim_time_font", p.get("font_family","Arial"))
        ts = p.get("zmanim_time_size", p.get("font_size",14))
        sep = p.get("zmanim_inline_sep"," | ")
        show_entries = self._get_show_entries()  # (uid, key, label)

        if disp_mode == "inline":
            parts = []
            for uid, key, label_text in show_entries:
                z = self._zdata_uid.get(uid) if hasattr(self,"_zdata_uid") else self._zdata.get(key)
                t_str = self._fmt_time(z) if z else "--:--"
                parts.append(f"{label_text} {t_str}")
            full_text = sep.join(parts)
            if hasattr(self,"_inline_var"):
                self._inline_var.set(full_text)
            elif hasattr(self,"_inline_id") and hasattr(self,"_inline_cv"):
                self._inline_cv.itemconfig(self._inline_id, text=full_text)
            return

        for uid, tv in self._tvars.items():
            z = self._zdata_uid.get(uid) if hasattr(self,"_zdata_uid") else None
            if z is None:
                # fallback: uid might be a key for legacy panels
                z = self._zdata.get(uid)
            tv.set(self._fmt_time(z) if z else "--:--")

        # Highlight next upcoming zman
        if p.get("highlight_next",True):
            now_t=datetime.now()
            next_uid=None; next_t=None
            zdata_to_check = self._zdata_uid if hasattr(self,"_zdata_uid") else {k:v for k,v in self._zdata.items()}
            for uid, z in zdata_to_check.items():
                if z and uid in self._tvars:
                    try:
                        zn=z.replace(tzinfo=None) if (hasattr(z,"tzinfo") and z.tzinfo) else z
                        if zn>now_t and (next_t is None or zn<next_t):
                            next_t=zn; next_uid=uid
                    except: pass
            hc=p.get("highlight_color",GOLD)
            for uid,lbl in self._ttime_labels.items():
                lbl.configure(fg=hc if uid==next_uid else tc)

    def tick(self):
        today = date.today()
        # Also recalc if calculation method changed since last calc
        cur_method = self.dsp.cfg.d.get("location",{}).get("zmanim_method","kosherzmanim")
        if today != self._zdate or getattr(self,"_last_method","") != cur_method:
            self._last_method = cur_method
            self._zdate = None  # force recalc
            self._calc_zmanim()
        else:
            self._update_labels()
        # Scrolling
        p = self.pc
        scroll_dir = p.get("zmanim_scroll","none")
        speed = max(1, int(p.get("zmanim_scroll_speed",2)))
        if scroll_dir != "none":
            if hasattr(self,"_scroll_cv") and hasattr(self,"_scroll_inner"):
                try:
                    total_h = self._scroll_inner.winfo_reqheight()
                    view_h  = self._scroll_cv.winfo_height() or 100
                    if total_h > view_h:
                        self._scroll_offset = getattr(self,"_scroll_offset",0.0)
                        if scroll_dir == "up":
                            self._scroll_offset += speed * 0.5
                            if self._scroll_offset >= total_h:
                                self._scroll_offset = 0.0
                        else:
                            self._scroll_offset -= speed * 0.5
                            if self._scroll_offset < 0:
                                self._scroll_offset = float(total_h)
                        frac = self._scroll_offset / max(1, total_h)
                        self._scroll_cv.yview_moveto(frac)
                except: pass
            elif hasattr(self,"_inline_cv") and hasattr(self,"_inline_id"):
                try:
                    W = p.get("width",360)
                    bb = self._inline_cv.bbox(self._inline_id)
                    tw = (bb[2]-bb[0]) if bb else W
                    if scroll_dir in ("up","down"):
                        self._inline_x -= speed
                        if self._inline_x < -(tw+20): self._inline_x = float(W+10)
                    self._inline_cv.coords(self._inline_id, self._inline_x, (p.get("zmanim_time_size",14)+8)//2)
                except: pass


# ── חלונית אלמנט עיצובי ──────────────────────────────────────────────────────
class ElemPW(PW):
    def build(self):
        bg=self._bg(); p=self.pc
        img_path=p.get("image_path","")
        w=p.get("width",200); h=p.get("height",200)
        if img_path and os.path.exists(img_path) and PIL_AVAILABLE:
            try:
                img=Image.open(img_path).convert("RGBA")
                fit=p.get("fit_mode","contain")
                if fit=="contain":
                    img.thumbnail((w,h),Image.LANCZOS)
                    ox=(w-img.width)//2; oy=(h-img.height)//2
                elif fit=="stretch":
                    img=img.resize((w,h),Image.LANCZOS)
                    ox=oy=0
                else:  # cover
                    ratio=max(w/img.width,h/img.height)
                    img=img.resize((int(img.width*ratio),int(img.height*ratio)),Image.LANCZOS)
                    ox=(w-img.width)//2; oy=(h-img.height)//2

                if p.get("bg_transparent",False):
                    # Composite image with gradient background for real transparency
                    from PIL import ImageDraw as _PID
                    comp=Image.new("RGBA",(w,h),(0,0,0,255))
                    _d=_PID.Draw(comp)
                    if self.dsp.cfg.d["display"].get("gradient",True):
                        py_pos=p.get("y",0)
                        for row in range(h):
                            t=min(1.0,max(0.0,(py_pos+row)/max(1,self.dsp.H)))
                            r=int(7+t*8); g=int(7+t*3); bv=int(20+t*20)
                            _d.line([(0,row),(w-1,row)],fill=(r,g,bv,255))
                    else:
                        bgc=self.dsp.cfg.d["display"].get("bg_color",BG)
                        bc=bgc.lstrip("#")
                        rgb=tuple(int(bc[i:i+2],16) for i in (0,2,4))
                        comp=Image.new("RGBA",(w,h),rgb+(255,))
                    comp.paste(img,(ox,oy),img)
                    disp_img=comp.convert("RGB")
                else:
                    disp_img=Image.new("RGB",(w,h))
                    try:
                        bg_rgb=tuple(int(bg.lstrip("#")[i:i+2],16) for i in (0,2,4))
                        disp_img=Image.new("RGB",(w,h),bg_rgb)
                    except: pass
                    disp_img.paste(img.convert("RGB"),(ox,oy))

                cv=tk.Canvas(self._content,width=w,height=h,bg=bg,
                             highlightthickness=0,bd=0)
                cv.pack(fill="both",expand=True)
                self._photo=ImageTk.PhotoImage(disp_img)
                cv.create_image(w//2,h//2,anchor="center",image=self._photo)
                return
            except: pass
        tk.Label(self._content,text="\U0001f3a8\n\u05d0\u05dc\u05de\u05e0\u05d8 \u05e2\u05d9\u05e6\u05d5\u05d1\u05d9",
            font=("Arial",12),fg=TEXT2,bg=bg,justify="center"
        ).pack(fill="both",expand=True)
    def tick(self): pass

# ── חלונית הודעה צפה ─────────────────────────────────────────────────────────
class NoticePW(PW):
    """Scrolling/static notice banner panel with enter/exit animations."""

    # ── Entry animation ───────────────────────────────────────────────────────
    def _start_enter_anim(self):
        anim = self.pc.get("anim_enter", "none")
        dur  = max(100, self.pc.get("anim_duration", 400))
        if anim == "none":
            return
        if anim == "fade_in":
            self._anim_fade(0.0, 1.0, dur)
        elif anim == "slide_up":
            self._anim_slide(0, self.pc.get("height", 80), 0, 0, dur)
        elif anim == "slide_down":
            self._anim_slide(0, -self.pc.get("height", 80), 0, 0, dur)
        elif anim == "slide_right":
            self._anim_slide(-self.pc.get("width", 900), 0, 0, 0, dur)
        elif anim == "slide_left":
            self._anim_slide(self.pc.get("width", 900), 0, 0, 0, dur)
        elif anim == "bounce":
            self._anim_bounce(dur)

    def start_exit_anim(self, on_done=None):
        """Start exit animation; call on_done() when complete."""
        anim = self.pc.get("anim_exit", "none")
        dur  = max(100, self.pc.get("anim_duration", 400))
        if anim == "none":
            if on_done: on_done()
            return
        if anim == "fade_out":
            self._anim_fade(1.0, 0.0, dur, on_done=on_done)
        elif anim == "slide_down":
            self._anim_slide(0, 0, 0, self.pc.get("height", 80), dur, on_done=on_done)
        elif anim == "slide_up":
            self._anim_slide(0, 0, 0, -self.pc.get("height", 80), dur, on_done=on_done)
        elif anim == "slide_right":
            self._anim_slide(0, 0, self.pc.get("width", 900), 0, dur, on_done=on_done)
        elif anim == "slide_left":
            self._anim_slide(0, 0, -self.pc.get("width", 900), 0, dur, on_done=on_done)

    def _anim_fade(self, alpha_from, alpha_to, dur_ms, on_done=None):
        """Fade using canvas window alpha via repeated alpha attribute."""
        steps = max(5, dur_ms // 16)
        delta = (alpha_to - alpha_from) / steps
        self._anim_alpha = alpha_from

        def _step(remaining):
            if not self.winfo_exists():
                return
            self._anim_alpha = max(0.0, min(1.0, self._anim_alpha + delta))
            try:
                # tkinter doesn't support per-widget alpha natively,
                # but we can approximate via wm_attributes on Toplevel.
                # For canvas-embedded windows we use a trick: tint bg towards bg_color
                pass  # alpha fade best-effort: just complete immediately on non-Toplevel
            except: pass
            if remaining > 0:
                self.after(16, lambda: _step(remaining - 1))
            else:
                if on_done: on_done()

        _step(steps)

    def _anim_slide(self, dx_from, dy_from, dx_to, dy_to, dur_ms, on_done=None):
        """Slide by adjusting the canvas window position."""
        if not hasattr(self, "_canvas_cid") or not self._canvas_cid:
            if on_done: on_done()
            return
        canvas = self.master  # bg_canvas
        steps  = max(5, dur_ms // 16)
        base_x = self.pc.get("x", 10)
        base_y = self.pc.get("y", 10)

        def _step(i):
            if not self.winfo_exists():
                return
            t = i / steps
            # Ease-out cubic
            t_e = 1 - (1 - t) ** 3
            cx = base_x + dx_from + (dx_to - dx_from) * t_e
            cy = base_y + dy_from + (dy_to - dy_from) * t_e
            try:
                canvas.coords(self._canvas_cid, cx, cy)
            except: pass
            if i < steps:
                self.after(16, lambda: _step(i + 1))
            else:
                try: canvas.coords(self._canvas_cid, base_x + dx_to, base_y + dy_to)
                except: pass
                if on_done: on_done()

        _step(0)

    def _anim_bounce(self, dur_ms):
        """Bounce entry: slide up from below with overshoot."""
        if not hasattr(self, "_canvas_cid") or not self._canvas_cid:
            return
        canvas = self.master
        h = self.pc.get("height", 80)
        base_x = self.pc.get("x", 10)
        base_y = self.pc.get("y", 10)
        steps = max(10, dur_ms // 16)

        def _bounce_ease(t):
            # Bounce easing
            if t < 1/2.75:
                return 7.5625 * t * t
            elif t < 2/2.75:
                t -= 1.5/2.75
                return 7.5625*t*t + 0.75
            elif t < 2.5/2.75:
                t -= 2.25/2.75
                return 7.5625*t*t + 0.9375
            else:
                t -= 2.625/2.75
                return 7.5625*t*t + 0.984375

        def _step(i):
            if not self.winfo_exists(): return
            t = _bounce_ease(i / steps)
            cur_y = base_y + h * (1 - t)
            try: canvas.coords(self._canvas_cid, base_x, cur_y)
            except: pass
            if i < steps:
                self.after(16, lambda: _step(i + 1))
            else:
                try: canvas.coords(self._canvas_cid, base_x, base_y)
                except: pass

        _step(0)

    def build(self):
        bg=self._bg(); p=self.pc
        ff=p.get("font_family","Arial")
        fs=p.get("font_size",26)
        fc=p.get("font_color",GOLD)
        bold="bold" if p.get("bold",True) else ""
        text=p.get("content","")
        w=p.get("width",900); h=p.get("height",80)

        self._scroll=p.get("scroll",True)
        self._speed=max(1,p.get("scroll_speed",2))
        self._dir=p.get("scroll_dir","rtl")
        self._canvas_cid = None  # set by display after create_window

        if self._scroll:
            self._cv=tk.Canvas(self._content,bg=bg,highlightthickness=0,
                               width=w,height=h)
            self._cv.pack(fill="both",expand=True)
            if self._dir=="rtl":
                self._tx=w
            else:
                self._tx=-100
            self._tid=self._cv.create_text(
                self._tx, h//2,
                text=text,
                font=(ff,fs,bold) if bold else (ff,fs),
                fill=fc, anchor="w" if self._dir=="rtl" else "e"
            )
            self._cv.update_idletasks()
            bb=self._cv.bbox(self._tid)
            self._tw=(bb[2]-bb[0]) if bb else len(text)*fs//2
        else:
            tk.Label(self._content,text=text,
                font=(ff,fs,bold) if bold else (ff,fs),
                fg=fc,bg=bg,anchor="center",justify="center",
                wraplength=w-20).pack(fill="both",expand=True,padx=10)

        # Kick off entry animation after a short delay (widget needs to be placed first)
        self.after(80, self._start_enter_anim)

    def tick(self):
        if not self._scroll: return
        try:
            w=self.pc.get("width",900)
            if self._dir=="rtl":
                self._tx-=self._speed
                if self._tx < -(self._tw+20):
                    self._tx=w+10
            else:
                self._tx+=self._speed
                if self._tx > w+self._tw+20:
                    self._tx=-(self._tw+10)
            self._cv.coords(self._tid,self._tx,self.pc.get("height",80)//2)
        except: pass

    def build_content_override(self, text):
        """Update displayed text without rebuilding the panel."""
        self.pc["content"] = text
        if getattr(self,"_scroll", True):
            try: self._cv.itemconfig(self._tid, text=text)
            except: pass
        else:
            for w in self.winfo_children(): w.destroy()
            self.build()

# ── חלונית הודעת מסך (מיוצבת) ─────────────────────────────────────────────────
class ScreenMsgPW(PW):
    """Positioned on-screen message panel — static styled text, not fullscreen."""
    def build(self):
        bg=self._bg(); p=self.pc
        ff=p.get("font_family","Arial")
        fs=p.get("font_size",28)
        fc=p.get("font_color",GOLD)
        bold="bold" if p.get("bold",True) else ""
        italic="italic" if p.get("italic",False) else ""
        text=p.get("content","")
        w=p.get("width",600); h=p.get("height",140)
        align=p.get("align","center")
        anch={"right":"e","left":"w","center":"center"}.get(align,"center")
        font=(ff,fs,bold,italic) if bold or italic else (ff,fs)
        self._lbl=tk.Label(self._content,text=text,font=font,fg=fc,bg=bg,
                 anchor=anch,justify=align,wraplength=w)
        self._lbl.pack(fill="both",expand=True)
    def tick(self): pass
    def build_content_override(self, text):
        self.pc["content"]=text
        try: self._lbl.configure(text=text)
        except: pass

# ── חלונית לוח זמנים ─────────────────────────────────────────────────────────
# HEB_WEEK_NAMES: שמות השבועות לפי הפרשיות (לסינון אירועים)
HEB_PARASHA_LIST = [
    "בראשית","נח","לך לך","וירא","חיי שרה","תולדות","ויצא","וישלח","וישב","מקץ",
    "ויגש","ויחי","שמות","וארא","בא","בשלח","יתרו","משפטים","תרומה","תצוה",
    "כי תשא","ויקהל","פקודי","ויקרא","צו","שמיני","תזריע","מצורע","אחרי מות",
    "קדושים","אמור","בהר","בחוקותי","במדבר","נשא","בהעלותך","שלח","קרח",
    "חקת","בלק","פינחס","מטות","מסעי","דברים","ואתחנן","עקב","ראה","שופטים",
    "כי תצא","כי תבוא","נצבים","וילך","האזינו","וזאת הברכה",
]

def _schedule_event_active(ev, now=None):
    """Return True if a schedule event dict is active right now.
    ev keys: name, date (YYYY-MM-DD or ""), time (HH:MM or ""),
    date_from/date_to (YYYY-MM-DD), weekdays (list 0-6), parshiyot (list of names),
    time_from/time_to (HH:MM)."""
    if now is None:
        now = datetime.now()
    today = now.date()
    cur_time = now.hour * 60 + now.minute

    # ── Specific date+time (one-off event) ──
    ev_date  = ev.get("date", "")
    ev_time  = ev.get("time", "")
    if ev_date:
        try:
            from datetime import date as _date
            d = _date.fromisoformat(ev_date)
            if d != today:
                return False
        except: pass
    if ev_time:
        try:
            hh, mm = map(int, ev_time.split(":"))
            # Show from ev_time for the rest of the day
            if cur_time < hh * 60 + mm:
                return False
        except: pass
    # ── Date range ──
    df = ev.get("date_from", ""); dt = ev.get("date_to", "")
    if df:
        try:
            from datetime import date as _date
            if today < _date.fromisoformat(df): return False
        except: pass
    if dt:
        try:
            from datetime import date as _date
            if today > _date.fromisoformat(dt): return False
        except: pass
    # ── Weekday filter ──
    wds = ev.get("weekdays", [])
    if wds and today.weekday() not in wds:
        return False
    # ── Parasha filter ──
    pars = ev.get("parshiyot", [])
    if pars:
        try:
            cur_par = get_parasha(israel=True) or ""
            if cur_par not in pars: return False
        except: pass
    # ── Time-of-day range ──
    tf = ev.get("time_from", ""); tt = ev.get("time_to", "")
    if tf:
        try:
            hh, mm = map(int, tf.split(":")); st = hh * 60 + mm
            if cur_time < st: return False
        except: pass
    if tt:
        try:
            hh, mm = map(int, tt.split(":")); en = hh * 60 + mm
            if cur_time > en: return False
        except: pass
    return True


class SchedulePW(PW):
    """Schedule panel — shows upcoming events for today (name right, time left).
    Filters: shows events that haven't passed yet, plus a 10-minute grace period.
    At rollover time (default 00:00, configurable) switches to show tomorrow's events.
    Supports bg_image: draws content on a Canvas so image stays visible behind text.
    """

    def build(self):
        p = self.pc
        W = p.get("width", 350); H = p.get("height", 200)
        # Determine canvas background:
        # - transparent → sample actual composited bg colour from _bg_pil
        # - bg_image    → black (image draws over it)
        # - opaque      → use bg_color setting
        if p.get("bg_transparent", False):
            bg = self._sample_canvas_bg()
        elif p.get("bg_image","") and os.path.exists(p.get("bg_image","")):
            bg = "#000000"
        else:
            bg = self._bg()
        self._cv = tk.Canvas(self._content, bg=bg, highlightthickness=0,
                             width=W, height=H)
        self._cv.pack(fill="both", expand=True)
        self._draw()

    def _sample_canvas_bg(self):
        """Sample the composited bg colour at this panel's centre for transparency."""
        try:
            bg_pil = getattr(self.dsp, "_bg_pil", None)
            if bg_pil:
                p = self.pc
                cx = p.get("x",0) + p.get("width",350)//2
                cy = p.get("y",0) + p.get("height",200)//2
                cx = max(0,min(cx,bg_pil.width-1)); cy = max(0,min(cy,bg_pil.height-1))
                r,g,b = bg_pil.getpixel((cx,cy))[:3]
                return f"#{r:02x}{g:02x}{b:02x}"
        except: pass
        return self.dsp.display.cget("bg") if hasattr(self.dsp,"display") else "#000000"

    def _get_display_date(self):
        """Return the 'logical today' date considering day rollover setting."""
        p = self.pc
        now = datetime.now()
        rollover_h = int(p.get("day_rollover_hour", 0))
        rollover_m = int(p.get("day_rollover_minute", 0))
        rollover_mins = rollover_h * 60 + rollover_m
        cur_mins = now.hour * 60 + now.minute
        if rollover_mins > 0 and cur_mins < rollover_mins:
            # Before rollover time — show tomorrow's events
            from datetime import timedelta
            return (now + timedelta(days=1)).date(), True
        return now.date(), False

    def _get_upcoming_events(self):
        """Return events that are upcoming or within 10-min grace period for display_date."""
        p = self.pc
        events = p.get("events", [])
        now = datetime.now()
        display_date, is_tomorrow = self._get_display_date()
        cur_mins = now.hour * 60 + now.minute
        GRACE = 10  # minutes

        result = []
        for ev in events:
            # Check scheduling rules (date range, weekdays, parshiyot)
            if not _schedule_event_active_for_date(ev, display_date):
                continue
            ev_time = ev.get("time", "")
            if ev_time:
                try:
                    hh, mm = map(int, ev_time.split(":"))
                    ev_mins = hh * 60 + mm
                    if not is_tomorrow:
                        # Only show if not more than GRACE minutes past
                        if cur_mins > ev_mins + GRACE:
                            continue
                except:
                    pass
            result.append(ev)
        return result

    def _draw(self):
        if not hasattr(self, "_cv"):
            return
        cv = self._cv
        cv.delete("sched_content")
        p = self.pc
        W = p.get("width", 350); H = p.get("height", 200)
        pt, pb, pl, pr = _get_pads(p, 14)
        usable_w = W - pl - pr
        usable_h = H - pt - pb

        name_ff  = p.get("name_font_family", p.get("font_family", "Arial"))
        name_fs  = p.get("name_font_size",   p.get("font_size", 20))
        name_fc  = p.get("name_font_color",  p.get("font_color", "#ffffff"))
        time_ff  = p.get("time_font_family", p.get("font_family", "Arial"))
        time_fs  = p.get("time_font_size",   p.get("font_size", 20))
        time_fc  = p.get("time_font_color",  "#aaddff")
        bold     = "bold" if p.get("bold", False) else "normal"
        italic   = "italic" if p.get("italic", False) else "roman"

        name_font = (name_ff, name_fs, bold, italic)
        time_font = (time_ff, time_fs, bold, italic)

        events = self._get_upcoming_events()
        if not events:
            empty = p.get("empty_text", "אין אירועים")
            cv.create_text(W // 2, H // 2, text=empty,
                font=name_font, fill=name_fc, anchor="center", tags="sched_content")
            return

        # Calculate row height based on font size
        row_h = max(name_fs, time_fs) + 8
        max_rows = max(1, usable_h // row_h)

        y = pt + row_h // 2
        for ev in events[:max_rows]:
            name = ev.get("name", "")
            t    = ev.get("time", "")
            # Name on right side, time on left side (RTL layout)
            x_name = W - pr  # right side
            x_time = pl       # left side
            if name:
                cv.create_text(x_name, y, text=name, font=name_font, fill=name_fc,
                               anchor="e", tags="sched_content")
            if t:
                cv.create_text(x_time, y, text=t, font=time_font, fill=time_fc,
                               anchor="w", tags="sched_content")
            elif name and not t:
                # No time — center the name
                cv.create_text(W // 2, y, text=name, font=name_font, fill=name_fc,
                               anchor="center", tags="sched_content")
                # Remove the right-side text we just drew and redo centered
                cv.delete("sched_content")
                y2 = pt + row_h // 2
                for ev2 in events[:max_rows]:
                    n2 = ev2.get("name",""); t2 = ev2.get("time","")
                    if t2:
                        cv.create_text(W - pr, y2, text=n2, font=name_font, fill=name_fc,
                                       anchor="e", tags="sched_content")
                        cv.create_text(pl, y2, text=t2, font=time_font, fill=time_fc,
                                       anchor="w", tags="sched_content")
                    else:
                        cv.create_text(W // 2, y2, text=n2, font=name_font, fill=name_fc,
                                       anchor="center", tags="sched_content")
                    y2 += row_h
                return
            y += row_h

    def tick(self):
        self._draw()


def _schedule_event_active_for_date(ev, target_date):
    """Check if event's scheduling rules (excluding time) match the given date."""
    from datetime import date as _date
    # Specific date match
    ev_date = ev.get("date", "")
    if ev_date:
        try:
            if _date.fromisoformat(ev_date) != target_date:
                return False
        except:
            pass
    # Date range (handles both DD/MM/YYYY and YYYY-MM-DD formats)
    def _parse_date(s):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try: return _date.strptime(s.strip(), fmt)
            except: pass
        return None
    df = ev.get("date_from", ""); dt = ev.get("date_to", "")
    if df:
        d_from = _parse_date(df)
        if d_from and target_date < d_from: return False
    if dt:
        d_to = _parse_date(dt)
        if d_to and target_date > d_to: return False
    # Weekday filter
    wds = ev.get("weekdays", [])
    if wds and target_date.weekday() not in wds:
        return False
    # Parasha filter (key: "parasha_weeks")
    pars = ev.get("parasha_weeks", ev.get("parshiyot", []))
    if pars:
        try:
            cur_par = get_parasha(israel=True) or ""
            if cur_par not in pars: return False
        except: pass
    # Date range: also handle DD/MM/YYYY format from editor
    return True


# ── חלוניות ישירות על ה-canvas הראשי (שקיפות אמיתית) ───────────────────────────
class DirectCanvasPanel:
    """
    Base class for panels that draw directly on bg_canvas (the main display canvas).
    This gives TRUE transparency: the panel content is drawn on top of whatever is
    already on bg_canvas — background, opaque panels drawn before it — with no
    Widget boundary or bg_color fill between them.

    All drawing uses canvas items tagged with f"dpanel_{pc['id']}" for easy cleanup.
    Coordinates are offset by (ox, oy) — the panel's top-left corner on the canvas.
    """
    def __init__(self, canvas, pc, dsp, ox, oy, W, H):
        self.canvas = canvas  # the shared bg_canvas
        self.pc = pc; self.dsp = dsp
        self.ox = ox; self.oy = oy
        self.W = W; self.H = H
        self._tag = f"dpanel_{pc['id']}"
        self._item_ids = []   # canvas item ids owned by this panel
        self.build()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _x(self, x): return self.ox + x
    def _y(self, y): return self.oy + y
    def cx(self, x): return self.ox + x   # alias
    def cy(self, y): return self.oy + y   # alias

    def create_text(self, x, y, **kw):
        kw.setdefault("tags", self._tag)
        iid = self.canvas.create_text(self.ox+x, self.oy+y, **kw)
        self._item_ids.append(iid); return iid

    def create_image(self, x, y, **kw):
        kw.setdefault("tags", self._tag)
        iid = self.canvas.create_image(self.ox+x, self.oy+y, **kw)
        self._item_ids.append(iid); return iid

    def create_line(self, x1, y1, x2, y2, **kw):
        kw.setdefault("tags", self._tag)
        iid = self.canvas.create_line(self.ox+x1, self.oy+y1, self.ox+x2, self.oy+y2, **kw)
        self._item_ids.append(iid); return iid

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        kw.setdefault("tags", self._tag)
        iid = self.canvas.create_rectangle(self.ox+x1, self.oy+y1, self.ox+x2, self.oy+y2, **kw)
        self._item_ids.append(iid); return iid

    def itemconfig(self, iid, **kw):
        try: self.canvas.itemconfig(iid, **kw)
        except: pass

    def coords(self, iid, *args):
        """Update coords with automatic offset applied."""
        if len(args) == 2:
            try: self.canvas.coords(iid, self.ox+args[0], self.oy+args[1])
            except: pass
        elif len(args) == 4:
            try: self.canvas.coords(iid, self.ox+args[0], self.oy+args[1],
                                         self.ox+args[2], self.oy+args[3])
            except: pass

    def bbox(self, iid):
        bb = self.canvas.bbox(iid)
        if bb:
            return (bb[0]-self.ox, bb[1]-self.oy, bb[2]-self.ox, bb[3]-self.oy)
        return None

    def delete(self, tag_or_id=None):
        """Delete items. If None/all, deletes all items owned by this panel."""
        if tag_or_id is None or tag_or_id == "all":
            try: self.canvas.delete(self._tag)
            except: pass
            self._item_ids.clear()
        else:
            try: self.canvas.delete(tag_or_id)
            except: pass

    def destroy(self):
        """Remove all canvas items drawn by this panel."""
        try: self.canvas.delete(self._tag)
        except: pass
        self._item_ids.clear()

    def build(self): pass
    def tick(self): pass
    def build_content_override(self, text):
        self.pc["content"] = text; self.tick()


class DirectClockPanel(DirectCanvasPanel):
    def build(self):
        p = self.pc
        cc = p.get("font_color", p.get("clock_color", BLUE))
        ff = p.get("font_family", "Arial")
        pt, pb, pl, pr = _get_pads(p, 0)
        # Content area (inside margins) — used for centering text/analog
        self._cx = pl + (self.W - pl - pr) // 2   # content center-x
        self._cy = pt + (self.H - pt - pb) // 2   # content center-y
        self._cW = max(1, self.W - pl - pr)
        self._cH = max(1, self.H - pt - pb)
        if p.get("clock_style","digital") == "analog":
            self._analog = True
            self.tick()
        else:
            self._analog = False
            fs = p.get("font_size", p.get("time_font_size", 56))
            self._t_id = self.create_text(self._cx, self._cy,
                text="", font=(ff, fs, "bold"), fill=cc, anchor="center")
            self.tick()

    def tick(self):
        now = get_now(getattr(self.dsp,"cfg",None) and self.dsp.cfg.d)
        p = self.pc
        if getattr(self,"_analog", False):
            self.canvas.delete(f"dclock_{p['id']}")
            import math as _math
            # Use content-area center (respects margins)
            cx = self.ox + getattr(self,"_cx", self.W//2)
            cy = self.oy + getattr(self,"_cy", self.H//2)
            cW = getattr(self,"_cW", self.W)
            cH = getattr(self,"_cH", self.H)
            r = min(cW, cH)//2 - 6
            if r < 10: r = 10
            cc = p.get("font_color", p.get("clock_color", BLUE))
            style = p.get("analog_style","classic")
            tag = f"dclock_{p['id']}"
            if style in ("classic","railway"):
                self.canvas.create_oval(cx-r-3,cy-r-3,cx+r+3,cy+r+3,fill="",outline="#1a2a6a",width=6,tags=tag)
            self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r,fill="",outline=cc,
                width=2 if style=="minimal" else 3,tags=tag)
            for i in range(60):
                a=_math.radians(i*6-90); ca=_math.cos(a); sa=_math.sin(a)
                if i%5==0:
                    if style=="railway":
                        self.canvas.create_line(cx+(r-2)*ca,cy+(r-2)*sa,cx+(r-18)*ca,cy+(r-18)*sa,fill=cc,width=4,tags=tag)
                    elif style=="minimal":
                        self.canvas.create_line(cx+(r-4)*ca,cy+(r-4)*sa,cx+(r-14)*ca,cy+(r-14)*sa,fill=cc,width=2,tags=tag)
                    else:
                        self.canvas.create_line(cx+(r-4)*ca,cy+(r-4)*sa,cx+(r-16)*ca,cy+(r-16)*sa,fill=cc,width=2,tags=tag)
                    if style not in ("minimal","railway"):
                        nx=cx+(r-28)*ca; ny=cy+(r-28)*sa
                        hn=i//5 or 12
                        lbl=str(hn) if style!="roman" else {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",8:"VIII",9:"IX",10:"X",11:"XI",12:"XII"}.get(hn,str(hn))
                        self.canvas.create_text(nx,ny,text=lbl,fill="#aabbdd",font=("Arial",max(7,r//14)),tags=tag)
                else:
                    if style!="minimal":
                        self.canvas.create_line(cx+(r-4)*ca,cy+(r-4)*sa,cx+(r-9)*ca,cy+(r-9)*sa,fill="#5566aa",width=1,tags=tag)
            ha=(now.hour%12+now.minute/60)*30; ma=(now.minute+now.second/60)*6; sa2=now.second*6
            for deg,L,col,w,back in [(ha,r*0.53,"#ffffff",5,False),(ma,r*0.76,cc,3,False),(sa2,r*0.87,"#f5a623",1,True)]:
                a=_math.radians(deg-90)
                hx=cx+L*_math.cos(a); hy=cy+L*_math.sin(a)
                if back:
                    ba=_math.radians(deg-90+180)
                    bx=cx+r*0.18*_math.cos(ba); by=cy+r*0.18*_math.sin(ba)
                    self.canvas.create_line(cx,cy,bx,by,fill=col,width=w,tags=tag)
                self.canvas.create_line(cx,cy,hx,hy,fill=col,width=w,capstyle="round",tags=tag)
            self.canvas.create_oval(cx-6,cy-6,cx+6,cy+6,fill=cc,outline="#070714",width=2,tags=tag)
        else:
            if hasattr(self,"_t_id"):
                sec=":%S" if p.get("show_seconds",True) else ""
                fmt=f"%I:%M{sec} %p" if p.get("time_format","24")=="12" else f"%H:%M{sec}"
                self.itemconfig(self._t_id, text=now.strftime(fmt))

    def destroy(self):
        super().destroy()
        try: self.canvas.delete(f"dclock_{self.pc['id']}")
        except: pass


class DirectDatePanel(DirectCanvasPanel):
    def build(self):
        p = self.pc
        ff = p.get("font_family","Arial"); fs = p.get("font_size", p.get("date_font_size",18))
        fc = p.get("font_color", p.get("date_color", TEXT))
        def icol(key, default):
            return p.get(key, fc if key not in ("hol_color","par_color") else default)
        sp = p.get("date_line_spacing", 4)
        self._layout_mode = p.get("date_layout","stacked")
        self._sep = p.get("date_separator"," | ")
        self._ff = ff; self._fs = fs
        self._hol_cache = ""; self._par_cache = ""; self._par_last = None
        self._extra_last = None; self._prayer_cache = {}
        self._torah_cache = ("",""); self._daf_cache = ""
        self._items = {}
        pt, pb, pl, pr = _get_pads(p, 0)
        cW = max(1, self.W - pl - pr)
        cH = max(1, self.H - pt - pb)
        cx_mid = pl + cW // 2
        cy_mid = pt + cH // 2
        if self._layout_mode == "inline":
            # Store params for dynamic line-building in tick()
            self._inline_fc = fc
            self._inline_ff = ff
            self._inline_fs = fs
            self._inline_pt = pt
            self._inline_pl = pl
            self._inline_cW = cW
            self._inline_cH = cH
            # Will create text items dynamically in tick()
        else:
            cy = pt + 6
            base_rows = [
                ("wd","show_weekday", icol("wd_color",TEXT), True),
                ("hd","show_heb_date", icol("hd_color",TEXT), False),
                ("gd","show_greg_date", icol("gd_color",TEXT), False),
                ("hol","show_holiday", icol("hol_color",GOLD), True),
                ("par","show_parasha", icol("par_color",LBLUE), False),
            ]
            new_rows = [
                ("tor","show_torah_reading", p.get("tor_color","#aaffaa"), False),
                ("haf","show_haftara", p.get("haf_color","#aaffcc"), False),
                ("yaaleh","show_yaaleh_veyavo", p.get("yaaleh_color","#ffdd88"), False),
                ("morid_tal","show_morid_hatal", p.get("morid_tal_color","#88ddff"), False),
                ("mashiv","show_mashiv_haruach", p.get("mashiv_color","#88ccff"), False),
                ("vten","show_vten_tal_umatar", p.get("vten_color","#ffcc88"), False),
                ("daf","show_daf_yomi", p.get("daf_color","#ccaaff"), False),
            ]
            for key, show_key, color, bold in base_rows + new_rows:
                # base rows default to True, new rows default to False
                default_val = True if (key,show_key,color,bold) in base_rows else False
                if p.get(show_key, default_val):
                    font_spec = (ff,fs,"bold") if bold else (ff,fs)
                    self._items[key] = self.create_text(cx_mid, cy, text="",
                        font=font_spec, fill=color, anchor="n")
                    cy += fs + sp
        self.tick()

    def tick(self):
        now = get_now(getattr(self.dsp,"cfg",None) and self.dsp.cfg.d)
        p = self.pc
        if p.get("show_holiday",True): self._hol_cache = get_today_holiday(israel=p.get("israel",True)) or ""
        if p.get("show_parasha",True):
            if self._par_last != now.date():
                self._par_cache = get_parasha(israel=p.get("israel",True)) or ""
                self._par_last = now.date()
        needs_new = self._extra_last != now.date()
        if needs_new:
            self._extra_last = now.date()
            self._prayer_cache = get_prayer_additions()
            self._torah_cache  = get_torah_reading(israel=p.get("israel",True))
            self._daf_cache    = get_daf_yomi()
        pr_cache = self._prayer_cache
        if self._layout_mode == "inline":
            # Build parts list as (text, color) tuples
            fc = self._inline_fc
            def icol(key, default):
                return p.get(key, fc if key not in ("hol_color","par_color") else default)
            parts = []
            if p.get("show_weekday",True): parts.append((get_weekday_heb(), icol("wd_color", fc)))
            if p.get("show_heb_date",True):
                hd = get_heb_date(getattr(self.dsp,"cfg",None) and self.dsp.cfg.d)
                if hd: parts.append((fmt_heb_date(*hd), icol("hd_color", fc)))
            if p.get("show_greg_date",True): parts.append((now.strftime("%d/%m/%Y"), icol("gd_color", fc)))
            if p.get("show_holiday",True) and self._hol_cache: parts.append((f"🕍 {self._hol_cache}", icol("hol_color", GOLD)))
            if p.get("show_parasha",True) and self._par_cache: parts.append((f"פרשת {self._par_cache}", icol("par_color", LBLUE)))
            tor, haf = self._torah_cache
            if p.get("show_torah_reading",False) and tor: parts.append((tor, p.get("tor_color","#aaffaa")))
            if p.get("show_haftara",False) and haf: parts.append((haf, p.get("haf_color","#aaffcc")))
            if p.get("show_yaaleh_veyavo",False) and pr_cache.get("yaaleh_veyavo"): parts.append((pr_cache["yaaleh_veyavo"], p.get("yaaleh_color","#ffdd88")))
            if p.get("show_morid_hatal",False) and pr_cache.get("morid_hatal"): parts.append((pr_cache["morid_hatal"], p.get("morid_tal_color","#88ddff")))
            if p.get("show_mashiv_haruach",False) and pr_cache.get("mashiv_haruach"): parts.append((pr_cache["mashiv_haruach"], p.get("mashiv_color","#88ccff")))
            if p.get("show_vten_tal_umatar",False) and pr_cache.get("vten_tal_umatar"): parts.append((pr_cache["vten_tal_umatar"], p.get("vten_color","#ffcc88")))
            if p.get("show_daf_yomi",False) and self._daf_cache: parts.append((self._daf_cache, p.get("daf_color","#ccaaff")))

            # Remove old inline items
            for key in list(self._items.keys()):
                if key.startswith("inline_line_"):
                    try: self.canvas.delete(self._items[key])
                    except: pass
                    del self._items[key]

            ff = self._inline_ff; fs = self._inline_fs
            sep = self._sep
            max_w = max(40, self._inline_cW - 8)
            pt = self._inline_pt; pl = self._inline_pl

            try:
                import tkinter.font as _tkF
                _fo = _tkF.Font(family=ff, size=fs)
                def _meas(t): return _fo.measure(t)
            except:
                def _meas(t): return int(len(t) * fs * 0.6)

            sep_w = _meas(sep)
            lines = []
            cur_line = []; cur_w = 0.0
            for txt, col in parts:
                iw = _meas(txt)
                if not cur_line:
                    cur_line.append((txt,col)); cur_w = iw
                elif cur_w + sep_w + iw <= max_w:
                    cur_line.append((txt,col)); cur_w += sep_w + iw
                else:
                    lines.append(cur_line)
                    cur_line = [(txt,col)]; cur_w = iw
            if cur_line:
                lines.append(cur_line)

            line_h = fs + 6
            total_h = len(lines) * line_h
            cy_start = pt + max(0, (self._inline_cH - total_h) // 2) + fs // 2
            cx_mid = pl + self._inline_cW // 2
            item_idx = 0
            for li, line_items in enumerate(lines):
                cy = cy_start + li * line_h
                total_line_w = sum(_meas(t) for t,c in line_items) + sep_w * (len(line_items)-1)
                x = cx_mid - total_line_w // 2
                for idx, (txt, col) in enumerate(line_items):
                    iw = _meas(txt)
                    iid = self.create_text(x + iw//2, cy, text=txt,
                        font=(ff,fs), fill=col, anchor="center")
                    self._items[f"inline_line_{item_idx}"] = iid
                    item_idx += 1
                    x += iw
                    if idx < len(line_items) - 1:
                        iid2 = self.create_text(x + sep_w//2, cy, text=sep,
                            font=(ff,fs), fill=fc, anchor="center")
                        self._items[f"inline_line_{item_idx}"] = iid2
                        item_idx += 1
                        x += sep_w
        else:
            if "wd" in self._items: self.itemconfig(self._items["wd"], text=get_weekday_heb())
            if "hd" in self._items:
                hd = get_heb_date(getattr(self.dsp,"cfg",None) and self.dsp.cfg.d)
                self.itemconfig(self._items["hd"], text=fmt_heb_date(*hd) if hd else "")
            if "gd" in self._items: self.itemconfig(self._items["gd"], text=now.strftime("%d/%m/%Y"))
            if "hol" in self._items: self.itemconfig(self._items["hol"], text=f"🕍 {self._hol_cache}" if self._hol_cache else "")
            if "par" in self._items: self.itemconfig(self._items["par"], text=f"פרשת {self._par_cache}" if self._par_cache else "")
            tor, haf = self._torah_cache
            if "tor" in self._items: self.itemconfig(self._items["tor"], text=tor)
            if "haf" in self._items: self.itemconfig(self._items["haf"], text=haf)
            if "yaaleh" in self._items: self.itemconfig(self._items["yaaleh"], text=pr_cache.get("yaaleh_veyavo",""))
            if "morid_tal" in self._items: self.itemconfig(self._items["morid_tal"], text=pr_cache.get("morid_hatal",""))
            if "mashiv" in self._items: self.itemconfig(self._items["mashiv"], text=pr_cache.get("mashiv_haruach",""))
            if "vten" in self._items: self.itemconfig(self._items["vten"], text=pr_cache.get("vten_tal_umatar",""))
            if "daf" in self._items: self.itemconfig(self._items["daf"], text=self._daf_cache)


class DirectTimePanel(DirectCanvasPanel):
    def build(self):
        p = self.pc; ff = p.get("font_family","Arial")
        _fc = p.get("font_color",None)
        self._cc = _fc if _fc else p.get("clock_color",BLUE)
        self._dc = _fc if _fc else p.get("date_color",TEXT)
        self._items = {}
        pt, pb, pl, pr = _get_pads(p, 0)
        cW = max(1, self.W - pl - pr)
        cx_mid = pl + cW // 2
        cy = pt + 10
        fs_base = p.get("font_size", p.get("time_font_size",42))
        fs_date = max(10, int(fs_base*0.38))
        if p.get("show_time",True):
            self._items["time"] = self.create_text(cx_mid, cy, text="",
                font=(ff, fs_base, "bold"), fill=self._cc, anchor="n")
            cy += fs_base + 8
        for key, show_key, color in [
            ("wd","show_weekday",None),("hd","show_heb_date",None),
            ("gd","show_greg_date",None),("hol","show_holiday",GOLD),("par","show_parasha",LBLUE)
        ]:
            if p.get(show_key,True):
                self._items[key] = self.create_text(cx_mid, cy, text="",
                    font=(ff, fs_date), fill=color if color else self._dc, anchor="n")
                cy += fs_date + 4
        self.tick()

    def tick(self):
        now = datetime.now(); p = self.pc
        if "time" in self._items:
            sec = ":%S" if p.get("show_seconds",True) else ""
            fmt = f"%I:%M{sec} %p" if p.get("time_format","24")=="12" else f"%H:%M{sec}"
            self.itemconfig(self._items["time"], text=now.strftime(fmt))
        if "wd" in self._items: self.itemconfig(self._items["wd"], text=get_weekday_heb())
        if "hd" in self._items:
            hd = get_heb_date(self.dsp.cfg.d)
            self.itemconfig(self._items["hd"], text=fmt_heb_date(*hd) if hd else "")
        if "gd" in self._items: self.itemconfig(self._items["gd"], text=now.strftime("%d/%m/%Y"))
        if "hol" in self._items:
            hol = get_today_holiday(israel=p.get("israel",True))
            self.itemconfig(self._items["hol"], text=f"🕍 {hol}" if hol else "")
        if "par" in self._items:
            if not hasattr(self,"_par_last") or self._par_last != now.date():
                self._par_cache = get_parasha(israel=p.get("israel",True))
                self._par_last = now.date()
            self.itemconfig(self._items["par"], text=f"פרשת {self._par_cache}" if self._par_cache else "")


class DirectTextPanel(DirectCanvasPanel):
    """Text panel drawn directly on bg_canvas.

    Clipping: four large stencil rectangles/images cover the screen OUTSIDE the panel
    bounds, masking any text items that scroll beyond the panel edges.
    For transparent/image-bg panels the stencils are PhotoImage crops of _bg_pil.

    Seamless loop (scroll_up / scroll_right):
    Two copies of the text block are placed back-to-back (stride = total_size + GAP).
    When anchor moves by one stride the positions wrap: anchor += stride.
    Because two copies span 2*stride, one copy is always inside the panel.

    Per-segment styling: each segment is a separate canvas text item with its own
    font tuple and color.
    """
    _RLM = "\u200f"

    def _rfix(self, t):
        if not t: return t
        lines = []
        for line in t.split("\n"):
            has_heb = any('\u0590' <= ch <= '\u05FF' or '\uFB1D' <= ch <= '\uFB4F' for ch in line)
            lines.append(self._RLM + line if (has_heb and line) else line)
        return "\n".join(lines)

    def _font_spec(self, p):
        ff = p.get("font_family","Arial"); fs = p.get("font_size",20)
        wt = "bold"   if p.get("bold",False)   else "normal"
        sl = "italic" if p.get("italic",False)  else "roman"
        return (ff, fs, wt, sl)

    def _seg_font_spec(self, p, sd):
        ff = sd.get("font_family", p.get("font_family","Arial"))
        fs = sd.get("font_size",   p.get("font_size",20))
        wt = "bold"   if sd.get("bold",   p.get("bold",False))   else "normal"
        sl = "italic" if sd.get("italic", p.get("italic",False))  else "roman"
        fc = sd.get("font_color",  p.get("font_color","#ffffff"))
        return (ff, fs, wt, sl), fc

    def _build_seg_items(self, p):
        """Return list of (text, font_tuple, color) including separator items."""
        horiz = (self._mode == "scroll_right")
        sep_space = p.get("seg_separator_space", True)
        sep_char  = (p.get("seg_separator_char","") or "").strip()
        def_font  = self._font_spec(p)
        def_fc    = p.get("font_color","#ffffff")

        segs = p.get("content_segments",[])
        raw_items = []
        if segs:
            for sd in segs:
                t = sd.get("text","")
                if not t.strip(): continue
                if horiz: t = t.replace("\n"," ").strip()
                font, fc = self._seg_font_spec(p, sd)
                raw_items.append((self._rfix(t), font, fc))
        else:
            raw = p.get("content","")
            if horiz: raw = raw.replace("\n"," ").strip()
            if raw.strip():
                raw_items.append((self._rfix(raw), def_font, def_fc))
        if not raw_items: return []

        if len(raw_items) == 1: return raw_items

        result = []
        for i, item in enumerate(raw_items):
            result.append(item)
            if i < len(raw_items) - 1:
                if horiz:
                    sep_txt = ("  " if sep_space else "") + (sep_char or "") + ("  " if sep_space else "")
                    if sep_txt.strip():
                        result.append((sep_txt, def_font, def_fc))
                    elif sep_space:
                        result.append(("   ", def_font, def_fc))
                else:
                    sep_lines = []
                    if sep_space: sep_lines.append("")
                    if sep_char:  sep_lines.append(sep_char)
                    if sep_space and sep_char: sep_lines.append("")
                    if sep_lines:
                        result.append((self._rfix("\n".join(sep_lines)), def_font, def_fc))
        return result

    def _sample_bg(self, x, y):
        try:
            bg_pil = getattr(self.dsp, "_bg_pil", None)
            if bg_pil:
                px = max(0, min(int(x), bg_pil.width-1))
                py = max(0, min(int(y), bg_pil.height-1))
                r,g,b = bg_pil.getpixel((px,py))[:3]
                return f"#{r:02x}{g:02x}{b:02x}"
        except: pass
        try: return self.canvas.cget("bg")
        except: return "#000000"

    def _make_outer_stencils(self, p, transparent):
        """Cover screen OUTSIDE panel bounds so scrolling text is hidden there."""
        tag = self._tag
        ox = self.ox; oy = self.oy; cw = self.W; ch = self.H
        sw = getattr(self.dsp, "W", 1920)
        sh = getattr(self.dsp, "H", 1080)
        bg_img = p.get("bg_image","")
        use_image = transparent or bool(bg_img and os.path.exists(bg_img))
        self._stencil_photos = []

        def _make_rect(sx, sy, sw_, sh_):
            if sw_ <= 0 or sh_ <= 0: return
            if use_image:
                ph = getattr(self.dsp, "_get_bg_crop_photo", lambda *a: None)(sx, sy, sw_, sh_)
                if ph:
                    self._stencil_photos.append(ph)
                    iid = self.canvas.create_image(sx, sy, image=ph, anchor="nw", tags=tag)
                    self._stencil_item_ids.append(iid); return
            if transparent:
                clr = self._sample_bg(sx + sw_//2, sy + sh_//2)
            elif bg_img and os.path.exists(bg_img):
                clr = "#000000"
            else:
                clr = p.get("bg_color","#111128")
            rid = self.canvas.create_rectangle(sx, sy, sx+sw_, sy+sh_, fill=clr, outline="", tags=tag)
            self._stencil_item_ids.append(rid)

        _make_rect(0,    0,    sw,      oy)          # above panel
        _make_rect(0,    oy+ch, sw,     sh-(oy+ch))  # below panel
        _make_rect(0,    oy,    ox,     ch)           # left of panel
        _make_rect(ox+cw, oy,  sw-(ox+cw), ch)       # right of panel

    def build(self):
        p = self.pc
        raw_mode = p.get("scroll_mode","scroll_up")
        if raw_mode == "scroll": raw_mode = "scroll_up"
        self._mode = raw_mode

        pt, pb, pl, pr = _get_pads(p, 14)
        align = p.get("align","right")
        j = {"right":"right","left":"left","center":"center"}.get(align,"right")
        tag = self._tag
        transparent = p.get("bg_transparent", False)

        cw = self.W; ch = self.H
        content_w = max(4, cw - pl - pr)
        content_h = max(4, ch - pt - pb)
        cx_mid = self.ox + pl + content_w // 2

        self._scroll_tids = []
        self._tid = None
        self._needs_scroll = False
        self._stencil_item_ids = []

        # Background rectangle (opaque color panels only)
        if not transparent:
            bg_img_path = p.get("bg_image","")
            if not (bg_img_path and os.path.exists(bg_img_path)):
                self.canvas.create_rectangle(self.ox, self.oy, self.ox+cw, self.oy+ch,
                    fill=p.get("bg_color","#111128"), outline="", tags=tag)

        seg_items = self._build_seg_items(p)
        if not seg_items:
            seg_items = [(self._rfix(p.get("content","")), self._font_spec(p), p.get("font_color","#ffffff"))]
        self._seg_items_cache = seg_items

        # ── helper: measure heights of all segments placed at a given y ──────
        def _measure_heights(items, base_y):
            """Create items off-screen, measure, delete. Returns list of heights."""
            off_y = base_y
            hs = []
            tids = []
            for seg_text, seg_font, seg_fc in items:
                tid = self.canvas.create_text(cx_mid, off_y, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j,
                    width=content_w, anchor="n", tags=tag)
                tids.append(tid)
                off_y += 500  # space them apart while measuring
            self.canvas.update_idletasks()
            for i, tid in enumerate(tids):
                bb = self.canvas.bbox(tid)
                hs.append((bb[3]-bb[1]) if bb else (items[i][1][1]+4))
                self.canvas.delete(tid)
            return hs

        if self._mode == "static":
            cy = self.oy + pt + 4
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self.canvas.create_text(cx_mid, cy, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j,
                    width=content_w, anchor="n", tags=tag)
                self.canvas.update_idletasks()
                bb = self.canvas.bbox(tid)
                cy += ((bb[3]-bb[1]) if bb else seg_font[1]+4) + 4
            self._make_outer_stencils(p, transparent)
            # Stencils are created after text items — naturally on top, no tag_raise needed

        elif self._mode == "scroll_up":
            GAP = 30  # px gap between end of text and start of next loop copy
            # Measure each segment's height
            heights = _measure_heights(seg_items, self.oy + ch + 9000)
            # Build offsets within one copy
            offsets = []  # dy from copy-anchor for each segment
            cur_dy = 0
            for h in heights:
                offsets.append(cur_dy); cur_dy += h + 4
            total_h = cur_dy
            stride = total_h + GAP  # distance between copy A and copy B anchors

            self._needs_scroll = total_h > content_h
            self._th = total_h
            self._loop_stride = stride

            # Render two copies; anchor_y = canvas-y of copy A segment[0] top
            start_y = float(self.oy + ch)   # start: first seg just below panel bottom
            self._anchor_y = start_y
            self._scroll_tids = []  # (tid, dy)  dy = offset from anchor_y

            for copy_num in range(2):
                copy_base_dy = copy_num * stride
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dy = copy_base_dy + offsets[i]
                    tid = self.canvas.create_text(cx_mid, start_y + dy, text=seg_text,
                        font=seg_font, fill=seg_fc, justify=j,
                        width=content_w, anchor="n", tags=tag)
                    self._scroll_tids.append((tid, dy))

            self._make_outer_stencils(p, transparent)
            for sid in self._stencil_item_ids:
                try: self.canvas.tag_raise(sid)
                except: pass
            try: self.canvas.tag_raise("version_watermark")
            except: pass

        elif self._mode == "scroll_right":
            # "גלילה ימינה" = text moves rightward: enters from left, exits right.
            # anchor_x increases; start_x is left of panel (ox - total_w).
            GAP = 60
            mid_y = self.oy + pt + content_h // 2
            # Measure widths off-screen
            wid_tids = []
            off_x = self.ox + cw + 9000
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self.canvas.create_text(off_x, mid_y, text=seg_text,
                    font=seg_font, fill=seg_fc, anchor="w", tags=tag)
                wid_tids.append(tid)
            self.canvas.update_idletasks()
            widths = []
            for tid in wid_tids:
                bb = self.canvas.bbox(tid)
                widths.append((bb[2]-bb[0]) if bb else 80)
                self.canvas.delete(tid)
            offsets_x = []
            cur_dx = 0
            for w in widths:
                offsets_x.append(cur_dx); cur_dx += w
            total_w = cur_dx
            stride_x = total_w + GAP

            self._needs_scroll = total_w > content_w
            self._th = total_w
            self._loop_stride_x = stride_x

            # Start: first copy starts just off the LEFT edge of the panel
            start_x = float(self.ox - total_w - GAP)
            self._anchor_x = start_x
            self._scroll_tids = []

            for copy_num in range(2):
                copy_base_dx = copy_num * stride_x
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dx = copy_base_dx + offsets_x[i]
                    tid = self.canvas.create_text(start_x + dx, mid_y, text=seg_text,
                        font=seg_font, fill=seg_fc, anchor="w", tags=tag)
                    self._scroll_tids.append((tid, dx))

            self._make_outer_stencils(p, transparent)

        elif self._mode == "segments":
            self._seg_idx = 0; self._seg_last = time.time()
            segs_cfg = p.get("content_segments",[])
            self._seg_durations = [max(2,int(s.get("duration", p.get("segment_duration",5)))) for s in segs_cfg if s.get("text","").strip()] if segs_cfg else [max(2,p.get("segment_duration",5))]
            cx = cx_mid; cy = self.oy + pt + content_h // 2
            seg_text, seg_font, seg_fc = seg_items[0]
            self._tid = self.canvas.create_text(cx, cy, text=seg_text,
                font=seg_font, fill=seg_fc, justify=j,
                width=content_w, anchor="center", tags=tag)
            self._make_outer_stencils(p, transparent)

        self._cw=cw; self._ch=ch; self._pt=pt; self._pb=pb
        self._pl=pl; self._pr=pr; self._j=j; self._cx_mid=cx_mid

    def tick(self):
        p = self.pc
        raw_mode = p.get("scroll_mode","scroll_up")
        if raw_mode == "scroll": raw_mode = "scroll_up"

        if raw_mode == "static":
            return

        elif raw_mode == "scroll_up":
            if not self._scroll_tids: return
            try:
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_y -= spd
                stride = getattr(self, "_loop_stride", self._th + 30)
                if self._anchor_y < self.oy - stride:
                    self._anchor_y += stride
                for tid, dy in self._scroll_tids:
                    self.canvas.coords(tid, self._cx_mid, self._anchor_y + dy)
            except: pass

        elif raw_mode == "scroll_right":
            if not self._scroll_tids: return
            try:
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_x += spd  # moves rightward
                stride = getattr(self, "_loop_stride_x", self._th + 60)
                # When the first copy has fully passed the right edge, wrap back
                if self._anchor_x > self.ox + self._cw + stride:
                    self._anchor_x -= stride
                mid_y = self.oy + self._pt + (self._ch - self._pt - self._pb) // 2
                for tid, dx in self._scroll_tids:
                    self.canvas.coords(tid, self._anchor_x + dx, mid_y)
            except: pass

        elif raw_mode == "segments":
            if not self._tid: return
            now = time.time()
            seg_items = getattr(self, "_seg_items_cache", [])
            durs = getattr(self, "_seg_durations", [max(2,p.get("segment_duration",5))])
            dur = durs[self._seg_idx % max(1,len(durs))] if durs else max(2,p.get("segment_duration",5))
            new_items = self._build_seg_items(p)
            if not new_items:
                new_items = [(self._rfix(p.get("content","")), self._font_spec(p), p.get("font_color","#ffffff"))]
            segs_cfg = p.get("content_segments",[])
            new_durs = [max(2,int(s.get("duration", p.get("segment_duration",5)))) for s in segs_cfg if s.get("text","").strip()] if segs_cfg else [max(2,p.get("segment_duration",5))]
            if new_items != seg_items or new_durs != durs:
                self._seg_items_cache = new_items
                self._seg_durations = new_durs
                self._seg_idx = 0; self._seg_last = now
                if new_items:
                    st, sf, sfc = new_items[0]
                    try: self.canvas.itemconfig(self._tid, text=st, font=sf, fill=sfc)
                    except: pass
                return
            if now - self._seg_last >= dur:
                self._seg_last = now
                self._seg_idx = (self._seg_idx + 1) % max(1, len(seg_items))
                st, sf, sfc = seg_items[self._seg_idx]
                try: self.canvas.itemconfig(self._tid, text=st, font=sf, fill=sfc)
                except: pass

    def build_content_override(self, text):
        self.pc["content"] = text
        if self._tid:
            try: self.canvas.itemconfig(self._tid, text=self._rfix(text))
            except: pass

class DirectSchedulePanel(DirectCanvasPanel):
    """Schedule panel drawn directly on bg_canvas — true transparency, no widget boundary.
    Draws event name (right) and time (left) rows as canvas text items.
    Stencil strips clip content to panel bounds (same technique as DirectTextPanel).
    """

    def _get_upcoming_events(self):
        p = self.pc
        events = p.get("events",[])
        now = datetime.now()
        # Determine display date (with rollover support)
        rollover_h = int(p.get("day_rollover_hour",0))
        rollover_m = int(p.get("day_rollover_minute",0))
        rollover_mins = rollover_h*60 + rollover_m
        cur_mins = now.hour*60 + now.minute
        if rollover_mins > 0 and cur_mins < rollover_mins:
            from datetime import timedelta as _td
            display_date = (now + _td(days=1)).date(); is_tomorrow = True
        else:
            display_date = now.date(); is_tomorrow = False
        GRACE = 10
        result = []
        for ev in events:
            if not _schedule_event_active_for_date(ev, display_date): continue
            ev_time = ev.get("time","")
            if ev_time and not is_tomorrow:
                try:
                    hh,mm = map(int,ev_time.split(":"))
                    if now.hour*60+now.minute > hh*60+mm+GRACE: continue
                except: pass
            result.append(ev)
        return result

    def build(self):
        p = self.pc
        pt,pb,pl,pr = _get_pads(p, 14)
        self._pt=pt; self._pb=pb; self._pl=pl; self._pr=pr
        transparent = p.get("bg_transparent",False)
        tag = self._tag

        # Background rectangle (opaque only)
        if not transparent:
            bg_img = p.get("bg_image","")
            if not (bg_img and os.path.exists(bg_img)):
                self.canvas.create_rectangle(self.ox, self.oy,
                    self.ox+self.W, self.oy+self.H,
                    fill=p.get("bg_color","#111128"), outline="", tags=tag)

        self._draw()

    def _draw(self):
        p = self.pc
        # Remove old content items but keep background rect
        # Re-tag content items with a sub-tag
        for item in self.canvas.find_withtag(self._tag + "_content"):
            self.canvas.delete(item)
        content_tag = self._tag + "_content"
        self.canvas.addtag_withtag(content_tag, "___never___")  # init tag

        W=self.W; H=self.H; pt=self._pt; pb=self._pb; pl=self._pl; pr=self._pr
        usable_w = W-pl-pr; usable_h = H-pt-pb

        name_ff  = p.get("name_font_family",p.get("font_family","Arial"))
        name_fs  = p.get("name_font_size",  p.get("font_size",20))
        name_fc  = p.get("name_font_color", p.get("font_color","#ffffff"))
        time_ff  = p.get("time_font_family",p.get("font_family","Arial"))
        time_fs  = p.get("time_font_size",  p.get("font_size",20))
        time_fc  = p.get("time_font_color", "#aaddff")
        bold   = "bold"   if p.get("bold",False)   else "normal"
        italic = "italic" if p.get("italic",False) else "roman"
        name_font = (name_ff,name_fs,bold,italic)
        time_font = (time_ff,time_fs,bold,italic)

        events = self._get_upcoming_events()
        tags = (self._tag, content_tag)

        if not events:
            empty = p.get("empty_text","")
            if empty:
                self.canvas.create_text(
                    self.ox+W//2, self.oy+H//2, text=empty,
                    font=name_font, fill=name_fc, anchor="center", tags=tags)
            return

        row_h = max(name_fs,time_fs)+8
        max_rows = max(1, usable_h//row_h)
        y = self.oy + pt + row_h//2
        for ev in events[:max_rows]:
            name = ev.get("name",""); t = ev.get("time","")
            if name and t:
                self.canvas.create_text(self.ox+W-pr, y, text=name,
                    font=name_font, fill=name_fc, anchor="e", tags=tags)
                self.canvas.create_text(self.ox+pl, y, text=t,
                    font=time_font, fill=time_fc, anchor="w", tags=tags)
            else:
                self.canvas.create_text(self.ox+W//2, y, text=name or t,
                    font=name_font, fill=name_fc, anchor="center", tags=tags)
            y += row_h

    def tick(self):
        # Clear and redraw content (events may change as time passes)
        for item in self.canvas.find_withtag(self._tag + "_content"):
            self.canvas.delete(item)
        self._draw()


class DirectZmanimPanel(DirectCanvasPanel):
    def __init__(self, canvas, pc, dsp, ox, oy, W, H):
        self._zcalc = _make_zmanim_calc(dsp.cfg.d)
        self._zdata = {}; self._zdate = None; self._ttime_ids = {}
        super().__init__(canvas, pc, dsp, ox, oy, W, H)

    def _fmt_time(self, z):
        p = self.pc
        try:
            if hasattr(z,"tzinfo") and z.tzinfo:
                import pytz as _pytz
                ltz = _pytz.timezone(self.dsp.cfg.d["location"].get("tz","Asia/Jerusalem"))
                z = z.astimezone(ltz)
            fmt = "%I:%M %p" if p.get("zmanim_time_format","24")=="12" else "%H:%M"
            s = z.strftime(fmt)
            return s.lstrip("0") if fmt.startswith("%I") else s
        except: return "--:--"

    def _label_for(self, k, uid=None):
        if uid and uid != k:
            eff = get_effective_zmanim_entries(self.dsp.cfg.d)
            for e_uid, e_key, e_name, _ in eff:
                if e_uid == uid: return e_name
        custom = self.pc.get("zmanim_custom_names", {})
        return custom.get(k, ZMANIM_KEYS.get(k, k))

    def _get_show_entries(self):
        p = self.pc
        eff = get_effective_zmanim_entries(self.dsp.cfg.d)
        show_items = p.get("show_items", [e[0] for e in eff])
        uid_map = {e[0]: e for e in eff}
        # Build key → list of all entries (including duplicates)
        key_to_entries = {}
        for e in eff:
            k = e[1]
            key_to_entries.setdefault(k, []).append(e)
        result = []
        seen_uids = set()
        for uid in show_items:
            if uid in uid_map:
                e = uid_map[uid]
                if e[0] not in seen_uids:
                    result.append((e[0], e[1], e[2]))
                    seen_uids.add(e[0])
                # Also include any duplicate entries for this key that are NOT in show_items
                key = e[1]
                for dup_e in key_to_entries.get(key, []):
                    if dup_e[0] not in seen_uids:
                        result.append((dup_e[0], dup_e[1], dup_e[2]))
                        seen_uids.add(dup_e[0])
            elif uid in key_to_entries:
                # uid is actually a key string (legacy)
                for e in key_to_entries[uid]:
                    if e[0] not in seen_uids:
                        result.append((e[0], e[1], e[2]))
                        seen_uids.add(e[0])
        return result

    def build(self):
        p = self.pc
        lf  = p.get("zmanim_label_font", p.get("font_family","Arial"))
        ls  = p.get("zmanim_label_size", p.get("font_size",14))
        tf  = p.get("zmanim_time_font",  p.get("font_family","Arial"))
        ts  = p.get("zmanim_time_size",  p.get("font_size",14))
        lc  = p.get("label_color", p.get("font_color","#9090cc"))
        tc  = p.get("time_color",  p.get("title_color", BLUE))
        pt, pb, pl, pr = _get_pads(p, 0)
        cW = max(1, self.W - pl - pr)
        cy = pt + 6
        disp_mode  = p.get("zmanim_display_mode","rows")
        row_layout = p.get("zmanim_row_layout","same_row")
        row_sp     = max(2, int(p.get("zmanim_row_spacing",4)))

        if p.get("show_title",True):
            self.create_text(pl + cW//2, cy, text=p.get("title","זמני היום"),
                font=(tf, ts+4,"bold"), fill=tc, anchor="n")
            cy += ts + 16
            if p.get("show_separator",True):
                self.create_line(pl+4, cy, self.W-pr-4, cy, fill=p.get("border_color",BLUE))
            cy += 8

        # Pre-calculate zmanim so we can sort by actual time
        self._calc_zmanim_data()
        show_entries = self._get_show_entries_sorted()  # sorted by actual time
        self._ttime_ids = {}  # uid → canvas item id
        self._disp_mode = disp_mode
        self._inline_x = float(self.W + 10)

        if disp_mode == "inline":
            self._inline_id = self.create_text(pl + cW//2, cy, text="",
                font=(tf,ts), fill=tc, anchor="n", width=cW)
        else:
            for uid, key, label_text in show_entries:
                if row_layout == "stacked":
                    self.create_text(self.W-pr-4, cy, text=label_text,
                        font=(lf,ls), fill=lc, anchor="ne")
                    cy += ls + 2
                    tid = self.create_text(self.W-pr-4, cy, text="--:--",
                        font=(tf,ts,"bold"), fill=tc, anchor="ne")
                    self._ttime_ids[uid] = tid
                    cy += ts + row_sp
                else:
                    tid = self.create_text(pl+6, cy, text="--:--",
                        font=(tf,ts,"bold"), fill=tc, anchor="nw")
                    self._ttime_ids[uid] = tid
                    self.create_text(self.W-pr-6, cy, text=label_text,
                        font=(lf,ls), fill=lc, anchor="ne")
                    cy += max(ts,ls) + row_sp
        self._update_labels()

    def _calc_zmanim_data(self):
        """Calculate zmanim data without rebuilding UI. Called from build() and _calc_zmanim()."""
        today = date.today()
        try: self._zcalc = _make_zmanim_calc(self.dsp.cfg.d)
        except: pass
        try:
            global_zdata = self._zcalc.calc(today) or {}
        except:
            global_zdata = {}
        self._zdate = today
        # Build per-uid zdata with per-entry method overrides
        try:
            eff = get_effective_zmanim_entries(self.dsp.cfg.d)
        except:
            eff = []
        loc = self.dsp.cfg.d.get("location", {})
        self._zdata_uid = {}
        for uid, key, name, method_override in eff:
            if method_override:
                try:
                    alt_calc = ZmanimCalc(loc.get("lat",31.7683), loc.get("lng",35.2137),
                                         loc.get("elev",0), loc.get("tz","Asia/Jerusalem"),
                                         method=method_override)
                    alt_data = alt_calc.calc(today) or {}
                    self._zdata_uid[uid] = alt_data.get(key)
                except:
                    self._zdata_uid[uid] = global_zdata.get(key)
            else:
                self._zdata_uid[uid] = global_zdata.get(key)
        self._zdata = global_zdata

    def _get_show_entries_sorted(self):
        """Return show_entries sorted by actual calculated time (chronological)."""
        entries = self._get_show_entries()
        def _sort_key(e):
            uid = e[0]
            z = self._zdata_uid.get(uid) if hasattr(self,"_zdata_uid") else None
            if z is None: return datetime.max
            try:
                zn = z.replace(tzinfo=None) if (hasattr(z,"tzinfo") and z.tzinfo) else z
                return zn
            except: return datetime.max
        return sorted(entries, key=_sort_key)

    def _calc_zmanim(self):
        today = date.today()
        self._calc_zmanim_data()
        # If show_items might have changed or date changed, rebuild completely
        # to get correct sorted order
        self.delete()
        self.build()
        return  # build() calls _update_labels already

    def _update_labels(self):
        p = self.pc
        tc = p.get("time_color", p.get("title_color",BLUE))
        show_entries = self._get_show_entries()
        disp_mode = getattr(self,"_disp_mode", p.get("zmanim_display_mode","rows"))
        if disp_mode == "inline":
            sep = p.get("zmanim_inline_sep"," | ")
            parts = []
            for uid, key, label_text in show_entries:
                z = self._zdata_uid.get(uid) if hasattr(self,"_zdata_uid") else self._zdata.get(key)
                parts.append(f"{label_text} {self._fmt_time(z) if z else '--:--'}")
            if hasattr(self,"_inline_id"):
                self.itemconfig(self._inline_id, text=sep.join(parts))
            return
        for uid, tid in self._ttime_ids.items():
            z = self._zdata_uid.get(uid) if hasattr(self,"_zdata_uid") else self._zdata.get(uid)
            self.itemconfig(tid, text=self._fmt_time(z) if z else "--:--")
        if p.get("highlight_next",True):
            now_t = datetime.now(); next_uid = None; next_t = None
            zdata_check = self._zdata_uid if hasattr(self,"_zdata_uid") else {}
            for uid, z in zdata_check.items():
                if z and uid in self._ttime_ids:
                    try:
                        zn = z.replace(tzinfo=None) if (hasattr(z,"tzinfo") and z.tzinfo) else z
                        if zn > now_t and (next_t is None or zn < next_t):
                            next_t = zn; next_uid = uid
                    except: pass
            hc = p.get("highlight_color",GOLD)
            for uid, tid in self._ttime_ids.items():
                self.itemconfig(tid, fill=hc if uid==next_uid else tc)

    def tick(self):
        today = date.today()
        cur_method = self.dsp.cfg.d.get("location",{}).get("zmanim_method","kosherzmanim")
        if today != self._zdate or getattr(self,"_last_method","") != cur_method:
            self._last_method = cur_method
            self._zdate = None
            self._calc_zmanim()  # rebuilds completely with sorted order
        else:
            self._update_labels()
        # Inline scrolling
        p = self.pc
        if getattr(self,"_disp_mode","rows") == "inline":
            scroll_dir = p.get("zmanim_scroll","none")
            if scroll_dir != "none" and hasattr(self,"_inline_id"):
                speed = max(1, int(p.get("zmanim_scroll_speed",2)))
                W = p.get("width",360)
                try:
                    bb = self.bbox(self._inline_id)
                    tw = (bb[2]-bb[0]) if bb else W
                except: tw = W
                self._inline_x -= speed
                if self._inline_x < -(tw+20): self._inline_x = float(W+10)
                cy = p.get("height",490)//2
                try: self.canvas.coords(self._inline_id, self.ox+self._inline_x, self.oy+cy)
                except: pass


class DirectNoticePanel(DirectCanvasPanel):
    def build(self):
        p = self.pc
        ff = p.get("font_family","Arial"); fs = p.get("font_size",26)
        fc = p.get("font_color",GOLD)
        wt = "bold" if p.get("bold",True) else "normal"
        text = p.get("content","")
        self._scroll = p.get("scroll",True)
        self._speed = max(1, p.get("scroll_speed",2))
        self._dir = p.get("scroll_dir","rtl")
        self._tx = self.W if self._dir=="rtl" else -100
        self._ty = self.H//2
        self._tid = self.create_text(self._tx, self._ty, text=text,
            font=(ff,fs,wt), fill=fc,
            anchor="w" if self._dir=="rtl" else "e")
        bb = self.bbox(self._tid)
        self._tw = (bb[2]-bb[0]) if bb else len(text)*fs//2

    def tick(self):
        if not getattr(self,"_scroll",True): return
        try:
            if self._dir=="rtl":
                self._tx -= self._speed
                if self._tx < -(self._tw+20): self._tx = self.W+10
            else:
                self._tx += self._speed
                if self._tx > self.W+self._tw+20: self._tx = -(self._tw+10)
            self.coords(self._tid, self._tx, self._ty)
        except: pass

    def build_content_override(self, text):
        self.pc["content"] = text
        try: self.itemconfig(self._tid, text=text)
        except: pass


class DirectAdPanel(DirectCanvasPanel):
    """Ad/image slideshow panel drawn directly on bg_canvas.
    Supports: JPEG, PNG, BMP, GIF (animated — each frame = one slide),
    PDF (each page = one slide), MP4 (sampled frames = slides).
    Each entry in pc['images'] may be a plain path string or a dict with 'path' key.
    """

    # ── helpers ──────────────────────────────────────────────────────────────
    def _fit_frame(self, img_rgba):
        """Resize / crop an RGBA PIL image to (W,H) according to fit_mode."""
        W = self.W; H = self.H
        fit = self.pc.get("fit_mode", "contain")
        if fit == "contain":
            img_rgba.thumbnail((W, H), Image.LANCZOS)
            comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            comp.paste(img_rgba, ((W - img_rgba.width) // 2,
                                  (H - img_rgba.height) // 2), img_rgba)
            return comp
        elif fit == "stretch":
            return img_rgba.resize((W, H), Image.LANCZOS)
        else:  # cover
            ratio = max(W / img_rgba.width, H / img_rgba.height)
            img_rgba = img_rgba.resize((int(img_rgba.width * ratio),
                                        int(img_rgba.height * ratio)), Image.LANCZOS)
            x0 = (img_rgba.width  - W) // 2
            y0 = (img_rgba.height - H) // 2
            return img_rgba.crop((x0, y0, x0 + W, y0 + H))

    def _load_gif_frames(self, path):
        """Extract all frames from an animated GIF as PhotoImages."""
        frames = []
        try:
            gif = Image.open(path)
            while True:
                frame = gif.convert("RGBA")
                frames.append(ImageTk.PhotoImage(self._fit_frame(frame).convert("RGB")))
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
        except Exception:
            pass
        return frames

    def _load_pdf_frames(self, path):
        """Render each PDF page as a PhotoImage (requires pdf2image / poppler)."""
        frames = []
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(path, dpi=150)
            for page in pages:
                frames.append(ImageTk.PhotoImage(
                    self._fit_frame(page.convert("RGBA")).convert("RGB")))
        except Exception:
            pass
        return frames

    def _load_mp4_frames(self, path, max_frames=30):
        """Sample frames from an MP4 video as PhotoImages."""
        frames = []
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            step = max(1, total // max_frames)
            idx = 0
            while True:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    break
                # cv2 → RGB → PIL
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(rgb).convert("RGBA")
                frames.append(ImageTk.PhotoImage(self._fit_frame(pil).convert("RGB")))
                idx += step
                if len(frames) >= max_frames:
                    break
            cap.release()
        except Exception:
            pass
        return frames

    def build(self):
        p = self.pc
        self._imgs = []; self._cur = 0; self._last = 0.0
        self._gif_mode = False          # True when showing a single animated GIF
        self._gif_frame_idx = 0
        self._gif_delay = 100           # ms per GIF frame (updated from image)
        self._gif_delays = []           # per-frame durations in ms
        self._gif_last = 0.0
        self._interval = max(1, p.get("interval", 5))
        self._img_id = self.create_image(self.W // 2, self.H // 2, anchor="center")
        if not PIL_AVAILABLE:
            return
        raw_images = p.get("images", [])
        for entry in raw_images:
            # Support both plain-string paths and dict entries {"path": ..., ...}
            if isinstance(entry, str):
                path = entry
            elif isinstance(entry, dict):
                path = entry.get("path", "")
            else:
                continue
            if not path or not os.path.exists(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".gif":
                    # Animated GIF — extract all frames; if multiple GIFs or mixed
                    # media, each GIF contributes its first frame only (slideshow mode).
                    gif = Image.open(path)
                    frame_count = getattr(gif, "n_frames", 1)
                    if frame_count > 1 and len(raw_images) == 1:
                        # Single animated GIF: play animation frame-by-frame
                        self._gif_mode = True
                        self._gif_delays = []
                        while True:
                            try:
                                dur = gif.info.get("duration", 100)
                                self._gif_delays.append(max(50, int(dur)))
                                self._imgs.append(ImageTk.PhotoImage(
                                    self._fit_frame(gif.convert("RGBA")).convert("RGB")))
                                gif.seek(gif.tell() + 1)
                            except EOFError:
                                break
                    else:
                        # Multiple sources or static GIF — use first frame only
                        self._imgs.append(ImageTk.PhotoImage(
                            self._fit_frame(gif.convert("RGBA")).convert("RGB")))
                elif ext == ".pdf":
                    for ph in self._load_pdf_frames(path):
                        self._imgs.append(ph)
                elif ext == ".mp4":
                    for ph in self._load_mp4_frames(path):
                        self._imgs.append(ph)
                else:
                    img = Image.open(path).convert("RGBA")
                    self._imgs.append(ImageTk.PhotoImage(
                        self._fit_frame(img).convert("RGB")))
            except Exception:
                pass
        if self._imgs:
            self.itemconfig(self._img_id, image=self._imgs[0])

    def tick(self):
        if not self._imgs:
            return
        now = time.time()
        if self._gif_mode:
            # Animated GIF: advance frames using per-frame delay
            delay_sec = (self._gif_delays[self._gif_frame_idx]
                         if self._gif_delays else 100) / 1000.0
            if now - self._gif_last >= delay_sec:
                self._gif_last = now
                self._gif_frame_idx = (self._gif_frame_idx + 1) % len(self._imgs)
                try:
                    self.itemconfig(self._img_id, image=self._imgs[self._gif_frame_idx])
                except Exception:
                    pass
        else:
            if now - self._last >= self._interval:
                self._last = now
                self._cur = (self._cur + 1) % len(self._imgs)
                try:
                    self.itemconfig(self._img_id, image=self._imgs[self._cur])
                except Exception:
                    pass


class DirectElemPanel(DirectCanvasPanel):
    """Element panel drawn directly on bg_canvas.
    Uses PIL compositing against _bg_pil (which is updated in render order to include
    all previously-drawn panels) — fast, no pixel loops, no screenshots.
    Transparent pixels in the element image show whatever _bg_pil has beneath."""

    def build(self):
        p = self.pc; W = self.W; H = self.H
        img_path = p.get("image_path","")
        if img_path and os.path.exists(img_path) and PIL_AVAILABLE:
            try:
                img = Image.open(img_path).convert("RGBA")
                fit = p.get("fit_mode","contain")
                if fit == "contain":
                    img.thumbnail((W,H), Image.LANCZOS)
                elif fit == "stretch":
                    img = img.resize((W,H), Image.LANCZOS)
                else:  # cover
                    ratio = max(W/img.width, H/img.height)
                    img = img.resize((int(img.width*ratio),int(img.height*ratio)), Image.LANCZOS)
                ox = (W - img.width)//2; oy = (H - img.height)//2

                # Use _bg_pil as the background — it reflects all panels drawn before this one
                # in render order (baked in by _bake_panel_into_bg_pil).
                # Composite element RGBA on top of that background region.
                bg_pil = getattr(self.dsp, "_bg_pil", None)
                if bg_pil:
                    x0 = max(0, p.get("x",0)); y0 = max(0, p.get("y",0))
                    region = bg_pil.crop((x0, y0, x0+W, y0+H)).convert("RGBA")
                else:
                    try:
                        bgc = self.dsp.cfg.d["display"].get("bg_color",BG).lstrip("#")
                        rgb = tuple(int(bgc[i:i+2],16) for i in (0,2,4))
                    except: rgb=(7,7,20)
                    region = Image.new("RGBA",(W,H),rgb+(255,))

                region.paste(img, (ox, oy), img)   # alpha-composite element onto background
                self._photo = ImageTk.PhotoImage(region.convert("RGB"))
                self.create_image(0, 0, anchor="nw", image=self._photo)
                return
            except: pass
        self.create_text(W//2, H//2, text="🎨\nאלמנט עיצובי",
            font=("Arial",12), fill=TEXT2, anchor="center")

    def tick(self): pass

# ── חלוניות עם רקע שקוף (CanvasBackedPanel — legacy, still used for popup notices) ──
class CanvasBackedPanel(tk.Canvas):
    """
    Base for transparent panels: a tk.Canvas whose background is a PIL-composited
    crop of the actual display background (gradient + stars + bg_image),
    PLUS any non-transparent panels that appear below this one (higher layer number).
    Content (text, images) is drawn as canvas items on top — giving true visual
    transparency that works across all overlapping panels.
    """
    def __init__(self, parent, pc, dsp):
        self.pc = pc; self.dsp = dsp
        W = pc.get("width", 300); H = pc.get("height", 200)
        bw = 0 if pc.get("border_transparent", False) else pc.get("border_width", 2)
        bc = pc.get("border_color", BLUE)
        bg_color = pc.get("bg_color", PNL)
        transparent = pc.get("bg_transparent", False)
        has_bg_img = (not transparent and bool(pc.get("bg_image","")) and
                      os.path.exists(pc.get("bg_image","") or "") and PIL_AVAILABLE)

        # Canvas bg: use bg_color (will be covered by image or composited transparency)
        init_bg = dsp._get_bg_at_y(pc.get("y", 0)) if transparent and not PIL_AVAILABLE else bg_color
        super().__init__(parent, width=W, height=H, bg=init_bg,
                         highlightthickness=bw, highlightbackground=bc,
                         highlightcolor=bc)
        self._bg_photo = None

        if has_bg_img:
            # bg_image mode: load the image directly as canvas background.
            # bg_color is completely ignored when bg_image is set.
            try:
                img = Image.open(pc["bg_image"]).resize((W, H), Image.LANCZOS)
                self._bg_photo = ImageTk.PhotoImage(img)
                self.create_image(0, 0, anchor="nw", image=self._bg_photo, tags="cbp_bg")
                self.tag_lower("cbp_bg")
            except: pass
        else:
            # Transparency mode: composite real background (including lower-layer panels).
            # This is a best-effort early render; _update_transparent_bgs refines it
            # after all panels are placed and _panel_dims is fully populated.
            photo = dsp._get_composite_bg_photo(pc)
            if photo:
                self._bg_photo = photo  # keep reference to prevent GC
                self.create_image(0, 0, anchor="nw", image=photo, tags="cbp_bg")
                self.tag_lower("cbp_bg")
        self.build()


class TransparentTextPW(CanvasBackedPanel):
    """Text panel with transparent or bg-image background.
    Uses CanvasBackedPanel (a tk.Canvas widget) so content is naturally clipped
    to the widget boundary — no screen-covering stencils needed, no interference
    with other panels.  Supports all scroll modes with per-segment styling and
    seamless two-copy loop.
    """
    _RLM = "\u200f"

    def _rfix(self, text):
        if not text: return text
        lines = []
        for l in text.split("\n"):
            has_heb = any('\u0590' <= ch <= '\u05FF' or '\uFB1D' <= ch <= '\uFB4F' for ch in l)
            lines.append(self._RLM + l if (has_heb and l) else l)
        return "\n".join(lines)

    def _font_spec(self):
        p = self.pc
        ff = p.get("font_family","Arial"); fs = p.get("font_size",20)
        wt = "bold"   if p.get("bold",False)   else "normal"
        sl = "italic" if p.get("italic",False)  else "roman"
        return (ff, fs, wt, sl)

    def _seg_font_spec(self, sd):
        p = self.pc
        ff = sd.get("font_family", p.get("font_family","Arial"))
        fs = sd.get("font_size",   p.get("font_size",20))
        wt = "bold"   if sd.get("bold",   p.get("bold",False))   else "normal"
        sl = "italic" if sd.get("italic", p.get("italic",False))  else "roman"
        fc = sd.get("font_color",  p.get("font_color","#ffffff"))
        return (ff, fs, wt, sl), fc

    def _build_seg_items(self, horiz=False):
        p = self.pc
        sep_space = p.get("seg_separator_space", True)
        sep_char  = (p.get("seg_separator_char","") or "").strip()
        def_font  = self._font_spec()
        def_fc    = p.get("font_color","#ffffff")
        segs = p.get("content_segments",[])
        raw_items = []
        if segs:
            for sd in segs:
                t = sd.get("text","")
                if not t.strip(): continue
                if horiz: t = t.replace("\n"," ").strip()
                font, fc = self._seg_font_spec(sd)
                raw_items.append((self._rfix(t), font, fc))
        else:
            raw = p.get("content","")
            if horiz: raw = raw.replace("\n"," ").strip()
            if raw.strip():
                raw_items.append((self._rfix(raw), def_font, def_fc))
        if not raw_items: return []
        if len(raw_items) == 1: return raw_items
        result = []
        for i, item in enumerate(raw_items):
            result.append(item)
            if i < len(raw_items) - 1:
                if horiz:
                    sep_txt = ("  " if sep_space else "") + (sep_char or "") + ("  " if sep_space else "")
                    result.append((sep_txt or "   ", def_font, def_fc))
                else:
                    sep_lines = []
                    if sep_space: sep_lines.append("")
                    if sep_char:  sep_lines.append(sep_char)
                    if sep_space and sep_char: sep_lines.append("")
                    if sep_lines:
                        result.append((self._rfix("\n".join(sep_lines)), def_font, def_fc))
        return result

    def build(self):
        p = self.pc
        raw_mode = p.get("scroll_mode","scroll_up")
        if raw_mode == "scroll": raw_mode = "scroll_up"
        self._mode = raw_mode
        W = p.get("width",350); H = p.get("height",180)
        pt, pb, pl, pr = _get_pads(p, 14)
        content_w = max(4, W - pl - pr)
        content_h = max(4, H - pt - pb)
        cx = pl + content_w // 2
        align = p.get("align","right")
        j = {"right":"right","left":"left","center":"center"}.get(align,"right")

        self._scroll_tids = []; self._tid = None
        horiz = (raw_mode == "scroll_right")
        seg_items = self._build_seg_items(horiz=horiz)
        if not seg_items:
            seg_items = [(self._rfix(p.get("content","")), self._font_spec(), p.get("font_color","#ffffff"))]
        self._seg_items_cache = seg_items

        if raw_mode == "static":
            cy_now = pt + 4
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self.create_text(cx, cy_now, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n", tags="content")
                self.update_idletasks()
                bb = self.bbox(tid)
                cy_now += ((bb[3]-bb[1]) if bb else seg_font[1]+4) + 4

        elif raw_mode == "scroll_up":
            GAP = 30
            heights = []
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self.create_text(cx, H + 9000, text=seg_text,
                    font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n", tags="content")
                self.update_idletasks()
                bb = self.bbox(tid)
                heights.append((bb[3]-bb[1]) if bb else seg_font[1]+4)
                self.delete(tid)
            offsets = []; cur_dy = 0
            for h in heights: offsets.append(cur_dy); cur_dy += h + 4
            total_h = cur_dy; stride = total_h + GAP
            self._th = total_h; self._loop_stride = stride
            start_y = float(H)
            self._anchor_y = start_y
            for copy_num in range(2):
                base_dy = copy_num * stride
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dy = base_dy + offsets[i]
                    tid = self.create_text(cx, start_y + dy, text=seg_text,
                        font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="n", tags="content")
                    self._scroll_tids.append((tid, dy))

        elif raw_mode == "scroll_right":
            GAP = 60
            mid_y = pt + content_h // 2
            widths = []
            for seg_text, seg_font, seg_fc in seg_items:
                tid = self.create_text(W + 9000, mid_y, text=seg_text,
                    font=seg_font, fill=seg_fc, anchor="w", tags="content")
                self.update_idletasks()
                bb = self.bbox(tid)
                widths.append((bb[2]-bb[0]) if bb else 80)
                self.delete(tid)
            offsets_x = []; cur_dx = 0
            for w in widths: offsets_x.append(cur_dx); cur_dx += w
            total_w = cur_dx; stride_x = total_w + GAP
            self._th = total_w; self._loop_stride_x = stride_x
            # Start from left of widget (negative x), text moves rightward
            start_x = float(-total_w - GAP)
            self._anchor_x = start_x
            for copy_num in range(2):
                base_dx = copy_num * stride_x
                for i, (seg_text, seg_font, seg_fc) in enumerate(seg_items):
                    dx = base_dx + offsets_x[i]
                    tid = self.create_text(start_x + dx, mid_y,
                        text=seg_text, font=seg_font, fill=seg_fc, anchor="w", tags="content")
                    self._scroll_tids.append((tid, dx))

        elif raw_mode == "segments":
            self._seg_idx = 0; self._seg_last = time.time()
            segs_cfg = p.get("content_segments",[])
            self._seg_durations = [max(2,int(s.get("duration", p.get("segment_duration",5)))) for s in segs_cfg if s.get("text","").strip()] if segs_cfg else [max(2,p.get("segment_duration",5))]
            seg_text, seg_font, seg_fc = seg_items[0]
            self._tid = self.create_text(cx, pt + content_h // 2, text=seg_text,
                font=seg_font, fill=seg_fc, justify=j, width=content_w, anchor="center", tags="content")

    def tick(self):
        p = self.pc
        mode = p.get("scroll_mode","scroll_up")
        if mode == "scroll": mode = "scroll_up"

        if mode == "static": return

        elif mode == "scroll_up":
            if not self._scroll_tids: return
            try:
                W = p.get("width",350); H = p.get("height",180)
                pt, pb, pl, pr = _get_pads(p, 14)
                cx2 = pl + (W - pl - pr) // 2
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_y -= spd
                stride = getattr(self, "_loop_stride", self._th + 30)
                if self._anchor_y < -stride:
                    self._anchor_y += stride
                for tid, dy in self._scroll_tids:
                    self.coords(tid, cx2, self._anchor_y + dy)
            except: pass

        elif mode == "scroll_right":
            if not self._scroll_tids: return
            try:
                W2 = p.get("width",350); H2 = p.get("height",180)
                pt, pb, pl, pr = _get_pads(p, 14)
                mid_y = pt + (H2 - pt - pb) // 2
                spd = max(1, p.get("scroll_speed", 30)) / 10.0
                self._anchor_x += spd  # moves rightward
                stride = getattr(self, "_loop_stride_x", self._th + 60)
                if self._anchor_x > W2 + stride:
                    self._anchor_x -= stride
                for tid, dx in self._scroll_tids:
                    self.coords(tid, self._anchor_x + dx, mid_y)
            except: pass

        elif mode == "segments":
            if not self._tid: return
            now = time.time()
            seg_items = getattr(self, "_seg_items_cache", [])
            durs = getattr(self, "_seg_durations", [max(2,p.get("segment_duration",5))])
            dur = durs[self._seg_idx % max(1,len(durs))] if durs else max(2,p.get("segment_duration",5))
            new_items = self._build_seg_items()
            if not new_items:
                new_items = [(self._rfix(p.get("content","")), self._font_spec(), p.get("font_color","#ffffff"))]
            segs_cfg = p.get("content_segments",[])
            new_durs = [max(2,int(s.get("duration", p.get("segment_duration",5)))) for s in segs_cfg if s.get("text","").strip()] if segs_cfg else [max(2,p.get("segment_duration",5))]
            if new_items != seg_items or new_durs != durs:
                self._seg_items_cache = new_items; self._seg_durations = new_durs
                self._seg_idx = 0; self._seg_last = now
                if new_items:
                    st, sf, sfc = new_items[0]
                    try: self.itemconfig(self._tid, text=st, font=sf, fill=sfc)
                    except: pass
                return
            if now - self._seg_last >= dur:
                self._seg_last = now
                self._seg_idx = (self._seg_idx + 1) % max(1, len(seg_items))
                st, sf, sfc = seg_items[self._seg_idx]
                try: self.itemconfig(self._tid, text=st, font=sf, fill=sfc)
                except: pass

    def build_content_override(self, text):
        self.pc["content"] = text
        if self._tid:
            try: self.itemconfig(self._tid, text=self._rfix(text))
            except: pass
class TransparentNoticePW(CanvasBackedPanel):
    """Scrolling notice with transparent background."""
    def build(self):
        p=self.pc; W=p.get("width",900); H=p.get("height",80)
        ff=p.get("font_family","Arial"); fs=p.get("font_size",26)
        fc=p.get("font_color",GOLD)
        wt="bold" if p.get("bold",True) else "normal"
        text=p.get("content","")
        self._scroll=p.get("scroll",True)
        self._speed=max(1,p.get("scroll_speed",2))
        self._dir=p.get("scroll_dir","rtl")
        if self._dir=="rtl":
            self._tx=W
        else:
            self._tx=-100
        self._tid=self.create_text(self._tx,H//2,text=text,
            font=(ff,fs,wt),fill=fc,
            anchor="w" if self._dir=="rtl" else "e",tags="content")
        self.update_idletasks()
        try:
            bb=self.bbox(self._tid); self._tw=(bb[2]-bb[0]) if bb else len(text)*fs//2
        except: self._tw=len(text)*fs//2

    def tick(self):
        if not getattr(self,"_scroll",True): return
        try:
            W=self.pc.get("width",900)
            if self._dir=="rtl":
                self._tx-=self._speed
                if self._tx<-(self._tw+20): self._tx=W+10
            else:
                self._tx+=self._speed
                if self._tx>W+self._tw+20: self._tx=-(self._tw+10)
            self.coords(self._tid,self._tx,self.pc.get("height",80)//2)
        except: pass

    def build_content_override(self, text):
        self.pc["content"]=text
        try: self.itemconfig(self._tid,text=text)
        except: pass


class TransparentClockPW(CanvasBackedPanel):
    """Clock-only panel with transparent background.
    Analog clock is drawn directly on the CanvasBackedPanel (no nested Canvas —
    tkinter does not support bg="" on Canvas). The composited background image
    already fills self; clock items are drawn above it with fill="" face = transparent.
    """
    def build(self):
        p = self.pc
        W = p.get("width", 280); H = p.get("height", 280)
        cc = p.get("font_color", p.get("clock_color", BLUE))
        ff = p.get("font_family", "Arial")
        self._clock_W = W; self._clock_H = H
        self._clock_analog = p.get("clock_style", "digital") == "analog"
        if not self._clock_analog:
            fs = p.get("font_size", p.get("time_font_size", 56))
            self._t_id = self.create_text(W // 2, H // 2, text="",
                font=(ff, fs, "bold"), fill=cc, anchor="center", tags="content")
        self.tick()

    def tick(self):
        now = datetime.now(); p = self.pc
        if p.get("clock_style", "digital") == "analog":
            # Remove previous clock drawing items (keep cbp_bg background)
            self.delete("clock_items")
            cw = self.winfo_width() or self._clock_W
            ch = self.winfo_height() or self._clock_H
            _draw_analog_clock(self, p, now, cw, ch, transparent_bg=True,
                               tag="clock_items")
        else:
            if hasattr(self, "_t_id"):
                sec = ":%S" if p.get("show_seconds", True) else ""
                fmt = f"%I:%M{sec} %p" if p.get("time_format","24")=="12" else f"%H:%M{sec}"
                self.itemconfig(self._t_id, text=now.strftime(fmt))


class TransparentDatePW(CanvasBackedPanel):
    """Date-only panel with transparent/image background.
    Full feature parity with DirectDatePanel: per-item colors, padding,
    new fields (torah, hazkarot, daf), and multi-line inline wrap."""

    def build(self):
        p = self.pc
        W = p.get("width", 280); H = p.get("height", 160)
        ff = p.get("font_family", "Arial")
        fs = p.get("font_size", p.get("date_font_size", 18))
        fc = p.get("font_color", p.get("date_color", TEXT))
        sp = p.get("date_line_spacing", 4)

        def icol(key, default):
            return p.get(key, fc if key not in ("hol_color","par_color") else default)

        self._ff = ff; self._fs = fs; self._fc = fc
        self._sep = p.get("date_separator", " | ")
        self._layout_mode = p.get("date_layout", "stacked")
        self._hol_cache = ""; self._par_cache = ""; self._par_last = None
        self._extra_last = None; self._prayer_cache = {}
        self._torah_cache = ("",""); self._daf_cache = ""
        self._items = {}
        self._inline_item_ids = []

        pt, pb, pl, pr_ = _get_pads(p, 0)
        cW = max(1, W - pl - pr_)
        cH = max(1, H - pt - pb)
        cx_mid = pl + cW // 2

        if self._layout_mode == "inline":
            # Params stored; items built dynamically in tick()
            self._pt = pt; self._pl = pl; self._cW = cW; self._cH = cH
        else:
            cy = pt + 6
            base_rows = [
                ("wd",  "show_weekday",    icol("wd_color",  TEXT), True),
                ("hd",  "show_heb_date",   icol("hd_color",  TEXT), False),
                ("gd",  "show_greg_date",  icol("gd_color",  TEXT), False),
                ("hol", "show_holiday",    icol("hol_color", GOLD), True),
                ("par", "show_parasha",    icol("par_color", LBLUE), False),
            ]
            new_rows = [
                ("tor",      "show_torah_reading",  p.get("tor_color",      "#aaffaa"), False),
                ("haf",      "show_haftara",         p.get("haf_color",      "#aaffcc"), False),
                ("yaaleh",   "show_yaaleh_veyavo",   p.get("yaaleh_color",   "#ffdd88"), False),
                ("morid_tal","show_morid_hatal",     p.get("morid_tal_color","#88ddff"), False),
                ("mashiv",   "show_mashiv_haruach",  p.get("mashiv_color",   "#88ccff"), False),
                ("vten",     "show_vten_tal_umatar", p.get("vten_color",     "#ffcc88"), False),
                ("daf",      "show_daf_yomi",        p.get("daf_color",      "#ccaaff"), False),
            ]
            base_keys = {r[0] for r in base_rows}
            for key, show_key, color, bold in base_rows + new_rows:
                default_val = key in base_keys
                if p.get(show_key, default_val):
                    font_spec = (ff, fs, "bold") if bold else (ff, fs)
                    self._items[key] = self.create_text(
                        cx_mid, cy, text="",
                        font=font_spec, fill=color, anchor="n", tags="content")
                    cy += fs + sp
        self.tick()

    def _get_parts(self, now, p):
        """Return list of (text, color) for active items."""
        fc = self._fc
        def icol(key, default):
            return p.get(key, fc if key not in ("hol_color","par_color") else default)
        parts = []
        if p.get("show_weekday", True):
            parts.append((get_weekday_heb(), icol("wd_color", fc)))
        if p.get("show_heb_date", True):
            hd = get_heb_date(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
            if hd: parts.append((fmt_heb_date(*hd), icol("hd_color", fc)))
        if p.get("show_greg_date", True):
            parts.append((now.strftime("%d/%m/%Y"), icol("gd_color", fc)))
        if p.get("show_holiday", True) and self._hol_cache:
            parts.append((f"🕍 {self._hol_cache}", icol("hol_color", GOLD)))
        if p.get("show_parasha", True) and self._par_cache:
            parts.append((f"פרשת {self._par_cache}", icol("par_color", LBLUE)))
        tor, haf = self._torah_cache
        pr = self._prayer_cache
        if p.get("show_torah_reading", False) and tor:
            parts.append((tor, p.get("tor_color", "#aaffaa")))
        if p.get("show_haftara", False) and haf:
            parts.append((haf, p.get("haf_color", "#aaffcc")))
        if p.get("show_yaaleh_veyavo", False) and pr.get("yaaleh_veyavo"):
            parts.append((pr["yaaleh_veyavo"], p.get("yaaleh_color", "#ffdd88")))
        if p.get("show_morid_hatal", False) and pr.get("morid_hatal"):
            parts.append((pr["morid_hatal"], p.get("morid_tal_color", "#88ddff")))
        if p.get("show_mashiv_haruach", False) and pr.get("mashiv_haruach"):
            parts.append((pr["mashiv_haruach"], p.get("mashiv_color", "#88ccff")))
        if p.get("show_vten_tal_umatar", False) and pr.get("vten_tal_umatar"):
            parts.append((pr["vten_tal_umatar"], p.get("vten_color", "#ffcc88")))
        if p.get("show_daf_yomi", False) and self._daf_cache:
            parts.append((self._daf_cache, p.get("daf_color", "#ccaaff")))
        return parts

    def _rebuild_inline(self, parts):
        """Draw wrapped multi-color lines on this canvas."""
        p = self.pc
        ff = self._ff; fs = self._fs; sep = self._sep
        pt = self._pt; cW = self._cW; cH = self._cH; pl = self._pl
        max_w = max(40, cW - 8)

        try:
            import tkinter.font as _tkF
            _fo = _tkF.Font(family=ff, size=fs)
            def _meas(t): return _fo.measure(t)
        except Exception:
            def _meas(t): return int(len(t) * fs * 0.6)

        sep_w = _meas(sep)

        # Wrap parts into lines
        lines = []
        cur_line = []; cur_w = 0.0
        for txt, col in parts:
            iw = _meas(txt)
            if not cur_line:
                cur_line.append((txt, col)); cur_w = iw
            elif cur_w + sep_w + iw <= max_w:
                cur_line.append((txt, col)); cur_w += sep_w + iw
            else:
                lines.append(cur_line)
                cur_line = [(txt, col)]; cur_w = iw
        if cur_line:
            lines.append(cur_line)

        # Remove old inline items
        for iid in self._inline_item_ids:
            try: self.delete(iid)
            except: pass
        self._inline_item_ids = []

        # Draw centered lines
        line_h = fs + 6
        total_h = len(lines) * line_h
        cy_start = pt + max(0, (cH - total_h) // 2) + fs // 2
        cx_mid = pl + cW // 2

        for li, line_items in enumerate(lines):
            cy = cy_start + li * line_h
            # Measure total line width for centering each item
            total_line_w = sum(_meas(t) for t, c in line_items) + sep_w * (len(line_items) - 1)
            x = cx_mid - total_line_w // 2
            for idx, (txt, col) in enumerate(line_items):
                iw = _meas(txt)
                iid = self.create_text(
                    x + iw // 2, cy, text=txt,
                    font=(ff, fs), fill=col, anchor="center", tags="content")
                self._inline_item_ids.append(iid)
                x += iw
                if idx < len(line_items) - 1:
                    sw = sep_w
                    sep_col = p.get("font_color", p.get("date_color", TEXT))
                    iid2 = self.create_text(
                        x + sw // 2, cy, text=sep,
                        font=(ff, fs), fill=sep_col, anchor="center", tags="content")
                    self._inline_item_ids.append(iid2)
                    x += sep_w

    def tick(self):
        now = get_now(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
        p = self.pc

        if p.get("show_holiday", True):
            self._hol_cache = get_today_holiday(israel=p.get("israel", True)) or ""
        if p.get("show_parasha", True):
            if self._par_last != now.date():
                self._par_cache = get_parasha(israel=p.get("israel", True)) or ""
                self._par_last = now.date()

        needs_new = self._extra_last != now.date()
        if needs_new:
            self._extra_last = now.date()
            self._prayer_cache = get_prayer_additions()
            self._torah_cache  = get_torah_reading(israel=p.get("israel", True))
            self._daf_cache    = get_daf_yomi()

        if self._layout_mode == "inline":
            parts = self._get_parts(now, p)
            self._rebuild_inline(parts)
        else:
            pr = self._prayer_cache
            tor, haf = self._torah_cache
            if "wd"  in self._items: self.itemconfig(self._items["wd"],  text=get_weekday_heb())
            if "hd"  in self._items:
                hd = get_heb_date(getattr(self.dsp, "cfg", None) and self.dsp.cfg.d)
                self.itemconfig(self._items["hd"], text=fmt_heb_date(*hd) if hd else "")
            if "gd"  in self._items: self.itemconfig(self._items["gd"],  text=now.strftime("%d/%m/%Y"))
            if "hol" in self._items: self.itemconfig(self._items["hol"], text=f"🕍 {self._hol_cache}" if self._hol_cache else "")
            if "par" in self._items: self.itemconfig(self._items["par"], text=f"פרשת {self._par_cache}" if self._par_cache else "")
            if "tor"       in self._items: self.itemconfig(self._items["tor"],       text=tor)
            if "haf"       in self._items: self.itemconfig(self._items["haf"],       text=haf)
            if "yaaleh"    in self._items: self.itemconfig(self._items["yaaleh"],    text=pr.get("yaaleh_veyavo",""))
            if "morid_tal" in self._items: self.itemconfig(self._items["morid_tal"], text=pr.get("morid_hatal",""))
            if "mashiv"    in self._items: self.itemconfig(self._items["mashiv"],    text=pr.get("mashiv_haruach",""))
            if "vten"      in self._items: self.itemconfig(self._items["vten"],      text=pr.get("vten_tal_umatar",""))
            if "daf"       in self._items: self.itemconfig(self._items["daf"],       text=self._daf_cache)


class TransparentTimePW(CanvasBackedPanel):
    """Clock / date panel with transparent background."""
    def build(self):
        p=self.pc
        W=p.get("width",420); H=p.get("height",240)
        self._ff=p.get("font_family","Arial")
        # Support unified font_color (new) or separate clock_color/date_color (legacy)
        _fc=p.get("font_color",None)
        self._cc=_fc if _fc else p.get("clock_color",BLUE)
        self._dc=_fc if _fc else p.get("date_color",TEXT)
        self._items={}
        cy=20
        # Unified font_size: clock uses it directly, date items use ~40%
        fs_base=p.get("font_size",p.get("time_font_size",42))
        fs_date=max(10,int(fs_base*0.38))
        if p.get("show_time",True):
            self._items["time"]=self.create_text(W//2,cy,text="",
                font=(self._ff,fs_base,"bold"),
                fill=self._cc,anchor="n",tags="content")
            cy+=fs_base+8
        for key,show_key,color in [
            ("wd","show_weekday",None),
            ("hd","show_heb_date",None),
            ("gd","show_greg_date",None),
            ("hol","show_holiday",GOLD),
            ("par","show_parasha",LBLUE),
        ]:
            if p.get(show_key,True):
                fill=color if color else self._dc
                self._items[key]=self.create_text(W//2,cy,text="",
                    font=(self._ff,fs_date),
                    fill=fill,anchor="n",tags="content")
                cy+=fs_date+4
        self.tick()

    def tick(self):
        now=datetime.now(); p=self.pc
        if "time" in self._items:
            sec=":%S" if p.get("show_seconds",True) else ""
            fmt=f"%I:%M{sec} %p" if p.get("time_format","24")=="12" else f"%H:%M{sec}"
            self.itemconfig(self._items["time"],text=now.strftime(fmt))
        if "wd" in self._items: self.itemconfig(self._items["wd"],text=get_weekday_heb())
        if "hd" in self._items:
            hd=get_heb_date(self.dsp.cfg.d)
            self.itemconfig(self._items["hd"],text=fmt_heb_date(*hd) if hd else "")
        if "gd" in self._items: self.itemconfig(self._items["gd"],text=now.strftime("%d/%m/%Y"))
        if "hol" in self._items:
            hol=get_today_holiday(israel=p.get("israel",True))
            self.itemconfig(self._items["hol"],text=f"🕍 {hol}" if hol else "")
        if "par" in self._items:
            if not hasattr(self,"_par_last") or self._par_last!=now.date():
                self._par_cache=get_parasha(israel=p.get("israel",True))
                self._par_last=now.date()
            par=self._par_cache
            self.itemconfig(self._items["par"],text=f"פרשת {par}" if par else "")



class TransparentZmanimPW(CanvasBackedPanel):
    """Zmanim panel with true transparent background via PIL compositing."""
    def __init__(self, parent, pc, dsp):
        self._zcalc = _make_zmanim_calc(dsp.cfg.d)
        self._zdata = {}; self._zdate = None
        self._ttime_ids = {}
        super().__init__(parent, pc, dsp)

    def _fmt_time(self, z):
        p = self.pc
        try:
            if hasattr(z,"tzinfo") and z.tzinfo:
                import pytz as _pytz
                ltz = _pytz.timezone(self.dsp.cfg.d["location"].get("tz","Asia/Jerusalem"))
                z = z.astimezone(ltz)
            fmt = "%I:%M %p" if p.get("zmanim_time_format","24")=="12" else "%H:%M"
            s = z.strftime(fmt)
            return s.lstrip("0") if fmt.startswith("%I") else s
        except: return "--:--"

    def _label_for(self, k):
        custom = self.pc.get("zmanim_custom_names", {})
        return custom.get(k, ZMANIM_KEYS.get(k, k))

    def build(self):
        p = self.pc
        W = p.get("width",350); H = p.get("height",400)
        lf  = p.get("zmanim_label_font", p.get("font_family","Arial"))
        ls  = p.get("zmanim_label_size", p.get("font_size",14))
        tf  = p.get("zmanim_time_font",  p.get("font_family","Arial"))
        ts  = p.get("zmanim_time_size",  p.get("font_size",14))
        lc  = p.get("label_color", p.get("font_color","#9090cc"))
        tc  = p.get("time_color",  p.get("title_color", BLUE))
        disp_mode  = p.get("zmanim_display_mode","rows")
        row_layout = p.get("zmanim_row_layout","same_row")
        row_sp     = max(2, int(p.get("zmanim_row_spacing",4)))
        cy = 10
        if p.get("show_title", True):
            self.create_text(W//2, cy, text=p.get("title","זמני היום"),
                font=(tf, ts+4, "bold"), fill=tc, anchor="n", tags="content")
            cy += ts + 16
            if p.get("show_separator", True):
                self.create_line(8, cy, W-8, cy, fill=p.get("border_color",BLUE), tags="content")
            cy += 8
        show = p.get("show_items", list(ZMANIM_KEYS.keys()))
        self._ttime_ids = {}
        self._disp_mode = disp_mode
        self._inline_x = float(W + 10)
        if disp_mode == "inline":
            self._inline_id = self.create_text(W//2, cy, text="",
                font=(tf,ts), fill=tc, anchor="n", width=W-16, tags="content")
        else:
            for k in show:
                if k not in ZMANIM_KEYS: continue
                label_text = self._label_for(k)
                if row_layout == "stacked":
                    self.create_text(W-8, cy, text=label_text,
                        font=(lf,ls), fill=lc, anchor="ne", tags="content")
                    cy += ls + 2
                    tid = self.create_text(W-8, cy, text="--:--",
                        font=(tf,ts,"bold"), fill=tc, anchor="ne", tags="content")
                    self._ttime_ids[k] = tid
                    cy += ts + row_sp
                else:
                    tid = self.create_text(8, cy, text="--:--",
                        font=(tf, ts, "bold"), fill=tc, anchor="nw", tags="content")
                    self._ttime_ids[k] = tid
                    self.create_text(W-8, cy, text=label_text,
                        font=(lf, ls), fill=lc, anchor="ne", tags="content")
                    cy += max(ts,ls) + row_sp
        self._calc_zmanim()

    def _calc_zmanim(self):
        today = date.today()
        try: self._zcalc = _make_zmanim_calc(self.dsp.cfg.d)
        except: pass
        self._zdata = self._zcalc.calc(today)
        per_key = self.pc.get("zmanim_per_key_method", {})
        if per_key:
            for k, method in per_key.items():
                if not method: continue
                try:
                    alt_calc = ZmanimCalc(
                        self._zcalc.lat, self._zcalc.lng,
                        self._zcalc.elev, self._zcalc.tz, method=method)
                    alt_data = alt_calc.calc(today)
                    if k in alt_data and alt_data[k] is not None:
                        self._zdata[k] = alt_data[k]
                except: pass
        self._zdate = today
        self._update_labels()

    def _update_labels(self):
        p = self.pc
        tc = p.get("time_color", p.get("title_color", BLUE))
        show = p.get("show_items", list(ZMANIM_KEYS.keys()))
        disp_mode = getattr(self,"_disp_mode", p.get("zmanim_display_mode","rows"))
        if disp_mode == "inline":
            sep = p.get("zmanim_inline_sep"," | ")
            parts = []
            for k in show:
                if k not in ZMANIM_KEYS: continue
                z = self._zdata.get(k)
                t_str = self._fmt_time(z) if z else "--:--"
                parts.append(f"{self._label_for(k)} {t_str}")
            if hasattr(self,"_inline_id"):
                self.itemconfig(self._inline_id, text=sep.join(parts))
            return
        for k, tid in self._ttime_ids.items():
            z = self._zdata.get(k)
            self.itemconfig(tid, text=self._fmt_time(z) if z else "--:--")
        if p.get("highlight_next", True):
            now_t = datetime.now()
            next_k = None; next_t = None
            for k, z in self._zdata.items():
                if z and k in self._ttime_ids:
                    try:
                        zn = z.replace(tzinfo=None) if (hasattr(z,"tzinfo") and z.tzinfo) else z
                        if zn > now_t and (next_t is None or zn < next_t):
                            next_t = zn; next_k = k
                    except: pass
            hc = p.get("highlight_color", GOLD)
            for k, tid in self._ttime_ids.items():
                try: self.itemconfig(tid, fill=hc if k==next_k else tc)
                except: pass

    def tick(self):
        today = date.today()
        cur_method = self.dsp.cfg.d.get("location",{}).get("zmanim_method","kosherzmanim")
        if today != self._zdate or getattr(self,"_last_method","") != cur_method:
            self._last_method = cur_method
            self._zdate = None
            self._calc_zmanim()
        else:
            self._update_labels()


class TransparentAdPW(CanvasBackedPanel):
    """Ad/slideshow panel with true transparent background (CanvasBackedPanel-based).
    Each image is composited onto the real display background (_bg_pil) so that
    transparent pixels in the image (e.g. cutout/PNG) reveal whatever is actually
    behind this panel on the screen — identical in principle to TransparentElemPW.
    Entries in pc['images'] may be plain path strings or dicts {"path":...}.
    Supports JPEG/PNG/BMP, animated GIF, PDF pages, MP4 sampled frames.
    """

    def _fit_rgba(self, img_rgba, W, H, fit):
        """Resize/crop image to (W,H) keeping RGBA (alpha intact)."""
        if fit == "contain":
            img_rgba.thumbnail((W,H), Image.LANCZOS)
            comp = Image.new("RGBA",(W,H),(0,0,0,0))
            comp.paste(img_rgba,((W-img_rgba.width)//2,(H-img_rgba.height)//2), img_rgba)
            return comp
        elif fit == "stretch":
            return img_rgba.resize((W,H), Image.LANCZOS).convert("RGBA")
        else:  # cover
            ratio = max(W/img_rgba.width, H/img_rgba.height)
            img_rgba = img_rgba.resize((int(img_rgba.width*ratio),int(img_rgba.height*ratio)), Image.LANCZOS)
            x0=(img_rgba.width-W)//2; y0=(img_rgba.height-H)//2
            return img_rgba.crop((x0,y0,x0+W,y0+H)).convert("RGBA")

    def _comp_on_bg(self, img_rgba, W, H):
        """Composite RGBA image onto the real screen background region (_bg_pil).
        Transparent pixels reveal the actual display content beneath this panel.
        This is the same technique used by TransparentElemPW."""
        p = self.pc
        bg_pil = getattr(self.dsp, "_bg_pil", None)
        if bg_pil:
            x0 = max(0, p.get("x",0)); y0 = max(0, p.get("y",0))
            region = bg_pil.crop((x0, y0, x0+W, y0+H)).convert("RGBA")
        else:
            try:
                bgc = self.dsp.cfg.d["display"].get("bg_color", BG).lstrip("#")
                rgb = tuple(int(bgc[i:i+2],16) for i in (0,2,4))
            except: rgb = (7,7,20)
            region = Image.new("RGBA",(W,H), rgb+(255,))
        # Alpha-composite: image pixels on top, transparent pixels show background
        region.paste(img_rgba, (0,0), img_rgba)
        return ImageTk.PhotoImage(region.convert("RGB"))

    def build(self):
        p = self.pc
        W = p.get("width",400); H = p.get("height",300)
        self._W = W; self._H = H
        self._imgs = []; self._img_meta = []
        self._cur = 0; self._last = 0.0
        self._gif_mode = False; self._gif_frame_idx = 0
        self._gif_delays = []; self._gif_last = 0.0
        self._interval = max(1, p.get("interval",5))
        self._img_id = self.create_image(0, 0, anchor="nw", tags="content")
        if not PIL_AVAILABLE: return
        fit = p.get("fit_mode","contain")
        raw_images = p.get("images",[])
        for entry in raw_images:
            if isinstance(entry, str):
                path = entry; meta = {}
            elif isinstance(entry, dict):
                path = entry.get("path",""); meta = entry
            else:
                continue
            if not path or not os.path.exists(path): continue
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext == ".gif":
                    gif = Image.open(path)
                    nframes = getattr(gif,"n_frames",1)
                    if nframes > 1 and len(raw_images) == 1:
                        self._gif_mode = True
                        while True:
                            try:
                                dur = gif.info.get("duration",100)
                                self._gif_delays.append(max(50,int(dur)))
                                fitted = self._fit_rgba(gif.convert("RGBA"),W,H,fit)
                                self._imgs.append(self._comp_on_bg(fitted,W,H))
                                self._img_meta.append(meta)
                                gif.seek(gif.tell()+1)
                            except EOFError: break
                    else:
                        fitted = self._fit_rgba(gif.convert("RGBA"),W,H,fit)
                        self._imgs.append(self._comp_on_bg(fitted,W,H))
                        self._img_meta.append(meta)
                elif ext == ".pdf":
                    try:
                        from pdf2image import convert_from_path
                        for page in convert_from_path(path, dpi=150):
                            fitted = self._fit_rgba(page.convert("RGBA"),W,H,fit)
                            self._imgs.append(self._comp_on_bg(fitted,W,H))
                            self._img_meta.append(meta)
                    except Exception: pass
                elif ext == ".mp4":
                    try:
                        import cv2
                        cap = cv2.VideoCapture(path)
                        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        step = max(1,total//30); idx = 0
                        while True:
                            cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
                            ret,frame = cap.read()
                            if not ret: break
                            rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                            fitted = self._fit_rgba(Image.fromarray(rgb).convert("RGBA"),W,H,fit)
                            self._imgs.append(self._comp_on_bg(fitted,W,H))
                            self._img_meta.append(meta)
                            idx += step
                            if len(self._imgs) >= 30: break
                        cap.release()
                    except Exception: pass
                else:
                    fitted = self._fit_rgba(Image.open(path).convert("RGBA"),W,H,fit)
                    self._imgs.append(self._comp_on_bg(fitted,W,H))
                    self._img_meta.append(meta)
            except: pass
        if self._imgs:
            self.itemconfig(self._img_id, image=self._imgs[0])

    def _active_indices(self):
        now=datetime.now(); today=now.date()
        cur_t=now.hour*60+now.minute; active=[]
        for i,meta in enumerate(self._img_meta):
            if not meta: active.append(i); continue
            df=meta.get("date_from",""); dt=meta.get("date_to","")
            if df:
                try:
                    from datetime import date as _d
                    if today<_d.fromisoformat(df): continue
                except: pass
            if dt:
                try:
                    from datetime import date as _d
                    if today>_d.fromisoformat(dt): continue
                except: pass
            wds=meta.get("weekdays",[])
            if wds and today.weekday() not in wds: continue
            tf=meta.get("time_from",""); tt=meta.get("time_to","")
            if tf:
                try:
                    hh,mm=map(int,tf.split(":")); 
                    if cur_t<hh*60+mm: continue
                except: pass
            if tt:
                try:
                    hh,mm=map(int,tt.split(":"))
                    if cur_t>hh*60+mm: continue
                except: pass
            active.append(i)
        return active

    def tick(self):
        now = time.time()
        if self._gif_mode and self._imgs:
            delay_sec = (self._gif_delays[self._gif_frame_idx] if self._gif_delays else 100)/1000.0
            if now-self._gif_last >= delay_sec:
                self._gif_last = now
                self._gif_frame_idx = (self._gif_frame_idx+1) % len(self._imgs)
                try: self.itemconfig(self._img_id, image=self._imgs[self._gif_frame_idx])
                except: pass
        else:
            if now-self._last >= self._interval:
                active = self._active_indices()
                if active:
                    self._cur = (self._cur+1) % len(active)
                    try: self.itemconfig(self._img_id, image=self._imgs[active[self._cur]])
                    except: pass
                self._last = now


class TransparentElemPW(CanvasBackedPanel):
    """Element/shape with true per-pixel transparency: composites RGBA image onto real background."""
    def build(self):
        p = self.pc
        W = p.get("width",200); H = p.get("height",200)
        img_path = p.get("image_path","")
        if img_path and os.path.exists(img_path) and PIL_AVAILABLE:
            try:
                img = Image.open(img_path).convert("RGBA")
                fit = p.get("fit_mode","contain")
                if fit == "contain":
                    img.thumbnail((W,H), Image.LANCZOS)
                elif fit == "stretch":
                    img = img.resize((W,H), Image.LANCZOS)
                else:
                    ratio = max(W/img.width, H/img.height)
                    img = img.resize((int(img.width*ratio),int(img.height*ratio)), Image.LANCZOS)
                ox=(W-img.width)//2; oy=(H-img.height)//2
                # Composite element onto the real captured background
                bg_pil = getattr(self.dsp, "_bg_pil", None)
                if bg_pil:
                    x0=max(0,p.get("x",0)); y0=max(0,p.get("y",0))
                    region = bg_pil.crop((x0,y0,x0+W,y0+H)).convert("RGBA")
                else:
                    try:
                        bgc=self.dsp.cfg.d["display"].get("bg_color",BG).lstrip("#")
                        rgb=tuple(int(bgc[i:i+2],16) for i in (0,2,4))
                    except: rgb=(7,7,20)
                    region = Image.new("RGBA",(W,H),rgb+(255,))
                region.paste(img,(ox,oy),img)
                self._photo = ImageTk.PhotoImage(region.convert("RGB"))
                self.create_image(0, 0, anchor="nw", image=self._photo, tags="content")
                return
            except: pass
        self.create_text(W//2, H//2, text="🎨\nאלמנט עיצובי",
            font=("Arial",12), fill=TEXT2, anchor="center", tags="content")

    def tick(self): pass


# ── ממשק ניהול ──────────────────────────────────────────────────────────────
class ManagerWin:
    def __init__(self,app):
        self.app=app; self.cfg=app.cfg
        self.win=tk.Toplevel(app.display.root)
        self.win.title(f"{APP} — ממשק ניהול")
        self.win.configure(bg=M_BG)
        self.win.attributes("-topmost",True)
        self.win.protocol("WM_DELETE_WINDOW",self._close)
        # Size and center
        W=app.display.W; H=app.display.H
        mw=min(1280,W-20); mh=min(860,H-20)
        x=(W-mw)//2; y=max(0,(H-mh)//2)
        self.win.geometry(f"{mw}x{mh}+{x}+{y}")
        # Fix 6: pull display out of topmost so manager stays visible
        app.display.root.attributes("-topmost",False)
        self.win.lift()
        self._setup_style()
        self._build()

    def _close(self):
        self.app.display.root.attributes("-topmost",True)
        self.app.manager=None; self.win.destroy()

    def _setup_style(self):
        s=ttk.Style(self.win); s.theme_use("clam")
        s.configure("TNotebook",background=M_BG2,borderwidth=0,tabmargins=[0,6,0,0])
        s.configure("TNotebook.Tab",background=M_BG3,foreground=M_TEXT,
                    padding=[20,10],font=("Arial",11,"bold"))
        s.map("TNotebook.Tab",
              background=[("selected",M_BG),("active",M_BTN)],
              foreground=[("selected",M_BLUE),("active",M_TEXT)])
        s.configure("Treeview",background=M_CARD,foreground=M_TEXT,
                    fieldbackground=M_CARD,rowheight=30,font=("Arial",11),borderwidth=0)
        s.map("Treeview",background=[("selected",M_BLUE)],foreground=[("selected","#fff")])
        s.configure("Treeview.Heading",background=M_BG2,foreground=M_TEXT,
                    font=("Arial",10,"bold"),relief="flat",padding=6)
        s.configure("Vertical.TScrollbar",background=M_BTN,troughcolor=M_BG2,
                    borderwidth=0,arrowcolor=M_TEXT2)

    def _build(self):
        # ── Header ──
        hdr=tk.Frame(self.win,bg=M_HDR,height=64); hdr.pack(fill="x"); hdr.pack_propagate(False)
        # Logo area
        logo=tk.Label(hdr,text="▣  "+APP,font=("Arial",16,"bold"),fg="#ffffff",bg=M_HDR)
        logo.pack(side="right",padx=20,pady=12)
        tk.Label(hdr,text=f"גרסה {VER}  |  F8 לסגירה",
            font=("Arial",9),fg="#aabbff",bg=M_HDR).pack(side="right",padx=4)
        # Close btn
        close_btn=tk.Button(hdr,text="✕ סגור ניהול",
            font=("Arial",11),fg="#ddeeff",bg="#2a3d8a",bd=0,
            activebackground="#cc2a2a",activeforeground="#fff",
            cursor="hand2",padx=16,pady=8,command=self._close)
        close_btn.pack(side="left",padx=12,pady=10)
        self._hover_btn(close_btn,"#2a3d8a","#cc2a2a")
        # Exit application button
        exit_btn=tk.Button(hdr,text="⏻  יציאה",
            font=("Arial",11),fg="#ffaaaa",bg="#2a3d8a",bd=0,
            activebackground="#700000",activeforeground="#fff",
            cursor="hand2",padx=12,pady=8,command=self._exit_app)
        exit_btn.pack(side="left",padx=4,pady=10)
        self._hover_btn(exit_btn,"#2a3d8a","#700000")
        # Refresh btn
        ref_btn=tk.Button(hdr,text="↻ רענן",
            font=("Arial",11),fg="#aaffcc",bg="#2a3d8a",bd=0,
            activebackground="#1a7a4a",activeforeground="#fff",
            cursor="hand2",padx=12,pady=8,
            command=lambda: self.app.refresh_display())
        ref_btn.pack(side="left",padx=4,pady=10)
        self._hover_btn(ref_btn,"#2a3d8a","#1a7a4a")
        # Fullscreen announcement button
        ann_btn=tk.Button(hdr,text="📢  הודעת מסך מלא",
            font=("Arial",11),fg="#fff",bg="#8a4a00",bd=0,
            activebackground=GOLD,activeforeground="#000",
            cursor="hand2",padx=14,pady=8,
            command=self._open_fullscreen_announce)
        ann_btn.pack(side="left",padx=4,pady=10)
        self._hover_btn(ann_btn,"#8a4a00",GOLD)
        # Status bar
        self.status_var=tk.StringVar(value="מוכן")
        tk.Label(hdr,textvariable=self.status_var,font=("Arial",10),
            fg="#44ffaa",bg=M_HDR).pack(side="left",padx=12)

        # ── Tabs ──
        self.nb=ttk.Notebook(self.win)
        self.nb.pack(fill="both",expand=True)
        self._t_panels  =tk.Frame(self.nb,bg=M_BG)
        self._t_location=tk.Frame(self.nb,bg=M_BG)
        self._t_security=tk.Frame(self.nb,bg=M_BG)
        self._t_remind  =tk.Frame(self.nb,bg=M_BG)
        self._t_about   =tk.Frame(self.nb,bg=M_BG)
        self.nb.add(self._t_panels,   text="   לוחות   ")
        self.nb.add(self._t_location, text=" הגדרת מיקום ")
        self.nb.add(self._t_security, text="   אבטחה   ")
        self.nb.add(self._t_remind,   text="  תזכורות  ")
        self.nb.add(self._t_about,    text="  אודות  ")
        self._build_panels_tab()
        self._build_location_tab()
        self._build_security_tab()
        self._build_reminders_tab()
        self._build_about_tab()

    # ── Tab: לוחות ──────────────────────────────────────────────────────────
    def _build_panels_tab(self):
        f=self._t_panels

        # Left sidebar
        left=tk.Frame(f,bg=M_BG2,width=300); left.pack(side="left",fill="y"); left.pack_propagate(False)

        tk.Label(left,text="לוחות פעילים",
            font=("Arial",13,"bold"),fg=M_TEXT,bg=M_BG2).pack(pady=(14,2),padx=12,anchor="e")

        # Add panel buttons
        tk.Label(left,text="הוסף לוח:",font=("Arial",10),fg=M_TEXT2,bg=M_BG2).pack(anchor="e",padx=12)
        btn_grid=tk.Frame(left,bg=M_BG2); btn_grid.pack(fill="x",padx=8,pady=4)
        for pt,lbl in PANEL_NAMES.items():
            if pt=="background": continue  # singleton — not addable
            b=tk.Button(btn_grid,text="+ "+lbl,font=("Arial",9,"bold"),
                fg=M_TEXT,bg=M_BTN,bd=0,activebackground=BLUE,activeforeground="#fff",
                cursor="hand2",padx=8,pady=5,anchor="e",justify="right",
                command=lambda t=pt: self._add_panel(t))
            b.pack(fill="x",pady=2)
            self._hover_btn(b,BTN,BLUE)

        tk.Frame(left,bg=M_SEP,height=1).pack(fill="x",padx=6,pady=6)

        # Export / Import layout
        io_frame=tk.Frame(left,bg=M_BG2); io_frame.pack(fill="x",padx=8,pady=2)
        exp_btn=tk.Button(io_frame,text="📤 יצוא פריסה",font=("Arial",9,"bold"),
            fg=M_TEXT,bg="#1a3a1a",bd=0,activebackground=GREEN,activeforeground="#fff",
            cursor="hand2",padx=8,pady=5,command=self._export_layout)
        exp_btn.pack(fill="x",pady=2); self._hover_btn(exp_btn,"#1a3a1a",GREEN)
        imp_btn=tk.Button(io_frame,text="📥 יבוא פריסה",font=("Arial",9,"bold"),
            fg=M_TEXT,bg="#1a2a3a",bd=0,activebackground=LBLUE,activeforeground="#fff",
            cursor="hand2",padx=8,pady=5,command=self._import_layout)
        imp_btn.pack(fill="x",pady=2); self._hover_btn(imp_btn,"#1a2a3a",LBLUE)

        tk.Frame(left,bg=M_SEP,height=1).pack(fill="x",padx=6,pady=4)

        # Panel tree
        tree_wrap=tk.Frame(left,bg=M_BG2); tree_wrap.pack(fill="both",expand=True,padx=5)
        vsb=ttk.Scrollbar(tree_wrap,orient="vertical"); vsb.pack(side="left",fill="y")
        self.tree=ttk.Treeview(tree_wrap,columns=("name","layer","status"),show="headings",
                                yscrollcommand=vsb.set,selectmode="browse")
        self.tree.heading("name",text="לוח"); self.tree.heading("layer",text="שכ׳")
        self.tree.heading("status",text="מצב")
        self.tree.column("name",width=160,anchor="e")
        self.tree.column("layer",width=34,anchor="center")
        self.tree.column("status",width=34,anchor="center")
        self.tree.pack(side="right",fill="both",expand=True)
        vsb.configure(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>",self._on_sel)

        del_btn=tk.Button(left,text="🗑  מחק לוח נבחר",
            font=("Arial",10),fg=RED,bg=M_BTN,bd=0,
            activebackground=RED,activeforeground="#fff",
            cursor="hand2",pady=7,command=self._del_panel)
        del_btn.pack(fill="x",padx=8,pady=(4,10))
        self._hover_btn(del_btn,BTN,RED)

        # Right: editor area
        self.editor_area=tk.Frame(f,bg=M_BG)
        self.editor_area.pack(side="right",fill="both",expand=True)
        self._placeholder()
        self._refresh_tree()

    def _hover_btn(self,btn,normal,hover):
        btn.bind("<Enter>",lambda e,b=btn,h=hover: b.configure(bg=h))
        btn.bind("<Leave>",lambda e,b=btn,n=normal: b.configure(bg=n))

    def _placeholder(self):
        for w in self.editor_area.winfo_children(): w.destroy()
        tk.Label(self.editor_area,
            text="← בחר לוח מהרשימה לעריכה",
            font=("Arial",14),fg=M_TEXT2,bg=M_BG).place(relx=0.5,rely=0.5,anchor="center")

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        # Background panel (singleton, always first)
        disp=self.cfg.d["display"]
        self.tree.insert("","end",iid="bg_panel",values=("רקע ראשי ★","—","✓"))
        # Regular panels
        for p in self.cfg.d.get("panels",[]):
            stat="✓" if p.get("enabled",True) else "✗"
            name=PANEL_NAMES.get(p.get("type",""),"?")
            pid=p.get("id","?"); lyr=p.get("layer",1)
            self.tree.insert("","end",iid=str(pid),values=(f"{name} #{pid}",lyr,stat))

    def _on_sel(self,e):
        sel=self.tree.selection()
        if not sel: return
        iid=sel[0]
        if iid=="bg_panel":
            self._open_bg_editor()
        else:
            pid=int(iid)
            pc=self.cfg.get_panel(pid)
            if pc: self._open_editor(pc)

    def _open_bg_editor(self):
        for w in self.editor_area.winfo_children(): w.destroy()
        BackgroundEditor(self.editor_area,self.cfg.d["display"],self).pack(fill="both",expand=True)

    def _add_panel(self,pt):
        p=self.cfg.add_panel(pt)
        self._refresh_tree()
        self.tree.selection_set(str(p["id"]))
        self._open_editor(p)
        self.app.refresh_display()
        self.status_var.set(f"לוח {PANEL_NAMES[pt]} נוסף בהצלחה")

    def _del_panel(self):
        sel=self.tree.selection()
        if not sel: return
        if sel[0]=="bg_panel":
            messagebox.showinfo("מידע","לוח הרקע הראשי לא ניתן למחיקה",parent=self.win); return
        pid=int(sel[0])
        if messagebox.askyesno("מחיקה","האם למחוק את הלוח?",parent=self.win):
            self.cfg.del_panel(pid)
            self._refresh_tree(); self._placeholder()
            self.app.refresh_display()

    def _open_editor(self,pc):
        for w in self.editor_area.winfo_children(): w.destroy()
        PanelEditor(self.editor_area,pc,self).pack(fill="both",expand=True)

    # ── Tab: הגדרת מיקום ────────────────────────────────────────────────────
    def _build_location_tab(self):
        f=self._t_location
        cv=tk.Canvas(f,bg=M_BG,highlightthickness=0)
        sb=ttk.Scrollbar(f,orient="vertical",command=cv.yview)
        cv.pack(side="left",fill="both",expand=True)
        sb.pack(side="right",fill="y")
        cv.configure(yscrollcommand=sb.set)
        inner=tk.Frame(cv,bg=M_BG)
        wid=cv.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(wid,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(-1*(1 if e.delta>0 else -1),"units"))
        self._build_location_content(inner)

    def _build_location_content(self,f):
        def section(title):
            fr=tk.Frame(f,bg=M_BG); fr.pack(fill="x",padx=25,pady=6)
            tk.Label(fr,text=title,font=("Arial",13,"bold"),fg=LBLUE,bg=M_BG).pack(side="right",pady=(10,3))
            tk.Frame(fr,bg=M_SEP,height=1).pack(fill="x",pady=2)
            c=tk.Frame(fr,bg=M_BG); c.pack(fill="x"); return c

        # ── מיקום ──
        ls=section("מיקום (לחישוב זמני הלכה)")
        loc=self.cfg.d["location"]
        r_city=tk.Frame(ls,bg=M_BG); r_city.pack(fill="x",padx=8,pady=5)
        tk.Label(r_city,text="בחר עיר:",font=("Arial",11),fg=M_TEXT,bg=M_BG,
                 width=22,anchor="e").pack(side="right",padx=(0,8))
        CITIES={
            "ירושלים":(31.7683,35.2137,754,"Asia/Jerusalem"),
            "תל אביב":(32.0853,34.7818,5,"Asia/Jerusalem"),
            "חיפה":(32.7940,34.9896,146,"Asia/Jerusalem"),
            "בני ברק":(32.0814,34.8340,28,"Asia/Jerusalem"),
            "ביתר עילית":(31.6960,35.1190,680,"Asia/Jerusalem"),
            "ביתר":(31.7042,35.1216,700,"Asia/Jerusalem"),
            "מודיעין עילית":(31.9318,35.0426,310,"Asia/Jerusalem"),
            "קרית ספר":(31.9318,35.0426,310,"Asia/Jerusalem"),
            "אלעד":(32.0525,34.9514,120,"Asia/Jerusalem"),
            "אשדוד":(31.8044,34.6553,30,"Asia/Jerusalem"),
            "אשקלון":(31.6688,34.5742,40,"Asia/Jerusalem"),
            "באר שבע":(31.2524,34.7913,270,"Asia/Jerusalem"),
            "נתניה":(32.3215,34.8532,15,"Asia/Jerusalem"),
            "פתח תקווה":(32.0841,34.8878,45,"Asia/Jerusalem"),
            "ראשון לציון":(31.9730,34.7925,25,"Asia/Jerusalem"),
            "רמת גן":(32.0681,34.8236,45,"Asia/Jerusalem"),
            "רחובות":(31.8928,34.8113,50,"Asia/Jerusalem"),
            "הרצליה":(32.1663,34.8432,15,"Asia/Jerusalem"),
            "כפר סבא":(32.1752,34.9058,60,"Asia/Jerusalem"),
            "מודיעין":(31.8976,35.0097,280,"Asia/Jerusalem"),
            "בית שמש":(31.7487,34.9887,270,"Asia/Jerusalem"),
            "ראש העין":(32.0959,34.9563,85,"Asia/Jerusalem"),
            "עפולה":(32.6052,35.2888,70,"Asia/Jerusalem"),
            "נצרת":(32.7021,35.2978,355,"Asia/Jerusalem"),
            "נהריה":(33.0039,35.0975,10,"Asia/Jerusalem"),
            "עכו":(32.9278,35.0828,5,"Asia/Jerusalem"),
            "טבריה":(32.7921,35.5305,-210,"Asia/Jerusalem"),
            "צפת":(32.9646,35.4956,900,"Asia/Jerusalem"),
            "קריית שמונה":(33.2089,35.5706,140,"Asia/Jerusalem"),
            "בית שאן":(32.4955,35.4994,-120,"Asia/Jerusalem"),
            "אילת":(29.5577,34.9519,15,"Asia/Jerusalem"),
            "ערד":(31.2587,35.2124,620,"Asia/Jerusalem"),
            "מצפה רמון":(30.6100,34.8017,860,"Asia/Jerusalem"),
            "דימונה":(31.0691,35.0327,590,"Asia/Jerusalem"),
            "קרית גת":(31.6100,34.7642,110,"Asia/Jerusalem"),
            "לוד":(31.9516,34.8950,70,"Asia/Jerusalem"),
            "רמלה":(31.9280,34.8680,60,"Asia/Jerusalem"),
            "חולון":(32.0114,34.7744,15,"Asia/Jerusalem"),
            "בת ים":(32.0167,34.7500,10,"Asia/Jerusalem"),
            "אור יהודה":(32.0258,34.8572,25,"Asia/Jerusalem"),
            "גבעתיים":(32.0711,34.8126,35,"Asia/Jerusalem"),
            "קרית ביאליק":(32.8302,35.0834,25,"Asia/Jerusalem"),
            "קרית אתא":(32.8100,35.1100,30,"Asia/Jerusalem"),
            "גדרה":(31.8120,34.7776,75,"Asia/Jerusalem"),
            "יבנה":(31.8674,34.7432,45,"Asia/Jerusalem"),
            "לוס אנג׳לס":(34.0522,-118.2437,93,"America/Los_Angeles"),
            "ניו יורק":(40.7128,-74.0060,10,"America/New_York"),
            "לונדון":(51.5074,-0.1278,11,"Europe/London"),
            "אמסטרדם":(52.3676,4.9041,5,"Europe/Amsterdam"),
            "אנטוורפן":(51.2194,4.4025,10,"Europe/Brussels"),
            "ברסל":(50.8503,4.3517,56,"Europe/Brussels"),
            "ציריך":(47.3769,8.5417,408,"Europe/Zurich"),
            "ברלין":(52.5200,13.4050,34,"Europe/Berlin"),
            "פרנקפורט":(50.1109,8.6821,109,"Europe/Berlin"),
            "מנצ׳סטר":(53.4808,-2.2426,38,"Europe/London"),
            "יוהנסבורג":(-26.2041,28.0473,1753,"Africa/Johannesburg"),
            "מלבורן":(-37.8136,144.9631,25,"Australia/Melbourne"),
            "סידני":(-33.8688,151.2093,25,"Australia/Sydney"),
        }
        city_cb=ttk.Combobox(r_city,values=sorted(CITIES.keys()),width=18,state="readonly",
                              font=("Arial",11)); city_cb.pack(side="right",padx=3)
        self._loc_vars={}
        fields=[("שם מיקום:","city",20),("קו רוחב (Lat):","lat",10),
                ("קו אורך (Lng):","lng",10),("גובה (מטר):","elev",8),("אזור זמן:","tz",20)]
        for label,key,w in fields:
            r2=tk.Frame(ls,bg=M_BG); r2.pack(fill="x",padx=8,pady=4)
            tk.Label(r2,text=label,font=("Arial",10),fg=M_TEXT,bg=M_BG,
                     width=22,anchor="e").pack(side="right",padx=(0,8))
            v=tk.StringVar(value=str(loc.get(key,"")))
            self._loc_vars[key]=v
            tk.Entry(r2,textvariable=v,width=w,
                bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
                font=("Arial",10)).pack(side="right")
        def set_city(e):
            c=city_cb.get()
            if c in CITIES:
                lt,ln,el,tz=CITIES[c]
                self._loc_vars["city"].set(c)
                self._loc_vars["lat"].set(str(lt))
                self._loc_vars["lng"].set(str(ln))
                self._loc_vars["elev"].set(str(el))
                self._loc_vars["tz"].set(tz)
        city_cb.bind("<<ComboboxSelected>>",set_city)

        # Save + export/import buttons
        tk.Frame(f,bg=M_SEP,height=1).pack(fill="x",padx=25,pady=12)
        btn_row=tk.Frame(f,bg=M_BG); btn_row.pack(pady=6)
        save_btn=tk.Button(btn_row,text="💾  שמור הגדרות",
            font=("Arial",12,"bold"),fg="#ffffff",bg=BLUE,bd=0,
            cursor="hand2",padx=24,pady=9,command=self._save_location)
        save_btn.pack(side="right",padx=8); self._hover_btn(save_btn,BLUE,LBLUE)
        tk.Button(btn_row,text="📤 יצוא",font=("Arial",10),fg=M_TEXT,bg=M_BTN,bd=0,
            cursor="hand2",padx=12,pady=9,command=self._export_settings
        ).pack(side="right",padx=4)
        tk.Button(btn_row,text="📥 יבוא",font=("Arial",10),fg=M_TEXT,bg=M_BTN,bd=0,
            cursor="hand2",padx=12,pady=9,command=self._import_settings
        ).pack(side="right",padx=4)

    def _save_location(self):
        for key,var in self._loc_vars.items():
            val=var.get().strip()
            if key in ("lat","lng","elev"):
                try: self.cfg.d["location"][key]=float(val)
                except: pass
            else: self.cfg.d["location"][key]=val
        self.cfg.save()
        self.app.refresh_display()
        messagebox.showinfo("הצלחה","הגדרות המיקום נשמרו!",parent=self.win)

    # ── Tab: אבטחה ──────────────────────────────────────────────────────────
    def _build_security_tab(self):
        f=self._t_security
        body=tk.Frame(f,bg=M_BG); body.place(relx=0.5,rely=0.4,anchor="center")
        tk.Label(body,text="🔐  הגדרות אבטחה",
            font=("Arial",16,"bold"),fg=GOLD,bg=M_BG).pack(pady=(0,16))
        tk.Frame(body,bg=M_SEP,height=1,width=340).pack(pady=4)

        has=self.cfg.has_pw()
        self._pw_status=tk.Label(body,
            text="✓ סיסמא מוגדרת" if has else "✗ אין סיסמא",
            font=("Arial",13,"bold"),fg=GREEN if has else TEXT2,bg=M_BG)
        self._pw_status.pack(pady=12)

        def set_pw():
            pw=simpledialog.askstring("סיסמא חדשה","הזן סיסמא חדשה:",show="*",parent=self.win)
            if pw is None: return
            if pw:
                pw2=simpledialog.askstring("אימות","הזן שוב את הסיסמא:",show="*",parent=self.win)
                if pw!=pw2:
                    messagebox.showerror("שגיאה","הסיסמאות אינן תואמות",parent=self.win); return
            self.cfg.set_pw(pw)
            has2=self.cfg.has_pw()
            self._pw_status.configure(
                text="✓ סיסמא מוגדרת" if has2 else "✗ אין סיסמא",
                fg=GREEN if has2 else TEXT2)
            messagebox.showinfo("הצלחה","הסיסמא עודכנה",parent=self.win)

        def del_pw():
            if self.cfg.has_pw():
                pw=simpledialog.askstring("אימות","הזן את הסיסמא הנוכחית:",show="*",parent=self.win)
                if not self.cfg.check_pw(pw or ""):
                    messagebox.showerror("שגיאה","סיסמא שגויה",parent=self.win); return
            self.cfg.set_pw("")
            self._pw_status.configure(text="✗ אין סיסמא",fg=M_TEXT2)
            messagebox.showinfo("הצלחה","הסיסמא נמחקה",parent=self.win)

        pw_row=tk.Frame(body,bg=M_BG); pw_row.pack(pady=8)
        tk.Button(pw_row,text="שנה / הגדר סיסמא",font=("Arial",11),fg=M_TEXT,bg=BLUE,
            bd=0,cursor="hand2",padx=14,pady=8,command=set_pw).pack(side="right",padx=6)
        tk.Button(pw_row,text="מחק סיסמא",font=("Arial",11),fg=RED,bg=M_BTN,
            bd=0,cursor="hand2",padx=14,pady=8,command=del_pw).pack(side="right",padx=6)

        tk.Frame(body,bg=M_SEP,height=1,width=340).pack(pady=16)
        tk.Label(body,text="הסיסמא נדרשת לפתיחת ממשק הניהול (F8).",
            font=("Arial",10),fg=M_TEXT2,bg=M_BG).pack()

    def _export_layout(self):
        path=filedialog.asksaveasfilename(
            parent=self.win,title="יצוא פריסה",
            defaultextension=".dbzip",
            filetypes=[("Digital Bulletin Layout","*.dbzip"),("ZIP","*.zip")])
        if not path: return
        try:
            n=self.cfg.export_layout_zip(path)
            messagebox.showinfo("יצוא הושלם",
                f"הפריסה יוצאה בהצלחה\nקבצי עיצוב שיוצאו: {n}",parent=self.win)
        except Exception as e:
            messagebox.showerror("שגיאה בייצוא",str(e),parent=self.win)

    def _import_layout(self):
        path=filedialog.askopenfilename(
            parent=self.win,title="יבוא פריסה",
            filetypes=[("Digital Bulletin Layout","*.dbzip *.zip")])
        if not path: return
        if not messagebox.askyesno("אישור יבוא",
            "היבוא ידרוס את הגדרות הפריסה הנוכחיות.\nהאם להמשיך?",parent=self.win): return
        try:
            self.cfg.import_layout_zip(path)
            self.app.refresh_display()
            self._refresh_tree()
            messagebox.showinfo("יבוא הושלם","הפריסה יובאה בהצלחה!",parent=self.win)
        except Exception as e:
            messagebox.showerror("שגיאה בייבוא",str(e),parent=self.win)

    def _export_settings(self):
        path=filedialog.asksaveasfilename(
            parent=self.win,title="יצוא הגדרות מיקום",
            defaultextension=".json",
            filetypes=[("JSON","*.json")])
        if not path: return
        try:
            self.cfg.export_settings(path)
            messagebox.showinfo("הצלחה","הגדרות המיקום יוצאו בהצלחה",parent=self.win)
        except Exception as e:
            messagebox.showerror("שגיאה",str(e),parent=self.win)

    def _import_settings(self):
        path=filedialog.askopenfilename(
            parent=self.win,title="יבוא הגדרות מיקום",
            filetypes=[("JSON","*.json")])
        if not path: return
        try:
            self.cfg.import_settings(path)
            self.app.refresh_display()
            messagebox.showinfo("הצלחה","הגדרות המיקום יובאו בהצלחה",parent=self.win)
        except Exception as e:
            messagebox.showerror("שגיאה",str(e),parent=self.win)

    def _open_fullscreen_announce(self):
        """Dialog to compose and show a full-screen announcement."""
        dlg=tk.Toplevel(self.win)
        dlg.title("הודעת מסך מלא")
        dlg.configure(bg=M_BG)
        dlg.resizable(False,False)
        dlg.geometry("560x440")
        dlg.attributes("-topmost",True)
        dlg.grab_set()

        tk.Label(dlg,text="📢  הודעת מסך מלא",
            font=("Arial",15,"bold"),fg=GOLD,bg=M_BG).pack(pady=(18,8))
        tk.Label(dlg,text="כתוב כאן את ההודעה שתוצג על המסך:",
            font=("Arial",11),fg=M_TEXT2,bg=M_BG).pack(anchor="e",padx=20)

        txt=tk.Text(dlg,height=6,font=("Arial",14),bg=M_INP,fg=M_TEXT,
            insertbackground=M_TEXT,bd=1,relief="solid",
            wrap="word",padx=10,pady=8)
        txt.pack(fill="x",padx=20,pady=6)

        opt=tk.Frame(dlg,bg=M_BG); opt.pack(fill="x",padx=20,pady=4)
        tk.Label(opt,text="גודל גופן:",font=("Arial",11),fg=M_TEXT,bg=M_BG).pack(side="right",padx=(0,6))
        fs_v=tk.StringVar(value="48")
        tk.Spinbox(opt,from_=24,to=120,textvariable=fs_v,width=5,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,
            font=("Arial",11),justify="center").pack(side="right",padx=2)
        tk.Label(opt,text="סגירה אוטומטית (שניות, 0=ידנית):",
            font=("Arial",11),fg=M_TEXT,bg=M_BG).pack(side="right",padx=(14,6))
        dur_v=tk.StringVar(value="0")
        tk.Spinbox(opt,from_=0,to=300,textvariable=dur_v,width=5,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,
            font=("Arial",11),justify="center").pack(side="right",padx=2)

        col=tk.Frame(dlg,bg=M_BG); col.pack(fill="x",padx=20,pady=4)
        fg_v=tk.StringVar(value=GOLD); bg_v=tk.StringVar(value="#0a0000")
        for lbl,var,side in [("צבע טקסט:",fg_v,"right"),("צבע רקע:",bg_v,"right")]:
            tk.Label(col,text=lbl,font=("Arial",11),fg=M_TEXT,bg=M_BG).pack(side=side,padx=(0,4))
            prev=tk.Frame(col,width=32,height=22,bg=var.get(),cursor="hand2",bd=1,relief="solid")
            prev.pack(side=side,padx=4)
            def pick(v=var,p=prev):
                c=colorchooser.askcolor(v.get(),parent=dlg)
                if c and c[1]: v.set(c[1]); p.configure(bg=c[1])
            prev.bind("<Button-1>",lambda e,p=pick: p())

        tk.Frame(dlg,bg=M_SEP,height=1).pack(fill="x",padx=20,pady=10)

        def show():
            msg=txt.get("1.0","end-1c").strip()
            if not msg:
                messagebox.showwarning("שגיאה","יש לרשום טקסט להודעה",parent=dlg); return
            try: fs=int(fs_v.get())
            except: fs=48
            try: dur=int(dur_v.get())
            except: dur=0
            dlg.destroy()
            self.app.display.show_fullscreen_msg(msg,duration=dur,
                bg=bg_v.get(),fg=fg_v.get(),fontsize=fs)

        btn_row=tk.Frame(dlg,bg=M_BG); btn_row.pack(pady=6)
        show_btn=tk.Button(btn_row,text="📢  הצג עכשיו",
            font=("Arial",13,"bold"),fg="#fff",bg=GOLD,bd=0,
            cursor="hand2",padx=24,pady=9,command=show)
        show_btn.pack(side="left",padx=8)
        tk.Button(btn_row,text="ביטול",font=("Arial",11),fg=M_TEXT2,bg=M_BTN,bd=0,
            cursor="hand2",padx=16,pady=9,command=dlg.destroy).pack(side="left",padx=8)

    # ── Tab: תזכורות ────────────────────────────────────────────────────────
    # ── Tab: תזכורות ────────────────────────────────────────────────────────
    def _build_reminders_tab(self):
        f=self._t_remind
        # ── Left: list ──
        left=tk.Frame(f,bg=M_BG2,width=310); left.pack(side="left",fill="y"); left.pack_propagate(False)
        tk.Label(left,text="🔔  תזכורות",font=("Arial",13,"bold"),fg=M_BLUE,bg=M_BG2
                 ).pack(pady=(14,2),padx=10,anchor="e")
        tk.Label(left,text="תזכורות אישיות ולפי זמני הלכה",
            font=("Arial",9),fg=M_TEXT2,bg=M_BG2).pack(anchor="e",padx=10,pady=(0,6))
        list_fr=tk.Frame(left,bg=M_BG2); list_fr.pack(fill="both",expand=True,padx=5)
        vsb=ttk.Scrollbar(list_fr); vsb.pack(side="left",fill="y")
        self._rem_tree=ttk.Treeview(list_fr,columns=("type","text","when","st"),
                                     show="headings",yscrollcommand=vsb.set,selectmode="browse")
        self._rem_tree.heading("type",text=""); self._rem_tree.heading("text",text="הודעה")
        self._rem_tree.heading("when",text="מועד"); self._rem_tree.heading("st",text="")
        self._rem_tree.column("type",width=28,anchor="center")
        self._rem_tree.column("text",width=120,anchor="e")
        self._rem_tree.column("when",width=95,anchor="center")
        self._rem_tree.column("st",width=22,anchor="center")
        self._rem_tree.pack(side="right",fill="both",expand=True)
        vsb.configure(command=self._rem_tree.yview)
        for txt2,cmd2,col2 in [("🗑 מחק",self._del_reminder,M_RED),
                                ("↺ הפעל מחדש",self._reset_reminder,M_TEXT2)]:
            b=tk.Button(left,text=txt2,font=("Arial",10),fg=col2,bg=M_BTN,bd=0,
                cursor="hand2",pady=6,command=cmd2)
            b.pack(fill="x",padx=8,pady=2); self._hover_btn(b,M_BTN,M_BTN2)

        # ── Right: scrollable form ──
        right=tk.Frame(f,bg=M_BG); right.pack(side="right",fill="both",expand=True)
        rcv=tk.Canvas(right,bg=M_BG,highlightthickness=0)
        rsb=ttk.Scrollbar(right,orient="vertical",command=rcv.yview)
        rcv.pack(side="left",fill="both",expand=True); rsb.pack(side="right",fill="y")
        rcv.configure(yscrollcommand=rsb.set)
        inner=tk.Frame(rcv,bg=M_BG)
        rwid=rcv.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",lambda e: rcv.configure(scrollregion=rcv.bbox("all")))
        rcv.bind("<Configure>",lambda e: rcv.itemconfig(rwid,width=e.width))
        rcv.bind("<MouseWheel>",lambda e: rcv.yview_scroll(-1*(1 if e.delta>0 else -1),"units"))

        def rsec(title):
            fr=tk.Frame(inner,bg=M_BG); fr.pack(fill="x",padx=18,pady=(10,2))
            tk.Label(fr,text=title,font=("Arial",11,"bold"),fg=M_BLUE,bg=M_BG).pack(anchor="e")
            tk.Frame(fr,bg=M_SEP,height=1).pack(fill="x",pady=2)
            c=tk.Frame(fr,bg=M_BG); c.pack(fill="x"); return c
        def rlrow(parent,label,w=22):
            r=tk.Frame(parent,bg=M_BG); r.pack(fill="x",padx=8,pady=4)
            tk.Label(r,text=label,font=("Arial",10),fg=M_TEXT,bg=M_BG,
                     width=w,anchor="e").pack(side="right",padx=(0,8))
            return r

        tk.Label(inner,text="הוסף תזכורת",font=("Arial",13,"bold"),
            fg=M_BLUE,bg=M_BG).pack(pady=(16,4),padx=18,anchor="e")
        tk.Frame(inner,bg=M_SEP,height=1).pack(fill="x",padx=18,pady=2)

        # Type toggle
        s0=rsec("סוג תזכורת")
        self._rem_type_v=tk.StringVar(value="personal")
        type_row=tk.Frame(s0,bg=M_BG); type_row.pack(fill="x",padx=8,pady=4)
        for val,lbl in [("personal","📅  תזכורת אישית"),("zmanim","🕍  זמן הלכה")]:
            tk.Radiobutton(type_row,text=lbl,variable=self._rem_type_v,value=val,
                font=("Arial",11,"bold"),fg=M_TEXT,bg=M_BG,selectcolor=M_INP,
                activebackground=M_BG,command=self._rem_toggle_type).pack(side="right",padx=10)

        # Text
        s1=rsec("תוכן ההודעה")
        r_txt=rlrow(s1,"טקסט:")
        self._rem_text_v=tk.StringVar()
        tk.Entry(r_txt,textvariable=self._rem_text_v,width=30,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,
            bd=1,relief="solid",font=("Arial",12)).pack(side="right")

        # Personal date/time
        self._rem_personal_fr=rsec("מועד (תזכורת אישית)")
        now_dt=datetime.now()
        self._rem_date_v=tk.StringVar(value=now_dt.strftime("%Y-%m-%d"))
        self._rem_time_v=tk.StringVar(value=now_dt.strftime("%H:%M"))
        for lbl2,var2,w2 in [("תאריך YYYY-MM-DD:",self._rem_date_v,14),("שעה HH:MM:",self._rem_time_v,8)]:
            r2=rlrow(self._rem_personal_fr,lbl2)
            tk.Entry(r2,textvariable=var2,width=w2,bg=M_INP,fg=M_TEXT,
                insertbackground=M_TEXT,bd=1,relief="solid",font=("Arial",12)).pack(side="right")

        # Zmanim fields (hidden initially)
        self._rem_zmanim_fr=rsec("זמן הלכה")
        self._rem_zmanim_fr.master.pack_forget()

        r_zm=rlrow(self._rem_zmanim_fr,"זמן:")
        self._rem_zman_v=tk.StringVar(value="sunset")
        zm_cb=ttk.Combobox(r_zm,textvariable=self._rem_zman_v,
            values=list(ZMANIM_KEYS.keys()),width=16,state="readonly",font=("Arial",10))
        zm_cb.pack(side="right")
        self._rem_zman_lbl=tk.Label(r_zm,text=ZMANIM_KEYS.get("sunset",""),
            font=("Arial",10),fg=M_TEXT2,bg=M_BG)
        self._rem_zman_lbl.pack(side="right",padx=6)
        zm_cb.bind("<<ComboboxSelected>>",
            lambda e: self._rem_zman_lbl.configure(text=ZMANIM_KEYS.get(self._rem_zman_v.get(),"")))

        r_off=rlrow(self._rem_zmanim_fr,"דקות (שלילי=לפני):")
        self._rem_offset_v=tk.StringVar(value="-15")
        tk.Spinbox(r_off,from_=-120,to=120,textvariable=self._rem_offset_v,width=6,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,
            font=("Arial",11),justify="center").pack(side="right",padx=2)

        # Recurring
        s2=rsec("חזרה")
        r_rec=rlrow(s2,"חזרה:")
        self._rem_rec_v=tk.StringVar(value="daily")
        for val,lbl in [("none","חד פעמי"),("daily","יומי"),("weekly","שבועי")]:
            tk.Radiobutton(r_rec,text=lbl,variable=self._rem_rec_v,value=val,
                font=("Arial",10),fg=M_TEXT,bg=M_BG,selectcolor=M_INP,
                activebackground=M_BG).pack(side="right",padx=6)

        # Days of week
        s3=rsec("ימי שבוע")
        days_row2=tk.Frame(s3,bg=M_BG); days_row2.pack(fill="x",padx=8,pady=6)
        HEB_DAY_SHORT=["ש׳","ו׳","ה׳","ד׳","ג׳","ב׳","א׳"]
        self._rem_days=[tk.BooleanVar(value=True) for _ in range(7)]
        for i,short in enumerate(HEB_DAY_SHORT):
            col2=tk.Frame(days_row2,bg=M_BG); col2.pack(side="right",padx=4)
            tk.Label(col2,text=short,font=("Arial",9,"bold"),fg=M_TEXT,bg=M_BG).pack()
            tk.Checkbutton(col2,variable=self._rem_days[6-i],bg=M_BG,
                selectcolor=M_INP,activebackground=M_BG).pack()

        # Exclusions
        s4=rsec("החרגות")
        self._rem_skip_shab=tk.BooleanVar(value=True)
        self._rem_skip_hol=tk.BooleanVar(value=False)
        for lbl3,var3 in [("דלג על שבת:",self._rem_skip_shab),
                           ("דלג על חגים ומועדים:",self._rem_skip_hol)]:
            r3=rlrow(s4,lbl3)
            tk.Checkbutton(r3,variable=var3,bg=M_BG,selectcolor=M_INP,
                activebackground=M_BG).pack(side="right")

        # Notification
        s5=rsec("אופן התראה")
        self._rem_vis=tk.BooleanVar(value=True)
        self._rem_snd=tk.BooleanVar(value=False)
        for lbl4,var4 in [("הצג הודעת מסך:",self._rem_vis),("השמע צליל:",self._rem_snd)]:
            r4=rlrow(s5,lbl4)
            tk.Checkbutton(r4,variable=var4,bg=M_BG,selectcolor=M_INP,
                activebackground=M_BG).pack(side="right")
        r_np=rlrow(s5,"חלונית הצפה:")
        self._rem_notice_v=tk.StringVar(value="")
        notice_panels=[(str(p["id"]),p["id"])
                        for p in self.cfg.d.get("panels",[]) if p.get("type")=="notice"]
        notice_vals=["הודעת מסך מלא"]+[f"חלונית צפה #{pid}" for pid,_ in notice_panels]
        npcb=ttk.Combobox(r_np,textvariable=self._rem_notice_v,
            values=notice_vals,width=22,state="readonly",font=("Arial",10))
        npcb.current(0); npcb.pack(side="right")

        # Add button
        tk.Frame(inner,bg=M_SEP,height=1).pack(fill="x",padx=18,pady=10)
        add_btn=tk.Button(inner,text="➕  הוסף תזכורת",
            font=("Arial",12,"bold"),fg="#fff",bg=M_BLUE,bd=0,
            cursor="hand2",padx=22,pady=10,command=self._add_reminder)
        add_btn.pack(pady=4)
        self._hover_btn(add_btn,M_BLUE,M_LBLUE)
        self._rem_status=tk.StringVar(value="")
        tk.Label(inner,textvariable=self._rem_status,
            font=("Arial",10),fg=M_GREEN,bg=M_BG).pack(pady=4)

        self._refresh_rem_tree()

    def _rem_toggle_type(self):
        t=self._rem_type_v.get()
        parent_p=self._rem_personal_fr.master
        parent_z=self._rem_zmanim_fr.master
        if t=="personal":
            parent_p.pack(fill="x"); parent_z.pack_forget()
        else:
            parent_p.pack_forget(); parent_z.pack(fill="x")

    def _refresh_rem_tree(self):
        self._rem_tree.delete(*self._rem_tree.get_children())
        for r in self.cfg.reminders():
            done=r.get("done",False); last=r.get("last_triggered","")
            st="✓" if done else ("↺" if last else "⏳")
            rtype="🕍" if r.get("rem_type")=="zmanim" else "📅"
            short=r.get("text","")[:16]
            if r.get("rem_type")=="zmanim":
                zname=ZMANIM_KEYS.get(r.get("zman",""),"?")
                off=r.get("offset_min",0)
                when=f"{zname} {'+' if off>=0 else ''}{off}′"[:18]
            else:
                when=r.get("dt","")[:16]
            self._rem_tree.insert("","end",iid=str(r["id"]),
                values=(rtype,short,when,st))

    def _add_reminder(self):
        txt=self._rem_text_v.get().strip()
        if not txt: self._rem_status.set("⚠ יש לרשום טקסט"); return
        rem_type=self._rem_type_v.get()
        days=[i for i,v in enumerate(self._rem_days) if v.get()]
        if not days: self._rem_status.set("⚠ יש לבחור לפחות יום אחד"); return
        notice_sel=self._rem_notice_v.get()
        notice_pid=None
        if notice_sel and "חלונית" in notice_sel:
            try: notice_pid=int(notice_sel.split("#")[-1])
            except: pass
        if rem_type=="personal":
            dt_str=f"{self._rem_date_v.get().strip()} {self._rem_time_v.get().strip()}"
            try: datetime.strptime(dt_str,"%Y-%m-%d %H:%M")
            except: self._rem_status.set("⚠ פורמט תאריך/שעה שגוי"); return
            self.cfg.add_reminder(txt,"personal",dt_str=dt_str,days=days,
                skip_shabbat=self._rem_skip_shab.get(),skip_holidays=self._rem_skip_hol.get(),
                recurring=self._rem_rec_v.get(),notify_visual=self._rem_vis.get(),
                notify_sound=self._rem_snd.get(),notice_panel_id=notice_pid)
        else:
            try: off=int(self._rem_offset_v.get() or 0)
            except: off=0
            self.cfg.add_reminder(txt,"zmanim",zman=self._rem_zman_v.get(),offset_min=off,
                days=days,skip_shabbat=self._rem_skip_shab.get(),
                skip_holidays=self._rem_skip_hol.get(),recurring=self._rem_rec_v.get(),
                notify_visual=self._rem_vis.get(),notify_sound=self._rem_snd.get(),
                notice_panel_id=notice_pid)
        self._rem_text_v.set(""); self._rem_status.set("✓ תזכורת נוספה בהצלחה")
        self._refresh_rem_tree()

    def _del_reminder(self):
        sel=self._rem_tree.selection()
        if not sel: return
        rid=int(sel[0])
        if messagebox.askyesno("מחיקה","למחוק את התזכורת?",parent=self.win):
            self.cfg.del_reminder(rid)
            self._refresh_rem_tree()

    def _reset_reminder(self):
        sel=self._rem_tree.selection()
        if not sel: return
        rid=int(sel[0])
        self.cfg.mark_reminder(rid,done=False)
        # Also clear last_triggered so it can fire again today
        for r in self.cfg.reminders():
            if r.get("id")==rid: r["last_triggered"]=""; break
        self.cfg.save()
        self._refresh_rem_tree()
        self._rem_status.set("✓ תזכורת הופעלה מחדש")

    def _exit_app(self):
        if messagebox.askyesno("יציאה מהתוכנה",
                "האם לצאת לגמרי מלוח המודעות?",
                parent=self.win):
            self.app.display.root.destroy()

    # ── Tab: אודות ──────────────────────────────────────────────────────────
    def _build_about_tab(self):
        f=self._t_about
        cv=tk.Canvas(f,bg=M_BG,highlightthickness=0)
        cv.pack(fill="both",expand=True)

        # Draw star-background
        import random; random.seed(99)
        cv.update_idletasks()

        body=tk.Frame(f,bg=M_BG); body.place(relx=0.5,rely=0.5,anchor="center")

        tk.Label(body,text="▣",font=("Arial",56),fg=BLUE,bg=M_BG).pack(pady=(0,8))
        tk.Label(body,text=APP,font=("Arial",26,"bold"),fg=M_TEXT,bg=M_BG).pack()
        tk.Label(body,text="Digital Bulletin Board",
            font=("Arial",14),fg=M_TEXT2,bg=M_BG).pack(pady=(2,0))

        tk.Frame(body,bg=BLUE,height=2,width=320).pack(pady=16)

        info=[
            ("גרסה","1.0.0.5"),
            ("פיתוח","Claude Sonnet 4 / Anthropic"),
            ("ספריות","Python · Tkinter · Pillow · pyluach · astral · pytz"),
            ("מסד נתונים",str(CFG)),
        ]
        for lbl,val in info:
            r=tk.Frame(body,bg=M_BG); r.pack(pady=3)
            tk.Label(r,text=f"{lbl}:",font=("Arial",12,"bold"),
                fg=M_TEXT2,bg=M_BG,width=14,anchor="e").pack(side="right",padx=(0,8))
            tk.Label(r,text=val,font=("Arial",12),
                fg=M_TEXT,bg=M_BG,anchor="w").pack(side="right")

        tk.Frame(body,bg=M_SEP,height=1,width=320).pack(pady=14)

        tk.Label(body,
            text="לוח מודעות דיגיטלי המיועד לתצוגה ציבורית בבתי כנסת,\n"
                 "מוסדות וקהילות. מציג שעון, זמני הלכה, הודעות ועוד.",
            font=("Arial",11),fg=M_TEXT2,bg=M_BG,justify="center").pack(pady=4)

        tk.Label(body,text="הנחיות מפתח: F8 = פתח ניהול  |  F9 = סגור הודעת מסך מלא",
            font=("Arial",10),fg=BLUE,bg=M_BG).pack(pady=8)

# ── עורך רקע ראשי ───────────────────────────────────────────────────────────
class BackgroundEditor(tk.Frame):
    """Editor for the main display background panel."""
    def __init__(self,parent,disp,mgr):
        super().__init__(parent,bg=M_BG)
        self.disp=disp; self.mgr=mgr; self.cfg=mgr.cfg
        self._build()

    def _build(self):
        hdr=tk.Frame(self,bg=M_BG2,height=52); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr,text="עריכת: רקע ראשי ★",
            font=("Arial",13,"bold"),fg=GOLD,bg=M_BG2).pack(side="right",padx=16,pady=10)
        save_btn=tk.Button(hdr,text="💾 שמור",font=("Arial",11,"bold"),fg="#fff",bg=BLUE,
            bd=0,cursor="hand2",padx=18,pady=6,command=self._save)
        save_btn.pack(side="left",padx=6,pady=8)
        self.mgr._hover_btn(save_btn,BLUE,LBLUE)

        body=tk.Frame(self,bg=M_BG); body.pack(fill="both",expand=True,padx=30,pady=20)

        def section(title):
            fr=tk.Frame(body,bg=M_BG); fr.pack(fill="x",pady=6)
            tk.Label(fr,text=title,font=("Arial",12,"bold"),fg=LBLUE,bg=M_BG).pack(anchor="e")
            tk.Frame(fr,bg=M_SEP,height=1).pack(fill="x",pady=2)
            return tk.Frame(fr,bg=M_BG)

        def rrow(parent,label):
            r=tk.Frame(parent,bg=M_BG); r.pack(fill="x",padx=8,pady=4)
            tk.Label(r,text=label,font=("Arial",10),fg=M_TEXT,bg=M_BG,
                     width=22,anchor="e").pack(side="right",padx=(0,8))
            return r

        s=section("צבע רקע")
        s.pack(fill="x")
        r1=rrow(s,"צבע רקע:")
        self._bg_color=tk.StringVar(value=self.disp.get("bg_color",BG))
        prev=tk.Frame(r1,width=36,height=24,bg=self._bg_color.get(),cursor="hand2",bd=1,relief="solid")
        prev.pack(side="right",padx=3)
        def pick_color():
            c=colorchooser.askcolor(self._bg_color.get(),parent=self.mgr.win)
            if c and c[1]: self._bg_color.set(c[1]); prev.configure(bg=c[1])
        tk.Button(r1,text="בחר",font=("Arial",9),fg=M_TEXT,bg=M_BTN,bd=0,cursor="hand2",
            padx=6,command=pick_color).pack(side="right",padx=2)
        prev.bind("<Button-1>",lambda e:pick_color())

        s2=section("תמונת רקע")
        s2.pack(fill="x")
        r2=rrow(s2,"קובץ תמונה:")
        self._bg_img=tk.StringVar(value=self.disp.get("bg_image",""))
        tk.Entry(r2,textvariable=self._bg_img,width=28,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",10)).pack(side="right",padx=3)
        def pick_img():
            p=filedialog.askopenfilename(parent=self.mgr.win,
                filetypes=[("תמונות","*.png *.jpg *.jpeg *.bmp *.gif")])
            if p: self._bg_img.set(p)
        tk.Button(r2,text="בחר",font=("Arial",9),fg=M_TEXT,bg=M_BTN,bd=0,cursor="hand2",
            padx=6,command=pick_img).pack(side="right",padx=2)
        tk.Button(r2,text="נקה",font=("Arial",9),fg=M_TEXT2,bg=M_BTN,bd=0,cursor="hand2",
            padx=6,command=lambda:self._bg_img.set("")).pack(side="right",padx=2)

        s3=section("אפקטים")
        s3.pack(fill="x")
        self._stars=tk.BooleanVar(value=self.disp.get("show_stars",True))
        self._gradient=tk.BooleanVar(value=self.disp.get("gradient",True))
        for lbl,var in [("הצג כוכבים",self._stars),("גרדיאנט עדין",self._gradient)]:
            r=rrow(s3,lbl+":")
            tk.Checkbutton(r,variable=var,bg=M_BG,fg=M_TEXT,selectcolor=M_INP,
                activebackground=M_BG).pack(side="right")

    def _save(self):
        self.disp["bg_color"]=self._bg_color.get()
        self.disp["bg_image"]=self._bg_img.get()
        self.disp["show_stars"]=self._stars.get()
        self.disp["gradient"]=self._gradient.get()
        self.cfg.d["display"].update(self.disp)
        self.cfg.save()
        self.mgr.app.refresh_display()
        self.mgr.status_var.set("רקע ראשי נשמר ✓")

# ── עורך לוח ────────────────────────────────────────────────────────────────
class PanelEditor(tk.Frame):
    def __init__(self,parent,pc,mgr):
        super().__init__(parent,bg=M_BG)
        self.pc=pc; self.mgr=mgr; self.cfg=mgr.cfg
        self._vars={}
        self._build()

    def _build(self):
        # Header bar
        hdr=tk.Frame(self,bg=M_BG2,height=52); hdr.pack(fill="x"); hdr.pack_propagate(False)
        ptype=self.pc.get("type",""); pid=self.pc.get("id","")
        name=PANEL_NAMES.get(ptype,"?")
        tk.Label(hdr,text=f"עריכת: {name}  #{pid}",
            font=("Arial",13,"bold"),fg=M_TEXT,bg=M_BG2).pack(side="right",padx=16,pady=10)
        # Enable toggle
        en_v=tk.BooleanVar(value=self.pc.get("enabled",True)); self._vars["enabled"]=en_v
        tk.Checkbutton(hdr,text="מופעל",variable=en_v,
            font=("Arial",11),fg=M_TEXT,bg=M_BG2,selectcolor=M_INP,activebackground=M_BG2,
            activeforeground=M_TEXT).pack(side="left",padx=14)
        save_btn=tk.Button(hdr,text="💾 שמור",
            font=("Arial",11,"bold"),fg="#fff",bg=BLUE,bd=0,
            cursor="hand2",padx=18,pady=6,command=self._save)
        save_btn.pack(side="left",padx=6,pady=8)
        self.mgr._hover_btn(save_btn,BLUE,LBLUE)

        # Scrollable body
        outer=tk.Frame(self,bg=M_BG); outer.pack(fill="both",expand=True)
        cv=tk.Canvas(outer,bg=M_BG,highlightthickness=0)
        sb=ttk.Scrollbar(outer,orient="vertical",command=cv.yview)
        cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        cv.configure(yscrollcommand=sb.set)
        inner=tk.Frame(cv,bg=M_BG)
        wid=cv.create_window(0,0,anchor="nw",window=inner)
        inner.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(wid,width=e.width))
        def _scroll(e): cv.yview_scroll(-1*(1 if e.delta>0 else -1),"units")
        cv.bind("<MouseWheel>",_scroll); inner.bind("<MouseWheel>",_scroll)

        self._build_position(inner)
        self._build_appearance(inner)
        self._build_type_specific(inner)

    # ── Helpers ──
    def _sec(self,parent,title):
        fr=tk.Frame(parent,bg=M_BG); fr.pack(fill="x",padx=18,pady=5)
        tk.Label(fr,text=title,font=("Arial",12,"bold"),fg=LBLUE,bg=M_BG).pack(anchor="e",pady=(10,2))
        tk.Frame(fr,bg=M_SEP,height=1).pack(fill="x",pady=2)
        c=tk.Frame(fr,bg=M_BG); c.pack(fill="x"); return c

    def _row(self,parent,label,width=22):
        r=tk.Frame(parent,bg=M_BG); r.pack(fill="x",padx=8,pady=3)
        tk.Label(r,text=label,font=("Arial",10),fg=M_TEXT,bg=M_BG,
                 width=width,anchor="e").pack(side="right",padx=(0,6))
        return r

    def _entry(self,parent,label,key,default="",w=12):
        r=self._row(parent,label)
        v=tk.StringVar(value=str(self.pc.get(key,default))); self._vars[key]=v
        e=tk.Entry(r,textvariable=v,width=w,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",font=("Arial",10))
        e.pack(side="right"); return v

    def _color_picker(self,parent,label,key,default=BLUE):
        r=self._row(parent,label)
        v=tk.StringVar(value=self.pc.get(key,default)); self._vars[key]=v
        prev=tk.Frame(r,width=34,height=22,bg=v.get(),cursor="hand2",bd=1,relief="solid")
        prev.pack(side="right",padx=2)
        def pick():
            c=colorchooser.askcolor(v.get(),parent=self.mgr.win,title=label)
            if c and c[1]: v.set(c[1]); prev.configure(bg=c[1])
        tk.Button(r,text="בחר",font=("Arial",9),fg=M_TEXT,bg=M_BTN,bd=0,
            cursor="hand2",padx=6,command=pick).pack(side="right",padx=2)
        prev.bind("<Button-1>",lambda e: pick()); return v

    def _check(self,parent,label,key,default=True):
        r=self._row(parent,label)
        v=tk.BooleanVar(value=self.pc.get(key,default)); self._vars[key]=v
        tk.Checkbutton(r,variable=v,font=("Arial",10),bg=M_BG,fg=M_TEXT,
            selectcolor=M_INP,activebackground=M_BG).pack(side="right"); return v

    def _radio_row(self,parent,label,key,options,default=""):
        r=self._row(parent,label)
        v=tk.StringVar(value=self.pc.get(key,default)); self._vars[key]=v
        for val,lbl in options:
            tk.Radiobutton(r,text=lbl,variable=v,value=val,font=("Arial",10),
                fg=M_TEXT,bg=M_BG,selectcolor=M_INP,activebackground=M_BG).pack(side="right",padx=3)
        return v

    def _spinbox(self,parent,label,key,from_,to,default=0):
        r=self._row(parent,label)
        v=tk.StringVar(value=str(self.pc.get(key,default))); self._vars[key]=v
        tk.Spinbox(r,from_=from_,to=to,textvariable=v,width=6,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            buttonbackground=BTN,font=("Arial",10)).pack(side="right"); return v

    def _font_family_entry(self,parent,label,key,default="Arial"):
        r=self._row(parent,label)
        v=tk.StringVar(value=self.pc.get(key,default)); self._vars[key]=v
        fams=sorted(set(tkFont.families()))
        cb=ttk.Combobox(r,textvariable=v,values=fams,width=18,font=("Arial",10))
        cb.pack(side="right"); return v

    # ── Position section ──
    def _build_position(self,parent):
        s=self._sec(parent,"מיקום, גודל ושכבה")

        # Layer selection (z-order)
        lr=self._row(s,"שכבת תצוגה:")
        lv=tk.IntVar(value=self.pc.get("layer",1)); self._vars["layer"]=lv
        for val,lbl,tip in [(1,"שכבה 1 — עליון","הכי קדמי"),
                             (2,"שכבה 2 — אמצעי",""),
                             (3,"שכבה 3 — תחתון","הכי רחוק")]:
            tk.Radiobutton(lr,text=lbl,variable=lv,value=val,
                font=("Arial",10),fg=M_TEXT,bg=M_BG,selectcolor=M_INP,
                activebackground=M_BG).pack(side="right",padx=4)

        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=6,pady=4)

        # Preset sizes
        preset_row=tk.Frame(s,bg=M_BG); preset_row.pack(fill="x",padx=8,pady=4)
        tk.Label(preset_row,text="גדלים מומלצים:",
            font=("Arial",10),fg=M_TEXT2,bg=M_BG).pack(side="right",padx=6)
        PRESETS=[
            ("קטן (300×150)",(300,150)),
            ("בינוני (420×220)",(420,220)),
            ("גדול (600×350)",(600,350)),
            ("רחב (800×200)",(800,200)),
            ("ריבועי (300×300)",(300,300)),
            ("גבוה (250×500)",(250,500)),
        ]
        for nm,(w,h) in PRESETS:
            b=tk.Button(preset_row,text=nm,font=("Arial",8),fg=M_TEXT,bg=M_BTN,bd=0,
                cursor="hand2",padx=5,pady=3,
                command=lambda w2=w,h2=h: (self._vars.get("width",tk.StringVar()).set(str(w2)),
                                           self._vars.get("height",tk.StringVar()).set(str(h2))))
            b.pack(side="right",padx=2)

        # Grid fields
        grid=tk.Frame(s,bg=M_BG); grid.pack(fill="x",padx=10,pady=6)
        for lbl,key,default in [("X (מצד שמאל)","x",20),("Y (מלמעלה)","y",20),
                                  ("רוחב","width",350),("גובה","height",200)]:
            col=tk.Frame(grid,bg=M_BG); col.pack(side="left",padx=12)
            tk.Label(col,text=lbl,font=("Arial",9),fg=M_TEXT2,bg=M_BG).pack(anchor="e")
            v=tk.StringVar(value=str(self.pc.get(key,default))); self._vars[key]=v
            tk.Entry(col,textvariable=v,width=7,
                bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
                font=("Arial",10)).pack()

    # ── Appearance section ──
    def _build_appearance(self,parent):
        s=self._sec(parent,"עיצוב ומראה")
        self._check(s,"רקע שקוף","bg_transparent",False)
        self._color_picker(s,"צבע רקע:","bg_color",PNL)

        r_bgi=self._row(s,"תמונת רקע:")
        bgi_v=tk.StringVar(value=self.pc.get("bg_image","")); self._vars["bg_image"]=bgi_v
        tk.Entry(r_bgi,textvariable=bgi_v,width=22,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",10)).pack(side="right",padx=2)
        tk.Button(r_bgi,text="בחר",font=("Arial",9),fg=M_TEXT,bg=M_BTN,bd=0,
            cursor="hand2",padx=6,
            command=lambda: bgi_v.set(filedialog.askopenfilename(
                filetypes=[("תמונות","*.png *.jpg *.jpeg *.bmp")]) or bgi_v.get())
        ).pack(side="right",padx=2)

        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=6,pady=6)
        self._check(s,"מסגרת שקופה","border_transparent",False)
        self._color_picker(s,"צבע מסגרת:","border_color",BLUE)
        self._spinbox(s,"עובי מסגרת:","border_width",0,20,2)

    # ── Type-specific ──
    def _build_type_specific(self,parent):
        pt=self.pc.get("type","")
        if pt=="time":    self._build_time(parent)
        elif pt=="text":  self._build_text(parent)
        elif pt=="ad":    self._build_ad(parent)
        elif pt=="zmanim": self._build_zmanim(parent)
        elif pt=="element": self._build_element(parent)
        elif pt=="notice": self._build_notice(parent)
        elif pt=="screen_msg": self._build_screen_msg(parent)

    def _build_time(self,parent):
        s=self._sec(parent,"הגדרות שעון / תאריך")
        self._check(s,"הצג שעה","show_time",True)
        self._check(s,"הצג שניות","show_seconds",True)
        self._check(s,"הצג יום בשבוע","show_weekday",True)
        self._check(s,"הצג תאריך עברי","show_heb_date",True)
        self._check(s,"הצג תאריך לועזי","show_greg_date",True)
        self._check(s,"הצג חגים ומועדים","show_holiday",True)
        self._check(s,"הצג פרשת השבוע","show_parasha",True)
        self._check(s,"לפי ישראל (ולא חו\"ל)","israel",True)
        self._radio_row(s,"סגנון שעון:","clock_style",
            [("digital","דיגיטלי"),("analog","אנלוגי")],"digital")
        self._radio_row(s,"פורמט שעה:","time_format",
            [("24","24 שעות"),("12","12 שעות")],"24")
        self._color_picker(s,"צבע שעון:","clock_color",BLUE)
        self._color_picker(s,"צבע תאריך:","date_color",TEXT)
        self._font_family_entry(s,"גופן:","font_family","Arial")
        self._spinbox(s,"גודל שעון:","time_font_size",14,120,56)
        self._spinbox(s,"גודל תאריך:","date_font_size",10,60,18)

    def _build_text(self,parent):
        s=self._sec(parent,"הגדרות טקסט")
        tk.Label(s,text="תוכן הטקסט:",
            font=("Arial",10),fg=M_TEXT,bg=M_BG).pack(anchor="e",padx=10,pady=(4,1))
        txt_wrap=tk.Frame(s,bg=M_BG); txt_wrap.pack(fill="x",padx=10,pady=3)
        self._txt=tk.Text(txt_wrap,width=42,height=6,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",13),wrap="word",undo=True)
        self._txt.pack(fill="x")
        self._txt.insert("1.0",self.pc.get("content",""))

        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=8,pady=6)
        self._font_family_entry(s,"גופן:","font_family","Arial")
        self._spinbox(s,"גודל גופן:","font_size",8,120,20)
        self._color_picker(s,"צבע טקסט:","font_color","#ffffff")
        self._check(s,"מודגש","bold",False)
        self._check(s,"נטוי","italic",False)
        self._radio_row(s,"יישור:","align",
            [("right","ימין"),("center","מרכז"),("left","שמאל")],"right")
        self._spinbox(s,"ריפוד:","padding",0,60,14)

    def _build_ad(self,parent):
        s=self._sec(parent,"הגדרות מודעה / תמונות")
        tk.Label(s,text="רשימת תמונות (סדר הצגה):",
            font=("Arial",10,"bold"),fg=M_TEXT,bg=M_BG).pack(anchor="e",padx=10,pady=(6,2))
        lf=tk.Frame(s,bg=M_INP,bd=1,relief="solid"); lf.pack(fill="x",padx=10,pady=3)
        vsb=ttk.Scrollbar(lf,orient="vertical"); vsb.pack(side="left",fill="y")
        self._img_lb=tk.Listbox(lf,bg=M_INP,fg=M_TEXT,font=("Arial",10),height=7,
            selectbackground=BLUE,bd=0,highlightthickness=0,yscrollcommand=vsb.set)
        self._img_lb.pack(side="right",fill="both",expand=True)
        vsb.configure(command=self._img_lb.yview)
        for img in self.pc.get("images",[]): self._img_lb.insert("end",img)
        # Buttons
        bf=tk.Frame(s,bg=M_BG); bf.pack(fill="x",padx=10,pady=3)
        def add_imgs():
            ps=filedialog.askopenfilenames(parent=self.mgr.win,
                filetypes=[("תמונות","*.png *.jpg *.jpeg *.bmp *.gif *.webp")])
            for p in ps: self._img_lb.insert("end",p)
        def del_img():
            for i in reversed(self._img_lb.curselection()): self._img_lb.delete(i)
        def move_up():
            sel=self._img_lb.curselection()
            if not sel or sel[0]==0: return
            i=sel[0]; v=self._img_lb.get(i)
            self._img_lb.delete(i); self._img_lb.insert(i-1,v); self._img_lb.selection_set(i-1)
        def move_dn():
            sel=self._img_lb.curselection()
            if not sel or sel[0]==self._img_lb.size()-1: return
            i=sel[0]; v=self._img_lb.get(i)
            self._img_lb.delete(i); self._img_lb.insert(i+1,v); self._img_lb.selection_set(i+1)
        for t,cmd in [("+ הוסף",add_imgs),("✕ הסר",del_img),("↑",move_up),("↓",move_dn)]:
            b=tk.Button(bf,text=t,font=("Arial",10),fg=M_TEXT,bg=M_BTN,bd=0,
                cursor="hand2",padx=8,pady=4,command=cmd); b.pack(side="right",padx=2)

        self._spinbox(s,"זמן הצגה (שניות):","interval",1,600,5)
        self._radio_row(s,"התאמת תמונה:","fit_mode",
            [("contain","כיל"),("cover","מלא"),("stretch","מותח")],"contain")

    def _build_zmanim(self,parent):
        s=self._sec(parent,"הגדרות זמני הלכה")
        self._check(s,"הצג כותרת","show_title",True)
        self._entry(s,"כותרת:","title","זמני היום",w=20)
        self._color_picker(s,"צבע שעות:","time_color",BLUE)
        self._color_picker(s,"צבע תוויות:","label_color","#9090cc")
        self._color_picker(s,"צבע הדגשה:","highlight_color",GOLD)
        self._check(s,"הדגש זמן הבא","highlight_next",True)
        self._font_family_entry(s,"גופן:","font_family","Arial")
        self._spinbox(s,"גודל גופן:","font_size",9,36,14)

        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=6,pady=6)
        tk.Label(s,text="בחר זמנים להצגה:",
            font=("Arial",10,"bold"),fg=M_TEXT,bg=M_BG).pack(anchor="e",padx=10,pady=(2,4))
        show_items=self.pc.get("show_items",list(ZMANIM_KEYS.keys()))
        self._zchk={}
        grid=tk.Frame(s,bg=M_BG); grid.pack(fill="x",padx=10,pady=2)
        items=list(ZMANIM_KEYS.items())
        cols=2
        for i,(key,label) in enumerate(items):
            v=tk.BooleanVar(value=key in show_items); self._zchk[key]=v
            r2=i//cols; c2=i%cols
            tk.Checkbutton(grid,text=label,variable=v,font=("Arial",10),
                fg=M_TEXT,bg=M_BG,selectcolor=M_INP,activebackground=BG
            ).grid(row=r2,column=c2,sticky="e",padx=10,pady=2)

    def _build_element(self,parent):
        s=self._sec(parent,"הגדרות אלמנט עיצובי")
        r=self._row(s,"קובץ תמונה:")
        v=tk.StringVar(value=self.pc.get("image_path","")); self._vars["image_path"]=v
        tk.Entry(r,textvariable=v,width=24,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",10)).pack(side="right",padx=2)
        tk.Button(r,text="בחר",font=("Arial",9),fg=M_TEXT,bg=M_BTN,bd=0,
            cursor="hand2",padx=6,
            command=lambda: v.set(filedialog.askopenfilename(
                filetypes=[("תמונות","*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg")]) or v.get())
        ).pack(side="right")
        self._radio_row(s,"התאמה:","fit_mode",
            [("contain","כיל"),("cover","מלא"),("stretch","מותח")],"contain")

    def _build_notice(self,parent):
        s=self._sec(parent,"הגדרות הודעה צפה")
        tk.Label(s,text="תוכן ההודעה:",
            font=("Arial",10),fg=M_TEXT,bg=M_BG).pack(anchor="e",padx=10,pady=(4,1))
        txt_wrap=tk.Frame(s,bg=M_BG); txt_wrap.pack(fill="x",padx=10,pady=3)
        self._txt=tk.Text(txt_wrap,width=42,height=3,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",13),wrap="word",undo=True)
        self._txt.pack(fill="x")
        self._txt.insert("1.0",self.pc.get("content",""))
        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=8,pady=6)
        self._font_family_entry(s,"גופן:","font_family","Arial")
        self._spinbox(s,"גודל גופן:","font_size",10,120,26)
        self._color_picker(s,"צבע טקסט:","font_color",GOLD)
        self._check(s,"מודגש","bold",True)
        self._check(s,"גלילה (מרקיז)","scroll",True)
        self._spinbox(s,"מהירות גלילה (פיקסל/שניה):","scroll_speed",1,20,2)
        self._radio_row(s,"כיוון גלילה:","scroll_dir",
            [("rtl","ימין לשמאל"),("ltr","שמאל לימין")],"rtl")

    def _build_screen_msg(self,parent):
        s=self._sec(parent,"הגדרות הודעת מסך")
        tk.Label(s,text="תוכן ההודעה:",
            font=("Arial",10),fg=M_TEXT,bg=M_BG).pack(anchor="e",padx=10,pady=(4,1))
        txt_wrap=tk.Frame(s,bg=M_BG); txt_wrap.pack(fill="x",padx=10,pady=3)
        self._txt=tk.Text(txt_wrap,width=42,height=4,
            bg=M_INP,fg=M_TEXT,insertbackground=M_TEXT,bd=1,relief="solid",
            font=("Arial",13),wrap="word",undo=True)
        self._txt.pack(fill="x")
        self._txt.insert("1.0",self.pc.get("content",""))
        tk.Frame(s,bg=M_SEP,height=1).pack(fill="x",padx=8,pady=6)
        self._font_family_entry(s,"גופן:","font_family","Arial")
        self._spinbox(s,"גודל גופן:","font_size",10,120,28)
        self._color_picker(s,"צבע טקסט:","font_color",GOLD)
        self._check(s,"מודגש","bold",True)
        self._check(s,"נטוי","italic",False)
        self._radio_row(s,"יישור:","align",
            [("right","ימין"),("center","מרכז"),("left","שמאל")],"center")

    # ── Save ──
    def _save(self):
        data={}
        INT_KEYS={"x","y","width","height","border_width","font_size","time_font_size",
                  "date_font_size","padding","interval","scroll_speed","layer"}
        BOOL_KEYS={"enabled","show_time","show_seconds","show_weekday","show_heb_date",
                   "show_greg_date","bg_transparent","border_transparent","bold","italic",
                   "show_title","highlight_next","scroll","show_holiday","show_parasha","israel"}
        for key,var in self._vars.items():
            val=var.get()
            if key in INT_KEYS:
                try: val=int(float(val))
                except: val=self.pc.get(key,0)
            elif key in BOOL_KEYS:
                val=bool(val)
            data[key]=val
        if hasattr(self,"_txt"):
            data["content"]=self._txt.get("1.0","end-1c")
        if hasattr(self,"_img_lb"):
            data["images"]=[self._img_lb.get(i) for i in range(self._img_lb.size())]
        if hasattr(self,"_zchk"):
            data["show_items"]=[k for k,v in self._zchk.items() if v.get()]
        self.pc.update(data)
        self.cfg.upd_panel(self.pc["id"],data)
        self.mgr.app.refresh_display()
        self.mgr._refresh_tree()
        self.mgr.status_var.set(f"לוח #{self.pc['id']} נשמר בהצלחה ✓")

# ── Main App ──────────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        self.cfg=Config()
        self.manager=None
        self.display=DisplayWin(self)
        self._mgr_proc=None
        self._screen_is_off = False
        # Poll for signals from PyQt6 manager every 500ms
        self.display.root.after(500, self._poll_signals)

    def open_mgr(self):
        """Launch the PyQt6 manager as a subprocess."""
        import subprocess, secrets
        if self._mgr_proc and self._mgr_proc.poll() is None:
            return  # already running
        # Reload config from disk so any password set since startup is honored
        try:
            with open(CFG,"r",encoding="utf-8") as _f: _raw=json.load(_f)
            _base=copy.deepcopy(_DEF_CFG); self.cfg._merge(_base,_raw); self.cfg.d=_base
        except: pass

        if self.cfg.has_pw():
            pw=simpledialog.askstring(
                "סיסמא","הזן סיסמת כניסה:",
                show="*",parent=self.display.root)
            if pw is None: return
            if not self.cfg.check_pw(pw):
                messagebox.showerror("שגיאה","סיסמא שגויה!",
                    parent=self.display.root); return

        # Try PyQt6 manager first; fall back to tkinter ManagerWin
        mgr_script=Path(__file__).parent/"manager_qt.py"
        if mgr_script.exists():
            # Clear old signals
            for sig in ("refresh_signal","manager_closed","cmd.json"):
                p=DATA/sig
                try: p.unlink()
                except: pass
            # Write one-time auth token so manager_qt.py knows it was launched properly
            token = secrets.token_hex(24)
            tok_file = DATA / "mgr_auth.tok"
            tok_file.write_text(token, encoding="utf-8")
            self.display.root.attributes("-topmost",False)
            self._mgr_proc=subprocess.Popen(
                [sys.executable, str(mgr_script), str(CFG), token],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
            )
        else:
            self.manager=ManagerWin(self)

    def _poll_signals(self):
        """Check for signals written by PyQt6 manager."""
        # Refresh signal
        sig=DATA/"refresh_signal"
        if sig.exists():
            try: sig.unlink()
            except: pass
            try:
                with open(CFG,"r",encoding="utf-8") as _f:
                    _raw=json.load(_f)
                _base=copy.deepcopy(_DEF_CFG)
                self.cfg._merge(_base,_raw)
                self.cfg.d=_base
            except Exception: pass
            self.refresh_display()

        # Command (fullscreen_msg / exit)
        cmd_path=DATA/"cmd.json"
        if cmd_path.exists():
            try:
                cmd=json.loads(cmd_path.read_text(encoding="utf-8"))
                cmd_path.unlink()
                action=cmd.get("action","")
                if action=="fullscreen_msg":
                    self.display.show_fullscreen_msg(
                        cmd["text"],
                        duration=cmd.get("duration",0),
                        fg=cmd.get("fg",GOLD),
                        bg=cmd.get("bg","#060015"),
                        fontsize=cmd.get("fontsize",48))
                elif action=="set_preview_board":
                    self.display._preview_board_id = cmd.get("board_id")
                    self.display.refresh()
                elif action=="popup_notice_test":
                    panel_id = cmd.get("panel_id")
                    duration = cmd.get("duration", 5)
                    pc = next((p for p in self.cfg.d.get("panels",[])
                               if p.get("id") == panel_id), None)
                    if pc:
                        test_text = pc.get("content","") or "דוגמה לחלונית הצפה"
                        self.display._show_popup_reminder(
                            f"__test_{panel_id}", test_text, duration=duration, _pc_override=pc)
                elif action=="exit":
                    self.display.root.destroy(); return
            except: pass

        # Manager closed signal
        closed=DATA/"manager_closed"
        if closed.exists():
            try: closed.unlink()
            except: pass
            try:
                with open(CFG,"r",encoding="utf-8") as _f: _raw=json.load(_f)
                _base=copy.deepcopy(_DEF_CFG); self.cfg._merge(_base,_raw); self.cfg.d=_base
            except: pass
            self.display.root.attributes("-topmost",True)
            self.display._preview_board_id = None   # end preview mode
            self._mgr_proc=None

        # ── Shutdown/Cover checks ──────────────────────────────────────────────
        self._check_cover()
        self._check_sleep()

        self.display.root.after(500,self._poll_signals)

    # ── Cover screen logic ────────────────────────────────────────────────────
    def _check_cover(self):
        """Show/hide Shabbat/Holiday cover overlay."""
        sc = self.cfg.d.get("shutdown_cover", {})
        if not sc.get("cover_enabled", False):
            self.display.hide_cover()
            return
        if not ASTRAL_OK:
            return
        try:
            loc = self.cfg.d.get("location", {})
            tz_name = loc.get("tz", "Asia/Jerusalem")
            import pytz as _pytz
            tz_obj = _pytz.timezone(tz_name)
            li = LocationInfo("loc","c", tz_name,
                              loc.get("lat",31.7683), loc.get("lng",35.2137))
            from astral.sun import sun as _sun
            now = datetime.now()
            today_s = _sun(li.observer, date=now.date(), tzinfo=tz_obj)
            sunset_today = today_s["sunset"].replace(tzinfo=None)
            # Tomorrow's sunset for havdala reference
            tomorrow = now.date() + timedelta(days=1)
            try:
                tom_s = _sun(li.observer, date=tomorrow, tzinfo=tz_obj)
                sunset_tom = tom_s["sunset"].replace(tzinfo=None)
            except:
                sunset_tom = sunset_today + timedelta(hours=24)
        except:
            self.display.hide_cover()
            return

        before_min = sc.get("cover_before_min", 18)
        after_min  = sc.get("cover_after_min", 50)
        holidays   = sc.get("holidays", {})
        blocked    = False
        cover_image = ""

        # Check Shabbat (Saturday = weekday 5 in Python / isoweekday 6)
        if holidays.get("shabbat", {}).get("enabled", True):
            # Friday evening block: from (sunset_friday - before_min) to (sunset_saturday + after_min)
            weekday = now.weekday()  # 0=Mon … 4=Fri … 5=Sat … 6=Sun
            if weekday == 4:  # Friday
                block_start = sunset_today - timedelta(minutes=before_min)
                if now >= block_start:
                    blocked = True
                    cover_image = holidays.get("shabbat",{}).get("image","")
            elif weekday == 5:  # Saturday
                block_end = sunset_today + timedelta(minutes=after_min)
                if now <= block_end:
                    blocked = True
                    cover_image = holidays.get("shabbat",{}).get("image","")

        # Check Jewish holidays via pyluach
        if not blocked and PYLUACH_OK:
            try:
                from pyluach import dates as _pd
                heb_today = _pd.HebrewDate.from_pydate(now.date())
                heb_tomorrow = _pd.HebrewDate.from_pydate(tomorrow)
                # Convert to (month, day) tuples
                today_md = (heb_today.month, heb_today.day)
                tom_md   = (heb_tomorrow.month, heb_tomorrow.day)
                for _hname, hkey, hdays in _JEWISH_HOLIDAYS:
                    if hkey == "shabbat": continue
                    hcfg = holidays.get(hkey, {})
                    if not hcfg.get("enabled", False): continue
                    if not hdays: continue
                    sel = hcfg.get("selected_days",
                        [f"{d[0]}_{d[1]}" for d in hdays])
                    # Check if today or tomorrow (eve) is a holiday day
                    today_key = f"{today_md[0]}_{today_md[1]}"
                    tom_key   = f"{tom_md[0]}_{tom_md[1]}"
                    # Eve of holiday: tonight's sunset begins the holiday
                    if tom_key in sel:
                        block_start = sunset_today - timedelta(minutes=before_min)
                        if now >= block_start:
                            blocked = True
                            cover_image = hcfg.get("image","")
                            break
                    # During holiday day: block until tonight's sunset + after_min
                    if today_key in sel:
                        block_end = sunset_today + timedelta(minutes=after_min)
                        if now <= block_end:
                            blocked = True
                            cover_image = hcfg.get("image","")
                            break
            except:
                pass

        if blocked:
            self.display.show_cover(cover_image)
        else:
            self.display.hide_cover()

    # ── Sleep/wake logic ──────────────────────────────────────────────────────
    def _check_sleep(self):
        """Turn screen off/on based on schedule."""
        sc = self.cfg.d.get("shutdown_cover", {})
        if not sc.get("sleep_enabled", False):
            if getattr(self, "_screen_is_off", False):
                self._wake_screen()
            return
        now = datetime.now()
        schedules = sc.get("sleep_schedules", [])
        should_sleep = False
        for sched in schedules:
            # Check days of week
            enabled_days = sched.get("days", list(range(7)))
            if now.weekday() not in enabled_days:
                continue
            # Check optional date range
            date_from = sched.get("date_from","")
            date_to   = sched.get("date_to","")
            if date_from:
                try:
                    if now.date() < datetime.strptime(date_from, "%Y-%m-%d").date():
                        continue
                except: pass
            if date_to:
                try:
                    if now.date() > datetime.strptime(date_to, "%Y-%m-%d").date():
                        continue
                except: pass
            # Check time range
            off_h = sched.get("off_hour",22); off_m = sched.get("off_min",0)
            on_h  = sched.get("on_hour",6);   on_m  = sched.get("on_min",0)
            cur_min = now.hour*60 + now.minute
            off_min_abs = off_h*60 + off_m
            on_min_abs  = on_h*60  + on_m
            if off_min_abs <= on_min_abs:
                # Same-day range (e.g. 14:00–16:00)
                if off_min_abs <= cur_min < on_min_abs:
                    should_sleep = True; break
            else:
                # Overnight range (e.g. 22:00–06:00)
                if cur_min >= off_min_abs or cur_min < on_min_abs:
                    should_sleep = True; break

        if should_sleep and not getattr(self, "_screen_is_off", False):
            self._sleep_screen()
        elif not should_sleep and getattr(self, "_screen_is_off", False):
            self._wake_screen()

    def _sleep_screen(self):
        self._screen_is_off = True
        try:
            if sys.platform == "win32":
                import ctypes
                # Send WM_SYSCOMMAND / SC_MONITORPOWER to turn off monitor
                ctypes.windll.user32.SendMessageW(
                    ctypes.windll.user32.GetForegroundWindow(), 0x0112, 0xF170, 2)
            elif sys.platform.startswith("linux"):
                os.system("xset dpms force off")
            elif sys.platform == "darwin":
                os.system("pmset displaysleepnow")
        except: pass

    def _wake_screen(self):
        self._screen_is_off = False
        try:
            if sys.platform == "win32":
                import ctypes, time as _t
                # Simulate mouse move to wake the display
                pt = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)   # move +1
                _t.sleep(0.05)
                ctypes.windll.user32.mouse_event(0x0001, -1, 0, 0, 0)  # move back
            elif sys.platform.startswith("linux"):
                os.system("xset dpms force on")
                os.system("xset s reset")
            elif sys.platform == "darwin":
                os.system("caffeinate -u -t 1")
        except: pass

    def refresh_display(self):
        self.display.refresh()

    def run(self):
        self.display.run()

# ── Entry ─────────────────────────────────────────────────────────────────────
def _try_install_deps():
    import subprocess
    pkgs=["pillow","pyluach","astral","pytz"]
    for pkg in pkgs:
        try: subprocess.run([sys.executable,"-m","pip","install",pkg,"-q",
                             "--break-system-packages"],check=True,capture_output=True)
        except: pass

def main():
    if sys.platform=="win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except: pass
    if not PYLUACH_OK or not ASTRAL_OK:
        print("\u05deתקין תלויות..."); _try_install_deps()
    app=App(); app.run()

if __name__=="__main__":
    main()
