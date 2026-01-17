This document outlines the recommended 2026 architecture for sandboxing LLM-generated Python code on a local machine. It satisfies the requirements for **sub-10ms startup times**, **process-level security**, and **dynamic script execution**.


# Secure Python Sandboxing for Agentic AI

## 1. The Stack Selection

To run "freshly written" scripts from an LLM without the 30-second overhead of a compiler (like `py2wasm`), we utilize an **Interpreter-in-a-Box** model.

* **Runtime:** **Wasmtime** (Industry-standard WASI runtime).
* **Interpreter:** **CPython WASI** (Official Tier-2 supported build).
* **The "Speed Hack":** **Wizer** (WebAssembly Pre-initializer).
* **The Bridge:** **WASI Host Functions** (Linking local laptop "skills" into the sandbox).

## 2. Why this Architecture?

1. **Sub-10ms Cold Starts:** Standard `python.wasm` takes ~150ms to boot. By using **Wizer** to snapshot the interpreter's initialized state (loaded built-ins, site-packages), we reduce startup to nearly zero.
2. **No-Network Sandbox:** The Wasm environment has no socket access. It can only interact with the outside world through the **Bridge** functions we explicitly define.
3. **Dynamic Execution:** Unlike `py2wasm` which requires a build step, this approach treats the LLM code as a string passed to a pre-booted interpreter.

---

## 3. Implementation Blueprint

### Step A: The Build Process (One-time)

The developer must create a "Snapshotted" version of Python.

1. Download the official `python.wasm` (WASI build).
2. Use **Wizer** to initialize it:
```bash
# This captures the state of the interpreter after it's warmed up
wasmtime wizer python.wasm -o python-snapshotted.wasm --allow-wasi

```



### Step B: The Host Runner (Python)

This script runs on the laptop, manages the sandbox, and injects the "skills."

```python
import wasmtime
from wasmtime import Engine, Linker, Store, Module, WasiConfig
import json

class AgentSandbox:
    def __init__(self, wasm_path="python-snapshotted.wasm"):
        self.engine = Engine()
        self.linker = Linker(self.engine)
        self.linker.define_wasi()
        
        # --- THE BRIDGE ---
        # Define the local "Skills" that the LLM thinks are local
        def call_skill_proxy(caller, name_ptr, name_len, payload_ptr, payload_len):
            # 1. Access Wasm Memory
            mem = caller.get_export("memory").into_memory()
            name = mem.read(caller, name_ptr, name_ptr + name_len).decode()
            payload = mem.read(caller, payload_ptr, payload_ptr + payload_len).decode()
            
            # 2. Route to your actual local/remote skill logic
            print(f"[Sandbox Bridge] Executing Skill: {name}({payload})")
            return 0 # Success

        # Link the bridge function into the 'env' namespace
        self.linker.define_func("env", "host_call_skill", 
                               wasmtime.FuncType([wasmtime.ValType.i32()] * 4, [wasmtime.ValType.i32()]), 
                               call_skill_proxy)
        
        self.module = Module.from_file(self.engine, wasm_path)

    def run_script(self, llm_code):
        store = Store(self.engine)
        wasi = WasiConfig()
        
        # Pass the code via environment variable or stdin
        wasi.env = [("PYTHON_CODE", llm_code)]
        wasi.inherit_stdout() # For debugging
        store.set_wasi(wasi)
        
        instance = self.linker.instantiate(store, self.module)
        start = instance.exports(store)["_start"]
        
        try:
            start(store)
        except Exception as e:
            print(f"Sandbox Crash: {e}")

# Usage:
sandbox = AgentSandbox()
llm_generated_code = """
import os
code = os.getenv("PYTHON_CODE")
# LLM Logic: call a skill via the bridge
# (In a real setup, you'd wrap the bridge in a nice Python function)
print("Hello from the Sandbox!")
"""
sandbox.run_script(llm_generated_code)

```

---

## 4. Summary for the Developer

* **Security:** Ensure `allow_wasi` is restricted. Do not map the host's root directory (`--dir .`).
* **Performance:** Use the `python-snapshotted.wasm` file for all runs. Do not re-instantiate the Engine every time; reuse it across requests.
* **The "Skill" interface:** You will need a tiny Python "wrapper" script inside the Wasm environment that provides a clean `call_skill(name, data)` function so the LLM doesn't have to deal with the low-level WASI bridge.


## 5. Fallback
Async: Fall back to asteval + sync bridge (currently implemented in the hub)
Sync: Fall back to RestrictedPython (pc-spoke)

## 6. Considerations
- User install: How do we compile everything into one shippable binary? 