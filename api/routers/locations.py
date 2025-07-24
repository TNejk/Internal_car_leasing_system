# from fastapi import APIRouter, Depends, HTTPException, status
# import api_models.response as mores
# import api_models.request as moreq
# import api_models.default as modef
# from typing import Annotated
# from internal.dependencies import get_current_user, connect_to_db, admin_or_manager, check_roles
# from sqlalchemy.orm import Session
# import db.models as model


# router = APIRouter(prefix='/v2/locations', tags=['location'])


# @router.get("/get", response_model=mores.LocationList)
# async def get_locations(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
#     pass


# @router.get("/create", response_model=mores.LocationList)
# async def create_locations(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
#     pass


# @router.get("/delete", response_model=mores.LocationList)
# async def delete_locations(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
#     pass


# @router.get("/edit", response_model=mores.LocationList)
# async def edit_locations(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
#     pass