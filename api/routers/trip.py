from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
import api_models.request as moreq
import api_models.response as mores
import api_models.default as modef
from sqlalchemy.orm import Session
from internal.dependencies import get_current_user, connect_to_db
import db.models as model
from db.enums import TripsStatuses, TripsInviteStatus

router = APIRouter(prefix="/v2/trip", tags=["trip"])


@router.post("/join/request", response_model=modef.DefaultResponse)
async def request_trip_join(request: moreq.TripJoinRequest,
                            current_user: Annotated[modef.User, Depends(get_current_user)],
                            db: Session = Depends(connect_to_db)):
  """Request to join a public trip"""
  try:
    trip = db.query(model.Trips).filter(
      model.Trips.id == request.trip_id,
      model.Trips.is_public == True,
      model.Trips.status == TripsStatuses.scheduled
    ).first()

    if not trip:
      return modef.DefaultResponse(status=False, msg="Trip not found or not available for joining")

    if trip.free_seats <= 0:
      return modef.DefaultResponse(status=False, msg="No free seats available")

    user = db.query(model.Users).filter(
      model.Users.email == current_user.email,
      model.Users.is_deleted == False
    ).first()

    if not user:
      return modef.DefaultResponse(status=False, msg="User not found")

    # Check if user already has a request or is already a participant
    existing_request = db.query(model.TripsJoinRequests).filter(
      model.TripsJoinRequests.id_trip == request.trip_id,
      model.TripsJoinRequests.id_user == user.id,
      model.TripsJoinRequests.status == TripsInviteStatus.pending
    ).first()

    if existing_request:
      return modef.DefaultResponse(status=False, msg="You already have a pending request for this trip")

    existing_participant = db.query(model.TripsParticipants).filter(
      model.TripsParticipants.id_trip == request.trip_id,
      model.TripsParticipants.id_user == user.id
    ).first()

    if existing_participant:
      return modef.DefaultResponse(status=False, msg="You are already a participant in this trip")

    # Create join request
    join_request = model.TripsJoinRequests(
      id_trip=request.trip_id,
      id_user=user.id,
      status=TripsInviteStatus.pending
    )

    db.add(join_request)
    db.commit()

    return modef.DefaultResponse(status=True, msg="Join request sent successfully")

  except Exception as e:
    db.rollback()
    return modef.DefaultResponse(status=False, msg=f"Error sending join request: {str(e)}")


@router.post("/invite/response", response_model=modef.DefaultResponse)
async def respond_trip_invite(request: moreq.TripInviteResponse,
                              current_user: Annotated[modef.User, Depends(get_current_user)],
                              db: Session = Depends(connect_to_db)):
  """Accept or reject a trip invite"""
  try:
    user = db.query(model.Users).filter(
      model.Users.email == current_user.email,
      model.Users.is_deleted == False
    ).first()

    if not user:
      return modef.DefaultResponse(status=False, msg="User not found")

    invite = db.query(model.TripsInvites).filter(
      model.TripsInvites.id == request.invite_id,
      model.TripsInvites.id_user == user.id,
      model.TripsInvites.status == TripsInviteStatus.pending
    ).first()

    if not invite:
      return modef.DefaultResponse(status=False, msg="Invite not found or already responded")

    trip = db.query(model.Trips).filter(model.Trips.id == invite.id_trip).first()

    if request.accepted:
      if trip.free_seats <= 0:
        return modef.DefaultResponse(status=False, msg="No free seats available")

      # Accept invite - add as participant
      invite.status = TripsInviteStatus.accepted

      # Find next available seat number
      existing_participants = db.query(model.TripsParticipants).filter(
        model.TripsParticipants.id_trip == invite.id_trip
      ).all()

      used_seats = [p.seat_number for p in existing_participants]
      seat_number = 2  # Start from 2 (driver is seat 1)
      while seat_number in used_seats:
        seat_number += 1

      participant = model.TripsParticipants(
        id_trip=invite.id_trip,
        id_user=user.id,
        seat_number=seat_number,
        trip_finished=False
      )

      db.add(participant)
      trip.free_seats -= 1

    else:
      # Reject invite
      invite.status = TripsInviteStatus.rejected
      trip.free_seats += 1

    db.commit()

    status_msg = "Invite accepted" if request.accepted else "Invite rejected"
    return modef.DefaultResponse(status=True, msg=status_msg)

  except Exception as e:
    db.rollback()
    return modef.DefaultResponse(status=False, msg=f"Error responding to invite: {str(e)}")


@router.get("/get_trips", response_model=mores.TripList)
async def get_trips(current_user: Annotated[modef.User, Depends(get_current_user)],
                    db: Session = Depends(connect_to_db)):
  """Get list of available trips"""
  try:
    # Get the full user from database (current_user from JWT doesn't have id)
    user = db.query(model.Users).filter(
      model.Users.email == current_user.email,
      model.Users.is_deleted == False
    ).first()
    
    if not user:
      return mores.TripList(trips=[])
    
    # Get public trips and trips created by the user
    trips = db.query(model.Trips).filter(
      (model.Trips.is_public == True) | (model.Trips.creator == user.id),
      model.Trips.status == TripsStatuses.scheduled
    ).all()

    trip_list = []
    for trip in trips:
      creator = db.query(model.Users).filter(model.Users.id == trip.creator).first()
      car = db.query(model.Cars).filter(model.Cars.id == trip.id_car).first()

      trip_list.append(modef.Trip(
        trip_id=trip.id,
        trip_name=trip.trip_name,
        creator_email=creator.email,
        car_name=car.name,
        is_public=trip.is_public,
        status=trip.status.value,
        free_seats=trip.free_seats,
        total_seats=car.seats,
        destination_name=trip.destination_name,
        destination_lat=float(trip.destination_lat),
        destination_lon=float(trip.destination_lon),
        created_at=trip.created_at
      ))

    return mores.TripList(trips=trip_list)

  except Exception as e:
    return mores.TripList(trips=[])


@router.get("/participants/lease/{lease_id}", response_model=mores.TripParticipantsResponse)
async def get_trip_participants_by_lease(
    lease_id: int,
    current_user: Annotated[modef.User, Depends(get_current_user)],
    db: Session = Depends(connect_to_db)
):
    """
    Get trip participants for a lease.
    Access is allowed if:
    - Trip is public, OR
    - User is the trip creator, OR 
    - User is already a participant in the trip
    """
    try:
        # Get the current user from database
        user = db.query(model.Users).filter(
            model.Users.email == current_user.email,
            model.Users.is_deleted == False
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Find the trip associated with this lease
        trip = db.query(model.Trips).filter(
            model.Trips.id_lease == lease_id
        ).first()
        
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No trip found for this lease"
            )
        
        has_access = False
        
        if trip.is_public:
            has_access = True
        
        if trip.creator == user.id:
            has_access = True
        
        if not has_access:
            participant = db.query(model.TripsParticipants).filter(
                model.TripsParticipants.id_trip == trip.id,
                model.TripsParticipants.id_user == user.id
            ).first()
            
            if participant:
                has_access = True
        
        if user.role in ["manager", "admin"]:
           has_access = True

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view participants of public trips or trips you created/participate in."
            )
        
        participants_query = db.query(model.TripsParticipants).filter(
            model.TripsParticipants.id_trip == trip.id
        ).all()
        

        participants_list = []
        for participant in participants_query:
            participant_user = db.query(model.Users).filter(
                model.Users.id == participant.id_user,
                model.Users.is_deleted == False
            ).first()
            
            if participant_user:
                participants_list.append(mores.TripParticipant(
                    user_id=participant_user.id,
                    user_email=participant_user.email,
                    user_name=participant_user.name,
                    seat_number=participant.seat_number,
                    trip_finished=participant.trip_finished
                ))
        
        return mores.TripParticipantsResponse(
            trip_id=trip.id,
            trip_name=trip.trip_name,
            is_public=trip.is_public,
            participants=participants_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trip participants: {str(e)}"
        )


@router.get("/join/requests", response_model=mores.TripJoinRequestListResponse)
async def get_trip_join_requests(current_user: Annotated[modef.User, Depends(get_current_user)],
                                 db: Session = Depends(connect_to_db)):
    """Get trip join requests for trips created by the current user (or all if admin)"""
    try:
        user = db.query(model.Users).filter(
            model.Users.email == current_user.email,
            model.Users.is_deleted == False
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # If admin, get all join requests; otherwise only for trips created by the user
        if user.role in ["admin", "manager"]:
            join_requests = db.query(model.TripsJoinRequests).all()
        else:
            # Get join requests only for trips created by this user
            join_requests = db.query(model.TripsJoinRequests).join(
                model.Trips, model.TripsJoinRequests.id_trip == model.Trips.id
            ).filter(
                model.Trips.creator == user.id
            ).all()

        requests_list = []
        for request in join_requests:
            # Get user details
            request_user = db.query(model.Users).filter(
                model.Users.id == request.id_user,
                model.Users.is_deleted == False
            ).first()
            
            # Get trip details for context
            trip = db.query(model.Trips).filter(model.Trips.id == request.id_trip).first()
            
            if request_user and trip:
                requests_list.append(mores.TripJoinRequestInfo(
                    request_id=request.id,
                    trip_id=request.id_trip,
                    user_email=request_user.email,
                    status=request.status.value,
                    requested_at=trip.created_at  # Using trip creation as approximation since no timestamp in join requests
                ))

        return mores.TripJoinRequestListResponse(join_requests=requests_list)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving join requests: {str(e)}"
        )


@router.post("/join/approve", response_model=modef.DefaultResponse)
async def approve_trip_join_request(request: moreq.TripJoinResponse,
                                    current_user: Annotated[modef.User, Depends(get_current_user)],
                                    db: Session = Depends(connect_to_db)):
    """Approve or reject a trip join request"""
    try:
        user = db.query(model.Users).filter(
            model.Users.email == current_user.email,
            model.Users.is_deleted == False
        ).first()

        if not user:
            return modef.DefaultResponse(status=False, msg="User not found")

        join_request = db.query(model.TripsJoinRequests).filter(
            model.TripsJoinRequests.id == request.request_id,
            model.TripsJoinRequests.status == TripsInviteStatus.pending
        ).first()

        if not join_request:
            return modef.DefaultResponse(status=False, msg="Join request not found or already processed")

        trip = db.query(model.Trips).filter(model.Trips.id == join_request.id_trip).first()

        if not trip:
            return modef.DefaultResponse(status=False, msg="Trip not found")

        # Check if user has permission to approve (trip creator or admin)
        if trip.creator != user.id and user.role not in ["admin", "manager"]:
            return modef.DefaultResponse(status=False, msg="You don't have permission to approve this request")

        if request.approved:
            if trip.free_seats <= 0:
                return modef.DefaultResponse(status=False, msg="No free seats available")

            # Approve request - add as participant
            join_request.status = TripsInviteStatus.accepted

            # Find next available seat number
            existing_participants = db.query(model.TripsParticipants).filter(
                model.TripsParticipants.id_trip == join_request.id_trip
            ).all()

            used_seats = [p.seat_number for p in existing_participants]
            seat_number = 2  # Start from 2 (driver is seat 1)
            while seat_number in used_seats:
                seat_number += 1

            participant = model.TripsParticipants(
                id_trip=join_request.id_trip,
                id_user=join_request.id_user,
                seat_number=seat_number,
                trip_finished=False
            )

            db.add(participant)
            trip.free_seats -= 1

        else:
            # Reject request
            join_request.status = TripsInviteStatus.rejected

        db.commit()

        status_msg = "Join request approved" if request.approved else "Join request rejected"
        return modef.DefaultResponse(status=True, msg=status_msg)

    except Exception as e:
        db.rollback()
        return modef.DefaultResponse(status=False, msg=f"Error processing join request: {str(e)}")


@router.get("/invites", response_model=mores.TripInviteListResponse)
async def get_trip_invites(current_user: Annotated[modef.User, Depends(get_current_user)],
                           db: Session = Depends(connect_to_db)):
    """Get trip invites for the current user"""
    try:
        user = db.query(model.Users).filter(
            model.Users.email == current_user.email,
            model.Users.is_deleted == False
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get all invites for this user
        invites = db.query(model.TripsInvites).filter(
            model.TripsInvites.id_user == user.id
        ).all()

        invites_list = []
        for invite in invites:
            # Get trip details for context
            trip = db.query(model.Trips).filter(model.Trips.id == invite.id_trip).first()
            
            if trip:
                invites_list.append(mores.TripInvite(
                    invite_id=invite.id,
                    trip_id=invite.id_trip,
                    user_email=user.email,
                    status=invite.status.value,
                    invited_at=trip.created_at  # Using trip creation as approximation since no timestamp in invites
                ))

        return mores.TripInviteListResponse(invites=invites_list)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving invites: {str(e)}"
        )
