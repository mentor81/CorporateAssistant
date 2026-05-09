from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.schemas.auth import UserLogin

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# @app.post("/register")
# def register_user(user: UserCreate, db: Session = Depends(get_db)):
#     db_user = db.query(User).filter(User.username == user.username).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Username already registered")
#
#     hashed_pw = get_password_hash(user.password)
#     new_user = User(username=user.username, hashed_password=hashed_pw, scopes=user.scopes)
#     db.add(new_user)
#     db.commit()
#     return {"msg": f"User {user.username} created with scopes {user.scopes}"}

@router.post("/token")
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_credentials.username).first()

    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    encoded_jwt = create_access_token({
        "sub": user.username,
        "scopes": user.scopes
    })

    return {"access_token": encoded_jwt, "token_type": "bearer"}
