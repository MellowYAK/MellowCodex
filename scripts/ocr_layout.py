"""Group slanted document word boxes into reading rows without text-specific rules."""
import numpy as np
from paddleocr_hebrew.heb_postprocess import order_row

def rows(words,with_boxes=False):
    pending=list(words); result=[]
    while pending:
        a=np.array([[(w['bbox'][0]+w['bbox'][2])/2,(w['bbox'][1]+w['bbox'][3])/2] for w in pending])
        h=float(np.median([w['bbox'][3]-w['bbox'][1] for w in pending])); best=None
        for slope in np.linspace(-.18,.18,181):
            offsets=a[:,1]-slope*a[:,0]
            distances=np.abs(offsets[:,None]-offsets[None,:]); masks=distances<h*.38
            counts=masks.sum(axis=1);residuals=(distances*masks).sum(axis=1)/counts
            candidates=np.flatnonzero(counts==counts.max());j=candidates[np.argmin(residuals[candidates])]
            anchor=offsets[j];mask=masks[j];score=int(counts[j]);residual=float(residuals[j])
            rank=(score,-residual)
            if best is None or rank>best[0]:best=(rank,mask,slope,anchor)
        mask=best[1]; selected=[w for w,m in zip(pending,mask) if m]
        boxes=[w['bbox'] for w in selected]
        result.append((float(np.mean(a[mask,1])), {'text':' '.join(w['text'] for w in order_row(selected)), 'bbox':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]}))
        pending=[w for w,m in zip(pending,mask) if not m]
    ordered=[s for _,s in sorted(result,key=lambda x:x[0])]
    return ordered if with_boxes else [s['text'] for s in ordered]

