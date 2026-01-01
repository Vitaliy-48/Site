from flask import Flask, render_template, request, redirect, url_for
from flask import Blueprint
import sqlite3


admin_app = Blueprint("admin", __name__, url_prefix="/admin")
# ---------- Адмінка свічок ----------

@admin_app.route("/")
def admin_index():
    return render_template("admin/admin_index.html")

@admin_app.route("/candles")
def admin_candles():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candles ORDER BY id DESC")
    candles = cursor.fetchall()
    conn.close()
    return render_template("admin/admin_candles.html", candles=candles)

@admin_app.route("/candles/add", methods=["GET", "POST"])
def add_candle():
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        image_url = request.form["image_url"]
        shape = request.form["shape"]
        colors = request.form["colors"]
        conn = sqlite3.connect("app.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO candles (name, price, description, image_url, shape, colors)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, price, description, image_url, shape, colors))
        conn.commit()
        conn.close()
        return redirect(url_for("admin.admin_candles"))
    return render_template("admin/add_candle.html")

@admin_app.route("/candles/edit/<int:candle_id>", methods=["GET", "POST"])
def edit_candle(candle_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candles WHERE id=?", (candle_id,))
    candle = cursor.fetchone()
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        image_url = request.form["image_url"]
        shape = request.form["shape"]
        colors = request.form["colors"]
        cursor.execute("""
            UPDATE candles SET name=?, price=?, description=?, image_url=?, shape=?, colors=?
            WHERE id=?
        """, (name, price, description, image_url, shape, colors, candle_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin.admin_candles"))
    conn.close()
    return render_template("admin/edit_candle.html", candle=candle)

@admin_app.route("/candles/delete/<int:candle_id>")
def delete_candle(candle_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candles WHERE id=?", (candle_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin.admin_candles"))

# ---------- Адмінка замовлень ----------

@admin_app.route("/orders")
def admin_orders():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    conn.close()
    return render_template("admin/admin_orders.html", orders=orders)
