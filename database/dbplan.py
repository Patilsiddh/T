import os
import psycopg2
from werkzeug.security import generate_password_hash

# =========================
# DATABASE CONNECTION
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in environment variables")

conn = psycopg2.connect(DATABASE_URL)
c = conn.cursor()

print("✅ Connected to Railway Postgres DB")

# =========================
# 🧨 DROP TABLES
# =========================
tables = [
    "plan_features",
    "plan_speeds",
    "plan_durations",
    "plans",
    "categories",
    "offers",
    "users"
]

for t in tables:
    c.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

# =========================
# 👤 USERS
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)
""")

# =========================
# 🎁 OFFERS
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS offers (
    id SERIAL PRIMARY KEY,
    title TEXT,
    subtitle TEXT,
    amount_text TEXT,
    image_url TEXT,
    offer_type TEXT,
    is_popup INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
)
""")

# =========================
# 📂 CATEGORIES
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
)
""")

# =========================
# 📦 PLANS
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    image_url TEXT,
    is_best_seller INTEGER DEFAULT 0,
    category_id INTEGER
)
""")

# =========================
# ⏱ DURATIONS
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS plan_durations (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER,
    duration INTEGER
)
""")

# =========================
# ⚡ SPEEDS
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS plan_speeds (
    id SERIAL PRIMARY KEY,
    duration_id INTEGER,
    speed INTEGER,
    price REAL,
    discounted_price REAL
)
""")

# =========================
# 🎁 FEATURES
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS plan_features (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER,
    feature TEXT
)
""")

# =========================
# 👑 ADMIN USER
# =========================
admin_username = "admin"
admin_password = generate_password_hash("admin123")

c.execute("SELECT * FROM users WHERE username=%s", (admin_username,))
if not c.fetchone():
    c.execute(
        "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
        (admin_username, admin_password, 1)
    )

# =========================
# 📂 INSERT CATEGORIES
# =========================
c.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", ("Broadband",))
c.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", ("DTH (D2H)",))

c.execute("SELECT id FROM categories WHERE name=%s", ("Broadband",))
broadband_id = c.fetchone()[0]

c.execute("SELECT id FROM categories WHERE name=%s", ("DTH (D2H)",))
dth_id = c.fetchone()[0]

# =========================
# 📦 BROADBAND PLANS
# =========================
plans = [
    ("Lite 100 Mbps", 100, broadband_id, 0, "Perfect for small families"),
    ("Prime 200 Mbps", 200, broadband_id, 1, "Best for streaming"),
    ("Mega 500 Mbps", 500, broadband_id, 1, "Ultra fast internet"),
    ("Giga 1 Gbps", 1000, broadband_id, 1, "For professionals"),
]

image_map = {
    100: "https://images.unsplash.com/photo-1556740738-b6a63e27c4df",
    200: "https://images.unsplash.com/photo-1581091870627-3c1c5c1b5c1f",
    500: "https://images.unsplash.com/photo-1518779578993-ec3579fee39f",
    1000: "https://images.unsplash.com/photo-1535223289827-42f1e9919769"
}

pricing = {
    100: {1: 850, 3: 800, 6: 750, 12: 700},
    200: {1: 1050, 3: 1000, 6: 950, 12: 900},
    500: {1: 2700, 3: 2600, 6: 2500, 12: 2400},
    1000: {1: 4200, 3: 4000, 6: 3800, 12: 3600},
}

for name, speed, cat, best, desc in plans:

    c.execute("""
        INSERT INTO plans (name, description, image_url, is_best_seller, category_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (name, desc, image_map[speed], best, cat))

    pid = c.fetchone()[0]

    for d in [1, 3, 6, 12]:
        c.execute("""
            INSERT INTO plan_durations (plan_id, duration)
            VALUES (%s, %s)
            RETURNING id
        """, (pid, d))

        did = c.fetchone()[0]

        price = pricing[speed][d]
        discounted = price - 100

        c.execute("""
            INSERT INTO plan_speeds (duration_id, speed, price, discounted_price)
            VALUES (%s, %s, %s, %s)
        """, (did, speed, price, discounted))

    features = [
        "Unlimited Data",
        "Free Router",
        "No FUP Limit",
        "24/7 Support",
        f"{speed} Mbps Speed"
    ]

    for f in features:
        c.execute("""
            INSERT INTO plan_features (plan_id, feature)
            VALUES (%s, %s)
        """, (pid, f))

# =========================
# 📺 DTH PLANS
# =========================
dth_plans = [
    ("Basic DTH Pack", "100+ Channels", 300),
    ("Family Pack", "200+ Channels", 450),
    ("Premium Pack", "300+ Channels", 650),
]

for name, desc, price in dth_plans:

    c.execute("""
        INSERT INTO plans (name, description, image_url, is_best_seller, category_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (name, desc, "https://images.unsplash.com/photo-1593784991095-a205069470b6", 0, dth_id))

    pid = c.fetchone()[0]

    c.execute("""
        INSERT INTO plan_durations (plan_id, duration)
        VALUES (%s, %s)
        RETURNING id
    """, (pid, 1))

    did = c.fetchone()[0]

    c.execute("""
        INSERT INTO plan_speeds (duration_id, speed, price, discounted_price)
        VALUES (%s, %s, %s, %s)
    """, (did, 0, price, price - 50))

# =========================
# 🎁 OFFER
# =========================
c.execute("""
INSERT INTO offers (title, subtitle, amount_text, image_url, offer_type, is_popup, is_active)
VALUES (%s, %s, %s, %s, %s, %s, %s)
""", (
    "🔥 Limited Offer",
    "Instant discount available",
    "₹300 OFF",
    "https://images.unsplash.com/photo-1607083206968-13611e3d76db",
    "popup",
    1,
    1
))

# =========================
# 💾 COMMIT
# =========================
conn.commit()
conn.close()

print("🔥 DATABASE READY ON RAILWAY POSTGRES")