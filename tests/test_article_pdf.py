import pymupdf
import pytest
from hub.article_pdf import render_article

def test_article_export_retains_all_pages_and_literal_markup():
 paragraphs=['טקסט בעברית עם English 123 ומידע נוסף. '*12 for _ in range(15)]
 paragraphs.append('END-OF-ARTICLE <b>literal markup</b>')
 raw=render_article({'title':'כותרת בעברית English','url':'https://example.test/article','paragraphs':paragraphs})
 with pymupdf.open(stream=raw,filetype='pdf') as doc:
  assert len(doc)>1
  text=''.join(p.get_text() for p in doc)
  assert 'END-OF-ARTICLE' in text and 'literal markup' in text
  assert 'https://example.test/article' in text
  assert '\ufffd' not in text

def test_empty_or_login_page_is_not_successful_article_export():
 with pytest.raises(ValueError,match='substantive article'):
  render_article({'title':'Log in','url':'https://example.test/login','paragraphs':['Sign in']})
