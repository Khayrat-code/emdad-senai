from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

# إعدادات رفع الملفات
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

app = Flask(_name_)
app.secret_key = 'secure_key_here'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB_NAME = 'users.db'

# التأكد من نوع الملف
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# دوال قاعدة البيانات
def init_db():
    alter_factory_requests_table()
    create_orders_table()
    create_offers_table()
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
        conn.commit()

def create_orders_table():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        description TEXT,
                        sector TEXT,
                        quantity INTEGER,
                        delivery_date TEXT,
                        created_at TEXT,
                        user_id INTEGER,
                        attachment TEXT
                    )''')
        conn.commit()

def create_offers_table():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS offers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        offer_text TEXT NOT NULL,
                        order_id INTEGER,
                        user_id INTEGER,
                        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
        conn.commit()

def alter_factory_requests_table():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("ALTER TABLE factory_requests ADD COLUMN lat REAL")
            c.execute("ALTER TABLE factory_requests ADD COLUMN lng REAL")
            conn.commit()
    except:
        pass  # إذا العمود موجود مسبقاً

# دعم تغيير اللغة
@app.context_processor
def inject_lang():
    return dict(get_locale=lambda: session.get('lang', 'ar'))

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# الصفحات الرئيسية
@app.route('/')
def index():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'factory'")
        factories_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'supplier'")
        suppliers_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders")
        orders_count = c.fetchone()[0]
    return render_template('index.html',
                           factories_count=factories_count,
                           suppliers_count=suppliers_count,
                           orders_count=orders_count)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/join-factory', methods=['GET', 'POST'])
def join_factory():
    if request.method == 'POST':
        flash("تم إرسال طلبك بنجاح.")
        return redirect(url_for('index'))
    return render_template('join_factory.html')

# التسجيل والدخول
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        sector = request.form.get('sector', '')

        if password != confirm_password:
            flash("كلمتا المرور غير متطابقتين.")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (name, email, password, role, sector) VALUES (?, ?, ?, ?, ?)",
                          (name, email, hashed_password, role, sector))
                conn.commit()
            flash("تم إنشاء الحساب بنجاح.")
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

@app.route('/logout')
def logout():
    session.clear()
    flash("تم تسجيل الخروج.")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['name'], role=session['role'])

# أوامر المصنع
@app.route('/create-order', methods=['GET', 'POST'])
def create_order():
    if 'user_id' not in session or session['role'] != 'factory':
        flash("يجب تسجيل الدخول كمصنع.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        sector = request.form['sector']
        quantity = request.form['quantity']
        delivery_date = request.form['delivery_date']
        user_id = session['user_id']

        filename = None
        file = request.files.get('attachment')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO orders (title, description, sector, quantity, delivery_date, created_at, user_id, attachment) VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                      (title, description, sector, quantity, delivery_date, user_id, filename))
            conn.commit()
        flash("تم نشر الطلب بنجاح.")
        return redirect(url_for('dashboard'))

    return render_template('create_order.html')

@app.route('/orders')
def view_orders():
    if 'user_id' not in session or session['role'] != 'supplier':
        flash("يجب تسجيل الدخول كمورد.")
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders")
        orders = c.fetchall()
    return render_template('view_orders.html', orders=orders)

@app.route('/submit-offer/<int:order_id>', methods=['GET', 'POST'])
def submit_offer(order_id):
    if 'user_id' not in session or session['role'] != 'supplier':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = c.fetchone()
        if request.method == 'POST':
            offer_text = request.form['offer_text']
            c.execute("INSERT INTO offers (offer_text, order_id, user_id) VALUES (?, ?, ?)",
                      (offer_text, order_id, session['user_id']))
            conn.commit()
            flash("تم إرسال العرض.")
            return redirect(url_for('view_orders'))
    return render_template('submit_offer.html', order=order)

# القطاعات والمصانع
@app.route('/industries')
def industries():
    sectors = ["غذائي", "طبي", "معدني", "كيميائي", "بلاستيكي", "إنشائي", "إلكتروني", "تغليف"]
    return render_template('browse_industries.html', sectors=sectors)

@app.route('/factories/<sector>')
def factories_by_sector(sector):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE role = 'factory' AND sector = ?", (sector,))
        factories = c.fetchall()
    return render_template('factories_by_sector.html', sector=sector, factories=factories)

@app.route('/order/<int:order_id>')
def order_details(order_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = c.fetchone()
    return render_template('request_details.html', order=order)

@app.route('/factory/<int:user_id>')
def factory_profile(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND role = 'factory'", (user_id,))
        factory = c.fetchone()
        c.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
        orders = c.fetchall()
    return render_template('factory_profile.html', factory=factory, orders=orders)

# لوحة تحكم المشرف
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == 'admin123':
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM users")
                users = c.fetchall()
                c.execute("SELECT * FROM factory_requests")
                requests = c.fetchall()
            return render_template('admin.html', users=users, requests=requests)
        else:
            flash("كلمة المرور غير صحيحة.")
            return redirect(url_for('admin'))
    return '''
        <form method="POST">
            <h2>دخول المدير</h2>
            <input type="password" name="password" placeholder="كلمة المرور">
            <input type="submit" value="دخول">
        </form>
    '''

# تشغيل التطبيق
if _name_ == '_main_':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
