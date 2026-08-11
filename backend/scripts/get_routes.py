from app.main import app
for r in app.routes:
    if hasattr(r, "path"):
        print(r.path)
    elif hasattr(r, "routes"):
        for sub in r.routes:
            print("SUB:", getattr(sub, "path", None))
    else:
        print("OTHER:", r)
