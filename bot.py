import json
import threading
import signal
import sys
import os
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Конфигурационный файл
CONFIG_FILE = "bot_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Ошибка чтения конфига. Создаю новый.")
    return {
        "token": "ВАШ_ТОКЕН_БОТА",
        "admin_id": "ВАШ_TELEGRAM_ID",
        "commands": {},
        "channels": {},
        "subscribers": []
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

config = load_config()

# Инициализация бота
bot = None
updater = None
dispatcher = None

def start(update: Update, context: CallbackContext):
    """Обработка команды /start"""
    user_id = update.effective_user.id
    update.message.reply_text(
        f"👋 Привет! Твой ID: `{user_id}`\n"
        "Используй /help для списка команд",
        parse_mode='Markdown'
    )

def help_command(update: Update, context: CallbackContext):
    """Обработка команды /help"""
    commands_list = "\n".join([f"/{cmd}" for cmd in config["commands"]])
    update.message.reply_text(
        f"📚 Доступные команды:\n{commands_list or 'Пока нет команд'}\n"
        "ℹ️ Используй /check для проверки подписок"
    )

def check_subscription(update: Update, context: CallbackContext):
    """Проверка подписки на каналы"""
    user_id = update.effective_user.id
    not_subscribed = []
    
    for channel_id, data in config["channels"].items():
        try:
            member = bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(f"[{data['name']}](https://t.me/{data.get('username', '')})")
        except Exception as e:
            print(f"Ошибка проверки подписки: {str(e)}")
            not_subscribed.append(data['name'])
    
    if not_subscribed:
        update.message.reply_text(
            f"❌ Для использования бота подпишитесь на каналы:\n" + '\n'.join(not_subscribed),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        update.message.reply_text("✅ Вы подписаны на все необходимые каналы!")

def broadcast_message(message: str, media=None):
    """Рассылка сообщения всем подписчикам"""
    success, fail = 0, 0
    for user_id in config["subscribers"]:
        try:
            if media and os.path.exists(media):
                bot.send_photo(user_id, photo=open(media, 'rb'), caption=message)
            else:
                bot.send_message(user_id, message)
            success += 1
        except Exception as e:
            print(f"❌ Ошибка отправки {user_id}: {str(e)}")
            fail += 1
    return success, fail

def console_interface():
    """Интерфейс управления через консоль"""
    print("\n" + "="*50)
    print("🤖 ТЕЛЕГРАМ БОТ КОНТРОЛЬ ПАНЕЛЬ")
    print("="*50)
    print("1. Добавить команду")
    print("2. Добавить канал для проверки")
    print("3. Сделать рассылку")
    print("4. Показать конфигурацию")
    print("5. Запустить/перезапустить бота")
    print("6. Выход")
    
    while True:
        choice = input("\n>>> Выберите действие: ")
        
        if choice == "1":
            cmd = input("⌨️ Имя команды (без /): ").strip().lower()
            if not cmd:
                print("❌ Имя команды не может быть пустым!")
                continue
                
            print("📝 Типы действий: text, photo, check")
            action = input("🔧 Тип действия: ").strip().lower()
            if action not in ["text", "photo", "check"]:
                print("❌ Неподдерживаемый тип действия!")
                continue
                
            content = ""
            if action != "check":
                content = input("📦 Содержимое (текст/URL фото): ").strip()
                if not content:
                    print("❌ Содержимое не может быть пустым!")
                    continue
            
            config["commands"][cmd] = {"action": action, "content": content}
            
            if updater and updater.running:
                dispatcher.add_handler(CommandHandler(cmd, custom_command))
                
            save_config(config)
            print(f"✅ Команда /{cmd} успешно добавлена!")
            
        elif choice == "2":
            channel_name = input("📢 Название канала: ").strip()
            if not channel_name:
                print("❌ Название не может быть пустым!")
                continue
                
            channel_id = input("🔢 ID канала (начинается с -100): ").strip()
            if not channel_id.startswith('-100'):
                print("❌ Неверный формат ID канала!")
                continue
                
            config["channels"][channel_id] = {
                "name": channel_name,
                "id": channel_id
            }
            save_config(config)
            print(f"✅ Канал '{channel_name}' добавлен для проверки!")
            
        elif choice == "3":
            if not config["subscribers"]:
                print("❌ Нет подписчиков для рассылки!")
                continue
                
            msg = input("💬 Сообщение для рассылки: ")
            media = input("🖼 Путь к изображению (Enter если без медиа): ").strip()
            
            print(f"⏳ Рассылка для {len(config['subscribers']} пользователей...")
            success, fail = broadcast_message(msg, media if media else None)
            print(f"📊 Результат: {success} успешно, {fail} ошибок")
            
        elif choice == "4":
            print("\n⚙️ Текущая конфигурация:")
            print(f"🔑 Токен: {'***установлен***' if config['token'] != 'ВАШ_ТОКЕН_БОТА' else '❌ НЕ НАСТРОЕН'}")
            print(f"🆔 Admin ID: {config.get('admin_id', '❌ НЕ НАСТРОЕН')}")
            print(f"📜 Команды ({len(config['commands'])}):")
            for cmd, data in config["commands"].items():
                print(f"  /{cmd} -> [{data['action']}] {data['content'][:30]}{'...' if len(data['content']) > 30 else ''}")
                
            print(f"📣 Каналы ({len(config['channels'])}):")
            for channel in config["channels"].values():
                print(f"  {channel['name']} (ID: {channel['id']})")
                
            print(f"👥 Подписчики: {len(config['subscribers'])}")
            
        elif choice == "5":
            if start_bot():
                print("🟢 Бот запущен! Для остановки используйте Ctrl+C")
            else:
                print("❌ Не удалось запустить бота. Проверьте конфигурацию.")
            
        elif choice == "6":
            print("👋 Завершение работы...")
            if updater and updater.running:
                updater.stop()
            os._exit(0)

def custom_command(update: Update, context: CallbackContext):
    """Обработка пользовательских команд"""
    cmd = update.message.text[1:].split()[0].lower()
    if cmd in config["commands"]:
        action = config["commands"][cmd]["action"]
        content = config["commands"][cmd]["content"]
        
        try:
            if action == "text":
                update.message.reply_text(content)
            elif action == "photo":
                update.message.reply_photo(content)
            elif action == "check":
                check_subscription(update, context)
        except Exception as e:
            print(f"Ошибка выполнения команды /{cmd}: {str(e)}")
            update.message.reply_text("⚠️ Произошла ошибка при выполнении команды")

def start_bot():
    """Запуск/перезапуск бота"""
    global bot, updater, dispatcher
    
    if config["token"] == "ВАШ_ТОКЕН_БОТА":
        print("❌ Токен бота не настроен! Задайте его в bot_config.json")
        return False
        
    try:
        if updater and updater.running:
            updater.stop()
            
        bot = Bot(token=config["token"])
        updater = Updater(token=config["token"], use_context=True)
        dispatcher = updater.dispatcher
        
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("check", check_subscription))
        
        for cmd in config["commands"]:
            dispatcher.add_handler(CommandHandler(cmd, custom_command))
        
        def track_subscribers(update: Update, context: CallbackContext):
            user_id = update.effective_user.id
            if user_id not in config["subscribers"]:
                config["subscribers"].append(user_id)
                save_config(config)
                
        dispatcher.add_handler(MessageHandler(Filters.all, track_subscribers))
        
        threading.Thread(
            target=updater.start_polling, 
            name="BotPollingThread",
            daemon=True
        ).start()
        
        return True
    except Exception as e:
        print(f"❌ Критическая ошибка запуска бота: {str(e)}")
        return False

def graceful_shutdown(signum, frame):
    """Корректное завершение работы"""
    print("\n🛑 Получен сигнал завершения...")
    if updater and updater.running:
        updater.stop()
        print("Бот остановлен")
    sys.exit(0)

if __name__ == "__main__":
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    print("="*50)
    print("🤖 Telegram Bot Builder")
    print("🚀 Динамически настраиваемый Telegram-бот")
    print("="*50)
    print("ℹ️ Для управления используйте консольное меню")
    
    console_thread = threading.Thread(
        target=console_interface, 
        daemon=True
    )
    console_thread.start()
    
    if config["token"] != "ВАШ_ТОКЕН_БОТА" and config.get("admin_id"):
        print("\n🔎 Обнаружена конфигурация - пробуем запустить бота...")
        if start_bot():
            print("🟢 Бот запущен в фоновом режиме")
        else:
            print("❌ Не удалось запустить бота. Проверьте токен в bot_config.json")
    else:
        print("\n⚠️ ВНИМАНИЕ: Бот не настроен!")
        print("1. Создайте бота через @BotFather")
        print("2. Получите свой ID через @userinfobot")
        print("3. Заполните bot_config.json\n")
    
    while True:
        console_thread.join(timeout=1)
        if not console_thread.is_alive():
            break
