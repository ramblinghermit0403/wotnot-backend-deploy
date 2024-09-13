import dramatiq
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dramatiq import Middleware
from ..models import Broadcast  # Adjust this import as needed based on your project structure
import requests
import json
from dramatiq.middleware import Middleware,SkipMessage
from fastapi import HTTPException


# SQLAlchemy Database Configuration
SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:Naveen1971$@my-db-instance.cv0mgo68yu9n.eu-north-1.rds.amazonaws.com/wotnot'
# SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:Denmarks123$@localhost/wati_clone'
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Function to get task status
def get_task_status(task_id: int, db: Session):
    """
    Fetches the status of a task based on the task_id from the database.
    """
    broadcast = db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.task_id == task_id).first()
    if broadcast:
        return broadcast.status
    
    return "unknown"

# Middleware to handle task cancellations
class CancelationMiddleware(Middleware):
    def before_process_message(self, broker, message):
        # Create a new database session
        db: Session = SessionLocal()
        print("run")
        try:
            task_id = message.message_id
            status = get_task_status(task_id, db)  # Pass the session directly
            if status == 'Cancelled':
                raise SkipMessage("Task has been canceled.")
        finally:
            db.close()  # Ensure the session is closed after use

# Add the middleware to your Dramatiq broker
from dramatiq.brokers.redis import RedisBroker

redis_broker = RedisBroker(url="redis://localhost:6379")
redis_broker.add_middleware(CancelationMiddleware())
dramatiq.set_broker(redis_broker)


@dramatiq.actor(max_retries=0)
def send_broadcast(template, recipients, API_url, headers,broadcast_id):
    """
    Dramatiq actor to send broadcast messages.
    """
    success_count = 0
    failed_count=0
    errors = []

    for recipient in recipients:
        data = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template,
                "language": {
                    "code": "en_US"
                }
            }
        }

        response = requests.post(API_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            success_count += 1
        else:
            failed_count += 1
            errors.append({"recipient": recipient, "error": response.json()})


    db: Session = SessionLocal()
    broadcast=db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.id == broadcast_id).first()

    if not broadcast:
        raise HTTPException(status_code=404,detail="Broadcast not found")

    if broadcast_id:
        broadcast.success=success_count
        broadcast.status="Successful"
        broadcast.failed=failed_count
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    
    if errors:
        print(f"Failed to send some messages: {errors}")
        raise Exception(f"Failed to send broadcast: {errors}")
    
    print(f"Successfully sent {success_count} messages.{errors.count}")

 