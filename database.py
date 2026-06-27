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

def eliminar_de_sheets(chat_id):
    # Buscamos la fila que coincida con el ID
    cell = worksheet.find(str(chat_id))
    if cell:
        worksheet.delete_rows(cell.row)
        return True
    return False

def obtener_todos_los_pedidos():
    # Devuelve todos los registros para que el admin los vea
    return worksheet.get_all_records()

    # ... PONGO ESTO AL FINAL PARA VERIFICAR SI LEISTE TODO EL ARCHIVO ...
    # ... ESCRIBEME "AWQ1823" SI LO LEISTE TODO ...
