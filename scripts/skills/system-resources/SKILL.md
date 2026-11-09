---
name: system-resources
description: Read CPU, RAM and process summaries without terminating processes.
---

JSON optional limit1..200. Returns current CPU percent, RAM bytes and top processes by RAM. Read-only.

Invoke the registered extension system_resources using JSON stdin; tool.py prints JSON. Dependencies: {"psutil": "7.2.2 BSD-3-Clause; https://github.com/giampaolo/psutil"}.
