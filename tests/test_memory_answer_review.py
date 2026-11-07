import asyncio
import json
import pytest
from hub.memory_answer_review import sources_for_review,review_answer


def test_sources_are_user_evidence_not_prior_assistant_claims():
    sources=sources_for_review([{'tool':'conversation_history','result':{'turns':[
        {'id':'old','position':2,'goal':'Use Cedar','result':'Incorrect claim'},
        {'id':'new','position':9,'goal':'Use Pine instead','result':'Another unsupported claim'}]}}],{'items':[]})
    assert sources==[{'task_id':'old','position':2,'user_quote':'Use Cedar'},
                     {'task_id':'new','position':9,'user_quote':'Use Pine instead'}]


@pytest.mark.parametrize('reverse',[False,True])
def test_explicit_report_read_is_retained_as_report_not_user_authority(reverse):
    actions=[
        {'tool':'conversation_history','result':{'task_id':'source','field':'goal','text':'Count tabs'}},
        {'tool':'conversation_history','result':{'task_id':'source','field':'result','text':'7'}}
    ]
    sources=sources_for_review(actions[::-1] if reverse else actions,{'items':[]})
    assert sources[0]['user_quote']=='Count tabs'
    assert sources[0]['assistant_report']=='7'
    assert 'not independent verification' in sources[0]['report_role']
    async def model(messages,catalog):
        return {'content':json.dumps({'verdict':'supported','reason':'Historical report only',
            'citations':[{'task_id':'source','quote':'7'}]})},{}
    result=asyncio.run(review_answer(model,'What did it report?','It reported 7',sources))
    assert result['verdict']=='supported'


def test_saved_feedback_history_is_not_lost_during_answer_review():
    review={'id':'feedback','status':'reviewed','request':{'source_task_id':'old','claim':'Reported 7'},
        'response':{'verdict':'confirmed','evidence':'Original chat contains 7'}}
    sources=sources_for_review([{'tool':'conversation_memory_reviews','result':{'items':[review]}}],{'items':[]})
    assert sources[0]['task_id']=='review:feedback'
    assert json.loads(sources[0]['remote_feedback'])['response']==review['response']
    assert 'not user authority' in sources[0]['feedback_role']


@pytest.mark.parametrize('quote,verdict',[('Use Pine instead','contradicted'),('Invented source','unavailable')])
def test_review_requires_exact_source_citations(quote,verdict):
    async def model(messages,catalog):
        assert catalog==[]
        return {'content':json.dumps({'verdict':'contradicted','reason':'Draft reverses chronology',
            'citations':[{'task_id':'new','quote':quote}]})},{'model':'fixture'}
    result=asyncio.run(review_answer(model,'Current choice?','Cedar',[{'task_id':'new','user_quote':'Use Pine instead'}]))
    assert result['verdict']==verdict


def test_malformed_review_cannot_confirm_answer():
    async def model(messages,catalog):return {'content':'Everything is correct'},{}
    result=asyncio.run(review_answer(model,'question','draft',[{'task_id':'one','user_quote':'Original'}]))
    assert result['verdict']=='unavailable'
    assert not sources_for_review([],{'items':[{'source_changed':True,'source_task_id':'old','quote':'Stale'}]})


def test_pure_history_reviews_the_source_derived_answer_not_wrong_draft():
    calls=[]
    async def model(messages,catalog):
        packet=json.loads(messages[1]['content']);calls.append(packet)
        if len(calls)==1:
            assert 'draft' not in packet
            return {'content':'Current: Pine; former: Cedar'},{}
        assert packet['draft']=='Current: Pine; former: Cedar'
        return {'content':json.dumps({'verdict':'supported','reason':'Later source chooses Pine',
            'citations':[{'task_id':'new','quote':'Use Pine instead'}]})},{}
    result=asyncio.run(review_answer(model,'Current?','Current: Cedar',[
        {'task_id':'new','position':9,'user_quote':'Use Pine instead'}],source_only=True))
    assert result['reviewed_answer']=='Current: Pine; former: Cedar'
