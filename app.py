from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v6-flawless-key-2026"

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

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT, bio TEXT DEFAULT 'Mekan''da yeni!',
        avatar_color TEXT DEFAULT '#1d9bf0', last_seen TEXT, is_verified INTEGER DEFAULT 0,
        ghost_mode INTEGER DEFAULT 0, last_login_date TEXT, profile_views INTEGER DEFAULT 0,
        mood TEXT DEFAULT '✨ Yeni', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        followers_count INTEGER DEFAULT 0, following_count INTEGER DEFAULT 0, posts_count INTEGER DEFAULT 0, is_blocked INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT,
        likes_count INTEGER DEFAULT 0, retweets_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0,
        burns_count INTEGER DEFAULT 0, views_count INTEGER DEFAULT 0, quote_id INTEGER, reply_to_id INTEGER, is_whisper INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT,
        is_read INTEGER DEFAULT 0, is_snap INTEGER DEFAULT 0, expires_at TEXT, created_at TEXT
    )""")

    # Kolektif İdam tablosu
    c.execute("""CREATE TABLE IF NOT EXISTS burns (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT, views_count INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(follower, followed))""")
    c.execute("""CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS retweets (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, post_id INTEGER, is_read INTEGER DEFAULT 0, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE, count INTEGER DEFAULT 1)""")

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
        new_users_list = conn.execute("SELECT username, is_verified FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 5", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        user_data = conn.execute("SELECT is_verified, ghost_mode FROM users WHERE username = ?", (user,)).fetchone()
        
        # DM listesi (Sol panel için)
        chats = conn.execute("""
            SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner 
            FROM messages WHERE sender = ? OR recipient = ? ORDER BY id DESC LIMIT 10
        """, (user, user, user)).fetchall()
        
        conn.commit()
        conn.close()
        
        return dict(
            current_user=user, is_verified=user_data['is_verified'] if user_data else 0,
            ghost_mode=user_data['ghost_mode'] if user_data else 0, unread_notifs=unread,
            new_users=new_users_list, trends=trends, chat_list=chats, is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    return render_template("index.html", page="home")

@app.route("/<path:page>")
def catch_all(page):
    if not session.get("username"): return redirect(url_for("home"))
    valid_pages = ['explore', 'bookmarks', 'messages', 'notifications', 'settings', 'search']
    if page in valid_pages: 
        if page == 'notifications':
            conn = get_db()
            notifs = conn.execute("SELECT n.*, u.avatar_color FROM notifications n JOIN users u ON n.sender = u.username WHERE n.recipient = ? ORDER BY n.id DESC LIMIT 50", (session["username"],)).fetchall()
            conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient = ?", (session["username"],))
            conn.commit()
            conn.close()
            return render_template("index.html", page=page, notifs=notifs)
        return render_template("index.html", page=page)
    if page.startswith("profile/"): 
        target = page.split("/")[1]
        conn = get_db()
        prof = conn.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
        if not prof:
            conn.close()
            return redirect(url_for("home"))
        followers = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
        is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], target)).fetchone() is not None
        conn.close()
        return render_template("index.html", page="profile", profile_user=prof, followers=followers, is_following=is_following)
    return redirect(url_for("home"))

@app.route("/api/feed")
def get_feed():
    username = session.get("username")
    if not username: return jsonify({"error": "Auth"}), 401
    conn = get_db()
    
    query = """
        SELECT p.*, u.is_verified, u.mood, u.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM retweets WHERE post_id = p.id) as retweets_count,
               (SELECT content FROM posts WHERE id = p.quote_id) as quote_content,
               (SELECT author FROM posts WHERE id = p.quote_id) as quote_author,
               (SELECT COUNT(*) FROM burns WHERE post_id = p.id) as current_burns
        FROM posts p JOIN users u ON p.author = u.username 
        WHERE p.is_whisper = 0 OR (p.is_whisper = 1 AND (p.author = ? OR EXISTS (SELECT 1 FROM follows f1 JOIN follows f2 ON f1.follower = f2.followed AND f1.followed = f2.follower WHERE f1.follower = ? AND f1.followed = p.author)))
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
        conn.execute("INSERT INTO posts (author, content, created_at, is_whisper, quote_id, reply_to_id) VALUES (?, ?, ?, ?, ?, ?)", (username, content, t, is_whisper, quote_id, reply_to_id))
        conn.execute("UPDATE users SET posts_count = posts_count + 1 WHERE username = ?", (username,))
        
        for tag in re.findall(r"#(\w+)", content):
            conn.execute("INSERT OR IGNORE INTO hashtags (tag) VALUES (?)", (tag,))
            conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
            
        if reply_to_id:
            parent = conn.execute("SELECT author FROM posts WHERE id=?", (reply_to_id,)).fetchone()
            if parent and parent['author'] != username:
                conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'reply', ?)", (parent['author'], username, t))
                conn.execute("UPDATE posts SET replies_count = replies_count + 1 WHERE id = ?", (reply_to_id,))
                
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

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        is_snap = int(request.form.get("is_snap", 0))
        if content:
            expires = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S") if is_snap else None
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) VALUES (?, ?, ?, ?, ?, ?)", (me, partner, content, t, is_snap, expires))
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'message', ?)", (partner, me, t))
            conn.commit()

    ghost_mode = conn.execute("SELECT ghost_mode FROM users WHERE username = ?", (me,)).fetchone()['ghost_mode']
    if not ghost_
