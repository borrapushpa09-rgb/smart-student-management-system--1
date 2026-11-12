# Smart Student Management System

A single-page, full-stack student portal built with Flask, SQLite (local) / PostgreSQL (optional), HTML, CSS and JavaScript.

## Features
- Teacher and student registration/login/logout with password hashing and server-side sessions.
- Teacher-only student create, update and delete operations.
- Same-dashboard student list, search, reports and attendance.
- Branch performance is intentionally blank until a branch is selected and **Load Data** is clicked.
- Student accounts can view their own linked profile, reports and attendance; they cannot manage other students.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `python -m venv venv`.
4. Activate it: Windows `venv\\Scripts\\activate`; macOS/Linux `source venv/bin/activate`.
5. Run `pip install -r requirements.txt`.
6. Set a secret key (recommended): Windows PowerShell `$env:SECRET_KEY="a-long-random-secret"`; macOS/Linux `export SECRET_KEY="a-long-random-secret"`.
7. Run `python app.py` and open `http://127.0.0.1:5000`.

The database is created automatically on first run. SQLite file is stored in the app's instance folder.

## Deploy to GitHub + Render
1. Create a **public** GitHub repository and upload the contents of this folder (not the outer ZIP file).
2. On Render, choose **New → Web Service**, connect the GitHub repository, and select the `main` branch.
3. Set Language to **Python**.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add environment variable `SECRET_KEY` with a long random value. Set `COOKIE_SECURE` to `true` (the included `render.yaml` already configures these when using a Blueprint).
7. Deploy. Render will provide a public `https://...onrender.com` URL.

### Important database note
The default SQLite database is suitable for local testing. A Render instance's local filesystem can be ephemeral, so SQLite data may be lost on a redeploy/restart unless you attach a persistent disk and set the database path accordingly. For a real multi-user public deployment, create a managed PostgreSQL database on Render and set `DATABASE_URL` on the web service to its **internal connection URL**. The app automatically supports PostgreSQL. Do not use a temporary demo database for important student records.

## Roles
- Anyone can register as a teacher or student in this learning/demo version. For a real institution, teacher registration should be restricted to an administrator or invitation code; do not expose unrestricted teacher sign-up publicly.
- Student registration creates a linked student record with 0 marks and 0 attendance. Teachers can update those values later.

## Security / production checklist
Use a unique `SECRET_KEY`, PostgreSQL, HTTPS, backups, restricted teacher account creation, and institution-approved privacy practices before using real student information. This starter is an educational project, not a certified student information system.
