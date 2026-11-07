"""Evidence gate for explicit tab-close requests, independent of model/provider."""
import re

def requests_tab_close(goal):
    # Proposed steps are not user authorization. Negated instructions must
    # never cause the completion gate to demand an otherwise forbidden write.
    objective=goal.split('Proposed next step from the linked ChatGPT assistant:',1)[0]
    for clause in re.split(r'[.;!?\n]+',objective):
        close=re.search(r'(?i)(?:\bclose\b|סגור|תסגור|סגרו)',clause)
        if not close or not re.search(r'(?i)(?:\btabs?\b|לשוני|טאבים|טאב)',clause):continue
        prefix=clause[:close.start()]
        if re.search(r"(?i)\b(?:no|not|never|without|avoid|don['’]t|cannot|can't|אין|לא|אל|בלי|אסור)\b",prefix):continue
        return True
    return False

def verified_tab_close(actions):
    return any(a['tool']=='browser_close_tabs' and (a.get('result') or {}).get('closed_verified') is True for a in actions)
