from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import api_models.request as moreq
import api_models.response as mores
import api_models.default as modef
from sqlalchemy.orm import Session
from internal.dependencies import get_current_user, connect_to_db
import db.models as model
from db.enums import UserRoles

router = APIRouter(prefix="/v2/user", tags=["users"])


@router.post("/v2/edit_user", response_model=modef.DefaultResponse)
async def edit_user(request: moreq.UserEdit, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Edit user information (admin only)"""

  pass

@router.post("/v2/delete_user", response_model=modef.DefaultResponse)
async def delete_user(request: moreq.UserDelete, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Delete a user (admin only)"""
  pass

@router.get("/v2/get_users", response_model=mores.UserList)
async def get_users(current_user: Annotated[modef.User, Depends(get_current_user)],
                    db: Session = Depends(connect_to_db)):
  """Get list of all users (manager/v2/admin only)"""

  if not db:
    return HTTPException(
      status_code=500,
      detail="Error getting users!",
      headers={"WWW-Authenticate": "Bearer"}
    )

  # Get all users, that are not disabled
  users = db.query(model.Users).filter(
    model.Users.is_deleted == False,
    model.Users.role != UserRoles.admin
  ).all()

  user_list = []
  for user in users:
    user_list.append(
      modef.User(
        email=user.email,
        username=user.name,
        role=user.role,
        disabled=user.is_deleted
      )
    )

  return mores.UserList(
    users=user_list
  )

@router.post("/v2/get_all_user_info", response_model=list[mores.UserInfoResponse])
async def get_all_user_info(current_user: Annotated[modef.User, Depends(get_current_user)],
                            db: Session = Depends(connect_to_db)):
  """Get information about all users (admin only)"""

  if current_user.role != "admin":
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )

  try:
    # Get all non-deleted users except admin users
    users = db.query(model.Users).filter(
      model.Users.is_deleted == False,
      model.Users.name != 'admin'
    ).all()

    if not users:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No users found"
      )

    user_info_list = []

    for user in users:
      user_info_list.append(mores.UserInfoResponse(
        user_id=user.id,
        username=user.name,
        email=user.email,
        role=user.role.value
      ))

    return user_info_list

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving user information: {str(e)}"
    )

