# FinTrack INR

FinTrack INR is a secure personal finance web application for Indian users built with Flask, MongoDB Atlas, Flask-Login, Flask-WTF, Flask-Limiter, bcrypt, ReportLab, Pandas, NumPy, Bootstrap 5, and Chart.js.

## Features

- OTP-based registration using secure SMTP over STARTTLS
- Login, logout, password change, and account deletion
- Multiple wallets and wallet balance tracking
- Income and expense tracking with user isolation
- Expense and income categories with seeded defaults
- Dashboard summaries, charts, and recent transactions
- Weekly, monthly, yearly, and financial-year reports
- Multi-page PDF export with ReportLab
- Secure headers, CSRF protection, and rate limiting

## Setup

1. Create a virtual environment with Python 3.12+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in:
- `SECRET_KEY`
- `MONGO_URI`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_EMAIL`
- `SMTP_PASSWORD`

4. Point `MONGO_URI` to MongoDB Atlas.
5. Make sure the SMTP account allows authenticated STARTTLS sending.

## Run Locally

```bash
python app.py
```

The application listens on port `5000` by default.

## Production Deployment

### Gunicorn

Run the WSGI app with:

```bash
gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

### Nginx

Use Nginx as a reverse proxy in front of Gunicorn and terminate HTTPS with Let’s Encrypt.

Recommended proxy headers:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

### HTTPS

Configure Let’s Encrypt certificates and force HTTPS at the Nginx layer. The application is already configured for secure cookies and HSTS.

## Collections

- `users`
- `wallets`
- `expense_categories`
- `income_categories`
- `expenses`
- `income`
- `otp_verifications`

## Notes

- Passwords are stored only as `password_hash` using bcrypt.
- Every financial query is scoped by `user_id`.
- Default expense and income categories are seeded automatically after successful OTP verification.
