from hub.ui_tars import is_generated_evidence
def test_old_image_evidence_without_images_is_deduplicated():
 oid='a'*32
 m={'role':'user','content':'Evidence from the browser_act call that just completed, NOT a new request.\nCurrent screenshot. Observation ID: '+oid}
 assert is_generated_evidence(m,{oid})
 assert not is_generated_evidence(m,{'b'*32})
def test_user_correction_is_preserved():
 assert not is_generated_evidence({'content':'Do not save; use the other account.'},set())
