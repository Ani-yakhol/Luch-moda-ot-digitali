# לוח מודעות דיגיטלי — Digital Bulletin Board v4.5
=================================================

## חדש בגרסה 4.5:
   - לשונית 'תצוגה' — כפתור 'הוסף לוח' פותח חלונית צפה עם כל סוגי הלוחות (10 סוגים),
     במקום גריד כפתורים קבוע — חוסך מקום ומגדיל את שטח רשימת הלוחות הקיימים
   - ערכות עיצוב: שמירה וטעינה של מספר ערכות עיצוב במסד הנתונים —
     לחצן 'ערכות עיצוב' מעל רשימת הלוחות, בחירה מרשימה נגללת, הוספה/מחיקה,
     יצוא ויבוא פועלים על הערכה הנוכחית הנבחרת
   - קובץ requirements.txt מעודכן עם כל הספריות הנדרשות

## חדש בגרסה 4.4:
   - בחירת גופן (כל הלוחות): שדה גופן הוחלף לרשימה נגללת של כל הגופנים המותקנים,
     עם אפשרות הקלדה חופשית (editable combo) — בהגדרות עיצוב ובעורכי תוכן
   - לוח תאריך — שדות חדשים (כל אחד עם תיבת סימון + בחירת צבע):
       • קריאת התורה / השבוע
       • הפטרה / מועד
       • יעלה ויבוא (מוצג רק ביו"ט / ר"ח)
       • מוריד הטל / ותן ברכה
       • משיב הרוח ומוריד הגשם
       • ותן טל ומטר לברכה
       • דף יומי (תלמוד בבלי) — חישוב אוטומטי
   - יישור RTL בסקציית מיקום וגודל: כל שורות ההגדרות מיושרות לצד ימין
   - פקודות קומפול עודכנו ל-onedir (יציב יותר, קובץ exe קל יותר)

## הפעלה מהירה (Windows):
1. לחץ פעמיים על install_and_run.bat
   → יתקין ספריות ויפעיל אוטומטית

## הפעלה ידנית:
   pip install pillow pyluach astral pytz PyQt6 zmanim

   # אופציונלי — לתמיכה ב-PDF ו-MP4:
   pip install pdf2image opencv-python

   python digital_bulletin.py

## שימוש:
   F8  ← פתיחת ממשק ניהול
   F9  ← סגירת הודעת מסך מלא
   ESC ← לא סוגר (מכוון, כדי למנוע סגירה בטעות)
   לסגירה: ממשק ניהול → כפתור X

## ספריות נדרשות:
   - Python 3.8+
   - pillow, pyluach, astral, pytz, PyQt6, zmanim
   - pdf2image (אופציונלי — דורש גם poppler)
   - opencv-python / cv2 (אופציונלי — לתמיכה ב-MP4)

=======================================================
## קומפול לתיקיית הפעלה (.exe + קבצי משנה) — Windows
=======================================================

### מדוע onedir ולא onefile?
   onedir (ברירת מחדל) מייצר תיקייה עם exe + קבצי משנה.
   יתרונות: הפעלה מהירה יותר, יציבות גבוהה יותר, גודל exe קטן משמעותית.
   כדי להפיץ: zip את כל תיקיית dist\LuachModaot ושלח.

### התקנת PyInstaller:
   pip install pyinstaller

### ⚠️ דרישות לפני קומפול:
   - digital_bulletin.py ו-manager_qt.py חייבים להיות באותה תיקייה
   - אם יש digital_bulletin.ico — הכנס לאותה תיקייה; אחרת הסר את --icon

=======================================================
### קומפול מלא — תצוגה + ממשק ניהול (Windows, ללא אייקון):
=======================================================
   pyinstaller --onedir --noconsole ^
     --add-data "manager_qt.py;." ^
     --collect-all PyQt6 ^
     --hidden-import=PIL ^
     --hidden-import=PIL._imagingtk ^
     --hidden-import=pyluach ^
     --hidden-import=astral ^
     --hidden-import=pytz ^
     --hidden-import=zmanim ^
     --hidden-import=zmanim.zmanim_calendar ^
     --name "LuachModaot" ^
     digital_bulletin.py

### עם אייקון (רק אם digital_bulletin.ico קיים):
   pyinstaller --onedir --noconsole ^
     --add-data "manager_qt.py;." ^
     --collect-all PyQt6 ^
     --hidden-import=PIL ^
     --hidden-import=PIL._imagingtk ^
     --hidden-import=pyluach ^
     --hidden-import=astral ^
     --hidden-import=pytz ^
     --hidden-import=zmanim ^
     --hidden-import=zmanim.zmanim_calendar ^
     --icon=digital_bulletin.ico ^
     --name "LuachModaot" ^
     digital_bulletin.py

=======================================================
### קומפול ממשק ניהול בנפרד (manager_qt.exe, Windows):
=======================================================
   pyinstaller --onedir --noconsole ^
     --collect-all PyQt6 ^
     --hidden-import=pyluach ^
     --hidden-import=astral ^
     --hidden-import=pytz ^
     --hidden-import=zmanim ^
     --hidden-import=zmanim.zmanim_calendar ^
     --name "LuachModaot_Manager" ^
     manager_qt.py

### עם אייקון:
   pyinstaller --onedir --noconsole ^
     --collect-all PyQt6 ^
     --hidden-import=pyluach ^
     --hidden-import=astral ^
     --hidden-import=pytz ^
     --hidden-import=zmanim ^
     --hidden-import=zmanim.zmanim_calendar ^
     --icon=digital_bulletin.ico ^
     --name "LuachModaot_Manager" ^
     manager_qt.py

=======================================================
### קומפול על Linux / Mac:
=======================================================

### קומפול מלא (ללא אייקון):
   pyinstaller --onedir --noconsole \
     --add-data "manager_qt.py:." \
     --collect-all PyQt6 \
     --hidden-import=PIL \
     --hidden-import=PIL._imagingtk \
     --hidden-import=pyluach \
     --hidden-import=astral \
     --hidden-import=pytz \
     --hidden-import=zmanim \
     --hidden-import=zmanim.zmanim_calendar \
     --name "LuachModaot" \
     digital_bulletin.py

### קומפול ממשק ניהול בנפרד (Linux/Mac):
   pyinstaller --onedir --noconsole \
     --collect-all PyQt6 \
     --hidden-import=pyluach \
     --hidden-import=astral \
     --hidden-import=pytz \
     --hidden-import=zmanim \
     --hidden-import=zmanim.zmanim_calendar \
     --name "LuachModaot_Manager" \
     manager_qt.py

   הערה: ב-Linux/Mac השתמש ב : (נקודותיים) במקום ; ב--add-data

=======================================================
### כיצד F8 עובד אחרי קומפול:
=======================================================
   - --add-data "manager_qt.py;." ארז את manager_qt.py בתוך תיקיית LuachModaot
   - בזמן ריצה הוא נמצא ב-_MEIPASS — F8 עובד ללא קבצים נוספים
   - אם קימפלת גם LuachModaot_Manager — שתי התיקיות חייבות לשתף את אותו
     קובץ הגדרות (config.json נשמר ב-%USERPROFILE%\.digital_bulletin)
   - תיקיית הפצה מלאה: zip את dist\LuachModaot כולה

=======================================================
### הפצה — מה לכלול ב-zip:
=======================================================
   dist\LuachModaot\          ← תיקייה שלמה (exe + _internal)
   (אופציונלי) dist\LuachModaot_Manager\  ← אם קומפלת בנפרד
