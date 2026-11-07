"""Paged UTF-8 reads with bounded memory, regardless of source file size."""
import hashlib


def read_page(path,offset=0,chars=1500):
    if offset<0 or not 1<=chars<=6000:raise ValueError('Invalid text page')
    before=path.stat();total=0;parts=[];digest=hashlib.sha256()
    with path.open('r',encoding='utf-8') as source:
        while chunk:=source.read(65536):
            digest.update(chunk.encode('utf-8'))
            first=max(0,offset-total);last=min(len(chunk),offset+chars-total)
            if first<last:parts.append(chunk[first:last])
            total+=len(chunk)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('File changed during reading; obtain a fresh page')
    content=''.join(parts);end=offset+len(content)
    return {'path':str(path),'content':content,'offset':offset,
            'next_offset':end if end<total else None,'total_characters':total,'sha256':digest.hexdigest()}
