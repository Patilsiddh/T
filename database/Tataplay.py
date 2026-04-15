import sqlite3
from werkzeug.security import generate_password_hash
import os

# ---------------- Paths ---------------- #
DB_FOLDER = "database"
DB_PATH = os.path.join(DB_FOLDER, "Tataplay.db")
os.makedirs(DB_FOLDER, exist_ok=True)

# ---------------- Connect ---------------- #
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ⚠️ IMPORTANT: Enable FK
c.execute("PRAGMA foreign_keys = ON")

# =========================
# 🧨 DROP ALL TABLES (SAFE ORDER)
# =========================
c.execute("DROP TABLE IF EXISTS plan_ott")
c.execute("DROP TABLE IF EXISTS plan_features")
c.execute("DROP TABLE IF EXISTS plan_speeds")
c.execute("DROP TABLE IF EXISTS plan_durations")
c.execute("DROP TABLE IF EXISTS plan_images")
c.execute("DROP TABLE IF EXISTS plans")
c.execute("DROP TABLE IF EXISTS ott_apps")
c.execute("DROP TABLE IF EXISTS categories")
c.execute("DROP TABLE IF EXISTS users")

# =========================
# 👤 USERS TABLE
# =========================
c.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)
''')

# =========================
# 🎁 OFFERS (NEW ADMIN CONTROLLED SYSTEM)
# =========================
c.execute('''
CREATE TABLE offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    subtitle TEXT,
    amount_text TEXT,
    image_url TEXT,
    offer_type TEXT,  -- broadband / dth / general / popup
    is_popup INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    start_date TEXT,
    end_date TEXT
)
''')

# =========================
# ✅ CATEGORIES
# =========================
c.execute('''
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
''')

# =========================
# 📦 PLANS
# =========================
c.execute('''
CREATE TABLE plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    image_url TEXT,
    is_best_seller INTEGER DEFAULT 0,
    category_id INTEGER,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
)
''')

# =========================
# 🖼 PLAN IMAGES
# =========================
c.execute('''
CREATE TABLE plan_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    filename TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
)
''')

# =========================
# ⏱ DURATIONS
# =========================
c.execute('''
CREATE TABLE plan_durations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    duration INTEGER,
    FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
)
''')

# =========================
# ⚡ SPEEDS (NO REQUIRED FIELDS ✅)
# =========================
c.execute('''
CREATE TABLE plan_speeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    duration_id INTEGER,
    speed INTEGER,
    price REAL,
    discounted_price REAL DEFAULT 0,
    FOREIGN KEY(duration_id) REFERENCES plan_durations(id) ON DELETE CASCADE
)
''')


c.execute("""
    CREATE TABLE IF NOT EXISTS global_offer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)


# =========================
# 🎬 OTT APPS
# =========================
c.execute('''
CREATE TABLE ott_apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    logo_url TEXT
)
''')

# =========================
# 🔗 PLAN ↔ OTT
# =========================
c.execute('''
CREATE TABLE plan_ott (
    plan_id INTEGER,
    ott_id INTEGER,
    FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY(ott_id) REFERENCES ott_apps(id) ON DELETE CASCADE
)
''')

# =========================
# 🎁 FEATURES
# =========================
c.execute('''
CREATE TABLE plan_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    feature TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
)
''')

# =========================
# 👑 DEFAULT ADMIN
# =========================
admin_username = "admin"
admin_password = generate_password_hash("admin123")

c.execute(
    "INSERT INTO users (username, password, is_admin) VALUES (?,?,?)",
    (admin_username, admin_password, 1)
)

# =========================
# 💾 SAVE
# =========================
conn.commit()
conn.close()

print("🔥 Database RESET + READY (All fields optional)")