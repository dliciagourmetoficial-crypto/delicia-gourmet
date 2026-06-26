import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_chats 
                      (admin_id INTEGER, client_id INTEGER, client_name TEXT)''')
    conn.commit()
    conn.close()

# Funciones para insertar y borrar chats se manejarán en main.py