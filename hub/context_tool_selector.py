"""One-shot catalog reduction after a measured mandatory context overflow.

Mandatory messages and user requirements are never discarded. Only the tool
schema set for the next model dispatch is narrowed, and this is explicitly
recorded in the diagnostic. No retry after external side effects.
"""
TOOL_PRIORITY={
    "code":("project_context","context_search","context_expand","context_related",
            "read_file","write_file","run_shell","terminal_run","terminal_read",
            "tools_enable","extensions_list","extension_run"),
    "browser":("agent_environment","browser_navigate","browser_observe","browser_act","browser_assess",
               "browser_tabs","browser_frame","browser_pointer","browser_extract","find_login",
               "browser_close_tabs","browser_save_pdf","tools_enable","extensions_list","extension_run","chatgpt_ask"),
    "desktop":("app_find","app_open","window_inspect","window_act","observe_screen",
               "capture_screenshot","run_shell","chatgpt_ask","extensions_list","extension_run")
}

def compact_tool_catalog(catalog,mode):
    names=TOOL_PRIORITY.get(mode,TOOL_PRIORITY["code"])
    by_name={x.get("function",{}).get("name"):x for x in catalog}
    selected=[by_name[n] for n in names if n in by_name]
    if not selected or len(selected)>=len(catalog):
        return catalog,{"reduced":False,"before":len(catalog),"after":len(catalog)}
    return selected,{"reduced":True,"before":len(catalog),"after":len(selected),
                     "excluded_names":[x.get("function",{}).get("name") for x in catalog
                                       if x.get("function",{}).get("name") not in names],
                     "note":"Only next-call tool schemas narrowed; durable task messages unchanged"}
