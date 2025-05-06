from flask import Flask, request
import requests
import json
import os
import time

app = Flask(__name__)

# تنظیمات
BASE_URL = "https://tapi.bale.ai/bot"
TOKEN = "2043746351:J1aQzkuOsauG8GbRSM6Ng471SxBpOcQXGG6DGAA6"  # توکن ربات بله
CHAT_ID = "1819736588"       # آیدی چت مقصد
REQUEST_FILE = "/app/files/request.txt"  # مسیر فایل در Render
RESPONSE_FILE = "/app/files/account_info.json"  # مسیر فایل در Render

# دیکشنری برای مپینگ کلمات به ایموجی‌ها
emoji_map = {
    "red_circle": "🔴",
    "green_circle": "🟢",
    "black_circle": "⚫️",
    "warning": "⚠️",
    "exclamation": "❗️",
    "cross_mark": "❌",
    "check_mark": "✅",
    "black_large_square": "⬛️",
    "bell": "🔔",
    "speech_balloon": "💬",
    "chart_increasing": "📈",
    "bar_chart": "📊"
}

# تابع برای جایگزینی متن با ایموجی
def convert_to_emoji(message):
    for word, emoji in emoji_map.items():
        message = message.replace(word, emoji)
    return message

# تابع برای ارسال پیام به بله
def send_bale_message(chat_id, message):
    url = f"{BASE_URL}{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return "Message sent successfully"
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

# تابع برای ایجاد فایل درخواست
def create_request_file():
    try:
        os.makedirs(os.path.dirname(REQUEST_FILE), exist_ok=True)
        with open(REQUEST_FILE, "w") as f:
            f.write("balance")
        return True
    except Exception as e:
        print(f"Error creating request file: {str(e)}")
        return False

# تابع برای خواندن فایل پاسخ
def read_response_file():
    try:
        if os.path.exists(RESPONSE_FILE):
            with open(RESPONSE_FILE, "r") as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error reading response file: {str(e)}")
        return None

@app.route('/send', methods=['POST'])
def send_message():
    emoji_text = request.form.get('emoji_text', '')
    order_id = request.form.get('order_id', '')
    trade_type = request.form.get('trade_type', '')
    symbol = request.form.get('symbol', '')
    price = request.form.get('price', '0.0')
    profit = request.form.get('profit', '0.0')
    close_percent = request.form.get('close_percent', '0.0')
    date = request.form.get('date', '')
    time = request.form.get('time', '')
    order_type = request.form.get('order_type', 'Market')
    stop_loss = request.form.get('stop_loss', '0.0')
    take_profit = request.form.get('take_profit', '0.0')
    
    if not emoji_text:
        return "Error: No emoji text provided", 400
    
    emoji = convert_to_emoji(emoji_text)
    
    if float(close_percent) == 0.0:
        sl_str = f"{stop_loss}" if float(stop_loss) != 0.0 else "Not Set"
        tp_str = f"{take_profit}" if float(take_profit) != 0.0 else "Not Set"
        message = f"{emoji} {trade_type} Position Opened #{order_id}\n" \
                  f"💱 Symbol: {symbol}\n" \
                  f" Type: {order_type}\n" \
                  f" Price: {price}\n" \
                  f" Stop Loss: {sl_str}\n" \
                  f" Take Profit: {tp_str}\n" \
                  f" Date: {date}\n" \
                  f" Time: {time}"
    else:
        profit_str = f"+{profit}" if float(profit) >= 0 else f"{profit}"
        message = f"{emoji} {trade_type} Position ({close_percent}%) Closed #{order_id}\n" \
                  f"💱 Symbol: {symbol}\n" \
                  f" Type: {trade_type} {order_type}\n" \
                  f" Price: {price}\n" \
                  f" Profit/Loss: {profit_str}\n" \
                  f" Date: {date}\n" \
                  f" Time: {time}"
    
    result = send_bale_message(CHAT_ID, message)
    return result, 200

@app.route('/update', methods=['POST'])
def handle_update():
    update = request.get_json()
    if not update or 'message' not in update:
        return "No message provided", 400
    
    message = update['message']
    chat_id = message['chat']['id']
    text = message['text'].strip()

    if text == '/balance':
        if create_request_file():
            start_time = time.time()
            while time.time() - start_time < 5:
                account_info = read_response_file()
                if account_info:
                    message = f"📊 Account Information\n" \
                              f"💰 Balance: {account_info['balance']:.2f}\n" \
                              f"📈 Equity: {account_info['equity']:.2f}\n" \
                              f"📉 Margin: {account_info['margin']:.2f}\n" \
                              f"🔄 Open Positions: {account_info['open_positions']}\n" \
                              f"📋 Pending Orders: {account_info['pending_orders']}\n" \
                              f"📅 Today Profit: {account_info['today_profit']:.2f}\n" \
                              f"🗓 Week Profit: {account_info['week_profit']:.2f}\n" \
                              f"🗓 Month Profit: {account_info['month_profit']:.2f}"
                    send_bale_message(chat_id, message)
                    if os.path.exists(RESPONSE_FILE):
                        os.remove(RESPONSE_FILE)
                    return "Balance info sent", 200
                time.sleep(0.1)
            send_bale_message(chat_id, "❌ Error: No response from MetaTrader")
            return "Error: Timeout waiting for response", 500
        else:
            send_bale_message(chat_id, "❌ Error: Could not create request")
            return "Error: Could not create request", 500
    
    return "Message processed", 200

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com/update")
    url = f"{BASE_URL}{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    return response.json(), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)