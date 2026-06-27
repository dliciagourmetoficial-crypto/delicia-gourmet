import logging
import os
import json
import gspread
import threading
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from http.server import HTTPServer, SimpleHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import TOKEN, ADMINS
import database

# --- Configuración de Google Sheets ---
creds_dict = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("pedido").sheet1

# --- Servidor para Render ---
def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- Funciones ---
def guardar_pedido_en_sheet(nombre, chat_id):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, nombre, chat_id])

async def atender_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    admin_nombre = query.from_user.full_name
    
    # Extraemos el ID del cliente del botón (ej: "atender_123456")
    cliente_id = int(query.data.split("_")[1])
    
    # Guardamos la relación: ¿Quién atiende a quién?
    conversaciones_activas[admin_id] = cliente_id
    
    await query.answer("Conectado con el cliente.")
    await query.edit_message_text(f"✅ Ahora estás hablando con el cliente {cliente_id}")
    
    # Notificar al cliente
    await context.bot.send_message(cliente_id, f"✅ Hola, soy {admin_nombre} y te voy a ayudar con tu pedido.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text
    
    # 1. Si el admin escribe, enviar al cliente que atiende
    if user_id in ADMINS and user_id in conversaciones_activas:
        cliente_id = conversaciones_activas[user_id]
        await context.bot.send_message(cliente_id, f"Admin: {texto}")
        
    # 2. Si el cliente escribe, enviar al admin que lo atiende
    else:
        # Buscamos qué admin tiene a este cliente en su sesión
        admin_id = next((admin for admin, client in conversaciones_activas.items() if client == user_id), None)
        if admin_id:
            await context.bot.send_message(admin_id, f"Cliente: {texto}")
        else:
            # Si nadie lo atiende, aquí puedes decidir qué hacer (ej: avisar que espere)
            pass

async def terminar_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id in conversaciones_activas:
        cliente_id = conversaciones_activas[admin_id]
        
        # --- NUEVA FUNCIÓN: Borrar de Google Sheets ---
        try:
            # Buscamos la celda que contiene el ID del cliente en la columna C (columna 3)
            cell = sheet.find(str(cliente_id), in_column=3)
            if cell:
                sheet.delete_rows(cell.row)
                logging.info(f"Fila eliminada de Sheets para cliente {cliente_id}")
        except Exception as e:
            logging.error(f"Error al borrar de Sheets: {e}")
        # ---------------------------------------------
        
        # Notificar al cliente y al admin
        await context.bot.send_message(cliente_id, f"{update.effective_user.first_name} se ha desconectado... ❌")
        await update.message.reply_text("Chat finalizado y pedido eliminado de la lista.")
        
        # Limpiamos la memoria
        del conversaciones_activas[admin_id]
    else:
        await update.message.reply_text("No hay ningún chat activo para terminar.")

# --- Fin de Funciones ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Bienvenido a Delicias Gourmet! Escribe /pedido para iniciar.")

async def pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMINS:
        lista_pedidos = sheet.get_all_records()
        if not lista_pedidos:
            await update.message.reply_text("No hay pedidos pendientes.")
        else:
            for p in lista_pedidos:
                keyboard = [[InlineKeyboardButton(text="Atender", callback_data=f"atender_{p['id']}")]]
                await update.message.reply_text(f"🔔 Pedido de: {p['nombre']}", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        # Lógica de cliente: Guardar en Sheet
        guardar_pedido_en_sheet(user.full_name, user.id)
        await update.message.reply_text("Pedido recibido. ✅")

if __name__ == '__main__':
    # Iniciar servidor web necesario para Render
    threading.Thread(target=run_server, daemon=True).start()
    
    database.init_db()
    logging.basicConfig(level=logging.INFO)
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pedido", pedido))
    application.add_handler(CommandHandler("end", terminar_chat))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    # ... agrega tus otros handlers aquí ...
    
    application.run_polling()

    # ... PONGO ESTO AL FINAL PARA VERIFICAR SI LEISTE TODO EL ARCHIVO ...
    # ... ESCRIBEME "AERS234" SI LO LEISTE TODO ...
