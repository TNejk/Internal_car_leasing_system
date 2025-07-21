from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import api_models.response as mores
import api_models.request as moreq
import api_models.default as modef
from internal.dependencies import connect_to_db, get_current_user, admin_or_manager, calculate_usage_metric
from internal.dependencies.timedates import get_sk_date, ten_minute_tolerance
from sqlalchemy.orm import Session
import db.models as model
from db.enums import LeaseStatus, RequestStatus, CarStatus, UserRoles, Regions, TripsStatuses, TripsInviteStatus
from datetime import timedelta

router = APIRouter(prefix="/v2/lease", tags=["lease"])

@router.post("/get_leases", response_model=mores.LeaseList)
async def get_leases(request: moreq.LeaseList, current_user: Annotated[modef.User, Depends(get_current_user)],
                     db: Session = Depends(connect_to_db)):
  """Get list of leases with optional filtering, including pending private ride requests at the top"""
  try:

    # Query actual leases
    lease_query = db.query(model.Leases).join(
      model.Users, model.Leases.id_user == model.Users.id
    ).join(
      model.Cars, model.Leases.id_car == model.Cars.id
    ).filter(
      model.Users.is_deleted == False,
      model.Cars.is_deleted == False
    )

    # Query pending lease requests
    request_query = db.query(model.LeaseRequests).join(
      model.Users, model.LeaseRequests.id_user == model.Users.id
    ).join(
      model.Cars, model.LeaseRequests.id_car == model.Cars.id
    ).filter(
      model.LeaseRequests.status == RequestStatus.pending,
      model.Users.is_deleted == False,
      model.Cars.is_deleted == False
    )


    if current_user.role == "user":
      lease_query = lease_query.filter(model.Users.email == current_user.email)
      request_query = request_query.filter(model.Users.email == current_user.email)

    elif current_user.role in ["manager", "admin"]:
      if request.filter_email:
        lease_query = lease_query.filter(model.Users.email == request.filter_email)
        request_query = request_query.filter(model.Users.email == request.filter_email)
    else:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions"
      )

    if request.filter_car_id:
      lease_query = lease_query.filter(model.Leases.id_car == request.filter_car_id)
      request_query = request_query.filter(model.LeaseRequests.id_car == request.filter_car_id)

    if request.filter_time_from:
      lease_query = lease_query.filter(model.Leases.start_time >= request.filter_time_from)
      request_query = request_query.filter(model.LeaseRequests.start_time >= request.filter_time_from)

    if request.filter_time_to:
      lease_query = lease_query.filter(model.Leases.end_time <= request.filter_time_to)
      request_query = request_query.filter(model.LeaseRequests.end_time <= request.filter_time_to)


    status_filters = []
    if request.filter_active_leases:
      status_filters.extend([LeaseStatus.scheduled, LeaseStatus.active, LeaseStatus.late])
    if request.filter_inactive_leases:
      status_filters.extend([LeaseStatus.returned, LeaseStatus.canceled, LeaseStatus.missing, LeaseStatus.aborted])


    if not request.filter_active_leases and not request.filter_inactive_leases:
      #print("")
      pass
    elif status_filters:
      lease_query = lease_query.filter(model.Leases.status.in_(status_filters))

    leases = lease_query.order_by(model.Leases.start_time.desc()).all()
    pending_requests = request_query.order_by(model.LeaseRequests.start_time.desc()).all()

    lease_entries = []

    # Add pending lease requests at the top (only for managers/admins)
    if current_user.role in ["manager", "admin"]:
      for lease_request in pending_requests:
        lease_entries.append(modef.Lease(
          lease_id=lease_request.id,
          lease_status="pending_request",  # Special status to identify requests, doesnt actually exist in the db
          creation_time=None,  
          starting_time=lease_request.start_time,
          ending_time=lease_request.end_time,
          approved_return_time=None,
          missing_time=None,
          cancelled_time=None,
          aborted_time=None,
          driver_email=lease_request.user.email,
          car_name=lease_request.car.name,
          status_updated_at=None,
          last_changed_by="",
          region_tag="local"  
        ))


    for lease in leases:
      last_changed_by_name = ""
      if lease.last_changed_by:
        changed_by_user = db.query(model.Users).filter(
          model.Users.id == lease.last_changed_by
        ).first()
        if changed_by_user:
          last_changed_by_name = changed_by_user.email

      lease_entries.append(modef.Lease(
        lease_id=lease.id,
        lease_status=lease.status.value,
        creation_time=lease.create_time,
        starting_time=lease.start_time,
        ending_time=lease.end_time,
        approved_return_time=lease.return_time,
        missing_time=lease.missing_time,
        cancelled_time=lease.canceled_time,
        aborted_time=lease.aborted_time,
        driver_email=lease.user.email,
        car_name=lease.car.name,
        status_updated_at=lease.status_updated_at,
        private= lease.private,
        last_changed_by=last_changed_by_name,
        region_tag=lease.region_tag.value
      ))

    return mores.LeaseList(active_leases=lease_entries)

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving leases: {str(e)}"
    )


@router.post("/cancel", response_model=mores.LeaseCancel)
async def cancel_lease(request: Annotated[moreq.LeaseCancel, Depends()], current_user: Annotated[modef.User, Depends(get_current_user)],
                       db: Session = Depends(connect_to_db)):
  """Cancel an active lease"""
  try:

    recipient_email = request.recipient or current_user.email


    if recipient_email != current_user.email:
      if admin_or_manager(current_user.role) == False:
        raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Insufficient permissions to cancel another user's lease"
        )


    recipient_user = db.query(model.Users).filter(
      model.Users.email == recipient_email,
      model.Users.is_deleted == False
    ).first()

    if not recipient_user:
      return mores.LeaseCancel(cancelled=False)


    car = None
    if request.car_id:
      car = db.query(model.Cars).filter(
        model.Cars.id == request.car_id,
        model.Cars.is_deleted == False
      ).first()
    elif request.car_name:
      car = db.query(model.Cars).filter(
        model.Cars.name == request.car_name,
        model.Cars.is_deleted == False
      ).first()

    if not car:
      return mores.LeaseCancel(cancelled=False)

    active_lease = db.query(model.Leases).filter(
      model.Leases.id_user == recipient_user.id,
      model.Leases.id_car == car.id,
      model.Leases.id == request.lease_id,
      model.Leases.status.in_([LeaseStatus.scheduled]) # No idea what the lease statuses mean, i guess leasestatus.active means the lease began allready?
    ).order_by(model.Leases.id.desc()).first()

    if not active_lease:
      return mores.LeaseCancel(cancelled=False)


    current_user_db = db.query(model.Users).filter(
      model.Users.email == current_user.email
    ).first()


    old_status = active_lease.status
    active_lease.status = LeaseStatus.canceled
    active_lease.canceled_time = get_sk_date()
    active_lease.status_updated_at = get_sk_date()
    active_lease.last_changed_by = current_user_db.id if current_user_db else None

    # TODO: CHECK IF WE EVEN WANT TO DO THIS
    # AS THE CAR CAN BE LEASED INTO THE FUTURE AND THEN CANCELLED
    # WE SHOULD NOT CHANGE THE CAR STATUS TO AVAILABLE, as its kinda redundant
    #car.status = CarStatus.available

    change_log = model.LeaseChangeLog(
      id_lease=active_lease.id,
      changed_by=current_user_db.id if current_user_db else None,
      previous_status=old_status,
      new_status=LeaseStatus.canceled,
      note=f"Lease cancelled by {current_user.email}"
    )
    db.add(change_log)

    # Send notification if manager/admin is cancelling for someone else
    if (current_user.role in ["manager", "admin"] and
      current_user.email != recipient_email):
      # TODO: Implement notification system for FastAPI
      # This would replace the Firebase messaging from the old Flask app
      # For now, we'll just log that a notification should be sent
      print(f"NOTIFICATION: Lease cancelled by {current_user.email} for {recipient_email}, car: {car.name}")

    db.commit()

    return mores.LeaseCancel(cancelled=True)

  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error cancelling lease: {str(e)}"
    )


@router.get("/month/{month}", response_model=mores.LeaseMonthlyList)
async def get_monthly_leases(month: int,
                             current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Get leases for a specific month (manager/v2/admin only)"""
  pass


@router.post("/lease_car", response_model=mores.LeaseStart)
async def lease_car(request: moreq.LeaseCar, current_user: Annotated[modef.User, Depends(get_current_user)],
                    db: Session = Depends(connect_to_db)):
  """Create a lease for a car and optionally create a trip with participants"""
  try:
    car_id = request.car_id
    time_from = request.time_from
    time_to = request.time_to
    recipient = request.recipient or current_user.email
    private_ride = request.private_ride
    private_trip = request.private_trip
    trip_participants = request.trip_participants or []
    trip_name = request.trip_name or None

    # Is the lease, or Trip is private this won' be displayed to the user as an option to fill out. 
    # If the lease is public therefore Trip is public it MAY not be mandatory for now, but later maybe (It's an experimental feature for now)
    destination_name = request.destination_name
    longitude = request.longitude
    langitude = request.langitude


    has_privilege = admin_or_manager(current_user.role)


    if current_user.email != recipient:
      if not has_privilege:
        raise HTTPException(
          status_code=401,
          detail="Unauthorized lease.",
          headers={"WWW-Authenticate": "Bearer"}
        )


    if not time_from or not time_to:
      return modef.ErrorResponse(msg="Time from and time to are required.", status=False)

    today = get_sk_date()


    if time_to.replace(tzinfo=None) < today.replace(tzinfo=None):
      return modef.ErrorResponse(msg=f"Nemožno rezervovať do minulosti. \nDnes: {today}\nDO: {time_to}", status=False)

    if ten_minute_tolerance(str(time_from), today.replace(tzinfo=None)):
      return modef.ErrorResponse(msg=f"Nemožno rezervovať z minulosti. \nDnes: {today}\nOD: {time_from}", status=False)


    car = db.query(model.Cars).filter(
      model.Cars.id == car_id,
      model.Cars.status != CarStatus.decommissioned,
      model.Cars.is_deleted == False
    ).first()

    if not car:
      return modef.ErrorResponse(msg="Auto nie je dostupné alebo neexistuje.", status=False)

    # ~ character means NOT, so here it makes sure the (query) doesnt return true, which would overlapp a lease
    conflicting_lease = db.query(model.Leases).filter(
      model.Leases.id_car == car_id,
      model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active]),
      ~((model.Leases.end_time <= time_from) | (model.Leases.start_time >= time_to))
    ).first()

    if conflicting_lease:
      return modef.ErrorResponse(msg="Zabratý dátum (hodina typujem)", status=False)


    recipient_user = db.query(model.Users).filter(
      model.Users.email == recipient,
      model.Users.is_deleted == False
    ).first()

    if not recipient_user:
      return modef.ErrorResponse(msg="Príjemca neexistuje.", status=False)

    # If private ride and user is not manager/admin, create a request instead
    if private_ride and not has_privilege:
      # Create lease request for approval
      lease_request = model.LeaseRequests(
        id_car=car_id,
        id_user=recipient_user.id,
        start_time=time_from,
        end_time=time_to,
        status=RequestStatus.pending
      )
      db.add(lease_request)
      db.commit()

      # TODO: Send notification to managers

      return mores.LeaseStart(status=True, private=True, msg="Request for a private ride was sent!")


    new_lease = model.Leases(
      id_car=car_id,
      id_user=recipient_user.id,
      start_time=time_from,
      end_time=time_to,
      status=LeaseStatus.scheduled,
      private=private_ride,
      region_tag=Regions.local  # Default to local
    )

    db.add(new_lease)
    db.flush()  # Get the lease ID, without commiting the transaction, the changes are stashed on the db untill we commit(), which means we can still rollback

    # Once again i have no fucking idea how car statuses work, shouldnt the car be away only when such a lease begins??? Like wtff
    # I thingk its better to have a check in the notificator to change a cars status if it detects a lease for that car has started.
    #car.status = CarStatus.away

    # Also set destination name, and somehow longitude and langitude?
    # That would be annoying for the user, but would look cool in the app as the manager could see the google maps trail to where he is going.
    # If its a private trip a destination name is not needed neither is the longitude and langitude, if its a public trip everyone can see where you are going and can join

    if trip_name is None:
      trip_name = f"Trip for {car.name} - {recipient}"
    
    new_trip = model.Trips(
      trip_name=trip_name,
      id_lease=new_lease.id,
      id_car=car_id,
      creator=recipient_user.id,
      is_public=not private_trip,
      status=TripsStatuses.scheduled,
      free_seats=car.seats - 1,  # -1 for the driver
      destination_name= destination_name,
      destination_lat= langitude,
      destination_lon= longitude
    )

    db.add(new_trip)
    db.flush()  # Get the trip ID

    # Add creator as participant
    trip_participant = model.TripsParticipants(
      id_trip=new_trip.id,
      id_user=recipient_user.id,
      seat_number=1,  # Driver seat
      trip_finished=False
    )
    db.add(trip_participant)


    if trip_participants:
      for participant_email in trip_participants:
        participant_user = db.query(model.Users).filter(
          model.Users.email == participant_email,
          model.Users.is_deleted == False
        ).first()

        if participant_user and participant_user.id != recipient_user.id:
          trip_invite = model.TripsInvites(
            id_trip=new_trip.id,
            id_user=participant_user.id,
            status=TripsInviteStatus.pending
          )
          db.add(trip_invite)
          new_trip.free_seats -= 1  # Reserve seat for invited participant

    db.commit()

    # TODO: Send notifications

    return mores.LeaseStart(status=True, private=private_ride, msg="Lease created successfully!")

  except Exception as e:
    db.rollback()
    return modef.ErrorResponse(msg=f"Error creating lease: {str(e)}", status=False)


@router.get("/private_requests", response_model=mores.LeaseRequestList)
async def get_requests(current_user: Annotated[modef.User, Depends(get_current_user)],
                       db: Session = Depends(connect_to_db)):
  """Get pending private ride requests (manager/admin only)"""
  try:
    if not admin_or_manager(current_user.role):
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorized.",
        headers={"WWW-Authenticate": "Bearer"}
      )

    # Query lease requests with car and user information
    requests = db.query(model.LeaseRequests).join(
      model.Cars, model.LeaseRequests.id_car == model.Cars.id
    ).join(
      model.Users, model.LeaseRequests.id_user == model.Users.id
    ).filter(
      model.LeaseRequests.status.in_([RequestStatus.pending]),
      model.Cars.is_deleted == False,
      model.Users.is_deleted == False
    ).order_by(model.LeaseRequests.start_time.asc()).all()

    request_entries = []
    for req in requests:
      request_entries.append(mores.LeaseRequest(
        request_id=req.id,
        starting_time=req.start_time,
        ending_time=req.end_time,
        request_status=req.status.value,
        car_name=req.car.name,
        spz=req.car.plate_number,
        driver_email=req.user.email,
        image_url=req.car.img_url
      ))

    return mores.LeaseRequestList(active_requests=request_entries)

  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving lease requests: {str(e)}"
    )


@router.post("/approve", response_model=modef.DefaultResponse)
async def approve_request(request: moreq.LeasePrivateApprove,
                          current_user: Annotated[modef.User, Depends(get_current_user)],
                          db: Session = Depends(connect_to_db)):
  """Approve or reject a private ride request (manager/admin only)"""
  try:
    # Check if user has manager/admin privileges
    if not admin_or_manager(current_user.role):
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorized.",
        headers={"WWW-Authenticate": "Bearer"}
      )

    lease_request = db.query(model.LeaseRequests).filter(
      model.LeaseRequests.id == request.request_id,
      model.LeaseRequests.status == RequestStatus.pending
    ).first()

    if not lease_request:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Lease request not found or already processed"
      )

    car = db.query(model.Cars).filter(
      model.Cars.id == request.car_id,
      model.Cars.is_deleted == False
    ).first()

    if not car:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Car not found"
      )

    user = db.query(model.Users).filter(
      model.Users.email == request.requester,
      model.Users.is_deleted == False
    ).first()

    if not user:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Requester not found"
      )

    current_user_db = db.query(model.Users).filter(
      model.Users.email == current_user.email
    ).first()

    if request.approval:
      time_from = request.time_from or lease_request.start_time
      time_to = request.time_to or lease_request.end_time

      conflicting_lease = db.query(model.Leases).filter(
        model.Leases.id_car == car.id,
        model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active]),
        ~((model.Leases.end_time <= time_from) | (model.Leases.start_time >= time_to))
      ).first()

      if conflicting_lease:
        raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Time slot conflicts with existing lease"
        )

      new_lease = model.Leases(
        id_car=car.id,
        id_user=user.id,
        start_time=time_from,
        end_time=time_to,
        status=LeaseStatus.scheduled,
        private=True,  # Private lease request
        region_tag=Regions.local,  # Default to local
        last_changed_by=current_user_db.id if current_user_db else None
      )

      db.add(new_lease)
      db.flush()  # Get the lease ID

      trip_name = f"Private trip for {car.name} - {user.email}"
      
      new_trip = model.Trips(
        trip_name=trip_name,
        id_lease=new_lease.id,
        id_car=car.id,
        creator=user.id,
        is_public=False,  # Private trip
        status=TripsStatuses.scheduled,
        free_seats=car.seats - 1,  # -1 for the driver
        destination_name="Private destination",  # Default for private trips
        destination_lat=0.0,  # Default coordinates
        destination_lon=0.0
      )

      db.add(new_trip)
      db.flush()

      trip_participant = model.TripsParticipants(
        id_trip=new_trip.id,
        id_user=user.id,
        seat_number=1,  # Driver seat
        trip_finished=False
      )
      db.add(trip_participant)

      lease_request.status = RequestStatus.approved

      db.commit()

      # TODO: Send notification to user about approval
      print(f"NOTIFICATION: Private lease request approved by {current_user.email} for {user.email}, car: {car.name}")

      return modef.DefaultResponse(status=True, msg="Private lease request approved successfully!")

    else:
      lease_request.status = RequestStatus.rejected
      db.commit()

      # TODO: Send notification to user about rejection
      print(f"NOTIFICATION: Private lease request rejected by {current_user.email} for {user.email}, car: {car.name}")

      return modef.DefaultResponse(status=True, msg="Private lease request rejected.")

  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error processing lease request: {str(e)}"
    )


# TODO: Implement a request to the manager to see if the car was actually properly returned to the company!!!
# Maybe use the leaseRequest or maybe a notífication? idk for now

@router.post("/return", response_model=modef.DefaultResponse)
async def return_car(request: moreq.LeaseFinish, 
                     current_user: Annotated[modef.User, Depends(get_current_user)],
                     db: Session = Depends(connect_to_db)):
  """Return a leased car"""
  try:
    lease = db.query(model.Leases).filter(
      model.Leases.id == request.lease_id
    ).first()
    
    if not lease:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Lease not found"
      )
    
    user = db.query(model.Users).filter(
      model.Users.email == current_user.email,
      model.Users.is_deleted == False
    ).first()
    
    if not user:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
      )
    
    is_manager_or_admin = admin_or_manager(current_user.role)
    
    if lease.id_user != user.id and not is_manager_or_admin:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorized to return this lease"
      )
    
    if lease.status == LeaseStatus.returned:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Lease already returned"
      )
    
    car = db.query(model.Cars).filter(
      model.Cars.id == lease.id_car
    ).first()
    
    if not car:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Car not found"
      )
    
    current_time = get_sk_date()
    return_time = request.time_of_return or current_time
    
    region_mapping = {
      "Bratislava": Regions.local,
      "Banská Bystrica": Regions.local,
      "Kosice": Regions.local,
      "Private": Regions._global,
    }
    return_region = region_mapping.get(request.return_location, Regions.local)
    
    old_status = lease.status
    lease.status = LeaseStatus.returned
    lease.return_time = return_time
    lease.note = None
    lease.is_damaged = request.damaged
    lease.dirty = request.dirty_car
    lease.exterior_damage = request.exterior_damage
    lease.interior_damage = request.interior_damage
    lease.collision = request.collision
    lease.status_updated_at = current_time
    lease.last_changed_by = user.id
    
    car.status = CarStatus.available
    car.region = return_region
    
    usage_metric = calculate_usage_metric(car.id, db)
    car.usage_metric = usage_metric
    
    change_log = model.LeaseChangeLog(
      id_lease=lease.id,
      changed_by=user.id,
      previous_status=old_status,
      new_status=LeaseStatus.returned,
      note=f"Car returned by {current_user.email}"
    )
    db.add(change_log)
    
    trip = db.query(model.Trips).filter(
      model.Trips.id_lease == lease.id
    ).first()
    
    if trip:
      trip.status = TripsStatuses.ended
    
    db.commit()
    
    if request.damaged:
      print(f"NOTIFICATION: Car {car.name} returned with damage by {current_user.email}")
    
    return modef.DefaultResponse(status=True, msg="Car returned successfully")
    
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error returning car: {str(e)}"
    )


