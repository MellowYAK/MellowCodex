"""CPU Hebrew OCR worker. Runs only in the isolated OCR environment."""
import json,sys,time
from pathlib import Path
import numpy as np
from paddleocr_hebrew import HebrewOCR
from paddleocr_hebrew.heb_postprocess import cluster_rows,order_row

def assemble(words):
    # Estimate perspective slope from nearby words, independent of text content.
    if len(words)<12:return None
    a=np.array([[(w['bbox'][0]+w['bbox'][2])/2,(w['bbox'][1]+w['bbox'][3])/2,w['bbox'][3]-w['bbox'][1]] for w in words])
    h=float(np.median(a[:,2]));pairs=[]
    for i in range(len(a)):
        for j in range(i):
            dx=a[i,0]-a[j,0];dy=a[i,1]-a[j,1]
            if 1.4*h<abs(dx)<5*h and abs(dy)<min(.55*h,abs(dx)*.16):pairs.append(((a[i,1]+a[j,1])/2,dy/dx))
    if len(pairs)<10:return None
    p=np.array(pairs);low,high=np.quantile(a[:,1],[.15,.75]);bins=[]
    for y in np.linspace(low,high,12):
        z=p[np.abs(p[:,0]-y)<4*h,1]
        if len(z)>3:bins.append((y,float(np.median(z))))
    if len(bins)<4:return None
    fit=np.polyfit(*np.array(bins).T,1);adjusted=[];center=float(np.median(a[:,0]))
    for w,xy in zip(words,a):
        b=list(w['bbox']);shift=float(np.clip(np.polyval(fit,xy[1]),-.16,.16))*(xy[0]-center);b[1]-=shift;b[3]-=shift;adjusted.append(dict(w,bbox=b))
    return [' '.join(w['text'] for w in order_row(row)) for row in cluster_rows(adjusted,.6)]

def main():
    source,models,output=map(Path,sys.argv[1:4]);start=time.perf_counter()
    ocr=HebrewOCR.word(str(models),providers=['CPUExecutionProvider'])
    quality=sys.argv[4] if len(sys.argv)>4 else 'fast'
    result=ocr.read(str(source),rec_mode='nrtr' if quality=='thorough' else 'cascade');raw=[line['text'] for line in result['lines']]
    alternatives=[]
    if quality=='thorough':
        second=ocr.read(str(source),rec_mode='cascade')
        lookup={tuple(w['bbox']):w['text'] for w in second['words']}
        for word in result['words']:
            alternate=lookup.get(tuple(word['bbox']))
            if alternate and alternate!=word['text']:
                alternatives.append({'recognized':word['text'],'alternative':alternate,'bbox':word['bbox']})
        from ocr_layout import rows
        lines=rows(result['words'],with_boxes=True)
        text='\n'.join(line['text'] for line in lines)
    else:
        lines=result['lines'];text='\n'.join(assemble(result['words']) or raw)
    from PIL import Image
    with Image.open(source) as im:width,height=im.size
    regions=[]
    for i in range(0,len(lines),4):
        block=lines[i:i+4];boxes=[line['bbox'] for line in block]
        regions.append({'text':' '.join(line['text'] for line in block)[:80],'crop':[round(max(0,(min(b[0] for b in boxes)-15)/width),4),round(max(0,(min(b[1] for b in boxes)-15)/height),4),round(min(1,(max(b[2] for b in boxes)+15)/width),4),round(min(1,(max(b[3] for b in boxes)+15)/height),4)]})
    result.update(text=text,regions=regions,alternatives=alternatives,raw_text='\n'.join(raw),seconds=round(time.perf_counter()-start,3),engine='paddleocr-hebrew CPU',requires_review=True,warning='Automatic transcription can contain letter, punctuation and reading-order errors. Alternative recognizers can disagree: compare candidates against source pixels, mark unresolved words. Signatures are not verified.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
if __name__=='__main__':main()
