"""Detect successful read cycles without treating new evidence as a failure."""
import hashlib
import json

READ_TOOLS = frozenset(('read_file', 'project_context', 'context_search',
    'context_expand', 'context_related', 'conversation_history',
    'conversation_search', 'browser_tabs', 'list_files'))


def _is_read_only_action(action):
    if action['tool'] in READ_TOOLS:
        return True
    if action['tool'] != 'run_shell':
        return False
    # Do not classify arbitrary shell commands as reads. Only a narrow
    # PowerShell directory-listing pipeline qualifies for loop detection.
    args = action.get('args') or {}
    command = args.get('command', '')
    if args.get('shell') not in (None, 'powershell') or not isinstance(command, str):
        return False
    import re
    if len(command) > 800 or any(c in command for c in (';', '\n', '\r', '&&', '||', '$(', '`')):
        return False
    stages = [stage.strip() for stage in command.split('|')]
    return bool(stages and re.match(r'^Get-ChildItem(?:\s|$)', stages[0], re.I)
                and all(re.match(r'^(?:Select-Object|Sort-Object|Format-Table|Format-List)(?:\s|$)', stage, re.I)
                        for stage in stages[1:]))


def stalled_reads(actions, baseline=()):
    """Only a consecutive suffix of completed, known read-only actions counts.

    Different arguments or different returned evidence reset novelty. No shell
    commands or UI actions are assumed read-only. A resumed attempt starts fresh.
    """
    suffix=[]
    for action in reversed(actions):
        if action['id'] in baseline or not _is_read_only_action(action):
            break
        result=action.get('result')
        if action.get('state')!='complete' or not isinstance(result,dict) or result.get('error'):
            break
        suffix.append(action)
    suffix.reverse()
    if len(suffix)<6:
        return None
    seen=set();duplicates=0
    for action in suffix:
        # Shell execution produces a different artifact log filename on each
        # invocation. Logs are not new source evidence when stdout is identical.
        result = action['result']
        evidence = ({key: result.get(key) for key in ('exit_code', 'output', 'truncated')}
                    if action['tool'] == 'run_shell' else result)
        fingerprint=hashlib.sha256(json.dumps(
            [action['tool'], action['args'], evidence],
            sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        if fingerprint in seen:
            duplicates+=1
        else:
            seen.add(fingerprint);duplicates=0
    if duplicates<4:
        return None
    return {'reason':'Repeated successful reads returned no new evidence',
            'consecutive_redundant_reads':duplicates,
            'recent_actions':[{'action_id':a['id'],'tool':a['tool'],'args':a['args']}
                              for a in suffix[-8:]],
            'next_step':'Director: inspect existing evidence and supply one focused next action. '
                        'For an image transfer provide a registered file_id or a verified downloadable source. '
                        'Do not repeat the same history, map or file reads. No completion is claimed.'}
