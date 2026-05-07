# Authentication System Setup Guide

## Overview

The health-data-app now includes a complete authentication system with:
- **PIN-based authentication** (sent via email)
- **User roles** (Admin and Regular)
- **JWT token-based sessions**
- **Admin data management** capabilities

## Features

### User Authentication
- Registration with email
- PIN code sent via SMTP email
- PIN expires in 10 minutes
- JWT tokens for session management (7-day expiry)
- Role-based access control

### User Roles
- **Regular User**: Can create and view their own measurements
- **Admin**: Can manage all data and users

### Admin Capabilities
- View all measurements
- Edit/Delete any measurement
- Manage users (view, edit, delete, promote to admin)
- View user statistics

## Setup Instructions

### 1. Configure Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# JWT Secret (REQUIRED - Change this!)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# SMTP Configuration (Required for email PIN codes)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password for Gmail
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Health Data App
```

**For Gmail:**
1. Enable 2-Factor Authentication
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password as `SMTP_PASSWORD`

### 2. Restart Backend

```bash
cd /root/health-data-app
docker-compose restart backend
```

Or rebuild if needed:
```bash
docker-compose up -d --build backend
```

### 3. Create First Admin User

After the backend is running, create your first admin:

```bash
docker exec -it health_data_backend python create_admin.py
```

Follow the prompts to enter an email address. The PIN will be displayed and sent via email (if SMTP is configured).

### 4. Verify Database Tables

The new tables should be created automatically:
- `users` - User accounts
- `health_measurements` - Updated with `created_by` field

## API Endpoints

### Authentication Endpoints

#### Register New User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Registration successful. PIN code sent to your email.",
  "expires_in_minutes": 10
}
```

#### Request PIN (for login)
```http
POST /auth/request-pin
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Verify PIN and Get Token
```http
POST /auth/verify-pin
Content-Type: application/json

{
  "email": "user@example.com",
  "pin_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "regular",
    "is_active": true,
    "created_at": "2026-01-23T..."
  }
}
```

#### Get Current User Info
```http
GET /auth/me
Authorization: Bearer <token>
```

### Health Data Endpoints (Now Require Authentication)

#### Create Measurement
```http
POST /health-data/receive-measurement
Authorization: Bearer <token>
Content-Type: application/json

{
  "patient_id": "NDT-98241",
  "kiosk_location": "Station Santé A1",
  "measurement_data": {
    "height": 175,
    "weight": 75,
    "bmi": 24.5,
    "blood_pressure": "120/80"
  }
}
```

#### List Measurements (Public - no auth required)
```http
GET /health-data/receive-measurement?page=1&page_size=20
```

### Admin Endpoints

All admin endpoints require admin role and authentication.

#### List All Measurements
```http
GET /admin/measurements?page=1&page_size=20
Authorization: Bearer <admin_token>
```

#### Get Measurement
```http
GET /admin/measurements/{measurement_id}
Authorization: Bearer <admin_token>
```

#### Update Measurement
```http
PUT /admin/measurements/{measurement_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "patient_id": "NDT-98241",
  "kiosk_location": "Station Santé A1",
  "measurement_data": {...}
}
```

#### Delete Measurement
```http
DELETE /admin/measurements/{measurement_id}
Authorization: Bearer <admin_token>
```

#### List All Users
```http
GET /admin/users
Authorization: Bearer <admin_token>
```

#### Get User
```http
GET /admin/users/{user_id}
Authorization: Bearer <admin_token>
```

#### Update User
```http
PUT /admin/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "role": "admin",
  "is_active": true
}
```

#### Delete User
```http
DELETE /admin/users/{user_id}
Authorization: Bearer <admin_token>
```

#### Promote User to Admin
```http
POST /admin/users/{user_id}/make-admin
Authorization: Bearer <admin_token>
```

## Usage Flow

### For Regular Users:
1. Register: `POST /auth/register` with email
2. Check email for PIN code
3. Verify PIN: `POST /auth/verify-pin` → receive JWT token
4. Use token in `Authorization: Bearer <token>` header for authenticated requests
5. Create measurements: `POST /health-data/receive-measurement`

### For Admins:
1. Same registration/login flow as regular users
2. Use admin endpoints to manage data and users
3. All admin operations are logged

## Security Notes

1. **JWT Secret Key**: Must be changed in production! Use a strong random string.
2. **SMTP Credentials**: Store securely, never commit to git
3. **PIN Expiry**: PINs expire in 10 minutes for security
4. **Token Expiry**: JWT tokens expire in 7 days
5. **HTTPS**: Use HTTPS in production for secure token transmission

## Troubleshooting

### PIN Not Received
- Check SMTP configuration
- Check spam folder
- Check backend logs: `docker-compose logs backend`
- If SMTP not configured, PIN will be logged in console

### Authentication Errors
- Verify token is included in `Authorization: Bearer <token>` header
- Check token hasn't expired
- Verify user account is active

### Admin Access Denied
- Verify user role is "admin"
- Use `/admin/users/{user_id}/make-admin` to promote user

## Database Schema

### Users Table
- `id` (UUID) - Primary key
- `email` (String) - Unique, indexed
- `role` (Enum) - "admin" or "regular"
- `pin_hash` (String) - Hashed PIN
- `pin_code` (String) - Temporary hashed PIN for login
- `pin_expires_at` (DateTime) - PIN expiration
- `is_active` (Boolean) - Account status
- `created_at`, `updated_at`, `last_login` (DateTime)

### Health Measurements Table
- All existing fields
- `created_by` (UUID) - Foreign key to users.id (nullable)


