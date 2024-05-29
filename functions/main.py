import json
import re
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi import APIRouter
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore

# FIREBASE INITIALIZATION
cred = credentials.Certificate("daily-pe-firebase-adminsdk-36c2m-269b5fdbc7.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

# MODELS
class User(BaseModel):
    full_name: str
    mob_num: str
    pan_num: str
    manager_id: str = None

class UserUpdate(BaseModel):
    user_ids: list
    update_data: dict

class GetUser(BaseModel):
    user_id: str = None
    mob_num: str = None
    manager_id: str = None

class DeleteUser(BaseModel):
    user_id: str = None
    mob_num: str = None

# CREATE USER ROUTE
@app.post('/create_user')
async def create_user(user: User):
    full_name = user.full_name
    mob_num = user.mob_num
    pan_num = user.pan_num
    manager_id = user.manager_id

    # VALIDATION
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name must not be empty")

    if not re.match(r'^\+?0?91?\d{10}$', mob_num):
        raise HTTPException(status_code=400, detail="Invalid mobile number")

    mob_num = re.sub(r'^\+?0?91?', '', mob_num)

    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_num.upper()):
        raise HTTPException(status_code=400, detail="Invalid PAN number")

    pan_num = pan_num.upper()

    if manager_id:
        try:
            uuid.UUID(manager_id, version=4)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid manager_id")

        manager_ref = db.collection('managers').document(manager_id)
        manager = manager_ref.get()

        if not manager.exists:
            raise HTTPException(status_code=400, detail="manager_id Not found")

    # INSERT INTO FIRESTORE
    user_id = str(uuid.uuid4())
    user_data = {
        "user_id": user_id,
        "full_name": full_name,
        "mob_num": mob_num,
        "pan_num": pan_num,
        "manager_id": manager_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None,
        "is_active": True
    }

    db.collection('users').document(user_id).set(user_data)
    return {"message": "User created successfully", "user_id": user_id}

# GET USERS ROUTE


router = APIRouter()

@router.get('/get_users')
async def get_users():
    users_ref = db.collection('users')
    query = users_ref.where('is_active', '==', True)
    users = [doc.to_dict() for doc in query.stream()]
    return {"users": users}


# DELETE USER ROUTE
@app.post('/delete_user')
async def delete_user(user: DeleteUser):
    user_id = user.user_id
    mob_num = user.mob_num

    if not user_id and not mob_num:
        raise HTTPException(status_code=400, detail="Either user_id or mob_num must be provided")

    users_ref = db.collection('users')

    if user_id:
        user_doc = users_ref.document(user_id).get()
        if not user_doc.exists:
            raise HTTPException(status_code=400, detail="User not found")
        users_ref.document(user_id).delete()
    else:
        query = users_ref.where('mob_num', '==', mob_num).limit(1)
        user_doc = next(query.stream(), None)
        if not user_doc:
            raise HTTPException(status_code=400, detail="User not found")
        users_ref.document(user_doc.id).delete()

    return {"message": "User deleted successfully"}

# UPDATE USER ROUTE
@app.post('/update_user')
async def update_user(update: dict = Body(...)):
    user_id = update.get("user_id")
    update_data = update.get("update_data")

    if not user_id or not update_data:
        raise HTTPException(status_code=400, detail="Both user_id and update_data must be provided")

    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    # UPDATE
    user_ref.update(update_data)

    return {"message": "User updated successfully"}

app.include_router(router)
