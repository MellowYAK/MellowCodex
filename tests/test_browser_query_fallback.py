from hub.browser_evidence import filter_controls,compact_browser,resolve_ref
def test_no_match_returns_actual_controls_with_current_refs():
    state={'id':'new','text':'Page','elements':[{'ref':'e9','name':'Социальные сети','tag':'button'}]}
    filtered=filter_controls(state,'Social/Connections')
    assert filtered['query_matched'] is False
    assert filtered['elements'][0]['name']=='Социальные сети'
    compact=compact_browser(filtered,2000)
    assert compact['query_matched'] is False and compact['elements'][0]['ref']=='e9'
    assert 'unfiltered' in compact['query_note']
def test_match_remains_filtered_and_no_translation_is_invented():
    state={'elements':[{'ref':'e1','name':'Save'},{'ref':'e2','name':'Cancel'}]}
    assert filter_controls(state,'save')['elements']==[{'ref':'e1','name':'Save'}]
