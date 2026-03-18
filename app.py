from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(**name**)

# ⚠️ Secret key - SABIT bir değer (Render.com veya başka yerlerde deploy edince session kaybolmasın)

app.secret_key = "bizim-mekan-super-secret-key-2024"

# ⚠️ Admin şifresini burada değiştir

ADMIN_SIFRESI = "faruk4848"

DATABASE = "mekan.db"

def get_db_connection():
“”“Veritabanı bağlantısı oluştur”””
conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row  # Dict gibi erişim sağla
return conn

def init_db():
“”“Veritabanını başlat”””
conn = get_db_connection()
c = conn.cursor()

```
# Kullanıcılar tablosu
c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              kullanici_adi TEXT UNIQUE NOT NULL, 
              sifre TEXT NOT NULL,
              olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP)''')

# Mesajlar tablosu
c.execute('''CREATE TABLE IF NOT EXISTS mesajlar
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              kullanici_adi TEXT NOT NULL, 
              mesaj TEXT NOT NULL, 
              tarih TEXT NOT NULL,
              FOREIGN KEY(kullanici_adi) REFERENCES kullanicilar(kullanici_adi) ON DELETE CASCADE)''')

# Admin kullanıcısını kontrol et ve oluştur
c.execute('SELECT * FROM kullanicilar WHERE kullanici_adi = ?', ('admin',))
if not c.fetchone():
    hashli_sifre = generate_password_hash(ADMIN_SIFRESI)
    c.execute('INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)', 
             ('admin', hashli_sifre))

conn.commit()
conn.close()
```

# Başlangıçta veritabanını başlat

init_db()

@app.route(’/’)
def ana_sayfa():
“”“Ana sayfa - Tüm mesajları göster”””
try:
conn = get_db_connection()
c = conn.cursor()
c.execute(‘SELECT id, kullanici_adi, mesaj, tarih FROM mesajlar ORDER BY id DESC LIMIT 100’)
gonderiler = c.fetchall()
conn.close()

```
    # Admin kontrolü
    is_admin = session.get('kullanici') == 'admin'
    
    return render_template('index.html', gonderiler=gonderiler, is_admin=is_admin)
except Exception as e:
    print(f"Hata ana_sayfa: {e}")
    flash("Veritabanında bir hata oluştu. Lütfen daha sonra dene.")
    return redirect(url_for('ana_sayfa'))
```

@app.route(’/kayit’, methods=[‘POST’])
def kayit():
“”“Yeni kullanıcı kaydı”””
try:
k_adi = request.form.get(‘kullanici_adi’, ‘’).strip()
sifre = request.form.get(‘sifre’, ‘’).strip()

```
    # Validasyon
    if not k_adi or not sifre:
        flash("Kullanıcı adı ve şifre boş olamaz!")
        return redirect(url_for('ana_sayfa'))
    
    if len(k_adi) < 3:
        flash("Kullanıcı adı en az 3 karakter olmalı!")
        return redirect(url_for('ana_sayfa'))
    
    if len(sifre) < 3:
        flash("Şifre en az 3 karakter olmalı!")
        return redirect(url_for('ana_sayfa'))
    
    if k_adi.lower() == "admin":
        flash("Bu ad zaten kullanılıyor!")
        return redirect(url_for('ana_sayfa'))
    
    # Veritabanına ekle
    hashli_sifre = generate_password_hash(sifre)
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)', 
                 (k_adi, hashli_sifre))
        conn.commit()
        session['kullanici'] = k_adi
        flash(f"Hoşgeldin {k_adi}! 🎉")
    except sqlite3.IntegrityError:
        flash("Bu kullanıcı adı zaten alınmış!")
    finally:
        conn.close()
    
    return redirect(url_for('ana_sayfa'))

except Exception as e:
    print(f"Hata kayit: {e}")
    flash("Kayıt sırasında bir hata oluştu.")
    return redirect(url_for('ana_sayfa'))
```

@app.route(’/giris’, methods=[‘POST’])
def giris():
“”“Giriş yap”””
try:
k_adi = request.form.get(‘kullanici_adi’, ‘’).strip()
sifre = request.form.get(‘sifre’, ‘’).strip()

```
    if not k_adi or not sifre:
        flash("Kullanıcı adı ve şifre boş olamaz!")
        return redirect(url_for('ana_sayfa'))
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT sifre FROM kullanicilar WHERE kullanici_adi = ?', (k_adi,))
    kullanici = c.fetchone()
    conn.close()
    
    if kullanici and check_password_hash(kullanici['sifre'], sifre):
        session['kullanici'] = k_adi
        flash(f"Hoşgeldin {k_adi}! 👋")
    else:
        flash("Kullanıcı adı veya şifre yanlış!")
    
    return redirect(url_for('ana_sayfa'))

except Exception as e:
    print(f"Hata giris: {e}")
    flash("Giriş sırasında bir hata oluştu.")
    return redirect(url_for('ana_sayfa'))
```

@app.route(’/cikis’)
def cikis():
“”“Çıkış yap”””
kullanici = session.get(‘kullanici’, ‘Kullanıcı’)
session.pop(‘kullanici’, None)
flash(f”Hoşça kalın!”)
return redirect(url_for(‘ana_sayfa’))

@app.route(’/gonder_api’, methods=[‘POST’])
def gonder_api():
“”“AJAX ile gönderi gönder”””
try:
if ‘kullanici’ not in session:
return jsonify({‘hata’: ‘Lütfen giriş yap.’}), 401

```
    kullanici = session['kullanici']
    mesaj = request.form.get('mesaj', '').strip()
    
    if not mesaj:
        return jsonify({'hata': 'Mesaj boş olamaz.'}), 400
    
    if len(mesaj) > 280:
        return jsonify({'hata': 'Mesaj 280 karakterden fazla olamaz.'}), 400
    
    # Tarih formatı
    tarih = datetime.datetime.now().strftime("%H:%M - %d.%m.%Y")
    
    # Veritabanına ekle
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO mesajlar (kullanici_adi, mesaj, tarih) VALUES (?, ?, ?)', 
             (kullanici, mesaj, tarih))
    mesaj_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Cevap gönder
    return jsonify({
        'success': True,
        'id': mesaj_id,
        'kullanici_adi': kullanici,
        'mesaj': mesaj,
        'tarih': tarih,
        'is_admin': kullanici == 'admin'
    }), 201

except Exception as e:
    print(f"Hata gonder_api: {e}")
    return jsonify({'hata': 'Gönderi gönderilirken bir hata oluştu.'}), 500
```

@app.route(’/sil/<int:mesaj_id>’, methods=[‘POST’, ‘GET’])
def sil(mesaj_id):
“”“Admin: Gönderi sil”””
try:
if session.get(‘kullanici’) != ‘admin’:
if request.method == ‘POST’:
return jsonify({‘hata’: ‘Sadece admin silebilir!’}), 403
else:
flash(“Sadece admin silebilir!”)
return redirect(url_for(‘ana_sayfa’))

```
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM mesajlar WHERE id = ?', (mesaj_id,))
    conn.commit()
    conn.close()
    
    if request.method == 'POST':
        return jsonify({'success': True}), 200
    else:
        flash("Gönderi silindi.")
        return redirect(url_for('ana_sayfa'))

except Exception as e:
    print(f"Hata sil: {e}")
    if request.method == 'POST':
        return jsonify({'hata': 'Silme sırasında bir hata oluştu.'}), 500
    else:
        flash("Silme sırasında bir hata oluştu.")
        return redirect(url_for('ana_sayfa'))
```

@app.route(’/api/stats’)
def api_stats():
“”“Admin paneli için istatistikler”””
try:
if session.get(‘kullanici’) != ‘admin’:
return jsonify({‘hata’: ‘Yetkisiz’}), 403

```
    conn = get_db_connection()
    c = conn.cursor()
    
    # Toplam kullanıcı
    c.execute('SELECT COUNT(*) as count FROM kullanicilar')
    toplam_kullanici = c.fetchone()['count']
    
    # Toplam mesaj
    c.execute('SELECT COUNT(*) as count FROM mesajlar')
    toplam_mesaj = c.fetchone()['count']
    
    # En aktif kullanıcılar
    c.execute('SELECT kullanici_adi, COUNT(*) as count FROM mesajlar GROUP BY kullanici_adi ORDER BY count DESC LIMIT 5')
    en_aktif = c.fetchall()
    
    conn.close()
    
    return jsonify({
        'toplam_kullanici': toplam_kullanici,
        'toplam_mesaj': toplam_mesaj,
        'en_aktif': [dict(row) for row in en_aktif]
    }), 200

except Exception as e:
    print(f"Hata api_stats: {e}")
    return jsonify({'hata': 'İstatistik alınamadı'}), 500
```

# Hata sayfaları

@app.errorhandler(404)
def not_found(e):
return render_template(‘404.html’), 404

@app.errorhandler(500)
def server_error(e):
return render_template(‘500.html’), 500

if **name** == ‘**main**’:
# Üretim ortamında debug=False olmalı
app.run(debug=True, host=‘0.0.0.0’, port=5000)
