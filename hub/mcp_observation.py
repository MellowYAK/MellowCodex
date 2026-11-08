"""Persist direct MCP context reads in their explicitly associated conversation."""
import json


def record_observation(conversations, transcript, chat_id, event):
    chat = conversations.get(chat_id)
    if chat['project_id'] != event['project_id']:
        raise ValueError('The chat belongs to another project; bind_chat_project first')
    phase = event['phase']
    if phase not in ('started', 'completed', 'failed'):
        raise ValueError('Invalid observation phase')
    operation = event['operation']
    if not operation or not event['request_id']:
        raise ValueError('Operation and request_id are required')
    transcript.configure(chat_id, transport='mcp')
    transcript.append(chat_id, 'chatgpt' if phase == 'started' else 'local_agent',
                      'chatgpt_to_agent' if phase == 'started' else 'agent_to_chatgpt',
                      json.dumps({'mcp_observation': {'operation': operation, 'phase': phase,
                                                    'payload': event['payload']}}, ensure_ascii=False),
                      key='mcp-read:'+event['request_id']+':'+phase, status=phase)
    return {'chat_id': chat_id, 'recorded': True, 'phase': phase}
