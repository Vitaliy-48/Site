from flask import Flask, render_template, request, redirect, url_for, session, make_response
from admin_app import admin_app
from datetime import datetime
from dotenv import load_dotenv
from flask_babel import Babel, _
from __init__ import init_db
import sqlite3, json, requests, os


# Ініціалізація
load_dotenv()
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.register_blueprint(admin_app)

with app.app_context():
    host = "http://127.0.0.1:5000"
    print(f"* Running on {host}/admin")

# Babel конфіг
app.config["BABEL_DEFAULT_LOCALE"] = os.getenv("DEFAULT_LOCALE", "uk")
app.config["BABEL_SUPPORTED_LOCALES"] = ["uk", "en", "de"]


def get_locale():
    # пріоритет: ?lang= → cookie → DEFAULT_LOCALE
    lang = request.args.get("lang")
    if lang in app.config["BABEL_SUPPORTED_LOCALES"]:
        return lang
    cookie_lang = request.cookies.get("lang")
    if cookie_lang in app.config["BABEL_SUPPORTED_LOCALES"]:
        return cookie_lang
    return app.config["BABEL_DEFAULT_LOCALE"]

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in app.config["BABEL_SUPPORTED_LOCALES"]:
        resp = make_response(redirect(url_for("index")))
        resp.set_cookie("lang", lang)  # зберігаємо вибір
        return resp
    return redirect(url_for("index"))


babel = Babel(app, locale_selector=get_locale)

# Секрети Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Контекст: кількість в кошику + поточна мова
@app.context_processor
def inject_globals():
    cart = session.get("cart", [])
    return dict(cart_count=len(cart), current_lang=get_locale())

# ---------- Маршрути каталогу і продукту ----------

@app.route("/")
def index():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candles")
    candles = cursor.fetchall()
    conn.close()
    return render_template("site/index.html", candles=candles)

@app.route("/product/<int:candle_id>")
def product(candle_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candles WHERE id=?", (candle_id,))
    candle = cursor.fetchone()
    conn.close()
    return render_template("site/product.html", candle=candle)

@app.route("/add_to_cart/<int:candle_id>", methods=["POST"])
def add_to_cart(candle_id):
    selected_color = request.form.get("color", _("без кольору"))
    quantity = int(request.form.get("quantity", 1))
    cart = session.get("cart", [])
    cart.append({"id": candle_id, "color": selected_color, "quantity": quantity})
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    candles = []
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    total = 0
    for item in cart:
        cursor.execute("SELECT * FROM candles WHERE id=?", (item["id"],))
        candle_data = cursor.fetchone()
        subtotal = candle_data[2] * item["quantity"]
        total += subtotal
        candles.append({"data": candle_data, "color": item["color"], "quantity": item["quantity"], "subtotal": subtotal})
    conn.close()
    total = sum(item["data"][2] * item["quantity"] for item in candles)
    return render_template("site/cart.html", candles=candles, total=total)


# ---------- Оформлення замовлення ----------

@app.route("/checkout", methods=["POST"])
def checkout():
    customer_name = request.form["name"]
    cart = session.get("cart", [])
    candles = []
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    for item in cart:
        cursor.execute("SELECT * FROM candles WHERE id=?", (item["id"],))
        candle_data = cursor.fetchone()
        candles.append({"data": candle_data, "color": item["color"], "quantity": item["quantity"]})
    conn.close()

    order_number = datetime.now().strftime("%d-%m-%Y %H:%M")
    items_json = json.dumps(cart, ensure_ascii=False)
    total_price = sum(c['data'][2] * c['quantity']for c in candles)
    created_at = datetime.now().isoformat(timespec="minutes")

    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (customer_name, items, total_price, order_number, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_name, items_json, total_price, order_number, created_at))
    conn.commit()

    cursor.execute("""
            DELETE FROM orders
            WHERE id NOT IN (SELECT id FROM orders ORDER BY id DESC LIMIT 10)
    """)
    conn.commit()

    conn.close()

    send_order_to_telegram(order_number, customer_name, candles)
    session["cart"] = []
    return render_template("site/order_success.html", name=customer_name, total=total_price, order_number=order_number)

def send_order_to_telegram(order_number, customer_name, candles):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    message = _("🧾 Замовлення №%(order)s\n", order=order_number)
    message += _("👤 Ім'я: %(name)s\n\n", name=customer_name)
    message += _("🕯️ Товари:\n")
    for item in candles:
        name = item['data'][1]
        price = item['data'][2]
        color = item['color']
        message += _("- %(name)s (%(color)s) — %(price).0f грн\n", name=name, color=color, qty=item['quantity'], price=price * item['quantity'])
    total = sum(item['data'][2] * item['quantity'] for item in candles)
    message += _("\n💰 Разом: %(total).0f грн", total=total)

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    for item in candles:
        photo_url = item['data'][4]
        if photo_url:
            caption = _("%(name)s (%(color)s)", name=item['data'][1], color=item['color'])
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                          data={"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": caption})



if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
