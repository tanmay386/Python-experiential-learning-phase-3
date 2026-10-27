# Student Attendance Tracker — Render

This is a web version of the desktop Tkinter project. Render web services host web apps, so the Tkinter interface was converted to Flask.

## Deploy
1. Download and unzip this package.
2. Upload `app.py`, `requirements.txt`, and `render.yaml` to a GitHub repository.
3. In Render, choose **New + → Web Service** and connect that repository.
4. Use build command `pip install -r requirements.txt`
5. Use start command `gunicorn app:app`
6. Deploy, then open the generated `onrender.com` address.

## Data persistence warning
Render's default filesystem is ephemeral. On the free service, SQLite records may be lost after a restart or redeploy. For persistent SQLite, use a paid service with a persistent disk mounted at `/var/data` and set `DB_PATH=/var/data/attendance.db`. For multi-user production use, use a managed PostgreSQL database.

## Included
Student management, last-10-days attendance, semester summary and date-wise matrix, 70% defaulter status, history, CSV export.
