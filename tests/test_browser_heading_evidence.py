import json
from hub.browser_evidence import compact_browser

def test_separate_multilingual_headings_survive_dense_controls():
 headings=[{'text':'News','level':1},{'text':'\u05db\u05d5\u05ea\u05e8\u05ea','level':2},{'text':'\u041d\u043e\u0432\u043e\u0441\u0442\u0438','level':2}]
 page={'id':'x','url':'https://example.test','headings':headings,'text':'News body. '*80,'elements':[{'ref':f'e{i}','name':f'Control {i}','tag':'button','enabled':True} for i in range(40)]}
 packet=compact_browser(page,2500)
 assert [h['text'] for h in packet['headings']]==[h['text'] for h in headings]
 assert len(json.dumps(packet,ensure_ascii=False))<=2500
 assert packet['elements'] and packet['text']
 assert 'never concatenate' in packet['reading_hint']

def test_no_heading_is_not_invented_from_flat_text():
 packet=compact_browser({'id':'x','text':'Menu Headlines Footer','elements':[]},2500)
 assert packet['headings']==[]
