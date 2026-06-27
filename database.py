import sqlite3
from config import DB_NAME
app.add_handler(CallbackQueryHandler(atender_cliente, pattern='^atender_'))
app.add_handler(CommandHandler("end", terminar_chat))

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_chats 
                      (admin_id INTEGER, client_id INTEGER, client_name TEXT)''')
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
