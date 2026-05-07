from minio import Minio
import os
from datetime import timedelta
import uuid

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "health-data")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9002/health-data")

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)
    # Set public policy for the bucket
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}"]
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"]
            }
        ]
    }
    import json
    minio_client.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))

def upload_file(file_data, file_name, content_type):
    """Upload a file to MinIO and return the unique name (key)"""
    file_ext = os.path.splitext(file_name)[1]
    unique_name = f"{uuid.uuid4()}{file_ext}"
    
    minio_client.put_object(
        MINIO_BUCKET,
        unique_name,
        file_data,
        length=-1,
        part_size=10*1024*1024,
        content_type=content_type
    )
    
    # Return just the unique name, the backend will proxy it
    return unique_name

def get_file(file_name):
    """Get a file from MinIO"""
    try:
        response = minio_client.get_object(MINIO_BUCKET, file_name)
        return response
    except Exception:
        return None

