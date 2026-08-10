from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_admin
from app.services.auth_service import authenticate_admin, create_access_token_for_admin
from app.models.admin import Admin

router = APIRouter(tags=["auth"])

@router.get("/debug-admin")
async def debug_admin(db: AsyncSession = Depends(get_db)):
    """TEMPORARY: check admin status"""
    try:
        result = await db.execute(text("SELECT username, is_active FROM admins"))
        rows = result.fetchall()
        return {"admin_count": len(rows), "admins": [{"username": r[0], "is_active": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/debug-create")
async def debug_create(db: AsyncSession = Depends(get_db)):
    """TEMPORARY: force-create admin"""
    try:
        import uuid as _u, bcrypt as _b
        row = (await db.execute(text("SELECT id FROM admins WHERE username='user'"))).fetchone()
        if row:
            return {"status": "already_exists"}
        _hash = _b.hashpw(b"12345", _b.gensalt()).decode()
        await db.execute(
            text("INSERT INTO admins (id, username, password_hash, full_name, is_active) VALUES (:id, 'user', :pw, 'Admin', 1)"),
            {"id": str(_u.uuid4()), "pw": _hash}
        )
        await db.commit()
        return {"status": "created_ok"}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@router.post("/login")
async def login(response: Response, data: dict, db: AsyncSession = Depends(get_db)):
    admin = await authenticate_admin(db, data.get("username"), data.get("password"))
    if not admin:
        raise HTTPException(status_code=400, detail="Invalid credentials")
        
    token = await create_access_token_for_admin(admin.id, admin.username)
    response.set_cookie(key="jwt", value=token, httponly=True)
    return {"token": token, "message": "Success", "admin": {"username": admin.username, "full_name": admin.full_name}}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("jwt")
    return {"message": "Logged out"}

@router.get("/me")
async def get_me(admin: Admin = Depends(get_current_admin)):
    return {"username": admin.username, "full_name": admin.full_name}
