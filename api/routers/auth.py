from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db, authenticate_user, create_access_token, admin_or_manager
import api_models.default as modef
import api_models.request as moreq
import api_models.response as mores
import internal.token_models as tokemod
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jwt.exceptions import InvalidTokenError
import jwt
import os
import db.models as model

router = APIRouter(prefix='/v2/auth', tags=['auth'])
TOKEN_EXPIRATION_MINUTES = 30

@router.post("/logout", response_model=modef.DefaultResponse)
async def logout(
    current_user: Annotated[modef.User, Depends(get_current_user)],
    token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="token"))],
    db: Session = Depends(connect_to_db)
):
    """Logout endpoint to revoke JWT token"""
    try:
        # Decode the token to get the jti (if it exists) or use the whole token
        SECRET_KEY = os.environ.get('APP_SECRET_KEY')
        ALGORITHM = "HS256"
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_to_revoke = payload.get("jti", token)  # Use jti if available, otherwise use the token itself
        except jwt.InvalidTokenError:
            # If we can't decode, just use the token as is
            token_to_revoke = token
        
        # Add token to revoked list
        revoked_token = model.RevokedJWT(
            token=token_to_revoke,
            added_at=datetime.now()
        )
        
        db.add(revoked_token)
        db.commit()
        
        return modef.DefaultResponse(
            status=True,
            msg="JWT revoked successfully"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error revoking JWT: {str(e)}"
        )

@router.post("/login", response_model=mores.LoginResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(connect_to_db)):
  """ Login user to app, returns a login_response obj that includes a token and role email combo. """
  user = authenticate_user(
    email=form_data.username,
    password=form_data.password,
    db=db
  )

  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Zlé meno alebo heslo!",
      headers={"WWW-Authenticate": "Bearer"}
    )

  access_token = create_access_token(
    data={'email': user.email, 'name': user.name, "role": user.role},
    expires_delta=timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
  )

  return mores.LoginResponse(
    token=access_token,
  )

