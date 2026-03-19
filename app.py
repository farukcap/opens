from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bizim-mekan-kusursuz-v3"

ADMIN_USERNAME = "faruk"
ADMIN_PASSWORD = "faruk4848"
DATABASE = "mekan.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Temel Tablolar
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT, bio TEXT DEFAULT 'Mekan''a yeni katıldı!',
        last_seen TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, 
        created_at TEXT, likes_count INTEGER DEFAULT 0, retweets_count INTEGER DEFAULT 0, 
        replies_count INTEGER DEFAULT 0, views_count INTEGER DEFAULT 0)""")
    
    c.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, author TEXT, content TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS retweets (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS post_views (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    
    # YENİ TABLOLAR
    c.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, post_id INTEGER, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE, count INTEGER DEFAULT 1)")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio) VALUES (?, ?, ?)", (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu 👑"))
    
    conn.commit(); conn.close()

init_db()

# Çevrimiçi Durumu Güncelleme
@app.before_request
def update_last_seen():
    if "username" in session:
        conn = get_db()
        conn.execute("UPDATE users SET last_seen = ? WHERE username = ?", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session["username"]))
        conn.commit(); conn.close()

def notify(recipient, sender, n_type, post_id=0):
    if recipient != sender:
        conn = get_db()
        conn.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                     (recipient, sender, n_type, post_id, datetime.datetime.now().strftime("%d %b %H:%M")))
        conn.commit(); conn.close()

# --- YÖNLENDİRMELER ---
@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    conn = get_db()
    posts = conn.execute("SELECT p.*, u.last_seen FROM posts p JOIN users u ON p.author = u.username ORDER BY p.id DESC LIMIT 50").fetchall()
    users = conn.execute("SELECT username, last_seen FROM users WHERE username != ? ORDER BY RANDOM() LIMIT 5", (session["username"],)).fetchall()
    trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
    unread_notifs = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (session["username"],)).fetchone()['c']
    conn.close()
    return render_template("index.html", page="home", posts=posts, users=users, trends=trends, unread_notifs=unread_notifs, current_user=session["username"], is_admin=(session["username"]==ADMIN_USERNAME))

@app.route("/profile/<username>")
def profile(username):
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user: return redirect(url_for("home"))
    
    posts = conn.execute("SELECT p.*, u.last_seen FROM posts p JOIN users u ON p.author = u.username WHERE author = ? ORDER BY p.id DESC", (username,)).fetchall()
    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone() is not None
    followers = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']
    following = conn.execute("SELECT COUNT(*) as c FROM follows WHERE follower = ?", (username,)).fetchone()['c']
    conn.close()
    
    return render_template("index.html", page="profile", profile_user=user, posts=posts, followers=followers, following=following, is_following=is_following, current_user=session["username"])

@app.route("/notifications")
def notifications():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    notifs = conn.execute("SELECT * FROM notifications WHERE recipient = ? ORDER BY id DESC LIMIT 30", (session["username"],)).fetchall()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient = ?", (session["username"],))
    conn.commit(); conn.close()
    return render_template("index.html", page="notifications", notifs=notifs, current_user=session["username"])

@app.route("/bookmarks")
def bookmarks():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    posts = conn.execute("SELECT p.*, u.last_seen FROM posts p JOIN bookmarks b ON p.id = b.post_id JOIN users u ON p.author = u.username WHERE b.user = ? ORDER BY b.id DESC", (session["username"],)).fetchall()
    conn.close()
    return render_template("index.html", page="bookmarks", posts=posts, current_user=session["username"])

@app.route("/messages")
def messages():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    chats = conn.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ?", (session["username"], session["username"], session["username"])).fetchall()
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
    if len(username) < 3 or not username.isalnum():
        flash("Geçersiz kullanıcı adı! (Sadece harf ve rakam)"); return redirect(url_for("home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        conn.commit(); session["username"] = username
    except: flash("Bu isim alınmış!")
    finally: conn.close()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    conn = get_db()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password): session["username"] = username
    else: flash("Hatalı giriş!")
    return redirect(url_for("home"))

@app.route("/logout")
def logout(): session.pop("username", None); return redirect(url_for("home"))

@app.route("/api/edit_profile", methods=["POST"])
def edit_profile():
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    bio = request.form.get("bio", "")[:150]
    conn = get_db()
    conn.execute("UPDATE users SET bio = ? WHERE username = ?", (bio, session["username"]))
    conn.commit(); conn.close()
    return redirect(url_for("profile", username=session["username"]))

@app.route("/api/post", methods=["POST"])
def create_post():
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş olamaz"})
    
    # Spam Koruması
    conn = get_db()
    last_post = conn.execute("SELECT created_at FROM posts WHERE author = ? ORDER BY id DESC LIMIT 1", (session["username"],)).fetchone()
    
    # Hashtagleri Bul ve Ekle
    hashtags = re.findall(r"#(\w+)", content)
    for tag in hashtags:
        exists = conn.execute("SELECT id FROM hashtags WHERE tag = ?", (tag,)).fetchone()
        if exists: conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
        else: conn.execute("INSERT INTO hashtags (tag) VALUES (?)", (tag,))
        
    time_str = datetime.datetime.now().strftime("%d %b %H:%M")
    conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, time_str))
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/reply/<int:post_id>", methods=["POST"])
def add_reply(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"}), 401
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"error": "Boş olamaz"})
    
    time_str = datetime.datetime.now().strftime("%d %b %H:%M")
    conn = get_db()
    conn.execute("INSERT INTO replies (post_id, author, content, created_at) VALUES (?, ?, ?, ?)", (post_id, session["username"], content, time_str))
    conn.execute("UPDATE posts SET replies_count = replies_count + 1 WHERE id = ?", (post_id,))
    
    post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.commit(); conn.close()
    
    if post: notify(post["author"], session["username"], "reply", post_id)
    return jsonify({"success": True})

@app.route("/api/replies/<int:post_id>")
def get_replies(post_id):
    conn = get_db()
    replies = conn.execute("SELECT * FROM replies WHERE post_id = ? ORDER BY id ASC", (post_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in replies])

@app.route("/api/action/<action_type>/<int:post_id>", methods=["POST"])
def post_action(action_type, post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    
    conn = get_db()
    if action_type == "bookmark":
        exists = conn.execute("SELECT 1 FROM bookmarks WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
        if exists: conn.execute("DELETE FROM bookmarks WHERE user = ? AND post_id = ?", (session["username"], post_id))
        else: conn.execute("INSERT INTO bookmarks (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.commit(); conn.close()
        return jsonify({"success": True})

    table, col = ("likes", "likes_count") if action_type == "like" else ("retweets", "retweets_count")
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone()
    
    if exists:
        conn.execute(f"DELETE FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} - 1 WHERE id = ?", (post_id,))
    else:
        conn.execute(f"INSERT INTO {table} (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} + 1 WHERE id = ?", (post_id,))
        post_author = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()["author"]
        if action_type == "like": notify(post_author, session["username"], "like", post_id)
    
    count = conn.execute(f"SELECT {col} FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({"success": True, "count": count})

@app.route("/api/follow/<username>", methods=["POST"])
def follow_user(username):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    conn = get_db()
    exists = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone()
    if exists:
        conn.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (session["username"], username))
        action = "unfollowed"
    else:
        conn.execute("INSERT INTO follows (follower, followed) VALUES (?, ?)", (session["username"], username))
        action = "followed"
        notify(username, session["username"], "follow")
    conn.commit(); conn.close()
    return jsonify({"success": True, "action": action})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    me = session["username"]
    conn = get_db()
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        time_str = datetime.datetime.now().strftime("%H:%M")
        if content:
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", (me, partner, content, time_str))
            conn.commit()
            return jsonify({"success": True})
            
    conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
    conn.commit()
    msgs = conn.execute("SELECT sender, content, created_at, is_read FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/view/<int:post_id>", methods=["POST"])
def view_post(post_id):
    if "username" not in session: return jsonify({"success": False})
    conn = get_db()
    if not conn.execute("SELECT 1 FROM post_views WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone():
        conn.execute("INSERT INTO post_views (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute("UPDATE posts SET views_count = views_count + 1 WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    conn = get_db()
    users = conn.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 5", (f"%{q}%",)).fetchall()
    conn.close()
    return jsonify([u["username"] for u in users])

@app.route("/api/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    conn = get_db()
    post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
    if session["username"] == ADMIN_USERNAME or post["author"] == session["username"]:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
