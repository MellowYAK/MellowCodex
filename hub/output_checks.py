"""Concrete output checks that do not depend on the selected model's prose."""
import re
from pathlib import Path

def missing_document_outputs(goal,actions,workspace):
    if not re.search(r'\b(save|create|export|write|generate|produce)\b|שמור|תשמור|שמירת|צור|תיצור|ייצא|הפק',goal,re.I):return []
    formats=[ext for ext in ('pdf','docx','xlsx') if re.search(r'\b'+ext+r'\b',goal,re.I)]
    missing=[]
    for ext in formats:
        candidates=[]
        for action in actions:
            result=action.get('result') or {}
            if result.get('error'):continue
            if action['tool'] in ('browser_save_pdf','document_write','file_copy','file_share','write_file'):
                path=result.get('path') or (action.get('args') or {}).get('path')
                if path:
                    path=Path(path);path=path if path.is_absolute() else Path(workspace)/path
                    if path.suffix.lower()=='.'+ext:candidates.append(path)
        verified=False
        for path in candidates:
            try:
                if ext=='pdf':
                    import pymupdf
                    with pymupdf.open(path) as doc:verified=doc.page_count>0
                elif ext=='docx':
                    from docx import Document
                    Document(path);verified=True
                else:
                    from openpyxl import load_workbook
                    book=load_workbook(path,read_only=True);verified=bool(book.sheetnames);book.close()
                if verified:break
            except Exception:continue
        if not verified:missing.append(ext)
    return missing
