import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openpyxl

# ---------------- Paths ---------------- #
DB_FOLDER = "database"
DB_PATH = os.path.join(DB_FOLDER, "Tataplay.db")
EXCEL_PATH = os.path.join(DB_FOLDER, "user_logs.xlsx")
UPLOAD_FOLDER = "static/uploads"
os.makedirs(DB_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Flask App ---------------- #
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Use environment variable in production
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Database ---------------- #
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # Categories table
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Plans table
    c.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            is_best_seller INTEGER DEFAULT 0,
            category_id INTEGER,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)

    # Plan images table
    c.execute("""
        CREATE TABLE IF NOT EXISTS plan_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)

    # Plan durations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS plan_durations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)

    # Plan speeds table
    c.execute("""
        CREATE TABLE IF NOT EXISTS plan_speeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duration_id INTEGER NOT NULL,
            speed INTEGER NOT NULL,
            price REAL NOT NULL,
            discounted_price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(duration_id) REFERENCES plan_durations(id) ON DELETE CASCADE
        )
    """)

    # Services table
    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Default admin
    admin_username = "admin"
    admin_password = generate_password_hash("admin123")
    c.execute("SELECT * FROM users WHERE username=?", (admin_username,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?,?,?)",
            (admin_username, admin_password, 1)
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- Routes ---------------- #
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            log_user_action(username, "login")
            return redirect(url_for('admin') if user['is_admin'] else url_for('home'))
        else:
            flash('Invalid credentials!', "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



@app.route("/services")
def services():
    return render_template("services.html")
@app.route("/contact")
def contact():
    return render_template("contact.html")
@app.route('/delete_category/<int:id>')
def delete_category(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM categories WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Category deleted!', "success")
    return redirect(url_for('admin'))
# ---------------- Admin Panel ---------------- #
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        flash("You must be admin to access this page!", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # ---------------- ADD CATEGORY ---------------- #
    if request.method == 'POST' and 'new_category' in request.form:
        name = request.form['new_category'].strip()
        if name:
            try:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                conn.commit()
                flash(f'Category "{name}" added!', "success")
            except sqlite3.IntegrityError:
                flash(f'Category "{name}" already exists!', "error")
        return redirect(url_for('admin'))

    # ---------------- ADD PLAN ---------------- #
    if request.method == 'POST' and 'plan_name' in request.form:
        plan_name = request.form['plan_name'].strip()
        description = request.form.get('description', '')
        category_id = request.form['category_id']
        is_best_seller = 1 if request.form.get('best_seller') else 0

        cursor.execute(
            "INSERT INTO plans (name, description, is_best_seller, category_id) VALUES (?,?,?,?)",
            (plan_name, description, is_best_seller, category_id)
        )
        plan_id = cursor.lastrowid

        # Upload Images
        files = request.files.getlist('plan_images[]')
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                cursor.execute("INSERT INTO plan_images (plan_id, filename) VALUES (?,?)", (plan_id, filename))

        # Durations & Speeds
        durations = request.form.getlist('duration[]')
        speeds = request.form.getlist('speed[]')
        prices = request.form.getlist('price[]')
        discounted_prices = request.form.getlist('discounted_price[]')

        speed_idx = 0
        for dur in durations:
            cursor.execute("INSERT INTO plan_durations (plan_id, duration) VALUES (?,?)", (plan_id, dur))
            dur_id = cursor.lastrowid

            s = speeds[speed_idx]
            p = prices[speed_idx]
            d = discounted_prices[speed_idx] or 0

            cursor.execute(
                "INSERT INTO plan_speeds (duration_id, speed, price, discounted_price) VALUES (?,?,?,?)",
                (dur_id, s, p, d)
            )
            speed_idx += 1

        conn.commit()
        flash(f'Plan "{plan_name}" added successfully!', "success")
        return redirect(url_for('admin'))

    # ---------------- SHOW CATEGORIES & PLANS ---------------- #
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cat_list = []

    for cat in categories:
        cat_id = cat['id']

        cursor.execute("""
            SELECT p.*, 
                   GROUP_CONCAT(pi.filename) AS images
            FROM plans p
            LEFT JOIN plan_images pi ON p.id = pi.plan_id
            WHERE p.category_id=?
            GROUP BY p.id
        """, (cat_id,))
        plans = cursor.fetchall()

        plan_list = []

        for plan in plans:
            plan_id = plan['id']

            # Durations
            cursor.execute("SELECT * FROM plan_durations WHERE plan_id=?", (plan_id,))
            durations = cursor.fetchall()

            dur_list = []   # ✅ INIT HERE

            for dur in durations:
                dur_id = dur['id']

                cursor.execute("SELECT * FROM plan_speeds WHERE duration_id=?", (dur_id,))
                spds = cursor.fetchall()

                speeds_list = []
                for spd in spds:
                    speeds_list.append({
                        "id": spd["id"],
                        "speed": spd["speed"],
                        "price": spd["price"],
                        "discounted_price": spd["discounted_price"]
                    })

                # ✅ FIXED (inside loop)
                dur_list.append({
                    "id": dur["id"],
                    "duration": dur["duration"],
                    "speeds": speeds_list
                })

            # Images
            imgs = []
            if plan['images']:
                imgs = [{'filename': f} for f in plan['images'].split(',')]

            plan_list.append({
                'plan': plan,
                'images': imgs,
                'durations': dur_list
            })

        # ✅ KEEP THIS OUTSIDE plan loop
        cat_list.append({
            'id': cat_id,
            'name': cat['name'],
            'plans': plan_list
        })

    conn.close()
    return render_template('admin.html', categories=cat_list)
@app.route('/plans')
def plans():
    conn = get_db_connection()
    cur = conn.cursor()

    categories = cur.execute("SELECT * FROM categories").fetchall()

    category_data = []

    for cat in categories:
        plans = cur.execute(
            "SELECT * FROM plans WHERE category_id = ?",
            (cat["id"],)
        ).fetchall()

        plans_data = []

        for plan in plans:

            # IMAGES
            images = cur.execute(
                "SELECT * FROM plan_images WHERE plan_id = ?",
                (plan["id"],)
            ).fetchall()

            # DURATIONS (IMPORTANT: table name = plan_durations)
            durations = cur.execute(
                "SELECT * FROM plan_durations WHERE plan_id = ?",
                (plan["id"],)
            ).fetchall()

            duration_data = []

            for dur in durations:

                # SPEEDS (IMPORTANT: table name = plan_speeds)
                speeds = cur.execute(
                    "SELECT * FROM plan_speeds WHERE duration_id = ?",
                    (dur["id"],)
                ).fetchall()

                duration_data.append({
                    "id": dur["id"],
                    "duration": dur["duration"],
                    "speeds": speeds
                })

            plans_data.append({
                "plan": plan,
                "images": images,
                "durations": duration_data
            })

        category_data.append({
            "id": cat["id"],
            "name": cat["name"],
            "plans": plans_data
        })

    conn.close()

    return render_template("plans.html", categories=category_data)
@app.route('/admin/update_plan/<int:plan_id>', methods=['POST'])
def update_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        import json

        data = request.form.get('json_data')
        if data:
            data = json.loads(data)
        else:
            data = {}

        # -------- UPDATE PLAN -------- #
        best = data.get('is_best_seller')

        is_best = 1 if str(best).lower() in ['true', '1', 'yes', 'on'] else 0

        cursor.execute("""
            UPDATE plans SET name=?, description=?, is_best_seller=? WHERE id=?
        """, (data.get('name'), data.get('description'), is_best, plan_id))
      

        # -------- UPDATE EXISTING DURATIONS -------- #
        for dur_id, val in data.get('duration', {}).items():
            cursor.execute(
                "UPDATE plan_durations SET duration=? WHERE id=?",
                (val, dur_id)
            )

        # -------- UPDATE EXISTING SPEEDS -------- #
        for spd_id, val in data.get('speed', {}).items():
            cursor.execute(
                "UPDATE plan_speeds SET speed=? WHERE id=?",
                (val, spd_id)
            )

        for spd_id, val in data.get('price', {}).items():
            cursor.execute(
                "UPDATE plan_speeds SET price=? WHERE id=?",
                (val, spd_id)
            )

        for spd_id, val in data.get('discounted_price', {}).items():
            cursor.execute(
                "UPDATE plan_speeds SET discounted_price=? WHERE id=?",
                (val, spd_id)
            )

        # -------- ADD NEW DURATIONS -------- #
        new_duration_map = {}

        for dur in data.get('new_durations', []):
            cursor.execute(
                "INSERT INTO plan_durations (plan_id, duration) VALUES (?, ?)",
                (plan_id, dur)
            )
            new_duration_map[dur] = cursor.lastrowid

        # -------- ADD NEW SPEEDS -------- #
        for sp in data.get('new_speeds', []):
            dur_val = sp.get('duration')

            # find duration id
            dur_id = new_duration_map.get(dur_val)

            if not dur_id:
                cursor.execute(
                    "SELECT id FROM plan_durations WHERE plan_id=? AND duration=?",
                    (plan_id, dur_val)
                )
                row = cursor.fetchone()
                if row:
                    dur_id = row["id"]

            if dur_id:
                cursor.execute("""
                    INSERT INTO plan_speeds (duration_id, speed, price, discounted_price)
                    VALUES (?, ?, ?, ?)
                """, (
                    dur_id,
                    sp.get('speed'),
                    sp.get('price'),
                    sp.get('discounted_price', 0)
                ))

        # -------- IMAGE UPLOAD -------- #
        files = request.files.getlist('images')

        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                cursor.execute(
                    "INSERT INTO plan_images (plan_id, filename) VALUES (?, ?)",
                    (plan_id, filename)
                )

        # -------- DELETE IMAGES -------- #
        for img_id in data.get('delete_images', []):
            cursor.execute(
                "DELETE FROM plan_images WHERE id=?",
                (img_id,)
            )

        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"success": False})

    finally:
        conn.close()
        
@app.route('/delete-plan/<int:id>')
def delete_plan(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # delete plan
    cursor.execute("DELETE FROM plans WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    flash("Plan deleted successfully", "success")
    return redirect(url_for('admin'))



# ---------------- Run App ---------------- #
if __name__ == '__main__':
    app.run(debug=True)