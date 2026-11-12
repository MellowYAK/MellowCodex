# Desktop and internal browser on demand

Ask: Open MellowCodex / open the internal browser. MCP desktop_open(request_id, show=true) calls the existing authenticated Hub. desktop_status checks process ownership, native IPC and CDP; no model or visual-control session is required to start the UI. The local agent has the same tools in browser/code/desktop mode. The browser button in the web/native interface uses the same backend.

A successful result has ready=true and state=operational. A port alone or a spawned PID is not proof. Reuse request_id after an uncertain response and inspect desktop_status. Existing unresponsive or foreign processes are not killed or duplicated. Starts use the installed interpreter/source and the existing Qt singleton and profile. Work, chats, cookies and permissions remain untouched. A startup grace period prevents rapid retries. Automatic browser reads never gain launch privileges: desktop_open is a separate reversible action under the existing owner policy.

Services must be reachable. A service in Windows session zero cannot create an interactive user desktop; sign in and open the application. This does not unlock Windows or answer UAC. A power transition blocks launching. show=true verifies window visibility, not foreground focus or an unlocked screen.

Rollback: use the recorded prepared-update previous-file backups or a reviewed reverse candidate from published0.24.1 commit1e1dac8ce5fe5f5ae141d070bc060332f0613a29 through the existing ControlPlaneJobs/Guard workflow. Preserve state and browser profile; no database downgrade. A running Qt process loads new IPC code only after its next ordinary restart. Do not terminate active browser work for a documentation-only rollback.
