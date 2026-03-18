from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "bizim-mekan-super-secret-key-2024"

ADMIN_SIFRESI = "faruk4848"

DATABASE = "mekan.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS kullanicilar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  kullanici_adi TEXT UNIQUE NOT NULL, 
                  sifre TEXT NOT NULL,
                  olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS mesajlar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  kullanici_adi TEXT NOT NULL, 
                  mesaj TEXT NOT NULL, 
                  tarih TEXT NOT NULL,
                  FOREIGN KEY(kullanici_adi) REFERENCES kullanicilar(kullanici_adi) ON DELETE CASCADE)""")
    
    c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", ("admin",))
    if not c.fetchone():
        hashli_sifre = generate_password_hash(ADMIN_SIFRESI)
        c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", 
                 ("admin", hashli_sifre))
    
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def ana_sayfa():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, kullanici_adi, mesaj, tarih FROM mesajlar ORDER BY id DESC LIMIT 100")
        gonderiler = c.fetchall()
        conn.close()
        
        is_admin = session.get("kullanici") == "admin"
        
        return render_template("index.html", gonderiler=gonderiler, is_admin=is_admin)
    except Exception as e:
        print(f"Hata ana_sayfa: {e}")
        flash("Veritabaninda bir hata olustur.")
        return redirect(url_for("ana_sayfa"))

@app.route("/kayit", methods=["POST"])
def kayit():
    try:
        k_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "").strip()
        
        if not k_adi or not sifre:
            flash("Kullanici adi ve sifre bos olamaz!")
            return redirect(url_for("ana_sayfa"))
        
        if len(k_adi) < 3:
            flash("Kullanici adi en az 3 karakter olmali!")
            return redirect(url_for("ana_sayfa"))
        
        if len(sifre) < 3:
            flash("Sifre en az 3 karakter olmali!")
            return redirect(url_for("ana_sayfa"))
        
        if k_adi.lower() == "admin":
            flash("Bu ad zaten kullaniliyor!")
            return redirect(url_for("ana_sayfa"))
        
        hashli_sifre = generate_password_hash(sifre)
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", 
                     (k_adi, hashli_sifre))
            conn.commit()
            session["kullanici"] = k_adi
            flash(f"Hosgeldin {k_adi}!")
        except sqlite3.IntegrityError:
            flash("Bu kullanici adi zaten alinmis!")
        finally:
            conn.close()
        
        return redirect(url_for("ana_sayfa"))
    
    except Exception as e:
        print(f"Hata kayit: {e}")
        flash("Kayit sirasinda bir hata olustur.")
        return redirect(url_for("ana_sayfa"))

@app.route("/giris", methods=["POST"])
def giris():
    try:
        k_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "").strip()
        
        if not k_adi or not sifre:
            flash("Kullanici adi ve sifre bos olamaz!")
            return redirect(url_for("ana_sayfa"))
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT sifre FROM kullanicilar WHERE kullanici_adi = ?", (k_adi,))
        kullanici = c.fetchone()
        conn.close()
        
        if kullanici and check_password_hash(kullanici["sifre"], sifre):
            session["kullanici"] = k_adi
            flash(f"Hosgeldin {k_adi}!")
        else:
            flash("Kullanici adi veya sifre yanlis!")
        
        return redirect(url_for("ana_sayfa"))
    
    except Exception as e:
        print(f"Hata giris: {e}")
        flash("Giris sirasinda bir hata olustur.")
        return redirect(url_for("ana_sayfa"))

@app.route("/cikis")
def cikis():
    kullanici = session.get("kullanici", "Kullanici")
    session.pop("kullanici", None)
    flash("Hosca kalin!")
    return redirect(url_for("ana_sayfa"))

@app.route("/gonder_api", methods=["POST"])
def gonder_api():
    try:
        if "kullanici" not in session:
            return jsonify({"hata": "Lutfen giris yap."}), 401
        
        kullanici = session["kullanici"]
        mesaj = request.form.get("mesaj", "").strip()
        
        if not mesaj:
            return jsonify({"hata": "Mesaj bos olamaz."}), 400
        
        if len(mesaj) > 280:
            return jsonify({"hata": "Mesaj 280 karakterden fazla olamaz."}), 400
        
        tarih = datetime.datetime.now().strftime("%H:%M - %d.%m.%Y")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO mesajlar (kullanici_adi, mesaj, tarih) VALUES (?, ?, ?)", 
                 (kullanici, mesaj, tarih))
        mesaj_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "id": mesaj_id,
            "kullanici_adi": kullanici,
            "mesaj": mesaj,
            "tarih": tarih,
            "is_admin": kullanici == "admin"
        }), 201
    
    except Exception as e:
        print(f"Hata gonder_api: {e}")
        return jsonify({"hata": "Gonderir gonderilirken bir hata olustur."}), 500

@app.route("/sil/<int:mesaj_id>", methods=["POST", "GET"])
def sil(mesaj_id):
    try:
        if session.get("kullanici") != "admin":
            if request.method == "POST":
                return jsonify({"hata": "Sadece admin silebilir!"}), 403
            else:
                flash("Sadece admin silebilir!")
                return redirect(url_for("ana_sayfa"))
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM mesajlar WHERE id = ?", (mesaj_id,))
        conn.commit()
        conn.close()
        
        if request.method == "POST":
            return jsonify({"success": True}), 200
        else:
            flash("Gonderi silindi.")
            return redirect(url_for("ana_sayfa"))
    
    except Exception as e:
        print(f"Hata sil: {e}")
        if request.method == "POST":
            return jsonify({"hata": "Silme sirasinda bir hata olustur."}), 500
        else:
            flash("Silme sirasinda bir hata olustur.")
            return redirect(url_for("ana_sayfa"))

@app.errorhandler(404)
def not_found(e):
    return "Sayfa bulunamadi", 404

@app.errorhandler(500)
def server_error(e):
    return "Sunucu hatasi", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
