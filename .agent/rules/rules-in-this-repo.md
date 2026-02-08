---
trigger: always_on
---

# DevelopmentRules

1. **Commenting**: Comment throughout the code, and use Google-style docstrings when the code is complex.
Example of docstring format with a simple function:
```python
def hello_name(name: str) -> str:
    """
    Returns a greeting for the given name.
    
    Args:
        name: The name to greet.
    
    Returns:
        A greeting for the given name.
    """
    return f"Hello, {name}!"
```

2. **Testing**: Always run tests yourself after major changes. Don't stop early if the test for the code you changed breaks. Instead, keep testing and working until it's functional. Use background task management (Rule 7) for test runs to prevent hanging. Use `pytest -qq` unless you need more output. 
3. **ruff checking**: Use `ruff check --fix` (from your venv) and fix any and all issues. 
4. **Type Hints**: Use type hints to make the code more readable and maintainable. 
5. **Documentation**: Keep living notes as you work using memories and keep markdown documentation updated.
6. **Maintainability**: Keep files small and maintainable.
7. **Context**: Use the web tool whenever you need extra context or up-to-date documentation. If a piece of documentation is going to be used frequently, consider storing it in the docs folder. 
8. **Bash Interruptions**: If you see a command ends with a KeyboardInterrupt or ^C, it means the script had to be stopped manually and did not succeed. Look into these errors, and run the command in the background so you don't get stuck  can kill it if it does it again and fix it. Use background task management (Rule 7) for tests and potentially hanging commands.
   - Note: If pytest sticks at the end and doesn't close, it might have a stray process. 
9. **Background Task Management**: For long-running or potentially hanging tasks (like tests), use background execution with timeout:
   ```python
   # Start task with timeout (prevents hanging)
   result = bash(CommandLine="timeout 300 <command>", Background=True, WaitMsBeforeAsync=5000)
   command_id = result.split("Background command ID: ")[1].split("\n")[0]
   
   # Check status periodically (every 20-30 seconds)
   status = command_status(CommandId=command_id, OutputCharacterCount=200)
   
   # If status shows RUNNING, continue checking
   # If status shows DONE, review output and exit code  
   # If task times out, restart with different parameters
   ```
10. **Fail Loudly**: If a command fails, it should fail loudly and provide a clear error message. Don't suppress errors or hide them, especially in order to make a test succeed. 
11. **Logging**: Use logging throughout the code to help with debugging. Programs should log to a file. 
12. **Package Management**: Use `pip install --quiet`, `npm install --quiet`, or similar quiet installation flags to reduce noise.

# Repo Notes

Follow these rules and hints during dev. They'll help you maintain a consistent design. 
- Python venvs should be at: 
  - Spoke: `./ai-pc-spoke/.venv`
  - Hub: `./ai-hub/.venv`
  - General: `./.venv`

  If they don't exist, create them and install the necessary files.

- SUMMARY.md is the authoritative overview of this app. If it's not in your chat history, review it afresh. NEVER edit it unless explicitely told to. 
- Testing: run tests with pytest. Fix errors and warnings. 