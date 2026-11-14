def test_older_visual_user_correction_text_remains_mandatory():
    from hub.model_context import build_packet
    correction='Corrected requirement: preserve original file and write a separate copy.'
    messages=[{'role':'system','content':'Use evidence'},{'role':'user','content':'Original request'},
              {'role':'user','content':correction,'images':['older-image']},
              {'role':'assistant','content':'optional text '*5000},
              {'role':'user','content':'Current screenshot','images':['current-image']}]
    packet,diagnostic=build_packet(messages,[],16384,512,target_tokens=6000)
    assert any(m.get('content')==correction for m in packet)
    assert [m['images'] for m in packet if m.get('images')]==[['current-image']]
