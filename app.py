from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re, json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v40-final-secret-key-2024"

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
    # Users tablosu
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        bio TEXT DEFAULT 'Mekan''da yeni!',
        avatar_color TEXT DEFAULT '#1d9bf0',
        last_seen TEXT,
        is_verified INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_login_date TEXT,
        profile_views INTEGER DEFAULT 0,
        mood TEXT DEFAULT '✨ Yeni',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0
    )""")

    # Posts tablosu
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT,
        content TEXT,
        created_at TEXT,
        likes_count INTEGER DEFAULT 0,
        retweets_count INTEGER DEFAULT 0,
        replies_count INTEGER DEFAULT 0,
        views_count INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0,
        is_edited INTEGER DEFAULT 0
    )""")

    # Comments/Replies
    c.execute("""CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        author TEXT,
        content TEXT,
        created_at TEXT,
        likes_count INTEGER DEFAULT 0,
        FOREIGN KEY(post_id) REFERENCES posts(id)
    )""")

    # Stories tablosu
    c.execute("""CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT,
        content TEXT,
        created_at TEXT,
        views_count INTEGER DEFAULT 0
    )""")

    # Mesajlar
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        recipient TEXT,
        content TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # Takipçiler
    c.execute("""CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower TEXT,
        followed TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(follower, followed)
    )""")

    # Beğeniler
    c.execute("""CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        post_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user, post_id)
    )""")

    # Comment beğenileri
    c.execute("""CREATE TABLE IF NOT EXISTS comment_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        comment_id INTEGER,
        UNIQUE(user, comment_id)
    )""")

    # Retweets
    c.execute("""CREATE TABLE IF NOT EXISTS retweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        post_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user, post_id)
    )""")

    # Bildirimler
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient TEXT,
        sender TEXT,
        type TEXT,
        post_id INTEGER,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # Hashtags
    c.execute("""CREATE TABLE IF NOT EXISTS hashtags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT UNIQUE,
        count INTEGER DEFAULT 1
    )""")

    # Bookmarks
    c.execute("""CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        post_id INTEGER,
        UNIQUE(user, post_id)
    )""")

    # Post views
    c.execute("""CREATE TABLE IF NOT EXISTS post_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        post_id INTEGER,
        UNIQUE(user, post_id)
    )""")

    # Mute/Block
    c.execute("""CREATE TABLE IF NOT EXISTS blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blocker TEXT,
        blocked TEXT,
        UNIQUE(blocker, blocked)
    )""")

    # Search history
    c.execute("""CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        query TEXT,
        created_at TEXT
    )""")

    # Admin kontrol
    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("""INSERT INTO users 
                    (username, password, bio, is_verified, mood, avatar_color) 
                    VALUES (?, ?, ?, 1, '👑 Kurucu', '#ff6b6b')""",
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
        top_users = conn.execute("""SELECT u.username, u.is_verified, u.mood, 
                                   (SELECT COUNT(*) FROM follows WHERE followed = u.username) as followers 
                                   FROM users u WHERE u.username != ? AND u.is_blocked = 0 
                                   ORDER BY followers DESC LIMIT 5""", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        user_data = conn.execute("SELECT is_verified FROM users WHERE username = ?", (user,)).fetchone()
        
        conn.commit()
        conn.close()
        
        return dict(
            current_user=user,
            is_verified=user_data['is_verified'] if user_data else 0,
            unread_notifs=unread,
            new_users=new_users_list,
            top_users=top_users,
            trends=trends,
            is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

# ============ MAIN PAGES ============

@app.route("/")
def home():
    if not session.get("username"):
        return render_template("index.html")

    conn = get_db()
    posts = conn.execute("""
        SELECT p.*, u.is_verified, u.mood, u.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM retweets WHERE post_id = p.id) as retweets_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as replies_count
        FROM posts p 
        JOIN users u ON p.author = u.username 
        ORDER BY p.id DESC LIMIT 50
    """).fetchall()

    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    stories = conn.execute("""
        SELECT s.*, u.is_verified, u.avatar_color
        FROM stories s 
        JOIN users u ON s.author = u.username 
        WHERE s.created_at > ? AND u.username != ?
        ORDER BY s.id DESC LIMIT 20
    """, (yesterday, session["username"])).fetchall()

    conn.close()
    return render_template("index.html", page="home", posts=posts, stories=stories)

@app.route("/explore")
def explore():
    if not session.get("username"):
        return redirect(url_for("home"))

    conn = get_db()
    posts = conn.execute("""
        SELECT p.*, u.is_verified, u.mood, u.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count
        FROM posts p 
        JOIN users u ON p.author = u.username 
        ORDER BY p.views_count DESC, p.id DESC LIMIT 50
    """).fetchall()

    trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 10").fetchall()
    conn.close()

    return render_template("index.html", page="explore", posts=posts, trends=trends)

@app.route("/bookmarks")
def bookmarks():
    if not session.get("username"):
        return redirect(url_for("home"))

    conn = get_db()
    posts = conn.execute("""
        SELECT p.*, u.is_verified, u.mood, u.avatar_color
        FROM posts p 
        JOIN users u ON p.author = u.username 
        JOIN bookmarks b ON p.id = b.post_id
        WHERE b.user = ?
        ORDER BY p.id DESC
    """, (session["username"],)).fetchall()

    conn.close()
    return render_template("index.html", page="bookmarks", posts=posts)

@app.route("/profile/<username>")
def profile(username):
    if not session.get("username"):
        return redirect(url_for("home"))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if not user:
        conn.close()
        return redirect(url_for("home"))

    if username != session["username"]:
        conn.execute("UPDATE users SET profile_views = profile_views + 1 WHERE username = ?", (username,))
        conn.commit()

    posts = conn.execute("""
        SELECT p.*, u.is_verified, u.avatar_color
        FROM posts p 
        JOIN users u ON p.author = u.username 
        WHERE author = ? 
        ORDER BY p.id DESC
    """, (username,)).fetchall()

    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", 
                               (session["username"], username)).fetchone() is not None
    f_count = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']

    conn.close()
    return render_template("index.html", page="profile", profile_user=user, posts=posts, followers=f_count, is_following=is_following)

@app.route("/messages")
def messages_page():
    if not session.get("username"):
        return redirect(url_for("home"))

    conn = get_db()
    chats = conn.execute("""
        SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner 
        FROM messages 
        WHERE sender = ? OR recipient = ?
        ORDER BY id DESC
    """, (session["username"], session["username"], session["username"])).fetchall()

    conn.close()
    return render_template("index.html", page="messages", chats=chats)

@app.route("/notifications")
def notifications():
    if not session.get("username"):
        return redirect(url_for("home"))

    conn = get_db()
    notifs = conn.execute("""
        SELECT n.*, u.avatar_color, u.is_verified
        FROM notifications n
        JOIN users u ON n.sender = u.username
        WHERE n.recipient = ? 
        ORDER BY n.id DESC LIMIT 50
    """, (session["username"],)).fetchall()

    conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient = ?", (session["username"],))
    conn.commit()
    conn.close()

    return render_template("index.html", page="notifications", notifs=notifs)

@app.route("/settings")
def settings():
    if not session.get("username"):
        return redirect(url_for("home"))
    return render_template("index.html", page="settings")

@app.route("/search")
def search():
    if not session.get("username"):
        return redirect(url_for("home"))

    q = request.args.get("q", "").strip()
    results = {"users": [], "posts": [], "hashtags": []}

    if q:
        conn = get_db()
        # Kullanıcı ara
        results["users"] = conn.execute("""
            SELECT username, is_verified, avatar_color, mood, followers_count
            FROM users 
            WHERE username LIKE ? AND is_blocked = 0
            LIMIT 10
        """, (f"%{q}%",)).fetchall()
        
        # Post ara
        results["posts"] = conn.execute("""
            SELECT p.*, u.is_verified, u.avatar_color
            FROM posts p 
            JOIN users u ON p.author = u.username
            WHERE p.content LIKE ?
            ORDER BY p.id DESC LIMIT 10
        """, (f"%{q}%",)).fetchall()
        
        # Hashtag ara
        results["hashtags"] = conn.execute("""
            SELECT tag, count FROM hashtags 
            WHERE tag LIKE ?
            LIMIT 10
        """, (f"%{q}%",)).fetchall()
        
        conn.execute("INSERT INTO search_history (user, query, created_at) VALUES (?, ?, ?)",
                    (session["username"], q, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    return render_template("index.html", page="search", results=results, query=q)

# ============ API ENDPOINTS ============

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    me = session.get("username")
    if not me:
        return jsonify({"error": "Not authenticated"}), 401

    conn = get_db()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content and len(content) <= 500:
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)",
                        (me, partner, content, t))
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'message', ?)",
                        (partner, me, t))
            conn.commit()

    conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
    conn.commit()

    msgs = conn.execute("""
        SELECT * FROM messages 
        WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) 
        ORDER BY id ASC
    """, (me, partner, partner, me)).fetchall()

    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/post", methods=["POST"])
def create_post():
    content = request.form.get("content", "").strip()
    username = session.get("username")

    if content and len(content) <= 500 and username:
        conn = get_db()
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)",
                    (username, content, t))
        conn.execute("UPDATE users SET posts_count = posts_count + 1 WHERE username = ?", (username,))
        
        for tag in re.findall(r"#(\w+)", content):
            conn.execute("INSERT OR IGNORE INTO hashtags (tag) VALUES (?)", (tag,))
            conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    return jsonify({"success": False})

@app.route("/api/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    content = request.form.get("content", "").strip()
    username = session.get("username")

    if content and len(content) <= 300 and username:
        conn = get_db()
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn.execute("INSERT INTO comments (post_id, author, content, created_at) VALUES (?, ?, ?, ?)",
                    (post_id, username, content, t))
        conn.execute("UPDATE posts SET replies_count = replies_count + 1 WHERE id = ?", (post_id,))
        
        post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post and post['author'] != username:
            conn.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, 'reply', ?, ?)",
                        (post['author'], username, post_id, t))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    return jsonify({"success": False})

@app.route("/api/post/<int:post_id>/comments")
def get_comments(post_id):
    conn = get_db()
    comments = conn.execute("""
        SELECT c.*, u.avatar_color, u.is_verified
        FROM comments c
        JOIN users u ON c.author = u.username
        WHERE c.post_id = ?
        ORDER BY c.id DESC
    """, (post_id,)).fetchall()
    conn.close()
    return jsonify([dict(c) for c in comments])

@app.route("/api/story", methods=["POST"])
def post_story():
    content = request.form.get("content", "").strip()
    username = session.get("username")

    if content and len(content) <= 500 and username:
        conn = get_db()
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO stories (author, content, created_at) VALUES (?, ?, ?)",
                    (username, content, t))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    return jsonify({"success": False})

@app.route("/api/action/<action>/<int:post_id>", methods=["POST"])
def post_action(action, post_id):
    username = session.get("username")
    if not username:
        return jsonify({"success": False})

    conn = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "like":
        try:
            conn.execute("INSERT INTO likes (user, post_id, created_at) VALUES (?, ?, ?)", (username, post_id, now))
            conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
            if post and post['author'] != username:
                conn.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, 'like', ?, ?)",
                            (post['author'], username, post_id, now))
            conn.commit()
        except:
            conn.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            conn.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            conn.commit()

    elif action == "retweet":
        try:
            conn.execute("INSERT INTO retweets (user, post_id, created_at) VALUES (?, ?, ?)", (username, post_id, now))
            conn.execute("UPDATE posts SET retweets_count = retweets_count + 1 WHERE id = ?", (post_id,))
            conn.commit()
        except:
            conn.execute("DELETE FROM retweets WHERE user = ? AND post_id = ?", (username, post_id))
            conn.execute("UPDATE posts SET retweets_count = retweets_count - 1 WHERE id = ?", (post_id,))
            conn.commit()

    elif action == "bookmark":
        try:
            conn.execute("INSERT INTO bookmarks (user, post_id) VALUES (?, ?)", (username, post_id))
            conn.commit()
        except:
            conn.execute("DELETE FROM bookmarks WHERE user = ? AND post_id = ?", (username, post_id))
            conn.commit()

    elif action == "delete":
        post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post and (post['author'] == username or session.get("username") == ADMIN_USERNAME):
            conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()

    elif action == "view":
        try:
            conn.execute("INSERT INTO post_views (user, post_id) VALUES (?, ?)", (username, post_id))
            conn.commit()
        except:
            pass

    conn.close()
    return jsonify({"success": True})

@app.route("/api/follow/<target>", methods=["POST"])
def toggle_follow(target):
    username = session.get("username")
    if not username or username == target:
        return jsonify({"success": False})

    conn = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute("INSERT INTO follows (follower, followed, created_at) VALUES (?, ?, ?)", (username, target, now))
        conn.execute("UPDATE users SET followers_count = followers_count + 1 WHERE username = ?", (target,))
        conn.execute("UPDATE users SET following_count = following_count + 1 WHERE username = ?", (username,))
        conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'follow', ?)", (target, username, now))
        conn.commit()
    except:
        conn.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (username, target))
        conn.execute("UPDATE users SET followers_count = followers_count - 1 WHERE username = ?", (target,))
        conn.execute("UPDATE users SET following_count = following_count - 1 WHERE username = ?", (username,))
        conn.commit()

    conn.close()
    return jsonify({"success": True})

@app.route("/api/user/<username>")
def get_user_info(username):
    conn = get_db()
    user = conn.execute("SELECT username, bio, is_verified, mood, avatar_color, followers_count, posts_count, profile_views FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user:
        return jsonify(dict(user))
    return jsonify({"error": "User not found"}), 404

@app.route("/api/trending")
def get_trending():
    conn = get_db()
    trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 10").fetchall()
    conn.close()
    return jsonify([dict(t) for t in trends])

# ============ AUTH ============

@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()

    if len(u) < 3 or len(p) < 4:
        flash("Kullanıcı adı 3+ karakter, şifre 4+ karakter olmalı!")
        return redirect(url_for("home"))

    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p)))
        conn.commit()
        session["username"] = u
        flash("Hoşgeldiniz!")
    except:
        flash("İsim alınmış!")
    finally:
        conn.close()
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
        flash("Hoşgeldiniz!")
    else:
        flash("Hatalı kullanıcı adı veya şifre!")

    conn.close()
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yaptınız!")
    return redirect(url_for("home"))

@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    username = session.get("username")
    if not username:
        return jsonify({"success": False})

    bio = request.form.get("bio", "").strip()[:150]
    mood = request.form.get("mood", "").strip()[:30]
    avatar_color = request.form.get("avatar_color", "#1d9bf0")

    conn = get_db()
    conn.execute("UPDATE users SET bio = ?, mood = ?, avatar_color = ? WHERE username = ?", (bio, mood, avatar_color, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
