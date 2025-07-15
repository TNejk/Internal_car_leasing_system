from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import api_models.response as mores
import api_models.request as moreq
import api_models.default as modef
from internal.dependencies import connect_to_db, get_current_user, admin_or_manager
from internal.dependencies.timedates import get_sk_date, ten_minute_tolerance
from sqlalchemy.orm import Session
import db.models as model
from db.enums import LeaseStatus, RequestStatus, CarStatus, UserRoles, Regions, TripsStatuses, TripsInviteStatus

router = APIRouter(prefix="/v2/lease", tags=["lease"])

@router.post("/v2/get_leases", response_model=mores.LeaseList)
async def get_leases(request: moreq.LeaseList, current_user: Annotated[modef.User, Depends(get_current_user)],
                     db: Session = Depends(connect_to_db)):
  """Get list of leases with optional filtering"""
  try:
    # Build base query with joins
    query = db.query(model.Leases).join(
      model.Users, model.Leases.id_user == model.Users.id
    ).join(
      model.Cars, model.Leases.id_car == model.Cars.id
    ).filter(
      model.Users.is_deleted == False,
      model.Cars.is_deleted == False
    )

    # Role-based filtering
    if current_user.role == model.UserRoles.user:
      # Users can only see their own leases
      query = query.filter(model.Users.email == current_user.email)
    elif current_user.role in [model.UserRoles.manager, model.UserRoles.admin]:
      # Managers and admins can filter by email if provided
      if request.filter_email:
        query = query.filter(model.Users.email == request.filter_email)
    else:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions"
      )

    # Apply optional filters
    if request.filter_car_id:
      query = query.filter(model.Leases.id_car == request.filter_car_id)

    if request.filter_time_from:
      query = query.filter(model.Leases.start_time >= request.filter_time_from)

    if request.filter_time_to:
      query = query.filter(model.Leases.end_time <= request.filter_time_to)

    # Status filtering - map boolean filters to enum values
    status_filters = []
    if request.filter_active_leases:
      # Active leases include: scheduled, active, late
      status_filters.extend([LeaseStatus.scheduled, LeaseStatus.active, LeaseStatus.late])
    if request.filter_incactive_leases:
      # Inactive leases include: returned, canceled, missing, aborted
      status_filters.extend([LeaseStatus.returned, LeaseStatus.canceled, LeaseStatus.missing, LeaseStatus.aborted])

    # If neither filter is specified, show all lease statuses
    if not request.filter_active_leases and not request.filter_incactive_leases:
      # Show all statuses
      pass
    elif status_filters:
      query = query.filter(model.Leases.status.in_(status_filters))

    # Execute query with ordering
    leases = query.order_by(model.Leases.start_time.desc()).all()

    # Build response
    lease_entries = []
    for lease in leases:
      # Get last changed by user info
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


@router.post("/v2/cancel_lease", response_model=mores.LeaseCancel)
async def cancel_lease(request: moreq.LeaseCancel, current_user: Annotated[modef.User, Depends(get_current_user)],
                       db: Session = Depends(connect_to_db)):
  """Cancel an active lease"""
  try:
    # Determine whose lease to cancel
    recipient_email = request.recipient or current_user.email

    # Permission check: only managers and admins can cancel other people's leases
    if recipient_email != current_user.email:
      if admin_or_manager(current_user.role) == False:
        raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Insufficient permissions to cancel another user's lease"
        )

    # Find the recipient user
    recipient_user = db.query(model.Users).filter(
      model.Users.email == recipient_email,
      model.Users.is_deleted == False
    ).first()

    if not recipient_user:
      return mores.LeaseCancel(cancelled=False)

    # Find the car - use either car_id or car_name
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
      model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active])
    ).order_by(model.Leases.id.desc()).first()

    if not active_lease:
      return mores.LeaseCancel(cancelled=False)

    # Get current user for tracking changes
    current_user_db = db.query(model.Users).filter(
      model.Users.email == current_user.email
    ).first()

    # Cancel the lease
    old_status = active_lease.status
    active_lease.status = LeaseStatus.canceled
    active_lease.canceled_time = get_sk_date()
    active_lease.status_updated_at = get_sk_date()
    active_lease.last_changed_by = current_user_db.id if current_user_db else None

    # TODO: CHECK IF WE EVEN WANT TO DO THIS
    # AS THE CAR CAN BE LEASED INTO THE FUTURE AND THEN CANCELLED
    # WE SHOULD NOT CHANGE THE CAR STATUS TO AVAILABLE, as its kinda redundant
    #car.status = CarStatus.available

    # Create change log entry
    change_log = model.LeaseChangeLog(
      id_lease=active_lease.id,
      changed_by=current_user_db.id if current_user_db else None,
      previous_status=old_status,
      new_status=LeaseStatus.canceled,
      note=f"Lease cancelled by {current_user.email}"
    )
    db.add(change_log)

    # Send notification if manager/admin is cancelling for someone else
    if (current_user.role in [model.UserRoles.manager, model.UserRoles.admin] and
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


@router.post("/v2/get_monthly_leases", response_model=list[mores.LeaseMonthly])
async def get_monthly_leases(request: moreq.LeaseMonthly,
                             current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Get leases for a specific month (manager/v2/admin only)"""
  pass


@router.post("/v2/lease_car", response_model=mores.LeaseStart)
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

    # Check privilege
    has_privilege = admin_or_manager(current_user.role)

    # Check if leasing for someone else
    if current_user.email != recipient:
      if not has_privilege:
        raise HTTPException(
          status_code=401,
          detail="Unauthorized lease.",
          headers={"WWW-Authenticate": "Bearer"}
        )

    # Date validation
    if not time_from or not time_to:
      return modef.ErrorResponse(msg="Time from and time to are required.", status=False)

    today = get_sk_date()

    # Convert datetime to timezone-aware if needed
    if time_to.replace(tzinfo=None) < today.replace(tzinfo=None):
      return modef.ErrorResponse(msg=f"Nemožno rezervovať do minulosti. \nDnes: {today}\nDO: {time_to}", status=False)

    if ten_minute_tolerance(str(time_from), today.replace(tzinfo=None)):
      return modef.ErrorResponse(msg=f"Nemožno rezervovať z minulosti. \nDnes: {today}\nOD: {time_from}", status=False)

    # Get car and validate availability
    car = db.query(model.Cars).filter(
      model.Cars.id == car_id,
      model.Cars.status != CarStatus.decommissioned,
      model.Cars.is_deleted == False
    ).first()

    if not car:
      return modef.ErrorResponse(msg="Auto nie je dostupné alebo neexistuje.", status=False)

    # Check for conflicting leases
    conflicting_lease = db.query(model.Leases).filter(
      model.Leases.id_car == car_id,
      model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active]),
      ~((model.Leases.end_time <= time_from) | (model.Leases.start_time >= time_to))
    ).first()

    if conflicting_lease:
      return modef.ErrorResponse(msg="Zabratý dátum (hodina typujem)", status=False)

    # Get recipient user
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

    # Create the lease
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

    # Update car status
    car.status = CarStatus.away

    # Create trip for the lease
    trip_name = f"Trip for {car.name} - {recipient}"
    new_trip = model.Trips(
      trip_name=trip_name,
      id_lease=new_lease.id,
      id_car=car_id,
      creator=recipient_user.id,
      is_public=not private_trip,
      status=TripsStatuses.scheduled,
      free_seats=car.seats - 1,  # -1 for the driver
      destination_name="Not specified",
      destination_lat=0.0,
      destination_lon=0.0
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

    # Send invites to trip participants if provided
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

# !
# TODO: Here you need to get email and car name from id's, ALSO remake the sql table for Lease requests to add a foreign key to the lease table to get the IMG URL AND SUCH
@router.post("/v2/get_requests", response_model=mores.LeaseRequestList)
async def get_requests(current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Get pending private ride requests (manager/v2/admin only)"""
  # work with LeaseRequests object

  if not admin_or_manager(current_user.role):
    return HTTPException(
      status_code=401,
      detail="Unauthorized.",
      headers={"WWW-Authenticate": "Bearer"}
    )

  session = connect_to_db()

  requests = session.query(model.LeaseRequests).filter(
    model.LeaseRequests.status != RequestStatus.canceled,
    model.LeaseRequests.status != RequestStatus.rejected
  ).all()

  list_request = []

  # for req in requests:
  #     list_request.append(
  #         requestEntry(
  #             request_id= req.id,
  #             request_status= req.status,
  #             car_id=
  #             driver_id=
  #             image_url= req.img_url

  #             spz=
  #             starting_time=
  #             ending_time=

  #         )
  #     )


@router.post("/v2/approve_req", response_model=modef.DefaultResponse)
async def approve_request(request: moreq.LeasePrivateApprove,
                          current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Approve or reject a private ride request (manager/v2/admin only)"""
  pass


@router.post("/v2/return_car", response_model=modef.DefaultResponse)
async def return_car(request: moreq.LeaseFinish, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Return a leased car"""
  pass

