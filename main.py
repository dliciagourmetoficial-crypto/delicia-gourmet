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
conversaciones_activas = {}

def guardar_pedido(nombre, chat_id, pedido):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, nombre, chat_id, pedido])

async def atender_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    admin_nombre = query.from_user.full_name
    cliente_id = query.data.split("_")[1]
    
    conversaciones_activas[admin_id] = cliente_id
    
    await query.answer()
    # Notificar al admin
    await query.edit_message_text(f"✅ Ahora estás hablando con el cliente {cliente_id}")
    # Notificar al cliente
    await context.bot.send_message(cliente_id, f"✅ Ahora estás hablando con {admin_nombre}")
         
async def terminar_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id in conversaciones_activas:
        cliente_id = conversaciones_activas[admin_id]
        
        # Borrar de Sheets (debes tener una función que busque y elimine por ID)
        eliminar_de_sheets(cliente_id) 
        
        await update.message.reply_text("Chat finalizado.")
        await context.bot.send_message(cliente_id, "El administrador se ha desconectado... ❌")
        
        del conversaciones_activas[admin_id]
    
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import TOKEN, ADMINS
from database import guardar_pedido, obtener_pedidos, eliminar_de_sheets
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
    
    if user.id in ADMINS:
        # Aquí sí llamamos a tu función de database.py
        lista_pedidos = obtener_todos_los_pedidos()
             
        if not lista_pedidos:
            await update.message.reply_text("No hay pedidos pendientes.")
        else:
            for pedido in lista_pedidos:
                # Aquí generas el botón usando los datos que vienen de la hoja
                # Asumiendo que las columnas son 'nombre' y 'id'
                nombre = pedido['nombre']
                id_cliente = pedido['id']
                # ... lógica del botón ...
    else:
        # Tu lógica de cliente normal
        # Lógica para cliente: Registrar pedido y notificar
        pedido_texto = update.message.text
        guardar_pedido(user.full_name, user.id, pedido_texto)
        
        for admin_id in ADMINS:
            url_chat = f"https://delicia-gourmet.gt.tc/cliente.php?chat_id={user.id}&nombre={user.full_name.replace(' ', '%20')}"
            keyboard = [[InlineKeyboardButton(text="Abrir Chat", url=url_chat)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 Nuevo pedido:\nID: {user.id}\nNombre: {user.full_name}",
                reply_markup=reply_markup
            )
        await update.message.reply_text("¡Pedido recibido con éxito! ✅/n Nos comunicaremos con tigo pronto. 🚀")
             
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si el usuario no es admin, reenviar a admins
    if update.effective_user.id not in ADMINS:
        for admin_id in ADMINS:
            await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CallbackQueryHandler(atender_cliente, pattern='atender_'))   
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pedido", pedido))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
