import telebot
from telebot import types
import time

TOKEN = '8237377833:AAHX98FtE1zyLuq9AOjVczXEIG5oVXutsxE'
# СПИСОК АДМИНОВ (добавь сюда ID всех админов через запятую)
ADMIN_IDS = [8236173251, 8770292226, 8400872265]  

bot = telebot.TeleBot(TOKEN)

# База данных в памяти
all_users = {}          
banned_users = {}       
active_tickets = {}     
admin_chat_target = {}  # {admin_id: user_id}
user_last_ticket_time = {} 

class IsAdmin:
    @staticmethod
    def get_main_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔥 Активные тикеты")
        markup.add("👥 Пользователи", "🚫 Забаненные")
        markup.add("🔓 Разбанить ID", "❓ Help")
        return markup

    # Вспомогательная функция для рассылки всем админам
    @staticmethod
    def notify_all_admins(content, is_photo=False, is_video=False, caption=None, markup=None):
        for admin_id in ADMIN_IDS:
            try:
                if is_photo:
                    bot.send_photo(admin_id, content, caption=caption, parse_mode='Markdown', reply_markup=markup)
                elif is_video:
                    bot.send_video(admin_id, content, caption=caption, parse_mode='Markdown', reply_markup=markup)
                else:
                    bot.send_message(admin_id, content, parse_mode='Markdown', reply_markup=markup)
            except:
                pass

class IsUser:
    @bot.message_handler(commands=['start'])
    def start(message):
        uid = message.chat.id
        all_users[uid] = {
            'nick': message.from_user.first_name,
            'user': f"@{message.from_user.username}" if message.from_user.username else "скрыт"
        }
        
        if uid in ADMIN_IDS:
            bot.send_message(uid, "🦈 Админ-панель SharkHack", reply_markup=IsAdmin.get_main_menu())
        else:
            if uid in banned_users: return
            bot.send_message(uid, "👋 Напишите ваш вопрос (можно фото или видео):")

    @bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'video_note'], func=lambda m: m.chat.id not in ADMIN_IDS)
    def handle_user_msg(message):
        uid = message.chat.id
        if uid in banned_users: return

        allowed_types = ['text', 'photo', 'video']
        if message.content_type not in allowed_types:
            bot.send_message(uid, "❌ Ошибка: Вы можете отправлять только текст, фото или видео.")
            return

        is_new_ticket = (uid not in active_tickets)

        if is_new_ticket:
            last_time = user_last_ticket_time.get(uid, 0)
            if time.time() - last_time < 600:
                left = int(600 - (time.time() - last_time))
                bot.send_message(uid, f"⏳ Новый тикет можно создать через {left // 60} мин.")
                return
            
            user_last_ticket_time[uid] = time.time()
            active_tickets[uid] = all_users.get(uid, {'nick': message.from_user.first_name, 'user': '?'})
            bot.send_message(uid, "✅ Тикет создан. Поддержка скоро ответит.")

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Ответить 💬", callback_data=f"adm_reply_{uid}"),
            types.InlineKeyboardButton("Забанить ⛔", callback_data=f"adm_ban_{uid}")
        )
        
        u_info = all_users.get(uid, {'nick': message.from_user.first_name, 'user': '?'})
        header = (f"📩 **Сообщение от пользователя**\n"
                  f"👤 Имя: {u_info['nick']}\n"
                  f"🔗 Юзер: {u_info['user']}\n"
                  f"🆔 ID: `{uid}`\n"
                  f"────────────────────")

        # Уведомляем ВСЕХ админов о новом сообщении
        if message.content_type == 'text':
            IsAdmin.notify_all_admins(f"{header}\n💬: {message.text}", markup=markup)
        elif message.content_type == 'photo':
            IsAdmin.notify_all_admins(message.photo[-1].file_id, is_photo=True, caption=f"{header}\n🖼: {message.caption or ''}", markup=markup)
        elif message.content_type == 'video':
            IsAdmin.notify_all_admins(message.video.file_id, is_video=True, caption=f"{header}\n🎥: {message.caption or ''}", markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def handle_callbacks(call):
    if call.from_user.id not in ADMIN_IDS: return
    bot.answer_callback_query(call.id)
    
    _, action, target_id = call.data.split('_')
    target_id = int(target_id)
    admin_id = call.message.chat.id

    if action == "reply":
        admin_chat_target[admin_id] = target_id
        bot.send_message(admin_id, f"🤝 Вы взяли тикет `{target_id}`. Теперь ваши сообщения идут ему.")
    
    elif action == "ban":
        banned_users[target_id] = all_users.get(target_id, {'nick': '?', 'user': '?'})
        active_tickets.pop(target_id, None)
        # Убираем цель у всех админов, если они общались с ним
        for a_id in ADMIN_IDS:
            if admin_chat_target.get(a_id) == target_id:
                admin_chat_target.pop(a_id, None)
        
        bot.send_message(admin_id, f"⛔ Пользователь `{target_id}` забанен.")
        bot.send_message(target_id, "🚫 Вы были заблокированы поддержкой.")
    
    elif action == "close":
        active_tickets.pop(target_id, None)
        for a_id in ADMIN_IDS:
            if admin_chat_target.get(a_id) == target_id:
                admin_chat_target.pop(a_id, None)
        bot.send_message(target_id, "🔔 Ваш тикет закрыт.")
        bot.send_message(admin_id, f"✅ Тикет `{target_id}` закрыт.")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'video_note'], func=lambda m: m.chat.id in ADMIN_IDS)
def admin_chat_logic(message):
    admin_id = message.chat.id
    
    if message.text == "🔥 Активные тикеты":
        if not active_tickets:
            bot.send_message(admin_id, "Нет активных тикетов."); return
        for uid, data in active_tickets.items():
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Ответить 💬", callback_data=f"adm_reply_{uid}"),
                       types.InlineKeyboardButton("Закрыть ❌", callback_data=f"adm_close_{uid}"))
            bot.send_message(admin_id, f"👤 {data['nick']} ({data['user']})\nID: `{uid}`", reply_markup=markup)
        return

    if message.text == "👥 Пользователи":
        res = "📁База:\n"
        for uid, d in all_users.items(): res += f"• {d['nick']} | ID: `{uid}`\n"
        bot.send_message(admin_id, res or "Пусто"); return

    if message.text == "🚫 Забаненные":
        res = "🚫Бан-лист:\n"
        for uid, d in banned_users.items(): res += f"• {d['nick']} | ID: `{uid}`\n"
        bot.send_message(admin_id, res or "Пусто"); return

    if message.text == "🔓 Разбанить ID":
        msg = bot.send_message(admin_id, "Введите ID:"); bot.register_next_step_handler(msg, process_unban); return

    if message.text == "❓ Help":
        bot.send_message(admin_id, "Панель управления для нескольких админов активна."); return

    # ОТПРАВКА ОТ АДМИНА ЮЗЕРУ
    if admin_id in admin_chat_target:
        uid = admin_chat_target[admin_id]
        try:
            bot.copy_message(uid, admin_id, message.message_id, caption=message.caption if message.caption else None)
        except:
            bot.send_message(admin_id, "❌ Ошибка: юзер недоступен.")
    else:
        bot.send_message(admin_id, "⚠️ Выберите тикет для ответа.")

def process_unban(message):
    try:
        uid = int(message.text)
        banned_users.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Юзер `{uid}` разбанен.")
    except: bot.send_message(message.chat.id, "❌ Ошибка ID.")

if __name__ == "__main__":
    bot.polling(none_stop=True)