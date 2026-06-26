import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config import TOKEN, ADMINS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"¡Hola {user.first_name}! Bienvenido. Usa /pedido para realizar tu pedido.")

async def pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in ADMINS:
        # Lógica para administradores: mostrar clientes
        await update.message.reply_text("Lista de clientes activos (Simulación):")
        # Aquí iría la consulta a la BD
    else:
        # Lógica para cliente: Notificar a admins
        for admin_id in ADMINS:
            keyboard = [[InlineKeyboardButton("Abrir Chat", callback_data=f"chat_{user.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"Nuevo pedido manual:\nID: {user.id}\nNombre: {user.full_name}",
                reply_markup=reply_markup
            )
        await update.message.reply_text("Tu pedido ha sido enviado a nuestros administradores.")

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