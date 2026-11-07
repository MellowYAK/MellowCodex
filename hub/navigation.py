"""Ground navigation in the request and recorded browser observations."""
import re
from urllib.parse import urlsplit, urlunsplit
from .errors import ObservationError

def normalized_url(url):
    parts=urlsplit(url)
    return urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path or '/',parts.query,''))

def observed_urls(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('href','url') and isinstance(item,str) and item.startswith(('https://','http://')):
                yield normalized_url(item)
            elif isinstance(item,(dict,list)):
                yield from observed_urls(item)
    elif isinstance(value,list):
        for item in value:yield from observed_urls(item)

def require_observed_navigation(goal,url,actions):
    requested={normalized_url(u.rstrip('.,;:)')) for u in re.findall(r'https?://[^\s<>"\x27]+',goal)}
    evidence=[]
    for action in actions:
        result=action.get('result')
        if action['tool'] in ('browser_navigate','browser_observe','browser_act','browser_extract','browser_tabs') and isinstance(result,dict) and not result.get('error'):
            evidence.append(result)
    allowed=requested|set(observed_urls(evidence))
    # A named website without a URL may establish the first navigation.
    # Subsequent destinations must be observed, not invented article/login paths.
    if (requested or evidence) and normalized_url(url) not in allowed:
        raise ObservationError('This URL was neither supplied in the task nor observed in browser evidence. Return to a requested URL or inspect actual links with browser_observe/browser_extract; do not substitute another site or guess article/login paths.')
