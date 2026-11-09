---
name: windows-apps
description: Launch applications and inspect, click or fill Windows controls by observed handles.
---

JSON operation launch with absolute executable and args array, inspect with handle, fill with handle,text, click with handle. Inspect fresh handles first. Perform actions only for user requested workflow. Never accept shell command strings. launch returns PID; doesn't assert window is ready. Do not close unrelated apps.

Invoke the registered extension windows_apps using JSON stdin; tool.py prints JSON. Dependencies: {"pywinauto": "0.6.9 BSD-3-Clause; https://pywinauto.readthedocs.io/"}.
