# Validation — 5 November 2026

## Executed successfully

| Check | Result |
| --- | --- |
| Python test suite | 26 passed; store, API, interruption, revision control, evidence changes, path boundaries, input guards, native Qt request composition and asynchronous UI delivery |
| JavaScript syntax | `node --check hub/static/app.js` passed |
| Ollama local endpoint | Online; qwen3.5:4b available with tools and vision capabilities |
| Cold text request | `LOCAL_READY`; 69.69 seconds including about 37.72 seconds load time and initial GPU processing |
| Autonomous code task | Completed in approximately 16.37 seconds with an already-loaded model |
| Code-task artifacts | arithmetic.py and test_arithmetic.py created; five unittest tests ran and passed; exit code 0 independently read from the action log |
| Vision fixture | Red shape on left, blue circle on right, text LOCAL VISION 42 recognized, with a missing space in returned text; 13.88 seconds |
| Hub MCP | Initialize, list six tools, call get_capabilities succeeded over stdio |
| Windows-MCP | Initialize and list Snapshot tool succeeded; no UI action was executed by this probe |
| OpenCode | 1.19.5 healthy on authenticated loopback server; session creation through adapter succeeded |
| Native Windows UI | Qt offscreen rendering inspected; Hebrew glyphs corrected by explicitly loading Windows fonts; native submit payload and controls tested |
| Native UI against live service | Loaded the completed task, 6,854 characters of events, and live model readiness with no errors; rendered and inspected in `native-live-preview.png` |
| Global emergency key | Ctrl+Alt+F12 registered according to live capability endpoint; physical key delivery not tested |
| Live restart | Hub restarted after a consistent SQLite backup; completed task remained available |

Evidence is under `E:\AI\artifacts`, including `model-text-probe.json`, `vision-probe.json`, `hub-mcp-probe.json`, `windows-mcp-probe.json`, `native-app-preview.png`, and the code-task review bundle for `6e311b424edc4dfca088a371bf2e2b1d`.

## Explicitly not verified

- Desktop input against a real application/game, DPI/multi-monitor transitions, inaccessible windows, minimized/exclusive-fullscreen game capture.
- The HTTP UI's visual appearance: Codex iab and computer-use runtimes failed before initialization with `failed to prepare MXC sandbox: permission path cannot be represented losslessly`. No external browser was substituted.
- Browser support is now implemented; see the later verification below.
- Ten reboot recovery runs, Windows scheduled startup, or continuation across an actual computer reboot. No reboot was performed.
- Real SSH or service changes on a target server: none was supplied.
- The document's full 50-case evaluation, 90% production target, expert-model comparison, real-time gaming, or parity with Codex.
- Full Microsoft Agent Framework Workflow orchestration. Framework checkpoint storage is integrated; the scheduling loop is custom Python.
- Automatic delegation to OpenCode. The local server adapter was exercised for health and session creation; Hub code execution uses its own tool loop.

## Interpretation

The application is a runnable local pilot with measured code and image behavior. Its presence, installed dependencies, and unit tests do not establish universal control of arbitrary applications or games. The only measured code task here is the small arithmetic example, not a large-repository benchmark.

## Independent browser and locked session update (2026-11-05)

- 36 Python tests passed including durable desktop deferral and automatic queue resumption with simulated session transitions.
- Native unlocked fixture passed real click, Unicode typing, replacement, drag, scroll and stop checks (artifacts/desktop-acceptance/result.json). Arbitrary apps/games remain untested.
- Real local LLM browser task 25c2e25d2c2c436a857c0d1a71b10ae2 completed navigation, field fill, click and verified Saved: LOCAL_AGENT_BROWSER_OK in 16.12 seconds while the runtime was hidden and WTS reported locked/disconnected. Browser uses live DOM fallback when screenshot rendering is unavailable.
- Subsequent task ac45539e61cc42fb940c88a370baa965 performed those actions but incorrectly included the word EXACTLY in the text. Its exact-content acceptance check failed. This is a small-model instruction-following limitation, not a claim of perfect reliability.
- Background UIA fixture: SetValue verified while WTS locked=true/state=4; Invoke returned but no button click event occurred. Do not claim general native app operation while locked. Evidence: artifacts/background-accessibility.json.
- Synthetic Chrome HttpOnly cookie plus localStorage/sessionStorage transfer and extension mock tests passed. Extension has not been installed in personal Chrome and no real account login transfer has been verified.
- Screen unlock/resume tested by state simulation; no real unlock transition or reboot was forced.

- Final locked-session browser acceptance f2aca057261f40259f599b4849e6b0b4 passed exact text verification in 16.14 seconds; WTS locked=true/state=4 recorded before and after. Report: E:/AI/artifacts/agent-browser-f2aca057261f40259f599b4849e6b0b4.json.
- Product run_shell executed and verified BACKGROUND_SHELL_OK 42 with exit code 0 while WTS stayed locked/disconnected. Report: E:/AI/artifacts/locked-shell-check.json.

## Conversation interface update

44 Python tests pass, plus mobile UUID fallback and Chrome bridge JavaScript checks. Real local-model UI testing confirms two-turn recall and transcript persistence after reload. Responsive layout measured at 1440px and 390px with no horizontal overflow; offscreen Qt desktop/mobile renders inspected. File preview traversal, project notes, worktree isolation, attachment validation, schedule dispatch and emergency schedule pause have dedicated tests. Feature boundaries and official research links are in docs/UI_CAPABILITIES.md.

## Native login and bidirectional visual feedback — 6 November 2026

- 93 Python regression tests passed in 17.34 seconds. JavaScript syntax, mobile UUID fallback and extension transfer fixture tests passed. Regressions cover virtualized chat anchors, old-turn rejection, multi-stage login detection, physical input preference, duplicate image exclusion, current-attempt evidence and screenshot request repetition.
- Real Walla task `6b092360d5bb49d5bb546a03b3401648`: local semantic navigation closed an owned Edge translation popup, followed the observed `mail` hyperlink, and reached `https://friends.walla.co.il/#/login`. It used the existing tab. The visible form contains an email field and Continue button; no credentials were entered. Navigation took 7.75 seconds, excluding later local inference and final ChatGPT review. The final screenshot was visually inspected here and ChatGPT returned an explicit positive visual review. Evidence: `E:/AI/artifacts/login-navigation-acceptance.json`.
- The first screenshot test exposed an obsolete listener anchor after ChatGPT virtualized its history. Fixed recovery uses stable turn order when the stored anchor is absent; regression tests also reject older turns. A second attempt exposed repeated screenshot requests caused by re-inserting the original wording after every image. The observation message now identifies a completed action without reissuing that request.
- Clean final screenshot test `77565a08f4424c7d93043915b7db03b2`: a plain-language ChatGPT request triggered exactly one `capture_screenshot`, produced a valid original 1792×1120 PNG, delivered exactly one attachment, and received “Final screenshot captured and received.” The measured task-to-delivery interval was 9.89 seconds; request-to-delivery was 18.56 seconds, including the initial ChatGPT response. These are individual measurements, not a service-level guarantee. Evidence and hash: `E:/AI/artifacts/desktop-share-acceptance.json`.
- Model and visual assistance controls were exercised in the product's own embedded UI. Continuous mode survived reload, then smart mode was restored; no JavaScript page errors were observed. The settings screenshot was visually inspected: `E:/AI/artifacts/model-visual-settings-verified.png`. Live progress was observed in the actual desktop screenshot and the progress API returned HTTP 200 during execution.
- The app remains running with the saved ChatGPT conversation and continuous listener enabled. Fast local inference preset and smart visual assistance remain selected.

Limits: the continuous visual mode's settings persistence was tested, but a full multi-step live workflow in that mode was not run. The final live navigation used accessibility controls; physical preference has regression coverage and earlier fixture evidence, not a new general application acceptance test. Cross-device arrival was simulated by a newly submitted message in the linked web conversation, not by operating the user's phone. Existing external browser tabs were preserved. Arbitrary games/apps, native control while locked, and full Codex parity remain unverified.

## Documentation and version consolidation — 0.3.0, 6 November 2026

README now consolidates the implemented features, fixes, usage, evidence and limitations. CHANGELOG records the delivered changes; AGENTS requires release notes for future fixes, updates and upgrades. Package/source/API version consistency was checked at 0.3.0; the API imports the shared source version instead of its former 0.1.0 literal. Documentation relative links, listed source paths, UTF-8 and fenced code blocks passed checks. All 11 API tests passed in 3.45 seconds after the metadata change. The running service was not restarted for this documentation update; it loads the new version metadata on its next normal restart.

## Listener recovery and usable screenshot attachments — 0.3.1, 6 November 2026

- 101 Python tests passed in 19.07 seconds; `node --check hub/static/app.js` passed. Regression coverage includes renumbered turns after reload, an archived but unexecuted request, missing stable anchors, duplicate prevention, draft/generation/overlay guards for idle refresh, image load verification and bounded correction after a failed file-share tool call.
- The earlier turn-order recovery claim above is superseded: ChatGPT fallback turn numbers can reset on reload. Live state retained order 27 while current turns were numbered 0–5. Authorization now requires a stable message-ID anchor, with the last authorized human message as fallback when the agent feedback is absent. When neither anchor is present, execution is deferred visibly rather than granting authority based on DOM numbers.
- Idle cross-device refresh is guarded at 30 seconds without activity. Fixture tests simulate a remote arrival and draft changes immediately before refresh. Real refresh was observed in the linked conversation; the user's phone was not operated in this test.
- Live task `c139c2cbb409454ab1d3748823c0347b` executed exactly one `capture_screenshot`, registered a valid original PNG of 1792×1120 pixels (205,619 bytes), and delivered one attachment with `attachment=verified_image`. Task-to-delivery was approximately 12.48 seconds; test request-to-delivery was approximately 24.82 seconds, including the initial ChatGPT response. These measurements are not latency guarantees.
- The actual original attachment was opened in the product's embedded ChatGPT viewer: the image loaded with natural dimensions 1792×1120 and no file-load error. Its screenshot was visually inspected. Evidence: `E:/AI/artifacts/listener-recovery-acceptance.json` and `E:/AI/artifacts/listener-original-attachment-open.png`.
- A subsequent human request for a fresh desktop screenshot produced task `3cefca36164848f388d4049c710b7911`: one capture, a 204,193-byte PNG, and verified image delivery. The device used to submit that request is unknown. A further human request was then detected and dispatched without manually resetting the listener.
- The prior reported PNG itself was valid and its original attachment loaded. The additional download link generated in ChatGPT's answer failed. The bridge now directs ChatGPT to the real original attachment and checks actual image loading before reporting delivery. ChatGPT still generated an additional link during the new test, so link-generation compliance is not guaranteed; opening/downloading that extra link on the phone was not validated.
- Version 0.3.1 is loaded by the restarted hub service. The existing embedded browser process, profile and login were preserved.
# אימות 0.4.0 — 2026-11-06

- 136 בדיקות pytest עברו ב־23.05 שניות. כולל עומס בתור ללא אובדן בקשה, התחלת עבודה לפני אישור מרוחק, סינון חלון Explorer, התאוששות לשונית, הקשר מודל, פקדים מוסתרים/מכוסים, צירופים, הרחבות ומסמכים. רוב הבדיקות סינתטיות; בדיקות DOM מריצות את JavaScript האמיתי על fixtures.
- בדיקות מתאם ישירות: לשונית Qt שקרסה חזרה באותו מזהה לאחר reload. הדפסה מקורית של אתר החזירה גם PDF עם פרסומות החוסמות את התוכן; לכן אינה נחשבת הצלחה חזותית.
- PDF קריא של כתבה, שהופק ישירות במהלך פיתוח, רונדר ונבדק חזותית בשני עמודים. זהו תוצר בדיקה בלבד, ללא תמונות, ולא ביצוע של משימת המשתמש בידי הסוכן. הועבר מחוץ לתיקיית העבודה; טיוטת מסירתו בוטלה ללא שליחה.
- קובצי Word/Excel נבדקו ב־round trip סינתטי; לא נבדקו חזותית ביישומי Office. PDF עברי מעורב נבדק בנפרד. לא בוצעו בדיקת נייד, אתחול Windows או מסך נעול לעדכון זה.
- ריצת הסוכן עצמו `99117bc7aaa8454faf02c724aec838d6` בחרה את הכתבה `https://www.walla.co.il/news/breaking-news/383960340` באמצעות קישור שנצפה, הפעילה `browser_save_pdf(layout=page)`, `file_copy`, `document_read` ו־`file_share`. הפלט `E:/AI/repos/sandbox/walla-article.pdf` הוא PDF בן 3 עמודים, 4,283,988 בתים, SHA256 `a0dad32cf570a9cddad69484fde8062745ff7a949157a2a4b2aee49993e8ca1a`.
- שלושת העמודים רונדרו ונבדקו חזותית בידי המפתח (לא בידי הסוכן): הכותרת בעברית וטקסט הכתבה קריאים; קיימים גם תמונה, פרסומות ושאריות ממשק האתר. אין טענה ליצוא נקי או לעריכה מושלמת. ראיות: `E:/AI/artifacts/agent-pdf-acceptance/page-1.png`, `page-2.png`, `page-3.png`.
- ניסיון המסירה הראשון נכשל לפני שליחת ההודעה, כאשר לשונית ChatGPT ברקע הייתה בגודל אפס ושדה ההודעה לא היה נגיש. לאחר אבחון, הוסר רק צירוף הטיוטה של הניסיון הכושל, נרשמה התאמה של מצב המסירה, ומתאם Qt תוקן כללית. השירות והדפדפן הופעלו מחדש תוך שמירת הפרופיל. לא נוצר PDF חלופי ידנית ולא הורצה שוב משימת התוכן; הגשר של הסוכן חידש את מסירת הפלט הקיים.
- הודעת הסוכן `1fb80a6b-9dfb-420c-97c6-b9f2ddab6ff6` כוללת כרטיס ממשי בשם `walla-article(2).pdf`; validator הקבצים החדש עבר על ההודעה הקיימת. ChatGPT השיב שקיבל ובדק את שלושת העמודים. לא הורד הקובץ חזרה להשוואת hash, ולא נבדקה הורדה מהנייד או תקינות קישור נוסף ש־ChatGPT יצר. ראיות ממוקדות: `E:/AI/artifacts/agent-pdf-acceptance/delivery.json`.
- תיקוני התכנון, הכלים והמסירה משותפים למודלים; הקבלה האמיתית הזו בוצעה עם המודל המקומי הנבחר בלבד. אין הבטחת הצלחה בכל אתר או מודל. התאוששות מלאה ללא התערבות מפתח לאורך כל הריצה לא הוכחה, משום שהתיקונים הוחלו בין ניסיונות.
- בבדיקת מצב ההאזנה לאחר המסירה נמצא תור ישן עם הודעת `#` שתשובתה כבר טופלה. נוספה התאמה כללית המוציאה בקשה כזו מהתור ללא הרצה חוזרת; fixture כולל הוראת פעולה שכבר טופלה ומוודא שלא מתקבלת משימה נוספת.



## 0.5.0 — public MCP bridge, 6 November 2026

- Full Python suite: **141 passed in 25.78s**. `node --check hub/static/app.js` and `node tests/test_extension.cjs` passed.
- Five new regression tests cover PKCE rejection, authorization-code replay, refresh rotation, revoked access, authenticated tool discovery, redirect restrictions, signed file delivery/tampering/expiry, stable submission dispatch and strict loopback SSH forwarding. These are fixture/adapter checks, not autonomous desktop acceptance.
- Remote deployment: independent SSH user/key, loopback 18897, HTTPS virtual host `agent.178-128-45-70.sslip.io`; nginx and sshd configuration checks passed. SHA256 values of existing Ember Table/Video nginx files, SSH match file and authorized_keys were unchanged. Ember apps were not running their tunnels at inspection time; their business functions were not retested.
- Public health and both OAuth discovery documents returned HTTP 200. Unauthenticated MCP returned 401. Live OAuth used client_secret_post plus PKCE and explicit approval through the authenticated local API. Test grants were revoked after each run (HTTP 200; subsequent access HTTP 401). No user account connector was configured by this test.
- Agent-owned live acceptance via public MCP: task **213894ee63af4bd995bd1191b060b637**, saved chat **19d2852658a745b5bdedee9dc1a6347c**. Submission returned in **0.344s**; completion observed at **5.33s**. The local model called `list_files`, recorded its actual result, and entered `waiting_review`. Duplicate submission returned the same task and exactly one saved turn. No developer performed the task's file inspection on the agent's behalf.
- An earlier acceptance task also executed successfully, but the developer assertion incorrectly expected `completed` instead of the store's `complete` action state. The assertion was corrected and the acceptance rerun; this was a test error, not an agent task failure.
- Separate developer file fixture: UTF-8 Hebrew text uploaded to the local library, retrieved through MCP `get_file` and downloaded through public HTTPS. Bytes matched exactly; SHA256 **359003622272ced0fff61331bbf9c560ebc0285336d97b22f1de2878c009b3fd**. This does not test ChatGPT attachment rendering or phone downloads.
- Evidence: `E:/AI/artifacts/mcp-acceptance.json`, `E:/AI/artifacts/relay-reconnect.json`, `E:/AI/artifacts/remote-settings-review.png`, `E:/AI/state/mcp/deployment.json`. Evidence contains no OAuth tokens or root password.
- Forced termination of this integration's SSH process only: supervisor created a new SSH process and public health recovered in **6.75s**. This tests tunnel recovery, not Windows reboot or every process-crash scenario.
- Qt offscreen settings screenshot was visually inspected: Hebrew text readable, connected status and public MCP address visible. The full-size model-settings dialog remains scrollable.
- Hub port migrated to **8876**; running API reports **0.5.0**. Existing local chats, task history and browser profile retained. Tailscale phone access on the new port was not tested.
- No claim of full Codex parity, guaranteed latency, Windows locked-screen mouse control, or resolution of every existing browser-listener issue. This release adds an independent authenticated dispatch path.


## 0.5.1 — 2026-11-06
- Full suite: 144 passed in 24.79s. New regression cases cover listener timeout releasing the runner lock, short MCP completion, and an active task at the wait deadline (never reported as success).
- Original user screenshot task 8ada50f1cfd0412eb9dba90d74d06ada recovered from queued and executed capture_screenshot through Engine; PNG registered as 1562ff0dc5754e50808e87393ea97834. Delivery into the user's ChatGPT conversation has not been observed.
- Public OAuth/MCP agent-owned inspect acceptance: fcf8aa3acb7140bcbb1a149047e54b88 returned within 4.156 seconds; repeated request ID did not duplicate execution.
- Public screenshot acceptance: first capture returned within 6.813 seconds; its developer download assertion failed because compact tool evidence was a JSON string, not a dict. Corrected the acceptance parser. A second complete run 015e2244179541139b6f103d611e8723 took 20.62 seconds through result polling and verified original image download SHA256 b9ebe003a2f4e2135bc866994677a6ab6443a8b3b4711c6aa2a14c93c94d8af9. Temporary test OAuth grants revoked; user grant retained.
- Public health verified 200, version 0.5.1. Actual desktop process reports visible main-window title Local Agent — התכתבות לצד ChatGPT. Duplicate launch during startup was rejected rather than opening a competing profile; a subsequent show request succeeded. Tray icon placement within Windows overflow was not visually verified.
- Limitations: ChatGPT client must continue polling long work and call get_file for returned images. Actual user ChatGPT message rendering, phone display, reboot and locked-desktop operation not verified here. Idle observation can still delay dispatch up to its 15-second bound; timings above are measurements, not latency guarantees.
`nFinal targeted checks after preserving status publication during active jobs: 13 passed in 3.42s. Backend reloaded; public health rechecked.

## 0.5.2 — 2026-11-06
Full regression suite: 147 passed in 24.63s. New fixtures validate Hebrew/English close-request detection, rejection of observation-only completion, browser-mode tool availability, all-or-none target validation, and use of native RequestClose. Public health verified 200/version 0.5.2 after reload. Saved browser session preserved on graceful desktop restart.
Live tab closure through the user's specified ChatGPT conversation is NOT verified: Codex iab automation failed before accessing the page with MXC sandbox path error. No alternate live closure was substituted. User must send the test from that conversation; the agent records resulting actions for subsequent verification.

## 0.6.0 — 2026-11-06
149 tests passed in 26.11s. Includes mocked MCP stage notifications and notification failure isolation. Actual ChatGPT conversation could not be inspected: Codex iab automation failed initialization (MXC permission path cannot be represented losslessly), including retry after reset. ChatGPT notification rendering and visual UI acceptance remain unverified.

## 0.7.0 — 2026-11-06
151 regression tests passed in 25.68s. Agent-owned task fc8bae9a84314d9390a06febbefe4659 used agent_environment, desktop_shortcut inspect and create; recorded verified target E:\AI\Start-Local-Agent.cmd at C:\Users\MellowYak\Desktop\MellowCodex.lnk. This is actual runner acceptance, not direct adapter execution.

Launcher acceptance: normal IPC shutdown confirmed no agent window; launching the agent-created .lnk then produced a visible Local Agent window. Services remained reachable (UI HTTP 200). Launch test is direct operational verification; shortcut creation was performed by the agent runner.

## 0.8.0 - 2026-11-06
154 tests passed in 26.54s, including real native shell exit-code/output checks. Agent-owned task 6d18707632ef4271a22ddb8d6c2ca755 selected powershell and cmd, returned PS_OK and CMD_OK with exit code 0 for both. No administrator/elevation or arbitrary-command coverage claimed.

## 0.9.0 - 2026-11-06
Initial suite: 153 passed, 2 native API mocks failed after changed DLL binding; corrected mocks and reran affected application/terminal tests (7 passed) and recovery tests (5 passed). Agent-owned terminal task 167899fcaffb4b8699e540b76fa2503e observed START while running then FINISH with exit 0. Agent-owned close task 8c4310fa89f243c6a813588ed2fd54df confirmed Win32 error 5 and Task Manager remained open. No successful closure claimed. Interactive SSH/PTTY and ChatGPT client rendering unverified; not complete capabilities.

## 0.9.1 - 2026-11-06
156 tests passed in 27.94s. Agent task 54be29f60ed94c4dbce4ccdeea2703c1 used agent_environment then app_close without shell retries. Executor elevated=false; close returned Windows error 5 and remaining Task Manager window. Closure NOT completed. The restarted executor is not elevated; prior UI elevation is not proof of backend elevation.

## 0.10.0 — 2026-11-06: model memory and quick selection
- Full regression suite: 160 passed in 27.43s (installed Windows Python, elevated tool execution).
- Four mocked Ollama tests cover verified switch with saved selection, failed load retaining selection, rejection of missing models before mutation, and unload-all/reload.
- JavaScript syntax: node --check hub/static/app.js passed.
- Actual sidebar interaction, live model switching and remote ChatGPT MCP invocation are NOT yet verified. The elevated service restart was canceled at Windows UAC; running services have not loaded these changes. Requires an approved administrator restart and UI refresh.
- A failed switch can leave the old model unloaded while retaining its selection; subsequent inference reloads it. A separately configured coding model is unchanged.

## 0.10.1 — 2026-11-06
162 tests passed in 33.55s. Fixture-driven Engine task completed 35 tool steps and reached waiting_review, demonstrating removal of the 30-step cap. Silent-shell guard tests cover duplicate rejection and allowance for changed arguments/results or intervening observation. Reported VS Code task e03de96fd99a400da95dc3e465347369 was read via local diagnostics: repeated identical empty shell results, then waiting_user at 30 steps; no successful launch verified. New live agent acceptance remains pending administrator-approved service restart; no manual VS Code modification performed.

## 0.10.2 — 2026-11-06
163 tests passed in 34.11s; JavaScript syntax passed after timeline expansion-state preservation. Fixture validates active command ID, step, wait reason, expected output, unknown total and blocked-state polling. Updated old get_task polling assertion for new wait_task contract. Live checks after user reopened UI still returned 0.9.2 from backend and gateway. UAC restart returned cancellation again. Version-aware administrator startup and live MCP/UI timeline remain unverified in the running services; not claimed deployed.


0.10.3: Python compilation and PowerShell parser validation performed. Live UAC activation and restart have not yet been verified.


0.10.4 (2026-11-06): Manual unload pauses active agent jobs and persists disabled local inference until explicit load/switch. Main and coding inference respect this flag. External Ollama clients are not controlled. Live restart/VRAM acceptance pending.


0.10.5 (2026-11-06): Preserve process name when executable-path access fails. Application inventory exposes unresolved title matches and refuses verified absence/closure when identity is unresolved or close delivery failed. Generic fixture added; live application closure not yet verified.


0.11.0 (2026-11-06): Configurable screenshot transport JPEG quality (30–95) and longest edge (640–3840), default 1600/75. Settings UI and MCP screenshot_settings tool; applies to local inference images, requested screenshot exports and ChatGPT visual evidence. Originals retained for native-coordinate input. File size is content dependent; no fixed KB guarantee. Live delivery/restart acceptance pending.


Vision benchmark — 2026-11-06: Actual local Qwen screenshot feedback, one desktop capture, warmed model, two runs per variant in reverse order. Prompt differed only in trial number to reduce prefix reuse. Original 1792x1120 PNG 1,206,987 bytes: 3.010/2.947 seconds. JPEG quality35 same dimensions 143,000 bytes: 2.836/2.856 seconds. JPEG quality35 960x600 49,413 bytes: 1.538/1.463 seconds. Prompt tokens 2022/2022/632 respectively. Simple app/text-label identification only; no OCR or coordinate accuracy acceptance. Original/JPEG responses incorrectly guessed Edge/Chrome for embedded Local Agent browser. Small version recognized Local Agent but fine text visibly degrades. Raw results: E:/AI/artifacts/vision-benchmark/results.json. This does not benchmark MCP latency or prove general accuracy/speed. Settings were not changed; model unloaded afterward if initially absent.


2026-11-06 Hebrew OCR trial: qwen3.5:4b, supplied contract photo, identical transcription prompt, JPEG quality85 at 720x960,1200x1600,2880x3840. Wall times 30.89s,23.33s,25.63s; first included4.52s model load. All three outputs visibly garbled; none accepted as reliable transcription. Single run per resolution, different output token counts; not a controlled throughput comparison. Raw outputs E:/AI/artifacts/qwen-hebrew-ocr/results.json. No persistent model/image settings changed.

### 2026-11-06 Hebrew OCR diagnostics (0.12.0)
- Qwen + Tesseract draft: 21.78s, failed exact transcription.
- Hebrew specialist CPU: 7.15s original; 7.12s geometrically rectified; 7.46s larger detector input. Larger detector did not consistently improve quality.
- Final adapter: 7.07s including model initialization/recognition/layout processing (subprocess overhead excluded). Output readable, with remaining character and ordering errors; no numerical accuracy score or perfect-transcription claim. Original photo remained unchanged.
- `pytest tests/test_image_ocr.py -q`: 2 passed (0.23s), missing-engine and workspace-boundary checks.
- Full ToolRunner attempt canceled after initialization stalled before producing artifacts. Direct adapter succeeded; this is NOT agent end-to-end acceptance.
- Results: E:/AI/artifacts/qwen-hebrew-ocr/readable.html, readable.txt; machine evidence: E:/AI/artifacts/hebrew-ocr-acceptance/.


### 0.13.0 visual assistance
- Four isolated tests passed: destination-specific dimensions and unchanged originals, OCR opt-in/cache/evidence labeling, existing OCR adapter tests (0.80 seconds).
- compileall hub passed. Broader visual recovery tests stalled in desktop-dependent ToolRunner construction and were interrupted; not counted as passing.
- Live process restart, visual UI inspection, OCR/ChatGPT correction roundtrip, and MCP callback behavior have not been validated. No end-to-end success claim.

### Live agent acceptance — 2026-11-06, document/UI follow-up
- Submitted the actual user-provided Hebrew photograph as `visual-document-test.jpg` in the sandbox workspace through MCP, task `d617de58d32249ee97ec46163b91c33b`.
- FAILED: running agent tried document_read (PDF/DOCX/XLSX only), searched for OCR, then repeated a PowerShell 5-incompatible `||` command. State waiting_user after six actions. No transcription or visual comparison completed; image_ocr was not invoked.
- Requested service version alignment through the existing launcher; Windows UAC approval pending. No updated-runtime success claimed.
- Independent computer-use initialization failed with `failed to prepare MXC sandbox: permission path cannot be represented losslessly`. Random-window visual acceptance has not yet run.


## OCR-on / ChatGPT-off actual task-runner acceptance — 2026-11-06

- Successful image_ocr calls now attach the original image through the configured local image transport to the next model turn. OCR remains supplementary, untrusted evidence. This applies to all supported local models and workspace images.
- Added scripts/ocr_agent_acceptance.py for real local task-runner document acceptance, retaining actions/results in an isolated persistent store.
- Actual Qwen 3.5 4B test with OCR on and ChatGPT feedback off: 23.39 seconds after image delivery fix (20.58 seconds before). Recognized a rental agreement but retained character and reading-order errors in clauses 16–17; full transcription accuracy did NOT pass.
- Running service observed at 0.10.5; this acceptance used the updated on-disk engine, not that older service.

Task: 67e7ec46b3ae493d9a138d4ec6099fb0. Action log contains image_ocr only; no ChatGPT calls. Report: E:/AI/artifacts/ocr-agent-acceptance.json. Source comparison found במחסך instead of במחסן and misplaced words in the final sentence of clause 16. Model output also ended mid-sentence. No desktop UI or live MCP acceptance is claimed.

## 0.13.3 desktop-independent OCR regression
Three tests passed in 0.33s with normal local execution. OCR worker is mocked; the desktop stub rejects every desktop query except the global stop flag. Python compilation passed. Sandbox test run stalled after two tests; this is not locked-Windows acceptance. Background replanning and live service activation have not been verified end-to-end.

## 0.13.4 background recovery — 2026-11-07
Controlled real-runner test 69ce53f4afb84056b0bc56c850292f9d: initial model/tool desktop call injected as unavailable, then real Qwen and real OCR. Actions observe_screen (deferred), image_ocr; waiting_review after 23.39 seconds. No ChatGPT call. Recovery passed; Hebrew transcription retains errors. Not a real Windows-lock acceptance. Initial core run: 22 passed, two fixture failures (user feedback setting and invalid image bytes); fixtures isolated/corrected without changing live settings.

Final targeted regressions: 25 passed in 12.92 seconds (core task runner and OCR adapter). Launcher activation requested; Windows UAC pending at time of recording.

## Requested repeat OCR acceptance — 2026-11-07
Actual updated engine, no injected calls/failures, task b773723229ce44d5a22dfade4936eb43. OCR on; ChatGPT feedback off. image_ocr succeeded, then model attempted read_file on the JPEG (too large), then on generated OCR txt/json outside workspace (correctly denied). waiting_user after 26.36 seconds. End-to-end acceptance FAILED despite successful OCR. Live hub and gateway still 0.10.5; prior launcher remains waiting. Report E:/AI/artifacts/ocr-agent-acceptance.json. No real locked-session acceptance claimed.

## 2026-11-07 — ongoing OCR acceptance

- 31 targeted unit tests passed before the latest two-recognizer worker change (not desktop acceptance).
- Real Qwen task f36e844d14a64e84b55d47beeee75382: 44.2 seconds, three image_ocr calls, readable ordering but a remaining final-letter error.
- Real Qwen task 1551e1f5c15d491fb2d328ec92f3dbe3: 180-second timeout after 19 OCR calls with repeated crops; not successful. ChatGPT feedback disabled.
- Real session diagnostic reported locked=true, interactive=false. Existing image reading does not verify live window capture or input under lock.

## 2026-11-07 background capture development
- 14 focused fixture tests passed: desktop guards/background selection/GDI fallback, source-region offsets and bounds, model context.
- Actual agent test e30043d0d94b4a5290a16e2d4c9743c4 reached list_windows/window_inspect but failed at context-budget handling in 12.89s; not a successful visual acceptance.
- Post-reboot MCP task 03c281ed868b425081e279c46c755ca2 returned a real two-monitor desktop screenshot (86,635 bytes JPEG); Windows was unlocked. This does not establish locked-session support.
- Earlier document agent tests 50e30d9c32c1467b925365c787ca76b9 and 5002b9b609af435ea8fd3f89caebbbe0 returned readable clauses 16–17 with punctuation omissions, in 36.06s/34.84s respectively, without ChatGPT feedback.
- Changes remain Unreleased pending live acceptance and deployment; fixture success is not locked-desktop acceptance.
`n- Actual agent b2dcb851e91043abaf12651be391c4ef captured the non-foreground Local Agent window with target-window-printwindow, no physical input, in 21.58s. Returned image visually inspected: actual application content, 83,976-byte JPEG. Windows remained unlocked; this validates background-window rendering, not locked-session acceptance. The broader desktop/visual/OCR test run stalled and was interrupted; no pass claimed for that run.

## 2026-11-07 tabbed application diagnosis
- Historical task 2933ce45938f4f41ae947bd936099a2a contained dozens of repeated coordinate clicks. Delivery of input was mistaken for progress.
- Live read-only task dc379e2e62c8496fbc0a41a139bf2b7d (15.28s) exposed a context-loss bug: UIA recorded 16 tabs and the last selected jokes-notepad.txt, but model reported two inactive tabs. Selected-tab prioritization and explicit summary added.
- 17 targeted fixture tests passed, including selected-last-tab retention, repeated-input blocking, capture regions, and desktop guards.
- First live writing acceptance 8f5867378a28445abc63db1de172d987 failed in 63.92s: invalid coordinates and unsupported UIA click spelling. Not claimed successful. UIA click alias added before retry.
- Shared typing regression tests validate Hebrew, newline key events and intact emoji surrogate pairs. 18 focused tests passed. Further live retries remained unsuccessful; deployment is not yet claimed.

- 0.14.0: live local-agent task 09adc2beab4c447194821c52472bdfa5 succeeded in 16.89s using window_new_document and capture_screenshot. Three Hebrew jokes and line breaks matched UIA readback; final image visually checked, no blocking error dialog. Existing tabs preserved; test-created tabs remain open. 20 focused tests passed in elevated Windows environment; sandbox test run stalled. Other editors and locked-session interactive input remain unverified.

## 2026-11-07 — APC context foundation (development)

18 tests passed: test_project_context, test_model_memory, test_model_context, test_extensions_documents. Synthetic fixtures verify source freshness, annotation persistence, multilingual retrieval, scope exclusions, AST relationships, idempotent APC metadata import and recovery. UI/runtime additions followed this run and require new validation. Live model/UI/MCP acceptance remains pending.

Practical context acceptance and failed-attempt analysis are recorded in docs/DEVELOPMENT_IMPLEMENTATION_STATUS.md. Real model run used search/expand/related and passed the unchanged synthetic test. IAB UI search and annotations verified on isolated service. Public connector acceptance still pending.
# Plan reconciliation audit — 2026-11-07 (development source)

- Read original Codex chat `01a11fa8-42ea-71c1-9f92-7ade0ca7c9f9` (בנה את מערכת Ember Table), technical plan/mirror, handoff and source. No Ember product changes.
- Rechecked 24 pinned APC hashes and 142 source ZIP entries: all match. Persistent backup hashes match; both SQLite backup integrity checks return ok. Manifest-listed hub.sqlite3-wal/shm are absent; full application restore drill remains unverified.
- In isolated LOCAL_AGENT_ROOT, ran `python -m pytest tests/test_project_context.py tests/test_context_integration.py tests/test_core.py tests/test_model_context.py -q -p no:cacheprovider`: initially **35 passed, 1 failed in 16.89s** (missing context.register_tool). After completing all three locale descriptions in en/he/ru: **36 passed in 16.49s**. Fresh isolated `import hub.mcp_gateway` succeeds.
- Disposable fixtures reproduced four open gaps: disabled setting still schedules a scan; a request during an active scan loses its immediate follow-up; preserved-size/mtime edits leave search stale; long optional notes can omit required constraints from overview. Evidence and harness: `E:/AI/audits/plan-reconciliation-20261107/findings.json` and `probes.py`.
- Reread historical real Engine actions in context-acceptance-20261107-c: successful source retrieval/edit and pytest exit 0, with two recovered tool errors and final waiting_review. This is reused historical evidence, not a new acceptance run.
- No model inference, UI/browser session, fresh public ChatGPT acceptance, service restart, deployment or version release in this audit. Current exposed connector inventory has seven legacy task/chat/file tools and no context/index tools. Source registration and public discovery remain distinct.


## Index queue lifecycle — 2026-11-07

11 tests passed in 3.58s: test_context_indexing, test_project_context, test_context_integration. New cases exercise settings without scanning, explicit refresh while disabled, a concurrent request during a scan, and retry after failure. Fixture evidence only; cancellation/shutdown live acceptance and UI/MCP/agent activation remain pending.

### Active implementation: context and local indexing tools — 2026-11-07

- Required constraints are separated from optional annotation notes and pinned in the fixed model packet; oversized required data raises an explicit limit.
- Refresh now detects same-size/same-mtime changes using content hashes and extractor identity, and refuses missing roots before deletion reconciliation. This correctness-first implementation rereads contents on refresh; incremental performance optimization remains open.
- Local task tools now expose current-project index requests/status/background settings through the existing shared queue. The UI shows readable source/search/relations, optional technical JSON and background status/settings. Practical UI acceptance remains pending.
- 42 focused tests passed in 18.99s before the final fixed-packet/UI addition; 15 context/integration/indexing tests passed in 13.39s afterward. JS syntax check passed.
- Real isolated Engine run de0d65b8ed6746e6957d4cf123d95610 used context_search/expand/related, edited billing.py, preserved its test and ran pytest successfully in 34.38s. Final state waiting_review. Evidence: E:/AI/audits/context-live-20261107-resumed/acceptance.json. Ollama reported no loaded models afterward. This validates a narrow real-agent repair, not all plan phases.
- No production restart or release. Phase 1 and all subsequent completion gates remain active work.

### Continuing Phase 2 foundation — 2026-11-07

APC design contracts from project_connection.php (source/work location separation) and project_source_history.php (content identity/staging) informed a new Python candidate prototype. No PHP copied. Added manifest candidate creation, base-hash and revision checked staged snapshots, typed patch/work packet contracts, task/workspace binding and durable candidate events. Three fixture tests passed in 0.49s. This is not an integrated coding worker or activation system; caller serialization is provided by the Development service and cross-process fencing remains pending.

Current Phase 1 evidence: real Engine de0d65b8ed6746e6957d4cf123d95610 completed a narrow repair in 34.38s, test unchanged, local model unloaded. IAB isolated port 18976 verified folder registration, automatic scan, readable map/search/source, background setting disable and persistence after reload. Disposable restore drill restored 142 files and two SQLite databases with integrity ok (E:/AI/audits/restore-drill-20261107/result.json). This does not verify production activation.

Active temporary UI server: PID 8044, port18976, isolated root E:/AI/audits/context-ui-resumed-20261107; exec session72874. Stop only this owned server after remaining UI tests. No production restart. Full-plan implementation continues; do not mark phases 1–5 complete.


### Candidate execution and direct facade — 2026-11-07

- Added candidate_test with explicit revision, argv-based pytest, environment allowlist, bounded output, timeout/process cleanup, before/after hashes and durable evidence. This is trusted same-account execution, not an OS sandbox.
- Added candidate_diff against the original snapshot and validation that a manifest cannot redirect the revision directory. Local tools, authenticated HTTP routes and MCP registrations share Development; public connector deployment remains pending.
- Real Engine task 13617df2c83f4f0cb8da7020e1de4a8c used candidate_create/inspect/patch/test with Qwen3.5:4b in 31.03s. Test passed at candidate revision 1; original source and original test remained unchanged. Full action records were inspected. Final task state waiting_review; no activation. Evidence E:/AI/audits/candidate-live-20261107/acceptance.json. Ollama empty after unload.
- Latest focused run: 12 fixture tests passed in 5.58s (development API/workspaces/context integration). HTTP and MCP imports passed. Earlier broad run had 36 passes and one test-placement NameError; corrected, then reran affected tests successfully. This is not full QA/QC.
- APC attribution remains source/work separation and source-history hash contracts, implemented in Python; no PHP execution. Cross-process fencing, full work packets/guidance, Git candidates, UI development review, resource/model management, Guardian and public ChatGPT acceptance are still pending.


### Guidance and review UI continuation — 2026-11-07

- Added durable revision/consumer-epoch fenced task_guide/task_guidance_status HTTP/MCP paths. Guidance is included in fixed model context; receipt/in-packet events explicitly do not prove execution. Required-tool evidence gates finalization with bounded correction attempts.
- Real first guidance run dd022b291ab842d6a0e72ef05b289ef7 received guidance but skipped candidate_diff. Kept failure evidence. After adding explicit evidence requirements, run 32a4df880c3b48d1b61ae77eb3504888 used candidate_create/patch/test/diff in 41.56s, preserving live source/tests, waiting_review. Two recovered test selector errors are in full actions; runner now accepts validated file.py::test_function selectors (9 focused tests passed in 4.11s).
- Guidance/core/API tests: 33 passed in 18.90s. Model protocol/core/API tests: 31 passed in 15.56s. Protocol adapter accepts only whole-response, catalog/schema-valid legacy JSON tool envelopes, never calls extracted from prose.
- Qwen2.5-Coder7B benchmark failed as director: first run 8ef824d718624f87aafd924b38d498a2 emitted textual tool JSON (33.62s). Adapter run eef8221e6cfb49158c7ade238851b62e executed create/diff but skipped patch/test (10.91s). Neither is a success; model remains non-default. Both unloaded their model afterward. Do not compare failure timings as equivalent performance.
- IAB actual review on isolated port18977 displayed candidate revision, original objective and unified diff. Fixed RTL code rendering after screenshot inspection. Proof E:/AI/audits/candidate-guidance-verified-20261107/development-review.jpg. Guidance submission through this UI is still untested.
- Old isolated UI server8044/18976 stopped after identity verification. New test server PID15956, exec84297, port18977 uses candidate-guidance-verified audit state. Production unchanged.


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
### Development continuation — 2026-11-07: coding worker and Hugging Face

- Agent-owned required worker task 80f93df5db2248d19f9360ea7995be96 passed in 36.24s, using candidate_create/candidate_repair/candidate_diff with no tool errors. Original code/tests preserved; worker tests verified; final waiting_review, no activation. Evidence: E:/AI/audits/coding-worker-engine-required-20261107/acceptance.json. Supersedes pending worker acceptance, not full plan completion.
- Provider/catalog fixtures: 5 passed in 0.91s. Catalog/context integration: 7 passed in 7.12s.
- Actual IAB on isolated API18980 searched Qwen's public Hugging Face repository, inspected license/files, installed qwen2.5-coder-0.5b-instruct-q4_k_m.gguf (491400064 source bytes), observed installed/verified, and recorded zero resident models afterward. Evidence E:/AI/audits/model-hf-ui-20261107/installation-evidence.json and catalog-hf-ui.png. This is a fresh provider download, not a local model inference test. Production unchanged.


## 2026-11-07 — conversation continuity and ongoing product QA
- 34 conversation/model-context/core fixtures passed in 21.75s; 25 API/memory/Guardian/job fixtures passed in 11.13s. These are fixtures, not public connector acceptance.
- Real Qwen3.5:4b Engine recall: 22 seeded prior turns, required fact in turn 4 outside the latest-12 seed. Model called conversation_history and returned the exact Hebrew identifier in 9.19 seconds. Evidence: E:/AI/audits/conversation-memory-live-20261107/acceptance.json. Models unloaded afterward. This is narrow recall acceptance, not a year-long workload benchmark.
- IAB port18981: settings category navigation, safe Markdown display, memory dialog, pagination from10 to20 turns, saving continuity note revision1 and reopening with the same text succeeded. Proof: E:/AI/audits/conversation-memory-live-20261107/continuity-ui.png. Other menus and native browser remain under QA.
- Earlier scoped-worker context-window failure was corrected with task-scoped tool groups. Real task7c047b4cd97641a8b378dc83691400ee completed required repair/diff/tests in29.14s with original source/tests preserved (worker-tool-discovery-20261107).
- Guardian Engine acceptance819ebac5b4234192a6a9bec884e76a8f failed after81.98s; retry ef35dc80a8194657b93546b5fa4c14ff exceeded420s while repeatedly observing stale index status. Both are failures, not verified deployment. The direct-refresh status bug was repaired; a new isolated run is in progress.
- Full earlier suite252 passed/1 fixture failure in56.23s; settings fake-client preflight fixture corrected and focused tests passed. Full latest suite still required.

2026-11-07 continuation: Python compilation succeeded for browser extension/view/IPC callers, API, gateway and tool registry. Seven session-transfer/conversation-memory regression tests passed in 5.26 seconds. This does not validate extension lifecycle, browser visual appearance, Chrome import on a real account or public MCP availability.

- Nine memory-review, conversation-history and session-transfer regression tests passed in 6.03 seconds. Review coverage includes disabled default, persistence, missing-context downgrade, replay protection, cross-chat isolation and stale-source rejection. These are fixture tests, not ChatGPT acceptance.
- Qt extension installation returned a real installed/disabled record. Enabling a minimal Manifest V3 extension exited the isolated process with code 1 in repeated direct Qt and view-backed probes, before returning from setExtensionEnabled. Full lifecycle failed; shared enable action is blocked.
- Real Guardian Engine acceptance task 30fe4b6a36794af989245c96a343a5a3 exceeded 420 seconds, paused, repeated list_files after candidate_repair, and did not activate a release. Original source preserved; Ollama models unloaded. Evidence: E:/AI/audits/guardian-engine-statefixed-20261107/acceptance.json.

- IAB on isolated port 18981 saved optional memory feedback enabled with MCP preference and displayed the saved state. Proof: E:/AI/audits/conversation-memory-live-20261107/memory-feedback-ui.png. Registered MCP Python adapters made real HTTP requests to the same server, read those settings, submitted and retrieved a source-bound review; false context availability correctly produced unavailable. Evidence: memory-review-mcp-adapter.json. This is adapter/UI parity, not a fresh public ChatGPT connector test.

- Real memory-feedback Engine run b returned the correct name in 14.52 seconds and invoked both tools, but independent action-log inspection found the wrong source task in its review packet. This run is NOT accepted; independent-review.json corrects the weak tool-presence-only script verdict. Added exact evidence_quote validation and a source-excerpt acceptance check; rerun pending.

- Real local Engine memory-feedback run d completed in 26.11 seconds, recovered after a deliberately rejected mismatched source ID, requested review with the correct original Hebrew quote, and accurately reported pending MCP feedback. Correct answer and source packet were inspected independently; Ollama ended empty. Evidence: E:/AI/audits/memory-feedback-engine-20261107-d/acceptance.json. This verifies local retrieval/request/fallback, not an actual ChatGPT response. Latest seven focused memory/coding-worker tests passed in 8.43 seconds; preceding 14 API/coding/memory/session tests passed in 19.10 seconds.

- Full suite snapshot: 270 tests passed in 66.97 seconds. Later conversation-submit scalability changes separately passed 11 conversation/recovery/memory tests in 6.44 seconds and three history tests in 6.78 seconds. Full suite must be rerun after final remaining edits.
- Synthetic 10,000-turn storage benchmark retained all 10,001 turns after a new request: literal search 0.080 s, submit 0.110 s, DB 104,927,232 bytes. E:/AI/audits/memory-scale-20261107/benchmark.json. This measures storage/dispatch, not year-long model reasoning quality.

2026-11-07 Guardian real Engine acceptance: task cefcb9828d824ebaba204a7285828c23 reached waiting_review with patch-worker ACTIVE_VERIFIED, 174.69 seconds and 60-second stabilization; original source preserved, resident models empty. Evidence: E:/AI/audits/guardian-engine-syntaxretry-20261107/acceptance.json. This is an isolated patch-worker activation, not full-app production acceptance.

2026-11-07 Memory-feedback adapter verification: 8 tests passed in 4.05s covering prompt return of pending reviews, current deduplicated replies, and MCP functions using the authenticated HTTP service with shared persisted settings. Missing original context downgraded an attempted confirmation to unavailable; original history unchanged. This is adapter integration, not a live ChatGPT response.

2026-11-07 Full regression after memory source binding, chronological fallback, worker Python preflight and MCP review observation: 273 passed in 69.52s. The subsequently added authenticated HTTP/MCP integration test passed in the separate eight-test run (4.05s). No production deployment.

2026-11-07 Conversation viewport: 17 tests passed/20.11s (conversation memory and HTTP API). IAB isolated port18982 with 65 synthetic retained turns: observed pages35–64,5–34,0–4, expanded first-turn history_probe evidence sequence0, returned to35–64. Screenshot E:/AI/audits/conversation-pagination-20261107/history-oldest.png. This is UI history navigation, not new model recall acceptance. ServerPID7448/session11323 remains isolated. Initial attempt to share18981 state correctly failed the exclusive owner lock; new root used.

Decision anchors: first regression run19passed/1failed because the test attempted unsupported Store.update(goal); changed test to simulate external DB corruption explicitly. Rerun7passed/26.38s. Real Engine trial13.22+18.47+12.91s FAILED: wrong source ID rejected, zero cursor produced empty list, final falsely claimed missing history. Corrected current-task identity in continuity and zero-as-start cursor; real rerun pending. Models unloaded after failed trial.

2026-11-07 Real decision-continuity Engine acceptance passed: conversation-anchors-engine-20261107-b/acceptance.json. Three independent Engine turns took12.05s/9.56s/8.47s. Model stored the first exact user quote, linked a later correction after20 filler turns, then recalled both current and former names after another20 fillers from the saved source-bound anchors. Inspected actions confirm writes/read and supersession link. Both sources preserved, resident models empty. This proves this scenario, not arbitrary year-long semantic recall or public ChatGPT feedback. Focused conversation/MCP wait tests12passed/18.38s.

2026-11-07 Live ChatGPT memory feedback: in the user-authorized original conversation, Codex IAB sent a source-quotation review about the Notepad-window-only screenshot request. ChatGPT returned matching review_id, confirmed/context_available=true and explicitly limited its finding to the historical request. Saved raw reply, screenshot and verified persisted annotation in E:/AI/audits/chatgpt-memory-feedback-live-20261107. The shared parser/service accepted it and original history was unchanged. Transport was manual Codex IAB, NOT the local agent automatic browser dispatch and NOT public MCP acceptance. Correlation regression tests10passed/4.10s, including wrong/missing review ID, invalid boolean and non-object JSON.

2026-11-07 Real Engine feedback continuity: E:/AI/audits/chatgpt-memory-feedback-live-20261107/engine-continuity.json. Qwen used conversation_memory_reviews to read the actual IAB-acquired ChatGPT reply, returned window-only screenshot scope and explicitly said feedback does not prove desktop execution.14.66s, waiting_review, resident models empty. This verifies consumption of real feedback, NOT automatic outbound dispatch. Nine focused memory/history tests passed16.22s before the final status-refresh edit; UI feedback-history rendering and public connector remain unverified.

2026-11-07 IAB UI feedback evidence: isolated18983/PID23808 (session30352) using SQLite backup of the live-feedback audit store, not production. Opened memory/history dialog, observed confirmed feedback/exact source quote and expanded original-source content successfully. Screenshot E:/AI/audits/feedback-ui-20261107/feedback-source.png. User-facing history kept intact; no model loaded.

2026-11-07 Full regression after feedback history/context propagation, decision anchors, viewport paging and fresh final-review state:278passed/77.44s. No production rollout; automatic local-browser outbound feedback and fresh public MCP remain acceptance gates.
# Memory-feedback flag validation — 2026-11-07 (Unreleased)

Shared service rejects string/numeric/container values for context availability and enabling feedback; invalid replies preserve pending status and original source. `tests/test_memory_review.py`: 17 passed in 4.65s. `tests/test_api.py tests/test_dispatch_wait.py`: 20 passed in 8.15s. These are fixture/API adapter tests, not automatic live ChatGPT/MCP deployment acceptance. No production restart performed.

# Long-history retrieval and cursor integrity — 2026-11-07 (Unreleased)

Real Engine recall from1,000 synthetic turns and26 anchors FAILED (11.64s,10.91s) in conversation-long-recall-20261107 and conversation-long-recall-20261107-b. Source IDs/codes absent from initial packet; action logs confirm insufficient retrieval and unrelated acknowledgement, so neither result qualifies as success. Models unloaded after each. Generic guidance insufficient. Source-preserving cursor regression plus API/conversation/wait tests:26passed25.44s. Automatic public connector and broader continuity remain unverified.

# Indexed decision recall — 2026-11-07 (Unreleased)

Full regression after indexed retrieval/audit changes:297passed94.57s. Unit/adapter success does not override the independently observed d answer failure.

Audit-event retest d took14.88s and returned correct codes with logged source IDs, but independent answer review FAILED: final sentence invented removal of the correction. Evidence conversation-long-recall-20261107-d/independent-review.json. Verifier now reports retrieval_verified separately and leaves overall verified unset until independent review; keyword/source checks alone do not certify answer correctness. This semantic failure remains open.

Real Engine acceptance conversation-long-recall-20261107-c passed11.30s:1,000 synthetic turns,26 anchors, requested codes absent from recent-eight packet, automatic source retrieval supplied original and correction with source IDs, answer correctly identified both. No remote feedback used. Model unloaded. This supersedes failure for this fixture only, not all semantic continuity.47 focused conversation/memory/context/API fixtures passed27.29s, including correction-chain expansion when correction omits subject, chat isolation, stale source and existing-anchor index migration. Audit-event retest pending.

# Historical report provenance — 2026-11-07 (Unreleased)

conversation-long-recall-20261107-e:12.14s, real Engine used conversation_memory_reviews and conversation_history; final codes and source positions137/413 match actual records, independent-review.json passed. Original replies preserved. conversation-unanchored-recall-20261107:29.11s FAILED; phrases with Hebrew article differences returned chronological fallback, then model confused history reading with forbidden desktop input. Failure preserved and models unloaded.19 conversation/context fixtures passed17.40s;20 API/wait fixtures passed8.28s before schema-message wording change. Whole continuity/public transports remain incomplete.

# Unanchored request retrieval — 2026-11-07 (Unreleased)

Added native Hub FTS5 original-request index, migration/triggers, chronological exact+token candidate union and per-record source roles. No APC code reused.38 focused memory/review/API tests passed27.47s before role labels;20 conversation/model-context tests passed17.33s afterward, including exact later question not hiding older approximate sources, page traversal, chat isolation and source update.

Real Engine conversation-unanchored-recall-20261107-b retrieved correct IDs10.05s but independent review FAILED speaker attribution and language. c retrieved both IDs13.33s but reversed current/old in final answer despite quoting correct chronology. Both independent-review.json files reject overall success. Models unloaded. Next required work: validate claims against retrieved sources/chronology before finalization; do not continue optimizing retrieval alone or treating keyword hits as answer correctness. Public automatic feedback/deployment remains unverified.

# Local historical-answer review — 2026-11-07 (Unreleased)

Added bounded source-only extraction, exact quote/ID validation and up to three review attempts using the already selected model. Same-model review is not independent proof. Two real trials incorrectly approved reversed drafts; independent-review.json marks both failed (conversation-unanchored-review-20261107 and -b). Pure history tasks now review and return the separately source-derived answer instead. Real Engine -c26.51s passed independent factual review: correct current/former codes, original quotations, chronology and distinction between questions and corrections. Terminology still says attached documents instead of conversation sources. Model unloaded; no GPT contacted.23 latest review/conversation/context/wait fixtures passed4.00s;17 earlier review/API fixtures passed6.11s. No public connector or universal recall claim.


### PLAY connection development QA - 2026-11-07
- Focused bridge/transcript/protocol/API run:42passed12.27s, before final new-conversation endpoint/test. JavaScript syntax checks passed before the last UI refinement.
- Actual Codex IAB UI, isolated root E:/AI/audits/play-ui-20261107, API18984: observed empty dialog caused by detached controls; repaired shell initialization, reopened PLAY/MCP panels, added an isolated project, saved a synthetic ChatGPT URL with MCP preference and favorite, reloaded and observed all three persisted. This is UI/settings acceptance, not a connection to that synthetic URL.
- Public connector discovery still exposes seven older tools. New connection/memory tools are not yet accepted publicly. No production restart or model load. New-conversation setup and hidden-pane traffic still need actual native agent browser validation.

2026-11-07 latest validation: full regression306passed95.20s; subsequent focused bridge/API/protocol run43passed23.91s includes the newest new-conversation bootstrap fixture. Full-suite collection preceded that one added test. Both runs exited0. Actual automatic browser/public connector acceptance still pending.

2026-11-07 update: added native AI connection catalog/cards for ChatGPT (Web PLAY/MCP), with Claude/DeepSeek explicitly not implemented. Reviewed APC browser/local-bridge candidates in docs/APC_BRIDGE_REUSE_REVIEW.md and manifest; no bridge code port claimed. Latest44 focused tests passed13.00s before connector catalog addition. Live isolated PLAY setup reached loading/not-ready error; fixed visible opening/attention status and45-second setup bound. Signed-in native bootstrap remains unverified.

## Browser chrome and connection QA — 2026-11-07 (Unreleased)
58 focused tests passed in 16.51s: API, browser UI queue, ChatGPT bridge, PLAY protocol, bridge transcript, browser input and DOM. JavaScript syntax and Python compilation passed. This is not a new full-suite result.
Offline Qt fixture used the real BrowserView under an inherited dark parent stylesheet; widths 480 and 820 verified painted light chrome, in-bounds toolbar controls and retained menu actions. Artifacts: E:/AI/audits/browser-chrome-20261107/chrome-480.png, chrome-820.png, render-evidence.json. These are offline widget renders, not live desktop or website acceptance.
Actual Codex IAB checked QA port 18984: selecting the ChatGPT tab updated the live frame/address after the serialization repair; a 700px viewport showed the model name on one line; the login-required probe remained visible during polling. Screenshots: sidebar-700.png and play-login-required.png in the same audit directory. Viewport override was reset afterward. The isolated native window was shown using the product browser control. Signed-in PLAY bootstrap/ACK and public MCP acceptance were not performed; the isolated profile is logged out. No production restart or new APC bridge code integration.

2026-11-07 saved-tab restoration:31 bridge/transcript/PLAY tests passed6.00s. Added fixture proving existing-tab login/loading failures raise the observed reason and show the existing tab rather than report successful restoration. This is regression evidence, not live authenticated PLAY acceptance. Production unchanged.

2026-11-07 uncertain handoff continuity:50 bridge/transcript/protocol/API tests passed13.31s. Fixture persisted an uncertain send, stopped/reloaded controller, attempted chat switch and new listen, verified both blocked before browser access and retained state/transcript. Original context remains accessible. Live authenticated acceptance remains pending.

2026-11-07 full regression completed:315 passed85.35s, exit0 (session6559). Actual IAB after user login: connection probe changed to ready. Clicked new PLAY conversation; observed sending state. Delivery/remote reply not yet verified. Transport tab selection was also observed updating saved-route selector in IAB. Production unchanged.

2026-11-07 actual PLAY bootstrap: after user login, IAB probe ready; new conversation sent instructions and displayed actual ChatGPT acknowledgment (12:38:47). Screenshot browser-chrome-20261107/play-live-bootstrap.png. Additional local conversation appeared during temporary-to-final remote URL transition; linking/deduplication gate remains open. No computer-action/hidden-pane success claimed.

2026-11-07 provisional URL fix:32 bridge/transcript tests passed6.92s. Fixture tests same-tab + matching new outbound message, rejects unrelated text/other tab, preserves pending text and restores permanent binding from disk. Full315-test run preceded this edit. Live bootstrap previously exposed duplicate local chat; post-fix live repeat required.

2026-11-07 post-fix live PLAY attempt failed before submission (busy or unsent draft). No pending outbound message recorded. Existing draft preserved/no resend. Screenshot E:/AI/audits/browser-chrome-20261107/play-draft-blocked.png. This does not verify provisional URL migration; it remains a release gate. Isolated API now5744/18984, native profile retained, production unchanged.

2026-11-07 preflight diagnostics:51 bridge/transcript/API tests passed13.63s;26 bridge tests passed5.59s after final metadata correction. Fixture verifies draft vs generation rejection before composer access, no pending send, not_sent classification, and preservation of uncertain status for submission timeout. This is fixture evidence; live duplicate-chat acceptance still pending.

2026-11-07 probe metadata follow-up:44 ChatGPT bridge/API tests passed12.44s; JavaScript syntax passed. Actual IAB screenshot play-existing-bootstrap-draft.png shows retained bootstrap-looking draft, not successful delivery. No draft altered. Live recovery acceptance remains open.

2026-11-07 draft provenance fixtures:34 passed6.54s. Exact complete local outbound draft resolves source chat/message/status; prefix, human message and modified text rejected. Read-only lookup, no browser mutation. Live draft ownership has not yet been queried with updated QA imports.

2026-11-07 actual IAB provenance probe: authenticated homepage draft blocks send; no generation active; exact local outbound match absent (draft_source null). Screenshot play-draft-probe.png. This refutes treating the observed prefix as sufficient ownership evidence. No clear/resend; live PLAY recovery still incomplete. QA API26856/18984.

2026-11-07 reversible draft service:19 draft/API fixtures passed7.74s; JS syntax passed. Fixture archives Hebrew text, restores it, prevents overwriting a current draft and retains saved copy. No live recovery or public MCP claim.


## PLAY draft recovery — 2026-11-07

Two draft fixtures passed (0.65s); app.js syntax passed. In isolated IAB UI on port 18984, archived 23,342 characters before clearing; the initial fill selected but did not erase text. Targeted unchanged-draft fallback then verified empty composer. Restoration retained all text but added six newline characters (two runs of three), so exact verification correctly failed. Archived restored content and verified clearing again. Original copies retained. Production untouched; full PLAY task roundtrip remains pending.

Live new-conversation PLAY after recovery: IAB confirmed listening and durable final conversation URL ending 593247d2331b after reload (temporary local-chatgpt URL resolved). Screenshot: E:/AI/audits/browser-chrome-20261107/play-linked-final-url.png. Stale probe warning is hidden while listening. Full task execution roundtrip still pending.

## Idle PLAY browser access — 2026-11-07
21 focused browser-access/draft/API tests passed in8.29s. Real IAB isolated18984: refreshed frame, selected connected tab, clicked composer, typed and sent a read-only browser_tabs request while PLAY remained enabled. Local transcript confirms user request at12:54:09. Browser pane hidden during processing. Task/result acceptance pending.

PLAY live acceptance exposed an absent initial cursor in empty conversations. Fixed bootstrap receipt anchoring and old-session fallback.28 bridge/access tests passed5.52s, including existing missing-cursor anti-replay regression. Previously consumed action was not replayed; submitted a new read-only request through IAB for live verification.

After cursor fix, a fresh user request was recognized and queued while pane hidden. ChatGPT instead used its installed MCP connector and reported Local Agent unavailable; isolated QA database correctly contains no task for that remote call. PLAY protocol v2 clarifies route ownership.1 protocol test passed0.25s. Revised live roundtrip remains pending; no complete acceptance claimed. Screenshot E:/AI/audits/browser-chrome-20261107/play-transport-collision.png.

## PLAY signed-in acceptance and repairs — 2026-11-07
Live protocol v2 acknowledgment succeeded in the existing conversation. Actual task 9c16c33407eb4243b40acfc9c6ee0b41 failed before tools due catalog context overflow. After desktop catalog reduction, task 373ad553ef3443708054c4946e105032 called browser_tabs three times and observed seven tabs, but its completion gate misread a prohibition as a close request. No close action occurred. Fixed negation and proposal handling. Transport recovery also needed generic-error receipt reconciliation and consumed-reply idle restoration. 34 core/context tests passed16.87s; 39 close/bridge tests passed7.59s; subsequent32 bridge tests passed7.89s. Full332 tests passed89.00s before the last recovery changes. Production and public MCP remain unchanged. Real successful end-to-end result delivery still pending.

Full335 tests passed102.49s before the keyboard-submit adjustment. Task cb7d881aca6648ab8fca4558b5f5f04a returned seven tabs after one browser_tabs call, but automatic feedback remained a draft and delivery was correctly uncertain. Existing draft submitted once through observed IAB UI for recovery; this is not automatic end-to-end acceptance. New keyboard-submit adapter:32 bridge tests passed7.70s.

Automatic PLAY result delivery verified: task708dccf24c7c49d2819ade085bb2a339 ran browser_tabs once, returned7, and persisted chatgpt_delivery sent=true with new message4937b254-a6c8-44b8-a49d-8c1af105605b. Independent IAB inspection of the linked conversation confirmed automatic result and ChatGPT answer7; no manual send for this task. Task execution4.17s. Evidence E:/AI/audits/browser-chrome-20261107/play-automatic-result.json and .png. Local listener remained waiting_reply despite remote answer; added safe idle refresh for waiting_reply and frame-only viewing (35 tests passed8.44s), recovery verification pending. This proves this read-only task roundtrip, not all PLAY/memory requirements.

2026-11-07: Grouped-message PLAY mapping live-verified on isolated API18984/PID23880. Task708dccf24c7c49d2819ade085bb2a339 automatically delivered result7; after mapping fix runtime last_reply=7, phase=listening, error empty; IAB tab12 showed the same answer and listening badge. Evidence: E:/AI/audits/browser-chrome-20261107/play-automatic-result.json. No manual result send for this task. Earlier manually recovered task is not counted. Latest focused tests35passed7.79s; full regression session90336 running. Native Hub implementation, no APC port.

2026-11-07: Live task ef3e9200def345ca8890fe740bd23c50 read source result7 and invoked conversation_memory_review. Browser ChatGPT returned correlated review458e2235220847a3b9c7d50f26280530, confirmed with accessible historical evidence in12.90s. Subsequent local answer-review distorted the feedback; this is NOT complete task acceptance. Saved memory-live-result-b.json. Added deterministic memory-only feedback reporting and explicit assistant-report source retention;28 focused tests passed8.35s. Earlier full337 passed91.63s predates these changes.

Live retry37f186b1db8d476f81e1489b0f86acc6 retrieved the correct saved browser review but final validation failed because saved-review evidence was omitted from the reviewer packet. Fixed evidence retention and added history/order regressions;30passed4.66s. New isolated Engine task a2d0ccfbe7ab4998b8d8a3483fe20176 running against API18984 PID22516/session28760.

2026-11-07 real Engine acceptance d: a2d0ccfbe7ab4998b8d8a3483fe20176 completed execution in24.84s (waiting_review). Exactly conversation_history then conversation_memory_review; final text preserves confirmed feedback, exact source7 and remote evidence, explicitly disclaims current-machine verification. This reused the correlated saved browser response from the earlier live consultation, not a second remote send. IAB displayed the same final text and listening status; evidence memory-live-result-d.json and memory-feedback-success.png. Production unchanged; arbitrary recall and public MCP acceptance remain unproven.

Full current regression:345 tests passed88.66s, session60964 exit0. Includes latest feedback/history report fixes; real acceptance scope remains the isolated scenarios above.

## Project binding / PLAY continuation acceptance — 2026-11-07

Full regression after the final code changes: `python -m pytest -q`: **352 passed in 96.25 seconds**. Tests include same-chat candidate continuation, cross-chat rejection, desktop/API parity, exact file paging, manifest compaction and feedback receipt reconciliation. This is regression evidence, not full product QA.

Real agent task `5f50adce769d45a5b675d1486fa11080` used read_file, tools_enable and project_bind, preserving the chat and changing future workspace to local-agent-hub. Task `7d9a370c25bf4495a37f70a15f4d4af7` used candidate_create and created isolated candidate `27873bf626e64134b65416ad48c11a1d` (233 files). Subsequent failed tasks exposed context-size and cross-task ownership issues; these were fixed rather than counted as successes. Live continuation task `519a0e529fb44622982e250c38872df2` has been observed running via actual MCP `get_task`, with successful candidate_inspect actions. Final outcome is recorded in `E:/AI/audits/browser-chrome-20261107/resumed-task-mcp.json`.

IAB verified the enabled project selector and persisted project selection. Evidence: `project-binding-interface.png` in that audit directory. Actual MCP call_tool forwarded to HTTP on port18984 and candidate_inspect returned HTTP200. The externally connected public MCP still points to a different instance; public deployment/parity is not claimed. No production activation, commit or release was performed.

Follow-up: the live 4B run initially repeated tool enabling/inspection because only its latest tool group fit inference input. A bounded factual ledger of successful tool names now survives context compaction without changing the original objective or durable history; candidate Git detail is summarized separately. After reloading and resuming the same task, actual candidate_read and paginated read_file calls completed and task519a0e529fb44622982e250c38872df2 reached waiting_review. This verifies resumed execution, not the correctness of every claim in its generated summary or completion of the entire development plan. PLAY result evidence now also includes candidate/project/context tool results.

### Supervised code execution — 2026-11-07
The shared PLAY/MCP director contract now assigns map retrieval, task decomposition and evidence review to the supervising model. It requests focused indexed sources/related tests and delegates candidate repairs to the configured coding model. New MCP `coding_model_settings` reads/changes the same persisted coding model as the UI without replacing the general/vision model. In the audit instance the previous coding_model was empty; it is now saved and read back through MCP as `qwen2.5-coder:7b`. This confirms configuration, not yet a completed Coder repair. Candidate/project/context actions are included in PLAY feedback. Resuming an existing handoff restores its authorized objective if pause handling had cleared it.

Regression run after context/progress fixes: 353 passed in92.35s. Subsequent supervision changes:52 focused tests passed, one protocol ordering assertion failed and was fixed by retaining the original transport rule first; the protocol/API rerun passed3 tests. Final combined verification follows. Public MCP deployment remains unverified.

Final checkpoint for this repair: full suite353 passed in96.35s; after the last catalog-focus change,8 binding/protocol tests passed in4.26s. Desktop-dispatched coding now exposes the development catalog without unrelated UI schemas; explicitly enabling desktop/browser groups restores those tools. Live resumed task c6d725a36a134b708a3e8dd1e6528f9f observed missing index, ran context_refresh (234 indexed files), and then context_search returned source references. Evidence: E:/AI/audits/browser-chrome-20261107/map-resumed-mcp.json. This is actual local agent execution observed through the local MCP facade, not a claim that the entire delegated development task or public connector deployment is finished.

### 2026-11-07 PLAY preparation recovery
- `pytest tests/test_chatgpt_bridge.py tests/test_project_binding.py -q`: 44 passed in 9.58s. Includes preparation-only recovery and rejection of changed/partial drafts and post-submit retry.
- Live isolated instance 18984: completed mapping task c6d725a36a134b708a3e8dd1e6528f9f feedback appeared in linked ChatGPT conversation; bridge advanced to waiting_reply/submission_started. Director continuation still under observation. Public MCP deployment not updated by this check.

- Linked ChatGPT reviewed the mapping, rejected unsupported local-model claims, and emitted step 009. Real local MCP then returned task 07961d751a55479385f8351c77144086 running with completed project_index_status/context_search actions. Evidence: E:/AI/audits/browser-chrome-20261107/play-continuation-mcp.json and play-feedback-recovered.png. This proves continuation, not completion of candidate repair or the full development plan.

- Full regression suite after PLAY recovery changes: 357 passed in 92.10s. This is automated regression coverage, separate from the live continuation evidence above.

### 2026-11-07 failure feedback and lookup continuity
11 model-context tests passed in0.12s.40 bridge tests passed in9.10s, including failed/waiting_user/waiting_desktop feedback retaining the original objective. Prepared an independent URL-validation acceptance test in isolated candidate27873bf626e64134b65416ad48c11a1d revision1; source unchanged. Asked linked ChatGPT director to run it through the agent, then direct Qwen2.5-Coder repair with read-only tests. This is acceptance preparation, not completed model repair.

2026-11-07 supervised self-repair follow-up: full suite initially 360 passed / 1 failed (legacy missing action_id). Fixed fallback and updated recovery test to assert actionable feedback and no uncertain-action replay; 45 focused passed17.71s; full361 passed93.88s. Subsequent resource warm-handoff regression:4 passed1.26s. Real PLAY step010 ran four failing URL tests; director issued step011 candidate_repair using qwen2.5-coder:7b. It failed before edits because primary warm model was unregistered. Error returned automatically; director issued diagnostic steps012/013. Audit runtime restarted with fixes, explicit primary load verified. No completed source repair or public MCP deployment asserted yet.

Further validation:363 full tests passed100.72s before the final no-op/director-yield changes;31 focused engine/worker tests then passed20.75s. Real Qwen2.5-Coder loaded alone (5.47GB VRAM), produced unchanged source twice; revisions2/3 failed4 and passed8. These are explicitly failed attempts, not successful repairs. Original acceptance test unchanged. Added no-op rejection and immediate director return; runtime PID23964 loads these fixes.


### 2026-11-07: observed ChatGPT/Qwen self-repair acceptance
Real Web PLAY step 014 used Qwen2.5-Coder 7B to fix BridgeTranscript.link URL validation in isolated candidate revision 4. Model time 44.33s; acceptance and existing tests: 12 passed in 2.44s. Independent hash checks confirmed protected tests unchanged. ChatGPT received actual diff/results, requested read-only review step 015, then accepted the isolated repair for Codex integration review. Evidence: E:/AI/audits/play-ui-20261107/self-repair-acceptance.json and director-review-complete.png.
Codex integrated only the hash-verified source change and independent acceptance fixture into shared source. No production deployment or public MCP parity is claimed. Earlier full suite: 366 passed in 94.48s; post-integration full regression is being recorded separately.
Fixed global evidence compaction: diff changed-file counts and bounded path summaries survive omitted patch bodies; omitted changes no longer appear as an empty files list. Focused model-context regressions: 12 passed in 0.11s. These are native Hub fixes, not copied APC components.
Remaining: production activation, public MCP end-to-end parity, full Guardian upgrade/rollback acceptance and broader implementation-plan/UI QA. The full plan is not complete.

Post-integration regression: 371 passed in97.03s. Director review step015 actually called tools_enable, candidate_inspect and candidate_diff; it accepted the previously recorded 12-test repair result, but did NOT run a separate candidate_test/candidate_read. Do not describe it as a second independent test run. Codex subsequently ran the full shared-source suite.

2026-11-07 Git acceptance (in progress): user authorized MellowYAK/MellowCodex publication and subsequent validated-change commits. Agent preflight initially repeated filtered empty ls-remote output; paused that read-only task, supplied precise director guidance, and a second agent task observed REMOTE_EXIT=0 REF_COUNT=0 with credential.helper=manager. Global shell evidence guidance now recognizes legitimate empty listings and asks for one explicit count/exit check instead of repeated filters. Publication rules added to AGENTS.md; .gitignore excludes runtime secrets/databases/profiles/artifacts. No push success asserted at this checkpoint.


### Git publication and runtime recovery — 2026-11-07
Agent task d013a2a334d343718be75384e29ef44e performed the initial commit and push to https://github.com/MellowYAK/MellowCodex, branch main, commit b535fb37f8d3181914d3142e7de6993cdf8779f7. Its command output confirms matching local/remote HEAD and clean status. Codex reviewed 239 staged blobs (1,714,965 bytes) before publication; no scanned credential patterns, sensitive extensions or oversized files were found. This was supervised execution with explicit director commands, not an unsupervised Git benchmark.
Audit runtime 18984 restarted as PID23984 with current evidence-compaction/shell-guidance fixes. PLAY restored connected/listening with no pending outbound replay. Agent task af144d8db2d343278a4afb6f4a24771f then executed project_git_status and one run_shell status check, correctly interpreted empty output as clean and completed without the earlier loop. 14 focused Git/model-context regressions passed in2.84s after the shell guidance edit. Production/public MCP services were not restarted or upgraded.
Native Hub changes; no APC code imported in this checkpoint. The wider technical plan, public connector parity, full Guardian deployment/rollback acceptance and UI QA remain incomplete. Future completed validated changes are to be committed/pushed by the agent under AGENTS.md publication rules.


2026-11-07 public MCP Git acceptance: task 6d06fb7c5f94424e9cd7194a78f39178 executed run_shell through the public connector and returned equal local/remote main hashes b618f0699ec6fc1bc01e7f300bb8f6ae083e7e1b, exit 0, clean status. This verifies actual public-MCP Git read access. Initial attempt in an older conversation was rejected before execution with HTTP409 because an unrelated prior action remained uncertain; that history was preserved. The read-only Git test used a separate persistent Git conversation. This does not establish discovery of all new development/memory tools or autonomous repair/deployment parity.
