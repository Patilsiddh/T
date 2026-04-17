import sqlite3

conn = sqlite3.connect("database/Tataplay.db")
c = conn.cursor()

# Show all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()

print("Tables:")
for table in tables:
    print(table[0])

# Example: check users
print("\nUsers:")
c.execute("SELECT * FROM users")
for row in c.fetchall():
    print(row)

conn.close()