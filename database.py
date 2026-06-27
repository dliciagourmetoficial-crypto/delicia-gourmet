import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_chats 
                      (admin_id INTEGER, client_id INTEGER, client_name TEXT)''')
    conn.commit()
    conn.close()
    
def guardar_chat_activo(admin_id, client_id, client_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_chats (admin_id, client_id, client_name) VALUES (?, ?, ?)", 
                   (admin_id, client_id, client_name))
    conn.commit()
    conn.close()
