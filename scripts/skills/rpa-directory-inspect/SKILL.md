---
name: inspect-directory-rpa
description: List files and byte sizes in a local directory using RPA Framework. Use for read-only file inventory before organizing or copying files.
---
Call rpa_directory_inspect with {"path":"E:/AI","limit":50}. Path must be an existing absolute directory. Limit is 1..200. Listing is non-recursive and read-only. Handle errors and truncation explicitly.
Source: https://pypi.org/project/rpaframework/ and https://github.com/robocorp/rpaframework
Version 34.0.1; Apache-2.0. Full RPA Framework installed in this extension's isolated environment. Adapter is original. Other library operations require their own task-specific integration.
