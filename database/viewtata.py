import sqlite3
import os
import pprint

DB_PATH = os.path.join("database", "Tataplay.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n=== 🔍 ALL POPUP OFFERS ===\n")

cursor.execute("""
    SELECT id, title, offer_type, image_url, is_active 
    FROM offers 
    WHERE offer_type='popup'
""")

rows = cursor.fetchall()

if rows:
    for row in rows:
        pprint.pprint(dict(row))
else:
    print("❌ No popup offers found")

# ✅ Check ACTIVE popup
print("\n=== ✅ ACTIVE POPUP OFFER ===\n")

cursor.execute("""
    SELECT * FROM offers 
    WHERE offer_type='popup' AND is_active=1
    LIMIT 1
""")

active = cursor.fetchone()

if active:
    pprint.pprint(dict(active))
else:
    print("❌ No active popup offer set")

conn.close()