import inspect
from app.main import app
for r in app.routes:
    print(r.__class__.__name__)
    for name, value in inspect.getmembers(r):
        if not name.startswith("__") and name not in ["app", "dependency_overrides_provider"]:
            try:
                print(f"  {name}: {type(value)}")
            except Exception:
                pass
