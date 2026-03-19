from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-god-mode-secret-key-2026"

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

    # USERS: Hayalet modu (ghost_mode) eklendi
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        bio TEXT DEFAULT 'Mekan''da yeni!',
        avatar_color TEXT DEFAULT '#1d9bf0',
        last_seen TEXT,
        is_verified INTEGER DEFAULT 0,
        ghost_mode INTEGER DEFAULT 0, 
        last_login_date TEXT,
        profile_views INTEGER DEFAULT 0,
        mood TEXT DEFAULT '✨ Yeni',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0
    )""")

    # POSTS: Alıntı (quote_id), Yanıt (reply_to_id) ve Fısıltı (is_whisper) eklendi
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT,
        content TEXT,
        created_at TEXT,
        likes_count INTEGER DEFAULT 0,
        retweets_count INTEGER DEFAULT 0,
        replies_count INTEGER DEFAULT 0,
        views_count INTEGER DEFAULT 0,
        quote_id INTEGER,
        reply_to_id INTEGER,
        is_whisper INTEGER DEFAULT 0,
        FOREIGN KEY(quote_id) REFERENCES posts(id),
        FOREIGN KEY(reply_to_id) REFERENCES posts(id)
    )""")

    # MESSAGES: Kendini imha eden mesajlar (expires_at) ve okundu bilgisi güncellendi
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        recipient TEXT,
        content TEXT,
        is_read INTEGER DEFAULT 0,
        is_snap INTEGER DEFAULT 0,
        expires_at TEXT,
        created_at TEXT
    )""")

    # Diğer Temel Tablolar
    c.execute("""CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT, views_count INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(follower, followed))""")
    c.execute("""CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS retweets (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, post_id INTEGER, is_read INTEGER DEFAULT 0, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE, count INTEGER DEFAULT 1)""")

    # Admin oluşturma
    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("""INSERT INTO users (username, password, bio, is_verified, mood, avatar_color) VALUES (?, ?, ?, 1, '👑 Kurucu', '#ff6b6b')""",
                 (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu"))

    conn.commit()
    conn.close()

init_db()

@app.context_processor
def inject_global_data():
    if "username" in session:
        conn = get_db()
        user = session["username"]
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET last_seen = ? WHERE username = ?", (time_str, user))

        unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        new_users_list = conn.execute("SELECT username, is_verified FROM users WHERE username != ? AND is_blocked = 0 ORDER BY created_at DESC LIMIT 10", (user,)).fetchall()
        top_users = conn.execute("""SELECT u.username, u.is_verified, u.mood, (SELECT COUNT(*) FROM follows WHERE followed = u.username) as followers FROM users u WHERE u.username != ? AND u.is_blocked = 0 ORDER BY followers DESC LIMIT 5""", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        user_data = conn.execute("SELECT is_verified, ghost_mode FROM users WHERE username = ?", (user,)).fetchone()
        
        conn.commit()
        conn.close()
        
        return dict(
            current_user=user,
            is_verified=user_data['is_verified'] if user_data else 0,
            ghost_mode=user_data['ghost_mode'] if user_data else 0,
            unread_notifs=unread,
            new_users=new_users_list,
            top_users=top_users,
            trends=trends,
            is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

# ============ MAIN PAGES ============
# Not: HTML render işlemleri için backend'i hazırladık. Arayüz kısmında sayfa içerikleri doldurulacak.

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    # Ana akışta Fısıltı gönderilerini sadece takipleşenlere göster
    return render_template("index.html", page="home")

@app.route("/<path:page>")
def catch_all(page):
    if not session.get("username"): return redirect(url_for("home"))
    valid_pages = ['explore', 'bookmarks', 'messages', 'notifications', 'settings', 'search']
    if page in valid_pages: return render_template("index.html", page=page)
    if page.startswith("profile/"): return render_template("index.html", page="profile", profile_username=page.split("/")[1])
    return redirect(url_for("home"))

# ============ API ENDPOINTS ============

@app.route("/api/feed")
def get_feed():
    username = session.get("username")
    if not username: return jsonify({"error": "Auth"}), 401
    conn = get_db()
    
    # Karmaşık Akış Algoritması: Fısıltıları filtrele, Alıntıları dahil et
    query = """
        SELECT p.*, u.is_verified, u.mood, u.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM retweets WHERE post_id = p.id) as retweets_count,
               (SELECT content FROM posts WHERE id = p.quote_id) as quote_content,
               (SELECT author FROM posts WHERE id = p.quote_id) as quote_author
        FROM posts p 
        JOIN users u ON p.author = u.username 
        WHERE p.is_whisper = 0 OR 
              (p.is_whisper = 1 AND (p.author = ? OR 
              EXISTS (SELECT 1 FROM follows f1 JOIN follows f2 ON f1.follower = f2.followed AND f1.followed = f2.follower WHERE f1.follower = ? AND f1.followed = p.author)))
        ORDER BY p.id DESC LIMIT 50
    """
    posts = conn.execute(query, (username, username)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in posts])

@app.route("/api/post", methods=["POST"])
def create_post():
    content = request.form.get("content", "").strip()
    is_whisper = int(request.form.get("is_whisper", 0))
    quote_id = request.form.get("quote_id")
    reply_to_id = request.form.get("reply_to_id")
    username = session.get("username")

    if content and len(content) <= 500 and username:
        conn = get_db()
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn.execute("INSERT INTO posts (author, content, created_at, is_whisper, quote_id, reply_to_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, content, t, is_whisper, quote_id, reply_to_id))
        conn.execute("UPDATE users SET posts_count = posts_count + 1 WHERE username = ?", (username,))
        
        # Etiketler (Hashtags)
        for tag in re.findall(r"#(\w+)", content):
            conn.execute("INSERT OR IGNORE INTO hashtags (tag) VALUES (?)", (tag,))
            conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
            
        # Bildirim (Eğer birine yanıt veriliyorsa)
        if reply_to_id:
            parent_author = conn.execute("SELECT author FROM posts WHERE id=?", (reply_to_id,)).fetchone()
            if parent_author and parent_author['author'] != username:
                conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'reply', ?)", (parent_author['author'], username, t))
                
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    me = session.get("username")
    if not me: return jsonify({"error": "Auth"}), 401
    conn = get_db()
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mesaj Gönderme
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        is_snap = int(request.form.get("is_snap", 0))
        if content:
            expires = None
            if is_snap:
                expires = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (me, partner, content, t, is_snap, expires))
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'message', ?)", (partner, me, t))
            conn.commit()

    # Hayalet mod kapalıysa okundu (Mavi Tık) yap
    ghost_mode = conn.execute("SELECT ghost_mode FROM users WHERE username = ?", (me,)).fetchone()['ghost_mode']
    if not ghost_mode:
        conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
        conn.commit()

    # Süresi dolan (Snap) mesajları temizle
    conn.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
    conn.commit()

    # Mesajları Çek
    msgs = conn.execute("""
        SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC
    """, (me, partner, partner, me)).fetchall()

    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/action/<action>/<int:post_id>", methods=["POST"])
def post_action(action, post_id):
    username = session.get("username")
    if not username: return jsonify({"success": False})
    conn = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "like":
        try:
            conn.execute("INSERT INTO likes (user, post_id, created_at) VALUES (?, ?, ?)", (username, post_id, now))
            conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
            if post and post['author'] != username:
                conn.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, 'like', ?, ?)", (post['author'], username, post_id, now))
            conn.commit()
        except:
            conn.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            conn.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            conn.commit()
            
    elif action == "delete":
        post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post and (post['author'] == username or session.get("username") == ADMIN_USERNAME):
            conn.execute("DELETE FROM posts WHERE id = ? OR quote_id = ? OR reply_to_id = ?", (post_id, post_id, post_id))
            conn.commit()

    conn.close()
    return jsonify({"success": True})

# ============ AUTH ============
@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    if len(u) < 3 or len(p) < 4: return redirect(url_for("home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p)))
        conn.commit()
        session["username"] = u
    except: pass
    finally: conn.close()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    conn = get_db()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p):
        session["username"] = u
        conn.execute("UPDATE users SET last_login_date = ? WHERE username = ?", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), u))
        conn.commit()
    conn.close()
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    username = session.get("username")
    if not username: return jsonify({"success": False})
    bio = request.form.get("bio", "").strip()[:150]
    mood = request.form.get("mood", "").strip()[:30]
    avatar_color = request.form.get("avatar_color", "#1d9bf0")
    ghost_mode = int(request.form.get("ghost_mode", 0))

    conn = get_db()
    conn.execute("UPDATE users SET bio = ?, mood = ?, avatar_color = ?, ghost_mode = ? WHERE username = ?", (bio, mood, avatar_color, ghost_mode, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
