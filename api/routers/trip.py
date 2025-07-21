from fastapi import APIRouter, Depends
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
