import json
import pytest
from hub.context.component_analysis import validate_components


def test_exact_quotes_are_required_without_claiming_semantic_approval():
    sources=[{'path':'report.py','start':10,'excerpt':'def render(text):\n    return pdf(text)','ref':'source-version'}]
    base={'path':'report.py','role':'output','description':'Produces a document','line':11,'quote':'    return pdf(text)'}
    items=[base,{**base,'line':10},{**base,'quote':'return pdf(text)'},{**base,'path':'other.py'}]
    result=validate_components({'role':'assistant','content':json.dumps({'components':items})},sources)
    assert len(result['accepted'])==1 and len(result['rejected'])==3
    assert result['accepted'][0]['quote_verified']
    assert not result['accepted'][0]['interpretation_verified']


def test_host_retrieved_quote_is_bounded_by_source_not_model_transcription_limit():
    source={'path':'large.py','start':1,'excerpt':'x=1\n'+'y=2; '*1000}
    item={'path':'large.py','role':'input','description':'Unverified','line':1,'end_line':2}
    result=validate_components({'role':'assistant','content':json.dumps({'components':[item]})},[source])
    assert len(result['accepted'])==1
    assert result['accepted'][0]['quote']==source['excerpt']
    assert not result['semantic_verified']


def test_bad_json_and_incomplete_quotes_cannot_become_evidence():
    assert validate_components({'role':'assistant','content':'trust me'},[])['accepted']==[]
    source={'path':'a.py','start':1,'excerpt':'first\nlast'}
    item={'path':'a.py','role':'input','description':'Reads','line':2,'quote':'last\nunseen'}
    assert not validate_components({'role':'assistant','content':json.dumps({'components':[item]})},[source])['accepted']


def test_batches_preserve_every_source_line_under_real_budget(monkeypatch):
    from hub.model_settings import ModelSettings
    from hub.context.component_analysis import extraction_batches
    monkeypatch.setattr('hub.model_settings.load_settings',lambda:ModelSettings(context_tokens=8192,response_tokens=2400))
    sources=[{'path':f'component-{n}.py','ref':str(n),'start':20,'end':119,
              'excerpt':'\n'.join(f'    value_{i} = transform(input_{i}, option="long value for coverage")' for i in range(100))} for n in range(5)]
    batches=extraction_batches('Trace producers and consumers',sources)
    assert len(batches)>1
    observed=[]
    for messages in batches:
        packet=json.loads(messages[-1]['content'])
        assert not packet.get('omitted_source_ranges')
        for source in packet['sources']:
            for line,text in enumerate(source['excerpt'].split('\n'),source['start']):
                observed.append((source['path'],line,text.partition(': ')[2] if source.get('line_numbered') else text))
    expected=[(s['path'],i,t) for s in sources for i,t in enumerate(s['excerpt'].split('\n'),s['start'])]
    assert observed==expected


def test_oversized_single_line_reports_failure_instead_of_omitting(monkeypatch):
    from hub.model_settings import ModelSettings
    from hub.context.component_analysis import extraction_batches
    monkeypatch.setattr('hub.model_settings.load_settings',lambda:ModelSettings(context_tokens=8192,response_tokens=2400))
    with pytest.raises(ValueError,match='exceeds extraction context'):
        extraction_batches('Read',[{'path':'huge.py','start':1,'excerpt':'x '*50000}])


def test_line_anchors_retrieve_original_text_but_never_approve_description():
    source={'path':'a.py','start':10,'excerpt':'def f():\n    return input_image','ref':'hash'}
    base={'path':'a.py','role':'output','description':'Unverified interpretation','line':11,'end_line':11}
    items=[base,{**base,'end_line':12},{**base,'line':9},{**base,'end_line':10},{**base,'path':'missing.py'}]
    result=validate_components({'role':'assistant','content':json.dumps({'components':items})},[source])
    assert len(result['accepted'])==1 and len(result['rejected'])==4
    assert result['accepted'][0]['quote']=='    return input_image'
    assert not result['accepted'][0]['interpretation_verified']
