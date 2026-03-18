from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Giriş yapanları hatırlaması için gizli anahtar (zorunlu)
app.secret_key = 'cok_gizli_anahtar_degistir' 

def init_db():
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    # Kullanıcılar tablosu (Benzersiz isimler)
    c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  kullanici_adi TEXT UNIQUE, 
                  sifre TEXT)''')
    # Mesajlar tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS mesajlar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  kullanici_adi TEXT, 
                  mesaj TEXT, 
                  tarih TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ANA SAYFA: AKIŞI GÖSTER
@app.route('/')
def ana_sayfa():
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    c.execute('SELECT kullanici_adi, mesaj, tarih FROM mesajlar ORDER BY id DESC')
    gonderiler = c.fetchall()
    conn.close()
    return render_template('index.html', gonderiler=gonderiler)

# KAYIT OLMA SİSTEMİ
@app.route('/kayit', methods=['POST'])
def kayit():
    k_adi = request.form['kullanici_adi'].strip()
    sifre = request.form['sifre']
    
    if len(k_adi) < 3 or len(sifre) < 3:
        flash("İsim ve şifre en az 3 harf olmalı!")
        return redirect(url_for('ana_sayfa'))
        
    hashli_sifre = generate_password_hash(sifre) # Şifreyi gizle
    
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)', (k_adi, hashli_sifre))
        conn.commit()
        session['kullanici'] = k_adi # Otomatik giriş yap
    except sqlite3.IntegrityError:
        flash("Bu lakap kapılmış moruk, başkasını dene!")
    finally:
        conn.close()
        
    return redirect(url_for('ana_sayfa'))

# GİRİŞ YAPMA SİSTEMİ
@app.route('/giris', methods=['POST'])
def giris():
    k_adi = request.form['kullanici_adi'].strip()
    sifre = request.form['sifre']
    
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    c.execute('SELECT sifre FROM kullanicilar WHERE kullanici_adi = ?', (k_adi,))
    kullanici = c.fetchone()
    conn.close()
    
    if kullanici and check_password_hash(kullanici[0], sifre):
        session['kullanici'] = k_adi
    else:
        flash("Kullanıcı adı veya şifre yanlış!")
        
    return redirect(url_for('ana_sayfa'))

# ÇIKIŞ YAPMA
@app.route('/cikis')
def cikis():
    session.pop('kullanici', None)
    return redirect(url_for('ana_sayfa'))

# TWEET ATMA
@app.route('/gonder', methods=['POST'])
def gonder():
    if 'kullanici' not in session:
        return redirect(url_for('ana_sayfa'))
        
    kullanici = session['kullanici']
    mesaj = request.form['mesaj']
    tarih = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
    
    if mesaj:
        conn = sqlite3.connect('mekan.db')
        c = conn.cursor()
        c.execute('INSERT INTO mesajlar (kullanici_adi, mesaj, tarih) VALUES (?, ?, ?)', (kullanici, mesaj, tarih))
        conn.commit()
        conn.close()
        
    return redirect(url_for('ana_sayfa'))

if __name__ == '__main__':
    app.run(debug=True)
