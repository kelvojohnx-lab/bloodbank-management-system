import os
import pyrebase
import json

# Read Firebase config from environment variable
firebase_config_json = os.environ.get("FIREBASE_CONFIG")
if firebase_config_json is None:
    raise Exception("FIREBASE_CONFIG environment variable not set!")

firebaseConfig = json.loads(firebase_config_json)

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()
