from firebase_config import auth

# Replace with the actual admin email and password
email = "admin@gmail.com"
password = "adm123"

try:
    user = auth.sign_in_with_email_and_password(email, password)
    print("✅ Login successful!")
    print("User Info:", user)
except Exception as e:
    print("❌ Login failed!")
    print(e)
