from fastapi import APIRouter,Depends,HTTPException, File, UploadFile,Request
from ..models import Broadcast,Contacts
from ..Schemas import broadcast,user
from ..database import database
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests
import json
from fastapi.responses import JSONResponse
import csv
import io
from ..oauth2 import get_current_user
from dramatiq import get_broker
from dramatiq import Message
from ..crud.template import send_template_to_whatsapp
from ..services import tasks
# Replace with your actual WhatsApp Business API endpoint and token


router=APIRouter( tags=['Broadcast'])

# access_token = "EAAXZCr1Or3lkBO9B0ZA84JDwoXgYd2BFqYA0Vn6BU2ZBk31OFEy3RPOwn68HWkabINs8y7OF2D2iDT5Uf8wwhcL51jlGANLZBUpGl26ezAAUM4f7pa3a80GUHVGQrP3n1z9dOGi54tZC3bXuK6kGcCsregUdZCl0y6c2oeBgRlw2ZBkSJFZCKuAtmbz1N9lk3uyZA5ZAU1KzXN1KZCeh1UJRgZDZD"
# BUSINESS_ACCOUNT_ID = '362091573648558'


# Broadcast 2 routes

@router.post("/send-template-message/")
async def send_template_message(request:broadcast.input_broadcast,get_current_user: user.newuser=Depends(get_current_user)):
    print(request)
    API_url=f"https://graph.facebook.com/v20.0/{get_current_user.Phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {get_current_user.PAccessToken}",
        "Content-Type": "application/json"
    }

    success_count = 0
    errors = []

    for recipient in request.recipients:
        data = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type":"template",
            "template": {
                "name": request.template,
                "language": {
                    "code": "en_US"
                }
            }
        }

        response = requests.post(API_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            success_count += 1
        else:
            errors.append({"recipient": recipient, "error": response.json()})
            
    
    
    return {
        "status": "completed",
        "successful_messages": success_count,
        "errors": errors
    }




# route for fetchlist in Broadcast template
@router.get("/templates")
def get_templates(get_current_user: user.newuser=Depends(get_current_user)):

    API_URL = f'https://graph.facebook.com/v15.0/{get_current_user.WABAID}/message_templates'
    headers = {
        'Authorization': f'Bearer {get_current_user.PAccessToken}'
    }

    response = requests.get(API_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    # Extract template names
    template_names = [template['name'] for template in data.get('data', [])]
    return JSONResponse(content=template_names)

# Route to create add broadcast in the list 
@router.post("/broadcast")
def broadcastList(request:broadcast.BroadcastListCreate,db: Session = Depends(database.get_db),get_current_user: user.newuser=Depends(get_current_user)):
    broadcastList=Broadcast.BroadcastList(
        user_id=get_current_user.id,
        name=request.name,
        template=request.template,
        contacts=request.contacts,
        type=request.type,
        success=request.success,
        failed=request.failed,
        status=request.status,
        scheduled_time=request.scheduled_time,
        task_id=request.task_id
    )
    db.add(broadcastList)
    db.commit()
    db.refresh(broadcastList)
    return{
        "broadcast_id":broadcastList.id
    } 

# Route to fetch the broadcastlist
@router.get('/broadcast')
def fetchbroadcastList(skip: int = 0, limit: int = 10, tag: str = None, db: Session = Depends(database.get_db),
                      get_current_user: user.newuser=Depends(get_current_user) ):
    broadcastList=db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.user_id==get_current_user.id).order_by(Broadcast.BroadcastList.id.desc()).all()
    return broadcastList
# Put route for the broadcastlist (rightnow primaryly used for updating the task_id )
@router.put("/broadcast/{broadcast_id}")
async def update_broadcast(broadcast_id: int, broadcast_update: broadcast.BroadcastListUpdate, db: Session = Depends(database.get_db),get_current_user: user.newuser=Depends(get_current_user)):
    # Retrieve the broadcast entry from the database
    broadcast = db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.id == broadcast_id).first()

    # If the broadcast entry does not exist, raise an HTTP 404 error
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    # Update the broadcast entry with new data
    if broadcast_update.task_id:
        broadcast.task_id = broadcast_update.task_id

    # Commit the changes to the database
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    # Return the updated broadcast entry
    return {"message": "Broadcast updated successfully", "broadcast_id": broadcast_id, "task_id": broadcast.task_id}


# Route to fetch the scheduled broadcastlist
@router.get("/scheduled-broadcast")
def fetchScheduledbroadcastList(skip: int = 0, limit: int = 10, tag: str = None, db: Session = Depends(database.get_db),
                      get_current_user: user.newuser=Depends(get_current_user) ):
    ScheduledbroadcastList=db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.status=="Scheduled").order_by(Broadcast.BroadcastList.id.desc()).all()
    return ScheduledbroadcastList

# Route to CSV import contacts in the broadcast form
@router.post("/import-contacts")
def import_contacts(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(contents))

    contacts = []
    for row in reader:
        contact = Contacts.Contact(name=row['name'], phone=row['phone'])
        contacts.append(contact)
       

    return {"contacts": contacts}
   
# Broadcast 1 routes

@router.get("/template")
def get_templates( get_current_user: user.newuser=Depends(get_current_user)):

    API_URL = f'https://graph.facebook.com/v15.0/{get_current_user.WABAID}/message_templates'
    headers = {
        'Authorization': f'Bearer {get_current_user.PAccessToken}'
    }

    response = requests.get(API_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()

    return data


@router.delete("/broadcasts-delete/{broadcast_id}")
async def delete_scheduled_broadcast(broadcast_id: str, db: Session = Depends(database.get_db),get_current_user: user.newuser=Depends(get_current_user)):
    # Fetch the broadcast
    broadcast = db.query(Broadcast.BroadcastList).filter(Broadcast.BroadcastList.id==broadcast_id).first()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # Update the status to 'canceled'
    broadcast.status = "Cancelled"
    db.commit()
    
    return {"detail": "Scheduled broadcast has been canceled."}



import logging

@router.post("/create-template", response_model=broadcast.TemplateResponse)
async def create_template(template: broadcast.TemplateCreate , request : Request , get_current_user: user.newuser=Depends(get_current_user)):
    try:
        template = await request.json()
        broadcast.TemplateCreate.validate_template(template)
        response = await send_template_to_whatsapp(template , get_current_user.PAccessToken , get_current_user.WABAID )
        return response
    except HTTPException as e:
        logging.critical(e)
        raise HTTPException(status_code=e.status_code, detail=e.detail)