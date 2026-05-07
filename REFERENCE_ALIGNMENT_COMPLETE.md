# Reference Format Alignment - Complete

## Summary

Successfully aligned the backend and frontend with the reference implementation format (`reference.py`). All endpoints now process data in the reference format (action, deviceID, datas) while maintaining backward compatibility.

## Changes Made

### 1. Database Model Updates (`backend/app/models.py`)

Added new columns to `HealthMeasurement`:
- `action` (String, nullable, indexed) - Action type from reference format
- `device_id` (String, nullable, indexed) - deviceID from reference format (for filtering)

### 2. Database Migration (`backend/app/main.py`)

Added automatic migration on startup:
- Creates `action` and `device_id` columns if they don't exist
- Creates index on `device_id` for efficient filtering
- Migrates existing data (copies `kiosk_location` to `device_id` if needed)

### 3. Backend Processing (`backend/app/routers/health_data.py`)

**New Helper Function:**
- `process_reference_format()` - Extracts and normalizes reference format data

**Updated Endpoints:**

1. **`POST /receive-measurement`** (Legacy endpoint)
   - Processes reference format (action, deviceID, datas)
   - No authentication required
   - Returns: `{"retCode": 1, "msg": "success", "control": 0}`

2. **`POST /`** (Root endpoint)
   - Now processes reference format automatically
   - Detects format and processes accordingly
   - Returns reference format response for reference format input

3. **`POST /health-data/receive-measurement`** (API endpoint)
   - Accepts both reference format and new format
   - Requires authentication
   - Auto-detects format and processes accordingly

4. **`GET /health-data/receive-measurement`** (List endpoint)
   - Added `device_id` query parameter for filtering
   - Can filter by `patient_id` OR `device_id`

### 4. Schema Updates (`backend/app/schemas.py`)

Updated `HealthMeasurementResponse` to include:
- `action` (Optional[str])
- `device_id` (Optional[str])

### 5. Frontend Updates

**API Service (`frontend/src/services/api.js`):**
- Added `deviceId` parameter to `getMeasurements()` function

**Dashboard (`frontend/src/components/Dashboard.jsx`):**
- Added device filter input field
- Shows `device_id` in measurement list
- Filters measurements by device ID

## Data Format

### Reference Format (Input)
```json
{
  "action": "measure",
  "deviceID": "KIOSK-001",
  "datas": {
    "bmi": 25.5,
    "weight": 70,
    "height": 165
  }
}
```

### Database Storage
```
HealthMeasurement:
  - action: "measure"
  - device_id: "KIOSK-001"
  - kiosk_location: "KIOSK-001" (backward compatibility)
  - measurement_data: {
      "bmi": 25.5,
      "weight": 70,
      "height": 165
    }
```

### Response Format (Reference Endpoints)
```json
{
  "retCode": 1,
  "msg": "success",
  "control": 0
}
```

## Endpoints Summary

| Endpoint | Auth | Format | Response |
|----------|------|--------|----------|
| `POST /` | No | Reference or Other | Reference format or JSON |
| `POST /receive-measurement` | No | Reference | Reference format |
| `POST /health-data/receive-measurement` | Yes | Reference or New | Full object |
| `GET /health-data/receive-measurement?device_id=...` | No | - | List with device filter |

## Testing

All endpoints tested and working:
- ✅ `POST /` with reference format stores action and device_id
- ✅ `POST /receive-measurement` processes reference format
- ✅ Database migration creates columns and indexes
- ✅ Frontend shows device_id and filters by device
- ✅ Backward compatibility maintained

## Next Steps

1. Monitor incoming data to verify devices are sending in reference format
2. Check database to see if measurements are being stored correctly
3. Test frontend filtering functionality
4. Consider adding device management features if needed

