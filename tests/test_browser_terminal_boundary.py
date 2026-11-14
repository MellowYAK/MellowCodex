from hub.browser_workflow import terminal_receipt,terminal_message

def actions(text='Demo Channel connected successfully.'):
 before={'id':'before','text':'Choose Demo Channel','elements':[],'coherent':True,'captured_at':10}
 after={'id':'after','text':text,'elements':[],'coherent':True,'captured_at':20}
 return [{'tool':'browser_observe','result':before},{'tool':'browser_act','args':{'action':'click'},'result':{'input_sent':True,'target':{'name':'Demo Channel'},'after':after}}]
def test_fresh_receipt_routes_to_assessment_not_back():
 m=terminal_message(actions(),'Connect Demo Channel',21)
 assert m['tool_calls'][0]['function']['name']=='browser_assess'
 assert m['tool_calls'][0]['function']['arguments']['entity']=='Demo Channel'
def test_generic_receipt_does_not_invent_entity():
 m=terminal_message(actions('Канал подключён. Вернитесь в приложение.'),'Connect Demo Channel',21)
 assert m['tool_calls'][0]['function']['arguments']['entity']==''
def test_intermediate_negative_stale_and_existing_status_are_not_terminal():
 a=actions();a[-1]['result']['after']['elements']=[{'tag':'button','name':'Next','width':80,'height':30}]
 assert terminal_receipt(a,21) is None
 assert terminal_receipt(actions('Channel not connected.'),21) is None
 assert terminal_receipt(actions(),200) is None
 a=actions();a[0]['result']['text']=a[-1]['result']['after']['text'];assert terminal_receipt(a,21) is None
def test_unverified_entity_reports_without_replaying_or_false_success():
 a=actions();a.append({'tool':'browser_assess','result':{'observation_id':'after','verified':False}})
 m=terminal_message(a,'Connect Demo Channel',21)
 assert not m.get('tool_calls') and 'unverified' in m['content']
