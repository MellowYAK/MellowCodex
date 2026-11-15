"""Bounded, reversible fast-path for local browser-agent inference only.

Browser requests are usually short tool decisions, not 20K-token essays.
Task logs, model settings, and durable context remain unchanged.
"""
from .context_tool_selector import compact_tool_catalog

def adapt_browser_policy(settings,catalog):
    focused,selection=compact_tool_catalog(catalog,"browser")
    limits={"response_tokens":min(settings.response_tokens,1024),
            "working_input_tokens":min(settings.working_input_tokens,5200)}
    updated=settings.model_copy(update=limits)
    return updated,focused,{
        "mode":"browser_default_fast",
        "context_tokens_unchanged":settings.context_tokens,
        "output_prediction_budget":updated.response_tokens,
        "working_input_target":updated.working_input_tokens,
        "tool_catalog_before":len(catalog),"tool_catalog_after":len(focused),
        "tool_selection":selection,
        "durable_messages_changed":False,
    }
