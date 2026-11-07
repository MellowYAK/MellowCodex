# Local Agent Hub

PLAY reply tracking distinguishes consecutive status and result messages even when ChatGPT groups them under one turn. The isolated browser acceptance verified automatic result delivery, ingestion of the remote answer and return to listening. This does not establish automatic correctness of memory feedback or complete production acceptance.

**גרסת קוד: 0.14.0 · עדכון תיעוד: 6 בנובמבר 2026.** [היסטוריית גרסאות ותיקונים](CHANGELOG.md) · [תוצאות בדיקות](VALIDATION.md).

סוכן מקומי ל־Windows, מותקן בכונן E. זו גרסת פיילוט עובדת, ולא תחליף מלא ומאומת לכל יכולות Codex.

## הפעלה

1. הרץ `E:\AI\Start-Local-Agent.cmd`. ייפתח חלון Windows עצמאי, ללא תלות ב־Codex או בדפדפן.
2. הדפדפן המובנה הוא Chromium עצמאי (Qt WebEngine), עם פרופיל שנשמר בכונן E. סגירת החלון משאירה את הממשק והדפדפן במגש המערכת. פתיחת הקיצור שוב מציגה את אותו מופע.
3. בחר תיקיית פרויקט קיימת, כתוב משימה ובחר מצב: קריאה, קוד ופקודות, או מחשב וראייה.
4. הוסף בדיקת קובץ צפוי אם אפשר. ללא בדיקת השלמה מוגדרת, התוצאה ממתינה לסקירה שלך.

עצירה: הכפתור **עצור הכול** או **Ctrl+Alt+F12** כאשר קיצור הדרך רשום בהצלחה. מצב הרישום מופיע ב־API היכולות. גם הזזת העכבר לפינה השמאלית העליונה של המסך הווירטואלי חוסמת קלט חדש. עצירה אינה מבטלת פעולה חיצונית שכבר הושלמה.

הסוכן מפעיל את הדפדפן שלו ישירות דרך Playwright/CDP, ללא Codex. כניסה רגילה נעשית באתר עצמו בדפדפן המובנה; cookies, כולל cookies של סשן ו־HttpOnly, וכן localStorage ו־IndexedDB נשמרים בפרופיל מקומי קבוע. שמירתם נבדקה בין שני תהליכי דפדפן נפרדים. האתר עדיין יכול לפוג או לבטל התחברות.

הכפתור "ייבוא כניסה מ־Chrome" מספק קוד חד־פעמי לתוסף המקומי בתיקיית chrome-session-bridge. זו אפשרות נפרדת: יש לטעון את התוסף ב־Chrome פעם אחת, ולבחור במפורש את האתר להעברה; אין העתקה או פענוח של פרופיל Chrome. בדיקת העברה סינתטית עברה, אבל העברת חשבון אישי אמיתי מ־Chrome לא אומתה. אין צורך בתוסף לצורך כניסה רגילה בדפדפן המובנה.

לגישה מקומית: `http://127.0.0.1:8876`. כתובת Tailscale שהוגדרה במחשב היא `http://100.78.233.10:8876`; מכשיר מרוחק צריך להיות מחובר לרשת Tailscale המתאימה ולהשלים את מנגנון הכניסה לממשק. כתובת זו תלויה בהגדרת המחשב ואינה כתובת ציבורית כללית. אין לשמור בתיעוד מפתח כניסה או קישור התחברות זמני.

## חיבור MCP דרך שרת הגשר — 0.10.0

כתובת החיבור הקבועה: **https://agent.178-128-45-70.sslip.io/mcp**. זהו שרת MCP מסוג Streamable HTTP עם OAuth; זו אינה כתובת הממשק המקומי.

הארכיטקטורה משתמשת באותו רעיון של Ember Table ו־Ember Video: המחשב יוצר מנהרת SSH יוצאת אל השרת. השרת הציבורי אינו צריך לדעת את כתובת ה־IP המשתנה של המחשב. בכל הפעלת Hub עם `E:\AI\state\relay.json` מופעלים שער MCP מקומי ומנהרה; לאחר ניתוק מתבצע ניסיון התחברות חוזר. סגירת חלון הסוכן למגש אינה מפסיקה את השירות. המחשב והשירות חייבים לפעול ולהיות מחוברים לרשת.

1. בחיבור MCP מותאם ב־ChatGPT השתמש בכתובת שלמעלה ובאימות OAuth.
2. תיפתח בקשת הרשאה עם קוד. בסוכן פתח **הגדרות → חיבור מרחוק ל־ChatGPT**, השווה את הקוד ואשר את החיבור.
3. בקשות נשלחות בשפה חופשית באמצעות `submit_task`; לכל בקשה מזהה קבוע למניעת ביצוע כפול. הפלאגין קורא התקדמות באמצעות `get_task`. העבודה נשמרת באותן שיחות ונעשית בידי אותו מנוע וכלים של הסוכן.
4. אפשר לבטל את הרשאות החיבור בהגדרות. קישור להורדת קובץ שהונפק קודם פג לאחר עד עשר דקות, גם אם ההרשאה בוטלה בינתיים.

הכלים הציבוריים: רשימת פרויקטים ושיחות, יצירת שיחה, שליחת משימה, קריאת מצב ואבחון, קריאת שיחה, ביטול משימה וקבלת קובץ קיים לפי מזהה. תמונות קטנות מוחזרות גם כתוכן תמונה. קבצים אחרים מוחזרים בקישור HTTPS חתום וקצר־חיים. זהו חיבור נוסף; ההאזנה לשיחת ChatGPT בדפדפן הפנימי נשארת מסלול נפרד, ואינה תנאי לקבלת פקודות דרך MCP. אין צורך לכתוב JSON בשיחת המשתמש.

הפרדה בין השירותים: Hub עבר מ־8765 ל־**8876**, כדי שלא יתנגש ב־Ember Table; שער MCP מאזין רק ב־`127.0.0.1:8897`; המנהרה משתמשת ב־`127.0.0.1:18897` בשרת ובמשתמש SSH ייעודי. הפורטים 18765/18893 והגדרות Ember לא שונו. מפתח המנהרה וה־OAuth נשמרים תחת `E:\AI\state\mcp`, עם הרשאות מקומיות מוגבלות; סיסמת מנהל השרת אינה נשמרת.

מצב החיבור מופיע בהגדרות. אבחון: `relay-status.json`, `relay.stderr.log`, `mcp.stderr.log` בתיקיית state. התקנה חוזרת לשרת באמצעות `deploy/bridge.py` דורשת אימות טביעת מפתח SSH וסיסמה בהקלדה; הסקריפט שומר גיבויים של קובצי החיבור שלו ובודק hashes של תצורת Ember. תעודת HTTPS מתחדשת באמצעות certbot הקיים בשרת.

נבדקו חיבור ציבורי, OAuth וביטולו, ביצוע משימת קריאה באמצעות הסוכן, שמירה ללא כפילות, הורדת קובץ והתאוששות מנהרת SSH. התקנת המחבר בחשבון ChatGPT של המשתמש, שימוש מהטלפון ואתחול Windows טרם נבדקו במסגרת שחרור זה. יכולות המחשב תלויות באותן מגבלות של הכלים והסשן; הגשר אינו מוסיף שליטה במסך Windows נעול.

## היכולות שקיימות בקוד

עדכון 0.4.0 נבדק בריצת הסוכן עצמו: בחירת כתבה בוואלה, יצירת PDF ושמירתו בתיקיית הפרויקט, ולאחר תיקון מתאם לשונית הרקע גם מסירתו לשיחת ChatGPT. תיקונים מיושמים במנגנונים המשותפים לכל המודלים; החלפת מודל אינה מבטלת את תור הבקשות, הגנות משחזור פעולות או דיווח השגיאות. איכות ההחלטות עדיין תלויה במודל ובתוכן האתר. בדיקת פיתוח ישירה אינה מוצגת כהצלחה אוטונומית של הסוכן.

- הקשר המודל: תוצאות גדולות מצומצמות ל־JSON תקין עם מזהים וקישורים; נשמרות המטרה וקבוצות קריאות הכלים האחרונות. התיעוד המקורי אינו משתנה. התקציב מבוסס אומדן שמרני, לא tokenizer; אם המידע החיוני אינו נכנס, מתקבלת שגיאה מפורשת במקום השמטת המטרה.
- לחיצות בדפדפן הפנימי מפעילות פקד DOM שנצפה ונבדק כגלוי, זמין ולא מכוסה, ללא תלות באנימציות של לשונית רקע. כשל תצפית אחרי קלט מדווח בנפרד. מעבר בין טאבים אינו דורש שהטאב הקודם יהיה תקין.
- לשונית רקע ששטח התצוגה שלה התאפס מופעלת מחדש במתאם Qt ומקבלת גודל תקין, בלי ניווט מחדש או הצגת חלון. הבדיקה חוזרת גם אחרי בחירת קובץ להעלאה.
- אימות צירופים: תמונות נבדקות כטעונות, וקבצים אחרים דורשים כרטיס קובץ תואם בהודעה החדשה שנשלחה. כרטיס מאמת נוכחות של צירוף, לא תקינות תוכנו המרוחק. תגובה שהגיעה לאחר ניקוי מטרת המשימה נשמרת ומחזירה את המאזין להמתנה לבקשה חדשה, בלי סמכות לבצע הוראות חדשות מתוכה.
- בקשה ישנה ששוחזרה בתור ותשובתה כבר טופלה נסגרת ללא ביצוע חוזר, כדי שלא תחסום את ההאזנה אחרי רענון.

- קבלת משימות: בקשה שנחסמה בגלל תור עסוק נשמרת וממתינה לקבלה. תקלה בהודעת האישור ל־ChatGPT אינה מונעת התחלת משימה שכבר התקבלה. פרטי אבחון נמצאים ב־`/api/tasks/{id}/diagnostics` ובהודעת מצב המשימה.
- אימות סיום: בבקשות יצירת PDF/DOCX/XLSX נדרש קובץ שנפתח בהצלחה מתוך תוצאות כלי הקבצים. צילום עמוד או טענה של המודל אינם מספיקים. הבדיקה אינה מוכיחה שלמות תוכן או פריסה תקינה.
- ניווט חדש מחייב כתובת מפורשת בבקשה או קישור שנצפה בתוצאות הדפדפן. בחידוש משימה אחרי כשל, הסוכן חוזר למטרה המקורית ולתצפית חדשה. חידוש handoff מפורש דרך API שומר את אותה משימה ושיחה, בלי לשגר שוב את בקשת המשתמש.
- דפדפן: התאוששות מוגבלת באותה לשונית, חילוץ טקסט/HTML/קישורים/טבלאות עם `browser_extract`, וסקריפט חד־פעמי עם `browser_script`. נדרשת תצפית טרייה; תוצאת סקריפט מחייבת אימות מחדש. כלי הדפדפן הפנימי אינם שולטים בחלון Windows חיצוני.
- PDF: `browser_save_pdf` מייצא כתבה קריאה עם כותרת, טקסט וכתובת מקור. מצב זה אינו כולל תמונות או וידאו. `layout=page` משתמש בהדפסה המקורית; שכבות אתר עלולות לפגוע בפריסה. תקינות מבנה PDF אינה הוכחת איכות חזותית.
- מסמכים: `document_read` ו־`document_write` קוראים ועורכים פעולות מוגדרות ב־PDF/Word/Excel ושומרים קובץ חדש. תמיכה בכיווניות אינה תחליף לבדיקה חזותית של מסמך מורכב; אין OCR מובנה או מנוע חישוב נוסחאות.
- הרחבות: `extension_register` דורש קוד ובדיקה בתיקיית הפרויקט, מריץ את הבדיקה לפני רישום ושומר גרסה ו־hash. `extension_run` מפעיל את הגרסה שנבדקה. זהו קוד מקומי בהרשאות המשתמש, ולא סביבת אבטחה מבודדת. מודל תכנות נפרד ניתן לבחירה בהגדרות מתוך המותקנים.

- חלון Windows עצמאי ב־Qt וממשק HTTP חלופי, בעברית, עם תור משימות, אירועים, השהיה, ביטול ובקשת תיקון.
- Ollama מקומי עם Qwen3.5 4B Q4_K_M, כלים ותמונות; מודל אחד ובקשה אחת בכל רגע.
- קריאה וכתיבה של קבצים בתיקיית המשימה, גיבוי לפני דריסה, PowerShell, בדיקות, Git ו־SSH דרך כלי הפקודות.
- צילום מסך באמצעות MSS; חלונות וקלט Windows באמצעות SendInput; תנועת עכבר, לחיצות, גרירה, גלילה, מקשים וטקסט Unicode. קלט דורש צילום טרי ואותו חלון קדמי.
- קריאה והפעלת פקדי Windows באמצעות UI Automation/pywinauto, כולל לשוניות, שמות פקדים וקישורים כשנחשפים. הדפדפן המובנה מספק בנפרד DOM דרך Playwright; Windows-MCP קיים גם כמתאם אופציונלי.
- SQLite כמקור מצב מחייב ו־Microsoft Agent Framework FileCheckpointStorage עבור checkpoints. מנוע התזמור עצמו הוא Python ייעודי; הוא עדיין אינו גרף Workflow של Agent Framework.
- חיבור MCP מקומי אופציונלי ב־stdio לפיקוח על משימות.
- OpenCode מותקן ומוגדר לספק מקומי. מתאם server API קיים; עבודות הממשק הנוכחי מופעלות במנוע Hub, ולא מנותבות אוטומטית ל־OpenCode. אין שני מתכננים שפועלים על אותה משימה.

## מה נבדק ומה עדיין חסר

ראה `VALIDATION.md` לתוצאות המדויקות. בדיקות סימולציה של קלט אינן הוכחה שמשחק או יישום מסוים מקבלים קלט. אין עדיין benchmark של 50 תרחישים, תמיכה מוכחת במשחק בזמן אמת, בדיקת UAC או מחזורי reboot אמיתיים. המודל קטן, ולכן איכות ההחלטות אינה שקולה באופן מובטח למודלי ענן.

חלון Windows והממשק נבדקו חזותית. כלי `iab` של סביבת הפיתוח נכשל באתחול; בהמשך בוצעה בדיקת שילוב בממשק הדפדפן המובנה של המוצר עצמו. בחירת הגדרות, שמירתן ורענון נבדקו בו, ונבדקו צילומי הממשק. אלה בדיקות נקודתיות, ולא כיסוי חזותי לכל המסכים והאתרים.

## התאוששות

כל פעולה נרשמת לפני הפעלה והתוצאה נשמרת אחריה. לאחר קריסה, משימה שהייתה פעילה עוברת ל־`waiting_user`. פעולה עם תוצאה לא ידועה נשארת `pending` ואי אפשר לחדש עד שמתעדים בדיקה של מצבה דרך `/api/tasks/{id}/reconcile`. אין הבטחת exactly-once מול תוכנות חיצוניות.

משימות שכבר היו בתור ממשיכות כשהשרת עולה. עדיין לא הותקנה משימת Windows להפעלה בכניסה ולא בוצע אתחול של המחשב. הפעלה מחדש ידנית היא דרך ההתאוששות הנתמכת בפיילוט.

גיבוי עקבי: `E:\AI\tools\hub-venv\Scripts\python.exe scripts\backup.py`. לשחזור: עצור את שרת ה־Hub, גבה את תיקיית `E:\AI\state` הנוכחית, והשתמש ב־SQLite backup API לשחזור מהעותק. אין להעתיק קובץ SQLite חי בלי להתחשב ב־WAL.

## גבולות הרשאה

סקריפט ההפעלה מאזין ב־`0.0.0.0:8876` כדי לאפשר את הגישה שהוגדרה דרך Tailscale. השרת בודק Host ו־Origin, וה־API דורש session cookie או מפתח מקומי. רשימת הכתובות המותרות כוללת localhost ואת כתובת Tailscale שהוגדרה. בדיקת Host אינה תחליף להגבלת רשת וחומת אש. ממשק השליטה של הדפדפן המובנה נשאר ב־`127.0.0.1:9223`. המפתח נמצא ב־`E:\AI\state\hub.key` ואינו נשלח למודל. קבצים שמוצגים בממשק אינם מבוצעים כ־HTML.

מצב קוד מאפשר הרצת shell בהרשאות המשתמש. זה **אינו sandbox**: הפקודות יכולות לגשת מחוץ לתיקיית העבודה, למרות שכלי הקבצים מוגבלים לתיקייה. אותו משתמש Windows יכול לקרוא את קובצי המצב והמפתח; מנגנון הסקירה אינו גבול אבטחה כנגד תהליך זדוני באותו חשבון. הגישה המרוחקת מיועדת לרשת פרטית מורשית; אין לחשוף את השירות לאינטרנט הציבורי.

תמונות, תוכן משימות ופלט פקודות נשמרים מקומית. המודל המקומי משתמש ב־Ollama; כאשר חיבור ChatGPT מופעל, שאלות, ראיות, צילומים וקבצים שנשלחים דרכו יוצאים לשירות ChatGPT. טלמטריה של Windows-MCP כבויה במתאם.

## פיתוח

```powershell
cd E:\AI\repos\local-agent-hub
E:\AI\tools\hub-venv\Scripts\python.exe -m pytest -q
E:\AI\tools\hub-venv\Scripts\python.exe scripts\acceptance.py vision
E:\AI\tools\hub-venv\Scripts\python.exe scripts\acceptance.py hub
E:\AI\tools\hub-venv\Scripts\python.exe scripts\acceptance.py windows
```

`install.ps1` מתקין מחדש את תלויות Python מהגרסאות הנעולות, בלי לשנות פרויקטים קיימים. המקורות, הגרסאות ו־SHA256 של הכלים הניידים נמצאים ב־`E:\AI\downloads\*-release.json`.

## חיבור MCP

הפעל מתוך תיקיית הפרויקט:

```json
{"command":"E:\\AI\\tools\\hub-venv\\Scripts\\python.exe","args":["-m","hub.mcp_server"],"cwd":"E:\\AI\\repos\\local-agent-hub"}
```

כלים: get_capabilities, submit_task, get_task, get_events, get_review_bundle, control_task. חיבור לפיקוח חיצוני אינו מוגדר אוטומטית בחשבון Codex או ChatGPT.

## מקורות רכיבים

- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Qwen3.5](https://ollama.com/library/qwen3.5)
- [OpenCode server](https://docs.opencode.ai/docs/server/)
- [Windows-MCP](https://github.com/CursorTouch/Windows-MCP)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/)

רישיונות הרכיבים והמודל נשארים נפרדים. ההתקנה אינה מעניקה זכויות הפצה מחדש מעבר לרישיונותיהם.

## עבודה בזמן נעילה

השרת, המודל, פקודות, קבצים והדפדפן ממשיכים ברקע גם כשהסשן נעול או מנותק. הדפדפן משתמש בפקדים ובטקסט של הדף; אם המנוע המוסתר אינו מספק צילום, התוצאה מציינת זאת ואין המצאה של ראייה חזותית. משימת מילוי ולחיצה אמיתית נבדקה בהצלחה במצב נעול.

כלי window_inspect/window_act מפעילים UI Automation בלי להזיז עכבר. התמיכה תלויה בתוכנה: בבדיקת Qt נעולה שינוי ערך עבד, אבל Invoke על הכפתור לא גרם לאירוע לחיצה, ולכן אין הבטחה לכל תוכנה.

פעולה פיזית דורשת סשן פעיל ופתוח. כשאין כזה, המשימה נשמרת ב־waiting_desktop בלי לשלוח קלט ומשחררת את התור. עם פתיחת הסשן היא חוזרת לתור ומבקשת תצפית חדשה. כפתור עצירה מבטל גם חידוש אוטומטי זה. נעילה אינה כיבוי, שינה או יציאה מהחשבון; במצבים אלה תהליכים אינם ממשיכים כרגיל.

## ממשק פרויקטים וצ׳אטים

הממשק החדש מציג פרויקטים וצ׳אטים בסרגל שמאלי, שיחה ותיבת כתיבה במרכז ודפדפן או קבצים לצד השיחה. הוא פועל באפליקציית Windows ובנייד דרך Tailscale. ניתן להוסיף תיקיות מהמחשב, לחפש שיחות, לשנות שם, לנעוץ ולארכב, להמשיך שיחה, להוסיף תמונות וקובצי טקסט, לשמור הנחיות לפרויקט, לצפות בקבצים ובשינויי Git ולהריץ פקודות PowerShell. בהגדרות ניתן ליצור worktree בענף נפרד לפרויקט Git.

שיחות נשמרות במלואן במסד; עד 12 סבבים קודמים של אותה שיחה מועברים למודל. הנחיות פרויקט משותפות לצ׳אטים שלו; אין טענה לזיכרון בלתי מוגבל או ליבוא אוטומטי של שיחות מ־Codex. התיעוד `docs/UI_CAPABILITIES.md` מפרט את ההבדלים שנותרו ביחס ליכולות המוצר המקורי.

## התכתבות עם ChatGPT ושליטה במחשב

כפתור ChatGPT מאפשר להאזין לשיחה נבחרת בדפדפן העצמאי. בקשות נכתבות בשפה חופשית; הסוכן מגדיר בעצמו את ההודעות הטכניות בין הצדדים. הודעה מאותה שיחה בטלפון מטופלת כשהיא מסתנכרנת לדפדפן במחשב. נדרש שהמחשב, השרת והדפדפן ימשיכו לפעול. ההתחברות נשמרת בפרופיל הדפדפן; תוקף החשבון עדיין נקבע בידי האתר.

מצבי התצוגה הם התכתבות זה לצד זה, או ChatGPT בלבד כשהסוכן ברקע. הבחירה נשמרת להפעלה ולצ׳אט הבאים. שיחת ChatGPT מקושרת לצ׳אט מקומי שמור, כולל הודעות, תוצאות וקבצים. כפתור הדפדפן באפליקציית Windows ממקד את הדפדפן הצדדי; תצוגת הצילום המרוחקת מיועדת לממשק האינטרנט.

בהגדרות יש בחירת שליטה שנשמרת: אוטומטי, שקט באמצעות פקדים ישירים, או עכבר ומקלדת פיזיים. פעולות פיזיות דורשות סשן פתוח. Ctrl+Alt+F12 עוצר את הפעולות. תמיכת הפקדים הישירים תלויה ביישום; התוכנה אינה מבטיחה שליטה בכל משחק או ממשק.

כלי הפתיחה והפעולה ביישומי Windows מחזירים צילום חדש של חלון היעד כשאפשר לצלמו. כשל צילום מדווח במפורש. הסוכן יכול לבקש מ־ChatGPT הכוונה עם צילום חלון היעד. פעולת סגירה נבדקת מול חלונות ותהליכים, ומשימת ChatGPT בלי תוצאת כלי אינה מאושרת כביצוע מאומת. עדיין נדרשת בדיקת התוצאות: המודל המקומי עלול לטעות בהבנת ממשקים ומשימות מורכבות.

ספריית הקבצים שומרת הורדות וצירופים מקוריים, עד 100 MB לצירוף. ניתן להחזיר קבצים וצילומים ל־ChatGPT, להעלות קובץ שמור לאתר או להעתיקו לפרויקט. תמיכה בהעברת אודיו אינה הוכחה לאימון קול או לתמלול; פעולות אלה דורשות כלי מתאים והרצה מאומתת.

## הגדרות מודל, חיפוש כניסה וסיוע חזותי

גלגל השיניים פותח בחירת מודל מותקן, פרופילי מהיר/מאוזן/הקשר מורחב, אורך תשובה, גודל הקשר והגדרות מתקדמות. ההגדרות נשמרות להפעלה ולשיחות הבאות. נתוני זמן החישוב מתייחסים למודל המקומי בלבד; המתנה לאתרים ול־ChatGPT מתווספת להם.

במצב חכם וחסכוני הסוכן פועל בעזרת פקדים וראייה מקומית, ומבקש סיוע מ־ChatGPT לאחר כשלים חוזרים ולאימות סיום של משימות ממשק שהגיעו מהחיבור. במצב סיוע שוטף הוא מבקש ניתוח של צילום החלון אחרי פתיחת יישום ופעולות ממשק במקום להעביר את הצילום למודל המקומי. ההתייעצויות סדרתיות; אין שליחה מקבילית בלתי מוגבלת. כיבוי הסיוע מבטל את ההתייעצות החזותית האוטומטית.

`find_login` מחפש קישורים ופקדים שנצפו בפועל, כולל כתובת הקישור כש־UI Automation חושף אותה, ותפריטי חשבון/כניסה/דואר. הוא מטפל בכפתור סגירה מזוהה בחלונית השייכת לדפדפן, ומזהה גם התחברות בשני שלבים עם שדה מייל וכפתור המשך בכתובת התחברות. אין כתובת וואלה קשיחה בקוד. חיפוש זה אינו מחליף הבנת כל אתר: פקדים שאינם נגישים עשויים לדרוש צילום וקלט פיזי.

`capture_screenshot` מצלם ושומר את ה־PNG המקורי בספריית הקבצים ומסמן אותו לשליחה לשיחה המחוברת. צילום חלון חלופי אינו מדווח כצילום שולחן עבודה מלא. המאזין עוקב אחרי מזהי הודעות וסדר סבבים גם כשהאתר מסתיר היסטוריה ארוכה, והדיווח ממשימה שחודשה משתמש בראיות הניסיון העדכני. ההיסטוריה הקודמת נשמרת לביקורת.

### הגדרות שניתן לשנות

| הגדרה | התנהגות |
| --- | --- |
| מודל | בחירה מתוך המודלים המותקנים ב־Ollama; אינה מתקינה מודל חדש |
| מהיר | הקשר 16K, תשובה עד 512 טוקנים |
| מאוזן | הקשר 16K, תשובה עד 1,024 טוקנים |
| הקשר מורחב | הקשר 32K, תשובה עד 2,048 טוקנים |
| מתקדם | טמפרטורה, זמן השארת מודל בזיכרון וזמן המתנה לתגובה |
| סיוע חזותי | הפעלה/כיבוי, מצב חכם וחסכוני או סיוע שוטף |
| שליטה | אוטומטית, שקטה או עכבר ומקלדת פיזיים |
| תצוגת ChatGPT | התכתבות זה לצד זה או ChatGPT בלבד |

המצב שנשמר בסיום הבדיקות היה פרופיל מהיר, סיוע חכם, שליטה אוטומטית ותצוגה זה לצד זה. הקשר גדול יותר צורך יותר זיכרון ואינו מבטיח החלטות טובות יותר. הגדרות מודל אינן נשמרות באמצע משימה פעילה.

## תיקוני אמינות וביצועים שנכללו

- **פתיחה וסגירה של יישומים:** זיהוי חלון ותהליך בפועל; עצם קיומו של תהליך אינו הוכחה לפתיחה. בדיקת סגירה מול חלונות ותהליכים, ושמירת זהות היישום כדי למנוע מעבר בטעות לחלון המתאם או Codex.
- **לשוניות וחיפוש כניסה:** קריאת כל הלשוניות ואלה שנבחרו; שימוש בחלון קיים במקום פתיחה חוזרת של אותה כתובת באותה משימה, גם אחרי חידוש. דירוג קישורי כניסה, חשבון, תפריט ודואר לפי מידע שנצפה, כולל נתיב בתוך fragment כגון `#/login`. אין הכרה בשדה מייל אקראי כהוכחת התחברות.
- **חלוניות מפריעות:** טיפול בכפתור סגירה מזוהה בחלונית ששייכת לאותו יישום. חלונות שמירה והרשאות אינם מאושרים אוטומטית במסגרת ניקוי חלוניות. חיפוש כניסה מכבד את מצב השליטה שנבחר.
- **צילום וקלט:** צילום חלון קדמי מתוך המסך בפועל כדי להימנע מתוכן Chromium לבן שמוחזר לעיתים ב־PrintWindow; התאמת מזהה צילום למזהה תצפית הנגישות; בדיקת טריות, חלון היעד ונקודת הלחיצה לפני קלט. חלונית בבעלות אותו תהליך נבדלת מחלון זר שמכסה את היעד.
- **אימות תוצאה:** סיוע חיצוני אינו נחשב לביצוע מקומי. לאחר כשל חוזר אפשר לקבל הכוונה, לבצע את הצעד ולבדוק שוב. אימות חזותי סופי של משימות הממשק המחוברות דורש תשובת אימות מפורשת; מספר הניסיונות מוגבל.
- **האזנה לשיחה:** מזהי הודעות קבועים מעגנים את הבקשה האחרונה, גם כשהודעת המשוב נעלמה מהתצוגה. מספור סבבים של ChatGPT יכול להתאפס אחרי רענון ואינו משמש כהוכחה להודעה חדשה. כשאין עוגן מזוהה מופיע מצב המתנה לסנכרון, ללא ביצוע היסטוריה מספק. הבחנה בין בקשת משתמש להודעות שהסוכן שלח בעצמו, ומניעת ביצוע חוזר של מזהה פעולה.
- **שליחה לא ודאית:** בדיקה אם הודעה כבר נשלחה לפי מזהה ותוכן, גם כשהטקסט מקופל ב־Show more; אין שליחה חוזרת אוטומטית של הודעה שתוצאת שליחתה לא ידועה.
- **צילום שביקש המשתמש:** כלי ייעודי לצילום ולרישום הקובץ, בלי להמציא מזהה קובץ מתוך מזהה תצפית. הודעת הראיה אינה חוזרת על בקשת המשתמש כאילו ניתנה מחדש; תוקנה לולאת ״עוד צילום״.
- **מסירת קבצים:** אין צירוף כפול של אותו צילום גם כראיה וגם כקובץ. לאחר חידוש משימה נשלחות ראיות הניסיון העדכני, ולא אוסף צילומים מיושנים. הצלחת המסירה נרשמת אחרי קבלת אישור שליחה, בנפרד מהכנת הקובץ.
- **תקינות שליחת צילום:** תמונת PNG מצורפת חייבת להיטען בהודעת המשתמש ב־ChatGPT לפני אישור מסירה. יש לפתוח את הקובץ המצורף המקורי; קישור נוסף ש־ChatGPT ממציא בתשובה אינו הוכחת מסירה. שגיאה בכלי הכנת הקובץ מחייבת ניסיון תיקון בפועל, ולא רק הודעת "אנסה שוב".
- **סנכרון מהנייד:** לאחר 30 שניות ללא שינוי בשיחה פנויה, המאזין מרענן את אותה לשונית ChatGPT כדי לקבל הודעות שלא הגיעו בעדכון חי. אין רענון בזמן ביצוע משימה, יצירת תשובה, טיוטה לא שלוחה או חלון דו־שיח/תפריט פתוח; הרענון אינו מאפס את מזהי הבקשות ואינו שולח הודעה. זמן זה אינו הבטחת סנכרון של שירות ChatGPT.
- **זמן תגובה:** בדיקת הודעות פעילות והמתנה לתשובת ChatGPT במחזור של כחצי שנייה, צמצום תמונות בהקשר המודל לצילום האחרון, מסלול חיפוש כניסה מקומי ושורת התקדמות חיה. אין הבטחה לפעולה מיידית; זמני מודל, אתר ורשת עדיין משפיעים.
- **ממשק בנייד:** fallback ליצירת מזהה בקשה כשהדפדפן אינו מספק `crypto.randomUUID`, כולל גישה דרך HTTP.

## תוצאות מאומתות

| בדיקה | תוצאה ומגבלה |
| --- | --- |
| בדיקות Python | 93 עברו ב־17.34 שניות; אחרי שינוי דיווח המסירה האחרון עברו גם 19 בדיקות החיבור והראייה הרלוונטיות |
| JavaScript | בדיקת תחביר, fallback למזהים בנייד ובדיקת העברת סשן סינתטית עברו |
| כניסה לוואלה | נסגרה חלונית התרגום ב־Edge; נלחץ קישור `mail` שנצפה באתר; נפתח `https://friends.walla.co.il/#/login` עם מייל והמשך. לא הוזנו פרטי התחברות ולא נוספה לשונית במסלול המתוקן |
| זמן ניווט מקומי | 7.75 שניות בבדיקה זו, בלי זמן הבדיקה החזותית הסופית |
| צילום דו־כיווני | בקשה בשפה רגילה ב־ChatGPT הפעילה צילום אחד; PNG מקורי בגודל 1792×1120 נשלח כצירוף אחד ו־ChatGPT אישר קבלה |
| זמן מסירת צילום | 9.89 שניות מתחילת משימת הסוכן עד המסירה; 18.56 שניות מהבקשה, כולל התשובה הראשונית של ChatGPT. מדידה נקודתית בלבד |
| הגדרות | בחירת סיוע שוטף נשמרה אחרי רענון; מצב חכם הוחזר. לא נצפו שגיאות JavaScript בבדיקה |
| שמירת התחברות | cookies קבועים, cookies של סשן ו־HttpOnly, localStorage ו־IndexedDB נשמרו בין שני תהליכי בדיקה |
| קבצים | הורדה מקורית, שמירת מדיה והעלאה לאתר בדיקה אומתו לפי תוכן ו־SHA256 |
| קלט | בבדיקת fixture קודמת מצב שקט לא הזיז את הסמן; במצב פיזי התקבלו תנועה, לחיצה, מקשים וטקסט. אין להסיק מכך על כל יישום |
| סגירת Chrome | בדיקה אמיתית תיעדה אפס חלונות ואפס תהליכים לאחר סגירה רגילה, ללא סיום כפוי |

ראיות מקומיות ב־`E:\AI\artifacts`: `login-navigation-acceptance.json`, `desktop-share-acceptance.json`, `model-visual-settings-verified.png`, `browser-storage-acceptance.json`, `file-transfer-acceptance.json`, `chatgpt-attachment-proof.json`, `input-modes-acceptance/result.json` ו־`verified-chrome-close.json`. תוצאות היסטוריות מפורטות נשמרות ב־[VALIDATION.md](VALIDATION.md).

הבדיקה החיה האחרונה השתמשה במצב הסיוע החכם. מצב סיוע שוטף נבדק לשמירת הגדרות אך לא בתרחיש חי מלא של כמה צעדים. קליטת הודעה חדשה נבדקה דרך השיחה המחוברת באתר, בלי להפעיל את הטלפון עצמו. העברת אודיו ותמונות אינה מעידה שאימון קול, Photoshop או משחק כלשהו נבדקו. נותרו מגבלות מודל קטן, שינויים בממשקי אתרים, מצב מסך נעול והיעדר בדיקות reboot ועמידות ממושכת.

## מיקום הקוד והמידע

| מיקום | תפקיד |
| --- | --- |
| `hub/engine.py` | תור הרצה, הקשר המודל, התאוששות ואימות סיום |
| `hub/tools.py`, `hub/applications.py` | כלי הסוכן וזיהוי/פתיחה/סגירה של יישומים |
| `hub/desktop.py`, `hub/accessibility.py` | צילום, קלט Windows ופקדי נגישות |
| `hub/login_navigation.py`, `hub/visual_review.py` | חיפוש כניסה ואימות תשובת הבדיקה החזותית |
| `hub/browser.py`, `hub/browser_profile.py`, `hub/desktop_app.py` | דפדפן המוצר, פרופיל קבוע וחלון Windows |
| `hub/chatgpt_bridge.py`, `hub/bridge_controller.py`, `hub/bridge_transcript.py` | שליחה/קבלה, האזנה והיסטוריית ההתכתבות |
| `hub/file_library.py`, `hub/conversations.py`, `hub/store.py` | ספריית קבצים, פרויקטים, שיחות ומצב משימות |
| `hub/model_settings.py`, `hub/preferences.py` | הגדרות מודל והעדפות נשמרות |
| `hub/app.py`, `hub/static/` | API וממשק המשתמש |
| `E:\AI\state` | מסדי SQLite, העדפות, פרופיל דפדפן וקישור לשיחת ChatGPT |
| `E:\AI\files`, `E:\AI\artifacts` | קבצים מקוריים וראיות הרצה |

## רישום גרסאות ושינויים

כל תיקון, עדכון ושדרוג חייב לקבל רשומה ב־[CHANGELOG.md](CHANGELOG.md), עם הגרסה, התאריך, ההתנהגות ששונתה, הבדיקה שבוצעה ומגבלה אם קיימת. שינוי באופן השימוש מחייב גם עדכון README זה. אין לסמן תכונה כמאומתת רק מפני שנוסף קוד.

החל מגרסה 0.3.0 הרישום מרוכז ומחייב. העבודה הקודמת אוגדה ברשומת גרסה זו; לא הומצאו בדיעבד מספרי גרסאות או מועדי שחרור שלא תועדו. מספר הגרסה בחבילה וב־API מסונכרן; תהליך שרת שכבר פועל טוען שינוי גרסה רק בהפעלתו הבאה. כללי התחזוקה נמצאים ב־[AGENTS.md](AGENTS.md).

### MCP task waiting (0.10.0)
Submission waits up to 20 seconds for short tasks and returns observed status. When still active, ChatGPT must continue calling get_task; it must retrieve image/file IDs with get_file. The server cannot force the ChatGPT UI to keep replying. Idle browser listening has bounded timeouts and yields to queued tasks. Only one desktop runtime may own the persistent browser profile.

### Closing embedded tabs (0.10.0)
The agent can close observed tab IDs with browser_close_tabs and verify remaining tabs. Closing every page leaves one blank start tab. Unsaved-work prompts are preserved. Explicit Hebrew/English close requests cannot pass the completion gate on inventory alone. Other phrasing still depends on model planning.

### Global activity and MCP progress (0.10.0)
The composer now has an activity panel across all chats, including remotely submitted tasks, with stage, age of last update, chat navigation and full diagnostics. It polls every 1.5 seconds and retains recent terminal tasks. MCP submit_task emits stage-change progress notifications while its bounded wait is active. Client support determines whether these are displayed; ChatGPT must still poll get_task for longer tasks. Notifications do not create chat messages or continue after the tool call ends.

Desktop shortcuts: desktop_shortcut creates/inspects current-user .lnk files for any existing target, reads back properties, and refuses to overwrite a different target. agent_environment provides the actual launcher path and user identity. These tools are model-independent.

The desktop launcher starts services with -SkipDesktop and then opens one visible desktop instance, avoiding a competing background startup.

Native shells: run_shell supports powershell (default) and cmd. Both run scripts under the current Windows identity, in the task workspace, with recorded output/exit status and full logs. No automatic elevation; fresh noninteractive shell per call, timeout up to 180 seconds.

## 0.9.0 — 2026-11-06
Added task-owned live pipe command sessions (start/read/write/stop), output logs and exit status. Sessions are in-memory and do not survive service restarts. No PTY/full-screen SSH or password input support. The runner polls active sessions instead of accepting a premature final answer. Windows close failures now include actual Win32 codes and remaining windows rather than an ambiguous exception; no privilege bypass or force kill.

## 0.9.1 — 2026-11-06
Reject nested PowerShell -Command wrappers before execution, with corrective feedback. Shell error records are flagged even with zero native exit status; identical failed shell calls stop after two attempts. Runtime identity reports the actual executor PID and elevation, independent of the desktop UI.

## 0.9.2 — 2026-11-06
An explicitly elevated launcher replaces idle non-elevated agent backend, MCP gateway and desktop runtime. Tool subprocesses inherit backend elevation. Active tasks block replacement. Desktop must close normally. This does not elevate unrelated applications or bypass UAC. Shared Ollama services are not restarted.

## 0.10.0 — 2026-11-06
Added actual Ollama memory status and sidebar load/unload toggle beside model name. Direct MCP model_memory_status/model_memory_control work without model inference, including unload_all. Installed models only; no deletion/download. Active agent tasks block memory changes. Future inference can reload a model; other GPU processes are untouched.

Quick model selection: click the model name in the sidebar footer to list installed models with residency and GPU memory. Selection unloads the previous primary model, loads the chosen model, verifies residency and persists the selection for future tasks. On failure the previous selection remains (its memory may already be unloaded). Active tasks block switching; a separately configured coding model remains unchanged. The same switch action is available through direct MCP without inference. Fixed memory-tool registration order before the executable gateway starts.

## 0.10.1 — 2026-11-06
Removed the fixed 30-step task cap. Tasks can continue while working toward completion; cancellation and error handling remain. Two consecutive identical silent shell executions now block the next duplicate with corrective feedback; repeated refusal to change strategy pauses with a concrete error. Empty output explicitly does not prove target absence or success. Prompt guidance prioritizes exact user-provided paths and visible diagnostic errors. Applies independently of model choice.

## 0.11.0 — 2026-11-06
Task diagnostics and MCP responses include observed phase, model step, active tool arguments, last action result, waiting reason, elapsed phase time and polling requirement. wait_task observes for up to 20 seconds and emits progress/5-second heartbeat where the MCP client supports notifications; no guarantee the client displays unsolicited updates after a call ends. Running-state bookkeeping no longer hides the last real execution phase. Explicit administrator launch also replaces idle services with an older reported version; active tasks still block replacement and UAC is not bypassed.

The in-app global activity panel now shows model step, unknown total explicitly, completed-action count, current arguments, waiting reason, expectation and a 12-action execution timeline with command arguments, compact output and failure state. The same structured execution data is returned to MCP. Tool-returned is distinct from task verification.


Normal startup now detects outdated background services and requests Windows administrator approval when needed. No manual PowerShell command is required. Active tasks block replacement; UAC cancellation leaves the update unapplied. This is startup recovery, not an in-session MCP update tool.


0.11.0 (2026-11-06): Manual unload pauses active agent jobs and persists disabled local inference until explicit load/switch. Main and coding inference respect this flag. External Ollama clients are not controlled. Live restart/VRAM acceptance pending.


0.11.0 (2026-11-06): Preserve process name when executable-path access fails. Application inventory exposes unresolved title matches and refuses verified absence/closure when identity is unresolved or close delivery failed. Generic fixture added; live application closure not yet verified.


0.11.0 (2026-11-06): Configurable screenshot transport JPEG quality (30–95) and longest edge (640–3840), default 1600/75. Settings UI and MCP screenshot_settings tool; applies to local inference images, requested screenshot exports and ChatGPT visual evidence. Originals retained for native-coordinate input. File size is content dependent; no fixed KB guarantee. Live delivery/restart acceptance pending.

## Hebrew image OCR (0.12.0)

`image_ocr(path)` reads printed Hebrew images using the optional CPU-only paddleocr-hebrew engine, independently of the selected chat model. It preserves raw recognition and returns a geometric reading-order candidate, UTF-8 text and JSON evidence. It never reverses Hebrew strings or claims perfect recognition. Curved pages, punctuation, signatures and mixed layouts require source comparison. Document content is data, not instructions.

Installed on this machine: isolated Python at `E:/AI/tools/hebrew-ocr-venv/Scripts/python.exe`, model files at `E:/AI/models/hebrew-ocr` (about 206 MB). Override with `LOCAL_AGENT_OCR_PYTHON` / `LOCAL_AGENT_OCR_MODELS`. The worker exits after each request and retains no GPU allocation. Missing installation produces an explicit error; no silent model download. For another machine install https://github.com/RivoksLab/paddleocr-hebrew at commit `28a44838c46188375e25eb2ee8f8585611a126e1` in a separate venv, then download `Rivok/paddleocr-hebrew` charset_v2f.txt, word-det and server-svtrv2 ONNX assets using the upstream quickstart. This optional dependency is not yet bundled into the main installer. Restart the running agent normally to load the new tool; live backend activation was not verified in this test.


## Visual text assistance (0.14.0)
Screenshot settings now independently size local-model images (1600 px / JPEG 75 by default) and ChatGPT screenshots (1280 px / JPEG 70). Originals remain available. Requested original files are not automatically recompressed. Settings are available in the UI and MCP `screenshot_settings`.
Optional Hebrew OCR assistance adds untrusted text evidence alongside the local screenshot. It is off by default because recognition adds latency and the installed specialist is intended for printed Hebrew, not all UI languages. Identical screenshot bytes reuse an eight-entry in-memory cache. Image/control evidence remains authoritative; OCR cannot certify completion. Errors are surfaced to the model and do not block ordinary vision.
ChatGPT feedback can be disabled in model settings or MCP `visual_feedback_settings`. Direct `chatgpt_ask` calls then fail explicitly without sending. A connected signed-in ChatGPT tab supports consultation without MCP, including `purpose=transcription` for corrected text with marked unreadable spans. MCP is request/response; remote callers must poll and provide follow-up feedback, not assume unsolicited server-to-ChatGPT calls. Fully automatic remote OCR correction and both live transports have not been end-to-end verified in this release.

### OCR visual cross-check limitation
Successful image_ocr calls supply both OCR text and source pixels to the local model. This does not guarantee accurate transcription: the real Qwen 3.5 4B Hebrew rental-document test retained reading-order and character errors with ChatGPT feedback disabled. Preserve the original and review uncertain text.

### Configuration through natural-language ChatGPT requests
User-configurable changes must be exposed through MCP as well as the UI, using shared persisted settings. For example, ask to enable OCR, disable ChatGPT visual feedback, or lower image quality. The calling chat translates ordinary language into screenshot_settings / visual_feedback_settings calls; users do not need to supply JSON. These tools exist in the current source; availability in an older running gateway is not implied.

### Locked Windows sessions
Existing-image OCR, file analysis and shell operations do not inherently require the physical desktop. On DesktopUnavailable the runner offers one background replan before waiting. Missing attachments must be reported as missing files. Physical mouse/keyboard input and full desktop capture are not guaranteed while Windows is locked; compatible browser/application background APIs are separate capabilities. No new setting is introduced.

Background recovery is visible in shared task status and MCP: background_replan / background_replanning. Deferred desktop attempts are not successful operations.

## OCR development acceptance (unreleased)

Document reading and live UI verification are separate acceptance targets. `image_ocr` supports fast/thorough recognition and optional normalized crops through the shared tool catalog. OCR text and alternative readings supplement source pixels; they do not prove a desktop action succeeded. Current local Qwen tests still show letter errors and repeated-crop loops; this development change is not reported as complete or deployed.

### Screenshot regions and background windows (development)
Request a full desktop, identified application window, or a region of either through the agent chat/MCP. Regions use source-image pixel offsets [left, top, width, height], not compressed preview coordinates. Source evidence remains saved. A background window uses PrintWindow when physical desktop access is unavailable; applications may reject or stop rendering. Files/OCR and shell operations do not require desktop capture. This does not provide universal GUI control while Windows is locked.

Tabbed application recovery (development): selected tabs remain visible in compressed model context. The executor blocks repeated identical input on an unchanged screenshot after two attempts and directs the agent to inspect actual controls. UI Automation click maps to Invoke. Existing documents and save/discard prompts must be preserved. These shared mechanisms apply across applications, not just Notepad.

Version 0.14.0 adds window_new_document to the desktop agent tool catalog, available through natural-language MCP tasks and local chat. It supports editors exposing a New-tab button and readable UIA Document, verifies a single new blank document, enters up to 4000 characters once and verifies exact text. It requires interactive desktop input. Unsupported editors fail explicitly; this is not universal application compatibility. No new persisted setting is introduced.

## Development: APC project intelligence

The in-development context service adds project indexing, source search, annotations and recovery through shared HTTP/MCP/task tools and a project dialog. Coding tasks record context bootstrap actions. Current implementation and limitations are tracked in [the implementation ledger](docs/DEVELOPMENT_IMPLEMENTATION_STATUS.md); this does not claim live deployment or completion of the larger technical plan.

Continuation audit (2026-11-07): [technical plan section 15](docs/TECHNICAL_IMPLEMENTATION_PLAN.md#15-continuation-audit-against-source-and-original-chat--2026-11-07) records the verified APC provenance and remaining indexing, context-budget and integration gaps. Missing MCP tool descriptions are repaired in development source, but the background-index draft is not ready for activation. Current connector discovery in this chat does not expose the new tools. Do not restart production merely for this documentation update.

Development queue semantics: background-index settings control periodic work only. Changing them neither starts a scan nor cancels an explicit queued/running request. Concurrent refresh requests are retained for a subsequent scan. This source change is fixture-tested, not production-activated.

Development context UI now separates readable results from technical JSON and exposes shared background-index settings. Local tasks can request/status/configure their current project index. Source freshness currently favors full content verification over no-op scan speed; not yet production-activated.


Development preview: code tasks can use `candidate_create`, `candidate_inspect`, `candidate_patch`, `candidate_diff` and `candidate_test`. Candidates preserve the live project and bind patches/tests to file hashes and revisions. The same operations are registered in HTTP/MCP source, but a running gateway must load this revision before discovery; public connector validation is pending. Tests execute trusted project code under the current account with a filtered environment, not an operating-system sandbox. No activation/rollback is implemented by these tools.


Development source now includes frame-bound virtual browser pointer controls, isolated browser test runtime ports, Git status/clean worktrees and typed APC file metadata import. These are not a production release. Non-file APC entities report unsupported status; entity hashes are not treated as file hashes. Indexing honors Git ignored files and aborts atomically on read/budget failures. Local/HTTP/MCP registrations share services; public connector discovery remains to be verified. See VALIDATION.md for actual evidence and remaining limitations.

Model installation controls (development): open the model selector, enter an Ollama name and choose Download. Durable status, cancel and explicit resume are also exposed by model_catalog/model_install/model_install_cancel in local tools and MCP registrations. Installation does not select or load a model; Hugging Face support remains pending. Model memory status includes durable resource ownership. Inference refuses to evict unknown external resident models. New source requires a runtime restart to activate; public connector use is not yet verified.

Development candidate_repair can delegate selected files to an installed coding model in a patch-only child process, validate scope/hash/revisions and run unchanged acceptance tests. Test evidence is visible in development review. This does not activate code and is not an OS security sandbox. Existing project indexes are reused for new tasks; exact source hashes remain mandatory before edits.
Development continuation (Unreleased, 2026-11-07): the shared model catalog now searches public Hugging Face GGUF repositories, shows license/revision/file sizes and installs supported single-file models through Ollama. Local tools, HTTP, MCP registrations and the quick-model UI share the same durable jobs. Private/gated repositories, projection-only files and split shards are explicitly unsupported. Revision is recorded and checked again after downloading, not pinned by this adapter. Installed digest verification does not establish inference quality. No automatic selection or GPU load occurs. Production connector deployment remains pending.


### Development: conversation continuity and product shell
Conversation requests/results/actions/events remain in local SQLite without age-based expiry. The model receives recent conversation plus explicit continuity notes, and can read older exact evidence with conversation_history. HTTP and MCP expose the same chronological paging and revisioned notes; the UI opens them under the conversation menu. Notes are bounded to6000characters; full historical records are not deleted by that bound. Model context and machine storage remain finite. Historical success is not a fresh observation.
The development UI groups settings by purpose and keeps detailed diagnostics behind expandable controls. Plugin/skill installation and full native-browser extension support are still being implemented; no claim of complete product QA or public connector activation.

Embedded-browser extension management is under development: local Manifest V3 folders/ZIPs install disabled, with explicit enable/disable/uninstall and status through the desktop manager and MCP adapters. Chrome Web Store compatibility is not promised. The Chrome transfer helper transfers one site session, not an entire profile; some sites require a fresh login. These source changes have not been activated in production.

Optional conversation-memory review is off by default and configured per conversation in the memory dialog or conversation_memory_feedback_settings MCP tool. Browser requests use the connected ChatGPT chat; MCP requires its caller to inspect the pending packet and submit a correlated reply. Feedback is stored separately, does not rewrite history and cannot verify current computer state. These adapters still need real ChatGPT acceptance. Native extension enabling is currently blocked after a Qt runtime crash in isolated QA; installed extensions remain disabled.

Long-history storage remains independent of the finite model context. New turns read bounded recent context and can retrieve older evidence through chronological history; a no-match literal search is explicitly labelled before returning chronological fallback. Optional reviews require a verbatim source quote and cannot silently turn a guessed source into an accepted fact.

Memory feedback delivery: MCP task observation exposes bounded pending review packets and yields promptly for the calling model to answer against its available original conversation. If it lacks that context, it must answer unavailable; local history remains authoritative evidence. This new MCP source path is not yet activated/accepted through the public connector.

- Conversation viewport now loads 30 chronological turns per page without internal model message arrays. Earlier pages and return-to-latest retain original history. Tool evidence loads on expansion instead of every refresh. Ordinary chats no longer materialize full history for empty bridge correspondence. Native Hub implementation, not APC-derived.

- Added durable decision anchors: exact user-request quotations with source hashes, optional later-source supersession, retained old versions and paged access. Shared local tool, HTTP/MCP functions and memory-dialog source inspection. Labels/supersession remain annotations, not fresh authority. Included recent anchors and current request ID in model continuity packets. Initial real Engine trial failed corrected-source selection and recall; failure retained at conversation-anchors-engine-20261107/acceptance.json; rerun in progress. Native Hub code, not an APC port.

- Browser memory feedback now sends review_id and accepts only a structurally valid reply with that exact ID. Missing/mismatched IDs and malformed values become unavailable, never confirmation.

- Retained ChatGPT feedback now enters future conversation context with source quotations and current pending/reviewed/stale status. Added paged feedback history through shared local/HTTP/MCP services and the memory UI. Final task status rereads the persisted review instead of repeating a stale action snapshot. Contradictions remain separate evidence; originals are never overwritten.

Memory feedback enable/context flags require actual booleans at the shared service boundary; ambiguous strings are rejected without saving. A missing-context reply never confirms a recollection. Live manual ChatGPT feedback and subsequent local Engine consumption were observed in isolated acceptance; automatic browser dispatch and the deployed public MCP connector remain separate, unverified gates. These memory components are native Hub work, not APC-derived.

Conversation pagination remains valid after inference-result compaction: omitted records are available on the next page, with source quotations kept intact. Durable storage does not guarantee correct recall: the 1,000-turn/26-anchor real Engine retrieval test currently fails, returning an unrelated historical acknowledgement. This long-history retrieval gate remains open; history retention must not be described as an unlimited effective model context.

Follow-up: automatic indexed decision retrieval now supplies relevant original quotes and linked corrections to each Engine request, with source hashes and a `conversation_sources_retrieved` audit event. The earlier failed1,000-turn case passed after this change (11.30s). Matching is lexical, not proof of semantic relevance; paraphrases, unanchored decisions and incomplete correction chains still require chronological/source tools. The fixed input remains bounded, while original history has no expiry. This narrow success does not establish unlimited effective context or activate the public connector.

Follow-up context labels old assistant replies as historical reports with original task IDs and states; it does not treat previous prose as current verified facts. The anchored scenario passed independent answer review after this change, but an unanchored Hebrew paraphrase still failed literal retrieval. Do not interpret these improvements as general long-conversation completion.

History search now combines exact matches with FTS5 word candidates from original user requests. Each approximate candidate is labeled and must be checked against original text; source roles distinguish user goals from assistant reports. This fixed retrieval in the unanchored Hebrew case, but real-model answer review still found reversed current/previous values and incorrect speaker attribution. Retrieval success is not answer validation. The current source does not guarantee reliable semantic continuity for arbitrary conversations.

Historical-answer verification now derives a separate answer from original user sources and reviews source-bound claims using the already selected local model. Pure history-reading tasks return that reviewed source-derived answer; mixed-action tasks retain their own result subject to review. Up to three failed reviews lead to an explicit unverified result, with logs and original history intact. This does not contact GPT or load a second model. Model review is fallible and remains subject to independent acceptance. PLAY connection selection/favorites/pane-independent linking are newly planned, not deployed features.

### PLAY conversation connections (development, 2026-11-07)
The ChatGPT dialog offers PLAY (existing signed-in embedded browser conversation) and MCP. PLAY bootstrap includes a versioned, hashed operating contract and the actual local tool catalog. A new-conversation action creates a separate local chat and sends the bootstrap; existing conversations can be connected separately. Sending instructions is recorded as sent, not as verified remote understanding.
Local chats retain a PLAY/MCP preference, favorite flag and exact ChatGPT conversation URL in SQLite. Favorites and preferences are exposed through the same HTTP and MCP paths (`chatgpt_conversation_connection`, `chatgpt_favorite_conversations`). Saving a URL does not authenticate or connect. Selecting a linked PLAY chat attempts restoration and reports failure visibly; MCP selection opens no browser. Active/uncertain handoffs must be stopped/reconciled before relinking, and another local chat's remote link cannot be silently reassigned.
Closing the connection dialog is separate from stopping the listener. Hiding a browser pane must retain its underlying page/process; actual hidden-pane transport and public MCP acceptance remain release gates. Claude/DeepSeek adapters are not implemented. These additions are native Hub code, not APC reuse.

2026-11-07 update: added native AI connection catalog/cards for ChatGPT (Web PLAY/MCP), with Claude/DeepSeek explicitly not implemented. Reviewed APC browser/local-bridge candidates in docs/APC_BRIDGE_REUSE_REVIEW.md and manifest; no bridge code port claimed. Latest44 focused tests passed13.00s before connector catalog addition. Live isolated PLAY setup reached loading/not-ready error; fixed visible opening/attention status and45-second setup bound. Signed-in native bootstrap remains unverified.

### Browser presentation and connection checks (Unreleased, 2026-11-07)
The native browser uses compact navigation controls and a light, explicitly painted toolbar. Login transfer and extension management remain under the three-dot browser menu; their presence does not imply every extension is supported. Long tab/model names are elided rather than overflowing; hover reveals the full model name. Browser viewer input waits for frame capture and does not automatically replay failed mutations.
A ChatGPT connection check now distinguishes a visible login requirement from a page that is still loading. The latest check remains visible during status polling. Sign in within the agent's own browser profile when required; saving a conversation URL does not sign in, and these changes do not copy authentication from another browser. A successful probe is not proof of sent/acknowledged PLAY instructions. Production activation and signed-in automatic acceptance remain pending.

PLAY stop/restart retains unconfirmed outbound work. Before switching the remote conversation or starting a fresh listener, reconcile the pending delivery in the original conversation; the controller does not silently discard or automatically resend it. Local access to that original conversation remains available.

New PLAY conversations may initially have a temporary ChatGPT URL. The bridge adopts the permanent URL only with same-tab and matching outbound-message evidence, preserving the original local conversation. This development behavior still awaits a post-fix live acceptance run.

PLAY reports why no message was sent: sign-in required, unavailable composer, generation in progress, or an existing draft. Preflight blocks preserve drafts and are distinct from uncertain submission; the latter must be reconciled before retrying.
Connection probes distinguish a connected account from readiness to send: draft_present and generating are exposed without draft text, and send_ready is false while either blocks sending. UI displays the specific observed blocker.

Connection probe draft_source is present only for an exact recorded local-agent outbound message. It identifies the source local chat/message and delivery status without exposing draft text. This diagnostic does not clear a draft or authorize resubmission.

PLAY includes saved drafts: stop listening, select local chat, archive current draft before clearing, or list/restore saved drafts. Restoration requires the original URL and an empty composer. Copies remain in local SQLite; no text is sent. Same operations are exposed through MCP chatgpt_saved_drafts. Development feature, public deployment/live acceptance pending.

Draft clearing preserves the original copy first and verifies the empty composer. Unchanged Qt background text has one targeted keyboard fallback. Restoration currently reports a verification mismatch if the rich-text editor inserts additional paragraph breaks; the saved original remains available.

While PLAY is listening, browser controls wait briefly for its read-only observation to finish. Actual task execution still owns browser input; a task starting during the wait cancels that input before sending it.

PLAY protocol v2 explicitly distinguishes its local agent instance from any separately installed MCP connector. The reply JSON is the selected transport; changing transport requires user selection. This instruction still requires live provider compliance verification.

PLAY recovery recognizes a unique new outbound-message receipt after transport failures without resending. Desktop tasks start with a bounded core tool catalog and can enable persistent task-scoped groups with tools_enable; this avoids sending the entire catalog to small-context models. Existing browser conversations are chosen explicitly from the tab picker.

PLAY uses keyboard activation of the enabled send control and verifies a new message receipt. Stale idle pages can refresh while waiting for a reply; active generation and drafts prevent refresh. The browser viewer permits frame observation during reply waits while preserving input exclusion.

Memory feedback retains the original source and the remote review separately. For memory-only review tasks the final feedback status and evidence are rendered from the stored review, not reinterpreted by the local model. A historical report or confirmed recollection does not establish current machine state.

## Project folder binding and PLAY development — 2026-11-07 (Unreleased)

A conversation can be reassigned to an existing folder through the project selector, POST /api/chats/{chat_id}/project, MCP bind_chat_project, or the local project_bind tool. History and historical task workspaces are retained. Binding takes effect on the next task; external changes while a task is active are rejected. The active local task may prepare its own next-turn binding and records an audit event.

Desktop and code file tools accept explicit absolute paths outside the project folder using the existing Windows account permissions. Relative traversal remains rejected; inspect/browser modes remain scoped. This is not elevation or a promise to access locked/protected files. Candidate patch operations retain their separate candidate boundaries.

PLAY desktop tasks can enable the development tool group (index/search/Git/candidate creation, reads, patches, tests and diffs). This reuses the existing development implementation, not a new runner or APC port. On feedback transport timeout the controller reconciles observed delivery before any resend; unknown delivery remains pending rather than replaying work.

MCP source now exposes bind_chat_project. A running gateway must reload this version and client tool discovery must refresh before the public connector shows it. Public discovery and end-to-end acceptance are recorded separately in VALIDATION.md; source changes alone are not deployment evidence.

### Project continuation repair follow-up — 2026-11-07 (Unreleased)

Candidate development now accepts code and desktop/PLAY tasks consistently across local tools and the HTTP/MCP API. A later task in the same persistent chat and same project can inspect, read, test and patch its existing candidate; unrelated chats remain rejected. Candidate responses include the actual isolated `candidate_path` separately from the original `source`. Large manifests are summarized only in model input, with full evidence retained in action logs. File reads return continuation offsets instead of overflowing the model context. These changes are native Hub work, not copied APC components.

The live audit instance on port 18984 has loaded the fixes. The public ChatGPT MCP connector still addresses a different instance/database: local gateway verification is not proof of public deployment. No source candidate has been activated or production release published.

Follow-up: the live 4B run initially repeated tool enabling/inspection because only its latest tool group fit inference input. A bounded factual ledger of successful tool names now survives context compaction without changing the original objective or durable history; candidate Git detail is summarized separately. After reloading and resuming the same task, actual candidate_read and paginated read_file calls completed and task519a0e529fb44622982e250c38872df2 reached waiting_review. This verifies resumed execution, not the correctness of every claim in its generated summary or completion of the entire development plan. PLAY result evidence now also includes candidate/project/context tool results.

### Supervised code execution — 2026-11-07
The shared PLAY/MCP director contract now assigns map retrieval, task decomposition and evidence review to the supervising model. It requests focused indexed sources/related tests and delegates candidate repairs to the configured coding model. New MCP `coding_model_settings` reads/changes the same persisted coding model as the UI without replacing the general/vision model. In the audit instance the previous coding_model was empty; it is now saved and read back through MCP as `qwen2.5-coder:7b`. This confirms configuration, not yet a completed Coder repair. Candidate/project/context actions are included in PLAY feedback. Resuming an existing handoff restores its authorized objective if pause handling had cleared it.

Regression run after context/progress fixes: 353 passed in92.35s. Subsequent supervision changes:52 focused tests passed, one protocol ordering assertion failed and was fixed by retaining the original transport rule first; the protocol/API rerun passed3 tests. Final combined verification follows. Public MCP deployment remains unverified.

### PLAY delivery recovery (Unreleased)
The bridge persists preparation separately from submit activation. After interruption it can finish an unchanged agent-owned draft before any submit attempt, or recognize a new matching receipt. Changed drafts and uncertain post-submit outcomes are preserved rather than resent. This update is currently validated on the isolated audit instance, not the public MCP deployment.

### Continuous director recovery (Unreleased)
PLAY feedback includes failures as actionable evidence under the existing objective. ChatGPT may propose a corrected step; human pause/cancel still stops execution. This does not authorize replay of uncertain writes or bypass approval. Source lookup refs and continuation lines are retained in bounded inference context; full evidence stays in SQLite. End-to-end self-repair acceptance is in progress, not a released autonomous-upgrade guarantee.

The models tool group exposes read-only model_memory_status for resident models, VRAM and recorded leases. A completed Hub inference adopts its selected warm model into the managed workload so the coding worker can switch models. Unknown other models are not automatically evicted.


Development checkpoint (2026-11-07, unreleased): a real ChatGPT Web PLAY director/Qwen2.5-Coder repair round trip now has recorded passing tests and director review. Code integration is separate from deployment. Diff compaction preserves changed-file counts/path summaries when patch details are omitted; full evidence remains in task history. See VALIDATION.md for measured results and remaining public MCP/upgrade limitations.
