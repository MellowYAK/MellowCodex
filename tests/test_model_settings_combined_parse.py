from hub.model_settings import parse_model_command

def test_combined_parser_he():
    value = parse_model_command('הגדר את שניהם ל־16000')
    assert value == {'action':'set_many','fields':{'context_tokens':16000,'response_tokens':16000},'scope':'default'}, value

def test_combined_parser_en():
    value = parse_model_command('Set context and response tokens to 16000')
    assert value == {'action':'set_many','fields':{'context_tokens':16000,'response_tokens':16000},'scope':'default'}, value
