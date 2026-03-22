import os, sqlite3, datetime, re, random
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# 1. UYGULAMA YAPILANDIRMASI VE ÇEKİRDEK
# ==========================================

app = Flask(__name__)
app.secret_key = "mekan-v7-ultimate-god-mode-2026-x"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Maksimum 16MB dosya yükleme

ADMIN_USERNAME = "faruk"
ADMIN_PASSWORD = "faruk4848"
DATABASE = "mekan_v7.db"

# ==========================================
# 2. VERİTABANI BAĞLANTISI VE MİMARİSİ
# ==========================================

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
    if db is not None:
        db.close()

def init_db():
    """
    Kritik Düzeltme: Tabloların uygulama başlarken doğrudan oluşturulması.
    """
    conn = sqlite3.connect(DATABASE, timeout=20)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    c.execute("PRAGMA journal_mode = WAL;")

    # 1. KULLANICILAR (USERS)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        bio TEXT DEFAULT 'Mekan''da ferah bir gün!',
        avatar_color TEXT DEFAULT '#5da399',
        profile_banner TEXT,
        profile_music TEXT,
        last_seen TEXT,
        is_verified INTEGER DEFAULT 0,
        is_private INTEGER DEFAULT 0,
        ghost_mode INTEGER DEFAULT 0,
        muted_until TEXT,
        muted_by TEXT,
        last_mute_used TEXT,
        last_login_date TEXT,
        profile_views INTEGER DEFAULT 0,
        mood TEXT DEFAULT '🌸 Ferah',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        mekan_coin INTEGER DEFAULT 1000,
        trust_score INTEGER DEFAULT 100,
        streak_days INTEGER DEFAULT 0,
        night_lock INTEGER DEFAULT 0
    )""")

    # 2. GÖNDERİLER (POSTS)
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        content TEXT NOT NULL,
        media_url TEXT,
        created_at TEXT NOT NULL,
        likes_count INTEGER DEFAULT 0,
        retweets_count INTEGER DEFAULT 0,
        replies_count INTEGER DEFAULT 0,
        quote_id INTEGER,
        reply_to_id INTEGER,
        is_whisper INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0,
        is_nsfw INTEGER DEFAULT 0,
        location_tag TEXT, 
        poll_id INTEGER,
        burn_votes INTEGER DEFAULT 0,
        is_offline_vault INTEGER DEFAULT 0,
        duel_status INTEGER DEFAULT 0,
        FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE
    )""")

    # 3. MESAJLAR (MESSAGES)
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        recipient TEXT NOT NULL,
        content TEXT,
        media_url TEXT,
        is_read INTEGER DEFAULT 0,
        read_at TEXT,
        is_snap INTEGER DEFAULT 0,
        expires_at TEXT,
        reaction TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(sender) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(recipient) REFERENCES users(username) ON DELETE CASCADE
    )""")

    # 4. HİKAYELER
    c.execute("""CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        content TEXT,
        media_url TEXT,
        created_at TEXT NOT NULL,
        views_count INTEGER DEFAULT 0,
        is_highlight INTEGER DEFAULT 0
    )""")

    # 5. İLİŞKİLER VE LİSTELER
    c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, followed TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS follow_requests (sender TEXT, receiver TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(sender, receiver))")
    c.execute("CREATE TABLE IF NOT EXISTS blocks (blocker TEXT, blocked TEXT, UNIQUE(blocker, blocked))")

    # 6. ETKİLEŞİMLER
    c.execute("CREATE TABLE IF NOT EXISTS likes (user TEXT, post_id INTEGER, reaction_type TEXT DEFAULT 'heart', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS retweets (user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT UNIQUE, count INTEGER DEFAULT 1, last_used TEXT)")
    
    # 7. BİLDİRİMLER
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient TEXT NOT NULL,
        sender TEXT,
        type TEXT NOT NULL,
        post_id INTEGER,
        content TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )""")

    # 8. ANONİM İTİRAFLAR
    c.execute("""CREATE TABLE IF NOT EXISTS confessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_user TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_public INTEGER DEFAULT 0
    )""")

    # Admin Hesabı Kontrolü
    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("""INSERT INTO users (username, password, bio, is_verified, mood, avatar_color, mekan_coin) 
                      VALUES (?, ?, ?, 2, '👑 Kurucu', '#1d9bf0', 999999)""",
                 (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Sistemin Yaratıcısı"))
    
    conn.commit()
    conn.close()

# UYGULAMA BAŞLARKEN VERİTABANINI HAZIRLA (Hayat kurtaran satır)
init_db()

# ==========================================
# 3. YARDIMCI FONKSİYONLAR VE DECORATOR'LAR
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def check_night_lock(username, db):
    """ Gece Sarhoş/Uyku Kilidi Kontrolü (02:00 - 06:00 arası) """
    now = datetime.datetime.now()
    if 2 <= now.hour < 6:
        user = db.execute("SELECT night_lock FROM users WHERE username=?", (username,)).fetchone()
        if user and user['night_lock']:
            return True, "🌙 Gece kilidi aktif! Saat 06:00'a kadar gönderi atamazsın."
    return False, ""

def calculate_trending(db):
    """ Gelişmiş Gündem Algoritması """
    trends = db.execute("""
        SELECT tag, count 
        FROM hashtags 
        WHERE datetime(last_used) >= datetime('now', '-24 hours')
        ORDER BY count DESC LIMIT 5
    """).fetchall()
    return trends

# ==========================================
# 4. BAĞLAM VE ANA SAYFA YÖNLENDİRMELERİ
# ==========================================

@app.context_processor
def inject_global_data():
    if "username" in session:
        db = get_db()
        user = session["username"]
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db.execute("UPDATE users SET last_seen = ? WHERE username = ?", (time_str, user))
        
        unread = db.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        new_users = db.execute("SELECT username, is_verified, avatar_color FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 10", (user,)).fetchall()
        trends = calculate_trending(db)
        
        udata = db.execute("SELECT is_verified, ghost_mode, is_private, mekan_coin, night_lock, trust_score, avatar_color FROM users WHERE username = ?", (user,)).fetchone()
        db.commit()
        
        return dict(
            current_user=user, 
            current_user_color=udata['avatar_color'] if udata else '#5da399', # HTML burayı bekliyordu
            is_verified=udata['is_verified'] if udata else 0, 
            ghost_mode=udata['ghost_mode'] if udata else 0, 
            is_private=udata['is_private'] if udata else 0,
            mekan_coin=udata['mekan_coin'] if udata else 0,
            trust_score=udata['trust_score'] if udata else 100, # Güven skoru HTML'e gönderildi
            unread_notifs=unread, 
            new_users=new_users, 
            trends=trends, 
            is_admin=(user==ADMIN_USERNAME)
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
    
    valid_pages = ['explore', 'bookmarks', 'settings', 'search', 'arena', 'wallet']
    if page in valid_pages: 
        return render_template("index.html", page=page)
        
    if page == 'messages':
        return render_template("index.html", page="messages")
        
    if page.startswith("profile/"):
        target = page.split("/")[1]
        profile_user = db.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
        if not profile_user: return redirect(url_for("home"))
            
        f_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
        is_following = db.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (user, target)).fetchone() is not None
        
        last_dm = db.execute("SELECT recipient FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1", (target,)).fetchone()
        last_dm_to = last_dm['recipient'] if last_dm else "Kimseyle konuşmamış"
        
        return render_template("index.html", page="profile", profile_user=profile_user, followers=f_count, is_following=is_following, last_dm_to=last_dm_to)
        
    return redirect(url_for("home"))

# ==========================================
# 5. KULLANICI GİRİŞ / ÇIKIŞ (AUTH)
# ==========================================

@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    if len(u) < 3 or len(p) < 4: return redirect(url_for("home"))
    
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, mekan_coin) VALUES (?, ?, 1000)", (u, generate_password_hash(p)))
        db.commit()
        session["username"] = u
    except sqlite3.IntegrityError:
        pass # Kullanıcı adı zaten var
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "").lower().strip()
    p = request.form.get("password", "").strip()
    db = get_db()
    user = db.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p): 
        session["username"] = u
        db.execute("UPDATE users SET last_login_date = ? WHERE username = ?", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), u))
        db.commit()
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ==========================================
# 6. API VE ALGORİTMALAR
# ==========================================

@app.route("/api/feed")
def get_feed():
    username = session.get("username")
    if not username: return jsonify([])
    db = get_db()
    
    query = """
        SELECT p.*, u.is_verified, u.avatar_color, u.is_private,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id AND user = ?) as is_liked_by_me
        FROM posts p JOIN users u ON p.author = u.username 
        WHERE 
            (u.is_private = 0 OR u.username = ? OR EXISTS (SELECT 1 FROM follows WHERE follower = ? AND followed = p.author))
            AND
            (p.is_whisper = 0 OR (p.is_whisper = 1 AND (p.author = ? OR EXISTS (SELECT 1 FROM follows f1 JOIN follows f2 ON f1.follower = f2.followed AND f1.followed = f2.follower WHERE f1.follower = ? AND f1.followed = p.author))))
        ORDER BY p.is_pinned DESC, p.id DESC LIMIT 50
    """
    posts = db.execute(query, (username, username, username, username, username)).fetchall()
    return jsonify([dict(p) for p in posts])

@app.route("/api/post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    is_whisper = int(request.form.get("is_whisper", 0))
    is_offline_vault = int(request.form.get("is_offline_vault", 0))
    location_tag = request.form.get("location_tag", "").strip() # HTML'den gelen lokasyon verisi bağlandı
    username = session.get("username")
    
    db = get_db()
    
    # Gece kilidi kontrolü
    is_locked, lock_msg = check_night_lock(username, db)
    if is_locked:
        return jsonify({"success": False, "error": lock_msg})

    # Susturucu kontrolü
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data = db.execute("SELECT muted_until, muted_by FROM users WHERE username=?", (username,)).fetchone()
    if user_data['muted_until'] and user_data['muted_until'] > now_str:
        return jsonify({"success": False, "error": f"Susturuldun! Susturan: @{user_data['muted_by']} 🤫"})

    if content and len(content) <= 500:
        # Hashtagleri kaydet
        tags = re.findall(r"#(\w+)", content)
        for tag in tags:
            db.execute("INSERT INTO hashtags (tag, count, last_used) VALUES (?, 1, ?) ON CONFLICT(tag) DO UPDATE SET count=count+1, last_used=?", (tag, now_str, now_str))

        # Gönderiyi konumuyla birlikte veritabanına yaz
        db.execute("INSERT INTO posts (author, content, created_at, is_whisper, is_offline_vault, location_tag) VALUES (?, ?, ?, ?, ?, ?)", 
                  (username, content, now_str, is_whisper, is_offline_vault, location_tag))
        db.execute("UPDATE users SET posts_count = posts_count + 1 WHERE username = ?", (username,))
        db.commit()
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Geçersiz veya çok uzun içerik!"})

@app.route("/api/action/<action>/<int:post_id>", methods=["POST"])
@login_required
def post_action(action, post_id):
    username = session.get("username")
    db = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "like":
        try:
            db.execute("INSERT INTO likes (user, post_id) VALUES (?, ?)", (username, post_id))
            db.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            db.commit()
        except sqlite3.IntegrityError:
            db.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            db.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            db.commit()

    elif action == "burn":
        try:
            db.execute("UPDATE posts SET burn_votes = burn_votes + 1 WHERE id = ?", (post_id,))
            post = db.execute("SELECT author, burn_votes FROM posts WHERE id = ?", (post_id,)).fetchone()
            
            if post and post['burn_votes'] >= 3:
                db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            db.commit()
            return jsonify({"success": True, "msg": "Gönderi ateşe verildi! 🔥"})
        except Exception:
            return jsonify({"success": False})

    return jsonify({"success": True})

@app.route("/api/mute/<target>", methods=["POST"])
@login_required
def apply_mute(target):
    me = session.get("username")
    if me == target: return jsonify({"success": False, "error": "Kendini susturamazsın!"})
    
    db = get_db()
    my_data = db.execute("SELECT mekan_coin, last_mute_used FROM users WHERE username=?", (me,)).fetchone()
    now = datetime.datetime.now()
    
    if my_data['mekan_coin'] < 50:
        return jsonify({"success": False, "error": "Yetersiz bakiye! 50 Mekan Coin gerekli."})
    
    if my_data['last_mute_used'] and my_data['last_mute_used'][:10] == now.strftime("%Y-%m-%d"):
         return jsonify({"success": False, "error": "Günde sadece 1 kişiyi susturabilirsin!"})
        
    mute_until = (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE users SET muted_until=?, muted_by=?, mekan_coin=mekan_coin-50, last_mute_used=? WHERE username=?", (mute_until, me, now.strftime("%Y-%m-%d %H:%M:%S"), target))
    db.execute("UPDATE users SET last_mute_used=? WHERE username=?", (now.strftime("%Y-%m-%d %H:%M:%S"), me))
    db.commit()
    return jsonify({"success": True, "msg": f"@{target} 10 dakika susturuldu! (-50 Coin)"})

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
@login_required
def chat_api(partner):
    me = session.get("username")
    db = get_db()
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        is_snap = int(request.form.get("is_snap", 0))
        if content:
            expires = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S") if is_snap else None
            db.execute("INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) VALUES (?, ?, ?, ?, ?, ?)", (me, partner, content, t, is_snap, expires))
            db.commit()

    ghost_mode = db.execute("SELECT ghost_mode FROM users WHERE username = ?", (me,)).fetchone()['ghost_mode']
    if not ghost_mode:
        db.execute("UPDATE messages SET is_read = 1, read_at = ? WHERE sender = ? AND recipient = ? AND is_read = 0", (t, partner, me))
        db.commit()

    # Okunmuş ve süresi dolmuş snap mesajlarını temizle
    db.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
    db.commit()

    msgs = db.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/update_profile", methods=["POST"])
@login_required
def update_profile():
    username = session.get("username")
    bio = request.form.get("bio", "").strip()[:150]
    color = request.form.get("avatar_color", "#5da399")
    ghost = int(request.form.get("ghost_mode", 0))
    is_private = int(request.form.get("is_private", 0))
    night_lock = int(request.form.get("night_lock", 0))
    
    db = get_db()
    db.execute("UPDATE users SET bio=?, avatar_color=?, ghost_mode=?, is_private=?, night_lock=? WHERE username=?", 
              (bio, color, ghost, is_private, night_lock, username))
    db.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
