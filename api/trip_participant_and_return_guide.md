# Trip Participant Management & Car Returns Guide

## Overview
This guide covers two critical trip system features:
1. **Participant Cancellation** - Users can cancel their trip participation before it starts
2. **Trip Car Returns** - Only trip creators can return cars, with enhanced control

---

## 1. Trip Participant Cancellation

### Problem Solved
- Users were stuck in trips once they accepted
- No way to cancel participation without cancelling entire trip
- Trip creator had no visibility into cancellations

### New Endpoint: `POST /cancel_trip_participation`

#### Request Body:
```json
{
  "trip_id": 123
}
```

#### Workflow:
1. **Validation Checks**:
   - User must be an accepted participant (not creator)
   - Trip must not have started yet
   - User must exist in trip participants

2. **Driver Cancellation**:
   - If user is a driver → Cancel their lease + Free the car
   - If user is passenger → Just remove from trip

3. **Notifications**:
   - Trip creator gets notified about cancellation
   - If cancellation leaves cars without drivers → Alert creator

4. **Response Examples**:
```json
// Success
{
  "status": true,
  "msg": "Participation cancelled successfully"
}

// Error - Trip started
{
  "status": false,
  "msg": "Cannot cancel participation after trip has started"
}

// Error - User is creator
{
  "status": false,
  "msg": "Trip creator cannot cancel participation. Cancel the entire trip instead."
}
```

#### Business Logic:
- **Before Trip Starts**: ✅ Can cancel
- **After Trip Starts**: ❌ Cannot cancel
- **Trip Creator**: ❌ Must cancel entire trip
- **Driver Role**: Frees car + cancels lease
- **Passenger Role**: Just removes from trip

---

## 2. Trip Car Returns System

### Problem Solved
- Regular users could return trip cars individually
- No unified trip completion process
- Trip creator had no control over car returns

### Three New Endpoints:

#### A) `POST /return_trip_car` - Single Car Return
**Only trip creator can use this**

```json
{
  "trip_id": 123,
  "car_id": 456,
  "time_of_return": "2025-01-20 15:30:00",
  "health": "good",
  "note": "No issues",
  "location": "Bratislava",
  "damaged": false,
  "dirty": false,
  "int_damage": false,
  "ext_damage": false,
  "collision": false
}
```

#### B) `POST /return_all_trip_cars` - Bulk Return
**Return all trip cars at once**

```json
{
  "trip_id": 123,
  "time_of_return": "2025-01-20 15:30:00",
  "note": "Great trip!",
  "health": "good",
  "location": "Banská Bystrica",
  "car_data": {
    "456": {
      "health": "mild",
      "damaged": true,
      "note": "Minor scratch on door"
    },
    "789": {
      "health": "good",
      "note": "Perfect condition"
    }
  }
}
```

#### C) `POST /return_car_enhanced` - Smart Router
**Replaces existing return_car for trip-aware returns**

- Detects if lease is part of trip
- Blocks non-creators from returning trip cars
- Provides helpful error messages

```json
// Error response for trip cars
{
  "status": false,
  "msg": "This car is part of a trip. Only the trip creator can return cars.",
  "trip_id": 123,
  "trip_name": "Weekend Mountains",
  "creator_email": "creator@example.com"
}
```

---

## 3. Permission Matrix

| Action | Regular User | Trip Participant | Trip Creator | Manager/Admin |
|--------|-------------|------------------|--------------|---------------|
| Cancel own participation | ❌ | ✅ (before start) | ❌ (cancel trip) | ✅ |
| Return regular lease car | ✅ | ✅ | ✅ | ✅ |
| Return trip car | ❌ | ❌ | ✅ | ✅ |
| Return all trip cars | ❌ | ❌ | ✅ | ✅ |
| Cancel entire trip | ❌ | ❌ | ✅ | ✅ |

---

## 4. Notification System

### Participant Cancellation Notifications:

#### To Trip Creator:
```
📧 Title: "Účastník zrušil účasť na výlete: [Trip Name]"
📝 Message: "[Email] zrušil účasť na výlete. Auto: [Car], Rola: [Role]"
```

#### Warning if No Driver:
```
⚠️ Title: "Upozornenie: Výlet [Trip Name] nemá vodiča!"
📝 Message: "Po zrušení účasti [Email] nemajú niektoré autá vodičov. Priraďte nových vodičov alebo zrušte výlet."
```

### Car Return Notifications:

#### To Driver (when creator returns car):
```
🚗 Title: "Auto vrátené: [Trip Name]"
📝 Message: "Vaše auto [Car Name] bolo vrátené organizátorom výletu."
```

#### To Managers (if damaged):
```
🔧 Title: "Poškodenie auta pri výlete!"
📝 Message: "Auto [Car Name] z výletu '[Trip Name]' bolo vrátené s poškodením."
```

---

## 5. Frontend Integration

### Participant Cancellation UI:
```javascript
// Show cancel button only for non-creators before trip starts
if (!trip.is_creator && trip.status === 'scheduled' && isBeforeStartTime) {
  showCancelParticipationButton(trip.trip_id);
}

function cancelParticipation(tripId) {
  fetch('/cancel_trip_participation', {
    method: 'POST',
    body: JSON.stringify({ trip_id: tripId }),
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.status) {
      showMessage("Participation cancelled successfully");
      refreshTripsList();
    } else {
      showError(data.msg);
    }
  });
}
```

### Trip Car Returns UI:
```javascript
// Show return options only for trip creator
if (trip.is_creator && trip.status === 'ongoing') {
  showTripReturnOptions(trip.trip_id, trip.cars);
}

function returnAllTripCars(tripId) {
  const returnData = {
    trip_id: tripId,
    time_of_return: getCurrentTime(),
    location: getSelectedLocation(),
    car_data: getCarSpecificData() // Optional car-specific details
  };
  
  fetch('/return_all_trip_cars', {
    method: 'POST',
    body: JSON.stringify(returnData),
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
    if (data.status) {
      showMessage(`Trip completed! Returned: ${data.returned_cars.join(', ')}`);
      if (data.damaged_cars.length > 0) {
        showWarning(`Damaged cars: ${data.damaged_cars.join(', ')}`);
      }
    }
  });
}
```

---

## 6. Database Changes

### Trip Status Updates:
- When all cars returned via `/return_all_trip_cars` → Trip status = 'completed'
- Participant cancellation → Check if trip still viable
- Car return → Individual lease status = false, car status = 'stand_by'

### Cascade Effects:
- **Driver Cancellation**: Lease cancelled → Car freed → Trip viability checked
- **Car Return**: Lease completed → Car available → Driver notified
- **Trip Completion**: All leases closed → Trip status updated

---

## 7. Benefits

### For Users:
✅ **Flexibility**: Can cancel participation if plans change
✅ **Clarity**: Clear error messages about trip vs regular reservations  
✅ **Safety**: Cannot accidentally break trips by returning cars individually

### For Trip Creators:
✅ **Control**: Full authority over trip car returns
✅ **Visibility**: Notified of all participant changes
✅ **Efficiency**: Can return all cars at once
✅ **Flexibility**: Can return cars individually if needed

### For System:
✅ **Data Integrity**: Prevents inconsistent trip states
✅ **Clear Ownership**: Trip creator responsible for trip completion
✅ **Audit Trail**: All actions logged and tracked
✅ **Notification Coverage**: All stakeholders informed of changes

This system ensures that trips are managed cohesively while giving participants reasonable flexibility to adjust their participation before trips begin. 