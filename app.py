from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-kaos-mode-2026"

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
    # USERS tablosuna muted_until, muted_by ve last_mute_used eklendi
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT, bio TEXT DEFAULT 'Mekan''da yeni!',
        avatar_color TEXT DEFAULT '#1d9bf0', last_seen TEXT, is_verified INTEGER DEFAULT 0,
        ghost_mode INTEGER DEFAULT 0, muted_until TEXT, muted_by TEXT, last_mute_used TEXT,
        last_login_date TEXT, profile_views INTEGER DEFAULT 0, mood TEXT DEFAULT '✨ Yeni',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0, posts_count INTEGER DEFAULT 0, is_blocked INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT,
        likes_count INTEGER DEFAULT 0, retweets_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0,
        quote_id INTEGER, reply_to_id INTEGER, is_whisper INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT,
        is_read INTEGER DEFAULT 0, is_snap INTEGER DEFAULT 0, expires_at TEXT, created_at TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS retweets (user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, post_id INTEGER, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT UNIQUE, count INTEGER DEFAULT 1)")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio, is_verified, mood, avatar_color) VALUES (?, ?, ?, 1, '👑 Kurucu', '#ff6b6b')",
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
        new_users = conn.execute("SELECT username, is_verified, avatar_color FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 10", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        udata = conn.execute("SELECT is_verified, ghost_mode FROM users WHERE username = ?", (user,)).fetchone()
        conn.commit()
        conn.close()
        return dict(current_user=user, is_verified=udata['is_verified'] if udata else 0, ghost_mode=udata['ghost_mode'] if udata else 0, unread_notifs=unread, new_users=new_users, trends=trends, is_admin=(user==ADMIN_USERNAME))
    return dict(current_user=None)

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    return render_template("index.html", page="home")

@app.route("/<path:page>")
def catch_all(page):
    if not session.get("username"): return redirect(url_for("home"))
    valid_pages = ['explore', 'messages', 'notifications', 'settings', 'search']
    if page in valid_pages: return render_template("index.html", page=page)
    
    if page.startswith("profile/"):
        target = page.split("/")[1]
        conn = get_db()
        profile_user = conn.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
        if not profile_user: return redirect(url_for("home"))
        f_count = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
        is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], target)).fetchone() is not None
        
        # KAOS ÖZELLİĞİ: En Son Kime DM Attı?
        last_dm = conn.execute("SELECT recipient FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1", (target,)).fetchone()
        last_dm_to = last_dm['recipient'] if last_dm else "Kimseyle konuşmamış"
        
        conn.close()
        return render_template("index.html", page="profile", profile_user=profile_user, followers=f_count, is_following=is_following, last_dm_to=last_dm_to)
    return redirect(url_for("home"))

@app.route("/api/feed")
def get_feed():
    username = session.get("username")
    if not username: return jsonify([])
    conn = get_db()
    query = """
        SELECT p.*, u.is_verified, u.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM retweets WHERE post_id = p.id) as retweets_count,
               (SELECT content FROM posts WHERE id = p.quote_id) as quote_content,
               (SELECT author FROM posts WHERE id = p.quote_id) as quote_author
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
    username = session.get("username")
    
    if content and len(content) <= 500 and username:
        conn = get_db()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # SUSTURUCU KONTROLÜ
        user_data = conn.execute("SELECT muted_until, muted_by FROM users WHERE username=?", (username,)).fetchone()
        if user_data['muted_until'] and user_data['muted_until'] > now_str:
            kalan = user_data['muted_until'][11:16]
            conn.close()
            return jsonify({"success": False, "error": f"{user_data['muted_by']} seni susturdu! (Bitiş: {kalan})"})

        conn.execute("INSERT INTO posts (author, content, created_at, is_whisper) VALUES (?, ?, ?, ?)", (username, content, now_str, is_whisper))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Boş gönderi!"})

@app.route("/api/mute/<target>", methods=["POST"])
def apply_mute(target):
    me = session.get("username")
    if not me or me == target: return jsonify({"success": False})
    
    conn = get_db()
    my_data = conn.execute("SELECT last_mute_used FROM users WHERE username=?", (me,)).fetchone()
    now = datetime.datetime.now()
    
    # Günde 1 kez susturma hakkı
    if my_data['last_mute_used'] and my_data['last_mute_used'][:10] == now.strftime("%Y-%m-%d"):
        conn.close()
        return jsonify({"success": False, "msg": "Bugünlük mermi bitti! (Günde 1 hak)"})
        
    mute_until = (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE users SET muted_until=?, muted_by=? WHERE username=?", (mute_until, me, target))
    conn.execute("UPDATE users SET last_mute_used=? WHERE username=?", (now.strftime("%Y-%m-%d %H:%M:%S"), me))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "msg": f"{target} 10 dakika susturuldu 🤫"})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    me = session.get("username")
    if not me: return jsonify([])
    conn = get_db()
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        is_snap = int(request.form.get("is_snap", 0))
        if content:
            expires = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S") if is_snap else None
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) VALUES (?, ?, ?, ?, ?, ?)", (me, partner, content, t, is_snap, expires))
            conn.commit()

    ghost_mode = conn.execute("SELECT ghost_mode FROM users WHERE username = ?", (me,)).fetchone()['ghost_mode']
    if not ghost_mode:
        conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
        conn.commit()

    conn.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
    conn.commit()

    msgs = conn.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/action/<action>/<int:post_id>", methods=["POST"])
def post_action(action, post_id):
    username = session.get("username")
    if not username: return jsonify({"success": False})
    conn = get_db()
    if action == "like":
        try:
            conn.execute("INSERT INTO likes (user, post_id) VALUES (?, ?)", (username, post_id))
            conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            conn.commit()
        except:
            conn.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            conn.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            conn.commit()
    elif action == "delete":
        conn.execute("DELETE FROM posts WHERE id = ? AND author = ?", (post_id, username))
        conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p)))
        conn.commit()
        session["username"] = u
    except: pass
    conn.close()
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    conn = get_db()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p): session["username"] = u
    conn.close()
    return redirect(url_for("home"))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    username = session.get("username")
    if not username: return jsonify({"success": False})
    bio = request.form.get("bio", "").strip()[:150]
    color = request.form.get("avatar_color", "#1d9bf0")
    ghost = int(request.form.get("ghost_mode", 0))
    conn = get_db()
    conn.execute("UPDATE users SET bio=?, avatar_color=?, ghost_mode=? WHERE username=?", (bio, color, ghost, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
