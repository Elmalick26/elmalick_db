import ast
import os

for f in sorted(os.listdir('repositories')):
    if not f.endswith('.py'):
        continue
    src = open(f'repositories/{f}', encoding='utf-8').read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Expr)):
                if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    print(f'{f}:{node.lineno} DOCSTRING-ONLY: {node.name}')
                elif isinstance(body[0], ast.Pass):
                    print(f'{f}:{node.lineno} PASS-ONLY: {node.name}')
