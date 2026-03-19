from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v10-kusursuz"

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
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, bio TEXT DEFAULT 'Mekan''da yeni!', last_seen TEXT, is_verified INTEGER DEFAULT 0, profile_views INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT, likes_count INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT)") # YENİ: Gerçek Story Tablosu
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio, is_verified) VALUES (?, ?, ?, 1)", (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu 👑"))
    conn.commit(); conn.close()

init_db()

@app.context_processor
def inject_global():
    if "username" in session:
        conn = get_db()
        user = session["username"]
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET last_seen = ? WHERE username = ?", (time_str, user))
        
        unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        # Yeni Katılanlar (Her sayfada çalışır)
        new_users = conn.execute("SELECT username, is_verified FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 6", (user,)).fetchall()
        user_data = conn.execute("SELECT is_verified FROM users WHERE username = ?", (user,)).fetchone()
        conn.commit(); conn.close()
        
        return dict(
            current_user=user, 
            is_verified=user_data['is_verified'] if user_data else 0,
            unread_notifs=unread,
            new_users=new_users,
            is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

# --- SAYFALAR ---
@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    conn = get_db()
    posts = conn.execute("SELECT p.*, u.is_verified FROM posts p JOIN users u ON p.author = u.username ORDER BY p.id DESC LIMIT 50").fetchall()
    # Son 24 saatin hikayeleri
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    stories = conn.execute("SELECT s.*, u.is_verified FROM stories s JOIN users u ON s.author = u.username WHERE s.created_at > ? ORDER BY s.id DESC", (yesterday,)).fetchall()
    conn.close()
    return render_template("index.html", page="home", posts=posts, stories=stories)

@app.route("/profile/<username>")
def profile(username):
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user: return redirect(url_for("home"))
    
    if username != session["username"]:
        conn.execute("UPDATE users SET profile_views = profile_views + 1 WHERE username = ?", (username,))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    posts = conn.execute("SELECT p.*, u.is_verified FROM posts p JOIN users u ON p.author = u.username WHERE author = ? ORDER BY p.id DESC", (username,)).fetchall()
    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone() is not None
    followers = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']
    following = conn.execute("SELECT COUNT(*) as c FROM follows WHERE follower = ?", (username,)).fetchone()['c']
    conn.close()
    return render_template("index.html", page="profile", profile_user=user, posts=posts, followers=followers, following=following, is_following=is_following)

@app.route("/messages_page")
def messages_page():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    chats = conn.execute("""
        SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner 
        FROM messages WHERE sender = ? OR recipient = ?
    """, (session["username"], session["username"], session["username"])).fetchall()
    
    chat_list = []
    for c in chats:
        p_data = conn.execute("SELECT is_verified FROM users WHERE username = ?", (c['partner'],)).fetchone()
        chat_list.append({"partner": c['partner'], "is_verified": p_data['is_verified'] if p_data else 0})
    conn.close()
    return render_template("index.html", page="messages", chats=chat_list)

@app.route("/notifications")
def notifications():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    notifs = conn.execute("SELECT n.*, u.is_verified FROM notifications n JOIN users u ON n.sender = u.username WHERE recipient = ? ORDER BY n.id DESC LIMIT 30", (session["username"],)).fetchall()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient = ?", (session["username"],))
    conn.commit(); conn.close()
    return render_template("index.html", page="notifications", notifs=notifs)

# --- AUTH ---
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    if len(username) < 3: flash("En az 3 karakter!"); return redirect(url_for("home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
        conn.commit(); session["username"] = username
    except: flash("İsim alınmış!")
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

# --- GERÇEK API'LER ---
@app.route("/api/post_story", methods=["POST"])
def post_story():
    if "username" not in session: return jsonify({"error": "Hata"})
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        conn.execute("INSERT INTO stories (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/post", methods=["POST"])
def create_post():
    if "username" not in session: return jsonify({"error": "Hata"})
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "username" not in session: return jsonify({"error": "Hata"})
    conn = get_db()
    if conn.execute("SELECT 1 FROM likes WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone():
        conn.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (session["username"], post_id))
        conn.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
    else:
        conn.execute("INSERT INTO likes (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        # Bildirim
        post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post and post["author"] != session["username"]:
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'like', ?)", (post["author"], session["username"], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    count = conn.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({"success": True, "count": count})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    if "username" not in session: return jsonify({"error": "Hata"})
    me = session["username"]
    conn = get_db()
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", (me, partner, content, time_str))
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'message', ?)", (partner, me, time_str))
            conn.commit()
            return jsonify({"success": True})
            
    conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
    conn.commit()
    msgs = conn.execute("SELECT sender, content, created_at, is_read FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "username" not in session: return jsonify({"error": "Hata"})
    conn = get_db()
    post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
    if session["username"] == ADMIN_USERNAME or (post and post["author"] == session["username"]):
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/follow/<username>", methods=["POST"])
def follow_user(username):
    if "username" not in session: return jsonify({"error": "Hata"})
    conn = get_db()
    if conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone():
        conn.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (session["username"], username))
    else:
        conn.execute("INSERT INTO follows (follower, followed) VALUES (?, ?)", (session["username"], username))
        conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'follow', ?)", (username, session["username"], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
