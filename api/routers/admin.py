from fastapi import HTTPException, APIRouter, Depends, status
import api_models.response as mores
import api_models.response as moreq
import api_models.default as modef

router = APIRouter(prefix="/v2/admin", tags=["admin"])

@router.get("/cars", response_model=mores.CarInfoListResponse)
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

@router.patch("/decommission/{id_car}", response_model=modef.DefaultResponse)
async def decommission_car(id_car: int, payload: moreq.CarDecommission,current_user: Annotated[modef.User, Depends(get_current_user)]):

  if not admin_or_manager(current_user.role):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )

  pass

@router.post("/create", response_model=modef.DefaultResponse)
async def create_car(request: moreq.CarCreate, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Create a new car (admin only)"""
  pass


@router.patch("/edit/{id_car}", response_model=modef.DefaultResponse)
async def edit_car(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Edit car information (admin only)"""
  pass


@router.delete("/delete/{id_car}", response_model=modef.DefaultResponse)
async def delete_car(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Delete a car (admin only)"""
  pass