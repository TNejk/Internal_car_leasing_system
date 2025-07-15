from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import api_models.request as moreq
import api_models.response as mores
import api_models.default as modef
from internal.dependencies import get_current_user, connect_to_db, admin_or_manager
from internal.dependencies.report import find_reports_directory, get_reports_paths
from typing import Annotated
from sqlalchemy.orm import Session
import db.models as model
from db.enums import UserRoles
import os

router = APIRouter(prefix="/v2/report", tags=["report"])


@router.post("/list_reports", response_model=mores.ReportList)
async def list_reports(current_user: Annotated[modef.User, Depends(get_current_user)],
                       db: Session = Depends(connect_to_db)):
  """List available reports (manager/admin only)"""

  if not admin_or_manager(current_user.role):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access",
      headers={"WWW-Authenticate": "Bearer"}
    )

  db_user = db.query(model.Users).filter(
    model.Users.email == current_user.email,
    model.Users.role.in_([UserRoles.manager, UserRoles.admin]),
    model.Users.is_deleted == False
  ).first()

  if not db_user:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="User verification failed"
    )

  try:
    reports_dir = find_reports_directory()
    if not reports_dir:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Reports directory not found"
      )

    report_paths = get_reports_paths(reports_dir)
    if report_paths is None:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error accessing reports directory"
      )

    return mores.ReportList(reports=report_paths)

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error listing reports: {str(e)}"
    )


@router.get("/get_report/v2/{filename}")
async def get_report(filename: str, current_user: Annotated[modef.User, Depends(get_current_user)],
                     db: Session = Depends(connect_to_db)):
  """Download a specific report file (manager/admin only)"""

  if not admin_or_manager(current_user.role):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access",
      headers={"WWW-Authenticate": "Bearer"}
    )

  db_user = db.query(model.Users).filter(
    model.Users.email == current_user.email,
    model.Users.role.in_([UserRoles.manager, UserRoles.admin]),
    model.Users.is_deleted == False
  ).first()

  if not db_user:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Invalid authorization"
    )

  try:
    reports_dir = find_reports_directory()
    if not reports_dir:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Reports directory not found"
      )

    safe_path = os.path.join(reports_dir, filename)

    # Security check to prevent path traversal attacks
    if not os.path.realpath(safe_path).startswith(os.path.realpath(reports_dir)):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid file path"
      )

    if not os.path.isfile(safe_path):
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found"
      )

    return FileResponse(
      path=safe_path,
      filename=filename,
      media_type='application/octet-stream'
    )

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error accessing file: {str(e)}"
    )