import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyDWjuSCRf5bFIYwCRY_jaCOxSrlu-JG3f4",
    "authDomain": "bloodbank-management-syetem.firebaseapp.com",
    "databaseURL": "https://bloodbank-management-syetem-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "bloodbank-management-syetem",
    "storageBucket": "bloodbank-management-syetem.appspot.com",
    "messagingSenderId": "685674388951",
    "appId": "1:685674388951:web:16c6ee2d60eecaf8d5ff92"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()
