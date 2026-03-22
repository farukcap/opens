import os, sqlite3, datetime, re
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v8-ultimate-safe-mode"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

ADMIN_USERNAME = "faruk"
ADMIN_PASSWORD = "faruk4848"
DATABASE = "mekan.db"

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=20)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;") 
        g.db.execute("PRAGMA journal_mode = WAL;") 
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None: db.close()

def init_db():
    conn = sqlite3.connect(DATABASE, timeout=20)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    c.execute("PRAGMA journal_mode = WAL;")

    # Temel Tablolar (Eğer yoksa oluşturur, varsa dokunmaz)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT NOT NULL, bio TEXT DEFAULT 'Ferah bir gün!',
        avatar_color TEXT DEFAULT '#5da399', last_seen TEXT, is_verified INTEGER DEFAULT 0,
        is_private INTEGER DEFAULT 0, ghost_mode INTEGER DEFAULT 0, muted_until TEXT,
        muted_by TEXT, last_mute_used TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, 
        mekan_coin INTEGER DEFAULT 1000, trust_score INTEGER DEFAULT 100, night_lock INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT NOT NULL, content TEXT NOT NULL,
        created_at TEXT NOT NULL, likes_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0, 
        is_whisper INTEGER DEFAULT 0, location_tag TEXT, burn_votes INTEGER DEFAULT 0, 
        is_offline_vault INTEGER DEFAULT 0, FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, recipient TEXT NOT NULL,
        content TEXT, is_read INTEGER DEFAULT 0, read_at TEXT, is_snap INTEGER DEFAULT 0,
        expires_at TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY(sender) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(recipient) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT UNIQUE, count INTEGER DEFAULT 1, last_used TEXT)")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio, is_verified, avatar_color, mekan_coin) VALUES (?, ?, ?, 2, '#1d9bf0', 999999)",
                 (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Sistemin Yaratıcısı"))
    
    conn.commit()
    conn.close()

def upgrade_db():
    """ MEVCUT VERİLERİ SİLMEDEN YENİ ÖZELLİKLERİ EKLER """
    conn = sqlite3.connect(DATABASE, timeout=20)
    c = conn.cursor()
    try: c.execute("ALTER TABLE posts ADD COLUMN reply_to_id INTEGER;")
    except: pass
    try: c.execute("ALTER TABLE messages ADD COLUMN reaction TEXT;")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN followers_count INTEGER DEFAULT 0;")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN following_count INTEGER DEFAULT 0;")
    except: pass
    conn.commit()
    conn.close()

init_db()
upgrade_db() # Veritabanını güvenle günceller

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session: return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") != ADMIN_USERNAME: return jsonify({"success": False, "msg": "Sadece Faruk girebilir."})
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_data():
    if "username" in session:
        db = get_db()
        user = session["username"]
        udata = db.execute("SELECT * FROM users WHERE username = ?", (user,)).fetchone()
        
        if not udata:
            session.clear()
            return dict(current_user=None)

        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE users SET last_seen = ? WHERE username = ?", (t, user))
        
        # OKUNMAMIŞ DM BİLDİRİM SAYISI BURADA HESAPLANIYOR
        unread_dms = db.execute("SELECT COUNT(*) as c FROM messages WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        
        trends = db.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        new_users = db.execute("SELECT username, avatar_color FROM users ORDER BY created_at DESC LIMIT 10").fetchall()
        db.commit()
        
        return dict(
            current_user=user, current_user_color=udata['avatar_color'], is_verified=udata['is_verified'], 
            ghost_mode=udata['ghost_mode'], is_private=udata['is_private'], mekan_coin=udata['mekan_coin'],
            trust_score=udata['trust_score'], trends=trends, new_users=new_users, unread_dms=unread_dms, is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    return render_template("index.html", page="home")

@app.route("/<path:page>")
def catch_all(page):
    if not session.get("username"): return redirect(url_for("home"))
    user = session["username"]
    db = get_db()
    
    if page == 'messages':
        chats = db.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ?", (user, user, user)).fetchall()
        chat_list = []
        for c in chats:
            partner = c['partner']
            last_msg = db.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id DESC LIMIT 1", (user, partner, partner, user)).fetchone()
            p_info = db.execute("SELECT avatar_color, is_verified FROM users WHERE username=?", (partner,)).fetchone()
            if p_info and last_msg:
                chat_list.append({
                    "partner": partner, "avatar_color": p_info["avatar_color"], "is_verified": p_info["is_verified"],
                    "content": "💣 [Snap]" if last_msg["is_snap"] else last_msg["content"],
                    "time": last_msg["created_at"][11:16],
                    "unread": 1 if last_msg["recipient"] == user and last_msg["is_read"] == 0 else 0
                })
        chat_list.sort(key=lambda x: x['time'], reverse=True)
        return render_template("index.html", page="messages", chat_list=chat_list)
        
    if page.startswith("profile/"):
        target = page.split("/")[1]
        profile_user = db.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
        if not profile_user: return redirect(url_for("home"))
        
        f_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
        is_following = db.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (user, target)).fetchone() is not None
        
        last_dm = db.execute("SELECT recipient FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1", (target,)).fetchone()
        last_dm_to = last_dm['recipient'] if last_dm else "Kimseyle"
        
        return render_template("index.html", page="profile", profile_user=profile_user, followers=f_count, is_following=is_following, last_dm_to=last_dm_to)
        
    return redirect(url_for("home"))

@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    if len(u) > 2 and len(p) > 3:
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p)))
            db.commit()
            session["username"] = u
        except sqlite3.IntegrityError:
            pass
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    db = get_db()
    user = db.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p): session["username"] = u
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/api/search")
@login_required
def search_users():
    q = request.args.get('q', '').strip().lower()
    if not q: return jsonify([])
    db = get_db()
    users = db.execute("SELECT username, avatar_color, is_verified FROM users WHERE username LIKE ? LIMIT 10", (f"%{q}%",)).fetchall()
    return jsonify([dict(u) for u in users])

@app.route("/api/feed")
def get_feed():
    u = session.get("username")
    if not u: return jsonify([])
    db = get_db()
    posts = db.execute("""
        SELECT p.*, us.is_verified, us.avatar_color,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id AND user = ?) as is_liked_by_me,
               (SELECT author FROM posts WHERE id = p.reply_to_id) as reply_target
        FROM posts p JOIN users us ON p.author = us.username 
        ORDER BY p.id DESC LIMIT 50
    """, (u,)).fetchall()
    return jsonify([dict(p) for p in posts])

@app.route("/api/post", methods=["POST"])
@login_required
def create_post():
    c = request.form.get("content", "").strip()
    is_w = int(request.form.get("is_whisper", 0))
    loc = request.form.get("location_tag", "").strip()
    reply_id = request.form.get("reply_to_id")
    if reply_id == "": reply_id = None
    
    u = session.get("username")
    db = get_db()
    
    now = datetime.datetime.now()
    if 2 <= now.hour < 6:
        user_data = db.execute("SELECT night_lock FROM users WHERE username=?", (u,)).fetchone()
        if user_data and user_data['night_lock']: return jsonify({"success": False, "error": "Gece kilidi aktif! 06:00'a kadar gönderi atılamaz."})

    if c:
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        tags = re.findall(r"#(\w+)", c)
        for t in tags: db.execute("INSERT INTO hashtags (tag, count, last_used) VALUES (?, 1, ?) ON CONFLICT(tag) DO UPDATE SET count=count+1, last_used=?", (t, now_str, now_str))
        
        db.execute("INSERT INTO posts (author, content, created_at, is_whisper, location_tag, reply_to_id) VALUES (?, ?, ?, ?, ?, ?)", (u, c, now_str, is_w, loc, reply_id))
        
        if reply_id:
            db.execute("UPDATE posts SET replies_count = replies_count + 1 WHERE id = ?", (reply_id,))
            
        db.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Boş içerik!"})

@app.route("/api/action/<action>/<int:post_id>", methods=["POST"])
@login_required
def post_action(action, post_id):
    u = session.get("username")
    db = get_db()
    if action == "like":
        try:
            db.execute("INSERT INTO likes (user, post_id) VALUES (?, ?)", (u, post_id))
        except sqlite3.IntegrityError:
            db.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (u, post_id))
        db.commit()
    elif action == "burn":
        db.execute("UPDATE posts SET burn_votes = burn_votes + 1 WHERE id = ?", (post_id,))
        p = db.execute("SELECT burn_votes FROM posts WHERE id = ?", (post_id,)).fetchone()
        if p and p['burn_votes'] >= 3: db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        db.commit()
        return jsonify({"success": True, "msg": "Ateşe verildi! 🔥"})
    return jsonify({"success": True})

@app.route("/api/follow/<target>", methods=["POST"])
@login_required
def follow_user(target):
    me = session.get("username")
    if me == target: return jsonify({"success": False, "msg": "Kendini takip edemezsin!"})
    db = get_db()
    is_following = db.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (me, target)).fetchone()
    
    if is_following:
        db.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (me, target))
        msg = "Takipten çıkıldı."
    else:
        db.execute("INSERT INTO follows (follower, followed) VALUES (?, ?)", (me, target))
        msg = "Takip ediliyor."
    db.commit()
    return jsonify({"success": True, "msg": msg})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
@login_required
def chat_api(partner):
    me = session.get("username")
    db = get_db()
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ghost_mode_active = db.execute("SELECT ghost_mode FROM users WHERE username = ?", (me,)).fetchone()['ghost_mode']

    if request.method == "POST":
        c = request.form.get("content", "").strip()
        snap = int(request.form.get("is_snap", 0))
        if c:
            exp = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S") if snap else None
            db.execute("INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) VALUES (?, ?, ?, ?, ?, ?)", (me, partner, c, t, snap, exp))
            db.commit()

    if not ghost_mode_active:
        db.execute("UPDATE messages SET is_read = 1, read_at = ? WHERE sender = ? AND recipient = ? AND is_read = 0", (t, partner, me))
    
    db.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
    db.commit()

    msgs = db.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/react_msg/<int:msg_id>", methods=["POST"])
@login_required
def react_msg(msg_id):
    db = get_db()
    msg = db.execute("SELECT reaction FROM messages WHERE id = ?", (msg_id,)).fetchone()
    if msg:
        new_reaction = None if msg['reaction'] else '❤️'
        db.execute("UPDATE messages SET reaction = ? WHERE id = ?", (new_reaction, msg_id))
        db.commit()
    return jsonify({"success": True})

@app.route("/api/update_profile", methods=["POST"])
@login_required
def update_profile():
    u = session.get("username")
    b = request.form.get("bio", "").strip()[:150]
    c = request.form.get("avatar_color", "#5da399")
    g = int(request.form.get("ghost_mode", 0))
    p = int(request.form.get("is_private", 0))
    n = int(request.form.get("night_lock", 0))
    db = get_db()
    db.execute("UPDATE users SET bio=?, avatar_color=?, ghost_mode=?, is_private=?, night_lock=? WHERE username=?", (b, c, g, p, n, u))
    db.commit()
    return jsonify({"success": True})

# ⚡ KUSURSUZ GOD MODE
@app.route("/api/admin/god_mode", methods=["POST"])
@login_required
@admin_required
def god_mode_actions():
    action = request.form.get("action")
    target_user = request.form.get("target_user", "").strip().lower()
    db = get_db()
    
    if action == "add_coin":
        db.execute("UPDATE users SET mekan_coin = mekan_coin + 10000 WHERE username = ?", (target_user,))
    elif action == "verify_user":
        db.execute("UPDATE users SET is_verified = 1 WHERE username = ?", (target_user,))
    elif action == "ban_user":
        if target_user == ADMIN_USERNAME: return jsonify({"success": False, "msg": "Kendini silemezsin!"})
        db.execute("DELETE FROM users WHERE username = ?", (target_user,))
    elif action == "delete_post":
        post_id = request.form.get("post_id")
        db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    
    db.commit()
    return jsonify({"success": True, "msg": "Yüce komut yerine getirildi! ⚡"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
