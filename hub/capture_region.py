"""Crop evidence using source-image pixels, preserving desktop coordinates."""
from pathlib import Path
import uuid
from PIL import Image


def crop_capture(shot, region):
    if not isinstance(region, list) or len(region) != 4 or any(type(v) is not int for v in region):
        raise ValueError('region must be [left, top, width, height] integer source-image pixels')
    x,y,width,height=region
    with Image.open(shot['path']) as source:
        if min(x,y)<0 or min(width,height)<=0 or x+width>source.width or y+height>source.height:
            raise ValueError('region is outside the captured source image')
        token=uuid.uuid4().hex
        path=Path(shot['path']).with_name(token+'.png')
        source.crop((x,y,x+width,y+height)).save(path)
    return {**shot,'id':token,'path':str(path),'source_capture_id':shot['id'],
            'source_path':shot['path'],'region':region,'left':shot['left']+x,
            'top':shot['top']+y,'width':width,'height':height,'input_ready':False}
