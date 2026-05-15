"""Script to generate db_schema.py from database_setup.py."""
import re

with open('database_setup.py', encoding='utf-8') as f:
    lines = f.readlines()

method_lines = lines[133:1028]  # full initialize_database method

header = [
    '"""Database schema initialization -- extracted from database_setup.py."""\n',
    'import logging\n',
    'from psycopg2 import Error  # noqa: F401\n',
    '\n',
    '_logger = logging.getLogger("DatabaseManager")\n',
    '\n',
    '\n',
    'def initialize_schema(db_manager) -> None:\n',
    '    """Create / migrate all database tables. Call once at startup."""\n',
]

body = []
skip_first = True
for line in method_lines:
    if skip_first:
        skip_first = False
        continue
    # Convert 8-space indent -> 4-space (method -> function)
    if line.startswith('        '):
        line = '    ' + line[8:]
    line = line.replace('self.get_connection()', 'db_manager.get_connection()')
    line = line.replace('logger.info(', '_logger.info(')
    line = line.replace('logger.error(', '_logger.error(')
    line = line.replace('logger.warning(', '_logger.warning(')
    body.append(line)

with open('db_schema.py', 'w', encoding='utf-8') as f:
    f.writelines(header + body)

print(f'db_schema.py: {len(header) + len(body)} lines')
