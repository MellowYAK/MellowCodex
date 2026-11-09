---
name: file-operations
description: Copy and move files or folders; create directories; never overwrite existing destinations.
---

JSON operation copy|move with absolute source,destination; mkdir with destination. Destination must not exist. Ask for intended source/destination when ambiguous. No delete operation.

Invoke the registered extension file_operations using JSON stdin; tool.py prints JSON. Dependencies: {"python": "stdlib shutil/pathlib, PSF"}.
