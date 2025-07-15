from fastapi import APIRouter, Depends, HTTPException, status
import api_models.response as mores
import api_models.request as moreq
import api_models.default as modef
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db, admin_or_manager
from sqlalchemy.orm import Session
import db.models as model
from db.enums import CarStatus, LeaseStatus, RequestStatus

router = APIRouter(prefix='/v2/cars', tags=['cars'])

@router.get("/get_car_list", response_model=mores.CarListResponse)
async def get_car_list(current_user: Annotated[modef.User, Depends(get_current_user)],
                       db: Session = Depends(connect_to_db)): # Here we used a dependency to get the database session instead of creating a new one
  """Get list of all cars with basic information"""
  
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
        gearbox_type=car.gearbox_type,
        fuel_type=car.fuel_type,
        type=car.category,
        spz=car.plate_number,
        seats=car.seats,
        usage_metric=car.usage_metric,
        image_url=car.img_url
      )
    )

  return mores.CarListResponse(
    car_list=list_car
  )


@router.post("/decommission_car", response_model=modef.DefaultResponse)
async def decommission_car(request: moreq.CarDecommission,
                          current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Decommission a car for maintenance (manager/admin only)"""

  if admin_or_manager(current_user.role) == False:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )



  pass


@router.post("/activate_car", response_model=modef.DefaultResponse)
async def activate_car(request: moreq.CarActivation, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Activate a decommissioned car (manager/admin only)"""
  pass


@router.post("/get_full_car_info", response_model=mores.CarInfoResponse)
async def get_full_car_info(request: moreq.CarInfo, 
                           current_user: Annotated[modef.User, Depends(get_current_user)],
                           db: Session = Depends(connect_to_db)):
  """Get complete car information including availability"""
  
  try:
    # Get the car by ID
    car = db.query(model.Cars).filter(
      model.Cars.id == request.car_id,
      model.Cars.is_deleted == False
    ).first()
    
    if not car:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Car not found"
      )
    
    # Get decommission time - set to None for now since DecommissionedCars model doesn't exist
    # TODO: IMPLEMENT DECOMMISSION TIME IN THE TABLE!! ITS NEEDED FOR AUTOMATIC CAR ACTIVATION
    decommission_time = None
    
    # Get allowed hours (active leases and requests)
    allowed_hours = []
    
    # Get active leases for this car
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
      decommision_time=decommission_time,
      allowed_hours=allowed_hours
    )
    
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving car information: {str(e)}"
    )


@router.post("/get_all_car_info", response_model=list[mores.CarInfoResponse])
async def get_all_car_info(current_user: Annotated[modef.User, Depends(get_current_user)],
                           db: Session = Depends(connect_to_db)):
  """Get information about all cars (admin only)"""

  # Check if user is admin
  if admin_or_manager(current_user.role) == False:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )

  try:
    cars = db.query(model.Cars).filter(
      model.Cars.is_deleted == False
    ).all()

    if not cars:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No cars found"
      )

    car_info_list = []

    for car in cars:
      # Get decommission time - set to None for now since DecommissionedCars model doesn't exist
      # TODO: IMPLEMENT DECOMMISSION TIME IN THE TABLE!! iTS NEEDED FOR AUTOMATIC CAR ACTIVATION
      decommission_time = None

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

      for request in active_requests:
        allowed_hours.append([request.start_time, request.end_time])

      car_info_list.append(mores.CarInfoResponse(
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
        decommision_time=decommission_time,
        allowed_hours=allowed_hours
      ))

    return car_info_list

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving car information: {str(e)}"
    )




@router.post("/create_car", response_model=modef.DefaultResponse)
async def create_car(request: moreq.CarCreate, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Create a new car (admin only)"""
  pass


@router.post("/edit_car", response_model=modef.DefaultResponse)
async def edit_car(request: moreq.CarEdit, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Edit car information (admin only)"""
  pass


@router.post("/delete_car", response_model=modef.DefaultResponse)
async def delete_car(request: moreq.CarDelete, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Delete a car (admin only)"""
  pass
