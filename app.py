import os
import re
import random
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import session
from datetime import datetime , timedelta
from flask_migrate import upgrade, Migrate, init
from flask_mail import Mail, Message

MAX_ATTEMPTS = 5
LOCK_TIME = timedelta(minutes=10)

app = Flask(__name__)
app.secret_key = "neologin_secret"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'yourgmail@gmail.com'  # replace with your Gmail
app.config['MAIL_PASSWORD'] = 'your_app_password'   # must be app password if 2FA enabled
app.config['MAIL_DEFAULT_SENDER'] = 'yourgmail@gmail.com'

mail = Mail(app)

def generate_otp():
    return str(random.randint(100000, 999999))  # 6-digit OTP

os.makedirs(app.instance_path, exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

ADMIN_EMAIL = "admin@neologin.com"
ADMIN_PASSWORD = "Admin@123"

users = {}

basedir = os.path.abspath(os.path.dirname(__file__))

# Database configuration - Use SQLite for Render (MySQL localhost won't work on Render)
# For production, use PostgreSQL by setting DATABASE_URL environment variable in Render
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render PostgreSQL - replace postgres:// with postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # SQLite fallback (works on Render)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "neologin.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    dob = db.Column(db.String(20))
    mobile = db.Column(db.String(10))
    email = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1024))
    is_admin = db.Column(db.Boolean, default=False)  # ✅ ADD ONLY THIS
    reported = db.Column(db.Boolean, default=False)  # ✅ NEW FIELD
    profile_photo = db.Column(db.String(255), default="default.png")
    gender = db.Column(db.String(10))  # New column
    failed_attempts = db.Column(db.Integer, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiration = db.Column(db.DateTime, nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reward = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="pending")  # e.g., pending, accepted, completed

    # Who created the task
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_tasks")

    # Who is assigned or accepted the task
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assignee = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")

    # Task tracking
    active_for_user = db.Column(db.Boolean, default=False)  # Currently active task for user
    completed = db.Column(db.Boolean, default=False)        # Completed task

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database with error handling
try:
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                first_name="Admin",
                last_name="User",
                dob="2000-01-01",
                mobile="9999999999",
                email=ADMIN_EMAIL,
                username="Admin_No.1",
                password=ADMIN_PASSWORD,
                is_admin=True,
                gender="Male"
            )
            db.session.add(admin)
            db.session.commit()

        # Load all users into memory
        all_users = User.query.all()
        for u in all_users:
            users[u.username] = {
                "first_name": u.first_name,
                "last_name": u.last_name,
                "dob": u.dob,
                "mobile": u.mobile,
                "email": u.email,
                "username": u.username,
                "password": u.password,
            }
        print(f"✅ Database initialized successfully. Loaded {len(users)} users.")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database: {e}")
    print(f"   The app will continue to run, but database features may not work.")
    print(f"   Currently using: {app.config['SQLALCHEMY_DATABASE_URI']}")
def calculate_age(dob_str):
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        return "INVALID_DOB"
    today = datetime.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# Home Page - Portfolio
@app.route("/")
def home():
    return render_template_string(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Hari Krishna T | Portfolio</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            /* GLOBAL STYLES */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: Arial, Helvetica, sans-serif;
            }

            html {
                scroll-behavior: smooth;
            }

            body {
                background-color: #f9f9f9;
                color: #333;
                line-height: 1.6;
            }

            /* HERO / HEADER */
            .hero {
                background: #1e293b;
                color: white;
                text-align: center;
                padding: 60px 20px;
            }

            .hero h1 {
                font-size: 2.5rem;
            }

            .hero h2 {
                font-weight: normal;
                margin-top: 10px;
            }

            .hero p {
                margin: 10px 0 20px;
            }

            .btn {
                display: inline-block;
                padding: 10px 20px;
                background: #38bdf8;
                color: #000;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                transition: background 0.3s;
            }

            .btn:hover {
                background: #0ea5e9;
            }

            /* SECTIONS */
            .section {
                max-width: 900px;
                margin: 80px auto;
                padding: 0 20px;
            }

            .section h3 {
                margin-bottom: 15px;
                border-bottom: 2px solid #38bdf8;
                display: inline-block;
                padding-bottom: 5px;
            }

            /* SKILLS */
            .skills {
                display: flex;
                gap: 40px;
                flex-wrap: wrap;
            }

            .skills ul {
                list-style: square;
                margin-left: 20px;
            }

            /* PROJECTS */
            .project {
                background: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.05);
                margin-top: 20px;
            }

            .project-link {
                display: inline-block;
                margin-top: 10px;
                margin-right: 10px;
                padding: 8px 14px;
                background: #38bdf8;
                color: #000;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
                transition: background 0.3s;
            }

            .project-link:hover {
                background: #0ea5e9;
            }

            /* FOOTER */
            footer {
                text-align: center;
                padding: 20px;
                background: #1e293b;
                color: white;
                margin-top: 40px;
            }

            .section a {
                color: #38bdf8;
                text-decoration: none;
            }

            .section a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>

        <!-- HERO / HEADER -->
        <header class="hero">
            <h1>Hari Krishna T</h1>
            <h2>Web Development Intern</h2>
            <p>Web Developer</p>
            <a href="#projects" class="btn">View Projects</a>
        </header>

        <!-- ABOUT ME SECTION -->
        <section class="section">
            <h3>About Me</h3>
            <p>
                I am a Web Development Intern with hands-on experience in building web applications using Python and Flask.
                I focus on creating structured backend logic, authentication systems, and database-driven applications.
                I am actively improving my skills in full-stack development and writing clean, maintainable code.
            </p>
        </section>

        <!-- SKILLS SECTION -->
        <section class="section">
            <h3>Skills</h3>
            <div class="skills">
                <div>
                    <h4>Frontend</h4>
                    <ul>
                        <li>HTML</li>
                        <li>CSS</li>
                    </ul>
                </div>

                <div>
                    <h4>Backend</h4>
                    <ul>
                        <li>Python</li>
                        <li>Flask</li>
                        <li>MySQL</li>
                    </ul>
                </div>

                <div>
                    <h4>Tools</h4>
                    <ul>
                        <li>VS Code</li>
                    </ul>
                </div>
            </div>
        </section>

        <!-- PROJECTS SECTION -->
        <section class="section" id="projects">
            <h3>Projects</h3>
            <div class="project">
                <h4>Task Management & Reward Platform</h4>
                <p>
                    A web-based platform where users can create accounts, sign in,
                    and manage tasks by assigning or accepting them for rewards.
                    The system includes admin management features.
                </p>
                <p><strong>Technologies:</strong> Python, Flask, MySQL</p>
                <p><strong>Status:</strong> Under Development</p>

                <a href="{{ url_for('signup') }}" class="project-link">
                   View Live Website
                </a>
                <a href="https://github.com/Twilight007-2/Task-Management-Website" target="_blank" class="project-link">
                   View Project Code
                </a>
            </div>
        </section>

        <!-- CONTACT SECTION -->
        <section class="section">
            <h3>Contact</h3>
            <p>Email: <a href="mailto:swamythk07@gmail.com">swamythk07@gmail.com</a></p>
        </section>

        <!-- FOOTER -->
        <footer>
            <p>© 2025 Hari Krishna T</p>
        </footer>

    </body>
    </html>
    """)

# Sign Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    message = ""
    clear_mobile = False
    clear_email = False
    clear_password = False
    clear_username = False
    clear_dob = False
    clear_fname = False
    clear_lname = False
    
    if request.method == "POST":
        fname = request.form.get("first_name", "").strip()
        lname = request.form.get("last_name", "").strip()
        dob = request.form.get("dob", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        photo = request.files.get("profile_photo")
        gender = request.form.get("gender")  # New line
        filename = "default.png"

        if photo and photo.filename != "":
            filename = f"{username}_{photo.filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$'
        mobile_pattern = r'^[6-9]\d{9}$'
        mobile_exists = any(u["mobile"] == mobile for u in users.values())
        email_exists = any(u["email"] == email for u in users.values())

        if not (fname and lname and dob and mobile and email and username and password and confirm_password):
            message = "All fields are required"
        elif not re.match(mobile_pattern, mobile):
            message = "Mobile number must be 10 digits and start with 6, 7, 8, or 9"
            clear_mobile = True
        elif mobile_exists and email_exists:
            message = "Mobile number and Email ID already exist"
            clear_email = True
            clear_mobile = True
        elif mobile_exists:
            message = "Mobile number already exists"
            clear_mobile = True
        elif email_exists:
            message = "Email ID already exists"
            clear_email = True
        elif not re.match(pattern, password):
            message = "Password does not meet all requirements"
            clear_password = True
        elif password != confirm_password:
            message = "Passwords do not match"
            clear_password = True
        else:
            new_user = User(
                first_name=fname,
                last_name=lname,
                dob=dob,
                mobile=mobile,
                email=email,
                username=username,
                password=password,
                profile_photo=filename,
                gender=gender, # save in DB
                failed_attempts = 0,
                lock_until = None
            )

            db.session.add(new_user)
            db.session.commit()

            users[username] = {
                "first_name": fname,
                "last_name": lname,
                "dob": dob,
                "mobile": mobile,
                "email": email,
                "username": username,
                "password": password,
                "gender": gender,  # store in dictionary
                
            }
            return redirect(url_for('signin'))

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sign Up - NeoLogin</title>
        <style>
            *{
                box-sizing: border-box;
            }
            input:focus {
                outline: none;
                border: 2px solid #6f42c1;
                box-shadow: 0 0 6px rgba(111,66,193,0.4);
            }
            button:hover {
                opacity: 0.92;
                transform: translateY(-1px);
            }
            button {
                transition: all 0.2s ease;
            }
            body {
                animation: pageFade 0.4s ease;
            }
            @keyframes pageFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            body { font-family: Chiller, sans-serif; margin:0; padding:0; 
                   background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                   background-size: cover; background-position: center; }
            .overlay { background-color: rgba(255,255,255,0.65); min-height: 100vh; 
                       display:flex; flex-direction: column; align-items:center; justify-content:center; padding:20px;}
            .box { background:#f9f9f9; padding:40px; border-radius:8px; width:400px; }
            form { display:flex; flex-direction: column; }
            .row { display:flex; gap:10px; }
            input { padding:8px; margin-bottom:10px; flex:1; box-sizing:border-box; width:100%; }
            button { width:100%; padding:12px; font-size:16px; border:none; border-radius:5px; cursor:pointer; background-color:#ff7f50; color:white;}
            .msg { color:red; text-align:center; margin-top:10px; }
            .msg {background: #ffe6e6;padding: 10px;border-radius: 8px;font-weight: bold;}
            label { font-weight:bold; margin-bottom:3px; }
            .password-rules { font-size: 13px; margin-bottom: 10px; }
            .password-rules li { margin-bottom: 5px; color:red; transition: all 1s ease; }
            .password-container { position: relative; width:100%; }
            .password-container input { padding-right:35px; width:100%; }
            .eye { position:absolute; right:10px; top:50%; transform:translateY(-50%); cursor:pointer; font-size:18px; }
        </style>
        <script>
            function checkPassword() {
                var pwd = document.getElementById("password").value;
                var rules = [
                    {regex: /.{8,}/, id: "length"},
                    {regex: /[A-Z]/, id: "uppercase"},
                    {regex: /[a-z]/, id: "lowercase"},
                    {regex: /[0-9]/, id: "number"},
                    {regex: /[@$!%*#?&]/, id: "special"}
                ];
                rules.forEach(function(rule) {
                    var el = document.getElementById(rule.id);
                    if(rule.regex.test(pwd)) {
                        el.style.color = "green";
                        setTimeout(() => { el.style.display = "none"; }, 1500);
                    } else {
                        el.style.display = "list-item";
                        el.style.color = "red";
                    }
                });
            }
            function togglePassword(id, eyeId) {
                var pwd = document.getElementById(id);
                var eye = document.getElementById(eyeId);
                if(pwd.type === "password") {
                    pwd.type = "text";
                    eye.textContent = "👀";
                } else {
                    pwd.type = "password";
                    eye.textContent = "🛡️";
                }
            }
            window.onload = function() {
                document.getElementById("eye1").textContent = "🛡️";
                document.getElementById("eye2").textContent = "🛡️";
                // Mobile & Email validation
                const mobileInput = document.getElementById('mobile');
                const emailInput = document.querySelector('input[name="email"]');
                const existingEmails = {{ users.values() | map(attribute='email') | list | tojson }};
                mobileInput.addEventListener('blur', function() {
                    const mobilePattern = /^[6-9]\d{9}$/;
                    if (!mobilePattern.test(mobileInput.value) && mobileInput.value.length > 0) {
                        alert("Mobile number must be 10 digits and start with 6, 7, 8, or 9");
                        mobileInput.value = "";
                        mobileInput.focus();
                    }
                });
                emailInput.addEventListener('blur', function() {
                    const emailVal = emailInput.value.trim();
                    if (existingEmails.includes(emailVal)) {
                        alert("This Email ID is already registered!");
                        emailInput.value = "";
                        emailInput.focus();
                    }
                });
                // Prevent typing in DOB field - only allow calendar selection
                const dobInput = document.getElementById('dob');
                if (dobInput) {
                    dobInput.addEventListener('keydown', function(e) {
                        // Allow arrow keys, tab, and delete for navigation
                        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Tab', 'Delete', 'Backspace'].includes(e.key)) {
                            e.preventDefault();
                            return false;
                        }
                    });
                    dobInput.addEventListener('keypress', function(e) {
                        e.preventDefault();
                        return false;
                    });
                    dobInput.addEventListener('paste', function(e) {
                        e.preventDefault();
                        return false;
                    });
                }
            };
        </script>
    </head>
    <body>
        <div class="overlay">
            <div class="box">
                <h3>Sign Up</h3>
                <form method="POST" enctype="multipart/form-data" >
                    <div class="row">
                        <div>
                            <label>First Name</label>
                            <input type="text" name="first_name" placeholder="First Name" value="{{ '' if clear_fname else request.form.get('first_name','') }}" required>
                        </div>
                        <div>
                            <label>Last Name</label>
                            <input type="text" name="last_name" placeholder="Last Name" value="{{ '' if clear_lname else request.form.get('last_name','') }}" required>
                        </div>
                    </div>
                    <label>Profile Photo</label>
                    <input type="file" name="profile_photo" accept="image/*">
                    <label>Date of Birth</label>
                    <input type="date" name="dob" id="dob" value="{{ '' if clear_dob else request.form.get('dob','') }}" min="1900-01-01" max="2024-12-31" required onkeydown="return false;" onpaste="return false;">     
                    <label for="gender">Gender:</label>
                    <select name="gender" id="gender" required style="margin-bottom:15px;">
                        <option value="" disabled selected>Select your gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                    </select>
                    <label>Mobile Number</label>
                    <input type="text" id="mobile" name="mobile" placeholder="Mobile Number"
       value="{{ '' if clear_mobile else request.form.get('mobile','') }}" required>
                    <label>Email ID</label>
                    <input type="email" name="email" placeholder="Email ID"
        value="{{ '' if clear_email else request.form.get('email','') }}" required>
                    <label>Username</label>
                    <input type="text" name="username" placeholder="Username" value="{{ '' if clear_username else request.form.get('username','') }}" required>
                    <label>Password</label>
                    <div class="password-container">
                       <input type="password" id="password" name="password" placeholder="Password"
        value="{{ '' if clear_password else request.form.get('password','') }}"
        required onkeyup="checkPassword()">
                        <span class="eye" id="eye1" onclick="togglePassword('password','eye1')">🛡️</span>
                    </div>
                    <ul class="password-rules">
                        <li id="length">At least 8 characters</li>
                        <li id="uppercase">At least one uppercase letter</li>
                        <li id="lowercase">At least one lowercase letter</li>
                        <li id="number">At least one number</li>
                        <li id="special">At least one special character (@$!%*#?&)</li>
                    </ul>
                    <label>Confirm Password</label>
                    <div class="password-container">
                        <input type="password" id="confirm_password" name="confirm_password" placeholder="Confirm Password"
        value="{{ '' if clear_password else request.form.get('confirm_password','') }}"
        required>
                        <span class="eye" id="eye2" onclick="togglePassword('confirm_password','eye2')">🛡️</span>
                    </div>
                    <button type="submit">Register</button>
                </form>
                <div class="msg">{{ message }}</div>
            </div>
        </div>
    </body>
    </html>
    """, message=message, clear_mobile=clear_mobile, clear_email=clear_email, clear_password=clear_password,
       clear_dob=clear_dob, clear_fname=clear_fname, clear_lname=clear_lname, clear_username=clear_username,
       users=users)


# Sign In Page
@app.route("/signin", methods=["GET", "POST"])
def signin():
    message = ""

    if session.get("logged_in"):
        email = session.get("user_email")
        return render_template_string(r"""
        <script>
            alert("You are already logged in. Please logout first to access Sign In.");
            window.location.href = "{{ url_for('dashboard', email=email) }}";
        </script>
        """, email=email)

    if request.method == "POST":

        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter(
            (User.email == identifier) | (User.mobile == identifier)
        ).first()

        if user:
            # 1️⃣ Check if account is locked
            if user.lock_until and datetime.utcnow() < user.lock_until:
                remaining = user.lock_until - datetime.utcnow()
                minutes, seconds = divmod(remaining.seconds, 60)
                message = f"Account locked. Try again in {minutes}m {seconds}s"
                return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Locked - NeoLogin</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin:0; padding:0;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover; background-position: center;
            }
            .overlay {
                background-color: rgba(255,255,255,0.8);
                min-height:100vh;
                display:flex;
                flex-direction: column;
                align-items:center;
                justify-content:center;
                padding:20px;
            }
            .box {
                background:#f9f9f9;
                padding:40px;
                border-radius:10px;
                width:400px;
                text-align:center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }
            h2 { color:#c0392b; margin-bottom:20px; }
            p { font-size:16px; color:#333; }
            a {
                display:inline-block;
                margin-top:20px;
                padding:10px 20px;
                background:#6f42c1;
                color:white;
                text-decoration:none;
                border-radius:5px;
                transition:0.2s;
            }
            a:hover { background:#5931a0; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="box">
                <h2>Account Locked!</h2>
                <p>{YOU HAVE TRIED THE WRONG PASSWORD FOR TOO MANY TIMES WAIT FOR 10 MINS AND COOL UR HEAD BRO !!!!}</p>
                <a href="{{ url_for('signin') }}">Back to Sign In</a>
            </div>
        </div>
    </body>
    </html>
    """, message=message)
            # 2️⃣ Password check
            if user.password == password:
                # ✅ Successful login
                user.failed_attempts = 0
                user.lock_until = None
                db.session.commit()

                session['logged_in'] = True
                session['user_email'] = user.email
                session['is_admin'] = user.is_admin

                if user.is_admin and user.reported:
                    session["show_admin_warning"] = True

                if user.is_admin:
                    return redirect(url_for('admin_menu'))
                else:
                    return redirect(url_for('dashboard', email=user.email))

            else:
                # 3️⃣ Failed login attempt
                user.failed_attempts += 1
                if user.failed_attempts >= MAX_ATTEMPTS:
                    user.lock_until = datetime.utcnow() + LOCK_TIME
                    message = f"Too many failed attempts. Account locked for {LOCK_TIME.seconds // 60} minutes."
                else:
                    remaining = MAX_ATTEMPTS - user.failed_attempts
                    message = f"Invalid password. {remaining} attempts remaining."
                db.session.commit()

        else:
            message = "Invalid email/mobile or password"

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sign In - NeoLogin</title>
        <style>
            *{
                box-sizing: border-box;
            }
            input:focus {
                outline: none;
                border: 2px solid #6f42c1;
                box-shadow: 0 0 6px rgba(111,66,193,0.4);
            }
            button:hover {
                opacity: 0.92;
                transform: translateY(-1px);
            }
            button {
                transition: all 0.2s ease;
            }
            body {
                animation: pageFade 0.4s ease;
            }
            @keyframes pageFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }                      
            body { font-family: Arial, sans-serif; margin:0; padding:0;
                   background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                   background-size: cover; background-position: center; }
            .overlay { background-color: rgba(255,255,255,0.65); min-height:100vh; display:flex; flex-direction: column; align-items:center; justify-content:center; padding:20px; }
            .box { background:#f9f9f9; padding:40px; border-radius:8px; width:350px; }
            .password-container { position:relative; width:100%; }
            .password-container input { padding-right:35px; width:100%; }
            .eye { position:absolute; right:10px; top:50%; transform:translateY(-50%); cursor:pointer; font-size:18px; }
            input { width:100%; padding:8px; margin:5px 0 10px 0; box-sizing:border-box; }
            button { width:100%; padding:12px; font-size:16px; border:none; border-radius:5px; cursor:pointer; background-color:#6f42c1; color:white; }
            .msg { margin-top:15px; text-align:center; color:red; }
        </style>
        <script>
            function togglePassword(id, eyeId) {
                var pwd = document.getElementById(id);
                var eye = document.getElementById(eyeId);
                if (pwd.type === "password") {
                    pwd.type = "text";
                    eye.textContent = "👀";
                } else {
                    pwd.type = "password";
                    eye.textContent = "🛡️";
                }
            }
            window.onload = function() { document.getElementById("eye").textContent = "🛡️"; };
            .auth-actions {
                width: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            /* Divider */
            .divider {
                width: 100%;
                display: flex;
                align-items: center;
                margin: 18px 0;
                color: #777;
                font-size: 14px;
            }
            .divider::before,
            .divider::after {
                content: "";
                flex: 1;
                border-bottom: 1px solid #ccc;
            }
            .divider span {
                padding: 0 12px;
                white-space: nowrap;
            }
            /* Signup button */
            .signup-btn {
                width: 100%;
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
                text-align: center;
                background-color: #fff;
                color: #6f42c1;
                border: 2px solid #6f42c1;
                font-weight: bold;
                text-decoration: none;
                transition: all 0.2s ease;
            }
            .signup-btn:hover {
                background-color: #6f42c1;
                color: white;
            }
        </script>
    </head>
    <body>
        <div class="overlay">
            <div class="box">
                <h3>Sign In</h3>
                <form method="POST" autocomplete="off">
                    <input type="text" name="identifier" placeholder="Email or Mobile Number" required>
                    <div class="password-container">
                        <input type="password" id="password" name="password" placeholder="Password" autocomplete="new-password" required>
                        <span class="eye" id="eye" onclick="togglePassword('password','eye')">🛡️</span>
                    </div>
                        <button type="submit">Login</button>      
                        <div class="divider">
                            <span>-----------------------OR-----------------------</span>
                        </div>
                        <!-- ✅ NEW SIGN UP BUTTON -->
                        <a href="{{ url_for('signup') }}" style="text-decoration:none;">
                            <button type="button" class="signup-btn">Create New Account</button>
                        </a>
                            <p style="margin-top:12px; text-align:center;">
                            <a href="{{ url_for('forgot_password') }}"
                            style="color:#6f42c1; font-weight:bold; text-decoration:none;">
                            Forgot password?
                            </a>
                        </div>
                    </p>
                </form>
                <div class="msg">{{ message }}</div>
            </div>
        </div>
    </body>
    </html>
    """, message=message)
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template_string(r"""
                <script>
                    alert("User not found!");
                    window.location.href = "/forgot-password";
                </script>
            """)

        import pytz
        from datetime import datetime, timedelta

        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)

        # Check lock
        if user.lock_until:
            lock_until_ist = user.lock_until.astimezone(ist) if user.lock_until.tzinfo else ist.localize(user.lock_until)
            if now_ist < lock_until_ist:
                return render_template_string(r"""
                    <script>
                        alert("Too many reset attempts. Try again after 10 minutes.");
                        window.location.href = "/forgot-password";
                    </script>
                """)
            else:
                # Lock expired → reset
                user.failed_attempts = 0
                user.lock_until = None
                db.session.commit()

        # ✅ Generate OTP
        import random
        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.otp_expiration = datetime.now() + timedelta(minutes=5)
        db.session.commit()

        # ✅ Save email and password in session for verification
        session['reset_email'] = user.email

        # ✅ OTP prompt via JavaScript
        return render_template_string(f"""
            <script>
                var otp = prompt("Your OTP is: {otp}. Please enter it to verify:");
                if (otp) {{
                    // Redirect to verify-otp route with OTP as query param
                    window.location.href = "/verify-otp?entered_otp=" + otp;
                }} else {{
                    alert("OTP entry cancelled.");
                    window.location.href = "/forgot-password";
                }}
            </script>
        """)

    # GET request → show email input form
    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Forgot Password - NeoLogin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover; background-position: center; }
            .overlay { background-color: rgba(255,255,255,0.4); min-height: 100vh;
                display: flex; align-items: center; justify-content: center; }
            .card { background: white; padding: 40px 50px; border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 100%; max-width: 400px;
                animation: fadeIn 0.5s ease; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } 
                to { opacity: 1; transform: translateY(0); } }
            h2 { text-align: center; margin-bottom: 25px; color: #333; }
            input { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px;
                border: 1px solid #ccc; font-size: 15px; }
            input:focus { outline: none; border: 2px solid #6f42c1;
                box-shadow: 0 0 6px rgba(111,66,193,0.4); }
            button { width: 100%; padding: 12px; background-color: #6f42c1; color: white;
                border: none; border-radius: 8px; font-size: 16px; font-weight: bold;
                cursor: pointer; transition: all 0.2s ease; }
            button:hover { background-color: #532d91; transform: translateY(-1px); }
            .back-link { text-align: center; margin-top: 15px; }
            .back-link a { text-decoration: none; color: #6f42c1; font-weight: bold; }
            .back-link a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="card">
                <h2>Forgot Password</h2>
                <form method="POST">
                    <input type="email" name="email" placeholder="Enter your email" required>
                    <button type="submit">Send OTP</button>
                </form>
                <div class="back-link">
                    <a href="/signin">Back to Sign In</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    import re
    from datetime import datetime

    email = session.get("reset_email")
    if not email:
        return redirect("/forgot-password")

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect("/forgot-password")

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$'

        if user.otp != otp:
            return render_template_string(r"""
                <script>
                    alert("Invalid OTP!");
                    window.location.href = "/verify-otp";
                </script>
            """)

        if datetime.now() > user.otp_expiration:
            return render_template_string(r"""
                <script>
                    alert("OTP expired!");
                    window.location.href = "/forgot-password";
                </script>
            """)

        if not re.match(pattern, password):
            return render_template_string(r"""
                <script>
                    alert("Password does not meet requirements!");
                    window.location.href = "/verify-otp";
                </script>
            """)

        if password != confirm_password:
            return render_template_string(r"""
                <script>
                    alert("Passwords do not match!");
                    window.location.href = "/verify-otp";
                </script>
            """)

        # Update password
        user.password = password
        user.otp = None
        user.otp_expiration = None
        db.session.commit()

        session.pop("reset_email", None)

        return render_template_string(r"""
            <script>
                alert("Password updated successfully!");
                window.location.href = "/signin";
            </script>
        """)

    return render_template_string(r"""
<!DOCTYPE html>
<html>
<head>
    <title>Verify OTP - NeoLogin</title>
    <style>
        body {
            font-family: Chiller, sans-serif;
            margin: 0;
            padding: 0;
            background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
            background-size: cover;
            background-position: center;
        }
        .overlay {
            background-color: rgba(255,255,255,0.65);
            min-height: 100vh;
            display:flex;
            align-items:center;
            justify-content:center;
        }
        .box {
            background:#f9f9f9;
            padding:40px;
            border-radius:8px;
            width:400px;
        }
        input {
            width:100%;
            padding:8px;             
            margin:8px 0;            
            border-radius:6px;
            border:1px solid #ccc;
            font-size:14px;          
        }
        button {
            width:100%;
            padding:12px;
            font-size:16px;
            border:none;
            border-radius:5px;
            background:#ff7f50;
            color:white;
            cursor:pointer;
        }
        .password-rules {
            font-size:13px;
            margin-bottom:10px;
        }
        .password-rules li {
            color:red;
            transition: all 1s ease;
        }
        .password-container {
            position: relative;
            width:100%;
        }
        .password-container input {
            padding: 8px 35px 8px 8px;   /* SAME size as OTP */
            box-sizing: border-box;
        }
        .eye {
            position:absolute;
            right:10px;
            top:50%;
            transform:translateY(-50%);
            cursor:pointer;
            font-size:18px;
        }
    </style>

    <script>
        function checkPassword() {
            var pwd = document.getElementById("password").value;
            var rules = [
                {regex: /.{8,}/, id: "length"},
                {regex: /[A-Z]/, id: "uppercase"},
                {regex: /[a-z]/, id: "lowercase"},
                {regex: /[0-9]/, id: "number"},
                {regex: /[@$!%*#?&]/, id: "special"}
            ];
            rules.forEach(function(rule) {
                var el = document.getElementById(rule.id);
                if(rule.regex.test(pwd)) {
                    el.style.color = "green";
                    setTimeout(() => { el.style.display = "none"; }, 1500);
                } else {
                    el.style.display = "list-item";
                    el.style.color = "red";
                }
            });
        }

        function togglePassword(id, eyeId) {
            var pwd = document.getElementById(id);
            var eye = document.getElementById(eyeId);
            if(pwd.type === "password") {
                pwd.type = "text";
                eye.textContent = "👀";
            } else {
                pwd.type = "password";
                eye.textContent = "🛡️";
            }
        }

        window.onload = function() {
            document.getElementById("eye1").textContent = "🛡️";
            document.getElementById("eye2").textContent = "🛡️";
        };
    </script>
</head>

<body>
<div class="overlay">
    <div class="box">
        <h3>Verify OTP</h3>
        <form method="POST">
            <input type="text" name="otp" placeholder="Enter OTP" required>

            <label>New Password</label>
            <div class="password-container">
                <input type="password" id="password" name="password" required onkeyup="checkPassword()">
                <span class="eye" id="eye1" onclick="togglePassword('password','eye1')">🛡️</span>
            </div>

            <ul class="password-rules">
                <li id="length">At least 8 characters</li>
                <li id="uppercase">At least one uppercase letter</li>
                <li id="lowercase">At least one lowercase letter</li>
                <li id="number">At least one number</li>
                <li id="special">At least one special character (@$!%*#?&)</li>
            </ul>

            <label>Confirm Password</label>
            <div class="password-container">
                <input type="password" id="confirm_password" name="confirm_password" required>
                <span class="eye" id="eye2" onclick="togglePassword('confirm_password','eye2')">🛡️</span>
            </div>

            <button type="submit">Reset Password</button>
        </form>
    </div>
</div>
</body>
</html>
""")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    from werkzeug.security import generate_password_hash

    s = URLSafeTimedSerializer(app.secret_key)

    try:
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except SignatureExpired:
        return "The reset link has expired."
    except BadSignature:
        return "Invalid reset link."

    user = User.query.filter_by(email=email).first()
    if not user:
        return "Invalid user."

    if request.method == "POST":
        new_password = request.form.get("password").strip()
        confirm_password = request.form.get("confirm_password").strip()

        if new_password != confirm_password:
            return "Passwords do not match."

        # 🔹 Hash the password
        hashed_password = generate_password_hash(new_password, method="sha256")

        # 🔹 Update the DB
        user.password = hashed_password
        db.session.commit()   # ← THIS IS THE CRUCIAL LINE

        # Optional: update in-memory dictionary if you maintain one
        if user.username in users:
            users[user.username]["password"] = hashed_password

        return redirect(url_for("signin"))  # or show success message

    return render_template_string(r"""
        <form method="POST">
            New Password: <input type="password" name="password" required><br>
            Confirm Password: <input type="password" name="confirm_password" required><br>
            <button type="submit">Reset Password</button>
        </form>
    """)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('signin'))

@app.route("/make-admin/<int:user_id>")
def make_admin(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = User.query.get(user_id)
    if user:
        user.is_admin = True
        db.session.commit()

    return redirect(url_for("view_users"))

# Dashboard/Profile Page
@app.route("/dashboard/<email>")
def dashboard(email):
    # Find the user by email
    user_found = None
    for u in users.values():
        if u["email"] == email:
            user_found = u
            break

    if not user_found:
        return redirect(url_for('signin'))

    user = user_found

    age = calculate_age(user["dob"])
    if age == "INVALID_DOB":
        return render_template_string(r"""
            <script>
                alert("Your DOB is wrong. Please update it.");
                window.location.href = "/edit-profile";
            </script>
        """)

    full_name = f"{user['first_name']} {user['last_name']}"

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - NeoLogin</title>
        <style>                     
            form input[type="file"] {
                margin-top: 10px;
                display: block;
            }
            form button {
                margin-top: 10px;
                padding: 6px 15px;
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }
            form button:hover {
                background-color: #532d91;
            }
            .profile-pic {
                width: 120px;
                height: 120px;
                border-radius: 50%; /* makes it circular */
                object-fit: cover;
                margin-bottom: 20px;
                border: 3px solid #6f42c1; /* optional colored border */
            }
            *{
                box-sizing: border-box;
            }
            input:focus {
                outline: none;
                border: 2px solid #6f42c1;
                box-shadow: 0 0 6px rgba(111,66,193,0.4);
            }
            button:hover {
                opacity: 0.92;
                transform: translateY(-1px);
            }
            button {
                transition: all 0.2s ease;
            }
            .info p b {
                color: #6f42c1;
            }
            .dashboard {
                animation: fadeIn 0.6s ease;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            body {
                animation: pageFade 0.4s ease;
            }
            @keyframes pageFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            body { 
                font-family: Arial,sans-serif; 
                margin:0; padding:0; 
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover; 
                background-position: center; 
            }
            .overlay { 
                background-color: rgba(255,255,255,0.4); 
                min-height:100vh; 
                display:flex; 
                flex-direction: column; 
                align-items:center; 
                justify-content:flex-start; 
                padding:50px 20px; 
            }
            .logo { 
                font-size:60px; 
                font-weight:bold; 
                color:black; 
                margin-bottom:30px; 
                text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
            }
            .dashboard { 
                background: rgba(255, 255, 255, 1); 
                border-radius: 15px; 
                padding: 40px 60px; 
                box-shadow: 0 10px 25px rgba(0,0,0,0.2); 
                max-width: 500px; 
                width: 100%;
                transition: transform 0.3s, box-shadow 0.3s;
            }
            .dashboard:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.3);
            }
            h2 { 
                margin-bottom: 25px; 
                color: #333;
                text-align:center;
            }
            .info { 
                text-align:left; 
                font-size:18px; 
                color: #444;
            }
            .info p { 
                margin:8px 0; 
                padding:5px 10px;
                border-radius:8px;
                background: rgba(0,0,0,0.03);
            }
            .tasks-btn {
                display: block;
                margin: 20px auto 10px auto;
                padding: 10px 25px;
                background-color: #198754;
                color: white;
                text-decoration: none;
                font-weight: bold;
                border-radius: 8px;
                text-align: center;
                transition: background-color 0.3s;
            }
            .tasks-btn:hover {
                background-color: #146c43;
            }
            .logout-btn {
                display:inline-block;
                margin-top:20px;
                padding:10px 25px;
                background-color:#6f42c1;
                color:white;
                text-decoration:none;
                font-weight:bold;
                border-radius:8px;
                transition: background-color 0.3s;
            }
            .logout-btn:hover {
                background-color:#532d91;
            }
            .view-admins-btn {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #0d6efd;
                color: white;
                padding: 10px 18px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                box-shadow: 0 6px 15px rgba(0,0,0,0.2);
            }
            .view-admins-btn:hover {
                background: #084298;
            }
        </style>
    </head>
    <body>
        <a href="{{ url_for('view_admins') }}" class="view-admins-btn">
            👑 View Admins 👑
        </a>
        <div class="overlay">
            <div class="logo">NeoLogin</div>
            <div class="dashboard">
                <div style="position: relative; text-align:center; margin-bottom:20px;">
                    <!-- Profile Picture -->
                    <img src="{{ url_for('static', filename='profile_photos/' + user['profile_photo']) if user.get('profile_photo') else url_for('static', filename='profile_photos/default.png') }}"
                        alt="Profile Photo"
                        class="profile-pic"
                        style="width:120px; height:120px; border-radius:50%; object-fit:cover; border:3px solid #6f42c1; background:#ccc;">
                    <!-- Choose File (Pen icon) -->
                    <form action="{{ url_for('update_profile_photo', email=user['email']) }}" method="POST" enctype="multipart/form-data">
                        <label for="profile_photo" style="
                            position: absolute;
                            top: -10px;
                            right: -10px;
                            background-color: #6f42c1;
                            color: white;
                            width:30px;
                            height:30px;
                            border-radius:50%;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            cursor:pointer;
                            font-size:16px;
                            border:2px solid white;
                            box-shadow:0 2px 6px rgba(0,0,0,0.3);
                            transition: all 0.2s ease;
                        ">✏️</label>
                        <input type="file" name="profile_photo" id="profile_photo" accept="image/*" required style="display:none;">
        
                        <!-- Upload Button -->
                        <button type="submit" style="
                            display:block;
                            margin: 15px auto 0 auto;
                            background-color: #0d6efd;
                            color: white;
                            padding: 10px 25px;
                            border: none;
                            border-radius: 8px;
                            font-weight: bold;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        ">Upload</button>
                    </form>
                </div>
                <script>
                    const uploadBtn = document.querySelector('button[type="submit"]');
                    const chooseFileLabel = document.querySelector('label[for="profile_photo"]');
                    uploadBtn.onmouseover = () => uploadBtn.style.backgroundColor = "#084298";
                    uploadBtn.onmouseout = () => uploadBtn.style.backgroundColor = "#0d6efd";
                    chooseFileLabel.onmouseover = () => chooseFileLabel.style.backgroundColor = "#532d91";
                    chooseFileLabel.onmouseout = () => chooseFileLabel.style.backgroundColor = "#6f42c1";
                </script>
                <h2>Welcome, {{ full_name }}</h2>
                <div class="info">
                    <p><b>Name:</b> {{ full_name }}</p>
                    <p><b>Gender:</b> {{ user['gender'] }}</p>
                    <p><b>Date_of_Birth:</b> {{ user['dob'] }}</p>
                    <p><b>Age:</b> {{ age }}</p>
                    <p><b>Email_ID:</b> {{ user['email'] }}</p>
                    <p><b>Mobile_Number:</b> {{ user['mobile'] }}</p>
                    <p><b>User_Name:</b> {{ user['username'] }}</p>
                </div>
                <a href="{{ url_for('view_tasks') }}" class="tasks-btn">📋 Tasks</a>
                <a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
            </div>
        </div>
    </body>
    </html>
    """, user=user, full_name=full_name, age=age)

# ================= USER TASKS PAGE =================
from flask import flash

@app.route("/view-tasks", methods=["GET", "POST"])
def view_tasks():
    if not session.get("logged_in"):
        return redirect(url_for("signin"))
    
    user_email = session.get("user_email")
    user_obj = User.query.filter_by(email=user_email).first()
    if not user_obj:
        return redirect(url_for("signin"))
    
    # POST: if user is creating a new task
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reward = request.form.get("reward", "").strip()

        if title and description and reward:
            new_task = Task(
                title=title,
                description=description,
                reward=reward,
                status="pending",
                created_by=user_obj.id
            )
            db.session.add(new_task)
            db.session.commit()
            flash("Task posted successfully!", "success")
        else:
            flash("All fields are required!", "danger")
        return redirect(url_for("view_tasks"))

    # GET: Show tasks
    tasks = Task.query.filter_by(
        status="approved",
        assigned_to=None
    ).all()

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tasks - NeoLogin</title>
        <style>
            body {
                font-family: Arial,sans-serif;
                margin:0;
                padding:0;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
            }
            .overlay {
                background-color: rgba(255,255,255,0.9);
                min-height: 100vh;
                padding: 50px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .task-box {
                background: white;
                border-radius: 15px;
                padding: 30px 50px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 900px;
            }
            table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
            th { background-color: #6f42c1; color: white; }
            tr:hover { background-color: #eef1ff; }
            .accept-btn, .post-btn {
                padding: 6px 12px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }
            .accept-btn { background: #28a745; color: white; }
            .accept-btn:hover { background: #218838; }
            .post-btn { background: #0d6efd; color: white; }
            .post-btn:hover { background: #084298; }
            form input, form textarea {
                width: 100%;
                padding: 6px;
                margin: 5px 0;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            h2 { text-align:center; color:#333; margin-bottom:25px; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="task-box">

                <h2>Available Tasks</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Description</th>
                        <th>Reward</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                    {% for t in tasks %}
                    <tr>
                        <td>{{ t.id }}</td>
                        <td>{{ t.title }}</td>
                        <td>{{ t.description }}</td>
                        <td>{{ t.reward }}</td>
                        <td>{{ t.status }}</td>
                        <td>
                            {% if t.status == 'approved' and not t.assigned_to %}
                                <a href="{{ url_for('accept_task', task_id=t.id) }}" class="accept-btn">
                                    Accept Task
                                </a>
                            {% else %}
                                —
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>

                <h2>Post a New Task</h2>
                <form method="POST">
                    <a href="{{ url_for('my_tasks') }}" class="post-btn">
                        📋 My Tasks
                    </a>
                    <br><br>
                    <input type="text" name="title" placeholder="Task Title" required>
                    <textarea name="description" placeholder="Task Description" rows="4" required></textarea>
                    <input type="text" name="reward" placeholder="Reward" required>
                    <button type="submit" class="post-btn">Post Task</button>
                </form>

            </div>
        </div>
    </body>
    </html>
    """, tasks=tasks, user_obj=user_obj)

@app.route("/accept-task/<int:task_id>")
def accept_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    # 🔥 FIX: get user from DATABASE, not users dict
    user_email = session.get("user_email")
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return redirect(url_for("signin"))

    task = Task.query.get(task_id)

    # Only approved & unassigned tasks can be accepted
    if task and task.status == "approved" and not task.assigned_to:
        task.assigned_to = user.id
        task.status = "accepted"

    # 🔥 ADD THESE TWO LINES
        task.active_for_user = False   # goes to Pending Tasks
        task.completed = False

        db.session.commit()


    return redirect(url_for("view_tasks"))

@app.route("/complete-task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return redirect(url_for("signin"))

    task = Task.query.filter_by(
        id=task_id,
        assigned_to=user.id,
        completed=False
    ).first()

    if task:
        task.completed = True
        task.active_for_user = False   # IMPORTANT
        db.session.commit()

    # 🔴 THIS is the fix
    return redirect(url_for("my_tasks"))

@app.route("/my-tasks", methods=["GET", "POST"])
def my_tasks():
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user_obj = User.query.filter_by(email=user_email).first()
    if not user_obj:
        return redirect(url_for("signin"))

    # Fetch tasks
    active_task = Task.query.filter_by(assigned_to=user_obj.id, active_for_user=True, completed=False).first()
    pending_tasks = Task.query.filter_by(assigned_to=user_obj.id, active_for_user=False, completed=False).all()
    completed_tasks = Task.query.filter_by(assigned_to=user_obj.id, completed=True).all()

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Tasks - NeoLogin</title>
        <style>
            body {
                font-family: Arial,sans-serif;
                margin:0;
                padding:0;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
            }
            .overlay {
                background-color: rgba(255,255,255,0.9);
                min-height: 100vh;
                padding: 50px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .task-box {
                background: white;
                border-radius: 15px;
                padding: 30px 50px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 900px;
            }
            table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
            th { background-color: #6f42c1; color: white; }
            tr:hover { background-color: #eef1ff; }
            .accept-btn, .start-btn, .complete-btn {
                padding: 6px 12px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }
            .accept-btn { background: #28a745; color: white; }
            .accept-btn:hover { background: #218838; }
            .start-btn { background: #ffc107; color: white; }
            .start-btn:hover { background: #e0a800; }
            .complete-btn { background: #0d6efd; color: white; }
            .complete-btn:hover { background: #084298; }
            h2 { text-align:center; color:#333; margin-bottom:25px; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="task-box">

                <div style="text-align:center; margin-bottom: 20px;">
                    <a href="{{ url_for('view_tasks') }}" 
                        style="display:inline-block;
                            padding: 10px 25px;
                            background-color: #198754;
                            color: white;
                            font-weight: bold;
                            border-radius: 8px;
                            text-decoration: none;
                            transition: background-color 0.3s;">
                        📋 Available Tasks
                    </a>
                </div>

                <h2>Active Task</h2>
                {% if active_task %}
                <table>
                    <tr><th>ID</th><th>Title</th><th>Description</th><th>Reward</th><th>Action</th></tr>
                    <tr>
                        <td>{{ active_task.id }}</td>
                        <td>{{ active_task.title }}</td>
                        <td>{{ active_task.description }}</td>
                        <td>{{ active_task.reward }}</td>
                        <td>
                            <form method="POST" action="{{ url_for('complete_task', task_id=active_task.id) }}">
                                <button type="submit" class="complete-btn">Mark Completed</button>
                            </form>
                        </td>
                    </tr>
                </table>
                {% else %}
                    <p style="text-align:center;">No active task. Pick one from Pending or Available Tasks.</p>
                {% endif %}

                <h2>Pending Tasks</h2>
                {% if pending_tasks %}
                <table>
                    <tr><th>ID</th><th>Title</th><th>Description</th><th>Reward</th><th>Action</th></tr>
                    {% for t in pending_tasks %}
                    <tr>
                        <td>{{ t.id }}</td>
                        <td>{{ t.title }}</td>
                        <td>{{ t.description }}</td>
                        <td>{{ t.reward }}</td>
                        <td>
                            <a href="{{ url_for('switch_task', task_id=t.id) }}" class="start-btn">
                                Switch To This Task
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                    <p style="text-align:center;">No pending tasks.</p>
                {% endif %}

                <h2>Completed Tasks</h2>
                {% if completed_tasks %}
                <table>
                    <tr><th>ID</th><th>Title</th><th>Description</th><th>Reward</th></tr>
                    {% for t in completed_tasks %}
                    <tr>
                        <td>{{ t.id }}</td>
                        <td>{{ t.title }}</td>
                        <td>{{ t.description }}</td>
                        <td>{{ t.reward }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                    <p style="text-align:center;">No completed tasks yet.</p>
                {% endif %}

            </div>
        </div>
    </body>
    </html>
    """, active_task=active_task, pending_tasks=pending_tasks, completed_tasks=completed_tasks)

@app.route("/switch-task/<int:task_id>")
def switch_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return redirect(url_for("signin"))

    current_active = Task.query.filter_by(
        assigned_to=user.id,
        active_for_user=True,
        completed=False
    ).first()

    new_task = Task.query.filter_by(
        id=task_id,
        assigned_to=user.id,
        completed=False
    ).first()

    if not new_task:
        return redirect(url_for("my_tasks"))

    # 🔥 SAFETY CHECK
    if current_active and current_active.id == new_task.id:
        return redirect(url_for("my_tasks"))

    if current_active:
        current_active.active_for_user = False

    new_task.active_for_user = True

    db.session.commit()
    return redirect(url_for("my_tasks"))

@app.route("/start-task/<int:task_id>")
def start_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return redirect(url_for("signin"))

    # Deactivate current active task
    current = Task.query.filter_by(
        assigned_to=user.id,
        active_for_user=True,
        completed=False
    ).first()

    if current:
        current.active_for_user = False

    # Activate selected task
    task = Task.query.get(task_id)
    if task and task.assigned_to == user.id and not task.completed:
        task.active_for_user = True

    db.session.commit()
    return redirect(url_for("my_tasks"))

# ================= POST A TASK (USER) =================
@app.route("/post-task", methods=["GET", "POST"])
def post_task():
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reward = request.form.get("reward", "").strip()

        # For now: just confirm submission (no storage yet)
        return render_template_string(r"""
        <script>
            alert("Task submitted successfully! Waiting for admin approval.");
            window.location.href = "/tasks";
        </script>
        """)

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Post Task - NeoLogin</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f9;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 600px;
                margin: 60px auto;
                background: white;
                padding: 35px;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }
            h2 {
                text-align: center;
                margin-bottom: 25px;
            }
            input, textarea {
                width: 100%;
                padding: 10px;
                margin-bottom: 15px;
                border-radius: 6px;
                border: 1px solid #ccc;
                font-size: 15px;
            }
            textarea {
                resize: vertical;
                height: 120px;
            }
            button {
                display: block;
                width: 100%;
                padding: 10px;
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            button:hover {
                background-color: #532d91;
            }
            .back {
                text-align: center;
                margin-top: 15px;
            }
            .back a {
                text-decoration: none;
                color: #0d6efd;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Post a New Task</h2>
            <form method="POST">
                <input type="text" name="title" placeholder="Task Title" required>
                <textarea name="description" placeholder="Task Description" required></textarea>
                <input type="text" name="reward" placeholder="Reward (example: 100 points)" required>
                <button type="submit">Submit Task</button>
            </form>
            <div class="back">
                <a href="/tasks">⬅ Back to Tasks</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/update-profile-photo/<email>", methods=["POST"])
def update_profile_photo(email):
    # Find the user by email
    user_found = None
    for u in users.values():
        if u["email"] == email:
            user_found = u
            break

    if not user_found:
        return redirect(url_for('signin'))

    if "profile_photo" not in request.files or request.files["profile_photo"].filename == "":
        return "No file selected", 400

    file = request.files["profile_photo"]
    os.makedirs("static/profile_photos", exist_ok=True)

    # Save file securely with user id prefix
    user_obj = User.query.filter_by(email=email).first()
    if user_obj:
        from werkzeug.utils import secure_filename
        filename = secure_filename(f"User_{user_obj.id}_{file.filename}")
        filepath = os.path.join("static/profile_photos", filename)
        file.save(filepath)

        # Delete old photo if exists and not default
        if user_obj.profile_photo and user_obj.profile_photo != "default.png":
            old_path = os.path.join("static/profile_photos", user_obj.profile_photo)
            if os.path.exists(old_path):
                os.remove(old_path)

        # Update DB
        user_obj.profile_photo = filename
        db.session.commit()

        # Update in-memory dictionary
        user_found['profile_photo'] = filename

    return redirect(url_for("dashboard", email=email))

# ================= VIEW USERS (ADMIN ONLY) =================
@app.route("/view-users")
def view_users():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    all_users = User.query.all()

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>View Users - NeoLogin</title>
        <style>
            *{
                box-sizing: border-box;
            }
            input:focus {
                outline: none;
                border: 2px solid #6f42c1;
                box-shadow: 0 0 6px rgba(111,66,193,0.4);
            }
            button:hover {
                opacity: 0.92;
                transform: translateY(-1px);
            }
            button {
                transition: all 0.2s ease;
            }
            tr:hover {
                background-color: #eef1ff;
            }
            .pen:hover {
                color: #6f42c1;
            }
            .delete:hover {
                background: #b52a37;
            }
            body {
                animation: pageFade 0.4s ease;
            }
            @keyframes pageFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            body {
                font-family: Arial, sans-serif;
                background: #f2f2f2;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
                padding: 40px;
               position: relative;
            }
            /* Add a blur effect using a pseudo-element */
            body::before {
                content: "";
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: inherit;
                background-size: cover;
                background-position: center;
                filter: blur(3px) brightness(0.6); /* blur & dim */
                z-index: -1;
            }
            .overlay { 
                background-color: rgba(255,255,255,0.4); /* more transparent */
                min-height:100vh; 
                display:flex; 
                flex-direction: column; 
                align-items:center; 
                justify-content:flex-start; 
                padding:50px 20px; 
                position: relative;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }
            th, td {
                padding: 14px;
                text-align: center;
            }
            th {
                background: #6f42c1;
                color: white;
            }
            tr:nth-child(even) {
                background: #f9f9f9;
            }
            .username-input {
                width: 140px;
                padding: 6px;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            .username-input:disabled {
                background: #eaeaea;
                cursor: not-allowed;
            }
            .pen {
                cursor: pointer;
                font-size: 18px;
                margin-right: 6px;
            }
            .save-btn {
                display: none;
                background: #28a745;
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 6px;
                cursor: pointer;
            }
            .delete {
                background: #dc3545;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: bold;
            }
            .top-bar {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }
            .logout {
                background: #6f42c1;
                color: white;
                padding: 8px 18px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
    <div class="top-bar">
        <h2>Registered Users (Admin)</h2>
        <a class="logout" href="{{ url_for('logout') }}">Logout</a>
    </div>
    <table>
        <tr>
            <th>ID</th>
            <th>First Name (Edit)</th>
            <th>Last Name (Edit)</th>
            <th>Email</th>
            <th>Mobile </th>
            <th>Username (Edit)</th>
            <th>Gender (Edit)</th>
            <th>Role</th>
            <th>Admin Action</th>
            <th>Edit</th>
            <th>Delete</th>

        </tr>
    {% for u in users %}
    <tr>
        <td>{{ u.id }}</td>
        <!-- First Name -->
        <td>
            <form method="POST" action="{{ url_for('update_name', user_id=u.id) }}">
                <input type="text"
                        name="first_name"
                        value="{{ u.first_name }}"
                        class="username-input"
                        disabled>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <td>
            <form method="POST" action="{{ url_for('update_name', user_id=u.id) }}">
                <input type="text"
                        name="last_name"
                        value="{{ u.last_name }}"
                        class="username-input"
                        disabled>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <td>{{ u.email }}</td>
        <td>{{ u.mobile }}</td>
        <!-- Username -->
        <td>
            <form method="POST"
                action="{{ url_for('update_username', user_id=u.id) }}">
                <input type="text"
                        name="username"
                        value="{{ u.username }}"
                        class="username-input"
                        disabled>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <!-- GENDER -->
        <td>
            <form method="POST" action="{{ url_for('update_gender', user_id=u.id) }}">
                <select name="gender" class="username-input" disabled>
                    <option value="Male" {% if u.gender == 'Male' %}selected{% endif %}>Male</option>
                    <option value="Female" {% if u.gender == 'Female' %}selected{% endif %}>Female</option>
                    <option value="Other" {% if u.gender == 'Other' %}selected{% endif %}>Other</option>
                </select>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <!-- ROLE -->
        <td>
            {% if u.is_admin %}
                <b style="color:green;">ADMIN</b>
            {% else %}
                USER
            {% endif %}
        </td>
        <!-- ADMIN ACTION -->
        <td>
            {% if not u.is_admin %}
                <a href="{{ url_for('make_admin', user_id=u.id) }}"
                    onclick="return confirm('Make this user an admin?')">
                    👑 Make Admin 👑
                </a>
            {% elif u.is_admin and u.email != session.get('user_email') %}
                <a href="{{ url_for('remove_admin', user_id=u.id) }}"
                    onclick="return confirm('Remove admin rights from this user?')">
                    🚫 Remove Admin 🚫
                    </a>
                {% else %}
                        —  <!-- current admin cannot remove self -->
                {% endif %}
            </td>
            <!-- Edit -->
            <td>—</td>
            <!-- Delete -->
            <td>
                <a class="delete"
                    href="{{ url_for('delete_user', user_id=u.id) }}"
                    onclick="return confirm('Are you sure you want to delete this user?')">
                    ❌
                </a>
            </td>
        </tr>
        {% endfor %}
    </table>
    <script>
    function enableEdit(el) {
        const form = el.closest("form");
        const input = form.querySelector(".username-input"); // works for both input and select
        const saveBtn = form.querySelector(".save-btn");
        input.disabled = false;
        input.focus();
        saveBtn.style.display = "inline-block";
    }
    </script>
    </body>
    </html>
    """, users=all_users)


# ================= UPDATE USERNAME (ADMIN ONLY) =================
@app.route("/update-username/<int:user_id>", methods=["POST"])
def update_username(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    new_username = request.form.get("username", "").strip()

    # Prevent duplicates
    existing = User.query.filter_by(username=new_username).first()
    if existing and existing.id != user_id:
        return redirect(url_for("view_users"))


    user = User.query.get(user_id)
    if user:
        old_username = user.username
        user.username = new_username
        db.session.commit()

        # Sync in-memory dict
        users[new_username] = users.pop(old_username)
        users[new_username]["username"] = new_username

        # 🔥 ADD THESE 3 LINES ONLY
        if session.get("user_email") == user.email:
            session.clear()
            return redirect(url_for("signin"))

    return redirect(url_for("view_users"))

# ================= UPDATE FIRST / LAST NAME (ADMIN ONLY) =================
@app.route("/update-name/<int:user_id>", methods=["POST"])
def update_name(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("view_users"))

    new_first = request.form.get("first_name")
    new_last = request.form.get("last_name")

    if new_first:
        user.first_name = new_first
        users[user.username]["first_name"] = new_first

    if new_last:
        user.last_name = new_last
        users[user.username]["last_name"] = new_last

    db.session.commit()

    return redirect(url_for("view_users"))

# ================= UPDATE GENDER (ADMIN ONLY) =================
@app.route("/update-gender/<int:user_id>", methods=["POST"])
def update_gender(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = User.query.get(user_id)
    if user:
        new_gender = request.form.get("gender", "").strip()
        if new_gender:
            user.gender = new_gender
            db.session.commit()
    return redirect(url_for("view_users"))

# ================= UPDATE RECOVERY KEYWORD (ADMIN ONLY) =================
@app.route("/update-recovery/<int:user_id>", methods=["POST"])
def update_recovery(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = User.query.get(user_id)
    if user:
        new_keyword = request.form.get("recovery_keyword", "").strip()
        if new_keyword:
            from werkzeug.security import generate_password_hash
            user.recovery_keyword_hash = generate_password_hash(new_keyword)
            db.session.commit()
    return redirect(url_for("view_users"))

# ================= DELETE USER (ADMIN ONLY) =================
@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = User.query.get(user_id)
    
    if user:
        db.session.delete(user)
        db.session.commit()
        users.pop(user.username, None)

    return redirect(url_for("view_users"))


@app.route("/admin-menu")
def admin_menu():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))
    
    warning = session.pop("show_admin_warning", False)

    email = session.get("user_email")
    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Menu - NeoLogin</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
            body {
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            /* Background Image with Blur and Overlay */
            body::before {
                content: "";
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1470&q=80');
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                filter: blur(2px) brightness(0.5);
                z-index: -1;
            }
            .container {
                display: flex;
                background-color: rgba(255,255,255,0.95);
                border-radius: 20px;
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
                overflow: hidden;
                max-width: 900px;
                width: 90%;
                min-height: 400px;
            }
            /* Company Info Panel */
            .company-info {
                background: #1e3a8a; /* Deep blue */
                color: #f3f4f6; /* Light text */
                padding: 40px 30px;
                width: 40%;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .company-info h2 {
                margin-bottom: 20px;
                font-size: 28px;
                color: #fff;
            }
            .company-info p {
                margin: 8px 0;
                font-size: 16px;
                line-height: 1.5;
            }
            /* Admin Menu Side */
            .menu {
                padding: 50px 60px;
                width: 60%;
                text-align: center;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .menu h1 {
                margin-bottom: 40px;
                color: #4b0082;
            }
            .btn {
                display: block;
                width: 70%;
                margin: 15px auto;
                padding: 15px 0;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
                cursor: pointer;
                color: white;
                background: linear-gradient(45deg, #6f42c1, #a855f7);
                text-decoration: none;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.25);
                opacity: 0.95;
            }
            .logout-btn {
                background: linear-gradient(45deg, #dc3545, #f87171);
            }
            @media(max-width: 850px) {
                .container { flex-direction: column; min-height: auto; }
                .company-info, .menu { width: 100%; padding: 30px 20px; }
                .btn { width: 90%; font-size: 16px; }
            }
        </style>
    </head>
    <body>
        {% if warning %}
        <script>
        alert("⚠️ WARNING!\n\nYou have been reported.\nRepeated reports may remove admin rights.");
        </script>
        {% endif %}
        <div class="container">
            <!-- Company Info Panel -->
            <div class="company-info">
                <h2>NeoLogin Pvt. Ltd.</h2>
                <p><b>Address:</b> 123, Tech Park, Bengaluru, India</p>
                <p><b>Phone:</b> +91 98765 43210</p>
                <p><b>Email:</b> support@neologin.com</p>
                <p><b>Clients:</b> 50+ companies worldwide</p>
                <p><b>Website:</b> www.neologin.com</p>
            </div>
            <!-- Admin Menu Buttons -->
            <div class="menu">
                <h1>Welcome, Admin!</h1>
                <a href="{{ url_for('dashboard', email=email) }}" class="btn">Go to Dashboard</a>
                <a href="{{ url_for('view_users') }}" class="btn">View Users</a>
                <a href="{{ url_for('view_tasks') }}" class="btn">TASKS</a>
                <a href="{{ url_for('admin_task_management') }}" class="btn">TASK MANAGEMENT</a>
                <a href="{{ url_for('logout') }}" class="btn logout-btn">Logout</a>
            </div>
        </div>
    </body>
    </html>
    """, email=email)

# ================= ADMIN TASK MANAGEMENT =================
@app.route("/admin-tasks", methods=["GET", "POST"])
def admin_tasks():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    all_tasks = Task.query.order_by(Task.id.desc()).all()

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Task Management - NeoLogin</title>
        <style>
            body {
                font-family: Arial,sans-serif;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
                padding: 40px;
                position: relative;
            }
            body::before {
                content: "";
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background-image: inherit;
                background-size: cover;
                background-position: center;
                filter: blur(3px) brightness(0.6);
                z-index: -1;
            }
            .overlay {
                background-color: rgba(255,255,255,0.85);
                min-height:100vh;
                display:flex;
                flex-direction: column;
                align-items:center;
                justify-content:flex-start;
                padding:50px 20px;
                position: relative;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
                background: white;
            }
            th, td { padding: 14px; text-align:center; }
            th { background: #6f42c1; color:white; }
            tr:nth-child(even) { background: #f9f9f9; }
            tr:hover { background-color: #eef1ff; }
            button, .approve-btn, .reject-btn { padding:6px 10px; border:none; border-radius:6px; cursor:pointer; }
            .approve-btn { background:#28a745; color:white; }
            .reject-btn { background:#dc3545; color:white; }
            .logout { background: #6f42c1; color: white; padding: 8px 18px; border-radius: 8px; text-decoration:none; font-weight:bold; margin-bottom:20px; display:inline-block; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <a class="logout" href="{{ url_for('logout') }}">Logout</a>
            <h2>Admin Task Management</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Description</th>
                    <th>Reward</th>
                    <th>Posted By</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
                {% for task in tasks %}
                <tr>
                    <td>{{ task.id }}</td>
                    <td>{{ task.title }}</td>
                    <td>{{ task.description }}</td>
                    <td>{{ task.reward }}</td>
                    <td>{{ task.posted_by }}</td>
                    <td>
                        {% if task.approved %}
                            ✅ Approved
                        {% else %}
                            ❌ Pending
                        {% endif %}
                    </td>
                    <td>
                        {% if not task.approved %}
                        <a href="{{ url_for('approve_task', task_id=task.id) }}" class="approve-btn" onclick="return confirm('Approve this task?')">Approve</a>
                        <a href="{{ url_for('reject_task', task_id=task.id) }}" class="reject-btn" onclick="return confirm('Reject this task?')">Reject</a>
                        {% else %}
                            — 
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """, tasks=all_tasks)

@app.route("/approve-task/<int:task_id>")
def approve_task(task_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    task = Task.query.get(task_id)
    if task:
        task.status = "approved"
        db.session.commit()
    return redirect(url_for("admin_task_management"))

# ================= ADMIN TASK MANAGEMENT =================
@app.route("/admin-task-management", methods=["GET", "POST"])
def admin_task_management():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    # Approve a task
    if request.method == "POST":
        task_id = request.form.get("task_id")
        task = Task.query.get(task_id)
        if task:
            task.status = "approved"
            db.session.commit()
            flash("Task approved successfully!", "success")
        return redirect(url_for("admin_task_management"))

    # Show all tasks
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    users = User.query.all()

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Task Management - NeoLogin</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 30px; background: #f4f6f9; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: center; }
            th { background-color: #6f42c1; color: white; }
            tr:hover { background-color: #eef1ff; }
            .approve-btn { padding: 6px 12px; border: none; border-radius: 6px; background: #28a745; color: white; cursor: pointer; font-weight: bold; }
            .approve-btn:hover { background: #218838; }
        </style>
    </head>
    <body>
        <h2>Admin Task Management</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Description</th>
                <th>Reward</th>
                <th>Status</th>
                <th>Created By</th>
                <th>Accepted By</th>
                <th>Action</th>
            </tr>
            {% for t in tasks %}
            <tr>
                <td>{{ t.id }}</td>
                <td>{{ t.title }}</td>
                <td>{{ t.description }}</td>
                <td>{{ t.reward }}</td>
                <td>{{ t.status }}</td>
                <td>
                    {{ t.creator.username if t.creator else 'Unknown' }}
                </td>
                <td>
                    {% if t.assigned_to %}
                        {{ t.assignee.username }}
                    {% else %}
                        —
                    {% endif %}
                </td>
                <td>
                    {% if t.status == 'pending' %}
                    <!-- APPROVE FORM -->
                    <form method="POST" style="margin-bottom:6px;">
                        <input type="hidden" name="task_id" value="{{ t.id }}">
                        <button type="submit" class="approve-btn">Approve</button>
                    </form>
                    <!-- ASSIGN FORM -->
                    <form method="GET" action="{{ url_for('assign_task', task_id=t.id) }}">
                        <select name="user_id" required>
                            <option value="">Assign to user</option>
                            {% for u in users %}
                                <option value="{{ u.id }}">{{ u.username }}</option>
                            {% endfor %}
                        </select>
                    <button type="submit">Assign</button>
                </form>
                {% else %}
                    —
                {% endif %}
            </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, tasks=tasks , users=users)

@app.route("/assign-task/<int:task_id>")
def assign_task(task_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user_id = request.args.get("user_id")
    task = Task.query.get(task_id)
    user = User.query.get(user_id)

    if task and user:
        task.assigned_to = user.id
        task.status = "accepted"
        task.completed = False
        existing_active = Task.query.filter_by(
            assigned_to=user.id,
            active_for_user=True,
            completed=False
        ).first()

        if existing_active:
            task.active_for_user = False   # goes to Pending
        else:
            task.active_for_user = True    # becomes Active

        db.session.commit()

    return redirect(url_for("admin_task_management"))

@app.route("/view-admins", methods=["GET", "POST"])
def view_admins():
    all_admins = User.query.filter_by(is_admin=True).all()
    is_admin_logged_in = session.get("is_admin", False)
    logged_in_email = session.get("user_email")

    return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>View Admins - NeoLogin</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-image: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
                padding: 40px;
                position: relative;
            }
            body::before {
                content: "";
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background-image: inherit;
                background-size: cover;
                background-position: center;
                filter: blur(3px) brightness(0.6);
                z-index: -1;
            }
            .overlay {
                background-color: rgba(255,255,255,0.4);
                min-height:100vh;
                display:flex;
                flex-direction: column;
                align-items:center;
                justify-content:flex-start;
                padding:50px 20px;
                position: relative;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }
            th, td { padding: 14px; text-align:center; }
            th { background: #6f42c1; color:white; }
            tr:nth-child(even) { background: #f9f9f9; }
            tr:hover { background-color: #eef1ff; }
            button, .report-btn { padding:6px 10px; border:none; border-radius:6px; cursor:pointer; }
            .report-btn { background:#ff7f50; color:white; }
            .logout { background: #6f42c1; color: white; padding: 8px 18px; border-radius: 8px; text-decoration:none; font-weight:bold; }
        </style>
    </head>
    <body>
        <div class="overlay">
            <div class="top-bar" style="width:100%; display:flex; justify-content:space-between; margin-bottom:20px;">
                <h2>Admins</h2>
                <a class="logout" href="{{ url_for('logout') }}">Logout</a>
            </div>
            <table>
                <tr>
                    <th>ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Email</th>
                    <th>Mobile</th>
                    <th>Username</th>
                    <th>Actions</th>
                </tr>
                {% for admin in admins %}
                <tr>
                    <td>{{ admin.id }}</td>
                    <td>{{ admin.first_name }}</td>
                    <td>{{ admin.last_name }}</td>
                    <td>{{ admin.email }}</td>
                    <td>{{ admin.mobile }}</td>
                    <td>{{ admin.username }}</td>
                    <td>
                        {% if admin.email != logged_in_email %}
                            <a href="{{ url_for('report_admin', user_id=admin.id) }}"
                            onclick="return confirm('Report this admin?')"
                            class="report-btn">⚠️ Report Admin</a>
                        {% else %}
                             —  <!-- cannot report self -->
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """, admins=all_admins, is_admin=is_admin_logged_in, logged_in_email=logged_in_email)

@app.route("/remove-admin/<int:user_id>")
def remove_admin(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))
    user = User.query.get(user_id)
    current_admin_email = session.get("user_email")
    if user and user.is_admin and user.email != current_admin_email:
        user.is_admin = False  # ✅ revert to regular user
        db.session.commit()

    return redirect(url_for("view_users"))

@app.route("/report-admin/<int:user_id>")
def report_admin(user_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))
    admin = User.query.get(user_id)
    if admin:
        admin.reported = True
        db.session.commit()

    return redirect(url_for("view_admins"))

# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
