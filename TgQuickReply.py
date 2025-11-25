from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import threading
from playsound import playsound
import platform
import os
import sys

s = platform.system()

# -------------------
# Поток для опроса Telegram
class PollThread(QThread):
    new_message = Signal(object, str, str)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.offset = 0
        self.running = True
        self.sound_path = os.path.join(os.path.dirname(__file__), "notification.wav")

    async def poll(self):
        while self.running:
            try:
                updates = await self.bot.get_updates(offset=self.offset, timeout=1)
                for upd in updates:
                    self.offset = upd.update_id + 1
                    if upd.message:
                        chat_id = upd.message.chat.id
                        username = upd.message.from_user.username or upd.message.from_user.first_name or str(chat_id)
                        text = upd.message.text or "<не текстовое сообщение>"
                        self.new_message.emit(chat_id, username, text)
                        threading.Thread(target=lambda: playsound(self.sound_path), daemon=True).start()
            except Exception as e:
                print("Ошибка при получении: ", e)
            await asyncio.sleep(1)

    def run(self):
        asyncio.run(self.poll())

# -------------------
# Главное окно приложения
class TgQuickReply(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TgQuickReply PySide6")
        self.bot = None
        self.current_chat_id = None
        self.users = {}
        self.chat_history = {}
        self.poll_thread = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Токен бота:"))
        self.token_entry = QLineEdit()
        layout.addWidget(self.token_entry)

        paste_btn = QPushButton("Вставить токен")
        paste_btn.clicked.connect(self.paste_token)
        layout.addWidget(paste_btn)

        connect_btn = QPushButton("Подключиться")
        connect_btn.clicked.connect(self.connect_bot)
        layout.addWidget(connect_btn)

        layout.addWidget(QLabel("Список пользователей:"))
        self.chat_list = QListWidget()
        self.chat_list.currentRowChanged.connect(self.select_chat)
        layout.addWidget(self.chat_list)

        layout.addWidget(QLabel("История сообщений:"))
        self.msg_area = QTextEdit()
        self.msg_area.setReadOnly(True)
        layout.addWidget(self.msg_area)

        h = QHBoxLayout()
        self.reply_entry = QLineEdit()
        h.addWidget(self.reply_entry)

        paste_text_btn = QPushButton("Вставить")
        paste_text_btn.clicked.connect(self.paste_text)
        h.addWidget(paste_text_btn)

        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.send_reply)
        h.addWidget(send_btn)

        layout.addLayout(h)
        self.setLayout(layout)

    def paste_token(self):
        self.token_entry.paste()

    def paste_text(self):
        self.reply_entry.paste()

    def connect_bot(self):
        token = self.token_entry.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Введите токен!")
            return
        try:
            self.bot = Bot(token=token)
            QMessageBox.information(self, "Успех", "Бот подключён!")
            self.poll_thread = PollThread(self.bot)
            self.poll_thread.new_message.connect(self.on_new_message)
            self.poll_thread.start()
        except TelegramError as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def on_new_message(self, chat_id, username, text):
        if chat_id not in self.users:
            self.users[chat_id] = username
            self.chat_list.addItem(username)
        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []
        self.chat_history[chat_id].append(f"{username}: {text}")
        if chat_id == self.current_chat_id:
            self.msg_area.append(f"{username}: {text}")

    def select_chat(self, index):
        if index < 0:
            return
        username = self.chat_list.item(index).text()
        for cid, user in self.users.items():
            if user == username:
                self.current_chat_id = cid
                break
        self.msg_area.clear()
        if self.current_chat_id in self.chat_history:
            for msg in self.chat_history[self.current_chat_id]:
                self.msg_area.append(msg)

    def send_reply(self):
        if not self.current_chat_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя")
            return
        text = self.reply_entry.text().strip()
        if not text:
            return
        def send():
            try:
                asyncio.run(self.bot.send_message(
                    chat_id=self.current_chat_id,
                    text=f"TgQuickReply Desktop@{s}User : {text}"
                ))
            except TelegramError as e:
                print("Ошибка отправки:", e)
        threading.Thread(target=send, daemon=True).start()
        self.chat_history.setdefault(self.current_chat_id, []).append(f"Вы: {text}")
        self.msg_area.append(f"Вы: {text}")
        self.reply_entry.clear()

# -------------------
# Функция запуска на уровне модуля
def app_run():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #0b1a33; color: #e6ecff; }
        QLineEdit, QTextEdit, QListWidget {
            background-color: #10264d;
            border: 1px solid #1f3b66;
            color: #e6ecff;
        }
        QPushButton {
            background-color: #1f3b66;
            color: #e6ecff;
            border: 1px solid #2d518a;
            padding: 6px;
        }
        QPushButton:hover {
            background-color: #2d518a;
        }
    """)
    w = TgQuickReply()
    w.show()
    app.exec()

# -------------------
# запуск при прямом вызове файла
if __name__ == "__main__":
    app_run()
