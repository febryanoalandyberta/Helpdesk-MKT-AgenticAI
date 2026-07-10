import py_compile
try:
    py_compile.compile('/home/mkt-bryan/DATA/Helpdesk MKT Agentic AI Automation/backend/api/telegram.py', doraise=True)
    print("Syntax OK")
except Exception as e:
    print(f"Syntax Error: {e}")
