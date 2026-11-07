from PIL import Image
import pytest
from hub.visual_progress import VisualProgress
from hub.errors import ObservationError

def test_repeated_unchanged_input_blocks_despite_new_observation_ids(tmp_path):
    path=tmp_path/'screen.png';Image.new('RGB',(100,100),'white').save(path)
    shot={'path':str(path)};guard=VisualProgress()
    for i in range(2):
        args={'action':'click','x':10,'y':20,'observation_id':str(i)}
        guard.before('task',args,shot);guard.after('task',args,shot,shot)
    with pytest.raises(ObservationError,match='No input sent'):
        guard.before('task',{**args,'observation_id':'fresh'},shot)
    guard.before('another-task',args,shot)
    guard.before('task',{**args,'x':30},shot)
    Image.new('RGB',(100,100),'black').save(path)
    guard.before('task',args,shot)

def test_changed_image_resets_attempts(tmp_path):
    a=tmp_path/'a.png';b=tmp_path/'b.png'
    Image.new('RGB',(100,100),'white').save(a);Image.new('RGB',(100,100),'black').save(b)
    guard=VisualProgress();args={'action':'click','x':1,'y':1}
    result=guard.after('t',args,{'path':str(a)},{'path':str(b)})
    assert result['unchanged_attempts']==0 and not result['image_unchanged']
