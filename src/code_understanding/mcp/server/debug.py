import os
import sys

# Only activate debugpy when explicitly intended
if os.environ.get("DEBUGPY", "") == "1" and not os.environ.get("MCP_CHILD", "") == "1":
    try:
        import debugpy

        sys.stderr.write("🔍 [DEBUGPY] Listening for debugger attach on port 5678...\n")
        sys.stderr.flush()
        debugpy.listen(("127.0.0.1", 5678))
        debugpy.wait_for_client()
        sys.stderr.write("✅ [DEBUGPY] Debugger attached.\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"❌ [DEBUGPY] Debugger setup failed: {e}\n")
        sys.stderr.flush()
