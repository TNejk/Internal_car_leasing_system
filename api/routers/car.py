from fastapi import APIRouter, Depends, HTTPException, status
import api_models.response as mores
import api_models.request as moreq
import api_models.default as modef
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db, admin_or_manager, check_roles
from internal.dependencies.notifications import send_notification_to_user, notify_car_decommissioned
from sqlalchemy.orm import Session
import db.models as model
from db.enums import CarStatus, LeaseStatus, RequestStatus, TripsStatuses, TripsInviteStatus
from datetime import datetime

router = APIRouter(prefix='/v2/cars', tags=['cars'])


@router.get("/get_cars", response_model=mores.CarListResponse)
async def get_list_of_cars(current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):

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
        image_url=car.img_url,
        seats=car.seats
      )
    )

  
  return mores.CarListResponse(
    car_list=list_car
  )

@router.get("/car_info/{id_car}", response_model=mores.CarInfoResponse)
async def get_full_car_info(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
  """Get complete car information including availability"""

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
async def activate_car(id_car: int, current_user: Annotated[modef.User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
  # VCheck if car exists, check if the user is a manage admin, activate and send a notification

  if not admin_or_manager(current_user.role):
      return HTTPException(
        status_code=401,
        detail="Insufficient permissions.",       
      )

  car = db.query(model.Cars).filter(
    model.Cars.id == id_car,
    model.Cars.is_deleted == False,
    model.Cars.status == CarStatus.decommissioned
  ).first()

  if not car:
    raise HTTPException(
        status_code=404,
        detail="Auto neexistuje alebo už je aktivované.",       
      )

  car.status = CarStatus.available
  car.decommission_time = None

  db.commit()

  # Send system notification about car activation
  try:
    from internal.dependencies.notifications import notify_car_activated
    notify_car_activated(db, current_user.id, car.name)
  except Exception as e:
    print(f"WARNING: Failed to send activation notification: {e}")

  return modef.DefaultResponse(
    status=200,
    msg="Auto bolo aktivované."
  )


@router.patch("/decommision/{id_car}", response_model=modef.DefaultResponse)
async def decommision_car(
    id_car: int, 
    request: moreq.CarDecommission,
    current_user: Annotated[modef.User, Depends(get_current_user)], 
    db: Session = Depends(connect_to_db)
):

    if not admin_or_manager(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Insufficient permissions. Only managers and admins can decommission cars."
        )
    
    if id_car != request.car_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Car ID in URL does not match request body."
        )
    
    car = db.query(model.Cars).filter(
        model.Cars.id == id_car,
        model.Cars.is_deleted == False
    ).first()
    
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found or has been deleted."
        )
    
    if car.status == CarStatus.decommissioned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Car is already decommissioned."
        )
    
    if request.time_to <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decommission time must be in the future."
        )
    
    try:
        current_time = datetime.now()
        affected_user_emails = set()
        
        # 1. Update car status to decommissioned and set decommission time
        car.status = CarStatus.decommissioned
        car.decommission_time = request.time_to
        
        # 2. Find and cancel all leases that overlap with decommission period
        affected_leases = db.query(model.Leases).filter(
            model.Leases.id_car == id_car,
            model.Leases.status.in_([LeaseStatus.created, LeaseStatus.scheduled, LeaseStatus.active]),
            model.Leases.start_time >= current_time,  # Only future leases
            model.Leases.start_time < request.time_to  # That start before reactivation
        ).all()
        
        cancelled_lease_ids = []
        for lease in affected_leases:
            lease.status = LeaseStatus.canceled
            lease.canceled_time = current_time
            lease.last_changed_by = current_user.id
            lease.status_updated_at = current_time
            cancelled_lease_ids.append(lease.id)
            
            # Get user email for notification
            if lease.user and lease.user.email:
                affected_user_emails.add(lease.user.email)
        
        # 3. Cancel all trips associated with the cancelled leases
        if cancelled_lease_ids:
            affected_trips = db.query(model.Trips).filter(
                model.Trips.id_lease.in_(cancelled_lease_ids),
                model.Trips.status.in_([TripsStatuses.scheduled])
            ).all()
            
            cancelled_trip_ids = []
            for trip in affected_trips:
                trip.status = TripsStatuses.canceled
                cancelled_trip_ids.append(trip.id)
                
                # Get emails of trip participants
                participants = db.query(model.TripsParticipants).filter(
                    model.TripsParticipants.id_trip == trip.id
                ).all()
                
                for participant in participants:
                    if participant.user and participant.user.email:
                        affected_user_emails.add(participant.user.email)
            
            # 4. Cancel trip invites and join requests for affected trips
            if cancelled_trip_ids:
                # Cancel pending trip invites
                trip_invites = db.query(model.TripsInvites).filter(
                    model.TripsInvites.id_trip.in_(cancelled_trip_ids),
                    model.TripsInvites.status == TripsInviteStatus.pending
                ).all()
                
                for invite in trip_invites:
                    invite.status = TripsInviteStatus.expired
                    if invite.user and invite.user.email:
                        affected_user_emails.add(invite.user.email)
                
                # Cancel pending trip join requests
                join_requests = db.query(model.TripsJoinRequests).filter(
                    model.TripsJoinRequests.id_trip.in_(cancelled_trip_ids),
                    model.TripsJoinRequests.status == TripsInviteStatus.pending
                ).all()
                
                for join_request in join_requests:
                    join_request.status = TripsInviteStatus.expired
                    if join_request.user and join_request.user.email:
                        affected_user_emails.add(join_request.user.email)
        
        # 5. Cancel pending lease requests for this car during decommission period
        pending_requests = db.query(model.LeaseRequests).filter(
            model.LeaseRequests.id_car == id_car,
            model.LeaseRequests.status == RequestStatus.pending,
            model.LeaseRequests.start_time >= current_time,
            model.LeaseRequests.start_time < request.time_to
        ).all()
        
        for lease_request in pending_requests:
            lease_request.status = RequestStatus.canceled
            if lease_request.user and lease_request.user.email:
                affected_user_emails.add(lease_request.user.email)
        
        db.commit()
        
        for user_email in affected_user_emails:
            try:
                send_notification_to_user(
                    db=db,
                    title=f"Vaša rezervácia pre: {car.name} je zrušená",
                    message="Objednané auto bolo de-aktivované správcom.",
                    target_user_email=user_email,
                    actor_user_id=current_user.id
                )
            except Exception as e:
                print(f"WARNING: Failed to send notification to {user_email}: {e}")
        
        try:
            notify_car_decommissioned(db, current_user.id, car.name)
        except Exception as e:
            print(f"WARNING: Failed to send system notification: {e}")
        
        return modef.DefaultResponse(
            status=200,
            msg=f"Auto {car.name} bolo úspešne deaktivované do {request.time_to.strftime('%d.%m.%Y %H:%M')}."
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chyba pri deaktivácii auta: {str(e)}"
        )

