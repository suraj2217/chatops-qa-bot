from pathlib import Path
root=Path(r'S:\USE\Summer Training')
for name in ['requirements.txt','.env.example','pytest.ini','README.md','chatops_qa/config.py','chatops_qa/app.py','chatops_qa/runner.py','chatops_qa/database.py','chatops_qa/slack_security.py','chatops_qa/commands.py','tests/saucedemo/test_saucedemo.py']:
 p=root/name
 print('\n'+'='*18+' '+name+' '+'='*18)
 print(p.read_text(encoding='utf-8'))
