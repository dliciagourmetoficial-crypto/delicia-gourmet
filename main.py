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
    # ... agrega tus otros handlers aquí ...
    
    application.run_polling()
