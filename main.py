import logging
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Aquí carga la variable secreta que pusiste en Render
creds_dict = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("pedido").sheet1

def guardar_pedido(nombre, chat_id, pedido):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, nombre, chat_id, pedido])
    
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import TOKEN, ADMINS
import database
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

# Función para el servidor falso que mantiene a Render feliz
def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHTTPRequestHandler)
    server.serve_forever()

database.init_db()
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"¡Hola {user.first_name}! 👋 Bienvenido a Delicias Gourmet.\n Puedes realizar tu pedido desde la pagina\n Si quieres hacerlo manual escribe /pedido para comunicarte con nosotros")

async def pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pedido_texto = update.message.text
    guardar_pedido(user.full_name, user.id, pedido_texto)
    if user.id in ADMINS:
        # Lógica para administradores: mostrar clientes
        await update.message.reply_text("Lista de clientes activos (Simulación):")
        # Aquí iría la consulta a la BD
    else:
         for admin_id in ADMINS:
         url_chat = f"https://delicia-gourmet.gt.tc/cliente.php?chat_id={user.id}&nombre={user.full_name.replace(' ', '%20')}"
         keyboard = [[InlineKeyboardButton(text="Abrir Chat", url=url_chat)]]
         reply_markup = InlineKeyboardMarkup(keyboard)
         await context.bot.send_message(
         chat_id=admin_id,
         text=f"🔔 Nuevo pedido manual:\nID: {user.id}\nNombre: {user.full_name}",
         reply_markup=reply_markup
        )
        await update.message.reply_text("¡Pedido recibido con éxito! ✅\nTu solicitud ya ha sido enviada a nuestros administradores. 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si el usuario no es admin, reenviar a admins
    if update.effective_user.id not in ADMINS:
        for admin_id in ADMINS:
            await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pedido", pedido))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
