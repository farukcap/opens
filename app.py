from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
# ⚠️ ÖNEMLİ 1: Giriş yapanları hatırlaması için rastgele bir anahtar.
app.secret_key = str(uuid.uuid4())

# ⚠️ ÖNEMLİ 2: SİTENİN YÖNETİCİ ŞİFRESİ. Bunu kesinlikle değiştir!
# Yönetici kullanıcı adın her zaman 'admin' olacak.
ADMIN_SIFRESI = 'faruk48' # <--- Burayı 'asdf' gibi kendi şifrenle değiştir.

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
    
    # ⚠️ ÖNEMLİ 3: İlk kez kurulurken 'admin' kullanıcısını yarat.
    c.execute('SELECT * FROM kullanicilar WHERE kullanici_adi = "faruk"')
    if not c.fetchone():
        hashli_sifre = generate_password_hash(ADMIN_SIFRESI)
        c.execute('INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES ("admin", ?)', (hashli_sifre,))
        
    conn.commit()
    conn.close()

init_db()

# ANA SAYFA: AKIŞI GÖSTER
@app.route('/')
def ana_sayfa():
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    c.execute('SELECT id, kullanici_adi, mesaj, tarih FROM mesajlar ORDER BY id DESC')
    gonderiler = c.fetchall()
    conn.close()
    
    # Admin olup olmadığını kontrol et (SİL butonu için)
    is_admin = False
    if 'kullanici' in session and session['kullanici'] == 'admin':
        is_admin = True
        
    return render_template('index.html', gonderiler=gonderiler, is_admin=is_admin)

# KAYIT OLMA
@app.route('/kayit', methods=['POST'])
def kayit():
    k_adi = request.form['kullanici_adi'].strip()
    sifre = request.form['sifre']
    
    # Güvenlik Kontrolleri
    if len(k_adi) < 3 or len(sifre) < 3:
        flash("İsim ve şifre en az 3 harf olmalı!")
        return redirect(url_for('ana_sayfa'))
    
    if k_adi == "admin":
        flash("Bu lakap kapılmış moruk, başkasını dene!")
        return redirect(url_for('ana_sayfa'))
        
    hashli_sifre = generate_password_hash(sifre)
    
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)', (k_adi, hashli_sifre))
        conn.commit()
        session['kullanici'] = k_adi # Otomatik giriş
    except sqlite3.IntegrityError:
        flash("Bu lakap kapılmış moruk, başkasını dene!")
    finally:
        conn.close()
        
    return redirect(url_for('ana_sayfa'))

# GİRİŞ YAPMA
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

# YENİ: AJAX İLE GÖNDERİ ATMA (Sayfa Yenilenmez)
@app.route('/gonder_api', methods=['POST'])
def gonder_api():
    if 'kullanici' not in session:
        return jsonify({'hata': 'Lütfen giriş yap.'}), 401
        
    kullanici = session['kullanici']
    mesaj = request.form['mesaj'].strip()
    tarih = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
    
    if mesaj:
        conn = sqlite3.connect('mekan.db')
        c = conn.cursor()
        c.execute('INSERT INTO mesajlar (kullanici_adi, mesaj, tarih) VALUES (?, ?, ?)', (kullanici, mesaj, tarih))
        mesaj_id = c.lastrowid # Son eklenen mesajın ID'si (admin silmesi için)
        conn.commit()
        conn.close()
        
        # Admin olup olmadığını kontrol et
        is_admin = False
        if kullanici == 'admin':
            is_admin = True
            
        return jsonify({
            'success': True,
            'id': mesaj_id,
            'kullanici_adi': kullanici,
            'mesaj': mesaj,
            'tarih': tarih,
            'is_admin': is_admin
        })
        
    return jsonify({'hata': 'Mesaj boş olamaz.'}), 400

# YENİ: YÖNETİCİ GÖNDERİ SİLME
@app.route('/sil/<int:mesaj_id>')
def sil(mesaj_id):
    # Güvenlik kontrolü: Sadece 'admin' silebilir
    if 'kullanici' in session and session['kullanici'] == 'admin':
        conn = sqlite3.connect('mekan.db')
        c = conn.cursor()
        c.execute('DELETE FROM mesajlar WHERE id = ?', (mesaj_id,))
        conn.commit()
        conn.close()
        flash("Gönderi silindi.")
    else:
        flash("Sadece yönetici silebilir moruk!")
        
    return redirect(url_for('ana_sayfa'))

if __name__ == '__main__':
    app.run(debug=True)
