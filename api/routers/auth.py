from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db, authenticate_user, create_access_token, admin_or_manager
import api_models.default as modef
import api_models.request as moreq
import api_models.response as mores
import internal.token_models as tokemod
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jwt.exceptions import InvalidTokenError

router = APIRouter(prefix='/v2/auth', tags=['auth'])
TOKEN_EXPIRATION_MINUTES = 30

@router.post("/logout", response_model=modef.DefaultResponse)
async def logout(current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Logout endpoint to revoke JWT token"""
  pass

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

