from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bizim-mekan-kusursuz-2024"

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

    # Kullanıcılar
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE NOT NULL, 
                  password TEXT NOT NULL,
                  bio TEXT DEFAULT 'Mekan''a yeni katıldı!',
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # Gönderiler (Görüntülenme eklendi)
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  author TEXT NOT NULL, 
                  content TEXT NOT NULL, 
                  created_at TEXT NOT NULL,
                  likes_count INTEGER DEFAULT 0,
                  retweets_count INTEGER DEFAULT 0,
                  views_count INTEGER DEFAULT 0)""")

    # Yanıtlar
    c.execute("""CREATE TABLE IF NOT EXISTS replies (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER NOT NULL,
                  author TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL)""")

    # Mesajlar (Görüldü eklendi)
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  content TEXT NOT NULL,
                  is_read INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL)""")

    # Takip Sistemi
    c.execute("""CREATE TABLE IF NOT EXISTS follows (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  follower TEXT NOT NULL,
                  followed TEXT NOT NULL,
                  UNIQUE(follower, followed))""")

    # Beğeniler ve Retweetler
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS retweets (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS post_views (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")

    # Admin Kontrolü
    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio) VALUES (?, ?, ?)", 
                 (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu 👑"))

    conn.commit()
    conn.close()

init_db()

# --- YARDIMCI FONKSİYONLAR ---
def get_user_stats(username):
    conn = get_db_connection()
    followers = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']
    following = conn.execute("SELECT COUNT(*) as c FROM follows WHERE follower = ?", (username,)).fetchone()['c']
    conn.close()
    return followers, following

# --- SAYFALAR ---
@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 50").fetchall()
    users = conn.execute("SELECT username FROM users WHERE username != ? ORDER BY id DESC LIMIT 10", (session["username"],)).fetchall()
    conn.close()
    
    return render_template("index.html", page="home", posts=posts, users=users, current_user=session["username"], is_admin=(session["username"]==ADMIN_USERNAME))

@app.route("/profile/<username>")
def profile(username):
    if not session.get("username"): return redirect(url_for("home"))
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user: return redirect(url_for("home"))
    
    posts = conn.execute("SELECT * FROM posts WHERE author = ? ORDER BY id DESC", (username,)).fetchall()
    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone() is not None
    conn.close()
    
    followers, following = get_user_stats(username)
    
    return render_template("index.html", page="profile", profile_user=user, posts=posts, 
                           followers=followers, following=following, is_following=is_following,
                           current_user=session["username"], is_admin=(session["username"]==ADMIN_USERNAME))

@app.route("/messages")
def messages():
    if not session.get("username"): return redirect(url_for("home"))
    
    conn = get_db_connection()
    # Konuşulan kişileri getir
    chats = conn.execute("""
        SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner 
        FROM messages WHERE sender = ? OR recipient = ?
    """, (session["username"], session["username"], session["username"])).fetchall()
    conn.close()
    
    return render_template("index.html", page="messages", chats=chats, current_user=session["username"])

@app.route("/messages/<username>")
def chat_room(username):
    if not session.get("username"): return redirect(url_for("home"))
    return render_template("index.html", page="chat", chat_partner=username, current_user=session["username"])

# --- API (ETKİLEŞİMLER) ---
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    if len(username) < 3:
        flash("Kullanıcı adı en az 3 karakter olmalı!")
        return redirect(url_for("home"))
    
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        conn.commit()
        session["username"] = username
    except:
        flash("Bu isim alınmış!")
    finally:
        conn.close()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    conn = get_db_connection()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password): session["username"] = username
    else: flash("Şifre veya kullanıcı adı hatalı!")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@app.route("/api/post", methods=["POST"])
def create_post():
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş olamaz"})
    
    time_str = datetime.datetime.now().strftime("%d %b %H:%M")
    conn = get_db_connection()
    conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, time_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/follow/<username>", methods=["POST"])
def follow_user(username):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    me = session["username"]
    conn = get_db_connection()
    exists = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (me, username)).fetchone()
    if exists:
        conn.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (me, username))
        action = "unfollowed"
    else:
        conn.execute("INSERT INTO follows (follower, followed) VALUES (?, ?)", (me, username))
        action = "followed"
    conn.commit()
    conn.close()
    return jsonify({"success": True, "action": action})

@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    conn = get_db_connection()
    users = conn.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 5", (f"%{q}%",)).fetchall()
    conn.close()
    return jsonify([u["username"] for u in users])

@app.route("/api/view/<int:post_id>", methods=["POST"])
def view_post(post_id):
    if "username" not in session: return jsonify({"success": False})
    conn = get_db_connection()
    exists = conn.execute("SELECT 1 FROM post_views WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
    if not exists:
        conn.execute("INSERT INTO post_views (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute("UPDATE posts SET views_count = views_count + 1 WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/action/<action_type>/<int:post_id>", methods=["POST"])
def post_action(action_type, post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    table = "likes" if action_type == "like" else "retweets"
    col = "likes_count" if action_type == "like" else "retweets_count"
    
    conn = get_db_connection()
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
    if exists:
        conn.execute(f"DELETE FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} - 1 WHERE id = ?", (post_id,))
    else:
        conn.execute(f"INSERT INTO {table} (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} + 1 WHERE id = ?", (post_id,))
    
    count = conn.execute(f"SELECT {col} FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"success": True, "count": count})

@app.route("/api/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    conn = get_db_connection()
    post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
    if session["username"] == ADMIN_USERNAME or post["author"] == session["username"]:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- ANINDA MESAJLAŞMA SİSTEMİ ---
@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    me = session["username"]
    conn = get_db_connection()
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        time_str = datetime.datetime.now().strftime("%H:%M")
        if content:
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", (me, partner, content, time_str))
            conn.commit()
            return jsonify({"success": True})
            
    # GET: Mesajları getir ve okunmayanları 'Görüldü' yap
    conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
    conn.commit()
    
    msgs = conn.execute("""
        SELECT sender, content, created_at, is_read FROM messages 
        WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) 
        ORDER BY id ASC
    """, (me, partner, partner, me)).fetchall()
    conn.close()
    
    return jsonify([dict(m) for m in msgs])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
