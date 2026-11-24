# MCP reliability and VMware guest control

## Reliability
Conversation binding no longer loads full task history on each MCP message. Blocking conversation and connector-evidence storage operations are offloaded from the ASGI event loop. Concurrent health requests share a completed overlapping scan; observed timestamps remain unchanged. Downstream transport errors are returned as structured tool errors. An uncertain write is never automatically replayed. Native pointer movement must succeed and reach the observed target before a click.

## VMware (opt-in, Workstation Pro)
The gateway exposes vmware_status, vmware_screenshot and vmware_input. The module does not start, stop, configure or elevate the guest and does not use the host mouse or keyboard. The owner must configure the exact QA VM locally, with authenticated VNC bound only to 127.0.0.1. Wildcard or unverified listener ownership is rejected. Keep the VMware VNC credential distinct from Windows credentials and the VM encryption password.

In the configured LOCAL_AGENT_ROOT/state directory, create vmware-control.json with exactly these fields: enabled (boolean), vmrun (absolute path to vmrun.exe), vmx (absolute path to the selected .vmx), port (integer 5900-6001), keyboard_layout (en-US). Configure the dedicated generic credential MellowCodex/VMware/QA in Windows Credential Manager under the account running the gateway. Do not put passwords in JSON, source, command history or chat logs.

The owner must verify the guest uses an English US keyboard layout and arrange guest login and any secure prompts locally. Use vmware_screenshot, retrieve its file_id with get_file, inspect the image, then use its frame_id once with vmware_input. Frames expire after 45 seconds and are checked against current guest identity and pixels. Input is serialized. Inspect the returned after-frame; event delivery is not proof of effect. Do not replay an uncertain input. Only printable ASCII text is supported.

The lab previously demonstrated actual VMware VNC screenshot, mouse and corrected keyboard input. The integrated module still requires a new live test against a correctly configured loopback-only guest; unit tests alone do not establish that acceptance. The vendored RFB/DES implementation retains its MIT license in hub/vmware_rfb/LICENSE.txt.

No changes to Guard, OwnerBroker, firewall or OS security policy are included.