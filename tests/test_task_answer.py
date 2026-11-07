import pytest
from hub.task_answer import task_answer


def task(text, state='waiting_review'):
    return {'state':state, 'result':'System status prefix\n'+text,
            'messages':[{'role':'assistant','content':text}]}


def test_answer_keeps_raw_text_and_separates_system_status():
    text='```json\n{"value": 42}\n```'
    answer=task_answer(task(text))
    assert answer['text']==text
    assert answer['structured']=={'value':42}
    assert answer['format']=='fenced_json'
    assert answer['semantic_verification']=='not_established_by_parsing'


@pytest.mark.parametrize('text', ['Explanation {"x":1}', '{"x":1}\n{"x":2}',
                                '{"x":1,"x":2}', '{"x":NaN}', '```json\n{}\n``` extra'])
def test_does_not_salvage_ambiguous_or_invalid_json(text):
    assert not task_answer(task(text))['json_syntax_valid']


@pytest.mark.parametrize('state', ['queued','running','failed','paused','cancelled'])
def test_no_old_answer_during_correction_or_failure(state):
    assert task_answer(task('{}',state)) is None


def test_no_previous_answer_after_later_message_or_tool_call():
    value=task('{}')
    value['messages'].append({'role':'user','content':'Correct that'})
    assert task_answer(value) is None
    value['messages'][-1]={'role':'assistant','content':'Working','tool_calls':[{}]}
    assert task_answer(value) is None
