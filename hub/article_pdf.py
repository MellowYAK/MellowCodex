"""Readable, searchable article export when the native renderer cannot print."""
from html import escape
from io import BytesIO
import re
import pymupdf

def render_article(article):
    paragraphs=article.get('paragraphs',[])
    if not article.get('title') or sum(len(p) for p in paragraphs)<200:
        raise ValueError('No substantive article body was found; do not export an empty or login page')
    rtl=bool(re.search(r'[\u0590-\u05ff]',article['title']))
    direction='rtl' if rtl else 'ltr'
    html='<html dir="'+direction+'"><body><h1>'+escape(article['title'])+'</h1>'
    html+='<p dir="ltr" class="source">'+escape(article['url'])+'</p>'
    html+=''.join('<p>'+escape(p).replace('\n','<br>')+'</p>' for p in paragraphs)
    html+='<p dir="ltr" class="source">Readable article export · Original text, without site navigation, advertisements or interactive media.</p></body></html>'
    css='body {font-family:sans-serif;font-size:12pt;line-height:1.55;} h1 {font-size:23pt;} p {margin-bottom:12pt;} .source {font-size:9pt;color:#666;}'
    story=pymupdf.Story(html=html,user_css=css)
    output=BytesIO();writer=pymupdf.DocumentWriter(output)
    bounds=pymupdf.Rect(0,0,595,842);area=pymupdf.Rect(42,42,553,800)
    for _ in range(200):
        more,_=story.place(area)
        device=writer.begin_page(bounds);story.draw(device);writer.end_page()
        if not more:break
    else:raise ValueError('Article exceeded export page limit')
    writer.close()
    raw=output.getvalue()
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        text=''.join(p.get_text() for p in doc)
        if len(text.strip())<200:raise ValueError('PDF has no searchable article text')
    return raw
