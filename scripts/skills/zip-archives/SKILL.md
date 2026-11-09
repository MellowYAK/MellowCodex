---
name: zip-archives
description: Create ZIP archives and extract into a new directory with traversal protection.
---

JSON operation create|extract with source,destination absolute paths. Extraction creates a new directory; refuses path traversal, symlinks and archives above2GiB uncompressed.

Invoke the registered extension zip_archives using JSON stdin; tool.py prints JSON. Dependencies: {"python": "stdlib zipfile; PSF"}.
