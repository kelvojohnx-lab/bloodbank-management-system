from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey321")

# ✅ Import Firebase config
from app.firebase_config import auth, db

# ✅ Make routes work AFTER `auth` and `db` are loaded
from app import routes
