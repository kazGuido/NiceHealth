"""
Script to create the first admin user
Run this after starting the containers:
docker exec -it health_data_backend python create_admin.py
"""
import sys
import os
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import User
from app.auth import hash_pin, generate_pin
from app.email_service import send_pin_email
import asyncio
from datetime import datetime, timedelta

def create_admin():
    db = SessionLocal()
    try:
        email = input("Enter admin email: ").strip().lower()
        
        if not email:
            print("Email is required")
            return
        
        # Check if user already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User with email {email} already exists!")
            if existing.role == "admin":
                print("User is already an admin.")
            else:
                response = input("Promote to admin? (y/n): ")
                if response.lower() == 'y':
                    existing.role = "admin"
                    db.commit()
                    print(f"User {email} promoted to admin!")
            return
        
        # Generate PIN
        pin_code = generate_pin()
        pin_hash = hash_pin(pin_code)
        pin_expires = datetime.utcnow() + timedelta(minutes=10)
        
        # Create admin user
        admin_user = User(
            email=email,
            role="admin",
            pin_code=pin_hash,
            pin_expires_at=pin_expires,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"\n✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"PIN Code: {pin_code}")
        print(f"PIN expires in 10 minutes")
        print(f"\n⚠️  Save this PIN code! You'll need it to login.")
        
        # Try to send email
        try:
            email_sent = asyncio.run(send_pin_email(email, pin_code, is_registration=True))
            if email_sent:
                print(f"✅ PIN code sent to {email}")
            else:
                print(f"⚠️  Failed to send email. PIN code is: {pin_code}")
        except Exception as e:
            print(f"⚠️  Failed to send email: {e}")
            print(f"PIN code: {pin_code}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

