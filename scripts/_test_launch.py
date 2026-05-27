"""Quick launch test script."""
import sys
sys.path.insert(0, 'E:/oymm')

import traceback
try:
    from oymm_app.main import main
    print("Starting app...", flush=True)
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
