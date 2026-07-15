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
        
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN live_chat_requested BOOLEAN DEFAULT 0;")
        print("Added live_chat_requested to tickets")
    except Exception as e:
        print(f"Error adding live_chat_requested: {e}")
        
    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                sender VARCHAR(50) NOT NULL,
                message_type VARCHAR(50) DEFAULT 'TEXT',
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(ticket_id) REFERENCES tickets(ticket_id)
            )
        """)
        print("Created chat_messages table")
    except Exception as e:
        print(f"Error creating chat_messages table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade_db()
