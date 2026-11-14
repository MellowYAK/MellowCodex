from hub.ui_tars import compact_controls
def test_state_and_identity_preserved():
 e=dict(ref='e1',name='Continue',tag='button',type='',enabled=False,focused=True,modal=True,checked=False,options=None)
 assert compact_controls([e])==[dict(ref='e1',name='Continue',tag='button',enabled=False,focused=True,modal=True,checked=False)]
def test_defaults_compact_but_select_options_and_unicode_preserved():
 items=[dict(ref='e2',name='ערוץ',tag='select',enabled=True,focused=False,modal=False,checked=None,options=[dict(label='Комикс',value='c',selected=True)])]
 out=compact_controls(items)[0]
 assert out['ref']=='e2' and out['name']=='ערוץ' and out['options']==items[0]['options']
 assert not any(k in out for k in ('enabled','focused','modal','checked'))
