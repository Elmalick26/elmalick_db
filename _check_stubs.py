import ast
import os

for d in ['services', 'repositories']:
    for f in sorted(os.listdir(d)):
        if not f.endswith('.py'):
            continue
        src = open(f'{d}/{f}', encoding='utf-8').read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    print(f'{d}/{f}:{node.lineno} DOCSTRING-ONLY: {node.name}')
                elif len(body) == 1 and isinstance(body[0], ast.Pass):
                    print(f'{d}/{f}:{node.lineno} PASS-ONLY: {node.name}')
