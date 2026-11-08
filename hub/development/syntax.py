"""Parse Python without importing it or writing bytecode."""
import ast

def python_errors(files):
    errors=[]
    for path,data in files.items():
        if not path.endswith('.py'):continue
        try:
            ast.parse(data,filename=path)
        except (SyntaxError,UnicodeError,ValueError) as exc:
            errors.append({'path':path,'line':getattr(exc,'lineno',None),'error':getattr(exc,'msg',str(exc))})
    return errors
