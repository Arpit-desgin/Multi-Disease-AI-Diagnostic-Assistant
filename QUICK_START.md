# 🚀 QUICK START REFERENCE

## 📋 LOCAL SETUP (Copy-Paste Commands)

### Windows PowerShell

```powershell
# 1. BACKEND SETUP
cd C:\Projects\MedIntel\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install aiosqlite

# 2. CREATE .env (paste this into backend\.env)
# DATABASE_URL=sqlite+aiosqlite:///./medintel.db
# SECRET_KEY=dev-key-change-in-production
# GEMINI_API_KEY=
# CLOUDINARY_CLOUD_NAME=
# CLOUDINARY_API_KEY=
# CLOUDINARY_API_SECRET=
# REDIS_URL=
# ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# 3. START BACKEND (Terminal 1)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Open: http://localhost:8000/docs
```

```powershell
# 4. FRONTEND SETUP (Terminal 2)
cd C:\Projects\MedIntel\frontend
npm install
npm run dev
# Open: http://localhost:5173
```

---

## 🔑 API KEYS (3 minutes to set up)

| Service | Link | Variable |
|---------|------|----------|
| **Google AI** | https://aistudio.google.com/app/apikey | `GEMINI_API_KEY` |
| **Cloudinary** | https://cloudinary.com (Dashboard) | `CLOUDINARY_*` |
| **Secret Key** | `python -c "import secrets; print(secrets.token_hex(32))"` | `SECRET_KEY` |

---

## 🌐 DEPLOY TO RENDER

### Step 1: Push to GitHub
```powershell
cd backend
git add .
git commit -m "Ready for production"
git push
```

### Step 2: Create Render Web Service
1. https://render.com → New Web Service
2. Connect GitHub repo
3. Settings:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Region:** Singapore (Free)
4. Add all .env variables
5. Deploy

### Step 3: Test
```
https://medical-ai-backend.onrender.com/health
https://medical-ai-backend.onrender.com/docs
```

---

## 📦 ADD ML MODELS

Place in `backend/app/ml_models/`:
- `lung_cancer_model.h5`
- `skin_disease_model.h5`
- `diabetic_retinopathy_model.h5`

Then:
```powershell
git add app/ml_models/
git commit -m "Add models"
git push
```

---

## ✅ VERIFICATION TESTS

```powershell
# Local Backend
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"}

# Production Backend
curl https://medical-ai-backend.onrender.com/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

---

## 🆘 COMMON ISSUES

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: tensorflow` | `pip install tensorflow-cpu` (wait 5min) |
| CORS errors | Update `ALLOWED_ORIGINS` in Render env |
| Model not found | Commit to `app/ml_models/` and push |
| Server slow | Normal on Render free tier (cold start) |
| Keeps sleeping | Use https://uptimerobot.com to ping `/health` every 14min |

---

## 📱 FRONTEND ENV (.env.local)

```
VITE_API_URL=http://localhost:8000/api/v1
```

For production:
```
VITE_API_URL=https://medical-ai-backend.onrender.com/api/v1
```

---

## 📊 FOLDER STRUCTURE

```
medical-ai/
├── backend/               ← FastAPI app
│   ├── app/
│   │   ├── main.py       ← Entry point
│   │   ├── config.py     ← Settings (.env file)
│   │   ├── database.py   ← DB connection
│   │   ├── routes/       ← API endpoints
│   │   ├── models/       ← DB models
│   │   ├── schemas/      ← Pydantic schemas
│   │   ├── services/     ← Business logic
│   │   ├── ml_models/    ← Your .h5 files go HERE
│   │   └── utils/        ← Helpers
│   ├── requirements.txt
│   ├── .env              ← Your secrets (don't commit!)
│   └── venv/             ← Virtual environment
│
├── frontend/             ← React app
│   ├── src/
│   ├── package.json
│   ├── .env.local        ← API URL
│   └── node_modules/
│
└── SETUP_AND_DEPLOYMENT_GUIDE.md ← Read this start!
```

---

## 🎯 ENDPOINTS

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login user |
| POST | `/api/v1/diagnosis/lung-cancer` | Diagnose lung cancer |
| POST | `/api/v1/diagnosis/skin-disease` | Diagnose skin disease |
| POST | `/api/v1/diagnosis/diabetic-retinopathy` | Diagnose DR |
| POST | `/api/v1/chatbot/message` | Chat with AI |
| GET | `/api/v1/hospitals/nearby` | Find nearby hospitals |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI (interactive) |

---

## 💡 TIPS

1. **Local testing first:** Always test `localhost` before deploying
2. **Check logs:** `http://localhost:8000/health` shows status
3. **Swagger UI:** Use `/docs` to test all endpoints
4. **Rate limiting:** Auth: 5/min, Diagnosis: 10/min, Chat: 30/min
5. **Cold starts:** First request on Render takes 30-60s (normal for free tier)

---

Created: March 27, 2026  
Version: 1.0
