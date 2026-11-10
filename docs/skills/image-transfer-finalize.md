# Image transfer finalization (MellowCodex local skill)

Use **existing MCP tools** `image_upload_begin`, `image_upload_chunk`, and `image_upload_finish` to send actual ChatGPT-provided image bytes into the MellowCodex file library. **Do not** create an alternative upload channel. Only call `image_upload_begin` with the real byte length, original SHA-256, and image filename; transfer actual base64 chunks with exact offsets, then finish. The result must be `status: ready` with a genuine returned local `file_id`.

For an image **already received and ready** in the local FileLibrary, use the existing **Extensions** tool registry (not a second MCP uploader). In the MellowCodex code/desktop task, invoke `extension_run` with `name: image_transfer_finalize`, and `arguments` containing exactly:

```json
{
  "source_file_id": "<actual-ready-local-file-id>",
  "destination": "E:\\AI\\artifacts\\<chosen-folder>\\<new-name>.png",
  "expected_size": 12345,
  "expected_sha256": "<original-64-lowercase-hex-hash>"
}
```

Only use values from observed tools and original bytes. File IDs identify library records; never confuse them with ChatGPT attachment IDs or short-lived download URLs. This registered extension uses the absolute interpreter of the existing Hub registry (`sys.executable`), not `python` from Windows PATH. Its project-owned canonical source is `scripts/image_transfer_finalize.py` and its independent focused functional test is `scripts/test_image_transfer_finalize.py`. Registration creates a hash-pinned manifest under the existing `E:\\AI\\extensions\\image_transfer_finalize` registry.

Required success evidence: `extension_run` exit code zero and JSON `verified: true` with destination, source file ID, size, SHA-256 and decoded image format/dimensions. It creates a new file exclusively and refuses overwrites. A nonzero exit, missing file, hash mismatch, or decode failure means **not successful**. This operation copies an existing registered image only; it **does not** set wallpaper, guarantee a foreground image-viewer window, or prove a new MCP transfer occurred.
