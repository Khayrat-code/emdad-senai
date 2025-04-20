
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secure_key_here'
DB_NAME = 'emdad_sanai.db'

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

if __name__ == '__main__':
    app.run(debug=True)

from werkzeug.security import generate_password_hash, check_password_hash

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

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO orders (title, description, sector, quantity, delivery_date, created_at, user_id)
                         VALUES (?, ?, ?, ?, ?, datetime('now'), ?)''',
                      (title, description, sector, quantity, delivery_date, user_id))
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
        flash("يجب تسجيل الدخول كمورد لتقديم عرض.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        offer_text = request.form['offer_text']
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO offers (offer_text, order_id, user_id, submitted_at) VALUES (?, ?, ?, datetime('now'))",
                      (offer_text, order_id, session['user_id']))
            conn.commit()
        flash("تم إرسال العرض بنجاح.")
        return redirect(url_for('view_orders'))

    return render_template('submit_offer.html', order_id=order_id)


@app.route('/offers/<int:order_id>')
def view_offers(order_id):
    if 'user_id' not in session or session['role'] != 'factory':
        flash("الدخول للمصانع فقط.")
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM offers WHERE order_id = ?", (order_id,))
        offers = c.fetchall()
    return render_template('view_offers.html', offers=offers, order_id=order_id)


@app.route('/edit-order/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    if 'user_id' not in session or session['role'] != 'factory':
        flash("الدخول للمصانع فقط.")
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, session['user_id']))
        order = c.fetchone()

    if not order:
        flash("الطلب غير موجود أو لا تملك صلاحية تعديله.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        sector = request.form['sector']
        quantity = request.form['quantity']
        delivery_date = request.form['delivery_date']
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("""UPDATE orders SET title=?, description=?, sector=?, quantity=?, delivery_date=?
                         WHERE id=? AND user_id=?""",
                      (title, description, sector, quantity, delivery_date, order_id, session['user_id']))
            conn.commit()
        flash("تم تحديث الطلب.")
        return redirect(url_for('dashboard'))

    return render_template('edit_order.html', order=order)


@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    if 'user_id' not in session or session['role'] != 'factory':
        flash("الدخول للمصانع فقط.")
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE id = ? AND user_id = ?", (order_id, session['user_id']))
        conn.commit()
    flash("تم حذف الطلب.")
    return redirect(url_for('dashboard'))


@app.route('/stats')
def stats():
    if 'user_id' not in session or session['role'] != 'factory':
        flash("الدخول للمصانع فقط.")
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (session['user_id'],))
        total_orders = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM offers WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)",
                  (session['user_id'],))
        total_offers = c.fetchone()[0]

        c.execute("SELECT MAX(created_at) FROM orders WHERE user_id = ?", (session['user_id'],))
        last_order_date = c.fetchone()[0]

    return render_template('stats.html', total_orders=total_orders,
                           total_offers=total_offers, last_order_date=last_order_date)


@app.route('/factory/<int:user_id>')
def factory_profile(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND role = 'factory'", (user_id,))
        factory = c.fetchone()
        c.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
        orders = c.fetchall()
    return render_template('factory_profile.html', factory=factory, orders=orders)


@app.route('/rate-supplier/<int:supplier_id>', methods=['GET', 'POST'])
def rate_supplier(supplier_id):
    if 'user_id' not in session or session['role'] != 'factory':
        flash("فقط المصانع يمكنهم تقييم الموردين.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO ratings (supplier_id, rating) VALUES (?, ?)", (supplier_id, rating))
            conn.commit()
        flash("تم إرسال التقييم.")
        return redirect(url_for('dashboard'))

    return render_template('rate_supplier.html', supplier_id=supplier_id)


@app.route('/supplier/<int:supplier_id>')
def supplier_profile(supplier_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ? AND role = 'supplier'", (supplier_id,))
        supplier = c.fetchone()
        c.execute("SELECT AVG(rating) FROM ratings WHERE supplier_id = ?", (supplier_id,))
        avg_rating = c.fetchone()[0]
    return render_template('supplier_profile.html', supplier=supplier, avg_rating=avg_rating)
