"""Parse a visual review as evidence, never as executable code."""
import json,re

def parse_review(reply):
    texts=[reply.get('text',''),*reply.get('code_blocks',[])]
    for text in texts:
        candidates=[text,*re.findall(r'```(?:json)?\s*([\s\S]*?)```',text)]
        for candidate in candidates:
            try:
                value=json.loads(candidate.strip().removeprefix('JSON\n'))
                review=value.get('visual_verification')
                if isinstance(review,dict) and type(review.get('passed')) is bool:
                    return {'passed':review['passed'],'reason':str(review.get('reason',''))[:2000],'next_step':str(review.get('next_step',''))[:2000]}
            except (ValueError,AttributeError):pass
    return {'passed':None,'reason':'ChatGPT did not provide a verifiable final-state assessment','next_step':''}
