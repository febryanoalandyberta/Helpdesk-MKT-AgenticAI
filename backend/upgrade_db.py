import sqlite3

def upgrade_db():
    conn = sqlite3.connect('helpdesk_demo.db')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE devices ADD COLUMN disk_total_gb FLOAT;")
        print("Added disk_total_gb")
    except Exception as e:
        print(f"Error adding disk_total_gb: {e}")
        
    try:
        c.execute("ALTER TABLE devices ADD COLUMN disk_free_gb FLOAT;")
        print("Added disk_free_gb")
    except Exception as e:
        print(f"Error adding disk_free_gb: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
