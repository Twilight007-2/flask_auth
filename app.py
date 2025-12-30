import os
import re
import random
import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

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
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'swamythk07@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # must be app password if 2FA enabled
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'swamythk07@gmail.com')

mail = Mail(app)

def generate_otp():
    return str(random.randint(100000, 999999))  # 6-digit OTP

os.makedirs(app.instance_path, exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

ADMIN_EMAIL = "swamythk07@gmail.com"
ADMIN_PASSWORD = "Admin@123"

users = {}

basedir = os.path.abspath(os.path.dirname(__file__))

# Simple JSON-based database file
DB_FILE = os.path.join(basedir, "users_db.json")

# Simple Database Functions
def load_users():
    """Load users from JSON file."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    return {}

def save_users(users_data):
    """Save users to JSON file."""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def get_user_by_email(email):
    """Get user by email."""
    users_data = load_users()
    for username, user_info in users_data.items():
        if user_info.get('email') == email:
            return {'username': username, **user_info}
    return None

def get_user_by_username(username):
    """Get user by username."""
    users_data = load_users()
    if username in users_data:
        return {'username': username, **users_data[username]}
    return None

def get_user_by_mobile(mobile):
    """Get user by mobile number."""
    users_data = load_users()
    for username, user_info in users_data.items():
        if user_info.get('mobile') == mobile:
            return {'username': username, **user_info}
    return None

def create_user(username, email, password, mobile=None):
    """Create a new user."""
    users_data = load_users()
    if username in users_data:
        return False  # Username already exists
    
    # Check if email already exists
    for existing_username, user_info in users_data.items():
        if user_info.get('email') == email:
            return False  # Email already exists
    
    users_data[username] = {
        'email': email,
        'password': generate_password_hash(password),
        'mobile': mobile or '',
        'created_at': datetime.utcnow().isoformat()
    }
    return save_users(users_data)

def update_user_password(username, new_password):
    """Update user password."""
    users_data = load_users()
    if username in users_data:
        users_data[username]['password'] = generate_password_hash(new_password)
        return save_users(users_data)
    return False

# ================= TASK DATABASE FUNCTIONS =================
def load_tasks():
    """Load tasks from the JSON database file."""
    if not os.path.exists(TASKS_DB_FILE):
        return {}
    with open(TASKS_DB_FILE, 'r') as f:
        return json.load(f)

def save_tasks(tasks_data):
    """Save tasks to the JSON database file."""
    try:
        with open(TASKS_DB_FILE, 'w') as f:
            json.dump(tasks_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving tasks: {e}")
        return False

def create_task(task_data):
    """Create a new task."""
    tasks_data = load_tasks()
    task_id = str(len(tasks_data) + 1)  # Simple ID generation
    # Ensure unique ID
    while task_id in tasks_data:
        task_id = str(int(task_id) + 1)
    
    task_data['id'] = task_id
    task_data['created_at'] = datetime.utcnow().isoformat()
    tasks_data[task_id] = task_data
    if save_tasks(tasks_data):
        return task_id
    return None

def get_task_by_id(task_id):
    """Get task by ID."""
    tasks_data = load_tasks()
    task_id_str = str(task_id)
    if task_id_str in tasks_data:
        return tasks_data[task_id_str]
    return None

def query_tasks(filters=None):
    """Query tasks with optional filters."""
    tasks_data = load_tasks()
    tasks = []
    
    for task_id, task_info in tasks_data.items():
        task_info['id'] = task_id
        if filters:
            match = True
            for key, value in filters.items():
                if task_info.get(key) != value:
                    match = False
                    break
            if match:
                tasks.append(task_info)
        else:
            tasks.append(task_info)
    
    return tasks

def update_task(task_id, updates):
    """Update a task."""
    tasks_data = load_tasks()
    task_id_str = str(task_id)
    if task_id_str in tasks_data:
        tasks_data[task_id_str].update(updates)
        return save_tasks(tasks_data)
    return False

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
                padding: 10px 18px;
                background: #38bdf8;
                color: #000 !important;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                transition: background 0.3s;
                border: none;
                cursor: pointer;
            }

            .project-link:hover {
                background: #0ea5e9;
                color: #000 !important;
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

                <a href="{{ url_for('neologin_home') }}" class="project-link">
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

# NeoLogin Home Page
@app.route("/neologin")
def neologin_home():
    return render_template_string(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeoLogin - Secure Authentication</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
                overflow: hidden;
            }

            body::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
                opacity: 0.1;
                z-index: -1;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 30px;
                padding: 60px 50px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
                animation: slideUp 0.6s ease;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .logo {
                font-size: 80px;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 20px;
                text-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
            }

            h1 {
                font-size: 36px;
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
            }

            .description {
                font-size: 16px;
                color: #666;
                line-height: 1.8;
                margin-bottom: 40px;
                max-width: 500px;
                margin-left: auto;
                margin-right: auto;
            }

            .button-group {
                display: flex;
                gap: 20px;
                justify-content: center;
                flex-wrap: wrap;
            }

            .btn {
                padding: 15px 40px;
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                color: white;
            }

            .signup-btn {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            }

            .signup-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(17, 153, 142, 0.4);
            }

            .signin-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }

            .signin-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }

            @media (max-width: 600px) {
                .container {
                    padding: 40px 30px;
                }

                .logo {
                    font-size: 60px;
                }

                h1 {
                    font-size: 28px;
                }

                .button-group {
                    flex-direction: column;
                }

                .btn {
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">N</div>
            <h1>Welcome to NeoLogin</h1>
            <p class="description">
                NeoLogin is a secure and user-friendly authentication system.
                Register to create an account or sign in to access your personalized dashboard.
            </p>
            <div class="button-group">
                <form action="{{ url_for('signup') }}" method="get" style="display:inline;">
                    <button type="submit" class="btn signup-btn">Sign Up</button>
                </form>
                <form action="{{ url_for('signin') }}" method="get" style="display:inline;">
                    <button type="submit" class="btn signin-btn">Sign In</button>
                </form>
            </div>
        </div>
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
            from werkzeug.utils import secure_filename
            # Use secure_filename to prevent path traversal and special characters
            original_filename = secure_filename(photo.filename)
            # Create unique filename with username and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(original_filename)[1] or '.png'
            filename = f"{username}_{timestamp}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Ensure upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            photo.save(filepath)

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$'
        mobile_pattern = r'^[6-9]\d{9}$'
        # Check Firestore for existing users
        try:
            mobile_exists = get_user_by_mobile(mobile) is not None
            email_exists = get_user_by_email(email) is not None
            username_exists = get_user_by_username(username) is not None
        except Exception as e:
            print(f"Firestore query error during signup validation: {e}")
            message = "Database error. Please try again later."
            return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error - NeoLogin</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .error { color: #c0392b; font-size: 18px; }
            a { color: #667eea; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="error">{{ message }}</div>
        <a href="{{ url_for('signup') }}">Go back to Sign Up</a>
    </body>
    </html>
    """, message=message)

        if not (fname and lname and dob and mobile and email and username and password and confirm_password):
            message = "All fields are required"
        elif not re.match(mobile_pattern, mobile):
            message = "Mobile number must be 10 digits and start with 6, 7, 8, or 9"
            clear_mobile = True
        elif username_exists:
            message = "Username already exists"
            clear_username = True
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
            # Create user in simple JSON database
            try:
                success = create_user(username, email, password, mobile)
                if success:
                    # Update in-memory dictionary (optional, for backward compatibility)
                    users[username] = {
                        "email": email,
                        "password": password,
                        "mobile": mobile,
                    }
                    return redirect(url_for('signin'))
                else:
                    # Double-check for duplicates
                    if get_user_by_username(username):
                        message = "Username already exists"
                        clear_username = True
                    elif get_user_by_email(email):
                        message = "Email ID already exists"
                        clear_email = True
                    elif get_user_by_mobile(mobile):
                        message = "Mobile number already exists"
                        clear_mobile = True
                    else:
                        message = "Registration failed. Please try again."
            except Exception as e:
                print(f"Error during signup: {e}")
                message = f"Registration failed due to an error. Please try again. Error: {str(e)}"

    return render_template_string(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sign Up - NeoLogin</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
            }

            body::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
                opacity: 0.1;
                z-index: -1;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 50px 40px;
                max-width: 550px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.6s ease;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
            }

            .header h2 {
                font-size: 32px;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }

            .header p {
                color: #666;
                font-size: 14px;
            }

            form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }

            .form-group {
                display: flex;
                flex-direction: column;
            }

            label {
                font-size: 14px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }

            input, select {
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                font-family: 'Poppins', sans-serif;
                transition: all 0.3s ease;
                background: white;
            }

            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .password-container {
                position: relative;
            }

            .password-container input {
                padding-right: 45px;
            }

            .eye {
                position: absolute;
                right: 15px;
                top: 50%;
                transform: translateY(-50%);
                cursor: pointer;
                font-size: 18px;
                user-select: none;
            }

            .password-rules {
                list-style: none;
                padding: 0;
                margin: 10px 0;
                font-size: 12px;
            }

            .password-rules li {
                padding: 5px 0;
                color: #e74c3c;
                transition: all 0.3s ease;
            }

            .password-rules li[style*="green"] {
                color: #27ae60;
            }

            .file-input-wrapper {
                position: relative;
                overflow: hidden;
                display: inline-block;
                width: 100%;
            }

            .file-input-wrapper input[type=file] {
                position: absolute;
                left: -9999px;
            }

            .file-input-label {
                display: block;
                padding: 12px 15px;
                background: #f8f9fa;
                border: 2px dashed #e0e0e0;
                border-radius: 10px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                color: #666;
                font-size: 14px;
            }

            .file-input-label:hover {
                border-color: #667eea;
                background: #f0f4ff;
            }

            button[type="submit"] {
                padding: 15px;
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(17, 153, 142, 0.3);
                margin-top: 10px;
            }

            button[type="submit"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(17, 153, 142, 0.4);
            }

            .msg {
                background: #ffe6e6;
                color: #c0392b;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                font-weight: 500;
                font-size: 14px;
                margin-top: 15px;
                border-left: 4px solid #c0392b;
            }

            .back-link {
                text-align: center;
                margin-top: 20px;
            }

            .back-link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
            }

            .back-link a:hover {
                text-decoration: underline;
            }

            @media (max-width: 600px) {
                .container {
                    padding: 40px 25px;
                }

                .form-row {
                    grid-template-columns: 1fr;
                }

                .header h2 {
                    font-size: 28px;
                }
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
                        el.style.color = "#27ae60";
                        setTimeout(() => { el.style.display = "none"; }, 1500);
                    } else {
                        el.style.display = "list-item";
                        el.style.color = "#e74c3c";
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
                const dobInput = document.getElementById('dob');
                if (dobInput) {
                    dobInput.addEventListener('keydown', function(e) {
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
        <div class="container">
            <div class="header">
                <h2>Create Account</h2>
                <p>Join NeoLogin and start your journey</p>
            </div>
            <form method="POST" enctype="multipart/form-data">
                <div class="form-row">
                    <div class="form-group">
                            <label>First Name</label>
                            <input type="text" name="first_name" placeholder="First Name" value="{{ '' if clear_fname else request.form.get('first_name','') }}" required>
                        </div>
                    <div class="form-group">
                            <label>Last Name</label>
                            <input type="text" name="last_name" placeholder="Last Name" value="{{ '' if clear_lname else request.form.get('last_name','') }}" required>
                        </div>
                    </div>
                <div class="form-group">
                    <label>Profile Photo</label>
                    <div class="file-input-wrapper">
                        <input type="file" name="profile_photo" id="profile_photo" accept="image/*">
                        <label for="profile_photo" class="file-input-label">📷 Choose Profile Photo (Optional)</label>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                    <label>Date of Birth</label>
                        <input type="date" name="dob" id="dob" value="{{ '' if clear_dob else request.form.get('dob','') }}" min="1900-01-01" max="2024-12-31" required onkeydown="return false;" onpaste="return false;">
                    </div>
                    <div class="form-group">
                        <label>Gender</label>
                        <select name="gender" id="gender" required>
                            <option value="" disabled selected>Select Gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                    </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Mobile Number</label>
                    <input type="text" id="mobile" name="mobile" placeholder="10-digit mobile number" value="{{ '' if clear_mobile else request.form.get('mobile','') }}" required>
                </div>
                <div class="form-group">
                    <label>Email ID</label>
                    <input type="email" name="email" placeholder="your.email@example.com" value="{{ '' if clear_email else request.form.get('email','') }}" required>
                </div>
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" placeholder="Choose a username" value="{{ '' if clear_username else request.form.get('username','') }}" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <div class="password-container">
                        <input type="password" id="password" name="password" placeholder="Create a strong password" value="{{ '' if clear_password else request.form.get('password','') }}" required onkeyup="checkPassword()">
                        <span class="eye" id="eye1" onclick="togglePassword('password','eye1')">🛡️</span>
                    </div>
                    <ul class="password-rules">
                        <li id="length">At least 8 characters</li>
                        <li id="uppercase">At least one uppercase letter</li>
                        <li id="lowercase">At least one lowercase letter</li>
                        <li id="number">At least one number</li>
                        <li id="special">At least one special character (@$!%*#?&)</li>
                    </ul>
                </div>
                <div class="form-group">
                    <label>Confirm Password</label>
                    <div class="password-container">
                        <input type="password" id="confirm_password" name="confirm_password" placeholder="Re-enter your password" value="{{ '' if clear_password else request.form.get('confirm_password','') }}" required>
                        <span class="eye" id="eye2" onclick="togglePassword('confirm_password','eye2')">🛡️</span>
                    </div>
                </div>
                <button type="submit">Create Account</button>
                </form>
            {% if message %}
                <div class="msg">{{ message }}</div>
            {% endif %}
            <div class="back-link">
                <a href="{{ url_for('signin') }}">Already have an account? Sign In</a>
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

        try:
            # Try email first, then mobile
            user = get_user_by_email(identifier)
            if not user:
                user = get_user_by_mobile(identifier)
        except Exception as e:
            print(f"Database query error during signin: {e}")
            message = "Database error. Please try again later."
            return render_template_string(r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error - NeoLogin</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .error { color: #c0392b; font-size: 18px; }
            a { color: #667eea; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="error">{{ message }}</div>
        <a href="{{ url_for('signin') }}">Go back to Sign In</a>
    </body>
    </html>
    """, message=message)

        if user:
            # Password check
            password_valid = False
            try:
                user_password = user.get('password', '')
                username = user.get('username', '')
                
                if not user_password:
                    password_valid = False
                else:
                    # Check if password is hashed (werkzeug supports multiple formats: pbkdf2, scrypt, $2b$, $2a$)
                    # werkzeug's check_password_hash can handle all formats
                    is_hashed = (
                        user_password.startswith('$2b$') or  # bcrypt
                        user_password.startswith('$2a$') or  # bcrypt (old)
                        user_password.startswith('pbkdf2:') or  # pbkdf2
                        user_password.startswith('scrypt:')  # scrypt
                    )
                    
                    if is_hashed:
                        # Password is hashed, use check_password_hash (works with all werkzeug hash formats)
                        password_valid = check_password_hash(user_password, password)
                    else:
                        # Password is plain text (old format), compare directly
                        password_valid = (user_password == password)
                        # If login successful with plain text, hash it for future use
                        if password_valid and username:
                            update_user_password(username, password)
            except Exception as e:
                print(f"ERROR during password verification: {e}")
                import traceback
                traceback.print_exc()
                password_valid = False
            
            if password_valid:
                # ✅ Successful login
                session['logged_in'] = True
                session['user_email'] = user.get('email', '')
                session['username'] = user.get('username', '')
                return redirect(url_for('dashboard', email=user.get('email', '')))
            else:
                # Failed login attempt
                message = "Invalid password. Please try again."

        else:
            message = "Invalid email/mobile or password"

    return render_template_string(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sign In - NeoLogin</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
            }

            body::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
                opacity: 0.1;
                z-index: -1;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 50px 40px;
                max-width: 450px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.6s ease;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
            }

            .header h2 {
                font-size: 32px;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }

            .header p {
                color: #666;
                font-size: 14px;
            }

            form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .form-group {
                display: flex;
                flex-direction: column;
            }

            label {
                font-size: 14px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }

            input {
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                font-family: 'Poppins', sans-serif;
                transition: all 0.3s ease;
                background: white;
            }

            input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .password-container {
                position: relative;
            }

            .password-container input {
                padding-right: 45px;
            }

            .eye {
                position: absolute;
                right: 15px;
                top: 50%;
                transform: translateY(-50%);
                cursor: pointer;
                font-size: 18px;
                user-select: none;
            }

            button[type="submit"] {
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                margin-top: 10px;
            }

            button[type="submit"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }

            .divider {
                display: flex;
                align-items: center;
                margin: 20px 0;
                color: #999;
                font-size: 14px;
            }

            .divider::before,
            .divider::after {
                content: "";
                flex: 1;
                border-bottom: 1px solid #e0e0e0;
            }

            .divider span {
                padding: 0 15px;
            }

            .signup-btn {
                width: 100%;
                padding: 15px;
                background: white;
                color: #667eea;
                border: 2px solid #667eea;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                text-decoration: none;
                text-align: center;
                display: block;
                transition: all 0.3s ease;
                cursor: pointer;
            }

            .signup-btn:hover {
                background: #667eea;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }

            .forgot-link {
                text-align: center;
                margin-top: 10px;
            }

            .forgot-link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
            }

            .forgot-link a:hover {
                text-decoration: underline;
            }

            .msg {
                background: #ffe6e6;
                color: #c0392b;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                font-weight: 500;
                font-size: 14px;
                margin-top: 15px;
                border-left: 4px solid #c0392b;
            }

            @media (max-width: 600px) {
                .container {
                    padding: 40px 25px;
                }

                .header h2 {
                    font-size: 28px;
                }
            }
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
            window.onload = function() {
                document.getElementById("eye").textContent = "🛡️";
            };
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Welcome Back</h2>
                <p>Sign in to your account</p>
            </div>
            <form method="POST" autocomplete="off">
                <div class="form-group">
                    <label>Email or Mobile Number</label>
                    <input type="text" name="identifier" placeholder="Enter your email or mobile" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <div class="password-container">
                        <input type="password" id="password" name="password" placeholder="Enter your password" autocomplete="new-password" required>
                        <span class="eye" id="eye" onclick="togglePassword('password','eye')">🛡️</span>
                    </div>
                </div>
                <button type="submit">Sign In</button>
            </form>
            <div class="divider">
                <span>OR</span>
            </div>
            <a href="{{ url_for('signup') }}" class="signup-btn">Create New Account</a>
            <div class="forgot-link">
                <a href="{{ url_for('forgot_password') }}">Forgot password?</a>
            </div>
            {% if message %}
            <div class="msg">{{ message }}</div>
            {% endif %}
        </div>
    </body>
    </html>
    """, message=message)
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        # Find user
        user = get_user_by_email(email)
        if not user:
            return render_template_string(r"""
                <script>
                    alert("User not found!");
                    window.location.href = "/forgot-password";
                </script>
            """)

        # Check lock
        lock_until = user.get('lock_until')
        if lock_until:
            now_utc = datetime.utcnow()
            # Convert Firestore timestamp if needed
            if hasattr(lock_until, 'to_datetime'):
                lock_until = lock_until.to_datetime()
            elif isinstance(lock_until, str):
                lock_until = datetime.fromisoformat(lock_until.replace('Z', '+00:00'))
            # Compare UTC times
            if now_utc < lock_until:
                return render_template_string(r"""
                    <script>
                        alert("Too many reset attempts. Try again after 10 minutes.");
                        window.location.href = "/forgot-password";
                    </script>
                """)
            else:
                # Lock expired → reset
                update_user(user['id'], {'failed_attempts': 0, 'lock_until': None})

        # ✅ Generate OTP
        import random
        otp = str(random.randint(100000, 999999))
        otp_expiration = datetime.utcnow() + timedelta(minutes=5)
        update_user(user['id'], {'otp': otp, 'otp_expiration': otp_expiration})

        # ✅ Save email in session for verification
        session['reset_email'] = user.get('email', '')

        # ✅ Show OTP directly on the page (old method)
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Forgot Password - NeoLogin</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
            }

            body::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
                opacity: 0.1;
                z-index: -1;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 50px 40px;
                max-width: 450px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.6s ease;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
            }

            .header h2 {
                font-size: 32px;
                font-weight: 700;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }

            .header p {
                color: #666;
                font-size: 14px;
            }

            form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .form-group {
                display: flex;
                flex-direction: column;
            }

            label {
                font-size: 14px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }

            input {
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                font-family: 'Poppins', sans-serif;
                transition: all 0.3s ease;
                background: white;
            }

            input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            button[type="submit"] {
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                margin-top: 10px;
            }

            button[type="submit"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }

            .back-link {
                text-align: center;
                margin-top: 20px;
            }

            .back-link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
            }

            .back-link a:hover {
                text-decoration: underline;
            }

            @media (max-width: 600px) {
                .container {
                    padding: 40px 25px;
                }

                .header h2 {
                    font-size: 28px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Reset Password</h2>
                <p>Enter your email to receive an OTP</p>
            </div>
                <form method="POST">
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" name="email" placeholder="your.email@example.com" required>
                </div>
                    <button type="submit">Send OTP</button>
                </form>
                <div class="back-link">
                <a href="{{ url_for('signin') }}">Back to Sign In</a>
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

    user = get_user_by_email(email)
    if not user:
        return redirect("/forgot-password")
    
    # Handle OTP from query parameter (fallback when email fails)
    entered_otp = request.args.get("entered_otp", "").strip()

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

        otp_expiration = user.get('otp_expiration')
        if otp_expiration:
            if hasattr(otp_expiration, 'to_datetime'):
                otp_expiration = otp_expiration.to_datetime()
            elif isinstance(otp_expiration, str):
                otp_expiration = datetime.fromisoformat(otp_expiration.replace('Z', '+00:00'))
        if otp_expiration and datetime.utcnow() > otp_expiration:
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
        update_user_password(user.get('username', ''), password)
        
        # Clear OTP from session
        session.pop('reset_otp', None)
        session.pop('reset_otp_expiration', None)

        session.pop("reset_email", None)

        return render_template_string(r"""
            <script>
                alert("Password updated successfully!");
                window.location.href = "/signin";
            </script>
        """)

    return render_template_string(r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify OTP - NeoLogin</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
        }

        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
            opacity: 0.1;
            z-index: -1;
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 25px;
            padding: 50px 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideUp 0.6s ease;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .header h2 {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 14px;
        }

        form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
        }

        label {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }

        input {
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            font-family: 'Poppins', sans-serif;
            transition: all 0.3s ease;
            background: white;
        }

        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .password-container {
            position: relative;
        }

        .password-container input {
            padding-right: 45px;
        }

        .eye {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            font-size: 18px;
            user-select: none;
        }

        button[type="submit"] {
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            margin-top: 10px;
        }

        button[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .password-rules {
            list-style: none;
            padding: 0;
            margin: 10px 0;
            font-size: 12px;
        }

        .password-rules li {
            padding: 5px 0;
            color: #e74c3c;
            transition: all 0.3s ease;
        }

        .password-rules li[style*="green"] {
            color: #27ae60;
        }

        @media (max-width: 600px) {
            .container {
                padding: 40px 25px;
            }

            .header h2 {
                font-size: 28px;
            }
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
    <div class="container">
        <div class="header">
            <h2>Verify OTP</h2>
            <p>Enter the OTP and set your new password</p>
        </div>
        <form method="POST">
            <div class="form-group">
                <label>OTP Code</label>
                <input type="text" name="otp" id="otp" placeholder="Enter 6-digit OTP" value="{{ entered_otp }}" required maxlength="6">
            </div>
            <div class="form-group">
            <label>New Password</label>
            <div class="password-container">
                    <input type="password" id="password" name="password" placeholder="Create a strong password" required onkeyup="checkPassword()">
                <span class="eye" id="eye1" onclick="togglePassword('password','eye1')">🛡️</span>
            </div>
            <ul class="password-rules">
                <li id="length">At least 8 characters</li>
                <li id="uppercase">At least one uppercase letter</li>
                <li id="lowercase">At least one lowercase letter</li>
                <li id="number">At least one number</li>
                <li id="special">At least one special character (@$!%*#?&)</li>
            </ul>
            </div>
            <div class="form-group">
            <label>Confirm Password</label>
            <div class="password-container">
                    <input type="password" id="confirm_password" name="confirm_password" placeholder="Re-enter your password" required>
                <span class="eye" id="eye2" onclick="togglePassword('confirm_password','eye2')">🛡️</span>
            </div>
            </div>
            <button type="submit">Reset Password</button>
        </form>
</div>
</body>
</html>
""", entered_otp=entered_otp)

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

    user = get_user_by_email(email)
    if not user:
        return "Invalid user."

    if request.method == "POST":
        new_password = request.form.get("password").strip()
        confirm_password = request.form.get("confirm_password").strip()

        if new_password != confirm_password:
            return "Passwords do not match."

        # 🔹 Hash the password
        hashed_password = generate_password_hash(new_password, method="sha256")

        # 🔹 Update Firestore
        update_user(user['id'], {'password': hashed_password})

        # Optional: update in-memory dictionary if you maintain one
        if user.get('username') in users:
            users[user.get('username')]["password"] = hashed_password

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

    user = get_user_by_id(str(user_id))
    if user:
        update_user(user['id'], {'is_admin': True})

    return redirect(url_for("view_users"))

# Dashboard/Profile Page
@app.route("/dashboard/<email>")
def dashboard(email):
    # Check if user is logged in
    if not session.get("logged_in"):
        return redirect(url_for('signin'))
    
    # Verify the email matches the logged-in user
    if session.get("user_email") != email:
        return redirect(url_for('signin'))

    # Get user from database
    user_db = get_user_by_email(email)
    if not user_db:
        return redirect(url_for('signin'))
    
    # Simple user data from JSON database
    user = {
        "email": user_db.get('email', ''),
        "username": user_db.get('username', ''),
        "mobile": user_db.get('mobile', ''),
        "first_name": user_db.get('username', '').split('_')[0] if user_db.get('username') else '',  # Extract first part of username
        "last_name": '',  # Not stored in simple DB
        "dob": '',  # Not stored in simple DB
        "profile_photo": "default.png",  # Default
        "gender": ''  # Not stored in simple DB
    }

    # Use username as display name if first_name is not available
    full_name = user['username'] if user['username'] else user['email'].split('@')[0]

    return render_template_string(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - NeoLogin</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                position: relative;
                overflow-x: hidden;
            }

            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: url('https://images.unsplash.com/photo-1517511620798-cec17d428bc0?auto=format&fit=crop&w=1350&q=80') center/cover;
                opacity: 0.1;
                z-index: -1;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
            }

            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                flex-wrap: wrap;
                gap: 15px;
            }

            .logo {
                font-size: 32px;
                font-weight: 700;
                color: white;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .header-actions {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }

            .btn-header {
                padding: 12px 24px;
                background: rgba(255, 255, 255, 0.2);
                backdrop-filter: blur(10px);
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-weight: 500;
                transition: all 0.3s ease;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }

            .btn-header:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }

            .dashboard-card {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
                animation: slideUp 0.6s ease;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .profile-section {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                text-align: center;
                color: white;
                position: relative;
            }

            .profile-picture-container {
                position: relative;
                display: inline-block;
                margin-bottom: 20px;
            }

            .profile-pic {
                width: 150px;
                height: 150px;
                border-radius: 50%;
                object-fit: cover;
                border: 5px solid white;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                transition: transform 0.3s ease;
            }

            .profile-pic:hover {
                transform: scale(1.05);
            }

            .edit-photo-btn {
                position: absolute;
                bottom: 10px;
                right: 10px;
                width: 45px;
                height: 45px;
                background: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                transition: all 0.3s ease;
                border: 3px solid #667eea;
            }

            .edit-photo-btn:hover {
                transform: scale(1.1);
                background: #f0f0f0;
            }

            .edit-photo-btn span {
                font-size: 20px;
            }

            .profile-form {
                display: none;
            }

            .upload-btn {
                margin-top: 15px;
                padding: 10px 25px;
                background: white;
                color: #667eea;
                border: none;
                border-radius: 25px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }

            .upload-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.3);
            }

            .welcome-text {
                font-size: 28px;
                font-weight: 600;
                margin-top: 15px;
            }

            .info-section {
                padding: 40px;
            }

            .section-title {
                font-size: 24px;
                font-weight: 600;
                color: #333;
                margin-bottom: 25px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
            }

            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .info-card {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                padding: 20px;
                border-radius: 15px;
                transition: all 0.3s ease;
                border-left: 4px solid #667eea;
            }

            .info-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }

            .info-label {
                font-size: 12px;
                text-transform: uppercase;
                color: #666;
                font-weight: 600;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }

            .info-value {
                font-size: 18px;
                font-weight: 600;
                color: #333;
            }

            .action-buttons {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                justify-content: center;
                margin-top: 30px;
            }

            .btn-action {
                padding: 15px 35px;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                transition: all 0.3s ease;
                cursor: pointer;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }

            .btn-tasks {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
            }

            .btn-tasks:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(17, 153, 142, 0.4);
            }

            .btn-logout {
                background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
                color: white;
            }

            .btn-logout:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(235, 51, 73, 0.4);
            }

            @media (max-width: 768px) {
                .info-grid {
                    grid-template-columns: 1fr;
                }

                .header {
                    flex-direction: column;
                    text-align: center;
                }

                .profile-section {
                    padding: 30px 20px;
                }

                .info-section {
                    padding: 30px 20px;
                }

                .action-buttons {
                    flex-direction: column;
                }

                .btn-action {
                    width: 100%;
                    justify-content: center;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">✨ NeoLogin</div>
                <div class="header-actions">
                    {% if session.get('is_admin') %}
                    <a href="{{ url_for('view_admins') }}" class="btn-header">👑 View Admins</a>
                    <a href="{{ url_for('admin_menu') }}" class="btn-header">⚙️ Admin Menu</a>
                    {% endif %}
                </div>
            </div>

            <div class="dashboard-card">
                <div class="profile-section">
                    <div class="profile-picture-container">
                        {% if user.get('profile_photo') and user['profile_photo'] != 'default.png' %}
                            <img src="{{ url_for('static', filename='uploads/' + user['profile_photo']) }}"
                                alt="Profile Photo"
                                class="profile-pic"
                                onerror="this.src='{{ url_for('static', filename='uploads/default.png') }}';">
                        {% else %}
                            <img src="{{ url_for('static', filename='uploads/default.png') }}"
                                alt="Profile Photo"
                                class="profile-pic">
                        {% endif %}
                        <form action="{{ url_for('update_profile_photo', email=user['email']) }}" method="POST" enctype="multipart/form-data" class="profile-form">
                            <input type="file" name="profile_photo" id="profile_photo" accept="image/*" required>
                            <button type="submit" class="upload-btn">Upload Photo</button>
                    </form>
                        <label for="profile_photo" class="edit-photo-btn">
                            <span>✏️</span>
                        </label>
                </div>
                    <div class="welcome-text">Welcome, {{ full_name }}!</div>
                </div>

                <div class="info-section">
                    <h2 class="section-title">Profile Information</h2>
                    <div class="info-grid">
                        <div class="info-card">
                            <div class="info-label">Full Name</div>
                            <div class="info-value">{{ full_name }}</div>
            </div>
                        <div class="info-card">
                            <div class="info-label">Email Address</div>
                            <div class="info-value">{{ user['email'] }}</div>
        </div>
                        <div class="info-card">
                            <div class="info-label">Username</div>
                            <div class="info-value">{{ user['username'] }}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Mobile Number</div>
                            <div class="info-value">{{ user['mobile'] }}</div>
                        </div>
                    </div>

                    <div class="action-buttons">
                        <a href="{{ url_for('view_tasks') }}" class="btn-action btn-tasks">
                            📋 View Tasks
                        </a>
                        <a href="{{ url_for('logout') }}" class="btn-action btn-logout">
                            🚪 Logout
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const editBtn = document.querySelector('.edit-photo-btn');
            const fileInput = document.getElementById('profile_photo');
            const form = document.querySelector('.profile-form');

            editBtn.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    form.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """, user=user, full_name=full_name)

# ================= USER TASKS PAGE =================
from flask import flash

@app.route("/view-tasks", methods=["GET", "POST"])
def view_tasks():
    if not session.get("logged_in"):
        return redirect(url_for("signin"))
    
    user_email = session.get("user_email")
    user_obj = get_user_by_email(user_email)
    if not user_obj:
        return redirect(url_for("signin"))
    
    message = ""
    
    # POST: if user is creating a new task
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reward = request.form.get("reward", "").strip()

        if title and description and reward:
            task_data = {
                'title': title,
                'description': description,
                'reward': reward,
                'status': 'pending',
                'created_by': user_obj.get('username', user_obj.get('email', '')),
                'assigned_to': None,
                'active_for_user': False,
                'completed': False
            }
            task_id = create_task(task_data)
            if task_id:
                message = "Task posted successfully!"
            else:
                message = "Failed to create task!"
        else:
            message = "All fields are required!"

    # GET: Show tasks
    tasks = query_tasks({'status': 'approved', 'assigned_to': None})
    if not tasks:
        tasks = query_tasks({'status': 'pending'})  # Show pending tasks if no approved tasks

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
                    <td>{{ t.get('id', '') }}</td>
                    <td>{{ t.get('title', '') }}</td>
                    <td>{{ t.get('description', '') }}</td>
                    <td>{{ t.get('reward', '') }}</td>
                    <td>{{ t.get('status', '') }}</td>
                    <td>
                            {% if t.get('status') == 'approved' and not t.get('assigned_to') %}
                                <a href="{{ url_for('accept_task', task_id=t.get('id', '')) }}" class="accept-btn">
                                    Accept Task
                                </a>
                            {% else %}
                                —
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <p>No tasks available at the moment. Post a new task below!</p>
                    </div>
                {% endif %}

                <h2>Post a New Task</h2>
                <form method="POST" style="background: #f8f9fa; padding: 25px; border-radius: 15px; margin-top: 20px;">
                    <input type="text" name="title" placeholder="Task Title" required style="width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 2px solid #e0e0e0; font-family: 'Poppins', sans-serif;">
                    <textarea name="description" placeholder="Task Description" rows="4" required style="width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 2px solid #e0e0e0; font-family: 'Poppins', sans-serif;"></textarea>
                    <input type="text" name="reward" placeholder="Reward" required style="width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 2px solid #e0e0e0; font-family: 'Poppins', sans-serif;">
                    <button type="submit" class="post-btn" style="padding: 12px 24px; background: #0d6efd; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 10px;">Post Task</button>
                </form>
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{{ url_for('my_tasks') }}" class="post-btn" style="text-decoration: none; display: inline-block; padding: 12px 24px; background: #198754; color: white; border-radius: 8px; font-weight: 600;">
                        📋 My Tasks
                    </a>
                    <a href="{{ url_for('dashboard', email=user_obj.get('email', '')) }}" class="post-btn" style="text-decoration: none; display: inline-block; padding: 12px 24px; background: #667eea; color: white; border-radius: 8px; font-weight: 600; margin-left: 10px;">
                        🏠 Dashboard
                    </a>
                </div>

            </div>
        </div>
    </body>
    </html>
    """, tasks=tasks, user_obj=user_obj, message=message)

@app.route("/accept-task/<int:task_id>")
def accept_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    # 🔥 FIX: get user from DATABASE, not users dict
    user_email = session.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return redirect(url_for("signin"))

    task = get_task_by_id(str(task_id))

    # Only approved & unassigned tasks can be accepted
    if task and task.get('status') == "approved" and not task.get('assigned_to'):
        update_task(task['id'], {
            'assigned_to': user['id'],
            'status': 'accepted',
            'active_for_user': False,  # goes to Pending Tasks
            'completed': False
        })


    return redirect(url_for("view_tasks"))

@app.route("/complete-task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return redirect(url_for("signin"))

    task = get_task_by_id(str(task_id))

    if task and task.get('assigned_to') == user['id'] and not task.get('completed', False):
        update_task(task['id'], {'completed': True, 'active_for_user': False})

    # 🔴 THIS is the fix
    return redirect(url_for("my_tasks"))

@app.route("/my-tasks", methods=["GET", "POST"])
def my_tasks():
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user_obj = get_user_by_email(user_email)
    if not user_obj:
        return redirect(url_for("signin"))
    
    # Fetch tasks
    active_tasks = query_tasks({'assigned_to': user_obj['id'], 'active_for_user': True, 'completed': False})
    active_task = active_tasks[0] if active_tasks else None
    pending_tasks = query_tasks({'assigned_to': user_obj['id'], 'active_for_user': False, 'completed': False})
    completed_tasks = query_tasks({'assigned_to': user_obj['id'], 'completed': True})

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
                        <td>{{ active_task.get('id', '') }}</td>
                        <td>{{ active_task.get('title', '') }}</td>
                        <td>{{ active_task.get('description', '') }}</td>
                        <td>{{ active_task.get('reward', '') }}</td>
                        <td>
                            <form method="POST" action="{{ url_for('complete_task', task_id=active_task.get('id', '')) }}">
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
                        <td>{{ t.get('id', '') }}</td>
                        <td>{{ t.get('title', '') }}</td>
                        <td>{{ t.get('description', '') }}</td>
                        <td>{{ t.get('reward', '') }}</td>
                        <td>
                            <a href="{{ url_for('switch_task', task_id=t.get('id', '')) }}" class="start-btn">
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
    user = get_user_by_email(user_email)
    if not user:
        return redirect(url_for("signin"))

    current_active_tasks = query_tasks({'assigned_to': user['id'], 'active_for_user': True, 'completed': False})
    current_active = current_active_tasks[0] if current_active_tasks else None

    new_task = get_task_by_id(str(task_id))

    if not new_task:
        return redirect(url_for("my_tasks"))

    # 🔥 SAFETY CHECK
    if current_active and current_active.get('id') == new_task.get('id'):
        return redirect(url_for("my_tasks"))

    if current_active:
        update_task(current_active['id'], {'active_for_user': False})

    update_task(new_task['id'], {'active_for_user': True})
    return redirect(url_for("my_tasks"))

@app.route("/start-task/<int:task_id>")
def start_task(task_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))

    user_email = session.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return redirect(url_for("signin"))

    # Deactivate current active task
    current_tasks = query_tasks({'assigned_to': user['id'], 'active_for_user': True, 'completed': False})
    current = current_tasks[0] if current_tasks else None

    if current:
        update_task(current['id'], {'active_for_user': False})

    # Activate selected task
    task = get_task_by_id(str(task_id))
    if task and task.get('assigned_to') == user['id'] and not task.get('completed', False):
        update_task(task['id'], {'active_for_user': True})

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
    # Check if user is logged in
    if not session.get("logged_in"):
        return redirect(url_for('signin'))
    
    # Verify the email matches the logged-in user
    if session.get("user_email") != email:
        return redirect(url_for('signin'))

    # Get user from JSON database
    user_obj = get_user_by_email(email)
    if not user_obj:
        return redirect(url_for('signin'))

    if "profile_photo" not in request.files or request.files["profile_photo"].filename == "":
        return "No file selected", 400

    file = request.files["profile_photo"]
    
    # Use the same upload folder as signup
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Save file securely with user id and timestamp
    from werkzeug.utils import secure_filename
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(original_filename)[1] or '.png'
    filename = f"{user_obj.get('username', 'user')}_{timestamp}{file_ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Delete old photo if exists and not default
    old_photo = user_obj.get('profile_photo', '')
    if old_photo and old_photo != "default.png":
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_photo)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                print(f"Warning: Could not delete old photo {old_path}: {e}")

    # Note: Simple JSON DB doesn't store profile_photo, but file is saved
    # Update in-memory dictionary if it exists
    username = user_obj.get('username', '')
    if username in users:
        users[username]['profile_photo'] = filename

    return redirect(url_for("dashboard", email=email))

# ================= EDIT PROFILE (Simple redirect to dashboard) =================
@app.route("/edit-profile")
def edit_profile():
    """Simple edit profile route - redirects to dashboard since we only store login credentials."""
    if not session.get("logged_in"):
        return redirect(url_for('signin'))
    
    email = session.get("user_email")
    if email:
        return redirect(url_for('dashboard', email=email))
    return redirect(url_for('signin'))

# ================= VIEW USERS (ADMIN ONLY) =================
@app.route("/view-users")
def view_users():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    # Get all users from Firestore
    all_users_docs = db.collection('users').stream() if db else []
    all_users = []
    for doc in all_users_docs:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        all_users.append(user_data)

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
        <td>{{ u.get('id', '') }}</td>
        <!-- First Name -->
        <td>
            <form method="POST" action="{{ url_for('update_name', user_id=u.get('id', '')) }}">
                <input type="text"
                        name="first_name"
                        value="{{ u.get('first_name', '') }}"
                        class="username-input"
                        disabled>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <td>
            <form method="POST" action="{{ url_for('update_name', user_id=u.get('id', '')) }}">
                <input type="text"
                        name="last_name"
                        value="{{ u.get('last_name', '') }}"
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
                action="{{ url_for('update_username', user_id=u.get('id', '')) }}">
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
            <form method="POST" action="{{ url_for('update_gender', user_id=u.get('id', '')) }}">
                <select name="gender" class="username-input" disabled>
                    <option value="Male" {% if u.get('gender') == 'Male' %}selected{% endif %}>Male</option>
                    <option value="Female" {% if u.get('gender') == 'Female' %}selected{% endif %}>Female</option>
                    <option value="Other" {% if u.get('gender') == 'Other' %}selected{% endif %}>Other</option>
                </select>
                <span class="pen" onclick="enableEdit(this)">✏️</span>
                <button type="submit" class="save-btn">💾</button>
            </form>
        </td>
        <!-- ROLE -->
        <td>
            {% if u.get('is_admin', False) %}
                <b style="color:green;">ADMIN</b>
            {% else %}
                USER
            {% endif %}
        </td>
        <!-- ADMIN ACTION -->
        <td>
            {% if not u.get('is_admin', False) %}
                <a href="{{ url_for('make_admin', user_id=u.get('id', '')) }}"
                    onclick="return confirm('Make this user an admin?')">
                    👑 Make Admin 👑
                </a>
            {% elif u.get('is_admin', False) and u.get('email', '') != session.get('user_email') %}
                <a href="{{ url_for('remove_admin', user_id=u.get('id', '')) }}"
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
    existing = get_user_by_username(new_username)
    if existing and existing.get('id') != str(user_id):
        return redirect(url_for("view_users"))


    user = get_user_by_id(str(user_id))
    if user:
        old_username = user.get('username', '')
        update_user(user['id'], {'username': new_username})

        # Sync in-memory dict
        if old_username in users:
            users[new_username] = users.pop(old_username)
            users[new_username]["username"] = new_username

        # 🔥 ADD THESE 3 LINES ONLY
        if session.get("user_email") == user.get('email', ''):
            session.clear()
            return redirect(url_for("signin"))

    return redirect(url_for("view_users"))

# ================= UPDATE FIRST / LAST NAME (ADMIN ONLY) =================
@app.route("/update-name/<int:user_id>", methods=["POST"])
def update_name(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = get_user_by_id(str(user_id))
    if not user:
        return redirect(url_for("view_users"))

    new_first = request.form.get("first_name")
    new_last = request.form.get("last_name")

    updates = {}
    if new_first:
        updates['first_name'] = new_first
        username = user.get('username', '')
        if username in users:
            users[username]["first_name"] = new_first

    if new_last:
        updates['last_name'] = new_last
        username = user.get('username', '')
        if username in users:
            users[username]["last_name"] = new_last

    if updates:
        update_user(user['id'], updates)

    return redirect(url_for("view_users"))

# ================= UPDATE GENDER (ADMIN ONLY) =================
@app.route("/update-gender/<int:user_id>", methods=["POST"])
def update_gender(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = get_user_by_id(str(user_id))
    if user:
        new_gender = request.form.get("gender", "").strip()
        if new_gender:
            update_user(user['id'], {'gender': new_gender})
    return redirect(url_for("view_users"))

# ================= UPDATE RECOVERY KEYWORD (ADMIN ONLY) =================
@app.route("/update-recovery/<int:user_id>", methods=["POST"])
def update_recovery(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = get_user_by_id(str(user_id))
    if user:
        new_keyword = request.form.get("recovery_keyword", "").strip()
        if new_keyword:
            from werkzeug.security import generate_password_hash
            update_user(user['id'], {'recovery_keyword_hash': generate_password_hash(new_keyword)})
    return redirect(url_for("view_users"))

# ================= DELETE USER (ADMIN ONLY) =================
@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    user = get_user_by_id(str(user_id))
    
    if user:
        # Delete from Firestore
        if db:
            db.collection('users').document(user['id']).delete()
        # Remove from in-memory dict
        username = user.get('username', '')
        if username in users:
            users.pop(username, None)

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

    # Get all tasks from Firestore ordered by ID descending
    all_tasks_docs = db.collection('tasks').order_by('__name__', direction=firestore.Query.DESCENDING).stream() if db else []
    all_tasks = []
    for doc in all_tasks_docs:
        task_data = doc.to_dict()
        task_data['id'] = doc.id
        all_tasks.append(task_data)

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

    task = get_task_by_id(str(task_id))
    if task:
        update_task(task['id'], {'status': 'approved'})
    return redirect(url_for("admin_task_management"))

# ================= ADMIN TASK MANAGEMENT =================
@app.route("/admin-task-management", methods=["GET", "POST"])
def admin_task_management():
    if not session.get("logged_in") or not session.get("is_admin"):
        return redirect(url_for("signin"))

    # Approve a task
    if request.method == "POST":
        task_id = request.form.get("task_id")
        task = get_task_by_id(str(task_id))
        if task:
            update_task(task['id'], {'status': 'approved'})
            flash("Task approved successfully!", "success")
        return redirect(url_for("admin_task_management"))

    # Show all tasks
    all_tasks_docs = db.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING).stream() if db else []
    tasks = []
    for doc in all_tasks_docs:
        task_data = doc.to_dict()
        task_data['id'] = doc.id
        # Get creator and assignee usernames
        if task_data.get('created_by'):
            creator = get_user_by_id(task_data['created_by'])
            task_data['creator'] = {'username': creator.get('username', 'Unknown')} if creator else None
        if task_data.get('assigned_to'):
            assignee = get_user_by_id(task_data['assigned_to'])
            task_data['assignee'] = {'username': assignee.get('username', 'Unknown')} if assignee else None
        tasks.append(task_data)
    
    # Get all users for display
    all_users_docs = db.collection('users').stream() if db else []
    users_list = []
    for doc in all_users_docs:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        users_list.append(user_data)

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
                    <form method="GET" action="{{ url_for('assign_task', task_id=t.get('id', '')) }}">
                        <select name="user_id" required>
                            <option value="">Assign to user</option>
                            {% for u in users %}
                                <option value="{{ u.get('id', '') }}">{{ u.get('username', '') }}</option>
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
    task = get_task_by_id(str(task_id))
    user = get_user_by_id(str(user_id))

    if task and user:
        existing_active_tasks = query_tasks({'assigned_to': user['id'], 'active_for_user': True, 'completed': False})
        existing_active = existing_active_tasks[0] if existing_active_tasks else None

        updates = {
            'assigned_to': user['id'],
            'status': 'accepted',
            'completed': False
        }
        
        if existing_active:
            updates['active_for_user'] = False   # goes to Pending
        else:
            updates['active_for_user'] = True    # becomes Active

        update_task(task['id'], updates)

    return redirect(url_for("admin_task_management"))

@app.route("/view-admins", methods=["GET", "POST"])
def view_admins():
    # Get all admins from Firestore
    all_admins_docs = db.collection('users').where('is_admin', '==', True).stream() if db else []
    all_admins = []
    for doc in all_admins_docs:
        admin_data = doc.to_dict()
        admin_data['id'] = doc.id
        all_admins.append(admin_data)
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
                    <td>{{ admin.get('id', '') }}</td>
                    <td>{{ admin.get('first_name', '') }}</td>
                    <td>{{ admin.get('last_name', '') }}</td>
                    <td>{{ admin.get('email', '') }}</td>
                    <td>{{ admin.get('mobile', '') }}</td>
                    <td>{{ admin.get('username', '') }}</td>
                    <td>
                        {% if admin.get('email', '') != logged_in_email %}
                            <a href="{{ url_for('report_admin', user_id=admin.get('id', '')) }}"
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
    user = get_user_by_id(str(user_id))
    current_admin_email = session.get("user_email")
    if user and user.get('is_admin', False) and user.get('email', '') != current_admin_email:
        update_user(user['id'], {'is_admin': False})  # ✅ revert to regular user

    return redirect(url_for("view_users"))

@app.route("/report-admin/<int:user_id>")
def report_admin(user_id):
    if not session.get("logged_in"):
        return redirect(url_for("signin"))
    admin = get_user_by_id(str(user_id))
    if admin:
        update_user(admin['id'], {'reported': True})

    return redirect(url_for("view_admins"))

# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
