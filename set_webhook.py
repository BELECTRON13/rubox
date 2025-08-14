from rubox import Client
from rubox.filters import text, commands, inline_button_id
from rubox.keyboard import Button, Keypad, KeypadRow
import asyncio

TOKEN = 'BOT-TOKEN'
app = Client(TOKEN, set_webhook=True)

def create_inline_keypad():
    button1 = Button(button_text='دکمه ۱', id='100')
    button2 = Button(button_text='دکمه ۲', id='200')
    keypad_row = KeypadRow([button1, button2])
    my_keypad = Keypad(rows=[keypad_row])
    return my_keypad

@app.on_message(commands('start'))
async def start_handler(message):
    await message.reply('سلام! به ربات خوش آمدید.', inline_keypad=create_inline_keypad())

@app.on_inline_message(inline_button_id('100'))
async def inline_button1_handler(inline_msg):
    await app.send_message(inline_msg['chat_id'], 'شما روی دکمه ۱ کلیک کردید.')

@app.on_inline_message(inline_button_id('200'))
async def inline_button2_handler(inline_msg):
    await app.send_message(inline_msg['chat_id'], 'شما روی دکمه ۲ کلیک کردید.')

asyncio.run(
    app.run(
    webhook_url='https://yourdomain.com',
    path='/webhook',
    host='0.0.0.0',
    port=3000)
    )
