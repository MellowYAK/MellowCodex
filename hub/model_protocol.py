"""Normalize exact legacy tool envelopes; never extract calls from prose/code."""
import json
from jsonschema import validate, ValidationError

def normalize_message(message,catalog):
    if message.get('tool_calls'):return message,False
    content=message.get('content')
    if not isinstance(content,str) or len(content)>100000:return message,False
    try:data=json.loads(content)
    except (ValueError,TypeError):return message,False
    if not isinstance(data,dict) or set(data)!={'name','arguments'} or not isinstance(data['arguments'],dict):return message,False
    selected=next((t['function'] for t in catalog if t['function']['name']==data['name']),None)
    if selected is None:return message,False
    try:validate(data['arguments'],selected['parameters'])
    except ValidationError:return message,False
    return {**message,'content':'','tool_calls':[{'function':data}]},True
