from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import api_models.request as moreq
import api_models.response as mores
import api_models.default as modef
from sqlalchemy.orm import Session
from internal.dependencies import get_current_user, connect_to_db, admin_or_manager
import db.models as model
from db.enums import UserRoles

router = APIRouter(prefix="/v2/user", tags=["users"])




@router.get("/get_users", response_model=mores.UserList)
async def get_users(current_user: Annotated[modef.User, Depends(get_current_user)],
                    db: Session = Depends(connect_to_db)):
  """Get list of all users (manager/admin only)"""

  # Check if user has manager or admin role
  if not admin_or_manager(current_user.role):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Manager or admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )

  try:
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

  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving users: {str(e)}"
    )

