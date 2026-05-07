from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import appwrite_databases
from appwrite.query import Query
import json
import datetime
import os

# Router setup
health_data_router = APIRouter(prefix="", tags=["Health Data"])

# Appwrite Collection and Database IDs from environment variables
DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID")
MEASUREMENTS_COLLECTION_ID = os.getenv("APPWRITE_HEALTH_MEASUREMENTS_COLLECTION_ID")

# Templates setup
templates = Jinja2Templates(directory="app/ui/templates")

@health_data_router.post("/receive-measurement")
async def receive_measurement(request: Request):
    """
    Receives measurement data and stores it as a document in Appwrite.
    """
    if not DATABASE_ID or not MEASUREMENTS_COLLECTION_ID:
        raise HTTPException(
            status_code=500, 
            detail="Appwrite database or collection ID is not configured on the server."
        )

    try:
        data = await request.json()
        
        # Prepare document for Appwrite
        document_data = {
            "action": data.get("action", "N/A"),
            "deviceID": data.get("deviceID", "N/A"),
            "datas": json.dumps(data.get("datas", {})), # Store JSON as a string
            "timestamp": str(datetime.datetime.now())
        }

        # Create document in Appwrite
        appwrite_databases.create_document(
            database_id=DATABASE_ID,
            collection_id=MEASUREMENTS_COLLECTION_ID,
            document_id="unique()",
            data=document_data
        )

        return {
            "retCode": 1,
            "msg": "success",
            "control": 0
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data or Appwrite error: {str(e)}")

@health_data_router.get("/display-measurements", response_class=HTMLResponse)
async def display_measurements(request: Request):
    """
    Serves the standalone health_measurements.html page.
    The page will fetch its own data from the /api/measurements endpoint.
    """
    try:
        return templates.TemplateResponse(
            "health_measurements.html", 
            {"request": request, "measurements": []} 
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving page: {str(e)}")

@health_data_router.get("/api/measurements")
async def get_measurements_api():
    """
    Fetches all measurement records from Appwrite.
    """
    if not DATABASE_ID or not MEASUREMENTS_COLLECTION_ID:
        raise HTTPException(
            status_code=500, 
            detail="Appwrite database or collection ID is not configured on the server."
        )
        
    try:
        # Fetch all documents from the collection
        result = appwrite_databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=MEASUREMENTS_COLLECTION_ID,
            queries=[Query.order_desc("$createdAt")] # Order by creation time
        )
        
        # The 'datas' field is a JSON string, so we need to parse it
        documents = []
        for doc in result['documents']:
            # Rename Appwrite's internal fields to match the old structure
            doc['id'] = doc.pop('$id')
            doc['timestamp'] = doc.pop('$createdAt')
            try:
                # Safely parse the 'datas' JSON string
                doc['datas'] = json.loads(doc['datas']) if doc.get('datas') else {}
            except json.JSONDecodeError:
                doc['datas'] = {} # Handle cases where string is not valid JSON
            
            # Remove other Appwrite internal fields
            doc.pop('$databaseId', None)
            doc.pop('$collectionId', None)
            doc.pop('$permissions', None)
            doc.pop('$updatedAt', None)

            documents.append(doc)

        return documents

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records from Appwrite: {str(e)}")

@health_data_router.post("/response")
async def send_response():
    return {
        "retCode": 1,
        "msg": "success",
        "control": 0
    } 
