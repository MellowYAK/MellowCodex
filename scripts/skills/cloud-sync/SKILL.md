---
name: cloud-sync
description: List configured rclone remotes; copy and synchronize local or cloud paths, with preview by default.
---

JSON operation remotes|list|copy|sync. list takes source. copy/sync take source,destination and optional dry_run default true. Local paths must be absolute; cloud path is configuredRemote:path. Install does not authorize transferring private files or deletion. For actual sync (deletes destination extras), require explicit user authorization for that exact source/destination, inspect dry run first; set allow_delete:true and dry_run:false only then. No credentials printed or stored here. First cloud use needs a configured account. Runtime executable E:/AI/tools/rclone/1.76.0/rclone.exe.

Invoke the registered extension cloud_sync using JSON stdin; tool.py prints JSON. Dependencies: {"rclone": "1.76.0 MIT; https://rclone.org/downloads/"}.
