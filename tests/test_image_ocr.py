from pathlib import Path
import pytest
from hub.image_ocr import read_image
from hub.tools import ToolRunner,CATALOG

def test_missing_engine_has_actionable_error(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCAL_AGENT_OCR_PYTHON',str(tmp_path/'missing.exe'))
    with pytest.raises(RuntimeError,match='not installed'):read_image(tmp_path/'x.png',tmp_path)
    assert not list(tmp_path.iterdir())

def test_tool_is_read_only_catalog_and_confines_paths(tmp_path):
    runner=ToolRunner.__new__(ToolRunner)
    assert any(t['function']['name']=='image_ocr' for t in CATALOG)
    with pytest.raises(ValueError,match='leaves'):runner.path({'workspace':str(tmp_path)},'../private.png')


def test_existing_image_ocr_does_not_query_desktop(tmp_path, monkeypatch):
    import asyncio
    import hub.tools as tools
    import hub.image_ocr as ocr
    class LockedDesktop:
        stopped = False
        def __getattr__(self, name):
            raise AssertionError('OCR must not query desktop: ' + name)
    runner = ToolRunner.__new__(ToolRunner)
    runner.desktop = LockedDesktop(); runner.application_targets = {}
    monkeypatch.setattr(tools, 'ARTIFACTS', tmp_path / 'artifacts')
    source = tmp_path / 'image.jpg'
    source.write_bytes(b'fixture')
    monkeypatch.setattr(ocr, 'read_image', lambda path, folder: {'text': 'file OCR', 'path': str(path)})
    result = asyncio.run(runner.execute({'id': 'locked-test', 'mode': 'inspect', 'workspace': str(tmp_path)}, 'image_ocr', {'path': 'image.jpg'}))
    assert result['text'] == 'file OCR'
    assert result['path'] == str(source)

def test_read_file_allows_own_evidence_but_not_other_tasks(tmp_path,monkeypatch):
    import asyncio
    import hub.tools as tools
    from types import SimpleNamespace
    runner=ToolRunner.__new__(ToolRunner)
    runner.desktop=SimpleNamespace(stopped=False);runner.application_targets={}
    root=tmp_path/'evidence';workspace=tmp_path/'workspace';workspace.mkdir()
    monkeypatch.setattr(tools,'ARTIFACTS',root)
    own=root/'mine'/'ocr.txt';own.parent.mkdir(parents=True);own.write_text('readable',encoding='utf-8')
    other=root/'other'/'ocr.txt';other.parent.mkdir();other.write_text('private',encoding='utf-8')
    task={'id':'mine','workspace':str(workspace),'mode':'inspect'}
    assert asyncio.run(runner.execute(task,'read_file',{'path':str(own)}))['content']=='readable'
    with pytest.raises(ValueError,match='leaves'):
        asyncio.run(runner.execute(task,'read_file',{'path':str(other)}))

def test_crop_preserves_source_and_passes_quality(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    from PIL import Image
    import hub.image_ocr as ocr
    python=tmp_path/'python.exe';python.touch()
    models=tmp_path/'models';(models/'server-svtrv2').mkdir(parents=True);(models/'server-svtrv2/ctc.onnx').touch()
    monkeypatch.setenv('LOCAL_AGENT_OCR_PYTHON',str(python));monkeypatch.setenv('LOCAL_AGENT_OCR_MODELS',str(models))
    source=tmp_path/'page.png';Image.new('RGB',(200,400),'white').save(source);before=source.read_bytes()
    def run(argv,**kwargs):
        assert argv[-1]=='thorough'
        with Image.open(argv[2]) as crop:assert crop.size==(100,100)
        Path(argv[4]).write_text(json.dumps(dict(text='text',raw_text='text',seconds=1,engine='fixture',requires_review=True,warning='review')),encoding='utf-8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(ocr.subprocess,'run',run)
    result=read_image(source,tmp_path/'out',quality='thorough',crop=[.25,.25,.75,.5])
    assert result['original_dimensions']==(200,400) and source.read_bytes()==before
    with pytest.raises(ValueError,match='ordered'):
        read_image(source,tmp_path/'out',crop=[.8,0,.1,1])



def test_exif_orientation_matches_ocr_and_visual_pixels(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    from PIL import Image
    import hub.image_ocr as ocr
    python=tmp_path/'python.exe';python.touch()
    models=tmp_path/'models';(models/'server-svtrv2').mkdir(parents=True);(models/'server-svtrv2/ctc.onnx').touch()
    monkeypatch.setenv('LOCAL_AGENT_OCR_PYTHON',str(python));monkeypatch.setenv('LOCAL_AGENT_OCR_MODELS',str(models))
    source=tmp_path/'rotated.jpg';im=Image.new('RGB',(100,200),'white');exif=im.getexif();exif[274]=6;im.save(source,exif=exif)
    before=source.read_bytes()
    def run(argv,**kwargs):
        with Image.open(argv[2]) as normalized:assert normalized.size==(200,100)
        Path(argv[4]).write_text(json.dumps(dict(text='text',raw_text='text',seconds=1,engine='fixture',requires_review=True,warning='review')),encoding='utf-8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(ocr.subprocess,'run',run)
    result=read_image(source,tmp_path/'out')
    assert result['original_dimensions']==(200,100)
    assert result['source_path']!=str(source) and source.read_bytes()==before
