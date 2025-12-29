# Quick Deployment Guide for Render

## Prerequisites
1. GitHub/GitLab/Bitbucket account with your code pushed
2. Render account (sign up at https://render.com)

## Step-by-Step Deployment

### 1. Push Your Code to Git
```bash
git init
git add .
git commit -m "Initial commit - Ready for Render deployment"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. Create Render Account & Service

1. Go to https://dashboard.render.com
2. Sign up/Login
3. Click **"New +"** → **"Web Service"**
4. Connect your Git repository (GitHub/GitLab/Bitbucket)
5. Select your repository

### 3. Configure Service Settings

**Basic Settings:**
- **Name**: `neologin` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### 4. Add Environment Variables

Click **"Environment"** tab and add:

**Required:**
```
SECRET_KEY = <generate a strong secret key>
```
Generate secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

**Optional but Recommended:**
```
ADMIN_EMAIL = admin@neologin.com
ADMIN_PASSWORD = <your-secure-password>
```

**For Email Features (Optional):**
```
MAIL_USERNAME = yourgmail@gmail.com
MAIL_PASSWORD = your_app_password
MAIL_DEFAULT_SENDER = yourgmail@gmail.com
```

### 5. Add PostgreSQL Database (Recommended)

1. In Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Name it: `neologin-db`
3. Select same region as your web service
4. Click **"Create Database"**
5. Render automatically sets `DATABASE_URL` for your web service

**Note:** The app will automatically use PostgreSQL if `DATABASE_URL` is available.

### 6. Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete (usually 2-5 minutes)
3. Your app will be live at: `https://neologin.onrender.com` (or your custom domain)

### 7. Initialize Database

After first deployment, the database tables will be created automatically on first request.

## Troubleshooting

### Build Fails
- Check build logs in Render dashboard
- Ensure all dependencies are in `requirements.txt`
- Verify Python version in `runtime.txt`

### Database Connection Issues
- Verify `DATABASE_URL` is set (if using PostgreSQL)
- Check database is in same region as web service
- Review database connection logs

### App Crashes
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `SECRET_KEY` is set

### Static Files Not Loading
- Verify `static/` folder structure
- Check file paths in templates
- Ensure proper URL routing

## Post-Deployment

1. **Change Default Admin Credentials** - Update `ADMIN_EMAIL` and `ADMIN_PASSWORD`
2. **Set Strong SECRET_KEY** - Generate a new one and update
3. **Configure Custom Domain** (Optional) - In Render dashboard → Settings → Custom Domain
4. **Set up Email** (Optional) - Configure Gmail app password for password reset features

## File Uploads Note

⚠️ **Important**: Files uploaded to `static/uploads/` are stored in ephemeral filesystem on Render. They will be lost on redeploy. For production, consider:
- AWS S3
- Cloudinary
- Google Cloud Storage
- Other cloud storage solutions

## Support

- Render Docs: https://render.com/docs
- Render Status: https://status.render.com

