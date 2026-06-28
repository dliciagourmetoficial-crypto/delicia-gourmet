import logging
import os
import json
import gspread
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
conversaciones_activas = {}

# --- Servidor para Render ---

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
             
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
             
    def log_message(self, format, *args):
        return

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    print("Servidor web iniciado en el puerto 8080")
    server.serve_forever()

# --- Funciones ---
def guardar_pedido_en_sheet(nombre, chat_id):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([fecha, nombre, chat_id])

async def atender_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id
    admin_nombre = query.from_user.full_name
    
    # Extraemos el ID Y NOMBRE del cliente del botón (ej: "atender_123456")
    cliente_id = int(query.data.split("_")[1])
    cell = sheet.find(str(cliente_id), in_column=3)
    cliente_nombre = sheet.cell(cell.row, 2).value
    
    # Guardamos la relación: ¿Quién atiende a quién?
    conversaciones_activas[admin_id] = cliente_id
    
    await query.answer("Conectado con el cliente.")
    await query.edit_message_text(f"✅ Ahora estás hablando con el cliente {cliente_nombre}")
    
    # Notificar al cliente
    await context.bot.send_message(cliente_id, f"✅ Hola, Hablas con {admin_nombre}, es un gusto atenderte, que vas a ordenar?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    # Identificar quién es el destinatario
    destinatario_id = None
    if user_id in ADMINS and user_id in conversaciones_activas:
        destinatario_id = conversaciones_activas[user_id]
    else:
        admin_id = next((admin for admin, client in conversaciones_activas.items() if client == user_id), None)
        if admin_id:
            destinatario_id = admin_id
            
    if destinatario_id:
        # --- Lógica de reenvío de archivos ---
        if message.text:
            await context.bot.send_message(destinatario_id, 
                f"<b>{update.effective_user.first_name}:</b>\n{message.text}", 
                parse_mode="HTML")
        elif message.photo:
            await context.bot.send_photo(destinatario_id, message.photo[-1].file_id, caption=message.caption)
        elif message.document:
            await context.bot.send_document(destinatario_id, message.document.file_id, caption=message.caption)
        elif message.sticker:
            await context.bot.send_sticker(destinatario_id, message.sticker.file_id)
        elif message.animation: # Para GIFs
            await context.bot.send_animation(destinatario_id, message.animation.file_id, caption=message.caption)
        elif message.audio:
            await context.bot.send_audio(destinatario_id, message.audio.file_id)
        elif message.voice:
            await context.bot.send_voice(destinatario_id, message.voice.file_id)
        elif message.video:
            await context.bot.send_video(destinatario_id, message.video.file_id, caption=message.caption)

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
        await update.message.reply_text("Comando no disponible")

# --- Fin de Funciones ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
         
         keyboard = [
        [InlineKeyboardButton("🛒 Ir a nuestra Web", url="https://delicia-gourmet.gt.tc/index.php")]
         ]
         reply_markup = InlineKeyboardMarkup(keyboard)
         user = update.effective_user
         mensaje = (
                 f"👋 ¡Hola, {user.full_name}! \n"
                 f"✨ Bienvenid@ a **Delicias Gourmet**! 🍱\n\n"
                 f"👉 Para realizar su pedido pulse /pedido y lo atenderemos. 📝\n\n"
                 f"📱 O también puede realizar su pedido desde nuestra Mini App 🔗"
          )
    await update.message.reply_text(
        mensaje, 
        parse_mode="Markdown", 
        reply_markup=reply_markup
    )

async def pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in ADMINS:
        lista_pedidos = sheet.get_all_records()
        if not lista_pedidos:
            await update.message.reply_text("🚫 No hay pedidos pendientes.")
        else:
            for p in lista_pedidos:
                keyboard = [[InlineKeyboardButton(text="Atender", callback_data=f"atender_{p['id']}")]]
                await update.message.reply_text(f"🔔 Pedido de: {p['nombre']}", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        # Lógica de cliente: Guardar en Sheet
        ids_en_sheets = sheet.col_values(3) # Columna C
        
        if str(user.id) in ids_en_sheets:
            # Si el ID ya existe, enviamos el mensaje de aviso
            await update.message.reply_text(
                "⏳ **Ya su petición está en la lista**, en breve lo atenderemos. 🍕",
                parse_mode="Markdown"
            )
        else:
            # Si no existe, lo guardamos normalmente
            guardar_pedido_en_sheet(user.full_name, user.id)
            await update.message.reply_text(
                "✅ **¡Pedido recibido con éxito!** 🎊\n\n"
                "⏳ Está en la lista. En un momento nos pondremos en contacto con usted para confirmar los detalles. 🚀",
                parse_mode="Markdown"
            )

            # Notificar al admin
            nombre_codificado = user.full_name.replace(' ', '%20')
            url_chat = f"https://delicia-gourmet.gt.tc/cliente.php?chat_id={user.id}&nombre={nombre_codificado}"
            
            keyboard = [[InlineKeyboardButton(text="Agregar a la pagina", url=url_chat)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            for admin_id in ADMINS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"🔔 Nuevo pedido manual:\n\n👤 Cliente: {user.full_name}\n🆔 ID: {user.id}",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logging.error(f"No se pudo enviar aviso al admin {admin_id}: {e}")
                     

if __name__ == '__main__':
    # Iniciar servidor web necesario para Render
    threading.Thread(target=run_server, daemon=True).start()
    
    database.init_db()
    logging.basicConfig(level=logging.INFO)
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CallbackQueryHandler(atender_cliente, pattern='^atender_'))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pedido", pedido))
    application.add_handler(CommandHandler("end", terminar_chat))
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    # ... agrega tus otros handlers aquí ...
    
    application.run_polling()

    # ... PONGO ESTO AL FINAL PARA VERIFICAR SI LEISTE TODO EL ARCHIVO ...
    # ... ESCRIBEME "AERS234" SI LO LEISTE TODO ...
