# KisaanLink Module 1 — Full Stack

A simple farmer-first FastAPI + MongoDB + HTML/CSS/JavaScript application.

## Theme
- Light theme by default
- Green, gold and beige palette
- Crop-related icons and subtle animations
- Responsive layout for desktop and mobile
- Large, simple controls for farmer usability

## Run locally

1. Create `.env` from `.env.example`.
2. Put your MongoDB connection string in `MONGO_URI`.
3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Start the server from this folder:

```powershell
python -m uvicorn main:app --reload
```

5. Open `http://127.0.0.1:8000`
6. API documentation: `http://127.0.0.1:8000/docs`

## Authentication

Registration and password login return a JWT. Protected endpoints use:

`Authorization: Bearer <token>`

Password reset uses a development OTP returned by the API so it can be tested without Firebase SMS billing. Do not expose this development OTP flow in production.

## Render

Set the environment variables from `.env.example` in the Render service. The app binds to the `PORT` supplied by Render when launched through `main.py`; for a Render start command you can use:

```text
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```
