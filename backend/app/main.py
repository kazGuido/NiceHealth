from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import engine, Base, SessionLocal
from .routers import health_data
import os
import logging
import json
from .models import HealthMeasurement
from sqlalchemy import text

# Configure logging - console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console output
    ]
)
logger = logging.getLogger(__name__)

# Import error handler (this will set up file logging)
from .error_handler import log_and_store_error, general_logger

# Import v2 models so they're registered with Base (Organization, Location, etc.)
from . import models_v2  # noqa: F401

# Create database tables
Base.metadata.create_all(bind=engine)

# Lightweight startup migration for existing DBs (no Alembic yet)
with engine.begin() as conn:
    # Fix the userrole enum if it exists and is missing 'regular'
    try:
        # Check if userrole enum exists
        result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'userrole'"))
        if result.fetchone():
            # Add 'regular' if it's missing (Postgres doesn't support IF NOT EXISTS for ADD VALUE)
            conn.execute(text("COMMIT")) # End current transaction to allow ALTER TYPE
            try:
                conn.execute(text("ALTER TYPE userrole ADD VALUE 'regular'"))
            except Exception:
                pass # Already exists
            try:
                conn.execute(text("ALTER TYPE userrole ADD VALUE 'admin'"))
            except Exception:
                pass # Already exists
            try:
                conn.execute(text("ALTER TYPE userrole ADD VALUE 'staff'"))
            except Exception:
                pass # Already exists
            try:
                conn.execute(text("ALTER TYPE userrole ADD VALUE 'customer'"))
            except Exception:
                pass # Already exists
    except Exception as e:
        logger.warning(f"Enum migration warning: {e}")

    # Add new columns to existing table if missing
    conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS created_by uuid"))
    conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS action varchar"))
    conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS device_id varchar"))
    conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS customer_id uuid"))
    conn.execute(text("ALTER TABLE health_measurements ADD COLUMN IF NOT EXISTS raw_data jsonb"))
    
    # Customer table enhancements
    conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS email varchar"))
    conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS dob timestamp with time zone"))
    
    # User table enhancements
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_notified_at timestamp with time zone"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS business_name varchar"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium boolean DEFAULT false"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS branding_logo_url varchar"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS branding_primary_color varchar DEFAULT '#3B82F6'"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_cta_text varchar"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_cta_link varchar"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_phone_e164 varchar"))
    
    # New device metadata columns (auto-registration)
    conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_model varchar"))
    conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS mac_addr varchar"))
    conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS unit_no varchar"))
    conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS unit_name varchar"))

    # Create index on device_id for filtering
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_device_id ON health_measurements(device_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_health_measurements_customer_id ON health_measurements(customer_id)"))
    except Exception:
        pass  # Index might already exist
    
    # Create error_logs table if it doesn't exist
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                error_type VARCHAR NOT NULL,
                error_message VARCHAR NOT NULL,
                error_details JSONB NOT NULL,
                endpoint VARCHAR,
                method VARCHAR,
                client_ip VARCHAR,
                user_id UUID REFERENCES users(id),
                request_body JSONB,
                stack_trace TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                resolved BOOLEAN NOT NULL DEFAULT FALSE,
                resolved_at TIMESTAMP WITH TIME ZONE,
                resolved_by UUID REFERENCES users(id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_error_logs_error_type ON error_logs(error_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_error_logs_endpoint ON error_logs(endpoint)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_error_logs_created_at ON error_logs(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_error_logs_resolved ON error_logs(resolved)"))
    except Exception as e:
        logger.warning(f"Error creating error_logs table: {e}")
    
    # device_user_owners: multiple owners per device (V1). UNIQUE(device_id, user_id) = no duplicate (same user twice), still allows multiple owners per device.
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS device_user_owners (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(device_id, user_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_device_user_owners_device_id ON device_user_owners(device_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_device_user_owners_user_id ON device_user_owners(user_id)"))
        # Ensure unique constraint exists (table may have been created before we added UNIQUE)
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'device_user_owners'::regclass AND conname = 'device_user_owners_device_id_user_id_key'
                ) THEN
                    ALTER TABLE device_user_owners ADD CONSTRAINT device_user_owners_device_id_user_id_key UNIQUE (device_id, user_id);
                END IF;
            END $$;
        """))
        # Migrate existing Device.owner_id into device_user_owners (one row per device)
        conn.execute(text("""
            INSERT INTO device_user_owners (device_id, user_id)
            SELECT id, owner_id FROM devices WHERE owner_id IS NOT NULL
            ON CONFLICT (device_id, user_id) DO NOTHING
        """))
    except Exception as e:
        logger.warning(f"device_user_owners migration: {e}")

    # Migrate existing data: if kiosk_location exists but device_id doesn't, copy it
    conn.execute(text("""
        UPDATE health_measurements 
        SET device_id = kiosk_location 
        WHERE device_id IS NULL AND kiosk_location IS NOT NULL
    """))

# V2 migrations (organizations, locations, device_owners, etc.)
from .migrations_v2 import run_v2_migrations
run_v2_migrations(engine)

# After organizations exist: audit log for owner WhatsApp / PDF sends
with engine.begin() as conn:
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS owner_notification_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                measurement_id UUID NOT NULL REFERENCES health_measurements(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
                phone_e164 VARCHAR NOT NULL,
                channel VARCHAR NOT NULL DEFAULT 'whatsapp',
                status VARCHAR NOT NULL,
                detail TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_owner_notification_logs_measurement_id ON owner_notification_logs(measurement_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_owner_notification_logs_created_at ON owner_notification_logs(created_at)"))
    except Exception as e:
        logger.warning(f"owner_notification_logs migration: {e}")

app = FastAPI(
    title="Health Data API",
    description="API for storing and retrieving health measurements",
    version="1.0.0"
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    url = str(request.url)
    
    # Log request
    logger.info(f"Incoming {method} {url} from {client_ip}")
    
    try:
        response = await call_next(request)
        logger.info(f"{method} {url} - Status: {response.status_code}")
        return response
    except Exception as e:
        # Log to file and store in database
        # Note: We can't read request body here as it may have already been consumed
        try:
            log_and_store_error(
                error=e,
                error_type="MIDDLEWARE_ERROR",
                endpoint=url,
                method=method,
                client_ip=client_ip,
                request_body=None  # Can't read body in middleware after exception
            )
        except Exception as log_error:
            logger.error(f"Failed to log error: {str(log_error)}")
        
        logger.error(f"Error processing {method} {url}: {str(e)}", exc_info=True)
        raise

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routers import auth, admin, customers, devices, files, webhooks
from .routers.v2 import health_data as health_data_v2
from .routers.v2 import admin_organizations, organizations, measurements, device_owners, retail, auth_retail, public

app.include_router(health_data.router)
app.include_router(health_data_v2.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(customers.router)
app.include_router(devices.router)
app.include_router(files.router)
app.include_router(webhooks.router)

# V2 API (prefix /v2)
app.include_router(admin_organizations.router, prefix="/v2")
app.include_router(organizations.router, prefix="/v2")
app.include_router(measurements.router, prefix="/v2")
app.include_router(device_owners.router, prefix="/v2")
app.include_router(retail.router, prefix="/v2")
app.include_router(auth_retail.router, prefix="/v2")
app.include_router(public.router, prefix="/v2")

# Initialize background worker
from .worker import setup_worker
from .owner_notifications import notify_owners_for_measurement

setup_worker(app)

@app.get("/")
async def root():
    return {"message": "Health Data API", "version": "1.0.0"}

@app.post("/")
async def root_post(request: Request, background_tasks: BackgroundTasks):
    """
    Accept and store any POST to / (no auth).
    Processes reference format (action, deviceID, datas) or other formats.
    Returns reference format response: {"retCode": 1, "msg": "success", "control": 0}
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"POST / received from {client_ip}, headers: {dict(request.headers)}")
    
    try:
        # Read body once
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace") if body else ""
        logger.info(f"POST / body length: {len(body)} bytes, full payload: {body_str}")

        payload: object
        try:
            # Parse JSON from the body string
            payload = json.loads(body_str) if body_str else {}
            logger.info(f"POST / parsed JSON successfully, keys: {list(payload.keys()) if isinstance(payload, dict) else 'not a dict'}")
        except Exception as json_err:
            logger.warning(f"POST / failed to parse JSON: {str(json_err)}, using raw body")
            payload = {"_raw_body": body_str}

        db = SessionLocal()
        try:
            # Auto-register device from root POST
            if isinstance(payload, dict):
                _root_device_id = payload.get("deviceID") or payload.get("device_id") or payload.get("deviceNo")
                if _root_device_id:
                    try:
                        from .models import Device
                        if not db.query(Device).filter(Device.device_id == _root_device_id).first():
                            _model     = payload.get("deviceModel") or ""
                            _unit_name = payload.get("unitName")    or ""
                            _unit_no   = payload.get("unitNo")      or ""
                            _parts     = [p for p in [_model, _unit_name, _unit_no] if p]
                            _name      = " – ".join(_parts) if _parts else _root_device_id
                            db.add(Device(device_id=_root_device_id, name=_name, owner_id=None))
                            db.flush()
                            logger.info(f"Auto-registered device from POST /: {_root_device_id!r}")
                    except Exception as _de:
                        logger.warning(f"Device auto-register failed (POST /): {_de}")

            # Dedupe by recordNo (same as health_data router)
            if isinstance(payload, dict):
                from .routers.health_data import _get_record_no, _find_measurement_by_record_no
                record_no = _get_record_no(payload)
                if record_no:
                    existing = _find_measurement_by_record_no(db, record_no)
                    if existing:
                        logger.info(f"POST / duplicate recordNo={record_no}, skipping store")
                        return JSONResponse(status_code=200, content={"retCode": 1, "msg": "success", "control": 0})

            # Store raw data for analysis - preserve EVERYTHING about the request
            raw_data = {
                "raw_body": body_str,  # Original raw string
                "parsed_data": payload if isinstance(payload, dict) else None,  # Parsed JSON for reference
                "request_metadata": {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "client_ip": client_ip,
                    "headers": dict(request.headers),
                    "user_agent": request.headers.get("user-agent"),
                    "content_type": request.headers.get("content-type"),
                    "content_length": request.headers.get("content-length"),
                }
            }
            
            # Store full payload: all keys kept in measurement_data
            if isinstance(payload, dict):
                measurement_data = dict(payload)
                action = payload.get("action") or payload.get("Action")
                device_id = payload.get("deviceID") or payload.get("device_id")
                patient_id = payload.get("patient_id")
                kiosk_location = payload.get("kiosk_location") or payload.get("deviceID") or payload.get("device_id")
                customer_id = payload.get("customer_id")
            else:
                measurement_data = {"payload": payload}
                action = device_id = patient_id = kiosk_location = customer_id = None

            db_measurement = HealthMeasurement(
                action=action,
                device_id=device_id,
                patient_id=patient_id,
                kiosk_location=kiosk_location,
                measurement_data=measurement_data,
                raw_data=raw_data,
                created_by=None,
                customer_id=customer_id,
            )
            db.add(db_measurement)
            db.commit()
            db.refresh(db_measurement)
            background_tasks.add_task(notify_owners_for_measurement, db_measurement.id)
            logger.info(
                f"Stored POST /: id={db_measurement.id}, measurement_data keys={list(measurement_data.keys()) if isinstance(measurement_data, dict) else []}"
            )
            return JSONResponse(
                status_code=200,
                content={"retCode": 1, "msg": "success", "control": 0},
            )
        finally:
            db.close()
    except Exception as e:
        # Log to file and store in database
        log_and_store_error(
            error=e,
            error_type="POST_ROOT_ERROR",
            endpoint="/",
            method="POST",
            client_ip=client_ip,
            request_body=payload if isinstance(payload, dict) else {"raw_body": str(payload)[:1000]}
        )
        logger.error(f"Error processing POST to root: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": str(e)}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
