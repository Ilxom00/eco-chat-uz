from app.main import app
for r in app.routes:
    if hasattr(r, "path"):
        print(r.path)
    elif hasattr(r, "include_context"):
        ctx = r.include_context
        prefix = ctx.prefix
        for sub in ctx.included_router.routes:
            print(prefix + sub.path)
