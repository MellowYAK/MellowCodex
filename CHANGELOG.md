# 0.14.1 — 2026-11-07

PLAY conversation recovery and directed execution:

- Restore the exact remote conversation linked to the local chat after a missing tab, load failure or service restart. A different visible browser tab cannot silently move the listener.
- Persist each chat's message cursor, objective, action IDs and pending-send state. Stop/resume continues the same session without duplicate connection instructions; a new chat is linked after its first observed send creates a conversation URL.
- Execute the director's current step within the overall human authorization, returning observed evidence before accepting the next step. PLAY supports an explicit execution mode, including code.
- Avoid blocking a feedback status notification behind an active model inference lock. Known conversation-load failures have bounded retries and preserve uncertain sends.
- Validation: 64 focused bridge/transcript/protocol tests passed. Real Web PLAY with Qwen3.5:4b completed two separately directed read_file steps; ChatGPT received both tool results, issued the second step and reviewed the matching versions. Restart and UI stop/resume preserved the original chat and action/message cursors. The earlier overbroad execution trial failed and is retained in the audit.
- Scope: verified in the isolated running app on port 18984. This is not public MCP deployment, autonomous Ember semantic acceptance or a guarantee for every website/model. These changes are native Hub code; no additional APC source was copied.

# 0.14.0 — 2026-11-07

Shared native-editor workflow: observed New-tab control, asynchronous tab-creation verification, blank-document guard, paced Unicode typing, real newline keys, exact UIA readback and fresh screenshot. Exact-name controls and selected-tab context preservation reduce wrong-target actions. Repeated unchanged physical input is blocked. Region capture and background-window fallback are included; arbitrary locked desktop GUI operation is NOT verified.

Live acceptance 09adc2beab4c447194821c52472bdfa5: three Hebrew jokes, text_verified true, screenshot visually inspected, two tool calls, 16.89 seconds. 20 focused tests passed. Not validated across all applications. Earlier development failures remain recorded below.

## Unreleased — 2026-11-07

- PLAY associates replies with the preceding rendered user message before falling back to a turn key. ChatGPT can group consecutive status/result messages under the status turn key; this previously left delivered results waiting indefinitely. Live isolated delivery, answer ingestion and return to listening verified. Native Hub change, not APC-derived; not deployed to production.

- Browser-frame observation can run while PLAY awaits a reply (input remains blocked); bounded idle-page refresh also runs while waiting for a reply, preserving active generation and unsent drafts. 35 focused bridge/access tests passed8.44s. Native Hub changes, not APC-derived.

- PLAY submit uses keyboard activation of the observed enabled button instead of a synthetic JavaScript click. Live Qt testing found the latter could leave the result in the composer; receipt verification still prevents false delivery claims. 32 bridge tests passed7.70s; new live automatic delivery pending.

- Native Hub PLAY repairs: explicit existing-tab picker; bounded desktop tool catalog with on-demand groups; negated tab-close instructions no longer demand closure; wait for delayed submit controls; reconcile confirmed outbound receipts after generic transport failures and return consumed replies to idle without replay. These changes reuse no APC code. Isolated live acceptance remains in progress.

PLAY protocol v2 explicitly routes local-agent requests through reply JSON rather than an installed MCP connector, which may target another instance. Live acceptance exposed that cross-transport ambiguity; revised protocol live acceptance is pending.


- Empty PLAY conversations now anchor incoming requests to the confirmed bootstrap receipt. Recovery uses that receipt only when no human cursor exists; missing established cursors remain blocked against historical replay. Added first-request regression;28 bridge/access tests passed5.52s.

- Human browser controls now serialize behind idle PLAY observations instead of reporting a false active-task conflict. An actual task or response handoff still blocks input, including when it starts during the wait. Shared frame/input/tab endpoints use one guard. Native Hub implementation, no APC code copied.

- PLAY draft archive now verifies clearing and, only if the same archived text remains unchanged, uses a targeted select/delete fallback for Qt background editors. Status notifications render inside open dialogs. Native Hub implementation; no APC code copied. Live archive clearing passed; rich-text restoration adds blank lines and remains explicitly unverified.

- Repaired native embedded-browser chrome: paint the custom widget background, remove inherited dark desktop styling, use compact accessible navigation controls, retain login transfer/extensions in an overflow menu, and elide long tab titles. The account/model footer now uses a stable grid and full-name tooltip instead of wrapping model names one letter per line.
- Serialized browser viewer controls with frame capture; tab selection waits for the current capture. Failed mutations are not automatically replayed. ChatGPT connection probes detect a visible login requirement and persist that observation during status polling without clearing uncertain outbound work.
- Validation: 58 focused tests passed in 16.51s; JavaScript syntax and Python compilation passed. Offline native Qt rendering passed at widths 480/820; actual IAB checked account layout at width 700, tab switching and persisted login-required feedback. Production was not restarted; signed-in automatic PLAY acceptance remains pending. Native Hub fixes, not copied APC bridge code.

- Added bounded same-model source-only extraction and answer review for historical claims, exact citation validation and logged review attempts. Pure history-reading tasks use a separately source-derived answer after review rather than carrying forward an unsupported draft. This is local verification, not remote GPT and not independent proof; initial review trials failed semantic validation and are retained. Added PLAY/MCP linked-conversation requirements to the active plan, not claimed implemented.

- Conversation history now includes indexed token candidates from original user requests alongside literal matches, with explicit match types and source roles. This finds unanchored decisions when a phrase differs and keeps chronological pagination stable even when later questions match exactly. Existing requests migrate once; triggers track changes. Real Engine retrieval succeeded but whole-answer reviews failed attribution/ordering; not complete semantic acceptance.38 fixtures passed27.47s before role labels;20 conversation/context fixtures passed17.33s afterward.

- Recent assistant replies now enter follow-up context as source-identified historical reports, explicitly not verified current state. Original user requests/replies remain unchanged in storage. Real1,000-turn anchored recall e passed independent whole-answer review in12.14s; unanchored paraphrase test still failed29.11s. Schema errors no longer instruct window focus for non-visual tools. This is native Hub continuity work, not APC-derived.

- Added SQLite FTS5 selection of source-bound decisions for the current request, including linked corrections in either direction and source-change checks. The Engine receives bounded original records automatically and logs their IDs/hashes; all history remains retained. Existing anchors migrate once; triggers maintain the index. Native Hub implementation, not an APC port. Real Engine recall over1,000 synthetic turns/26 anchors passed in11.30s after two retained failures.47 focused fixtures passed27.29s; public connector and broader semantic coverage remain unverified.

- Conversation result compaction now preserves whole source records and moves pagination cursors to the last retained record, preventing skipped history/decision/feedback entries. Anchor and feedback pages expose record cursors. Added real Engine long-history acceptance with 1,000 synthetic turns and 26 anchors: both initial and retrieval-guidance trials failed semantic recall; failure evidence retained, not a completion claim.

- Memory feedback now rejects non-boolean context/enable flags in the shared service, preventing strings such as `"false"` from becoming confirmation or enabling remote review. Rejected replies remain pending and preserve source history. Validation: 17 memory-review tests and 20 API/MCP-wait tests passed; production activation and automatic public-connector acceptance remain pending.

- Added revision/epoch fenced director guidance with required-tool evidence, candidate review UI and strict legacy tool-envelope normalization. Initial model omissions remain documented; full-plan QA/release pending.

- Development candidate testing now records revision-bound output, timeout and source verification; candidate diffs and shared HTTP/MCP endpoints added. Real agent fixture repair passed; public deployment and full QA/QC pending.

- Development prototype: APC-inspired candidate source separation, hash/revision checked staging, typed patch contracts and task-bound events. Three fixture tests pass; not yet exposed or activated as a complete development workflow.

- Development: pinned required project constraints, content-checked refresh, missing-root protection, local indexing tools and readable context UI with background settings. See implementation ledger for fixture and real Engine evidence; UI/public connector acceptance and activation pending.

- Index queue development fix: background settings no longer enqueue refreshes; generation tracking preserves refresh requests arriving during active scans. Shutdown waits for the owned scan thread before returning its job to the queue. 11 isolated context/indexing tests passed; production and live-client acceptance pending.


- Reconciled the transferred MellowCodex plan against the original Ember Table-titled chat, pinned APC sources, backup hashes and full historical action evidence. Section 15 records reproduced indexing/context gaps and implementation gates; the larger plan remains incomplete.
- Completed English/Hebrew/Russian descriptions for project_index, project_index_status and project_index_settings, fixing a KeyError during MCP registration. Before: 35 passed, 1 failed; after: 36 focused tests passed and isolated gateway import succeeded. No production restart, public connector verification or release performed.

- In development: APC-inspired project indexing/search, persistent multilingual annotations, source handles and recovery context, shared HTTP/MCP/task tools and project UI. See `docs/DEVELOPMENT_IMPLEMENTATION_STATUS.md` for evidence and incomplete acceptance; not yet deployed.

- Document OCR: optional focused crops, thorough recognition with alternative word candidates, slanted-row reconstruction, and source pixels returned to the local model. These remain under acceptance testing.
- Model context retains longer OCR text and artifact references without duplicating raw transcription; image budgets count each image. Read-only access to the current task artifacts allows retrieval of full text.
- Actual Qwen acceptance remains incomplete: a 44.2-second run produced readable clauses with a remaining letter error; the latest two-recognizer run repeated crops and timed out at 180 seconds. No ChatGPT feedback was used.
- Separate acceptance targets remain document transcription and visual action verification in live applications. Live locked-session GUI operation is not established by document OCR.

## 0.13.4 — 2026-11-07

- Shared task status now exposes background replanning to UI and MCP; deferred desktop operations are labeled deferred rather than returned.
- Added background OCR acceptance harness: injected first desktop observation/failure, then real Qwen and real file OCR. This is controlled failure testing, not a real Windows lock test.
- Live hub and MCP were observed at 0.10.5 before activation attempt. Do not equate source version with deployed version.

## 0.13.3 — 2026-11-06

- DesktopUnavailable now permits one background replanning turn before waiting for the desktop, instead of immediately blocking the entire task. Unexecuted calls are identified; physical input is not replayed automatically.
- Shared runner and MCP instructions distinguish existing-image OCR/file analysis from physical desktop capture and missing attachments. No lock bypass or universal locked-session GUI support is claimed.
- Added a mocked desktop-isolation OCR regression. Live locked-session acceptance and service activation remain unverified.

## 0.13.2 — 2026-11-06

- Recorded mandatory natural-language MCP configuration parity in AGENTS.md and README: shared persistence/validation, readable settings, and honest activation status for future changes.
- Source inspection confirms OCR/compression and optional ChatGPT feedback are exposed by screenshot_settings and visual_feedback_settings. Documentation-only update; no live MCP invocation or deployment performed.


## 0.13.1 — 2026-11-06

- Successful image_ocr calls now attach the original image through the configured local image transport to the next model turn. OCR remains supplementary, untrusted evidence. This applies to all supported local models and workspace images.
- Added scripts/ocr_agent_acceptance.py for real local task-runner document acceptance, retaining actions/results in an isolated persistent store.
- Actual Qwen 3.5 4B test with OCR on and ChatGPT feedback off: 23.39 seconds after image delivery fix (20.58 seconds before). Recognized a rental agreement but retained character and reading-order errors in clauses 16–17; full transcription accuracy did NOT pass.
- Running service observed at 0.10.5; this acceptance used the updated on-disk engine, not that older service.

## 0.10.3 — 2026-11-06

- Normal launcher detects outdated background services even without elevation and requests Windows administrator approval automatically. Cancellation stops startup with an explicit error instead of silently using stale services. Active tasks still block replacement.
- Live activation remains pending; ChatGPT cannot approve Windows UAC.

# 0.7.0 — 2026-11-06

- Generic desktop shortcut creation/inspection with target readback, idempotency and conflicting-target protection.
- Runtime identity/launcher discovery prevents guessing an agent process name. Shared PowerShell guidance corrects CommandLine inspection and empty-output inference.

# 0.6.0 — 2026-11-06

- Added global activity panel for remote and local tasks, recent outcomes, chat navigation and diagnostic details.
- Added MCP stage notifications during submit wait; notification failure does not fail execution. Client rendering and continued polling remain client-dependent.
- VS Code task investigation: initial shell timeout; follow-up used a username as command/process name and empty outputs, so it did not establish installation availability. No VS Code configuration changed by this fix.

# היסטוריית גרסאות — Local Agent Hub

כל תיקון, עדכון ושדרוג נרשמים כאן. הגרסאות מתייחסות לקוד; זמני בדיקות הם תוצאות שנמדדו ואינם התחייבות לביצועים. העבודה שקדמה להתחלת היומן אוגדה ב־0.3.0 לפי הקוד והראיות הקיימים, ללא המצאת היסטוריית שחרורים.

## 0.5.2 — 2026-11-06

- Added browser_close_tabs: validates exact observed tab IDs, requests native Qt closure, then re-enumerates targets to verify which actually closed. Does not accept unsaved-work dialogs. Keeps one blank start tab after all pages close.
- Native close buttons use RequestClose and windowCloseRequested rather than silently discarding pages.
- Added a model-independent completion gate for explicit Hebrew/English tab-close requests: a tab inventory alone cannot pass; bounded correction attempts end with a clear incomplete status if no verified closure exists.
- User requested final acceptance in their specific ChatGPT conversation. Codex internal-browser control failed before page access (MXC sandbox), so that acceptance is pending and no live user tabs were closed by the developer.

## 0.5.1 — 2026-11-06

- Bounded idle ChatGPT browser observation to 15 seconds (DOM reads to 8 seconds), releasing the shared runner lock on timeout. Queued engine work takes priority over idle listener polling.
- MCP submission waits up to 20 seconds for short tasks and returns actual state, evidence and explicit continuation instructions. Longer tasks still require get_task polling; ChatGPT response behavior is not guaranteed by the server.
- Added a process-lifetime desktop profile lock to prevent simultaneous launches from creating competing Qt browsers; duplicate launches request the existing window.
- Validation and remaining limitations are recorded in VALIDATION.md.

## 0.5.0 — 2026-11-06

- נוסף שער MCP מאומת ב־OAuth מעל אותו מנוע מקומי ושיחות מתמשכות: שבעה כלים לפרויקטים/שיחות, שליחת משימות, מצב ואבחון, עצירה וקבצים. קריאה חוזרת עם אותו request_id מחזירה את אותה משימה.
- חיבור יוצא אוטומטי ב־SSH אל שרת הגשר הקיים, עם מפתח שרת מוצמד, משתמש ומפתח נפרדים ופורט 18897. HTTPS בכתובת agent.178-128-45-70.sslip.io. קובצי תצורת Ember נבדקו ונשארו זהים.
- אישור חיבור מתוך הגדרות הסוכן, PKCE, הרשאות ניתנות לביטול, רענון אסימונים וקישורי הורדה חתומים לעשר דקות. מפתחות והרשאות נשמרים מחוץ למאגר; סיסמת root אינה נשמרת.
- התאמה ל־MCP SDK 2.3.0 המותקן, כולל ניהול חיי שרת HTTP. המנהרה ושער MCP מופעלים בפיקוח Hub עם בדיקות בריאות וניסיון חיבור מחדש; כיבוי רגיל מפסיק את תהליכי החיבור שלו.
- העברת פורט Hub מ־8765 ל־8876 כדי לאפשר הפעלה לצד Ember Table. עודכנו ההפעלה, ממשק Windows, מקורות מורשים, קוד התוסף האופציונלי וסקריפטי הבדיקות.
- נוספה תצוגת מצב חיבור ובקשות הרשאה בהגדרות, עם רענון אוטומטי כאשר החלון פתוח. בקשה שפגה או טופלה כבר מחזירה שגיאה מפורשת.
- בדיקות: 141 בדיקות Python, תחביר JavaScript ובדיקת לוגיקת התוסף עברו. קבלת משימה אמיתית דרך הגשר: 0.344 שניות; הסוכן ביצע list_files והחזיר תוצאה בתוך 5.33 שניות, ושמר סבב יחיד גם אחרי שליחה כפולה. הורדת קובץ בדיקה אומתה בבייטים; הרשאת הבדיקה בוטלה ונענתה ב־401. מנהרת SSH הוקמה מחדש בתוך 6.75 שניות לאחר עצירה מכוונת.
- הממשק נבדק בצילום Qt מקומי. חיבור בפועל לחשבון ChatGPT של המשתמש, בדיקה מהטלפון ואתחול Windows לא בוצעו. בדיקת הגשר אינה אימות מחדש של כל פעולות השליטה במחשב או של מנגנון ההאזנה בדפדפן.

## 0.4.0 — 2026-11-06

- בחירת לשונית רקע מאמתת את גודל אזור התצוגה של הלשונית שנבחרה ומתקנת גודל אפס באמצעות הפעלת דף Qt וגודל תצוגה תקין, בלי הצגת חלון. לאחר בחירת קובץ ל־ChatGPT הגודל נבדק שוב לפני מילוי ההודעה, בלי להעלות שוב את הקובץ.
- מסירת מסמכים דורשת כרטיס קובץ תואם בהודעה החדשה, כולל שינוי שם אוטומטי עם מספר כפילות. צירוף מעורב דורש גם טעינה תקינה של התמונות. האימות אינו מוכיח תקינות תוכן הקובץ המרוחק.
- תגובת משוב שהגיעה לאחר שמטרת המשימה נוקתה נשמרת ומחזירה את המאזין למצב האזנה; אינה משאירה אותו תקוע בהמתנה לתשובה ואינה מעניקה סמכות לפעולה חדשה.
- בקשה ששוחזרה בתור לאחר רענון, ותשובתה כבר טופלה, יוצאת מהתור ללא ביצוע חוזר. כך הודעה ישנה אינה חוסמת בקשות חדשות.

- תצפית הדפדפן מסננת יעדי לחיצה מחוץ לאזור הגלוי ומחזירה קישורי תוכן נפרדים לניווט. בדיקת DOM משחזרת את הכשל של קישור ב־x=1140 בחלון ברוחב 715.

- הקשר inference מצמצם תוצאות כלים בלי לשנות את היומן, שומר מטרה וקבוצות כלים שלמות ומחזיר שגיאה מפורשת אם תקציב ההקשר קטן מדי. בריצת הקבלה נמצא הקשר של 182,278 תווים; לאחר התיקון הסוכן התקדם לבחירת קישור במקום תיאור האתר.
- הפעלת פקד DOM פנימי מחליפה המתנה ליציבות אנימציה בלשונית רקע, עם בדיקת פקד גלוי/זמין/לא מכוסה. כשל צילום לאחר הפעולה אינו מוחק את העובדה שנשלח קלט.
- מלאי טאבים ומעבר ביניהם אינם תלויים בתצפית על הטאב הנוכחי, כדי שטאב שקרס לא יחסום מעבר לטאב תקין.

- חידוש מפורש של משימת handoff שומר את אותה משימה ושיחה; טיוטה לא מוכרעת חוסמת חידוש, ללא שליחת בקשה כפולה.
- ניווט נבדק מול כתובות מהבקשה וקישורים שנצפו בפועל; כתובות כתבה או התחברות מומצאות נדחות. חידוש אחרי כשל בדפדפן חוזר למטרה המקורית ולתצפית חדשה.
- בקשת יצירת PDF/DOCX/XLSX אינה מסתיימת על סמך תיאור מסך בלבד: נדרש קובץ מכלי קבצים שנפתח בהצלחה. זו בדיקת מבנה, לא הוכחה לתוכן מלא או לאיכות חזותית.
- צילום ראיה מצורף להקשר המשימה ואינו הופך לבקשה חדשה לתיאור תמונה. בקשת צילום והחזרה נשארת חד־פעמית.
- התאוששות renderer ממתינה למוכנות המסמך אחרי אישור הרענון; ניסיון שני משתמש ברענון Qt מקורי באותה לשונית. מספר הניסיונות נשאר מוגבל.
- קבלת בקשות ל־ChatGPT נשמרת עד קבלה מוצלחת לתור. עומס אינו צורך בקשה; הוצאה לפועל מתחילה לפני ניסיון שליחת אישור מרוחק. מזהה פעולה כפול או מגבלת צעדים עוצרים את הבקשה הנוכחית ומאפשרים המשך האזנה.
- דיווח התקדמות ושגיאות מתוך מצב המשימה והאירועים, כולל API אבחון; כשל משימה אינו משבית את המאזין. בקשה חדשה מבודדת ממשימה קודמת עם פעולה לא מוכרעת, בלי לשחזר אותה.
- סגירת Explorer מסננת חלונות תיקייה בלבד, ואינה סוגרת את מעטפת שולחן העבודה. כשל צילום לאחר קלט אינו מוחק את תוצאת הקלט שכבר נשלח.
- התאוששות דפדפן באותה לשונית: זיהוי renderer שקרס גם כשהלשונית חסרה ב־Playwright, עד שתי טעינות מחדש ב־120 שניות. אין שחזור אוטומטי של פעולות בעלות השפעה. נוספו חילוץ DOM והרצת סקריפט מותנית בתצפית טרייה.
- יצוא PDF דרך מנוע Qt המקורי ויצוא כתבה קריאה מתוך DOM. ברירת המחדל לכתבה היא טקסט וכותרת ללא פרסומות, תמונות או וידאו; הדפסת האתר המלאה עשויה לכלול שכבות פרסום ודורשת בדיקה.
- כלי קריאה ועריכה ל־PDF/DOCX/XLSX, תמיכה בסיסית בעברית ובכיווניות, ושמירת מקור. אין הבטחה לעריכה מלאה של כל פריסה, OCR או חישוב נוסחאות Excel.
- הרחבות מקומיות עם גרסה, בדיקה לפני הפעלה ואימות hash; התקנת תלויות בסביבה נפרדת. נוספה בחירת מודל תכנות נפרד מתוך המודלים המותקנים. לא הורד מודל חדש במסגרת העדכון.
- שליחה ל־ChatGPT מפעילה את פקד השליחה שנצפה, ללא המתנת יציבות עכבר בלשונית רקע; אין שליחה חוזרת אוטומטית כשלא ידוע אם ההודעה נשלחה.
- כללי תחזוקה מחייבים ביצוע קבלה באמצעות הסוכן עצמו. תוצר בדיקת מפתח אינו נחשב השלמת משימת משתמש.
- אימות: 136 בדיקות מלאות עברו ב־23.05 שניות. הסוכן עצמו בחר כתבה, יצר PDF בן שלושה עמודים, שמר בפרויקט ומסר לשיחה. כרטיס הקובץ נצפה ו־ChatGPT אישר קבלה. הבדיקה החזותית המקומית בוצעה בידי המפתח; המסמך כולל גם פרסומות. פרטי ההתערבות לתיקון המסירה והמגבלות ב־VALIDATION.md.

## 0.3.1 — 2026-11-06

- תיקון מאזין: התאפסות מספור ChatGPT אחרי רענון אינה חוסמת בקשות חדשות שנשמרו בהיסטוריה. שימוש בעוגן הבקשה האנושית האחרונה כשמשוב הסוכן אינו מוצג.
- סנכרון מהנייד: רענון מוגן של השיחה הפנויה לאחר 30 שניות ללא שינוי, ללא שליחה חוזרת או איפוס ההיסטוריה.
- הצגת המתנה לסנכרון כאשר חסר עוגן מזוהה, במקום לדווח שהסוכן מאזין כרגיל.
- תיקון שליחת קבצים: אחרי כשל בכלי file_share/capture_screenshot, אמירה כמו "אנסה שוב" אינה מסיימת את המשימה. נדרשת קריאת כלי מתקנת; לאחר שני ניסיונות הנחיה ללא תיקון המשימה מסומנת חסומה. הובהרו ההבדלים בין מזהה קובץ, מזהה משימה ונתיב.
- מסירת תמונות: אישור טקסט אינו מספיק; נבדקת תמונה מצורפת טעונה עם ממדים חיוביים בהודעה שנשלחה. כשאין שדה העלאה מתאים, לא נשלחת הודעה ללא הקובץ.
- הנחיית משוב ל־ChatGPT מפנה לקובץ המצורף המקורי ואוסרת המצאת קישור sandbox מנתיב מקומי. אין הבטחה ש־ChatGPT תמיד יציית להנחיה.
- רענון סנכרון אינו מופעל כשחלון דו־שיח או תפריט מוצגים.
- בדיקות: 101 בדיקות Python עברו ב־19.07 שניות; תחביר JavaScript נבדק. בבדיקה חיה בוצע צילום אחד ונמסר PNG אחד בגודל 1792×1120. התמונה המקורית נפתחה במציג ChatGPT ללא שגיאת טעינה. בקשת צילום נוספת שהמשתמש הזין לשיחה בוצעה ונמסרה גם היא; מקור המכשיר לא נבדק.
- זמן שנמדד בבדיקה החיה: כ־12.48 שניות מיצירת משימת הסוכן למסירה, וכ־24.82 שניות משליחת בקשת הבדיקה. אלו מדידות נקודתיות בלבד.
- מגבלה: ChatGPT עדיין עשוי לייצר קישור הורדה נוסף שאינו תקין. האימות מתייחס לתמונה המקורית המצורפת להודעת הסוכן; הורדה בטלפון עצמו לא נבדקה. השירות הפעיל עודכן לגרסה זו ללא סגירת הדפדפן או מחיקת ההתחברות.

## 0.3.0 — 2026-11-06

### נוספו ושודרגו

- חלון Windows עצמאי ומגש מערכת, דפדפן Qt WebEngine אמיתי עם לשוניות, ניווט ופרופיל קבוע; הפרדה בין הדפדפן המובנה לבין יישום Windows שהמשתמש ביקש במפורש.
- שמירת cookies, נתוני אתר ולשוניות בין הפעלות; התחברות רגילה בתוך הדפדפן ואפשרות נפרדת להעברה יזומה דרך תוסף Chrome עם קוד חד־פעמי.
- פרויקטים ותיקיות, שיחות נשמרות, המשך הקשר, חיפוש, שינוי שם, נעיצה, ארכוב, הנחיות פרויקט, קבצים, שינויי Git, worktrees ומשימות מתוזמנות מקומיות.
- חיבור דו־כיווני ישיר לאתר ChatGPT בלי שרת MCP כתנאי לחיבור; בקשות משתמש בשפה חופשית, החלפת הודעות טכניות פנימית, תוצאות וקבצים באותה שיחה.
- מצב האזנה לשיחה המחוברת; שיוך שיחה מקומית לשיחה המרוחקת, תיעוד הודעות וקבצים ומניעת הודעות מקומיות ללא שיחה.
- מצב ChatGPT בלבד ומצב התכתבות זה לצד זה, עם שמירת הבחירה האחרונה; כפתור הדפדפן בחלון Windows ממקד את הדפדפן הצדדי.
- שליטה אוטומטית, שקטה או פיזית, העדפה נשמרת, עצירה וקלט מותנה בתצפית טרייה.
- ספריית קבצים מקוריים עם מזהה, מצב, גודל ו־SHA256; הורדה, שמירת מדיה, העלאה לאתר, העתקה לפרויקט והחזרת צירופים ל־ChatGPT.
- ממשק הגדרות מודל: מודלים מותקנים, פרופילי מהיר/מאוזן/הקשר מורחב, הקשר, אורך תגובה, טמפרטורה, שמירה בזיכרון וזמן המתנה. ההגדרות מיושמות בבקשות הבאות.
- מדיניות סיוע חזותי חכם וחסכוני או שוטף; הכוונה עם צילום חלון היעד ואימות סופי מפורש במשימות הממשק המחוברות.
- כלי `find_login` לחיפוש מקומי בקישורים ובתפריטים שנצפו, סגירת חלונית מזוהה של הדפדפן ובדיקת טופס כניסה.
- כלי `capture_screenshot` לצילום שולחן עבודה או חלון, רישום ה־PNG המקורי וסימון למסירה לשיחה.
- שורת התקדמות חיה, מצב טעינת המודל, שימוש בזיכרון וזמני חישוב שנמדדו.

### תיקונים

- הוחלפה ההסתמכות על תצוגת טקסט וכפתורים כתחליף לאתר בתצוגת הדפדפן המובנה האינטראקטיבית.
- נוסף fallback ל־`crypto.randomUUID` שאינו זמין בחלק מהדפדפנים בגישת HTTP.
- פתיחת יישום נבדקת מול חלון ותהליך; סגירה נבדקת מול החלונות והתהליכים שנותרו. טענת המודל לבדה אינה אישור הצלחה.
- נשמרת זהות יישום היעד כדי למנוע פעולות בחלון המתאם או ביישום אחר.
- פתיחה חוזרת של אותה כתובת באותה משימה משתמשת בחלון שנרשם במקום ליצור לשונית נוספת; הזהות משוחזרת גם בחידוש משימה.
- קריאת לשוניות כוללת לשוניות שאינן נבחרות; מסך New Tab עם לוגו Google אינו מוכיח שכתובת google.com פתוחה.
- חיפוש כניסה מדרג קישורי כניסה/חשבון/תפריט/דואר, כולל fragment של הכתובת, בלי לקבע כתובת אתר בקוד.
- זיהוי טופס התחברות כולל מייל ו־Continue/המשך כאשר כתובת ההתחברות נצפתה; טופס הרשמה לניוזלטר או קישור התחברות בלבד אינם מספיקים.
- חיפוש כניסה מכבד מצב קלט פיזי או שקט; חלוניות אופציונליות של הדפדפן נבדלות מחלונות שמירה והרשאה.
- צילום חלון Chromium קדמי משתמש בצילום מסך של גבולות החלון כדי להימנע מתוכן לבן שמתקבל לעיתים ב־PrintWindow.
- מזהי צילום ונגישות מסונכרנים, חלונית בבעלות אותו יישום מזוהה, ופקודה לא תקינה או נקודה מחוץ ליעד נחסמות לפני לחיצה.
- כשלים חוזרים מזוהים גם כשיש ביניהם פעולת תצפית מוצלחת; הכוונה חזותית אינה מסיימת משימה ללא ביצוע מקומי.
- אימות סופי מסתמך על תשובת בדיקה מפורשת ועל ראיות ההרצה העדכנית. תוצאה לא ברורה אינה מוצגת כהשלמה מאומתת.
- ההאזנה משתמשת במזהי הודעות ובסדר סבבים גם כש־ChatGPT מוציא היסטוריה ישנה מה־DOM; בקשה חדשה אינה נתקעת בגלל נקודת מעקב חסרה.
- הודעות שהסוכן שלח והכוונה שקיבל נבדלות מבקשות משתמש חדשות; מזהי פעולה כפולים אינם מופעלים שוב.
- שחזור שליחה לא ודאית בודק אם ההודעה כבר קיימת, לרבות טקסט מקופל ושינויים בהצגת Markdown, במקום לשלוח שוב.
- הנחיות לצילום מכוונות לכלי הייעודי במקום לניסיון לשתף נתיב ראיה מחוץ לתיקיית הפרויקט או להמציא מזהה קובץ.
- הודעת צילום חוזר אינה כוללת מחדש את ניסוח הבקשה המקורית; תוקנה לולאת צילום שנגרמה מפירוש ״עוד צילום״ כהוראה חדשה בכל צעד.
- אותו צילום אינו מצורף פעמיים כראיה וכקובץ; משימה שחודשה מדווחת על ראיות הניסיון העדכני בלי לצרף צילומים מיושנים מהניסיונות הקודמים.
- מצב מסירת קבצים מתעדכן אחרי אישור שליחה; צילום חלון חלופי אינו מסומן כצילום שולחן עבודה מלא.

### ביצועים

- מחזור בדיקת ההאזנה הפעילה והמתנת תשובת ChatGPT קוצר לכחצי שנייה.
- המודל מקבל את התמונה העדכנית במקום לצבור תמונות מכל הצעדים; המקור נשמר בראיות.
- חיפוש כניסה מקומי מופעל לפני ניחוש קואורדינטות או בקשת עזרה חיצונית.
- פרופיל מהיר מאפשר תשובות קצרות ושמירת מודל טעון; אין התחייבות שכל משימה או התייעצות חיצונית יהיו מהירות יותר.

### אימות

- 93 בדיקות Python עברו; לאחר שינוי מצב המסירה האחרון עברו 19 בדיקות החיבור והראייה הרלוונטיות. גם תחביר JavaScript ובדיקות המזהה בנייד והתוסף הסינתטי עברו.
- ניווט אמיתי ב־Edge הגיע דרך קישור באתר למסך כניסת וואלה, עם מייל והמשך, בלי הזנת פרטים ובלי לשונית נוספת במסלול המתוקן. זמן הניווט המקומי: 7.75 שניות; צילום הסיום נבדק גם חזותית.
- בדיקת צילום סופית: פעולה אחת, PNG אחד בגודל 1792×1120, צירוף אחד ואישור קבלה של ChatGPT. 9.89 שניות מתחילת משימת הסוכן עד השליחה, 18.56 שניות מהבקשה כולל תגובת ChatGPT הראשונית.
- שמירת העדפות סיוע אחרי רענון, הצגת התקדמות, שמירת נתוני אתר בין תהליכים והעברת קבצים מקוריים נבדקו. בבדיקות קודמות אומתו גם fixture של קלט שקט/פיזי וסגירת Chrome בפועל.
- פירוט הראיות, כישלונות הביניים והמגבלות נשמר ב־[VALIDATION.md](VALIDATION.md). מצב הסיוע השוטף לא נבדק בתרחיש חי מלא; הטלפון עצמו לא הופעל בבדיקה. אין אימות כללי לכל משחק/יישום או לשליטה פיזית במסך נעול.

### תיעוד וגרסה

- README עודכן עם כל תחומי העבודה, הוראות שימוש, הגדרות, תיקונים, בדיקות, זמני מדידה, מפת קוד ומגבלות.
- תוקנו תיאורים ישנים: השרת מוגדר להאזנה ברשת עבור Tailscale, בדיקת הממשק נעשתה בהמשך בתוך המוצר, וחיבור ChatGPT שולח מידע לשירות חיצוני.
- נוסף יומן גרסאות וכלל תחזוקה מחייב ב־AGENTS.md לכל תיקון/עדכון/שדרוג עתידי.
- גרסת החבילה הועלתה מ־0.2.0 ל־0.3.0; ה־API משתמש בגרסת החבילה המוצהרת בקוד במקום הערך הישן 0.1.0. שינוי מספר הגרסה אינו מפעיל מחדש שרת שכבר פועל.
- לאחר עדכון הגרסה עברו 11 בדיקות API ב־3.45 שניות; נבדקו התאמת מספר הגרסה בחבילה וב־API, קישורי התיעוד, נתיבי הקוד וקידוד UTF-8. התוכנה הפעילה לא הופעלה מחדש לצורך עדכון התיעוד.

- Fixed desktop launcher race between background and visible startup using start.ps1 -SkipDesktop. Verified normal interface shutdown followed by shortcut launch produces a visible agent window.

## 0.8.0 — 2026-11-06
Added model-independent CMD selection to run_shell alongside PowerShell. Native script execution preserves command syntax and records shell identity. Existing PowerShell calls remain compatible. Windows permissions still apply.

## 0.9.0 — 2026-11-06
Added task-owned live pipe command sessions (start/read/write/stop), output logs and exit status. Sessions are in-memory and do not survive service restarts. No PTY/full-screen SSH or password input support. The runner polls active sessions instead of accepting a premature final answer. Windows close failures now include actual Win32 codes and remaining windows rather than an ambiguous exception; no privilege bypass or force kill.

## 0.9.1 — 2026-11-06
Reject nested PowerShell -Command wrappers before execution, with corrective feedback. Shell error records are flagged even with zero native exit status; identical failed shell calls stop after two attempts. Runtime identity reports the actual executor PID and elevation, independent of the desktop UI.

## 0.9.2 — 2026-11-06
An explicitly elevated launcher replaces idle non-elevated agent backend, MCP gateway and desktop runtime. Tool subprocesses inherit backend elevation. Active tasks block replacement. Desktop must close normally. This does not elevate unrelated applications or bypass UAC. Shared Ollama services are not restarted.

## 0.10.0 — 2026-11-06
Added actual Ollama memory status and sidebar load/unload toggle beside model name. Direct MCP model_memory_status/model_memory_control work without model inference, including unload_all. Installed models only; no deletion/download. Active agent tasks block memory changes. Future inference can reload a model; other GPU processes are untouched.

Quick model selection: click the model name in the sidebar footer to list installed models with residency and GPU memory. Selection unloads the previous primary model, loads the chosen model, verifies residency and persists the selection for future tasks. On failure the previous selection remains (its memory may already be unloaded). Active tasks block switching; a separately configured coding model remains unchanged. The same switch action is available through direct MCP without inference. Fixed memory-tool registration order before the executable gateway starts.

Validation for 0.10.0: 160 tests passed (27.43s), including four mocked memory-control cases; JavaScript syntax passed. Live deployment/visual interaction pending: Windows UAC restart was canceled. No live success claimed.

## 0.10.1 — 2026-11-06
Removed the fixed 30-step task cap. Tasks can continue while working toward completion; cancellation and error handling remain. Two consecutive identical silent shell executions now block the next duplicate with corrective feedback; repeated refusal to change strategy pauses with a concrete error. Empty output explicitly does not prove target absence or success. Prompt guidance prioritizes exact user-provided paths and visible diagnostic errors. Applies independently of model choice.

## 0.10.2 — 2026-11-06
Task diagnostics and MCP responses include observed phase, model step, active tool arguments, last action result, waiting reason, elapsed phase time and polling requirement. wait_task observes for up to 20 seconds and emits progress/5-second heartbeat where the MCP client supports notifications; no guarantee the client displays unsolicited updates after a call ends. Running-state bookkeeping no longer hides the last real execution phase. Explicit administrator launch also replaces idle services with an older reported version; active tasks still block replacement and UAC is not bypassed.

The in-app global activity panel now shows model step, unknown total explicitly, completed-action count, current arguments, waiting reason, expectation and a 12-action execution timeline with command arguments, compact output and failure state. The same structured execution data is returned to MCP. Tool-returned is distinct from task verification.


0.10.4 (2026-11-06): Manual unload pauses active agent jobs and persists disabled local inference until explicit load/switch. Main and coding inference respect this flag. External Ollama clients are not controlled. Live restart/VRAM acceptance pending.


0.10.5 (2026-11-06): Preserve process name when executable-path access fails. Application inventory exposes unresolved title matches and refuses verified absence/closure when identity is unresolved or close delivery failed. Generic fixture added; live application closure not yet verified.


0.11.0 (2026-11-06): Configurable screenshot transport JPEG quality (30–95) and longest edge (640–3840), default 1600/75. Settings UI and MCP screenshot_settings tool; applies to local inference images, requested screenshot exports and ChatGPT visual evidence. Originals retained for native-coordinate input. File size is content dependent; no fixed KB guarantee. Live delivery/restart acceptance pending.


Vision benchmark — 2026-11-06: Actual local Qwen screenshot feedback, one desktop capture, warmed model, two runs per variant in reverse order. Prompt differed only in trial number to reduce prefix reuse. Original 1792x1120 PNG 1,206,987 bytes: 3.010/2.947 seconds. JPEG quality35 same dimensions 143,000 bytes: 2.836/2.856 seconds. JPEG quality35 960x600 49,413 bytes: 1.538/1.463 seconds. Prompt tokens 2022/2022/632 respectively. Simple app/text-label identification only; no OCR or coordinate accuracy acceptance. Original/JPEG responses incorrectly guessed Edge/Chrome for embedded Local Agent browser. Small version recognized Local Agent but fine text visibly degrades. Raw results: E:/AI/artifacts/vision-benchmark/results.json. This does not benchmark MCP latency or prove general accuracy/speed. Settings were not changed; model unloaded afterward if initially absent.

## 0.12.0 — 2026-11-06
- Added optional `image_ocr` tool and isolated CPU Hebrew OCR worker; workspace-confined input, timeout, explicit setup errors, raw and layout-adjusted evidence and review-required flag.
- Installed Hebrew-specific ONNX recognition locally (~206 MB); no persistent GPU model. Qwen OCR-assisted trial remained inaccurate and was not accepted.
- Verified real adapter recognition of the provided image in 7.07 seconds; two regression tests passed. Text is substantially readable but NOT an exact transcription: remaining letter, punctuation and layout errors are known. Full agent task-runner test stalled during runner initialization and was canceled; no live deployment or end-to-end acceptance claimed.


## 0.13.0 — 2026-11-06
- Separate local/ChatGPT screenshot sizing and quality, UI/MCP controls, including screenshot guidance file-path transport.
- Optional cached Hebrew OCR hints alongside local vision; errors remain explicit and OCR never proves success.
- Enforce feedback-off for direct consultations; add transcription review purpose and MCP feedback preference tool.
- Validation: isolated transport/OCR tests; live activation and full ChatGPT roundtrip not verified.

### Background window capture and region evidence — Unreleased, 2026-11-07
- Target-window capture uses PrintWindow when the worker session is non-interactive, even if Windows still reports that HWND as foreground. Failed foreground GDI capture falls back to the identified window. Background evidence never authorizes physical input.
- capture_screenshot accepts an optional region [left, top, width, height] in source-image pixels for desktop or window scope. Invalid bounds fail explicitly. Original evidence and desktop offsets are preserved; normal transport compression follows cropping. Available through agent tools/natural-language MCP tasks, with no new persistent setting.
- Dense latest visual evidence receives a compact retry before context-budget failure; current image remains attached and durable history is preserved.
- Arbitrary application rendering on a locked Windows desktop is not guaranteed. No unlock or secure-desktop bypass is performed.

### Tabbed application progress — Unreleased 2026-11-07
- Prioritize selected tabs and actionable controls when compacting dense UIA evidence; report selected_tab separately so a final tab is not lost behind restored tabs.
- Block identical physical input after two visually unchanged attempts, ignoring changing observation IDs. Preserve alternate actions and allow retry after image changes. Pixel equality is evidence of no visible progress, not proof of task failure.
- Normalize UIA click to Invoke without guessing coordinates. Expose modal/selected control state and preserve it in compact context.
- Planning guidance preserves unrelated tabs, creates new content separately, reads exact errors and verifies unobstructed final content before screenshot delivery.
- Follow-up generic input fixes: Unicode packet pacing (12ms per code point), CRLF normalization and real Enter/Tab events; exact observed control_name selection for UIA actions with uniqueness checks, as an alternative to model-confused numeric refs. No application-name-specific dispatch.


### Browser evidence, Git and APC import continuation — 2026-11-07

- Extended existing embedded-browser input with frame-bound virtual move/drag, coordinate normalization, observed region references and an owned Qt widget-event drag backend. Windows physical cursor is not used by this adapter. Isolated runtime supports distinct API/CDP/IPC identity; production defaults are unchanged.
- Real Engine tests exposed hidden-renderer CDP drag timeouts and a model-context reducer that discarded region labels/geometry. Errors now retain exception type, uncertain pointer actions stop blind replay, and compaction preserves region identity. Practical drag acceptance is still pending; failed runs retained under virtual-pointer-{refs,active,qt}-20261107.
- Added shared Git status and clean-base worktree creation. Unborn/dirty repositories preserve work and explicitly require manifest candidates; no reset/force/automatic commit. Local, HTTP and MCP Git status use the same adapter. Public connector activation remains pending.
- APC raw-index import now distinguishes entity source_hash from explicitly declared file content_hash, normalizes term arrays, rejects unsupported non-file entities with reasons and reports provenance/conflicts. Source contract: pinned APC inc/project_map.php entity_hash/addDoc. This is partial typed import, not full entity-graph parity.
- Git-aware indexing honors cached/untracked nonignored inventory. Traversal is limited to 100,000 entries/30 seconds and reads to 100 MB; read/traversal failure rolls back index changes. Resumable chunks, watcher-based optimization and large-project performance acceptance remain pending.
- Tests: earlier full development regression 224 passed in 46.76s; subsequent focused Git/API/browser 10 passed in 4.15s; browser/APC/context 15 passed in 2.34s; visual-context/inventory/APC 4 passed in 0.92s. These are fixtures, not final QA/QC or release acceptance.
- Production was not restarted. All plan completion gates remain open where no practical evidence exists.


### Verified pointer and model catalog/resource continuation — 2026-11-07

- Real Engine virtual-pointer task 86b2fa745b1f481a829573eb373fcfed passed in 40.20 seconds; retest 59c66c53c40345e09998ad5a143e6537 passed in 38.77 seconds after timer release handling. Synthetic page independently recorded clicked and dragged; final waiting_review. Evidence in virtual-pointer-context-20261107 and virtual-pointer-release-timer-20261107/acceptance.json. Both unloaded the model. This supersedes the earlier pending drag result, not general browser compatibility.
- Full regression at that revision: 231 passed in 51.06s (regression-context-pointer-20261107/junit.xml). Later candidate cross-process lock/API tests: 4 passed in 1.56s. Model catalog/core/context: 28 passed in 16.53s.
- Candidate patch/test now hold a Windows byte-range writer lock across processes, released by OS exit. Activation/Guardian ownership is still pending.
- Added persistent Ollama download jobs, progress, cancellation/interruption recovery and explicit resume with shared local/HTTP/MCP services and readable installation controls. Downloads do not select/load models. IAB on isolated port18979 requested the already installed qwen2.5-coder:7b, observed installed/verified, and Ollama showed zero loaded models. Evidence model-catalog-live-20261107/ui-install-evidence.json and catalog-ui.jpg. This verifies cache/reverification, not a fresh multi-GB download or public connector.
- Added initial durable model resource ownership shared by inference, coding advice and memory control. Internal switch evicts only recorded managed models; unknown external resident models block admission. Explicit user unload/disable remains separate. Resource integration is under test; external GPU telemetry, hardware budget admission and queue fairness remain unfinished. Hugging Face catalog/install and Guardian remain unfinished.
- Model/download/resource components are native Hub code, not APC ports. APC typed file import provenance is stored in context_import_reports; unsupported schema/entities report explicit reasons.
- Temporary isolated API7172/18979 remains for QA; old isolated15956/18977 also remains. Production unchanged. Full plan is not complete.


### Scoped coding worker and indexing efficiency — 2026-11-07

- Added a short-lived patch-only Python worker process using installed models and structured output. No model-provided shell/desktop tools. Parent validates allowed paths, original hashes, candidate revision, task/guidance revision, preserves selected acceptance tests, stages changes and runs tests. Same-account process isolation is not an OS sandbox. Work packets are persisted with original objective, source hashes, constraints, guidance and acceptance tests.
- Shared candidate_repair is registered for local tools, HTTP and MCP. Review UI displays persisted test results with revision and output. Full immutable WorkPacket/activation contracts and public long-running MCP delivery remain unfinished.
- Service-level real-model microbenchmark: Qwen3.5:4b 6.56s and Qwen2.5-Coder:7b 6.28s, both exact tests passed with original source/tests preserved. Models were tested serially and unloaded; default unchanged. Evidence coding-worker-benchmark-20261107/benchmark.json. This is a narrow worker diagnostic, not broad Phase3 model selection or completion of the catalog delivery gate.
- Engine worker delegation test e23844df2a314b4d8cb566f850305e25 (29.69s) failed the requested execution path: model used candidate_patch/test instead of candidate_repair. Required-tools flag false; retained failure evidence coding-worker-engine-20261107/acceptance.json. A new required-worker run is in progress.
- New code tasks reuse existing index instead of forcing a full scan. First index still scans; source handles revalidate hashes and search includes snapshot identity/freshness. No watcher/chunked resume claim. A 20-project/400-file fixture scanned in 3.36s; scoped search/overview in 0.218s, no model (context-many-projects-20261107/result.json).
- Fixture results: resources/memory/core 30 passed in 15.11s; context/resources/memory 13 passed in 2.89s; scoped worker/API/memory 9 passed in 3.10s; latest worker/API/ownership 6 passed in 2.98s.
- APC contribution remains the documented source/work identity, context/index metadata and history contracts. Resource ownership/model installer/worker process adapters are native Hub implementations. No production restart, release or commit. Full plan still in progress.
### Unreleased continuation — 2026-11-07: public model discovery

- Added public Hugging Face GGUF search/details/install to shared local/HTTP/MCP and UI paths, recording license/revision/file provenance. Raw HF aliases cannot bypass inspection. Restart/cancel retains provenance; a changed repository revision fails verification explicitly.
- Five provider/catalog fixtures passed. IAB downloaded the official Qwen 0.5B Q4_K_M GGUF and observed installed/verified, with no loaded model. Scope: installation integrity, not inference quality or public connector acceptance. Split/private/projection formats remain unsupported; repository revision is recorded but not pinned.


### Unreleased — 2026-11-07 continuation: memory and product shell
- Added chronological conversation_history with exact-text cursors across old requests, results, actions and events. Added revisioned explicit continuity notes shared by HTTP, MCP and the UI. Current objective is anchored in the fixed model prefix. Full retention does not imply an unlimited model input window.
- Added Hub-native navigation overflow, categorized settings, safe text-only Markdown rendering, conversation memory dialog and a consistent responsive design layer. Plugins/skills and RAG have separate navigation; unimplemented installation capabilities remain explicitly labeled. The embedded native browser is a separate surface still undergoing repair.
- Added durable factual execution state, bounded tool discovery, truthful source continuation and direct-index-refresh status synchronization. Metadata fast path retains periodic content-hash reconciliation.
- Guardian worker releases have independent journals, drain fencing, nonce health probes, observation, and health-validated rollback. Scope is the patch worker only; whole-application self-update remains incomplete.
- These are development changes, not a production release. No production restart or release commit.

- Development source: embedded-browser toolbar styling, portable single-site transfer helper location and explicit transfer errors; invalid/busy requests no longer consume the pairing code. Added Qt Manifest V3 extension manager with pending/completed distinction and shared local/MCP adapters. Real Qt lifecycle and public connector acceptance are still pending; no production restart.

- Optional source-bound memory review now has shared persisted settings, UI controls, local tool, browser-director path and caller-driven MCP request/reply adapters. Off by default. Identical requests are cached, browser dispatch is claimed once, unavailable context cannot confirm a claim, source edits invalidate feedback, and conflicting replays are rejected. Real ChatGPT acceptance pending.
- Native extension QA found that enabling a valid installed test extension terminates Qt in this environment. Enabling is explicitly blocked in shared service/UI until resolved; installation is not advertised as a working extension. No production deployment.

- Memory review now requires a verbatim evidence quote within the selected source excerpt to reject guessed/mismatched source IDs before transmission.
- Coding worker now parses proposed Python before applying changes and gets one bounded retry with the parser error; invalid proposals leave the candidate unchanged. Twelve focused tests passed in 8.78 seconds before the additional quote check; real Guardian rerun remains pending.

- Literal history queries with no matches now return an explicitly labelled chronological fallback page; this avoids repeated translated search misses without falsely labelling turns as matches. Task summaries append the actual memory-review status independently of model wording.

- New conversation submissions query recent context and unresolved actions directly instead of deserializing every historical task. Chronological summary pages bound text in SQLite. Added relevant indexes without deleting history.
- Replaced embedded-browser oversized dark start page with a compact responsive welcome view. Native visual acceptance remains pending.

- MCP task observation now returns pending memory reviews immediately to the caller and retrieves current review status instead of replaying stale action results. Replies do not resubmit or duplicate the original task. Public connector activation/acceptance is still pending.

- Conversation viewport now loads 30 chronological turns per page without internal model message arrays. Earlier pages and return-to-latest retain original history. Tool evidence loads on expansion instead of every refresh. Ordinary chats no longer materialize full history for empty bridge correspondence. Native Hub implementation, not APC-derived.

- Added durable decision anchors: exact user-request quotations with source hashes, optional later-source supersession, retained old versions and paged access. Shared local tool, HTTP/MCP functions and memory-dialog source inspection. Labels/supersession remain annotations, not fresh authority. Included recent anchors and current request ID in model continuity packets. Initial real Engine trial failed corrected-source selection and recall; failure retained at conversation-anchors-engine-20261107/acceptance.json; rerun in progress. Native Hub code, not an APC port.

- Browser memory feedback now sends review_id and accepts only a structurally valid reply with that exact ID. Missing/mismatched IDs and malformed values become unavailable, never confirmation.

- Retained ChatGPT feedback now enters future conversation context with source quotations and current pending/reviewed/stale status. Added paged feedback history through shared local/HTTP/MCP services and the memory UI. Final task status rereads the persisted review instead of repeating a stale action snapshot. Contradictions remain separate evidence; originals are never overwritten.

### Unreleased continuation - PLAY connections, 2026-11-07
- Extended the existing browser dispatcher with versioned PLAY instructions and the registered local tool catalog; no second dispatcher or extension requirement. Added explicit new-browser-conversation setup. Bootstrap status distinguishes sending from verified remote response.
- Persisted per-chat transport preference, ChatGPT link and favorites; exposed HTTP/MCP controls and a shared UI. Reject conflicting links and changing active/uncertain handoffs. Selecting MCP does not launch the browser.
- IAB QA found and fixed a detached-DOM initialization error which had emptied the connection dialog. Checked saved MCP preference/favorite/link after reload on isolated port18984.
- 42 focused fixtures passed before the final new-conversation addition; full regression and newest fixtures are in progress. No production restart/release, public connector or automatic native-browser acceptance claimed. Native Hub implementation; APC attribution unchanged.

2026-11-07 latest validation: full regression306passed95.20s; subsequent focused bridge/API/protocol run43passed23.91s includes the newest new-conversation bootstrap fixture. Full-suite collection preceded that one added test. Both runs exited0. Actual automatic browser/public connector acceptance still pending.

2026-11-07 update: added native AI connection catalog/cards for ChatGPT (Web PLAY/MCP), with Claude/DeepSeek explicitly not implemented. Reviewed APC browser/local-bridge candidates in docs/APC_BRIDGE_REUSE_REVIEW.md and manifest; no bridge code port claimed. Latest44 focused tests passed13.00s before connector catalog addition. Live isolated PLAY setup reached loading/not-ready error; fixed visible opening/attention status and45-second setup bound. Signed-in native bootstrap remains unverified.

Unreleased follow-up — 2026-11-07: opening an already-existing saved ChatGPT tab now rejects a not-ready connection instead of returning it as a successful open. It exposes the observed reason and shows the tab before the controller can replace its conversation context. New regression covers login/loading failures without opening duplicate tabs.31 bridge/transcript/PLAY tests passed6.00s. Native Hub fix, no APC code copied; production activation and live authenticated acceptance pending.

Unreleased — 2026-11-07: stopped/restarted PLAY sessions now retain uncertain outbound messages when selecting another conversation or starting listening again. Shared controller refuses these operations until the original delivery is reconciled; stopping does not discard or resend it. Regression simulates persisted stop/restart, checks original transcript/state unchanged and allows returning to the original local context.50 bridge/transcript/protocol/API tests passed13.31s. No production activation or authenticated live acceptance claimed; native Hub implementation, not APC-derived.

Unreleased — 2026-11-07: ChatGPT transport tabs and saved-route selector now stay synchronized. Choosing MCP/PLAY in either control updates the displayed panel and the value submitted on save. JavaScript syntax check passed; live UI persistence retest pending. Native Hub fix, no APC reuse.

Unreleased — 2026-11-07: provisional ChatGPT local-chatgpt URLs can now transition to their permanent /c/ URL without a second handshake/local chat. Adoption requires the same tab plus exactly one observed new message matching the pending outbound text; unrelated pages/tabs are rejected. The shared transcript binding updates before the saved browser binding, retaining pending evidence.32 bridge/transcript tests passed6.92s. Live post-fix repeat remains pending. Native Hub fix, no APC code copied.

Unreleased — 2026-11-07: PLAY now distinguishes typed preflight blocks (login, unavailable composer, active generation, existing draft) from uncertain submission. Drafts are preserved; observed preflight blocks record not_sent/connection_attention and a machine-readable reason. Other send exceptions remain submission_uncertain.51 focused tests passed13.63s; after clearing stale reason metadata,26 bridge tests passed5.59s. No APC reuse, production activation or new live success claim.

Unreleased — 2026-11-07: connection probes now expose draft_present, generating and send_ready separately from authenticated composer readiness. UI no longer describes an observed draft/generation as ready to send. No draft contents are exposed in probe metadata. Actual IAB saw a retained draft beginning with PLAY bootstrap; its provenance still needs exact verification before recovery. Screenshot browser-chrome-20261107/play-existing-bootstrap-draft.png. Native Hub change; production unchanged.

Unreleased — 2026-11-07: connection diagnostics identify a retained draft only when its complete text matches recorded local-agent outbound content (line-ending normalization only). Probe returns source message/chat/status, not draft text. Human drafts, prefixes and edited versions do not match.34 bridge/transcript tests passed6.54s. This adds provenance only; no automatic clearing/resubmission or completed recovery claim. Native Hub code, not APC reuse.

Unreleased — 2026-11-07: added shared reversible ChatGPT draft archive/list/restore service, HTTP endpoint, MCP chatgpt_saved_drafts and PLAY UI controls. Archive commits original text locally before clearing; rechecks URL/text/generation; restore requires original URL and empty composer. Copies remain, nothing sent.19 draft/API fixtures passed7.74s and shell.js syntax passed. Live UI/MCP recovery acceptance pending; native Hub code, not APC-derived.

- Unreleased native Hub memory-feedback repair: explicit historical result reads are retained as assistant reports in answer review, separate from user authority. Memory-only feedback tasks now render the saved correlated review status/evidence directly rather than allowing another local-model rewrite to reverse the verdict. 28 focused fixtures passed8.35s; new final-render path not yet live-verified. No APC code port.

- Memory answer validation now retains saved remote feedback (including verdict, status and source reference) returned by history tools. Explicit assistant reports survive source-read ordering. This addresses observed live loss of already-received feedback;30 focused fixtures passed4.66s. Full/live retest pending.

### Unreleased — 2026-11-07 project/PLAY dispatch repair
- Shared conversation folder binding through local tools, HTTP, UI selector and MCP; history preserved and active task workspace immutable.
- Explicit absolute file access for desktop/code; discoverable development tools in PLAY desktop mode.
- Feedback timeout receipt reconciliation and restart recovery for completed tasks.
- Native Hub changes; no APC source copied. Validation pending live acceptance.

### Project continuation repair follow-up — 2026-11-07 (Unreleased)

Candidate development now accepts code and desktop/PLAY tasks consistently across local tools and the HTTP/MCP API. A later task in the same persistent chat and same project can inspect, read, test and patch its existing candidate; unrelated chats remain rejected. Candidate responses include the actual isolated `candidate_path` separately from the original `source`. Large manifests are summarized only in model input, with full evidence retained in action logs. File reads return continuation offsets instead of overflowing the model context. These changes are native Hub work, not copied APC components.

The live audit instance on port 18984 has loaded the fixes. The public ChatGPT MCP connector still addresses a different instance/database: local gateway verification is not proof of public deployment. No source candidate has been activated or production release published.

Follow-up: the live 4B run initially repeated tool enabling/inspection because only its latest tool group fit inference input. A bounded factual ledger of successful tool names now survives context compaction without changing the original objective or durable history; candidate Git detail is summarized separately. After reloading and resuming the same task, actual candidate_read and paginated read_file calls completed and task519a0e529fb44622982e250c38872df2 reached waiting_review. This verifies resumed execution, not the correctness of every claim in its generated summary or completion of the entire development plan. PLAY result evidence now also includes candidate/project/context tool results.

### Supervised code execution — 2026-11-07
The shared PLAY/MCP director contract now assigns map retrieval, task decomposition and evidence review to the supervising model. It requests focused indexed sources/related tests and delegates candidate repairs to the configured coding model. New MCP `coding_model_settings` reads/changes the same persisted coding model as the UI without replacing the general/vision model. In the audit instance the previous coding_model was empty; it is now saved and read back through MCP as `qwen2.5-coder:7b`. This confirms configuration, not yet a completed Coder repair. Candidate/project/context actions are included in PLAY feedback. Resuming an existing handoff restores its authorized objective if pause handling had cleared it.

Regression run after context/progress fixes: 353 passed in92.35s. Subsequent supervision changes:52 focused tests passed, one protocol ordering assertion failed and was fixed by retaining the original transport rule first; the protocol/API rerun passed3 tests. Final combined verification follows. Public MCP deployment remains unverified.

Final checkpoint for this repair: full suite353 passed in96.35s; after the last catalog-focus change,8 binding/protocol tests passed in4.26s. Desktop-dispatched coding now exposes the development catalog without unrelated UI schemas; explicitly enabling desktop/browser groups restores those tools. Live resumed task c6d725a36a134b708a3e8dd1e6528f9f observed missing index, ran context_refresh (234 indexed files), and then context_search returned source references. Evidence: E:/AI/audits/browser-chrome-20261107/map-resumed-mcp.json. This is actual local agent execution observed through the local MCP facade, not a claim that the entire delegated development task or public connector deployment is finished.

### Unreleased — 2026-11-07 PLAY recovery
- Persist pre-submit versus submission-started phases; restore interrupted feedback after restart without duplicating submitted messages. Complete only full owned drafts (ignoring rendering whitespace), preserving edits and partial drafts.
- Restore embedded page viewport before composer preparation; record compact delivery diagnostics without draft text. Native Hub changes, no additional APC code copied.

### Unreleased — bidirectional failure feedback, 2026-11-07
Continuous PLAY now returns failed/blocked execution results and exact tool errors to its director without clearing the original authorization. Paused/cancelled work remains stopped. Recovery instructions require inspection of uncertain effects and prohibit bypassing permissions or approvals. Model context retains bounded source refs/cursors and the latest schema error, shared across models/tasks; repeated errors report the actual tool rather than a generic window message. Native Hub implementation; no APC code copied.

### Unreleased — supervised repair recovery follow-up
- Restored legacy handoff feedback without an action_id using its task identity; continuous failures remain actionable to the director.
- Completed inference records the selected warm model as managed, allowing a subsequent isolated coding worker to switch it out. Unknown other resident models remain protected.
- Local tools now expose model_memory_status, using the same backend as UI/MCP, instead of requiring ollama on PATH. Native Hub changes; no APC code copied.

- Supervised candidate_repair now yields measured test/diff/error evidence immediately to the director (PLAY or coding guidance); no executor replanning loop after a repair attempt. Identical source proposals are rejected without staging a revision. Failed shell feedback now retains exit code and bounded actual output.


### 2026-11-07: observed ChatGPT/Qwen self-repair acceptance
Real Web PLAY step 014 used Qwen2.5-Coder 7B to fix BridgeTranscript.link URL validation in isolated candidate revision 4. Model time 44.33s; acceptance and existing tests: 12 passed in 2.44s. Independent hash checks confirmed protected tests unchanged. ChatGPT received actual diff/results, requested read-only review step 015, then accepted the isolated repair for Codex integration review. Evidence: E:/AI/audits/play-ui-20261107/self-repair-acceptance.json and director-review-complete.png.
Codex integrated only the hash-verified source change and independent acceptance fixture into shared source. No production deployment or public MCP parity is claimed. Earlier full suite: 366 passed in 94.48s; post-integration full regression is being recorded separately.
Fixed global evidence compaction: diff changed-file counts and bounded path summaries survive omitted patch bodies; omitted changes no longer appear as an empty files list. Focused model-context regressions: 12 passed in 0.11s. These are native Hub fixes, not copied APC components.
Remaining: production activation, public MCP end-to-end parity, full Guardian upgrade/rollback acceptance and broader implementation-plan/UI QA. The full plan is not complete.

2026-11-07 Git acceptance (in progress): user authorized MellowYAK/MellowCodex publication and subsequent validated-change commits. Agent preflight initially repeated filtered empty ls-remote output; paused that read-only task, supplied precise director guidance, and a second agent task observed REMOTE_EXIT=0 REF_COUNT=0 with credential.helper=manager. Global shell evidence guidance now recognizes legitimate empty listings and asks for one explicit count/exit check instead of repeated filters. Publication rules added to AGENTS.md; .gitignore excludes runtime secrets/databases/profiles/artifacts. No push success asserted at this checkpoint.


### Git publication and runtime recovery — 2026-11-07
Agent task d013a2a334d343718be75384e29ef44e performed the initial commit and push to https://github.com/MellowYAK/MellowCodex, branch main, commit b535fb37f8d3181914d3142e7de6993cdf8779f7. Its command output confirms matching local/remote HEAD and clean status. Codex reviewed 239 staged blobs (1,714,965 bytes) before publication; no scanned credential patterns, sensitive extensions or oversized files were found. This was supervised execution with explicit director commands, not an unsupervised Git benchmark.
Audit runtime 18984 restarted as PID23984 with current evidence-compaction/shell-guidance fixes. PLAY restored connected/listening with no pending outbound replay. Agent task af144d8db2d343278a4afb6f4a24771f then executed project_git_status and one run_shell status check, correctly interpreted empty output as clean and completed without the earlier loop. 14 focused Git/model-context regressions passed in2.84s after the shell guidance edit. Production/public MCP services were not restarted or upgraded.
Native Hub changes; no APC code imported in this checkpoint. The wider technical plan, public connector parity, full Guardian deployment/rollback acceptance and UI QA remain incomplete. Future completed validated changes are to be committed/pushed by the agent under AGENTS.md publication rules.


2026-11-07 public MCP Git acceptance: task 6d06fb7c5f94424e9cd7194a78f39178 executed run_shell through the public connector and returned equal local/remote main hashes b618f0699ec6fc1bc01e7f300bb8f6ae083e7e1b, exit 0, clean status. This verifies actual public-MCP Git read access. Initial attempt in an older conversation was rejected before execution with HTTP409 because an unrelated prior action remained uncertain; that history was preserved. The read-only Git test used a separate persistent Git conversation. This does not establish discovery of all new development/memory tools or autonomous repair/deployment parity.
