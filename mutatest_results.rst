Mutatest diagnostic summary
===========================
 - Source location: C:\Users\EL MALICK\OneDrive\Documents\El Malick Gest - Copie\services
 - Test commands: ['cmd', '/c', 'run_service_tests.cmd']
 - Mode: s
 - Excluded files: []
 - N locations input: 20
 - Random seed: 42

Random sample details
---------------------
 - Total locations mutated: 20
 - Total locations identified: 158
 - Location sample coverage: 12.66 %


Running time details
--------------------
 - Clean trial 1 run time: 0:00:05.751969
 - Clean trial 2 run time: 0:00:05.654790
 - Mutation trials total run time: 0:02:49.114260

Overall mutation trial summary
==============================
 - DETECTED: 44
 - SURVIVED: 7
 - TOTAL RUNS: 51
 - RUN DATETIME: 2026-05-16 06:51:47.228460


Mutations by result status
==========================


SURVIVED
--------
 - services\attendance_service.py: (l: 91, c: 15) - mutation from <class 'ast.Eq'> to <class 'ast.LtE'>
 - services\attendance_service.py: (l: 96, c: 16) - mutation from If_Statement to If_False
 - services\backup_service.py: (l: 24, c: 37) - mutation from None to True
 - services\backup_service.py: (l: 44, c: 8) - mutation from If_Statement to If_True
 - services\finance_service.py: (l: 188, c: 33) - mutation from <class 'ast.Gt'> to <class 'ast.GtE'>
 - services\grade_service.py: (l: 48, c: 55) - mutation from <class 'ast.Eq'> to <class 'ast.GtE'>
 - services\migration_service.py: (l: 40, c: 31) - mutation from <class 'ast.Or'> to <class 'ast.And'>


DETECTED
--------
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.Mod'>
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.Sub'>
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.FloorDiv'>
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.Add'>
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.Div'>
 - services\attendance_service.py: (l: 36, c: 23) - mutation from <class 'ast.Mult'> to <class 'ast.Pow'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.Add'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.Mod'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.Pow'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.FloorDiv'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.Mult'>
 - services\attendance_service.py: (l: 36, c: 24) - mutation from <class 'ast.Div'> to <class 'ast.Sub'>
 - services\attendance_service.py: (l: 49, c: 8) - mutation from If_Statement to If_False
 - services\attendance_service.py: (l: 49, c: 8) - mutation from If_Statement to If_True
 - services\attendance_service.py: (l: 91, c: 12) - mutation from If_Statement to If_False
 - services\attendance_service.py: (l: 91, c: 12) - mutation from If_Statement to If_True
 - services\attendance_service.py: (l: 92, c: 36) - mutation from None to True
 - services\attendance_service.py: (l: 92, c: 36) - mutation from None to False
 - services\attendance_service.py: (l: 96, c: 16) - mutation from If_Statement to If_True
 - services\attendance_service.py: (l: 125, c: 8) - mutation from If_Statement to If_False
 - services\attendance_service.py: (l: 125, c: 8) - mutation from If_Statement to If_True
 - services\attendance_service.py: (l: 157, c: 15) - mutation from None to False
 - services\attendance_service.py: (l: 157, c: 15) - mutation from None to True
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.Mod'>
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.FloorDiv'>
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.Div'>
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.Pow'>
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.Sub'>
 - services\backup_service.py: (l: 67, c: 61) - mutation from <class 'ast.Mult'> to <class 'ast.Add'>
 - services\backup_service.py: (l: 91, c: 20) - mutation from If_Statement to If_False
 - services\backup_service.py: (l: 91, c: 20) - mutation from If_Statement to If_True
 - services\backup_service.py: (l: 116, c: 83) - mutation from None to True
 - services\backup_service.py: (l: 116, c: 83) - mutation from None to False
 - services\finance_service.py: (l: 188, c: 33) - mutation from <class 'ast.Gt'> to <class 'ast.LtE'>
 - services\finance_service.py: (l: 188, c: 33) - mutation from <class 'ast.Gt'> to <class 'ast.Eq'>
 - services\finance_service.py: (l: 188, c: 33) - mutation from <class 'ast.Gt'> to <class 'ast.NotEq'>
 - services\finance_service.py: (l: 188, c: 33) - mutation from <class 'ast.Gt'> to <class 'ast.Lt'>
 - services\grade_service.py: (l: 29, c: 36) - mutation from <class 'ast.In'> to <class 'ast.NotIn'>
 - services\grade_service.py: (l: 48, c: 55) - mutation from <class 'ast.Eq'> to <class 'ast.Lt'>
 - services\grade_service.py: (l: 48, c: 55) - mutation from <class 'ast.Eq'> to <class 'ast.LtE'>
 - services\grade_service.py: (l: 48, c: 55) - mutation from <class 'ast.Eq'> to <class 'ast.NotEq'>
 - services\migration_service.py: (l: 25, c: 12) - mutation from If_Statement to If_False
 - services\migration_service.py: (l: 25, c: 12) - mutation from If_Statement to If_True
 - services\migration_service.py: (l: 32, c: 17) - mutation from <class 'ast.And'> to <class 'ast.Or'>