

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from dramatiq import Message
from fastapi import APIRouter, Depends, HTTPException
from ..models import Broadcast
from ..Schemas import broadcast, user
from ..oauth2 import get_current_user
from .tasks import send_broadcast
from datetime import datetime, timezone
import pytz
from dramatiq import Actor
from dramatiq import Message
from dramatiq.middleware import Middleware,SkipMessage
from ..database import database
router = APIRouter()


# custom middleware to delete the task



@router.post("/schedule-template-message/")
async def schedule_template_message(
    request: broadcast.input,
    scheduled_time: str,
    get_current_user: user.newuser = Depends(get_current_user)
):
    """
    Endpoint to schedule a template message to be sent at a specified time.
    """
    API_url = f"https://graph.facebook.com/v20.0/{get_current_user.Phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {get_current_user.PAccessToken}",
        "Content-Type": "application/json"
    }

    # Convert 'scheduled_time' string to a datetime object
    try:
        scheduled_datetime = datetime.fromisoformat(scheduled_time).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601 format.")

    now = datetime.now(timezone.utc)  # Current time in UTC
    delay = (scheduled_datetime - now).total_seconds()

    if delay < 0:
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future.")

    # Schedule the task with the calculated delay and capture the task object
    task: Message = send_broadcast.send_with_options(
        args=[request.template, request.recipients, API_url, headers,request.broadcast_id],
        delay=delay * 1000  # delay is in milliseconds
    )
    
    # Return the message indicating the task was scheduled and include the task ID
    return {
        "message": f"Message {request.broadcast_id}scheduled to be sent at {scheduled_time}.",
        "task_id": task.message_id  # Access the message_id attribute to get the task ID
    }
