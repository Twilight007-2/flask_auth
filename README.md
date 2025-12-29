# NeoLogin - Flask Authentication System

A secure and user-friendly authentication system built with Flask.

## Features

- User registration and authentication
- Profile management with photo uploads
- Task management system
- Admin dashboard
- Password reset via OTP
- Account locking after failed attempts

## Local Development

### Prerequisites

- Python 3.13.4
- pip

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The app will run on `http://localhost:5000`

### Environment Variables (Optional)

For local development, you can set these environment variables:

- `SECRET_KEY`: Flask secret key (default: 'neologin_secret_change_in_production')
- `USE_MYSQL`: Set to 'true' to use MySQL instead of SQLite
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`: MySQL connection details
- `ADMIN_EMAIL`: Admin email (default: 'admin@neologin.com')
- `ADMIN_PASSWORD`: Admin password (default: 'Admin@123')
- `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`: Email configuration

## Deployment on Render

### Steps to Deploy

1. **Push your code to GitHub/GitLab/Bitbucket**

2. **Create a new Web Service on Render:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your repository

3. **Configure the service:**
   - **Name**: neologin (or your preferred name)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

4. **Add Environment Variables in Render Dashboard:**
   - `SECRET_KEY`: Generate a strong secret key (you can use: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ADMIN_EMAIL`: Your admin email
   - `ADMIN_PASSWORD`: Your admin password
   - `DATABASE_URL`: (Optional) If using Render PostgreSQL, this will be auto-set
   - `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`: (Optional) For email features

5. **Add PostgreSQL Database (Optional but Recommended):**
   - In Render Dashboard, click "New +" → "PostgreSQL"
   - After creation, the `DATABASE_URL` will be automatically available to your web service
   - The app will automatically use PostgreSQL if `DATABASE_URL` is set

6. **Deploy:**
   - Click "Create Web Service"
   - Render will build and deploy your application

### Using render.yaml (Alternative Method)

If you prefer using `render.yaml`, you can:
1. Push your code with `render.yaml` included
2. In Render Dashboard, select "Apply render.yaml" when creating the service
3. Render will automatically configure everything from the YAML file

### Important Notes

- **File Uploads**: User-uploaded files are stored in `static/uploads/`. On Render, these are stored in the ephemeral filesystem and will be lost on redeploy. Consider using cloud storage (AWS S3, Cloudinary) for production.
- **Database**: SQLite works for development, but PostgreSQL (available on Render) is recommended for production.
- **Static Files**: Make sure to configure static file serving in your Render service settings.

## Default Admin Credentials

- Email: `admin@neologin.com`
- Password: `Admin@123`

**⚠️ Change these in production!**

## License

MIT

