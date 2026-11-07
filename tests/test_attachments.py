import base64
import pytest
from hub.attachments import prepare_attachments

def test_user_text_attachment():
    text,images=prepare_attachments([{'name':'hello.txt','data':base64.b64encode('שלום'.encode()).decode(),'type':'text/plain'}])
    assert 'שלום' in text and not images

def test_binary_attachment_rejected():
    with pytest.raises(ValueError):prepare_attachments([{'data':'AA==','name':'binary'}])
