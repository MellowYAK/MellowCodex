"""One named disk-backed browser profile; never export authentication cookies."""
import json
from pathlib import Path
from urllib.parse import urlsplit


def persistent_profile(parent, state, cache):
    from PySide6.QtWebEngineCore import QWebEngineProfile
    storage=Path(state)/'browser-profile'
    storage.mkdir(parents=True,exist_ok=True)
    Path(cache).mkdir(parents=True,exist_ok=True)
    profile=QWebEngineProfile('LocalAgent',parent)
    profile.setPersistentStoragePath(str(storage))
    profile.setCachePath(str(cache))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
    profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
    return profile


def restorable_url(value):
    try:
        parts=urlsplit(value)
        if parts.scheme in ('http','https') and parts.hostname and not parts.username and not parts.password:
            # Do not replay an in-progress login callback, authorization code or download.
            if any(word in parts.path.lower() for word in ('callback','oauth','authorize','logout','signout')):
                return parts.scheme+'://'+parts.netloc+'/'
            return parts._replace(query='',fragment='').geturl()
    except (TypeError,ValueError):pass
    return 'about:blank'


def save_tabs(path, urls, selected):
    path=Path(path)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'urls':[restorable_url(u) for u in urls][:30], 'selected':selected}),encoding='utf-8')
    temporary.replace(path)


def load_tabs(path):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8'))
        urls=[restorable_url(u) for u in value['urls'][:30]]
        return urls,max(0,min(int(value.get('selected',0)),len(urls)-1))
    except (OSError,ValueError,TypeError,KeyError):return [],0
