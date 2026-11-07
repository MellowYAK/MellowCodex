"""Expose the executor's last answer separately from runtime status prose."""
import json
import re


def task_answer(task):
    # Never resurface a previous answer while a correction is queued/running,
    # or after a later user/tool message. Status is not semantic approval.
    if task.get('state') not in ('done', 'waiting_review'):
        return None
    messages = task.get('messages') or []
    if not messages:
        return None
    message = messages[-1]
    text = message.get('content')
    if message.get('role') != 'assistant' or message.get('tool_calls') or not isinstance(text, str):
        return None
    candidate = text.strip()
    fence = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    def reject_constant(value):
        raise ValueError('Non-JSON constant')
    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key] = item
        return value
    result = {'text': text, 'structured': None, 'json_syntax_valid': False,
              'format': 'text', 'semantic_verification': 'not_established_by_parsing'}
    try:
        value = json.loads(candidate, parse_constant=reject_constant, object_pairs_hook=unique_pairs)
    except (ValueError, TypeError):
        return result
    result.update(structured=value, json_syntax_valid=True, format='fenced_json' if fence else 'json')
    return result
