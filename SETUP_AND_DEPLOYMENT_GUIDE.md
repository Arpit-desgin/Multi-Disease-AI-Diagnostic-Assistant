# 🏥 MedIntel — Complete Setup & Deployment Guide

**For: Windows + VS Code + FastAPI Backend + React Frontend**

---

## ✅ PHASE 1 — LOCAL MACHINE SETUP

### Step 1: Verify Prerequisites

Open PowerShell and check you have these installed:

```powershell
python --version        # Need 3.11 or higher
git --version
node --version          # Need 16 or higher
```

**If Python is NOT installed:**
1. Go to https://www.python.org/downloads/
2. Download "Windows installer (64-bit)"
3. During install: ✅ **Check "Add Python to PATH"**
4. Click "Install Now"
5. Restart PowerShell

**If Git is NOT installed:**
1. Go to https://git-scm.com/downloads
2. Download Windows version and run installer
3. Use default settings, click Next until done

**If Node.js is NOT installed:**
1. Go to https://nodejs.org/
2. Download LTS version
3. Run installer with default settings

---

### Step 2: Clone & Open Project

```powershell
# Navigate to Desktop
cd Desktop

# Clone the repository
git clone https://github.com/Arpit-desgin/Multi-Disease-AI-Diagnostic-Assistant.git medical-ai
cd medical-ai

# Open in VS Code
code .
```

---

### Step 3: Set Up Backend Virtual Environment

```powershell
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# You should see (venv) at the start of your prompt
```

---

### Step 4: Install Backend Dependencies

```powershell
# Make sure you're in the backend folder with venv activated
pip install -r requirements.txt
pip install aiosqlite

# This may take 5-10 minutes. TensorFlow is large.
# Do NOT cancel this — let it finish.
```

---

### Step 5: Create .env File in Backend

Create a new file `backend\.env`:

```ini
# Database (SQLite for local development)
DATABASE_URL=sqlite+aiosqlite:///./medintel.db

# Security
SECRET_KEY=dev-key-change-in-production

# External APIs (get these from Phase 2)
GEMINI_API_KEY=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Optional
REDIS_URL=

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

### Step 6: Start Backend Server

```powershell
# Make sure venv is activated
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Success!** Open http://localhost:8000/docs in your browser.

You should see the **Swagger UI** with all API endpoints listed. If you see this, your backend works!

---

### Step 7: Set Up Frontend

Open a **NEW PowerShell terminal** (keep backend running in the first one):

```powershell
# From the project root
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

✅ **Success!** Open http://localhost:5173 in your browser.

You should see the **MedIntel web app**. If both backend and frontend load, your local setup is complete! 🎉

---

## 🔑 PHASE 2 — GET FREE API KEYS

You need API keys for 3 external services (all free, no credit card):

### Service 1: Database — Neon.tech (Free PostgreSQL)

**Later (optional):** For production, use a proper PostgreSQL instead of SQLite.

For now, SQLite works. Skip this until you deploy.

---

### Service 2: AI Chat — Google AI Studio (Free Gemini API)

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Click **"Create API key in new project"**
5. Copy the key (starts with `AIza`)
6. In `backend\.env`, set:
   ```ini
   GEMINI_API_KEY=AIza...your_copied_key
   ```

**Notes:**
- Free tier: 15 requests/minute, 1M tokens/day
- No credit card needed
- Perfect for testing

---

### Service 3: Image Storage — Cloudinary (Free Cloud Storage)

1. Go to: https://cloudinary.com
2. Click **"Sign Up For Free"**
3. Sign up with Google account
4. After signup, you're on the **Dashboard**
5. Scroll down to find **"Account Details"** section
6. You'll see:
   - **Cloud Name** (looks like: `abc123def`)
   - **API Key** (looks like: `123456789012345`)
   - **API Secret** (looks like: `abc_def_secret_key_xyz`)
7. Copy all 3 and add to `backend\.env`:
   ```ini
   CLOUDINARY_CLOUD_NAME=abc123def
   CLOUDINARY_API_KEY=123456789012345
   CLOUDINARY_API_SECRET=abc_def_secret_key_xyz
   ```

**Notes:**
- Free tier: 25GB storage, 1000 transformations/month
- No credit card needed
- Used for storing scan images

---

### Service 4: Generate Secret Key

Run this command in PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and add to `backend\.env`:

```ini
SECRET_KEY=<paste_the_output_here>
```

---

### ✅ Your .env Should Now Look Like:

```ini
DATABASE_URL=sqlite+aiosqlite:///./medintel.db
SECRET_KEY=a1b2c3d4e5f6...your_long_key...
GEMINI_API_KEY=AIzaSy...your_gemini_key...
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your_secret_xyz
REDIS_URL=
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

Test your backend again:
```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs — all endpoints should work now! ✅

---

## 🚀 PHASE 3 — DEPLOY TO RENDER (FREE)

Render is a free hosting platform perfect for testing. Your backend will get a public URL like `https://medical-ai-backend.onrender.com`.

### Step 1: Push Code to GitHub

First, create a GitHub repo:

1. Go to https://github.com/new
2. Create a repo named `medical-ai-backend` (private is fine)
3. Follow the instructions to "push an existing repository"

Or use these commands:

```powershell
cd C:\Projects\MedIntel\backend

git init
git add .
git commit -m "Initial MedIntel backend setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/medical-ai-backend.git
git push -u origin main
```

---

### Step 2: Create Render Account

1. Go to https://render.com
2. Click **"Sign Up"**
3. Sign up with **GitHub account** (easier)

---

### Step 3: Deploy Backend Web Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Click **"Connect GitHub"** and select your `medical-ai-backend` repo
3. Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | medical-ai-backend |
| **Region** | Singapore (closest to India) |
| **Branch** | main |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | FREE |

4. Scroll down to **"Environment"** section
5. Click **"Add Environment Variable"** and add each from your `.env`:

```
DATABASE_URL = sqlite+aiosqlite:///./medintel.db
SECRET_KEY = (your_secret_key)
GEMINI_API_KEY = (your_key)
CLOUDINARY_CLOUD_NAME = (your_name)
CLOUDINARY_API_KEY = (your_key)
CLOUDINARY_API_SECRET = (your_secret)
ALLOWED_ORIGINS = ["https://yourfrontend.com","http://localhost:3000"]
```

6. Click **"Create Web Service"**
7. Wait **3-5 minutes** for first deploy

Once deployed, you'll get a URL like: `https://medical-ai-backend.onrender.com`

---

### Step 4: Verify Deployment

Test these URLs in your browser:

```
https://medical-ai-backend.onrender.com/health
```

Should return:
```json
{"status": "healthy", "version": "1.0.0"}
```

And:
```
https://medical-ai-backend.onrender.com/docs
```

Should show the Swagger UI.

✅ If both work, your backend is live!

---

### Step 5: (Optional) Add Redis Cache

For now, skip this. It's optional and can be added later.

---

## 🎨 PHASE 4 — DEPLOY FRONTEND

### Frontend Setup (Local First)

```powershell
cd frontend

# Install dependencies
npm install

# Create .env.local file
# Add this content:
```

Create `frontend\.env.local`:

```
VITE_API_URL=http://localhost:8000/api/v1
```

```powershell
# Start frontend
npm run dev
```

Open http://localhost:5173 ✅

---

### Deploy Frontend to Vercel

1. Push frontend code to GitHub:

```powershell
cd C:\Projects\MedIntel\frontend

git add .
git commit -m "Frontend setup"
git push
```

2. Go to https://vercel.com
3. Click **"Sign Up"** with GitHub
4. Click **"New Project"**
5. Select your frontend repo
6. Add environment variable:
   ```
   VITE_API_URL=https://medical-ai-backend.onrender.com/api/v1
   ```
7. Click **"Deploy"**

Your frontend will get a URL like: `https://medical-ai.vercel.app`

---

### Update Backend ALLOWED_ORIGINS

After frontend deploys:

1. Go to Render dashboard
2. Select your web service
3. Go to **Environment**
4. Update `ALLOWED_ORIGINS`:
   ```
   ["https://medical-ai.vercel.app","http://localhost:5173"]
   ```
5. Click **"Save"** (Render auto-redeploys)

---

## 📊 PHASE 5 — ADD YOUR ML MODELS

Your `.h5` model files must be placed in `backend/app/ml_models/`

### Option A: Small Models (< 100MB)

1. Download or train your models:
   - `lung_cancer_model.h5`
   - `skin_disease_model.h5`
   - `diabetic_retinopathy_model.h5`

2. Place them in: `backend/app/ml_models/`

3. Push to GitHub:
   ```powershell
   cd backend
   git add app/ml_models/
   git commit -m "Add ML models"
   git push
   ```

4. Render will auto-redeploy

---

### Option B: Large Models (> 100MB)

Use Git LFS:

```powershell
# Install Git LFS
git lfs install

# Track .h5 and .pt files
git lfs track "*.h5"
git lfs track "*.pt"

# Add and push
git add .gitattributes app/ml_models/
git commit -m "Add models via LFS"
git push
```

---

## ✅ FINAL CHECKLIST

Print this and check off as you go:

### Services Setup
- [ ] Google AI Studio: GEMINI_API_KEY acquired
- [ ] Cloudinary: 3 credentials acquired
- [ ] SECRET_KEY: Generated and added to .env
- [ ] .env file: Complete and tested locally

### Local Development
- [ ] Backend starts with `uvicorn app.main:app --reload --port 8000`
- [ ] http://localhost:8000/docs loads Swagger UI
- [ ] Frontend starts with `npm run dev`
- [ ] http://localhost:5173 loads the web app
- [ ] Backend and frontend can communicate

### Production Deployment
- [ ] Code pushed to GitHub
- [ ] Render Web Service created and deployed
- [ ] https://medical-ai-backend.onrender.com/health returns 200
- [ ] https://medical-ai-backend.onrender.com/docs loads Swagger
- [ ] Frontend deployed to Vercel
- [ ] ALLOWED_ORIGINS updated on Render with frontend URL
- [ ] Both frontend and backend redeployed

### ML Models
- [ ] lung_cancer_model.h5 placed in backend/app/ml_models/
- [ ] skin_disease_model.h5 placed in backend/app/ml_models/
- [ ] diabetic_retinopathy_model.h5 placed in backend/app/ml_models/
- [ ] Models committed and pushed to GitHub

### Final Tests
- [ ] Load frontend: https://medical-ai.vercel.app
- [ ] Upload a test image: sees prediction result
- [ ] Chat works: chatbot responds with context
- [ ] Risk assessment calculates correctly

---

## ⚠️ CRITICAL NOTES

### Render Free Tier Limitations

- **Sleeps after 15 minutes** of inactivity
- **First request takes 30-60 seconds** (cold start)
- **Monthly limits**: 750 compute hours (≈ always free if you don't exceed)

To prevent sleep:
1. Go to https://uptimerobot.com
2. Create free account
3. Add monitor: `https://medical-ai-backend.onrender.com/health`
4. Set to ping every **14 minutes**
5. Your server never sleeps! ✅

---

### Common Errors & Fixes

**Error: `ModuleNotFoundError: No module named 'tensorflow'`**
- Fix: `pip install tensorflow-cpu`
- Takes 5+ minutes — don't cancel

**Error: `CORS error in browser`**
- Fix: Update ALLOWED_ORIGINS in Render environment
- Wait for auto-redeploy (2-3 minutes)

**Error: `Database connection failed`**
- For local: Just use SQLite (default)
- For production: Add real PostgreSQL from Neon.tech later

**Error: `Model file not found`**
- Ensure .h5 files are in `app/ml_models/`
- Commit and push to GitHub
- Render will re-download on next deploy

---

## 🎉 SUCCESS!

If your checklist is 100% complete:

1. ✅ Your backend is live at `https://medical-ai-backend.onrender.com`
2. ✅ Your frontend is live at `https://medical-ai.vercel.app`
3. ✅ Users can upload images and get AI predictions
4. ✅ ChatBot works with diagnosis context
5. ✅ Everything is auto-deployed via GitHub

**Next Steps:**
- Connect custom domain
- Add more diseases/models
- Improve UI/UX
- Upgrade to paid Render tier for production

---

## 📞 GETTING HELP

- **Backend errors?** Check `https://medical-ai-backend.onrender.com/docs`
- **Model issues?** Check Render logs: Dashboard → Logs tab
- **CORS problems?** Update ALLOWED_ORIGINS
- **Out of memory?** Render free tier: 512MB RAM (models may need upgrade)

---

**Created:** March 27, 2026  
**Project:** MedIntel - Multi-Disease AI Diagnostic Assistant
