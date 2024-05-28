import json
import re
import uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from functions_framework import create_app

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()
 
app = create_app()

# CREATE USER ROUTE
@app.route('/create_user', methods=['POST'])
def create_user(request):
    body = request.get_json()

    full_name = body.get('full_name')
    mob_num = body.get('mob_num')
    pan_num = body.get('pan_num')
    manager_id = body.get('manager_id')

    # VALIDATION

    if not full_name:
        return (json.dumbs({
            "error":"Full name must not be empty"
        }), 400)
    
    if not re.match(r'^\+?0?91?\d{10}$', mob_num):
        return (json.dumbs({
            "error":"Invalid mobile number"
        }), 400)
    
    mob_num = re.sub(r'^\+?0?91?', '', mob_num)

    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_num.upper()):
        return (json.dumbs({
            "error":"Invalid PAN number"
        }), 400)

    pan_num = pan_num.upper()
 
    if manager_id:
        try:
            uuid.UUID(manager_id, version=4)
        except ValueError:
            return (json.dumps({
                "error":"Invalid manager_id "
            }),400)

    manager_ref = db.collection('managers').document(manager_id)
    manager = manager_ref.get()

    if not manager.exists:
        return (json.dumps({
                "error":"manager_id Not found"
            }),400)
    
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

    db.collection('Users').document(user_id).set(user_data)

    return (json.dumps({"message": "User created successfully", "user_id": user_id}), 200)
