from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_, text
from typing import Optional, Dict, Any
from uuid import UUID
import logging
import json
from urllib.parse import parse_qs, unquote_plus
from ..database import get_db
from ..models import HealthMeasurement, User, Device, Customer
from ..schemas import (
    HealthMeasurementResponse,
    HealthMeasurementList,
    HealthMeasurementUpdate,
    SendReportEmailBody,
    StatsResponse
)
from ..auth import get_current_user, get_current_user_optional
from ..routers.devices import _allowed_device_ids_for_user
from ..email_service import send_report_email
from ..ai_service import analyze_health_data, stream_health_analysis
from ..error_handler import log_and_store_error
from ..owner_notifications import notify_owners_for_measurement

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_record_no(data: Dict[str, Any]) -> Optional[str]:
    """Extract recordNo from payload (top-level or datas[0])."""
    if not data or not isinstance(data, dict):
        return None
    record_no = data.get("recordNo")
    if record_no is not None and str(record_no).strip():
        return str(record_no).strip()
    datas = data.get("datas")
    if isinstance(datas, list) and len(datas) > 0 and isinstance(datas[0], dict):
        record_no = datas[0].get("recordNo")
        if record_no is not None and str(record_no).strip():
            return str(record_no).strip()
    return None


def _find_measurement_by_record_no(db: Session, record_no: str) -> Optional[HealthMeasurement]:
    """Return existing measurement with this recordNo (dedupe)."""
    return db.query(HealthMeasurement).filter(
        text(
            "measurement_data->>'recordNo' = :rn OR "
            "(measurement_data->'datas'->0->>'recordNo') = :rn"
        ).bindparams(rn=record_no)
    ).first()


def upsert_device(db: Session, device_id: str, data: Dict[str, Any]) -> None:
    """
    Ensure a Device row exists for `device_id`.
    On first sight the device is auto-registered with metadata extracted from
    the payload (deviceModel, unitName, unitNo, macAddr).
    Existing records are NOT overwritten (owner_id stays intact).
    """
    if not device_id:
        return
    try:
        existing = db.query(Device).filter(Device.device_id == device_id).first()
        if existing:
            return  # already known, nothing to do

        # Derive a friendly name from payload fields
        model     = data.get("deviceModel") or ""
        unit_name = data.get("unitName")    or ""
        unit_no   = data.get("unitNo")      or ""
        mac       = data.get("macAddr")     or ""
        parts = [p for p in [model, unit_name, unit_no] if p]
        friendly_name = " – ".join(parts) if parts else None

        db_device = Device(
            device_id=device_id,
            name=friendly_name or device_id,
            device_model=model  or None,
            mac_addr=mac        or None,
            unit_no=unit_no     or None,
            unit_name=unit_name or None,
            owner_id=None,   # unassigned until an admin links it
        )
        db.add(db_device)
        db.flush()   # don't commit yet – caller owns the transaction
        logger.info(
            f"Auto-registered new device: id={device_id!r} name={friendly_name!r} "
            f"model={model!r} mac={mac!r}"
        )
    except Exception as exc:
        # Non-fatal: log and continue so the measurement still gets stored
        logger.warning(f"upsert_device failed for {device_id!r}: {exc}")

@router.get("/health-data/analyze/{measurement_id}")
async def analyze_report(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin/Staff: Get AI analysis for a report"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    # Prepare customer info if available
    customer_info = None
    if measurement.customer:
        customer_info = {
            "name": measurement.customer.full_name,
            "age": None, # Calculate from dob if needed
            "email": measurement.customer.email
        }
        if measurement.customer.dob:
            from datetime import date
            today = date.today()
            customer_info["age"] = today.year - measurement.customer.dob.year - ((today.month, today.day) < (measurement.customer.dob.month, measurement.customer.dob.day))

    # Resolve primary record for AI (device format has measurement_data.datas[0])
    payload = measurement.measurement_data or {}
    if isinstance(payload.get("datas"), list) and len(payload["datas"]) > 0:
        primary_record = payload["datas"][0]
        device_context = {k: v for k, v in payload.items() if k != "datas"}
    else:
        primary_record = payload
        device_context = None
    analysis = await analyze_health_data(primary_record, customer_info, device_context=device_context)
    return analysis


@router.get("/health-data/analyze/{measurement_id}/stream")
async def stream_analyze_report(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream AI analysis as plain text (SSE). No JSON parsing on stream – text appears live."""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    customer_info = None
    if measurement.customer:
        customer_info = {
            "name": measurement.customer.full_name,
            "age": None,
            "email": measurement.customer.email,
        }
        if measurement.customer.dob:
            from datetime import date
            today = date.today()
            customer_info["age"] = today.year - measurement.customer.dob.year - (
                (today.month, today.day) < (measurement.customer.dob.month, measurement.customer.dob.day)
            )

    payload = measurement.measurement_data or {}
    if isinstance(payload.get("datas"), list) and len(payload["datas"]) > 0:
        primary_record = payload["datas"][0]
        device_context = {k: v for k, v in payload.items() if k != "datas"}
    else:
        primary_record = payload
        device_context = None

    async def sse_events():
        async for chunk in stream_health_analysis(primary_record, customer_info, device_context=device_context):
            if chunk.strip().startswith("{"):
                try:
                    obj = json.loads(chunk)
                    if obj.get("error"):
                        yield f"data: {json.dumps({'error': obj['error']})}\n\n"
                        return
                except json.JSONDecodeError:
                    pass
            yield f"data: {json.dumps({'text': chunk})}\n\n"

    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/health-data/send-report-email/{measurement_id}")
async def send_report_by_email(
    measurement_id: UUID,
    body: Optional[SendReportEmailBody] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send health report via email. Optionally pass body with email (e.g. after customer enters email on kiosk)."""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    target_email = None
    customer_name = "Client"
    
    if body and body.email:
        target_email = str(body.email).strip().lower()
        customer_name = "Client"
        if measurement.customer:
            customer_name = measurement.customer.full_name
        else:
            md = measurement.measurement_data or {}
            if isinstance(md.get("datas"), list) and md["datas"]:
                customer_name = md["datas"][0].get("name") or customer_name
            elif md.get("name"):
                customer_name = md["name"]
    else:
        if measurement.customer:
            target_email = measurement.customer.email
            customer_name = measurement.customer.full_name
            if not target_email and measurement.customer.user:
                target_email = measurement.customer.user.email
            
    if not target_email:
        raise HTTPException(
            status_code=400,
            detail="No email specified. Pass { \"email\": \"...\" } in the request body, or link the measurement to a customer with an email."
        )
    
    success = await send_report_email(
        target_email,
        customer_name,
        measurement.measurement_data,
        measurement.created_at,
        str(measurement.id)
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP configuration.")
    return {"message": f"Report sent successfully to {target_email}"}

def calculate_bmi_category(bmi: Optional[float]) -> Optional[str]:
    """Calculate BMI category"""
    if bmi is None:
        return None
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        return "normal"
    elif bmi < 30:
        return "overweight"
    else:
        return "obesity"

@router.post("/receive-measurement")
async def receive_measurement_legacy(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint that matches the original reference implementation.
    Receives measurement data in the original format (action, deviceID, datas).
    No authentication required - designed for kiosks/devices.
    
    Expected format:
    {
        "action": "string (optional, defaults to 'N/A')",
        "deviceID": "string (optional, defaults to 'N/A')",
        "datas": {
            // nested JSON object with actual measurement data
        }
    }
    
    Returns:
    {
        "retCode": 1,
        "msg": "success",
        "control": 0
    }
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"POST /receive-measurement received from {client_ip}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    data = None
    try:
        # Read body once
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace") if body else ""
        logger.info(f"POST /receive-measurement body length: {len(body)} bytes, full payload: {body_str}")
        
        if not body_str or not body_str.strip():
            raise HTTPException(status_code=400, detail="Empty request body")
        
        # Parse body: try JSON first, then form-urlencoded (e.g. data={"key":"value"})
        parsed = None
        try:
            parsed = json.loads(body_str)
        except json.JSONDecodeError:
            try:
                form = parse_qs(body_str, keep_blank_values=True)
                for key in ("data", "payload", "body"):
                    if key in form and form[key]:
                        raw = form[key][0]
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8", errors="replace")
                        parsed = json.loads(unquote_plus(raw) if raw.startswith("%") else raw)
                        logger.info(f"POST /receive-measurement parsed JSON from form field {key!r}")
                        break
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"POST /receive-measurement failed to parse JSON or form: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON or form-urlencoded body") from e
        if parsed is None:
            raise HTTPException(status_code=400, detail="Invalid JSON or form-urlencoded body")
        
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=400,
                detail="Request body must be a JSON object, not array or primitive"
            )
        # Unwrap one level if client sent { "body": {...} }, { "payload": {...} }, or { "data": {...} }
        if set(parsed.keys()) <= {"body", "payload", "data"}:
            for key in ("body", "payload", "data"):
                if key in parsed and isinstance(parsed[key], dict):
                    data = parsed[key]
                    logger.info(f"POST /receive-measurement unwrapped payload from top-level key: {key!r}")
                    break
            else:
                data = parsed
        else:
            data = parsed
        logger.info(f"POST /receive-measurement parsed JSON successfully, keys: {list(data.keys())}")
        
        # Dedupe by recordNo: skip if we already have this report
        record_no = _get_record_no(data)
        if record_no:
            existing = _find_measurement_by_record_no(db, record_no)
            if existing:
                logger.info(f"POST /receive-measurement duplicate recordNo={record_no}, returning success without storing")
                return {"retCode": 1, "msg": "success", "control": 0}
        
        # Store full payload: all keys kept in measurement_data
        measurement_data = dict(data)
        action = data.get("action") or data.get("Action")
        device_id = data.get("deviceID") or data.get("device_id") or data.get("deviceNo")
        kiosk_location = data.get("kiosk_location") or data.get("deviceID") or data.get("device_id") or data.get("deviceNo")
        customer_id = data.get("customer_id")
        
        raw_data = {
            "raw_body": body_str,
            "parsed_data": data,
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
        
        # Auto-register device if not yet known
        upsert_device(db, device_id, data)

        db_measurement = HealthMeasurement(
            action=action,
            device_id=device_id,
            kiosk_location=kiosk_location,
            measurement_data=measurement_data,  # Full payload, all keys kept
            raw_data=raw_data,
            created_by=None,
            customer_id=customer_id
        )
        db.add(db_measurement)
        db.commit()
        db.refresh(db_measurement)
        background_tasks.add_task(notify_owners_for_measurement, db_measurement.id)

        logger.info(
            f"Legacy measurement stored: id={db_measurement.id}, deviceID={device_id}, "
            f"action={action}, data_keys={list(measurement_data.keys())}"
        )

        # Return original response format
        return {
            "retCode": 1,
            "msg": "success",
            "control": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log to file and store in database (data may be unset if failure was before parse)
        request_body = (data if isinstance(data, dict) else {"raw_body": str(data)[:1000]}) if data is not None else {}
        log_and_store_error(
            error=e,
            error_type="POST_RECEIVE_MEASUREMENT_ERROR",
            endpoint="/receive-measurement",
            method="POST",
            client_ip=client_ip,
            request_body=request_body
        )
        logger.error(f"Error storing legacy measurement: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid data or error: {str(e)}")

@router.get("/health-data/receive-measurement", response_model=HealthMeasurementList)
async def get_measurements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    customer_id: Optional[UUID] = Query(None, description="Filter by customer ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all health measurements with pagination and ownership logic."""
    query = db.query(HealthMeasurement)
    
    # Ownership filtering logic (V1: device_user_owners + legacy owner_id + public)
    if current_user.role != "admin":
        allowed_device_ids = _allowed_device_ids_for_user(db, current_user)
        query = query.filter(
            or_(
                HealthMeasurement.device_id.in_(allowed_device_ids),
                HealthMeasurement.created_by == current_user.id
            )
        )

    if patient_id:
        query = query.filter(HealthMeasurement.patient_id.ilike(f"%{patient_id}%"))
    
    if device_id:
        device_id_val = device_id.strip()
        query = query.filter(
            or_(
                HealthMeasurement.device_id.ilike(f"%{device_id_val}%"),
                HealthMeasurement.measurement_data["deviceNo"].astext == device_id_val
            )
        )
        
    if customer_id:
        query = query.filter(HealthMeasurement.customer_id == customer_id)
    
    total = query.count()
    items = query.order_by(HealthMeasurement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return HealthMeasurementList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.post("/health-data/receive-measurement", response_model=HealthMeasurementResponse, status_code=201)
async def create_measurement(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Create a new health measurement.
    Stores the full request body as-is: every key is kept in measurement_data (no format split).
    Optional columns (action, device_id, patient_id, kiosk_location, customer_id) are filled from the same payload when present.
    Authentication is optional - kiosks can post without auth, authenticated users will be linked to the measurement.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_info = current_user.email if current_user else "anonymous (kiosk)"
    logger.info(f"POST /health-data/receive-measurement received from {client_ip}, user: {user_info}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    data = None  # So except block can safely reference it
    try:
        # Read body once
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace") if body else ""
        logger.info(f"POST /health-data/receive-measurement body length: {len(body)} bytes, full payload: {body_str}")
        
        if not body_str or not body_str.strip():
            raise HTTPException(status_code=400, detail="Empty request body")
        
        # Parse body: try JSON first, then form-urlencoded (e.g. data={"key":"value"})
        parsed = None
        try:
            parsed = json.loads(body_str)
        except json.JSONDecodeError:
            try:
                form = parse_qs(body_str, keep_blank_values=True)
                for key in ("data", "payload", "body"):
                    if key in form and form[key]:
                        raw = form[key][0]
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8", errors="replace")
                        parsed = json.loads(unquote_plus(raw) if raw.startswith("%") else raw)
                        logger.info(f"POST /health-data/receive-measurement parsed JSON from form field {key!r}")
                        break
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"POST /health-data/receive-measurement failed to parse JSON or form: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON or form-urlencoded body") from e
        if parsed is None:
            raise HTTPException(status_code=400, detail="Invalid JSON or form-urlencoded body")
        
        # Accept top-level dict only; unwrap common wrappers (body, payload, data)
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=400,
                detail="Request body must be a JSON object, not array or primitive"
            )
        # Unwrap one level if client sent { "body": {...} }, { "payload": {...} }, or { "data": {...} }
        if set(parsed.keys()) <= {"body", "payload", "data"}:
            for key in ("body", "payload", "data"):
                if key in parsed and isinstance(parsed[key], dict):
                    data = parsed[key]
                    logger.info(f"POST /health-data/receive-measurement unwrapped payload from top-level key: {key!r}")
                    break
            else:
                data = parsed
        else:
            data = parsed
        logger.info(f"POST /health-data/receive-measurement parsed JSON successfully, keys: {list(data.keys())}")
        
        # Dedupe by recordNo: skip if we already have this report
        record_no = _get_record_no(data)
        if record_no:
            existing = _find_measurement_by_record_no(db, record_no)
            if existing:
                logger.info(f"POST /health-data/receive-measurement duplicate recordNo={record_no}, returning existing id={existing.id}")
                return existing
        
        # Keep the entire payload: all keys stored in measurement_data (no format split)
        measurement_data = dict(data)
        customer_id = data.get("customer_id")
        action = data.get("action") or data.get("Action")
        device_id = data.get("deviceID") or data.get("device_id") or data.get("deviceNo")
        patient_id = data.get("patient_id")
        kiosk_location = data.get("kiosk_location") or data.get("deviceID") or data.get("device_id") or data.get("deviceNo")
        
        # Store raw data for analysis - preserve EVERYTHING about the request
        raw_data = {
            "raw_body": body_str,
            "parsed_data": data,
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
        
        # Auto-register device if not yet known
        upsert_device(db, device_id, data)

        db_measurement = HealthMeasurement(
            action=action,
            device_id=device_id,
            patient_id=patient_id,
            kiosk_location=kiosk_location,
            measurement_data=measurement_data,  # Full payload, all keys kept
            raw_data=raw_data,
            created_by=current_user.id if current_user else None,
            customer_id=customer_id
        )
        logger.info(f"Stored measurement: all keys kept, measurement_data keys={list(measurement_data.keys())}, user={user_info}")
        
        db.add(db_measurement)
        db.commit()
        db.refresh(db_measurement)
        logger.info(f"Successfully stored measurement with ID: {db_measurement.id}")
        background_tasks.add_task(notify_owners_for_measurement, db_measurement.id)
        return db_measurement
    except HTTPException:
        raise
    except Exception as e:
        # Log to file and store in database (data may be unset if failure was before parse)
        request_body = None
        if data is not None and isinstance(data, dict):
            request_body = data
        elif data is not None:
            request_body = {"raw_body": str(data)[:1000]}
        log_and_store_error(
            error=e,
            error_type="POST_HEALTH_DATA_MEASUREMENT_ERROR",
            endpoint="/health-data/receive-measurement",
            method="POST",
            client_ip=client_ip,
            user_id=current_user.id if current_user else None,
            request_body=request_body or {}
        )
        logger.error(f"Error storing measurement: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing measurement: {str(e)}")

@router.get("/health-data/receive-measurement/{measurement_id}", response_model=HealthMeasurementResponse)
async def get_measurement(
    measurement_id: str,
    db: Session = Depends(get_db)
):
    """Get a single health measurement by ID"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return measurement

@router.patch("/health-data/receive-measurement/{measurement_id}", response_model=HealthMeasurementResponse)
async def attribute_measurement(
    measurement_id: str,
    body: HealthMeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Staff/Admin: Attribute measurement to a customer (set or clear customer_id)."""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    updates = body.model_dump(exclude_unset=True)
    if "customer_id" in updates:
        measurement.customer_id = updates["customer_id"]
    if "patient_id" in updates:
        measurement.patient_id = updates["patient_id"]
    if "kiosk_location" in updates:
        measurement.kiosk_location = updates["kiosk_location"]
    db.commit()
    db.refresh(measurement)
    logger.info(f"Measurement {measurement_id} attributed by {current_user.email}")
    return measurement

@router.get("/health-data/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get statistics about health measurements"""
    query = db.query(HealthMeasurement)
    
    # Match get_measurements: device_user_owners + legacy owner + public (not owned_devices only)
    if current_user.role != "admin":
        allowed_device_ids = _allowed_device_ids_for_user(db, current_user)
        if not allowed_device_ids:
            query = query.filter(HealthMeasurement.created_by == current_user.id)
        else:
            query = query.filter(
                or_(
                    HealthMeasurement.device_id.in_(allowed_device_ids),
                    HealthMeasurement.created_by == current_user.id
                )
            )

    total = query.count()
    
    # Count BMI categories
    all_measurements = query.all()
    
    bmi_normal = 0
    bmi_overweight = 0
    bmi_obesity = 0
    
    for measurement in all_measurements:
        data = measurement.measurement_data
        bmi = data.get("bmi") or data.get("BMI") or data.get("imc") or data.get("IMC")
        
        if bmi is not None:
            try:
                bmi_value = float(bmi)
                category = calculate_bmi_category(bmi_value)
                if category == "normal":
                    bmi_normal += 1
                elif category == "overweight":
                    bmi_overweight += 1
                elif category == "obesity":
                    bmi_obesity += 1
            except (ValueError, TypeError):
                pass
    
    return StatsResponse(
        total_measurements=total,
        bmi_normal=bmi_normal,
        bmi_overweight=bmi_overweight,
        bmi_obesity=bmi_obesity
    )
