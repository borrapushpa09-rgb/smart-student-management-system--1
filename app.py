import os
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-before-deployment')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///student_management.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(30), nullable=False)
    year = db.Column(db.String(20), default='1st Year')
    marks = db.Column(db.Float, default=0)
    attendance = db.Column(db.Float, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('student_profile', uselist=False))

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False)
    student = db.relationship('Student', backref='attendance_records')
    __table_args__ = (db.UniqueConstraint('student_id', 'attendance_date', name='unique_student_attendance_day'),)

with app.app_context():
    db.create_all()

def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({'error': 'Please log in first.'}), 401
        return fn(*args, **kwargs)
    return wrapper

def teacher_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user().role != 'teacher':
            return jsonify({'error': 'Only teachers can perform this action.'}), 403
        return fn(*args, **kwargs)
    return wrapper

def student_json(s):
    return {'id': s.id, 'student_id': s.student_id, 'name': s.name, 'email': s.email,
            'branch': s.branch, 'year': s.year, 'marks': s.marks or 0,
            'attendance': s.attendance or 0}

def make_student_id():
    last = Student.query.order_by(Student.id.desc()).first()
    return f'STU{(last.id + 1 if last else 1):04d}'

def payload_value(data, key, default=''):
    value = data.get(key, default)
    return value.strip() if isinstance(value, str) else value

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/me')
def me():
    user = current_user()
    if not user:
        return jsonify({'user': None})
    return jsonify({'user': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}})

@app.post('/api/register')
def register():
    data = request.get_json(silent=True) or {}
    name, email = payload_value(data, 'name'), payload_value(data, 'email').lower()
    password, role = data.get('password', ''), payload_value(data, 'role', 'student').lower()
    branch = payload_value(data, 'branch', 'CSE').upper()
    if not name or not email or len(password) < 8:
        return jsonify({'error': 'Enter your name, email and a password with at least 8 characters.'}), 400
    if role not in ('teacher', 'student'):
        return jsonify({'error': 'Choose teacher or student.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'This email is already registered.'}), 409
    user = User(name=name, email=email, password_hash=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.flush()
    if role == 'student':
        db.session.add(Student(student_id=make_student_id(), name=name, email=email, branch=branch,
                               user_id=user.id, year='1st Year', marks=0, attendance=0))
    db.session.commit()
    session.clear(); session['user_id'] = user.id
    return jsonify({'message': 'Registration successful.', 'user': {'name': user.name, 'email': user.email, 'role': user.role}})

@app.post('/api/login')
def login():
    data = request.get_json(silent=True) or {}
    email = payload_value(data, 'email').lower()
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, data.get('password', '')):
        return jsonify({'error': 'Incorrect email or password.'}), 401
    session.clear(); session['user_id'] = user.id
    return jsonify({'message': 'Login successful.', 'user': {'name': user.name, 'email': user.email, 'role': user.role}})

@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify({'message': 'Logged out.'})

@app.get('/api/dashboard')
@login_required
def dashboard():
    user = current_user()
    if user.role == 'student':
        s = Student.query.filter_by(user_id=user.id).first()
        return jsonify({'total': 1 if s else 0, 'good': 1 if s and s.marks >= 75 else 0,
                        'risk': 1 if s and (s.marks < 40 or s.attendance < 75) else 0,
                        'top_count': 0, 'student': student_json(s) if s else None})
    total = Student.query.count()
    good = Student.query.filter(Student.marks >= 75).count()
    risk = Student.query.filter(or_(Student.marks < 40, Student.attendance < 75)).count()
    top_count = Student.query.filter(Student.marks >= 90).count()
    return jsonify({'total': total, 'good': good, 'risk': risk, 'top_count': top_count})

@app.get('/api/students')
@login_required
def get_students():
    user = current_user()
    if user.role == 'student':
        rows = Student.query.filter_by(user_id=user.id).all()
    else:
        rows = Student.query.order_by(Student.name.asc()).all()
    return jsonify([student_json(s) for s in rows])

@app.post('/api/students')
@teacher_required
def add_student():
    data = request.get_json(silent=True) or {}
    name, email, branch = payload_value(data, 'name'), payload_value(data, 'email').lower(), payload_value(data, 'branch').upper()
    if not name or not email or not branch:
        return jsonify({'error': 'Name, email and branch are required.'}), 400
    try:
        marks = float(data.get('marks', 0)); attendance = float(data.get('attendance', 0))
        if not 0 <= marks <= 100 or not 0 <= attendance <= 100: raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'Marks and attendance must be between 0 and 100.'}), 400
    s = Student(student_id=make_student_id(), name=name, email=email, branch=branch,
                year=payload_value(data, 'year', '1st Year'), marks=marks, attendance=attendance)
    db.session.add(s); db.session.commit()
    return jsonify(student_json(s)), 201

@app.put('/api/students/<int:sid>')
@teacher_required
def update_student(sid):
    s = db.session.get(Student, sid)
    if not s: return jsonify({'error': 'Student not found.'}), 404
    data = request.get_json(silent=True) or {}
    for field in ('name', 'email', 'branch', 'year'):
        if field in data: setattr(s, field, payload_value(data, field).upper() if field == 'branch' else payload_value(data, field))
    try:
        if 'marks' in data: s.marks = float(data['marks'])
        if 'attendance' in data: s.attendance = float(data['attendance'])
        if not 0 <= s.marks <= 100 or not 0 <= s.attendance <= 100: raise ValueError()
    except (TypeError, ValueError): return jsonify({'error': 'Marks and attendance must be between 0 and 100.'}), 400
    db.session.commit(); return jsonify(student_json(s))

@app.delete('/api/students/<int:sid>')
@teacher_required
def delete_student(sid):
    s = db.session.get(Student, sid)
    if not s: return jsonify({'error': 'Student not found.'}), 404
    AttendanceRecord.query.filter_by(student_id=s.id).delete()
    if s.user_id:
        linked_user = db.session.get(User, s.user_id)
        if linked_user: db.session.delete(linked_user)
    db.session.delete(s); db.session.commit()
    return jsonify({'message': 'Student deleted.'})

@app.get('/api/branches/<branch>/performance')
@login_required
def branch_performance(branch):
    branch = branch.upper()
    rows = Student.query.filter_by(branch=branch).order_by(Student.marks.desc(), Student.name.asc()).all()
    if not rows: return jsonify({'branch': branch, 'top_count': 0, 'average': 0, 'toppers': [], 'failed': [], 'students': []})
    avg = db.session.query(func.avg(Student.marks)).filter_by(branch=branch).scalar() or 0
    return jsonify({'branch': branch, 'top_count': sum(1 for s in rows if s.marks >= 90),
                    'average': round(avg, 1), 'toppers': [student_json(s) for s in rows if s.marks >= 75][:5],
                    'failed': [student_json(s) for s in rows if s.marks < 40][:5],
                    'students': [student_json(s) for s in rows]})

@app.get('/api/reports')
@login_required
def reports():
    user = current_user()
    rows = Student.query.filter_by(user_id=user.id).all() if user.role == 'student' else Student.query.all()
    return jsonify([{'student_id': s.student_id, 'name': s.name, 'branch': s.branch,
                     'marks': s.marks, 'grade': 'A+' if s.marks >= 90 else 'A' if s.marks >= 75 else 'B' if s.marks >= 60 else 'C' if s.marks >= 40 else 'Needs Improvement'} for s in rows])

@app.get('/api/attendance')
@login_required
def get_attendance():
    user = current_user()
    query = Student.query.filter_by(user_id=user.id) if user.role == 'student' else Student.query
    rows = query.order_by(Student.name.asc()).all()
    result = []
    for s in rows:
        records = AttendanceRecord.query.filter_by(student_id=s.id).order_by(AttendanceRecord.attendance_date.desc()).limit(10).all()
        result.append({'student': student_json(s), 'records': [{'date': r.attendance_date.isoformat(), 'status': r.status} for r in records]})
    return jsonify(result)

@app.post('/api/attendance')
@teacher_required
def mark_attendance():
    data = request.get_json(silent=True) or {}
    s = db.session.get(Student, data.get('student_id'))
    status = payload_value(data, 'status').capitalize()
    try: day = date.fromisoformat(data.get('date', date.today().isoformat()))
    except ValueError: return jsonify({'error': 'Invalid date.'}), 400
    if not s or status not in ('Present', 'Absent'): return jsonify({'error': 'Choose a valid student and attendance status.'}), 400
    record = AttendanceRecord.query.filter_by(student_id=s.id, attendance_date=day).first()
    if record: record.status = status
    else: db.session.add(AttendanceRecord(student_id=s.id, attendance_date=day, status=status))
    total = AttendanceRecord.query.filter_by(student_id=s.id).count()
    present = AttendanceRecord.query.filter_by(student_id=s.id, status='Present').count()
    s.attendance = round((present / total) * 100, 1) if total else 0
    db.session.commit()
    return jsonify({'message': f'{status} attendance saved.', 'attendance': s.attendance})

@app.get('/health')
def health(): return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
