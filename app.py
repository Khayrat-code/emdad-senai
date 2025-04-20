from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secure_key_here'
DB_NAME = 'emdad_sanai.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        sector TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        description TEXT,
                        sector TEXT,
                        quantity INTEGER,
                        delivery_date TEXT,
                        created_at TEXT,
                        user_id INTEGER
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS offers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        offer_text TEXT,
                        order_id INTEGER,
                        user_id INTEGER,
                        submitted_at TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS ratings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        supplier_id INTEGER,
                        rating INTEGER
                    )''')
        conn.commit()

def get_sectors():
    return ["غذائي", "طبي", "معدني", "كيميائي", "بلاستيكي", "إنشائي", "إلكتروني", "تغليف"]

@app.route('/')
def index():
    return redirect(url_for('industries'))

@app.route('/industries')
def industries():
    sectors = get_sectors()
    return render_template('browse_industries.html', sectors=sectors)

@app.route('/factories/<sector>')
def factories_by_sector(sector):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE role = 'factory' AND sector = ?", (sector,))
        factories = c.fetchall()
    return render_template('factories_by_sector.html', sector=sector, factories=factories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        sector = request.form.get('sector', '')
        hashed_password = generate_password_hash(password)
        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (name, email, password, role, sector) VALUES (?, ?, ?, ?, ?)",
                          (name, email, hashed_password, role, sector))
                conn.commit()
            flash("تم التسجيل بنجاح. يمكنك تسجيل الدخول الآن.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("البريد الإلكتروني مستخدم بالفعل.")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = c.fetchone()
            if user and check_password_hash(user[3], password):
                session['user_id'] = user[0]
                session['name'] = user[1]
                session['role'] = user[4]
                flash("تم تسجيل الدخول.")
                return redirect(url_for('dashboard'))
            else:
                flash("بيانات الدخول غير صحيحة.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['name'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    flash("تم تسجيل الخروج.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
