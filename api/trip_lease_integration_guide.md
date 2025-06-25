# Trip-Lease Integration Guide

## Problem
When implementing trips, we create leases for each car/driver combination. This creates duplication when users query their leases - they see both the trip and the individual lease entries.

## Solution
Use the `id_trip` column in the lease table to distinguish between:
- **Regular leases**: `id_trip IS NULL` - Normal car reservations
- **Trip leases**: `id_trip IS NOT NULL` - Leases created as part of a trip

## Implementation Strategy

### 1. Frontend App Structure
```
Reservations Tab
├── Regular Reservations (default view)
│   └── Shows only non-trip leases (id_trip IS NULL)
├── Trips Section
│   ├── My Trips (from trips table + trip participants)
│   └── Trip Invitations (pending invitations)
└── All Reservations (optional admin view)
    └── Shows both regular and trip leases
```

### 2. API Endpoints

#### Modified Existing Endpoints
- `POST /get_leases` - Modified to accept `include_trip_leases` parameter
  - `include_trip_leases: false` (default) - Shows only regular reservations
  - `include_trip_leases: true` - Shows all reservations including trip ones
  - Adds new fields: `trip_id`, `trip_name`, `lease_type`

#### New Dedicated Endpoints
- `POST /get_regular_leases` - Only non-trip leases
- `POST /get_trip_leases` - Only trip-related leases  
- `GET /get_my_trips` - Trip view with participants and cars
- `GET /get_trip_invitations` - Pending trip invitations
- `POST /cancel_lease_or_trip` - Smart cancellation with trip protection

### 3. Database Changes

#### Required Schema Updates
```sql
-- Add trip_id to lease table (already in trips_schema.sql)
ALTER TABLE lease ADD COLUMN id_trip INTEGER;
ALTER TABLE lease ADD CONSTRAINT fk_lease_trip FOREIGN KEY (id_trip) REFERENCES trips(id_trip) ON DELETE SET NULL;
CREATE INDEX idx_lease_trip ON lease(id_trip);
```

#### Query Examples
```sql
-- Get only regular leases for a user
SELECT * FROM lease l 
JOIN driver d ON l.id_driver = d.id_driver 
WHERE d.email = 'user@example.com' 
AND l.id_trip IS NULL;

-- Get only trip leases for a user  
SELECT * FROM lease l 
JOIN driver d ON l.id_driver = d.id_driver 
JOIN trips t ON l.id_trip = t.id_trip
WHERE d.email = 'user@example.com' 
AND l.id_trip IS NOT NULL;
```

### 4. Frontend Implementation

#### Regular Reservations View
```javascript
// Default view - shows only regular reservations
fetch('/get_leases', {
  method: 'POST',
  body: JSON.stringify({
    email: "",
    car_name: "",
    timeof: "",
    timeto: "",
    istrue: true,
    isfalse: false,
    include_trip_leases: false  // KEY: Exclude trip leases
  })
})
```

#### Trips View
```javascript
// Separate section for trips
fetch('/get_my_trips', {
  method: 'GET'
})
.then(response => response.json())
.then(data => {
  // Display trips with participant info, not individual leases
  data.trips.forEach(trip => {
    displayTripCard(trip); // Shows trip name, destination, participants
  });
});
```

### 5. User Experience

#### For Regular Users
1. **Reservations Tab**: Shows only their regular car reservations
2. **Trips Section**: Shows trips they're part of or have created
3. **Clear Distinction**: No confusion between individual leases and trips

#### For Managers/Admins
1. **Can see all lease types** with `include_trip_leases: true`
2. **Trip management**: Can cancel entire trips
3. **Lease protection**: Cannot cancel individual trip leases (must cancel whole trip)

### 6. Cancellation Logic

#### Regular Lease Cancellation
- Works as before for non-trip leases
- Updates car status to 'stand_by'

#### Trip Lease Protection
```javascript
// If user tries to cancel a trip lease individually
{
  "cancelled": false,
  "msg": "This reservation is part of a trip. Please cancel the entire trip instead.",
  "trip_id": 123
}
```

#### Trip Cancellation
- Cancels all related leases
- Frees up all cars
- Notifies all participants
- Updates trip status to 'cancelled'

### 7. Benefits

✅ **No Duplication**: Regular reservations and trips are shown separately
✅ **Data Integrity**: Leases are still created (other APIs depend on them)
✅ **Clear UX**: Users see trips as trips, not individual leases
✅ **Flexible**: Can show all reservations together if needed
✅ **Backward Compatibility**: Existing lease logic still works

### 8. Migration Steps

1. **Database**: Run `trips_schema.sql` to create trip tables
2. **API**: Replace existing `/get_leases` with modified version
3. **Frontend**: Update to use new endpoints and display logic
4. **Testing**: Verify no duplication in user views
5. **Documentation**: Update API docs

### 9. Example Responses

#### Regular Leases Response
```json
{
  "active_leases": [
    {
      "lease_id": 123,
      "car_name": "Škoda Octavia",
      "time_from": "2025-01-15 09:00:00",
      "trip_id": null,
      "trip_name": null,
      "lease_type": "regular"
    }
  ]
}
```

#### Trips Response
```json
{
  "trips": [
    {
      "trip_id": 456,
      "trip_name": "Weekend Trip to Mountains",
      "destination": "High Tatras",
      "start_time": "2025-01-20 08:00:00",
      "status": "scheduled",
      "is_creator": true,
      "cars_and_participants": [
        ["Škoda Octavia", "driver", "John Doe", "accepted"],
        ["Škoda Octavia", "passenger", "Jane Smith", "accepted"]
      ]
    }
  ]
}
```

This approach completely eliminates the duplication issue while maintaining all existing functionality and providing a clear separation between regular reservations and trips. 