from app.main import app
for r in app.routes:
    print(r.__class__.__name__, getattr(r, "path", None), getattr(r, "name", None))
