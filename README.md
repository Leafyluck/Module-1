# KisaanLink Module 1 — Full Stack

Farmer-first FastAPI + MongoDB + HTML/CSS/JavaScript application.

## Included

- Light theme by default
- Green, gold and beige UI
- Crop-related icons and subtle animations
- Responsive farmer-friendly interface
- Three account types: Farmer, FPO, Bulk Buyer
- Email OTP verification during registration
- Password login with email or mobile number
- 24-hour JWT access-token default (`1440` minutes)
- Role-aware profiles and dashboards
- Farmer farm profile
- Existing forecast API retained

## Account flow

`Register → Email OTP → Verify → Login → Role dashboard`

Email is required for all three account types. Mobile number is optional.

## Local setup

1. Copy `.env.example` to `.env`.
2. Add your MongoDB URI.
3. Add Gmail SMTP credentials. Use a Google App Password.
4. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

5. Start:

```powershell
python -m uvicorn main:app --reload
```

6. Open `http://127.0.0.1:8000`
7. API docs: `http://127.0.0.1:8000/docs`

## Render

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set these Render environment variables:

```text
MONGO_URI
JWT_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-gmail@gmail.com
```

Never commit `.env` or real SMTP credentials.

## Git workflow for the team

From the project folder:

```powershell
git pull origin main
git add .
git commit -m "Update KisaanLink Module 1"
git push origin main
```

Render automatically redeploys after a successful push to the connected `main` branch.

For simultaneous development, each developer should work on their own branch and open a pull request instead of overwriting another developer's work.
