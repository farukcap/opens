from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bizim-mekan-super-secret-key-2024-faruk"

ADMIN_USERNAME = "faruk"
ADMIN_PASSWORD = "faruk4848"
DATABASE = "mekan.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE NOT NULL, 
                  password TEXT NOT NULL,
                  bio TEXT DEFAULT '',
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  author TEXT NOT NULL, 
                  content TEXT NOT NULL, 
                  created_at TEXT NOT NULL,
                  likes_count INTEGER DEFAULT 0,
                  retweets_count INTEGER DEFAULT 0,
                  FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE)""")

    # YENİ: Yanıtlar (Yorumlar) Tablosu
    c.execute("""CREATE TABLE IF NOT EXISTS replies
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  author TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                  FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE)""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  is_read INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user TEXT NOT NULL,
                  post_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(user, post_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS retweets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user TEXT NOT NULL,
                  post_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(user, post_id))""")

    c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if not c.fetchone():
        hashed = generate_password_hash(ADMIN_PASSWORD)
        c.execute("INSERT INTO users (username, password, bio) VALUES (?, ?, ?)", 
                 (ADMIN_USERNAME, hashed, "Kurucu / Admin"))

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    if session.get("username"):
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""SELECT p.id, p.author, p.content, p.created_at, 
                     p.likes_count, p.retweets_count, u.bio
                     FROM posts p JOIN users u ON p.author = u.username
                     ORDER BY p.id DESC LIMIT 100""")
        posts = c.fetchall()
        
        c.execute("SELECT username, bio FROM users WHERE username != ? ORDER BY id DESC", (session["username"],))
        all_users = c.fetchall()
        
        # YENİ: Yeni katılanları ayır (Son 5 kişi)
        c.execute("SELECT username FROM users WHERE username != ? ORDER BY id DESC LIMIT 5", (session["username"],))
        new_users = c.fetchall()
        
        conn.close()
        return render_template("index.html", posts=posts, all_users=all_users, new_users=new_users, 
                             current_user=session.get("username"), is_admin=(session.get("username") == ADMIN_USERNAME))
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if len(username) < 2 or len(password) < 4:
        flash("Kullanıcı adı en az 2, şifre en az 4 karakter olmalı!")
        return redirect(url_for("home"))
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        conn.commit()
        session["username"] = username
    except sqlite3.IntegrityError:
        flash("Bu kullanıcı adı alınmış!")
    finally:
        conn.close()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    conn = get_db_connection()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user["password"], password):
        session["username"] = username
    else:
        flash("Hatalı giriş!")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@app.route("/post", methods=["POST"])
def create_post():
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş mesaj"}), 400
    
    created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, created_at))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "id": post_id, "author": session["username"], "content": content, "created_at": created_at, "likes_count": 0, "retweets_count": 0})

@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db_connection()
    post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post: return jsonify({"error": "Bulunamadı"}), 404
    
    if session["username"] != ADMIN_USERNAME and post["author"] != session["username"]:
        return jsonify({"error": "Yetkisiz"}), 403
        
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- YENİ: YANIT SİSTEMİ (REPLIES) ---
@app.route("/reply/<int:post_id>", methods=["POST"])
def add_reply(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş yorum"}), 400
    
    created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO replies (post_id, author, content, created_at) VALUES (?, ?, ?, ?)", 
             (post_id, session["username"], content, created_at))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "author": session["username"], "content": content, "created_at": created_at})

@app.route("/api/replies/<int:post_id>")
def get_replies(post_id):
    conn = get_db_connection()
    replies = conn.execute("SELECT author, content, created_at FROM replies WHERE post_id = ? ORDER BY id ASC", (post_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in replies])

# --- YENİ: DM / MESAJLAŞMA SİSTEMİ (MODAL İÇİN) ---
@app.route("/api/messages/<username>")
def fetch_messages(username):
    if "username" not in session: return jsonify([])
    current = session["username"]
    conn = get_db_connection()
    msgs = conn.execute("""SELECT sender, content, created_at FROM messages 
                           WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) 
                           ORDER BY id ASC""", (current, username, username, current)).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/send_message", methods=["POST"])
def api_send_msg():
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    recipient = request.form.get("recipient")
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş mesaj"})
    
    created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", 
                 (session["username"], recipient, content, created_at))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "sender": session["username"], "content": content, "created_at": created_at})

# Eylemler (Like/Retweet)
@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db_connection(); c = conn.cursor()
    existing = c.execute("SELECT id FROM likes WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
    if existing:
        c.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (session["username"], post_id))
        c.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
        action = "unliked"
    else:
        c.execute("INSERT INTO likes (user, post_id, created_at) VALUES (?, ?, ?)", (session["username"], post_id, datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
        c.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        action = "liked"
    likes = c.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,)).fetchone()["likes_count"]
    conn.commit(); conn.close()
    return jsonify({"success": True, "action": action, "likes_count": likes})

@app.route("/retweet/<int:post_id>", methods=["POST"])
def retweet_post(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    conn = get_db_connection(); c = conn.cursor()
    existing = c.execute("SELECT id FROM retweets WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
    if existing:
        c.execute("DELETE FROM retweets WHERE user = ? AND post_id = ?", (session["username"], post_id))
        c.execute("UPDATE posts SET retweets_count = retweets_count - 1 WHERE id = ?", (post_id,))
        action = "unretweeted"
    else:
        c.execute("INSERT INTO retweets (user, post_id, created_at) VALUES (?, ?, ?)", (session["username"], post_id, datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
        c.execute("UPDATE posts SET retweets_count = retweets_count + 1 WHERE id = ?", (post_id,))
        action = "retweeted"
    retweets = c.execute("SELECT retweets_count FROM posts WHERE id = ?", (post_id,)).fetchone()["retweets_count"]
    conn.commit(); conn.close()
    return jsonify({"success": True, "action": action, "retweets_count": retweets})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
