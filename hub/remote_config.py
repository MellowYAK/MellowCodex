"""Optional remote gateway configuration; credentials stay outside the repository."""
import json
from .config import STATE

HOME=STATE/'mcp'
CONFIG=STATE/'relay.json'

def load():
    try:return json.loads(CONFIG.read_text(encoding='utf-8'))
    except FileNotFoundError:return {'enabled':False}

PUBLIC=load().get('public_url','https://agent.178-128-45-70.sslip.io').rstrip('/')
GATEWAY_PORT=8897
RELAY_PORT=18897
