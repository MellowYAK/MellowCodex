# General browser-agent effectiveness: research and implementation
Date: 2026-11-12. Baseline installed MellowCodex0.25.0. This document distinguishes observations, proposals and acceptance; it is not a claim of human-level autonomy.

## Primary-source findings
- Playwright MCP structures page evidence as accessibility roles/names/refs. Vision is a complementary path for controls absent from that tree. Playwright auto-waits for unique, visible, stable, enabled, unobscured targets. Reuse our existing Playwright/Qt adapter, not a second profile or browser.
  https://github.com/microsoft/playwright-mcp
  https://playwright.dev/docs/actionability
- Stagehand separates observe/act/extract and deterministic actions from AI interpretation; the host application owns task planning, validation and storage. Current Stagehand architecture is not a drop-in Qt WebEngine adapter. Vendor token/speed comparisons are not MellowCodex results.
  https://www.stagehand.dev/blog/what-is-stagehand
  https://github.com/browserbase/stagehand
- Browser Use supports local Ollama and warns that small models can reach a page without finishing. Its long-task design retains original goals, recent steps and an evidence archive. Current1.0 differs from0.x: several old parameters no longer act. Do not copy old tutorials or default cloud settings into this local product.
  https://docs.browser-use.com/open-source/models
  https://docs.browser-use.com/open-source/long-tasks
  https://docs.browser-use.com/open-source/all-parameters
- BrowserGym/AgentLab support reproducible web-agent evaluations and trace analysis; they are research infrastructure, not a consumer-browser replacement. Use their evaluation principles with a small bounded local acceptance set.
  https://github.com/ServiceNow/BrowserGym
  https://github.com/ServiceNow/AgentLab
- OmniParser converts screenshots into structured UI elements. It can help visual grounding, but is not the task planner. Assess latency, model-weight licensing and memory before adding it; existing DOM and OCR remain first paths.
  https://github.com/microsoft/OmniParser

## Model candidates, not selected replacements
- Current Qwen3.5-4B already supports vision/tool use; model failure cannot be inferred solely from wrong tool routing.
  https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3-VL-4B-Instruct Q4_K_M is available in Ollama (~3.3GB download, not runtime VRAM). Compare, do not presume it beats Qwen3.5-4B.
  https://ollama.com/library/qwen3-vl:4b-instruct
- UI-TARS-1.5-7B is a GUI-specialized model. Its output needs action-format parsing and an adapter into the existing freshness/permission/verification gates. Eight-GB quantized runtime fit, Windows/Ollama compatibility, multilingual behavior and speed are unverified locally. Never execute generated pyautogui/code directly.
  https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B
  https://github.com/bytedance/UI-TARS-desktop
- DeskForge-Qwen3.5-4B specializes in target grounding. Authors use a separate27B planner for long-horizon evaluation, so results do not establish standalone4B planning.
  https://huggingface.co/docling-project/DeskForge-Qwen3.5-4B

## Established local failure and first candidate
Wrong native app_open for a web application throws before dispatch, but ValueError was treated as an uncertain side effect. Fix those exact validation branches with ObservationError; never globally label exceptions safe.
Clarify native-vs-web routing. Preserve desktop_open/status through browser progressive disclosure.
Add <=2400-character browser decision evidence derived from existing durable actions, latest page, modal controls, recent attempts and uncertain effects. Never promote planned results into verified facts. Add optional intent/expected_outcome to the same action call; no extra LLM call and no second memory database. Original user requirements stay in the existing protected packet. Code is candidate-only until separately deployed.

## Next acceptance and rollout
1. Replay wrong-tool error, state transition, Hebrew/English/Russian controls, stale refs, unknown effects and restart reconstruction.
2. Agent-owned synthetic multi-page tasks with changing labels/layouts: navigation, explicit dummy sign-in, modal interruption, folder selection, downloadable artifact verification, sign-out. Do not use real private inboxes or claim synthetic credentials prove OAuth reliability.
3. Compare current baseline/candidate using same model/settings. Separate no-feedback, genuinely received external-feedback and unavailable-feedback cases. Record total model input, calls, wall time, wrong tools, repeated reads, quality and artifact/logout evidence.
4. Only then compare compatible GUI models one at a time under the same tasks and safe adapter. Measure VRAM/RAM/model reloads; model size is not runtime memory. No model installation/selection has occurred.
5. A GUI specialist is optional: DOM when reliable, visual grounding when needed, existing OCR fallback. Feedback carries current observation/goal/last failure and a bounded response deadline; no fictional feedback or automatic remote consent.
6. Publish/deploy only reviewed tested changes through the existing Guard workflow, preserve browser profile and work, then repeat focused live acceptance. Hardware/session/user-only challenges remain explicit limitations.
