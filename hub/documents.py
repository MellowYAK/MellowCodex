"""Unicode document operations; preserve originals and verify saved structure."""
from pathlib import Path
import re

def rtl(text):return bool(re.search(r'[\u0590-\u05ff]',text))

def word_paragraph(paragraph,text):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    if '\ufffd' in text:raise ValueError('Text contains replacement characters; repair source encoding first')
    if rtl(text):
        ppr=paragraph._p.get_or_add_pPr();bidi=OxmlElement('w:bidi');bidi.set(qn('w:val'),'1');ppr.append(bidi)
        paragraph.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    # Latin/number spans are separate directional runs; never reverse stored text.
    for span in re.split(r'([A-Za-z0-9][A-Za-z0-9 .:/_+@%\-]*)',text):
        if not span:continue
        run=paragraph.add_run(span);run.font.name='Arial'
        props=run._r.get_or_add_rPr();direction=OxmlElement('w:rtl');direction.set(qn('w:val'),'1' if rtl(span) else '0');props.append(direction)
        fonts=props.rFonts;fonts.set(qn('w:cs'),'Arial')

def inspect_document(path):
    path=Path(path);suffix=path.suffix.lower()
    if suffix=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(path);pages=[p.extract_text() or '' for p in reader.pages]
        return {'format':'pdf','pages':len(pages),'text':pages,'ocr_required':not any(t.strip() for t in pages)}
    if suffix=='.docx':
        from docx import Document
        doc=Document(path)
        return {'format':'docx','paragraphs':[p.text for p in doc.paragraphs],'tables':[[[c.text for c in r.cells] for r in t.rows] for t in doc.tables]}
    if suffix=='.xlsx':
        from openpyxl import load_workbook
        book=load_workbook(path)
        return {'format':'xlsx','sheets':[{'name':s.title,'rtl':s.sheet_view.rightToLeft,'rows':list(s.values)[:200]} for s in book]}
    raise ValueError('Supported: PDF, DOCX, XLSX')

def write_document(output,operations,source=None):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new output path; the original is preserved')
    output.parent.mkdir(parents=True,exist_ok=True)
    if source and Path(source).suffix.lower()!=output.suffix.lower():raise ValueError('Editing requires the same file format')
    if output.suffix.lower()=='.docx':
        from docx import Document
        doc=Document(source) if source else Document()
        for op in operations:
            if op['type']=='paragraph':word_paragraph(doc.add_paragraph(),op['text'])
            elif op['type']=='replace_paragraph':
                p=doc.paragraphs[op['index']];p.clear();word_paragraph(p,op['text'])
            elif op['type']=='image':
                from docx.shared import Inches
                doc.add_picture(op['path'],width=Inches(op.get('width_inches',5)))
            else:raise ValueError('DOCX operations: paragraph, replace_paragraph, image')
        doc.save(output)
    elif output.suffix.lower()=='.xlsx':
        from openpyxl import Workbook,load_workbook
        from openpyxl.styles import Alignment,Font
        book=load_workbook(source) if source else Workbook()
        for op in operations:
            name=op.get('sheet','Sheet');sheet=book[name] if name in book.sheetnames else book.create_sheet(name)
            sheet.sheet_view.rightToLeft=True
            if op['type']=='cell':
                value=op['value'];cell=sheet[op['cell']]
                if isinstance(value,str) and '\ufffd' in value:raise ValueError('Invalid source encoding')
                cell.value=value
                if isinstance(value,str) and value.startswith('=') and not op.get('formula'):cell.data_type='s'
                cell.alignment=Alignment(horizontal='right' if rtl(str(value)) else 'left',readingOrder=2 if rtl(str(value)) else 1,wrap_text=True);cell.font=Font(name='Arial',size=11)
                sheet.column_dimensions[cell.column_letter].width=op.get('width',35)
            elif op['type']=='image':
                from openpyxl.drawing.image import Image
                sheet.add_image(Image(op['path']),op.get('cell','A1'))
            else:raise ValueError('XLSX operations: cell, image; formula=true explicitly enables a formula')
        book.save(output)
    elif output.suffix.lower()=='.pdf':
        import pymupdf
        doc=pymupdf.open(source) if source else pymupdf.open()
        for op in operations:
            if op['type']=='page':doc.new_page(width=595,height=842)
            else:
                if not doc.page_count:doc.new_page(width=595,height=842)
                page=doc[op.get('page',0)];rect=pymupdf.Rect(op.get('rect',[40,40,555,802]))
                if op['type']=='text':
                    import html
                    markup='<div dir="auto" style="font-family:Arial,sans-serif;font-size:12pt;line-height:1.5">'+html.escape(op['text']).replace('\n','<br>')+'</div>'
                    spare,scale=page.insert_htmlbox(rect,markup,scale_low=1)
                    if spare<0:raise ValueError('Text does not fit; use more space or another page')
                elif op['type']=='image':page.insert_image(rect,filename=op['path'])
                elif op['type']=='redact':page.add_redact_annot(rect,fill=(1,1,1));page.apply_redactions()
                else:raise ValueError('PDF operations: page, text, image, redact; editing is explicit by rectangle, not arbitrary reflow')
        doc.save(output);doc.close()
    else:raise ValueError('Supported output formats: PDF, DOCX, XLSX')
    check=inspect_document(output)
    return {'path':str(output),'bytes':output.stat().st_size,'verified_structure':True,'summary':check,'note':'Structure checked. Visual review is still required. Excel formulas are preserved, not recalculated here.'}
