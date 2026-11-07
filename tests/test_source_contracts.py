from hub.context.contracts import source_contracts


def test_validator_branch_cases_preserve_exclusive_inputs_and_do_not_run_calls():
    text='''class Delivery(BaseModel):
    kind: Literal['email', 'sms'] = 'email'
    email: str = ''
    phone: str = ''
    @model_validator(mode='after')
    def target(self):
        if (self.kind == 'email' and (not self.email or self.phone)) or (self.kind != 'email' and (not self.phone or self.email)):
            raise ValueError(secret_function())
        return self
'''
    facts=source_contracts('delivery.py',text,20)[0]['validators_to_check'][0]['measured_branch_cases']
    accepted=[r['inputs'] for r in facts['cases'] if not r['enters_raise_branch']]
    assert accepted==[{'kind':'email','email':True,'phone':False},{'kind':'sms','email':False,'phone':True}]
    assert facts['input_representation']=={'kind':'literal_value','email':'truthiness','phone':'truthiness'}
    assert len(facts['cases'])==8 and facts['line']==26
    for modified in (text.replace('not self.email','self.email.strip()'),
                     text.replace('        if (','        self.email = normalize(self.email)\n        if ('),
                     text.replace("mode='after'","mode='before'"),
                     text.replace('not self.email',"self.email == 'someone'")):
        assert 'measured_branch_cases' not in source_contracts('delivery.py',modified)[0]['validators_to_check'][0]


def test_direct_key_reads_retain_conditions_and_do_not_invent_user_requirements():
    from hub.context.contracts import source_flow
    result=source_flow('worker.py',"def build(spec):\n    mode=spec.get('mode', 'document')\n    if mode == 'document':\n        body=spec['body']\n    spec['output']=render(body)\n    return spec['output']",start=20)
    reads=[f for f in result['facts'] if f['kind']=='key_read']
    assert [(f['key'],f['line']) for f in reads]==[('body',23),('output',25)]
    assert reads[0]['conditions']==["mode == 'document'"]
    assert reads[1]['conditions']==[]
    assert all('required' not in f for f in reads)
    call=next(f for f in result['facts'] if f.get('callee')=='spec.get')
    assert call['positional_inputs']==["'mode'", "'document'"]


def test_flow_records_composition_without_guessing_compatibility():
    from hub.context.contracts import source_flow
    source='''def build(request):
    document = render_document(request.text)
    if request.publish:
        receipt = deliver(document, recipient=request.recipient)
        return receipt
    return document
'''
    result=source_flow('unrelated/reports.py',source,50)
    facts=result['facts']
    assignments=[f for f in facts if f['kind']=='assignment']
    assert assignments[0]['outputs']==['document'] and assignments[0]['line']==51
    delivery=next(f for f in facts if f.get('callee')=='deliver')
    assert delivery['positional_inputs']==['document']
    assert delivery['keyword_inputs']==[{'name':'recipient','expression':'request.recipient'}]
    assert delivery['conditions']==['request.publish']
    assert facts[-1]['conditions']==[]
    assert 'not proof' in result['scope']


def test_flow_partial_truncation_and_no_execution(tmp_path):
    from hub.context.contracts import source_flow
    target=tmp_path/'never-created'
    source=f"open({str(target)!r}, 'w').write('unsafe')"
    result=source_flow('code.py',source,limit=1)
    assert len(result['facts'])==1 and result['omitted_count']==1
    assert not target.exists()
    assert source_flow('a.py','    return value')['parse_status']=='incomplete_or_invalid_excerpt'
    assert source_flow('a.js','return value')['parse_status']=='unsupported'


def test_flow_keeps_else_and_keyword_unpacking_explicit():
    from hub.context.contracts import source_flow
    result=source_flow('a.py','''async def convert(x):
    if x:
        await first(**x)
    else:
        second(x)
''')
    calls=[f for f in result['facts'] if f['kind']=='call']
    assert calls[0]['keyword_inputs']==[{'name':None,'expression':'x'}]
    assert calls[1]['conditions']==['not (x)']


def test_partial_excerpt_only_extracts_whole_indexed_functions():
    from hub.context.contracts import source_flow
    excerpt='    tail_of_previous()\n\ndef middle(value):\n    return convert(value)\n\ndef unfinished(value):\n'
    symbols=[{'name':'previous','kind':'FunctionDef','line':3,'end_line':10},
             {'name':'middle','kind':'FunctionDef','line':12,'end_line':13},
             {'name':'unfinished','kind':'FunctionDef','line':15,'end_line':22}]
    flow=source_flow('partial.py',excerpt,start=10,symbols=symbols)
    assert flow['parse_status']=='complete_units_in_partial_excerpt'
    assert flow['complete_units']==[{'name':'middle','start':12,'end':13}]
    assert {f['function'] for f in flow['facts']}=={'middle'}
    assert next(f for f in flow['facts'] if f['kind']=='call')['line']==13
    assert 'surrounding code is incomplete' in flow['scope']


def test_required_defaults_factories_and_literal_contracts():
    text='''class Job(BaseModel):
    request_id: str
    asset: str = Field(min_length=1)
    prompt: str = Field(...)
    count: int = Field(3, ge=1)
    mode: Literal['fast', 'quality'] = 'fast'
    labels: list[str] = Field(default_factory=list)
    optional: str | None = None
'''
    c=source_contracts('arbitrary/project.py',text,20)[0]
    fields={f['field']:f for f in c['fields']}
    assert {k for k,v in fields.items() if v['required_in_this_declaration']}=={'request_id','asset','prompt'}
    assert fields['count']['default_expression']=='3'
    assert fields['labels']['default_expression']=='list'
    assert fields['mode']['annotation']=="Literal['fast', 'quality']"
    assert fields['request_id']['line']==21
    assert 'validators' in c['scope']


def test_partial_and_non_python_sources_do_not_claim_absence():
    assert source_contracts('partial.py','  required: str')==[]
    assert source_contracts('code.js','class Job(BaseModel):\n    required: str')==[]


def test_complete_indexed_class_survives_a_cutoff_next_function():
    text='class Request(BaseModel):\n    value: str\n\ndef partial():\n'
    result=source_contracts('request.py',text,10,symbols=[{'kind':'ClassDef','name':'Request','line':10,'end_line':11}])
    assert result[0]['fields'][0]['field']=='value'
    assert result[0]['fields'][0]['line']==11
    assert source_contracts('request.py',text,10,symbols=[{'kind':'ClassDef','name':'Request','line':10,'end_line':19}])==[]


def test_conditional_validator_preserved_without_calling_it():
    text='''class Request(BaseModel):
    asset: str = ''
    @model_validator(mode='after')
    def validate_asset(self):
        if not self.asset: raise ValueError('missing asset')
        return self
'''
    contract=source_contracts('request.py',text)[0]
    assert not contract['fields'][0]['required_in_this_declaration']
    assert "if not self.asset: raise ValueError('missing asset')" in contract['validators_to_check'][0]['source']


def test_valid_python_prefix_does_not_imply_complete_schema():
    full="class Generate(BaseModel):\n    name: str\n    project: str = ''\n"
    symbols=[{'kind':'ClassDef','name':'Generate','line':10,'end_line':12}]
    partial=source_contracts('a.py','\n'.join(full.splitlines()[:2]),10,symbols)[0]
    assert partial['class_source_complete'] is False
    assert partial['required_class_range']=={'start':10,'end':12}
    assert [f['field'] for f in partial['fields']]==['name']
    assert source_contracts('a.py',full,10,symbols)[0]['class_source_complete'] is True
    assert source_contracts('a.py',full,10)[0]['class_source_complete'] is None
