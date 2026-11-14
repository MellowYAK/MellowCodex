import pytest
from pydantic import ValidationError
from hub.model_settings import ModelSettings, field_metadata

def test_16000_output_and_context():
    settings = ModelSettings(context_tokens=16000, response_tokens=16000)
    assert settings.context_tokens == 16000
    assert settings.response_tokens == 16000
    assert field_metadata()['response_tokens']['maximum'] == 16000
    with pytest.raises(ValidationError):
        ModelSettings(response_tokens=16001)
