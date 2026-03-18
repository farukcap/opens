from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime

app = Flask(__name__)

# Veritabanını kuruyoruz
def init_db():
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS mesajlar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  kullanici TEXT, 
                  mesaj TEXT, 
                  tarih TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Ana sayfa: Mesajları göster
@app.route('/')
def ana_sayfa():
    conn = sqlite3.connect('mekan.db')
    c = conn.cursor()
    c.execute('SELECT kullanici, mesaj, tarih FROM mesajlar ORDER BY id DESC')
    gonderiler = c.fetchall()
    conn.close()
    return render_template('index.html', gonderiler=gonderiler)

# Yeni mesaj gönderme işlemi
@app.route('/gonder', methods=['POST'])
def gonder():
    kullanici = request.form['kullanici']
    mesaj = request.form['mesaj']
    tarih = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
    
    if kullanici and mesaj:
        conn = sqlite3.connect('mekan.db')
        c = conn.cursor()
        c.execute('INSERT INTO mesajlar (kullanici, mesaj, tarih) VALUES (?, ?, ?)', (kullanici, mesaj, tarih))
        conn.commit()
        conn.close()
        
    return redirect(url_for('ana_sayfa'))

if __name__ == '__main__':
    app.run(debug=True)
