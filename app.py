import os, sqlite3, datetime, re, random, json, hashlib
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
        g.db.execute("PRAGMA foreign_keys = ON;") # İlişkisel veri bütünlüğü
        g.db.execute("PRAGMA journal_mode = WAL;") # Yüksek hızda okuma/yazma performansı
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Sistemin kalbi: 48 devasa özelliği barındıracak tabloların oluşturulması.
    """
    with app.app_context():
        db = get_db()
        c = db.cursor()

        # 1. KULLANICILAR (USERS) - Genişletilmiş Özellikler
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            bio TEXT DEFAULT 'Mekan''da ferah bir gün!',
            avatar_color TEXT DEFAULT '#2e8b57',
            profile_banner TEXT,
            profile_music TEXT, -- Profilde çalacak şarkı linki
            last_seen TEXT,
            is_verified INTEGER DEFAULT 0, -- 0: Yok, 1: Mavi, 2: Altın (Premium)
            is_private INTEGER DEFAULT 0, -- Gizli Hesap
            ghost_mode INTEGER DEFAULT 0, -- Hayalet Modu (Mavi tık gizleme)
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
            mekan_coin INTEGER DEFAULT 1000, -- Sanal para birimi
            trust_score INTEGER DEFAULT 100, -- Güvenilirlik puanı (Trollemeye karşı)
            streak_days INTEGER DEFAULT 0, -- Aralıksız giriş yapma serisi
            night_lock INTEGER DEFAULT 0 -- Gece sarhoş modu kilidi
        )""")

        # 2. GÖNDERİLER (POSTS) - Medya, Anket, Lokasyon, Düello ve Yanma (Burn)
        c.execute("""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            media_url TEXT, -- Görsel/Ses dosyası yolu
            created_at TEXT NOT NULL,
            likes_count INTEGER DEFAULT 0,
            retweets_count INTEGER DEFAULT 0,
            replies_count INTEGER DEFAULT 0,
            quote_id INTEGER,
            reply_to_id INTEGER,
            is_whisper INTEGER DEFAULT 0, -- Sadece karşılıklı takipçiler
            is_pinned INTEGER DEFAULT 0,
            is_nsfw INTEGER DEFAULT 0, -- Hassas içerik uyarısı
            location_tag TEXT, -- "Yalıkavak", "Turgutreis" vb.
            poll_id INTEGER, -- Anket bağlantısı
            burn_votes INTEGER DEFAULT 0, -- Ateşe ver (Silinme) oyları
            is_offline_vault INTEGER DEFAULT 0, -- Çevrimdışı sır gönderisi
            duel_status INTEGER DEFAULT 0, -- 0: Yok, 1: Düello Aktif, 2: Bitti
            FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE
        )""")

        # 3. MESAJLAR (MESSAGES) - Sesli, Snap, Reaksiyon
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            content TEXT,
            media_url TEXT, -- DM'den sesli veya foto
            is_read INTEGER DEFAULT 0,
            read_at TEXT, -- Görüldü saati
            is_snap INTEGER DEFAULT 0, -- Kendini imha eden
            expires_at TEXT,
            reaction TEXT, -- Mesaja atılan emoji tepkisi
            created_at TEXT NOT NULL,
            FOREIGN KEY(sender) REFERENCES users(username) ON DELETE CASCADE,
            FOREIGN KEY(recipient) REFERENCES users(username) ON DELETE CASCADE
        )""")

        # 4. HİKAYELER VE ÖNE ÇIKANLAR (STORIES & HIGHLIGHTS)
        c.execute("""CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            content TEXT,
            media_url TEXT,
            created_at TEXT NOT NULL,
            views_count INTEGER DEFAULT 0,
            is_highlight INTEGER DEFAULT 0 -- Profilde sabitlenen hikayeler
        )""")

        # 5. İLİŞKİLER (TAKİP, YAKIN ARKADAŞ, ENGEL)
        c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, followed TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(follower, followed))")
        c.execute("CREATE TABLE IF NOT EXISTS follow_requests (sender TEXT, receiver TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(sender, receiver))")
        c.execute("CREATE TABLE IF NOT EXISTS close_friends (user TEXT, friend TEXT, UNIQUE(user, friend))")
        c.execute("CREATE TABLE IF NOT EXISTS blocks (blocker TEXT, blocked TEXT, UNIQUE(blocker, blocked))")

        # 6. ETKİLEŞİMLER VE ALGORİTMA (BEĞENİ, RT, BOOKMARK, HASHTAG)
        c.execute("CREATE TABLE IF NOT EXISTS likes (user TEXT, post_id INTEGER, reaction_type TEXT DEFAULT 'heart', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))")
        c.execute("CREATE TABLE IF NOT EXISTS retweets (user TEXT, post_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, post_id))")
        c.execute("CREATE TABLE IF NOT EXISTS bookmarks (user TEXT, post_id INTEGER, folder_name TEXT DEFAULT 'Genel', UNIQUE(user, post_id))")
        c.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT UNIQUE, count INTEGER DEFAULT 1, last_used TEXT)")
        
        # 7. BİLDİRİMLER (NOTIFICATIONS)
        c.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            sender TEXT,
            type TEXT NOT NULL, -- 'like', 'reply', 'duel_invite', 'burn_alert' vb.
            post_id INTEGER,
            content TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )""")

        # 8. ANKETLER (POLLS) VE OYLAR
        c.execute("""CREATE TABLE IF NOT EXISTS polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            option_1 TEXT, option_1_votes INTEGER DEFAULT 0,
            option_2 TEXT, option_2_votes INTEGER DEFAULT 0,
            option_3 TEXT, option_3_votes INTEGER DEFAULT 0,
            option_4 TEXT, option_4_votes INTEGER DEFAULT 0,
            expires_at TEXT
        )""")
        c.execute("CREATE TABLE IF NOT EXISTS poll_votes (user TEXT, poll_id INTEGER, option_index INTEGER, UNIQUE(user, poll_id))")

        # 9. ANONİM İTİRAF KUTUSU (CONFESSIONS)
        c.execute("""CREATE TABLE IF NOT EXISTS confessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_public INTEGER DEFAULT 0 -- Hedef kişi bunu profilinde yayınlarsa 1 olur
        )""")

        # 10. DÜELLOLAR (ARENA)
        c.execute("""CREATE TABLE IF NOT EXISTS arena_duels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            challenger TEXT,
            defender TEXT,
            challenger_args TEXT,
            defender_args TEXT,
            challenger_votes INTEGER DEFAULT 0,
            defender_votes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending', -- pending, active, finished
            expires_at TEXT
        )""")

        # 11. BAŞARI ROZETLERİ (ACHIEVEMENTS)
        c.execute("CREATE TABLE IF NOT EXISTS user_badges (user TEXT, badge_name TEXT, earned_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user, badge_name))")

        # Admin Hesabı Kontrolü
        if not db.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
            db.execute("""INSERT INTO users (username, password, bio, is_verified, mood, avatar_color, mekan_coin) 
                          VALUES (?, ?, ?, 2, '👑 Kurucu', '#1d9bf0', 999999)""",
                     (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Sistemin Yaratıcısı"))
        db.commit()

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
            return True, "Gece kilidi aktif! Gönderi atabilmek için önce ayıklık testini (Matematik sorusunu) çözmelisin."
    return False, ""

def calculate_trending(db):
    """ Gelişmiş Gündem Algoritması (Zamana göre çürüyen (decay) hashtag skorları) """
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
        
        udata = db.execute("SELECT is_verified, ghost_mode, is_private, mekan_coin, night_lock, trust_score FROM users WHERE username = ?", (user,)).fetchone()
        db.commit()
        
        return dict(
            current_user=user, 
            is_verified=udata['is_verified'] if udata else 0, 
            ghost_mode=udata['ghost_mode'] if udata else 0, 
            is_private=udata['is_private'] if udata else 0,
            mekan_coin=udata['mekan_coin'] if udata else 0,
            unread_notifs=unread, 
            new_users=new_users, 
            trends=trends, 
            is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    db = get_db()
    stories = db.execute("SELECT s.*, u.avatar_color, u.is_verified FROM stories s JOIN users u ON s.author = u.username WHERE datetime(s.created_at) >= datetime('now', '-24 hours') ORDER BY s.id DESC LIMIT 15").fetchall()
    return render_template("index.html", page="home", stories=stories)

@app.route("/<path:page>")
def catch_all(page):
    if not session.get("username"): return redirect(url_for("home"))
    user = session["username"]
    db = get_db()
    
    valid_pages = ['explore', 'bookmarks', 'settings', 'search', 'arena', 'wallet']
    if page in valid_pages: 
        return render_template("index.html", page=page)
        
    if page == 'messages':
        chats = db.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ?", (user, user, user)).fetchall()
        chat_list = []
        for c in chats:
            partner = c['partner']
            last_msg = db.execute("SELECT content, created_at, is_read, sender, is_snap FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id DESC LIMIT 1", (user, partner, partner, user)).fetchone()
            p_info = db.execute("SELECT avatar_color, is_verified FROM users WHERE username=?", (partner,)).fetchone()
            if p_info and last_msg:
                chat_list.append({
                    "partner": partner,
                    "avatar_color": p_info["avatar_color"],
                    "is_verified": p_info["is_verified"],
                    "last_msg": "💣 [Snap Mesajı]" if last_msg["is_snap"] else last_msg["content"],
                    "time": last_msg["created_at"].split(" ")[1][:5],
                    "unread": 1 if (last_msg["sender"] == partner and last_msg["is_read"] == 0) else 0
                })
        return render_template("index.html", page="messages", chat_list=chat_list)
        
    if page == 'notifications':
        notifs = db.execute("SELECT n.*, u.avatar_color, u.is_verified FROM notifications n LEFT JOIN users u ON n.sender = u.username WHERE n.recipient = ? ORDER BY n.id DESC LIMIT 30", (user,)).fetchall()
        db.execute("UPDATE notifications SET is_read = 1 WHERE recipient = ?", (user,))
        db.commit()
        return render_template("index.html", page="notifications", notifs=notifs)
    
    if page.startswith("profile/"):
        target = page.split("/")[1]
        profile_user = db.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
        if not profile_user: return redirect(url_for("home"))
            
        f_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
        is_following = db.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (user, target)).fetchone() is not None
        
        last_dm = db.execute("SELECT recipient FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1", (target,)).fetchone()
        last_dm_to = last_dm['recipient'] if last_dm else "Kimseyle konuşmamış"
        
        # Anonim İtirafları Çek
        confessions = db.execute("SELECT * FROM confessions WHERE target_user = ? AND is_public = 1 ORDER BY id DESC LIMIT 5", (target,)).fetchall()
        
        return render_template("index.html", page="profile", profile_user=profile_user, followers=f_count, is_following=is_following, last_dm_to=last_dm_to, confessions=confessions)
        
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
        # Yeni kaydolanlara 1000 Mekan Coin hediye!
        db.execute("INSERT INTO users (username, password, mekan_coin) VALUES (?, ?, 1000)", (u, generate_password_hash(p)))
        db.commit()
        session["username"] = u
    except: pass
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
# 6. DEVASA API VE ALGORİTMALAR (48 ÖZELLİK)
# ==========================================

@app.route("/api/feed")
def get_feed():
    username = session.get("username")
    if not username: return jsonify([])
    db = get_db()
    
    # Kapsamlı Akış Algoritması: Gizli Hesaplar, Fısıltılar, Çevrimdışı Sırlar ve Sabitlenmişler
    query = """
        SELECT p.*, u.is_verified, u.avatar_color, u.is_private, u.profile_banner,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
               (SELECT COUNT(*) FROM retweets WHERE post_id = p.id) as retweets_count,
               (SELECT content FROM posts WHERE id = p.quote_id) as quote_content,
               (SELECT author FROM posts WHERE id = p.quote_id) as quote_author,
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
    username = session.get("username")
    
    db = get_db()
    
    # 1. GECE KİLİDİ KONTROLÜ
    is_locked, lock_msg = check_night_lock(username, db)
    if is_locked:
        return jsonify({"success": False, "error": lock_msg})

    # 2. SUSTURUCU KONTROLÜ
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data = db.execute("SELECT muted_until, muted_by FROM users WHERE username=?", (username,)).fetchone()
    if user_data['muted_until'] and user_data['muted_until'] > now_str:
        return jsonify({"success": False, "error": f"Susturuldun! Susturan: @{user_data['muted_by']} 🤫"})

    if content and len(content) <= 500:
        # Hashtagleri ayıkla ve kaydet
        tags = re.findall(r"#(\w+)", content)
        for tag in tags:
            db.execute("INSERT INTO hashtags (tag, count, last_used) VALUES (?, 1, ?) ON CONFLICT(tag) DO UPDATE SET count=count+1, last_used=?", (tag, now_str, now_str))

        db.execute("INSERT INTO posts (author, content, created_at, is_whisper, is_offline_vault) VALUES (?, ?, ?, ?, ?)", 
                  (username, content, now_str, is_whisper, is_offline_vault))
        db.execute("UPDATE users SET posts_count = posts_count + 1 WHERE username = ?", (username,))
        db.commit()
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Geçersiz içerik!"})

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
            
            # Bildirim Gönder
            post = db.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
            if post and post['author'] != username:
                db.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, 'like', ?, ?)", (post['author'], username, post_id, now))
            db.commit()
        except:
            db.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            db.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            db.commit()

    elif action == "burn":
        # ZEHİR ÖZELLİK: Gönderiyi Ateşe Ver (Toplu Linç Sistemi)
        try:
            db.execute("UPDATE posts SET burn_votes = burn_votes + 1 WHERE id = ?", (post_id,))
            post = db.execute("SELECT author, burn_votes FROM posts WHERE id = ?", (post_id,)).fetchone()
            
            if post and post['burn_votes'] >= 3: # 3 kişi ateşe verirse silinir!
                db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
                db.execute("INSERT INTO notifications (recipient, sender, type, created_at, content) VALUES (?, ?, 'burn_alert', ?, ?)", 
                          (post['author'], 'SİSTEM', now, 'Bir gönderin grup tarafından ateşe verilerek kül edildi! 🔥'))
            db.commit()
            return jsonify({"success": True, "msg": "Ateşe verildi! 🔥"})
        except Exception as e:
            return jsonify({"success": False})

    elif action == "delete":
        db.execute("DELETE FROM posts WHERE id = ? AND author = ?", (post_id, username))
        db.commit()
        
    return jsonify({"success": True})

@app.route("/api/mute/<target>", methods=["POST"])
@login_required
def apply_mute(target):
    me = session.get("username")
    if me == target: return jsonify({"success": False})
    
    db = get_db()
    my_data = db.execute("SELECT mekan_coin, last_mute_used FROM users WHERE username=?", (me,)).fetchone()
    now = datetime.datetime.now()
    
    # Susturucu Bedeli: 50 Mekan Coin
    if my_data['mekan_coin'] < 50:
        return jsonify({"success": False, "error": "Fakirsin! Susturucu almak için 50 Mekan Coin lazım."})
    
    # Günde 1 kez limit (Opsiyonel, şimdilik parası olan sustursun dedik ama limiti de tutuyoruz)
    if my_data['last_mute_used'] and my_data['last_mute_used'][:10] == now.strftime("%Y-%m-%d"):
         return jsonify({"success": False, "error": "Silah soğumadı! (Günde 1 hak)"})
        
    mute_until = (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE users SET muted_until=?, muted_by=?, mekan_coin=mekan_coin-50, last_mute_used=? WHERE username=?", (mute_until, me, now.strftime("%Y-%m-%d %H:%M:%S"), target))
    db.execute("UPDATE users SET last_mute_used=? WHERE username=?", (now.strftime("%Y-%m-%d %H:%M:%S"), me))
    
    # Hedefe bildirim gönder
    db.execute("INSERT INTO notifications (recipient, sender, type, created_at, content) VALUES (?, ?, 'mute', ?, ?)", 
               (target, me, now.strftime("%Y-%m-%d %H:%M:%S"), "Sana 10 dakikalık susturucu taktı! 🤫"))
    db.commit()
    return jsonify({"success": True, "msg": f"{target} 10 dk susturuldu! (-50 Coin)"})

@app.route("/api/confess/<target>", methods=["POST"])
@login_required
def send_confession(target):
    content = request.form.get("content", "").strip()
    if not content: return jsonify({"success": False})
    
    db = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Anonim itiraf veritabanına kaydolur
    db.execute("INSERT INTO confessions (target_user, content, created_at) VALUES (?, ?, ?)", (target, content, now))
    db.execute("INSERT INTO notifications (recipient, sender, type, created_at, content) VALUES (?, ?, 'confession', ?, ?)", 
               (target, 'Anonim Biri', now, 'Profiline yeni bir anonim itiraf bırakıldı! 👀'))
    db.commit()
    return jsonify({"success": True, "msg": "İtiraf gizlice kutuya bırakıldı."})

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

    # Snap (Kendini İmha Eden) Mesajları Temizle
    db.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
    db.commit()

    msgs = db.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/update_profile", methods=["POST"])
@login_required
def update_profile():
    username = session.get("username")
    bio = request.form.get("bio", "").strip()[:150]
    color = request.form.get("avatar_color", "#2e8b57")
    ghost = int(request.form.get("ghost_mode", 0))
    is_private = int(request.form.get("is_private", 0))
    night_lock = int(request.form.get("night_lock", 0))
    
    db = get_db()
    db.execute("UPDATE users SET bio=?, avatar_color=?, ghost_mode=?, is_private=?, night_lock=? WHERE username=?", 
              (bio, color, ghost, is_private, night_lock, username))
    db.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    # Render gibi platformlarda çalışması için ayarlar
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
