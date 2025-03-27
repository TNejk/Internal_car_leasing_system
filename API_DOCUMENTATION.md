# Car Leasing System API Documentation

## Authentication
All endpoints except `/login` and `/register` require JWT authentication. Include the JWT token in the Authorization header.

## Endpoints

### Authentication
#### POST /login
Authenticates a user and returns a JWT token.

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
- 200: Returns JWT token and user role
- 401: Invalid credentials
- 501: Database error

#### POST /logout
Logs out the current user by invalidating their JWT token.

**Headers:**
- Authorization: JWT token

**Response:**
- 200: Successfully logged out
- 401: Unauthorized


### User Management
#### POST /register
Registers a new user. Only accessible by admin users.

**Headers:**
- Authorization: JWT token (admin only)

**Request Body:**
```json
{
    "requester": "string",
    "req_password": "string",
    "email": "string",
    "password": "string",
    "role": "string"
}
```

**Response:**
- 200: User successfully registered
- 400: Missing parameters
- 401: Unauthorized

#### POST /delete_user
Deletes a user from the system. Only accessible by admin users.

**Headers:**
- Authorization: JWT token (admin only)

**Request Body:**
```json
{
    "email": "string"
}
```

**Response:**
- 200: User successfully deleted
- 400: Unauthorized
- 500: Missing parameters or error

### Car Management

#### POST /create_car
Creates a new car in the system. Only accessible by admin users.

**Headers:**
- Authorization: JWT token (admin only)

**Request Body:**
```json
{
    "car_name": "string",
    "spz": "string",
    "location": "string",
    "status": "string",
    "gas": "string",
    "drive_type": "string",
    "image": "base64_string",
    "image_extension": "string"
}
```

**Response:**
- 200: Car successfully created
- 400: Unauthorized
- 500: Error creating car

#### POST /delete_car
Deletes a car from the system. Only accessible by admin users.

**Headers:**
- Authorization: JWT token (admin only)

**Request Body:**
```json
{
    "car_name": "string"
}
```

**Response:**
- 200: Car successfully deleted
- 400: Unauthorized
- 500: Missing parameters or error

#### POST /decommision_car
Marks a car as decommissioned. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Request Body:**
```json
{
    "car_name": "string",
    "timeto": "datetime"
}
```

**Response:**
- 200: Car successfully decommissioned
- 400: Unauthorized or missing parameters
- 500: Error processing request

#### POST /activate_car
Reactivates a decommissioned car. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Request Body:**
```json
{
    "car_name": "string"
}
```

**Response:**
- 200: Car successfully activated
- 401: Unauthorized

### Car Information

#### GET /get_cars
Retrieves a list of all cars. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Response:**
- 200: List of cars
- 400: Unauthorized
- 500: Database error

#### GET /get_car_list
Retrieves a filtered list of cars based on location.

**Headers:**
- Authorization: JWT token

**Query Parameters:**
- location (optional): Filter cars by location

**Response:**
- 200: List of filtered cars
- 500: Database error

#### POST /get_full_car_info
Retrieves detailed information about a specific car.

**Headers:**
- Authorization: JWT token

**Request Body:**
```json
{
    "car_id": "string"
}
```

**Response:**
- 200: Detailed car information
- 404: Car not found
- 500: Database error

### Leasing Operations

#### POST /lease_car
Creates a new car lease.

**Headers:**
- Authorization: JWT token

**Request Body:**
```json
{
    "recipient": "string",
    "car_name": "string",
    "stk": "string",
    "is_private": boolean,
    "timeof": "datetime",
    "timeto": "datetime"
}
```

**Response:**
- 200: Lease successfully created
- 400: Invalid parameters
- 500: Error creating lease

#### POST /cancel_lease
Cancels an existing car lease.

**Headers:**
- Authorization: JWT token

**Request Body:**
```json
{
    "recipient": "string",
    "car_name": "string"
}
```

**Response:**
- 200: Lease successfully cancelled
- 400: Unauthorized
- 500: Error cancelling lease

#### POST /return_car
Records the return of a leased car.

**Headers:**
- Authorization: JWT token

**Request Body:**
```json
{
    "id_lease": "string",
    "time_of_return": "datetime",
    "health": "string",
    "note": "string",
    "location": "string",
    "damaged": boolean,
    "dirty": boolean,
    "int_damage": boolean,
    "ext_damage": boolean,
    "collision": boolean
}
```

**Response:**
- 200: Car successfully returned
- 400: Missing parameters
- 500: Database error

### Request Management

#### POST /get_requests
Retrieves all pending car requests. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Response:**
- 200: List of pending requests
- 500: Database error

#### POST /approve_req
Approves or rejects a car request. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Request Body:**
```json
{
    "approval": boolean,
    "request_id": "string",
    "timeof": "datetime",
    "timeto": "datetime",
    "id_car": "string",
    "reciever": "string"
}
```

**Response:**
- 200: Request successfully processed
- 400: Unauthorized or invalid parameters
- 500: Error processing request

### Reports

#### POST /list_reports
Lists all available reports. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Response:**
- 200: List of report files
- 400: Unauthorized

#### GET /get_report/{filename}
Downloads a specific report file. Only accessible by manager and admin users.

**Headers:**
- Authorization: JWT token (manager/admin only)

**Parameters:**
- filename: Name of the report file

**Response:**
- 200: Report file
- 400: Unauthorized
- 404: File not found
- 500: Error accessing file

### Token Management

#### POST /check_token
Validates the current JWT token.

**Headers:**
- Authorization: JWT token

**Response:**
- 200: Token is valid
- 401: Invalid token 