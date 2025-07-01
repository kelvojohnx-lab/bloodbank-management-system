from flask import render_template, request, redirect, url_for, session, flash
from app import app
from app.firebase_config import auth, db
from datetime import datetime


@app.route('/')
def home():
    return render_template('home.html')

# ================= Admin Routes =================

@app.route('/admin')
def admin():
    if 'admin' in session:
        return redirect('/admin/dashboard')
    return redirect('/login/admin')

@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    error = None
    DEFAULT_ADMIN_EMAIL = "admin@muoki.com"
    DEFAULT_ADMIN_PASSWORD = "adm123"

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Default (hardcoded) admin login
        if email == DEFAULT_ADMIN_EMAIL and password == DEFAULT_ADMIN_PASSWORD:
            session['admin'] = email
            session['admin_token'] = "default_admin"  # Important for dashboard logic
            return redirect('/admin/dashboard')

        # Firebase-based admin login
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            user_id = user['localId']
            id_token = user['idToken']
            role = db.child("users").child(user_id).child("role").get(id_token).val()

            if role and role.lower() == "admin":
                session['admin'] = email
                session['token'] = id_token
                return redirect('/admin/dashboard')
            else:
                error = "Access denied: Not an admin."
        except Exception as e:
            print("❌ Firebase Login error:", e)
            error = "Invalid login credentials."

    return render_template('login_admin.html', error=error)


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/login/admin')

    try:
        is_default_admin = session['admin'] == 'admin@muoki.com'
        id_token = session.get('token')

        if not is_default_admin and not id_token:
            return redirect('/login/admin')

        # Retrieve Firebase snapshots
        donors_snapshot = db.child("donor_profiles").get() if is_default_admin else db.child("donor_profiles").get(id_token)
        users_snapshot = db.child("users").get() if is_default_admin else db.child("users").get(id_token)
        requests_snapshot = db.child("patient_requests").get() if is_default_admin else db.child("patient_requests").get(id_token)
        blood_stock_snapshot = db.child("blood_stock").get() if is_default_admin else db.child("blood_stock").get(id_token)

        # Initialize counters and data structures
        pending_requests_count = 0
        urgent_requests_count = 0
        critical_blood_types = set()
        recent_requests = []

        # Process patient requests
        patient_requests = []
        if requests_snapshot.each():
            for req in requests_snapshot.each():
                req_data = req.val()
                req_data['id'] = req.key()
                patient_requests.append(req_data)
                
                # Count pending requests
                if req_data.get("request_status", "").lower() == "pending":
                    pending_requests_count += 1
                
                # Count urgent requests and track critical blood types
                if req_data.get("urgency_status", "").lower() == "urgent":
                    urgent_requests_count += 1
                    critical_blood_types.add(req_data.get("blood_group", "").upper())
                
                # Track recent requests (last 5)
                if len(recent_requests) < 5:
                    recent_requests.append({
                        'name': req_data.get('patient_name', 'Unknown'),
                        'blood_group': req_data.get('blood_group', 'Unknown'),
                        'units_required': req_data.get('units_required', 0),
                        'date_requested': req_data.get('date_requested', 'N/A')
                    })

        # Process blood stock
        blood_stock = {}
        if blood_stock_snapshot and blood_stock_snapshot.val():
            blood_stock = blood_stock_snapshot.val()
        
        # Check critical stock levels
        for blood_type, units in blood_stock.items():
            if int(units) < 5:  # Consider less than 5 units as critical
                critical_blood_types.add(blood_type)

        # Build donors list
        donors = []
        if donors_snapshot.each():
            for donor in donors_snapshot.each():
                donor_data = donor.val()
                donor_data['id'] = donor.key()
                donors.append(donor_data)

        # Filter patients
        patients = []
        if users_snapshot.val():
            for key, user in users_snapshot.val().items():
                if user.get("role", "").lower() == "patient":
                    user['id'] = key
                    patients.append(user)

        return render_template(
            'admin_dashboard.html',
            donors=donors,
            patients=patients,
            patient_requests=patient_requests,
            donors_count=len(donors),
            patients_count=len(patients),
            pending_requests_count=pending_requests_count,
            urgent_requests_count=urgent_requests_count,
            critical_blood_types=list(critical_blood_types),
            recent_requests=recent_requests,
            blood_stock=blood_stock
        )

    except Exception as e:
        print("❌ Admin Dashboard Error:", e)
        return render_template(
            'admin_dashboard.html',
            donors=[], patients=[], patient_requests=[],
            donors_count=0, patients_count=0, 
            pending_requests_count=0,
            urgent_requests_count=0,
            critical_blood_types=[],
            recent_requests=[],
            blood_stock={}
        )

@app.route('/admin/blood_requests')
def admin_blood_requests():
    if 'admin' not in session:
        return redirect('/login/admin')

    token = session.get('token') or session.get('admin_token')
    if not token:
        return render_template("admin_blood_requests.html", patient_requests=[], error="Admin not authenticated")

    try:
        # Fetch requests and users
        requests_snapshot = db.child("patient_requests").get(token)
        users_snapshot = db.child("users").get(token)

        patient_requests = []
        
        if requests_snapshot.val():
            for req in requests_snapshot.each():
                request_data = req.val()
                patient_id = request_data.get('patient_id') or req.key()
                
                # Get patient info
                patient_info = {}
                if users_snapshot.val():
                    user_data = {}
                    users_val = users_snapshot.val()

                if users_val and patient_id in users_val:
                  user_data = users_val[patient_id]
                else:
                  print(f"⚠️ Patient ID {patient_id} not found in users database.")

                patient_info = {
                             'name': user_data.get('name', 'Unknown'),
                             'email': user_data.get('email', 'Unknown'),
                             'status': user_data.get('status', 'pending')
                            }


                # Structure data to match template
                enriched_request = {
                    "id": req.key(),
                    "name": patient_info.get('name'),
                    "email": patient_info.get('email'),
                    "blood_group": request_data.get("blood_group", "N/A"),
                    "units_required": request_data.get("units_required", "N/A"),
                    "reason": request_data.get("reason", "N/A"),
                    "date_requested": request_data.get("date_requested", "N/A"),
                    "urgency_status": request_data.get("urgency_status", "N/A"),
                    "request_status": request_data.get("request_status", patient_info.get('status', 'pending'))
                }
                patient_requests.append(enriched_request)

        return render_template("admin_blood_requests.html", 
                            patient_requests=patient_requests, 
                            error=None)

    except Exception as e:
        print("❌ Error loading blood requests:", e)
        return render_template("admin_blood_requests.html", 
                            patient_requests=[], 
                            error="Failed to load requests")

@app.route('/admin/blood_stock')
def blood_stock():
    if 'admin' not in session:
        return redirect('/login/admin')

    try:
        token = session.get('token') or session.get('admin_token')
        blood_stock_data = db.child("blood_stock").get(token)

        blood_stock = blood_stock_data.val() if blood_stock_data.val() else {}

        # Ensure all types are present (even if 0)
        all_blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        for bt in all_blood_types:
            if bt not in blood_stock:
                blood_stock[bt] = 0

        return render_template('blood_stock.html', blood_stock=blood_stock)

    except Exception as e:
        print("❌ Blood Stock Error:", e)
        return render_template('blood_stock.html', blood_stock={})








# ================= Patient Routes =================

@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']

        try:
            user = auth.create_user_with_email_and_password(email, password)
            login = auth.sign_in_with_email_and_password(email, password)
            user_id = login['localId']
            id_token = login['idToken']

            # Now include a status field for admin control
            db.child("users").child(user_id).set({
                "email": email,
                "name": name,
                "role": "patient",
                "status": "pending"  # Important for approval logic
            }, id_token)

            return redirect('/login/patient')

        except Exception as e:
            print("❌ Patient Registration error:", e)
            error = "Registration failed. Try again."

    return render_template('register_patient.html', error=error)


@app.route('/login/patient', methods=['GET', 'POST'])
def login_patient():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            user_id = user['localId']
            id_token = user['idToken']
            role = db.child("users").child(user_id).child("role").get(id_token).val()

            if role and role.lower() == "patient":
                session['patient'] = email
                session['patient_password'] = password
                session['token'] = id_token
                return redirect('/patient/profile')
            else:
                error = "Access denied: Not a patient."
        except Exception as e:
            print("❌ Patient Login error:", e)
            error = "Invalid login credentials."

    return render_template('login_patient.html', error=error)

from flask import request, redirect, render_template, session
from datetime import datetime
from app import app, db, auth  # Ensure auth and db are properly imported


@app.route('/patient/profile')
def patient_profile():
    try:
        if 'patient' not in session:
            return redirect('/login/patient')

        token = session.get('token')
        user = auth.get_account_info(token)
        user_id = user['users'][0]['localId']

        profile = db.child("patient_requests").child(user_id).get(token).val()
        return render_template("patient_profile.html", profile=profile)

    except Exception as e:
        print("❌ Patient profile error:", e)
        return render_template("patient_profile.html", error="Failed to load profile")


@app.route('/patient/submit', methods=['POST'])
def submit_patient_profile():
    try:
        if 'patient' not in session:
            return redirect('/login/patient')

        email = session['patient']
        token = session['token']
        user = auth.get_account_info(token)
        user_id = user['users'][0]['localId']

        profile_data = {
            "id": user_id,
            "name": request.form['name'],
            "gender": request.form['gender'],
            "dob": request.form['dob'],
            "age": request.form['age'],
            "blood_group": request.form['blood_group'],
            "contact_number": request.form['contact_number'],
            "email": request.form['email'],
            "emergency_contact": request.form['emergency_contact'],
            "medical_history": request.form['medical_history'],
            "current_medication": request.form['current_medication'],
            "last_transfusion": request.form['last_transfusion'],
            "num_transfusions": request.form['num_transfusions'],
            "transfusion_reason": request.form['transfusion_reason'],
            "allergies": request.form['allergies'],
            "conditions": request.form['conditions'],

            # New Fields
            "urgency_status": request.form['status'],  # Urgent or Not Urgent
            "date_requested": request.form['date_requested'],
            "reason": request.form['reason'],
            "units_required": request.form['units_required'],

            # Optional tracking field for admin
            "request_status": "pending",  # Admin can update to approved/rejected
            "submitted_at": datetime.now().isoformat()
        }

        db.child("patient_requests").child(user_id).set(profile_data, token)
        return redirect('/patient/profile')

    except Exception as e:
        print("❌ Error submitting patient profile:", e)
        return "Submission failed. Please try again."


# ================= Donor Routes =================

@app.route('/register/donor', methods=['GET', 'POST'])
def register_donor():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        blood_type = request.form['blood_type']

        try:
            user = auth.create_user_with_email_and_password(email, password)
            login = auth.sign_in_with_email_and_password(email, password)
            user_id = login['localId']
            id_token = login['idToken']

            db.child("users").child(user_id).set({
                "email": email,
                "name": name,
                "blood_type": blood_type,
                "role": "donor"
            }, id_token)

            return redirect('/login/donor')

        except Exception as e:
            print("❌ Donor Registration error:", e)
            error = "Registration failed. Try again."

    return render_template('register_donor.html', error=error)

@app.route('/login/donor', methods=['GET', 'POST'])
def login_donor():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            user_id = user['localId']
            id_token = user['idToken']
            role = db.child("users").child(user_id).child("role").get(id_token).val()

            if role and role.lower() == "donor":
                session['donor'] = email
                session['token'] = id_token
                return redirect('/donor/profile')
            else:
                error = "Access denied: Not a donor."
        except Exception as e:
            print("❌ Donor Login error:", e)
            error = "Invalid login credentials."

    return render_template('login_donor.html', error=error)
@app.route('/donor/profile')
def donor_profile():
    if 'donor' not in session:
        return redirect('/login/donor')

    try:
        token = session.get('token')
        user = auth.get_account_info(token)
        user_id = user['users'][0]['localId']

        profile = db.child("donor_profiles").child(user_id).get(token).val()

        return render_template("donor_profile.html", profile=profile)

    except Exception as e:
        print("❌ Donor profile error:", e)
        return render_template("donor_profile.html", error="Failed to load profile")


from datetime import datetime

@app.route('/donor/submit', methods=['POST'])
def submit_donor_profile():
    if 'donor' not in session:
        return redirect('/login/donor')

    try:
        token = session['token']
        user_info = auth.get_account_info(token)
        uid = user_info['users'][0]['localId']

        # Format the current date if not coming from form
        donation_date = request.form.get('donation_date') or datetime.today().strftime('%Y-%m-%d')
        unit = request.form.get('unit') or '0'

        donor_data = {
            "id": uid,
            "name": request.form['name'],
            "email": request.form['email'],
            "age": request.form['age'],
            "blood_type": request.form['blood_type'],
            "infections": request.form['infections'],
            "donation_date": donation_date,
            "unit": unit,
            "status": "available"
        }

        db.child("donor_profiles").child(uid).set(donor_data, token)
        return redirect('/donor/profile')

    except Exception as e:
        print("❌ Error submitting donor profile:", e)
        return "Submission failed. Try again."

    
@app.route('/admin/approve_donor/<donor_id>', methods=['POST'])
def approve_donor(donor_id):
    try:
        token = session.get('token') or session.get('admin_token')
        donor = db.child("donor_profiles").child(donor_id).get(token).val()
        if donor:
            blood_type = donor.get("blood_type", "").strip().upper()
            units = float(donor.get("unit", 0))

            db.child("donor_profiles").child(donor_id).update({"status": "approved"}, token)

            current_units = db.child("blood_stock").child(blood_type).get(token).val() or 0
            db.child("blood_stock").child(blood_type).set(float(current_units) + units, token)

            flash("Donor approved and stock updated.", "success")
        else:
            flash("Donor not found.", "error")
    except Exception as e:
        print("❌ Approve donor error:", e)
        flash("Failed to approve donor or update stock.", "error")

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject_donor/<donor_id>', methods=['POST'])
def reject_donor(donor_id):
    db.child("donor_profiles").child(donor_id).update({"status": "rejected"})
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/donations')
def admin_donations():
    if 'admin' not in session:
        return redirect('/login/admin')

    try:
        is_default_admin = session['admin'] == 'admin@muoki.com'
        id_token = session.get('token')

        if is_default_admin:
            donors_snapshot = db.child("donor_profiles").get()
        else:
            donors_snapshot = db.child("donor_profiles").get(id_token)

        approved_donors = []
        if donors_snapshot.each():
            for d in donors_snapshot.each():
                donor = d.val()
                donor['id'] = d.key()
                if donor.get('status', '').lower() == 'approved':
                    approved_donors.append(donor)

        return render_template('admin_donations.html', donors=approved_donors)

    except Exception as e:
        print("❌ Error fetching approved donors:", e)
        return render_template('admin_donations.html', donors=[])


@app.route('/admin/patient/approve/<patient_id>', methods=['POST'])
def approve_patient(patient_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    token = session.get('token') or session.get('admin_token')
    try:
        # Update patient status
        db.child("users").child(patient_id).update({
            "status": "approved"
        }, token)
        
        # Update any related blood requests
        requests = db.child("patient_requests").order_by_child("patient_id").equal_to(patient_id).get(token)
        if requests.each():
            for req in requests.each():
                db.child("patient_requests").child(req.key()).update({
                    "request_status": "approved"
                }, token)
        
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        print(f"Error approving patient {patient_id}:", e)
        return redirect(url_for('admin_dashboard'))
@app.route('/admin/patient/reject/<patient_id>', methods=['POST'])
def reject_patient(patient_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    token = session.get('token') or session.get('admin_token')
    try:
        # Update patient status
        db.child("users").child(patient_id).update({
            "status": "rejected"
        }, token)
        
        # Update any related blood requests
        requests = db.child("patient_requests").order_by_child("patient_id").equal_to(patient_id).get(token)
        if requests.each():
            for req in requests.each():
                db.child("patient_requests").child(req.key()).update({
                    "request_status": "rejected"
                }, token)
        
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        print(f"Error rejecting patient {patient_id}:", e)
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/blood_request/approve/<request_id>', methods=['POST'])
def approve_patient_request(request_id):
    try:
        if 'admin' not in session:
            return redirect(url_for('login_admin'))

        token = session.get('token') or session.get('admin_token')
        request_data = db.child("patient_requests").child(request_id).get(token).val()

        if not request_data:
            flash("Request not found.", "error")
            return redirect(url_for('admin_blood_requests'))

        blood_type = request_data.get("blood_group", "").strip().upper()
        units = float(request_data.get("units_required", 0))

        stock_units = db.child("blood_stock").child(blood_type).get(token).val() or 0

        if stock_units < units:
            flash(f"Insufficient stock for {blood_type}.", "error")
            return redirect(url_for('admin_blood_requests'))

        db.child("blood_stock").child(blood_type).set(round(stock_units - units, 2), token)
        db.child("patient_requests").child(request_id).update({"request_status": "approved"}, token)

        flash(f"{units} units of {blood_type} allocated. Request approved.", "success")

    except Exception as e:
        print("❌ Exception during approval:", e)
        flash("Unexpected error occurred. Please check logs.", "error")

    return redirect(url_for('admin_blood_requests'))




@app.route('/admin/blood_request/reject/<request_id>', methods=['POST'])
def reject_patient_request(request_id):
    if 'admin' not in session:
        return redirect(url_for('login_admin'))

    token = session.get('token') or session.get('admin_token')  # ✅ Define token here

    try:
        db.child("patient_requests").child(request_id).update({
            "request_status": "rejected"
        }, token)
        return redirect(url_for('admin_blood_requests'))
    except Exception as e:
        print(f"Error rejecting blood request {request_id}:", e)
        return redirect(url_for('admin_blood_requests'))




@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
