"""Optional isolated Hebrew OCR adapter; never loads the chat model."""
import json,os,subprocess,uuid
from pathlib import Path
from .config import ROOT

def read_image(path,output_dir,*,quality='fast',crop=None):
    if quality not in ('fast','thorough'):raise ValueError('Unknown OCR quality')
    python=Path(os.environ.get('LOCAL_AGENT_OCR_PYTHON',str(ROOT/'tools/hebrew-ocr-venv/Scripts/python.exe')))
    models=Path(os.environ.get('LOCAL_AGENT_OCR_MODELS',str(ROOT/'models/hebrew-ocr')))
    if not python.is_file() or not (models/'server-svtrv2/ctc.onnx').is_file():
        raise RuntimeError('Hebrew OCR is not installed. Configure LOCAL_AGENT_OCR_PYTHON and LOCAL_AGENT_OCR_MODELS; see README. No recognition was performed.')
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    output=output_dir/('ocr-'+uuid.uuid4().hex+'.json')
    from PIL import Image,ImageOps
    with Image.open(path) as original:
        picture=ImageOps.exif_transpose(original)
        dimensions=picture.size
        if crop is not None:
            if len(crop)!=4 or not all(0<=v<=1 for v in crop) or crop[0]>=crop[2] or crop[1]>=crop[3]:
                raise ValueError('crop requires ordered fractions [left,top,right,bottom] within 0..1')
            bounds=tuple(round(v*dimensions[i%2]) for i,v in enumerate(crop))
            if bounds[2]-bounds[0]<8 or bounds[3]-bounds[1]<8:raise ValueError('OCR crop is too small')
            path=output.with_suffix('.source.png')
            picture.crop(bounds).save(path)
        elif original.getexif().get(274,1)!=1:
            path=output.with_suffix('.source.png')
            picture.save(path)
    worker=Path(__file__).resolve().parents[1]/'scripts/hebrew_ocr_worker.py'
    run=subprocess.run([str(python),str(worker),str(path),str(models),str(output),quality],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:raise RuntimeError('OCR failed: '+run.stderr[-3000:])
    result=json.loads(output.read_text(encoding='utf-8'))
    text_path=output.with_suffix('.txt');text_path.write_text(result['text'],encoding='utf-8')
    return {k:result[k] for k in ('text','raw_text','seconds','engine','requires_review','warning')}|{'regions':result.get('regions',[]) if crop is None else [],'alternatives':result.get('alternatives',[]),'evidence_path':str(output),'text_path':str(text_path),'source_path':str(path),'original_dimensions':dimensions,'crop':crop,'quality':quality}
