"""Measured Python request schemas, without inferring runtime semantics."""
import ast
import itertools


def validator_branch_cases(member, fields, start):
    """Finite predicate interpretation, never execute project code or call Python eval.

    Only an unmodified instance, one rejecting if, then return self is supported.
    Cases describe this branch, not complete model/runtime validity.
    """
    body=member.body
    if len(body)!=2 or not isinstance(body[0],ast.If) or not isinstance(body[1],ast.Return):return None
    branch=body[0]
    if branch.orelse or len(branch.body)!=1 or not isinstance(branch.body[0],ast.Raise):return None
    if not isinstance(body[1].value,ast.Name) or body[1].value.id!='self':return None
    declarations={f.target.id:f for f in fields}
    domains={};kinds={}
    def field(node):
        if not isinstance(node,ast.Attribute) or not isinstance(node.value,ast.Name) or node.value.id!='self':raise ValueError()
        name=node.attr
        declaration=declarations[name]
        annotation=declaration.annotation
        if isinstance(annotation,ast.Subscript) and ast.unparse(annotation.value).split('.')[-1]=='Literal':
            values=annotation.slice.elts if isinstance(annotation.slice,ast.Tuple) else [annotation.slice]
            if not all(isinstance(v,ast.Constant) and type(v.value) in (str,int,bool,type(None)) for v in values):raise ValueError()
            domains[name]=[v.value for v in values];kinds[name]='literal_value'
        elif isinstance(annotation,ast.Name) and annotation.id in ('str','bool'):
            domains[name]=[False,True];kinds[name]='truthiness'
        else:raise ValueError()
        return name
    def interpret(node,values=None):
        if isinstance(node,ast.Attribute):
            name=field(node);return values[name] if values is not None else False
        if isinstance(node,ast.Constant) and type(node.value) in (str,int,bool,type(None)):return node.value
        if isinstance(node,ast.BoolOp) and isinstance(node.op,(ast.And,ast.Or)):
            parts=[interpret(v,values) for v in node.values]
            return all(parts) if isinstance(node.op,ast.And) else any(parts)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.Not):return not interpret(node.operand,values)
        if isinstance(node,ast.Compare) and len(node.ops)==1 and isinstance(node.ops[0],(ast.Eq,ast.NotEq)):
            for side in (node.left,node.comparators[0]):
                if not isinstance(side,(ast.Attribute,ast.Constant)):raise ValueError()
                if isinstance(side,ast.Attribute) and kinds.get(field(side))!='literal_value':raise ValueError()
            left,right=interpret(node.left,values),interpret(node.comparators[0],values)
            return left==right if isinstance(node.ops[0],ast.Eq) else left!=right
        raise ValueError()
    try:
        interpret(branch.test)
        size=1
        for values in domains.values():size*=len(values)
        if not domains or size>64:return None
        cases=[]
        for combination in itertools.product(*domains.values()):
            values=dict(zip(domains,combination))
            cases.append({'inputs':values,'enters_raise_branch':bool(interpret(branch.test,values))})
        return {'line':start+branch.lineno-1,'predicate':ast.unparse(branch.test),
                'input_representation':kinds,'cases':cases,
                'scope':'Exact predicate cases for this straight-line validator only. Truthiness is not a supplied value. Other fields, validators, types, defaults and downstream execution are not verified.'}
    except (ValueError,KeyError,TypeError,RecursionError):return None


def source_flow(path, text, start=1, limit=60, symbols=None):
    """Measured call/return wiring; no execution, alias resolution or feasibility claim."""
    result={'path':path,'parse_status':'unsupported','facts':[], 'omitted_count':0,
            'scope':'Syntax-only wiring in this excerpt. Branches may not execute; names are not resolved. Matching names are not proof of compatible types or an end-to-end capability.'}
    if not path.endswith('.py'):return result
    try:tree=ast.parse(text)
    except (SyntaxError,ValueError,RecursionError):
        result['parse_status']='incomplete_or_invalid_excerpt'
        # Only use complete indexed units actually present in the delivered
        # excerpt. Never invent the missing beginning/end of a function.
        import textwrap
        lines=text.split('\n');end=start+len(lines)-1
        units=[s for s in (symbols or []) if s.get('kind') in ('FunctionDef','AsyncFunctionDef','ClassDef')
               and start<=s.get('line',0)<=s.get('end_line',0)<=end]
        outer=[s for s in units if not any(o is not s and o['line']<=s['line'] and o['end_line']>=s['end_line']
                                        and (o['line'],o['end_line'])!=(s['line'],s['end_line']) for o in units)]
        facts=[];covered=[]
        for unit in sorted(outer,key=lambda s:s['line']):
            snippet=textwrap.dedent('\n'.join(lines[unit['line']-start:unit['end_line']-start+1]))
            parsed=source_flow(path,snippet,unit['line'],limit=max(0,limit-len(facts)))
            if parsed['parse_status']!='parsed':continue
            covered.append({'name':unit['name'],'start':unit['line'],'end':unit['end_line']})
            facts.extend(parsed['facts']);result['omitted_count']+=parsed['omitted_count']
        if covered:
            result.update(parse_status='complete_units_in_partial_excerpt',facts=facts,complete_units=covered)
            result['scope']+=' Only listed complete units were parsed; surrounding code is incomplete and enclosing conditions may be outside the excerpt.'
        return result
    result['parse_status']='parsed'
    facts=[]
    class Visitor(ast.NodeVisitor):
        def __init__(self):self.functions=[];self.conditions=[]
        def add(self,node,kind,**data):
            facts.append({'kind':kind,'function':'.'.join(self.functions) or '<module>',
                          'line':start+node.lineno-1,'conditions':list(self.conditions),**data})
        def visit_FunctionDef(self,node):
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
        def visit_If(self,node):
            self.visit(node.test)
            self.conditions.append(ast.unparse(node.test))
            for child in node.body:self.visit(child)
            self.conditions.pop()
            self.conditions.append('not ('+ast.unparse(node.test)+')')
            for child in node.orelse:self.visit(child)
            self.conditions.pop()
        def visit_Assign(self,node):
            if isinstance(node.value,(ast.Call,ast.Await)):
                self.add(node,'assignment',outputs=[ast.unparse(t) for t in node.targets],expression=ast.unparse(node.value))
            self.generic_visit(node)
        def visit_Call(self,node):
            self.add(node,'call',callee=ast.unparse(node.func),
                     positional_inputs=[ast.unparse(a) for a in node.args],
                     keyword_inputs=[{'name':k.arg,'expression':ast.unparse(k.value)} for k in node.keywords])
            self.generic_visit(node)
        def visit_Return(self,node):
            self.add(node,'return',expression=ast.unparse(node.value) if node.value else None)
            self.generic_visit(node)
        def visit_Subscript(self,node):
            # Preserve lookup syntax, not a claim about mandatory user input.
            # The value may be produced earlier or the branch may never run.
            if isinstance(node.ctx,ast.Load) and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str):
                self.add(node,'key_read',container=ast.unparse(node.value),key=node.slice.value,
                         expression=ast.unparse(node),lookup='direct_subscript')
            self.generic_visit(node)
    Visitor().visit(tree)
    result['facts']=facts[:max(0,limit)]
    result['omitted_count']=max(0,len(facts)-max(0,limit))
    return result


def source_contracts(path, text, start=1, symbols=None):
    if not path.endswith('.py'):
        return []
    try:
        tree=ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        import textwrap
        lines=text.split('\n');end=start+len(lines)-1
        contracts=[]
        for unit in symbols or []:
            if unit.get('kind')!='ClassDef' or not start<=unit.get('line',0)<=unit.get('end_line',0)<=end:continue
            snippet=textwrap.dedent('\n'.join(lines[unit['line']-start:unit['end_line']-start+1]))
            contracts.extend(source_contracts(path,snippet,unit['line'],symbols=[unit]))
        if contracts:return contracts
        return []  # A partial range is not evidence of an absent schema.
    contracts=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.ClassDef):continue
        if not any(ast.unparse(base).split('.')[-1]=='BaseModel' for base in node.bases):continue
        fields=[]
        for field in node.body:
            if not isinstance(field,ast.AnnAssign) or not isinstance(field.target,ast.Name):continue
            value=field.value
            required=value is None or isinstance(value,ast.Constant) and value.value is Ellipsis
            default=None
            if isinstance(value,ast.Call) and ast.unparse(value.func).split('.')[-1]=='Field':
                keywords={k.arg:k.value for k in value.keywords}
                supplied=keywords.get('default',value.args[0] if value.args else None)
                factory=keywords.get('default_factory')
                required=factory is None and (supplied is None or isinstance(supplied,ast.Constant) and supplied.value is Ellipsis)
                if not required:default=ast.unparse(factory if factory is not None else supplied)
            elif value is not None and not required:
                default=ast.unparse(value)
            fields.append({'field':field.target.id,'annotation':ast.unparse(field.annotation),
                           'required_in_this_declaration':required,'default_expression':default,
                           'line':start+field.lineno-1})
        if fields:
            validators=[]
            for member in node.body:
                if not isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                names=[ast.unparse(d.func if isinstance(d,ast.Call) else d).split('.')[-1] for d in member.decorator_list]
                if not set(names)&{'model_validator','field_validator','validator','root_validator'}:continue
                validator={'function':member.name,'line':start+member.lineno-1,
                           'source':ast.get_source_segment(text,member)}
                after=any(isinstance(d,ast.Call) and ast.unparse(d.func).split('.')[-1]=='model_validator'
                          and any(k.arg=='mode' and isinstance(k.value,ast.Constant) and k.value.value=='after' for k in d.keywords)
                          for d in member.decorator_list)
                if after:
                    cases=validator_branch_cases(member,[f for f in node.body if isinstance(f,ast.AnnAssign) and isinstance(f.target,ast.Name)],start)
                    if cases is not None:validator['measured_branch_cases']=cases
                validators.append(validator)
            class_line=start+node.lineno-1
            indexed=next((unit for unit in (symbols or []) if unit.get('kind')=='ClassDef'
                          and unit.get('line')==class_line and unit.get('name')==node.name),None)
            excerpt_end=start+len(text.splitlines())-1
            complete=(indexed['end_line']<=excerpt_end) if indexed and indexed.get('end_line') else None
            contracts.append({'class':node.name,'path':path,'line':class_line,'fields':fields,
                              'class_source_complete':complete,
                              'required_class_range':{'start':class_line,'end':indexed['end_line']} if indexed else None,
                              'validators_to_check':validators,
                              'scope':'Static declarations in the delivered excerpt only. A syntactically valid excerpt may end inside a class. Missing fields or validators cannot establish absence unless the complete indexed class was read. Inheritance, workers and runtime behavior remain separate checks.'})
    return contracts
