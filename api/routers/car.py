from fastapi import APIRouter, Depends, HTTPException, status
import api_models.response as mores
import api_models.request as moreq
import api_models.default as modef
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db, admin_or_manager, check_roles
from sqlalchemy.orm import Session
import db.models as model
from db.enums import CarStatus, LeaseStatus, RequestStatus

router = APIRouter(prefix='/v2/cars', tags=['cars'])

@router.get("/get_cars", response_model=mores.CarListResponse)
async def get_list_of_cars(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
  # checks if the role is correct
  check_roles(['user','manager'])

  cars = db.query(model.Cars).filter(
    model.Cars.is_deleted == False,
    model.Cars.status != CarStatus.unavailable,
  ).order_by(model.Cars.usage_metric.asc()).all()

  list_car = []
  for car in cars:
    list_car.append(
      mores.CarListContent(
        car_id=car.id,
        car_name=car.name,
        car_status=car.status,
        spz=car.plate_number,
        image_url=car.img_url
      )
    )

  return mores.CarListResponse(
    car_list=list_car
  )

@router.get("/car_info/{id_car}", response_model=mores.CarInfoResponse)
async def get_full_car_info(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
  """Get complete car information including availability"""

  check_roles(user=current_user,roles=['user','manager'])

  try:
    # Get the car by ID
    car = db.query(model.Cars).filter(
      model.Cars.id == id_car,
      model.Cars.is_deleted == False
    ).first()
    
    
    if not car:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Car not found"
      )
    
    # Get allowed hours (active leases and requests)
    allowed_hours = []
    
    active_leases = db.query(model.Leases).filter(
      model.Leases.id_car == car.id,
      model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active])
    ).all()

    for lease in active_leases:
      allowed_hours.append([lease.start_time, lease.end_time])

    # Get active private ride requests for this car
    active_requests = db.query(model.LeaseRequests).filter(
      model.LeaseRequests.id_car == car.id,
      model.LeaseRequests.status == RequestStatus.pending
    ).all()

    for request_item in active_requests:
      allowed_hours.append([request_item.start_time, request_item.end_time])

    return mores.CarInfoResponse(
      car_id=car.id,
      spz=car.plate_number,
      car_type=car.category.value,
      gearbox_type=car.gearbox_type.value,
      fuel_type=car.fuel_type.value,
      region=car.region.value,
      car_status=car.status.value,
      seats=car.seats,
      type=car.category,
      usage_metric=car.usage_metric,
      image_url=car.img_url,
      decommision_time=car.decommission_time,
      allowed_hours=allowed_hours
    )

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving car information: {str(e)}"
    )

@router.patch("/activation/{id_car}", response_model=modef.DefaultResponse)
async def activate_car(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Activate a decommissioned car (manager/admin only)"""
  pass



