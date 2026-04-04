import os, sqlite3, datetime, re, random, string, json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(**name**)
app.secret_key = “mekan-v2-ultimate-party-mode-2024”
app.config[‘MAX_CONTENT_LENGTH’] = 16 * 1024 * 1024

ADMIN_USERNAME = “faruk”
ADMIN_PASSWORD = “faruk4848”
DATABASE = “mekan.db”

def get_db():
if ‘db’ not in g:
g.db = sqlite3.connect(DATABASE, timeout=20)
g.db.row_factory = sqlite3.Row
g.db.execute(“PRAGMA foreign_keys = ON;”)
g.db.execute(“PRAGMA journal_mode = WAL;”)
return g.db

@app.teardown_appcontext
def close_connection(exception):
db = g.pop(‘db’, None)
if db is not None:
db.close()

def init_db():
if not os.path.exists(DATABASE):
conn = sqlite3.connect(DATABASE, timeout=20)
c = conn.cursor()
c.execute(“PRAGMA foreign_keys = ON;”)
c.execute(“PRAGMA journal_mode = WAL;”)

```
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, password TEXT NOT NULL, bio TEXT DEFAULT 'Ferah bir gun!',
        avatar_color TEXT DEFAULT '#5da399', avatar_emoji TEXT DEFAULT '🌸', last_seen TEXT, 
        is_verified INTEGER DEFAULT 0, is_private INTEGER DEFAULT 0, ghost_mode INTEGER DEFAULT 0, 
        muted_until TEXT, muted_by TEXT, last_mute_used TEXT, 
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, mekan_coin INTEGER DEFAULT 1000, 
        trust_score INTEGER DEFAULT 100, night_lock INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, total_posts INTEGER DEFAULT 0,
        total_likes_received INTEGER DEFAULT 0, badge_collection TEXT DEFAULT '[]',
        is_premium INTEGER DEFAULT 0, premium_until TEXT, birthday TEXT, gender TEXT,
        location TEXT, website TEXT, theme_color TEXT DEFAULT '#5da399',
        notification_sound INTEGER DEFAULT 1, new_followers_notification INTEGER DEFAULT 1,
        likes_notification INTEGER DEFAULT 1, messages_notification INTEGER DEFAULT 1,
        vip_status INTEGER DEFAULT 0, vip_until TEXT, followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0, blocked_users TEXT DEFAULT '[]',
        muted_words TEXT DEFAULT '[]', custom_status TEXT DEFAULT '', 
        status_emoji TEXT DEFAULT '🌱', is_online INTEGER DEFAULT 0, last_activity TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT NOT NULL, content TEXT NOT NULL,
        created_at TEXT NOT NULL, likes_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0, 
        reposts_count INTEGER DEFAULT 0, shares_count INTEGER DEFAULT 0, is_whisper INTEGER DEFAULT 0, 
        is_pinned INTEGER DEFAULT 0, location_tag TEXT, burn_votes INTEGER DEFAULT 0, 
        is_offline_vault INTEGER DEFAULT 0, post_type TEXT DEFAULT 'normal',
        mood_emoji TEXT, is_edited INTEGER DEFAULT 0, edited_at TEXT, poll_options TEXT,
        poll_votes TEXT, allows_replies INTEGER DEFAULT 1, allows_retweets INTEGER DEFAULT 1,
        media_urls TEXT DEFAULT '[]', hashtags TEXT DEFAULT '[]', mentions TEXT DEFAULT '[]',
        reply_to_id INTEGER, reply_count INTEGER DEFAULT 0, is_retweet INTEGER DEFAULT 0,
        retweet_of_id INTEGER, quote_tweet_id INTEGER,
        FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, recipient TEXT NOT NULL,
        content TEXT, is_read INTEGER DEFAULT 0, read_at TEXT, is_snap INTEGER DEFAULT 0,
        expires_at TEXT, created_at TEXT NOT NULL, reaction TEXT, message_type TEXT DEFAULT 'text',
        voice_url TEXT, image_url TEXT, is_encrypted INTEGER DEFAULT 0, is_pinned INTEGER DEFAULT 0,
        reply_to_msg_id INTEGER,
        FOREIGN KEY(sender) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(recipient) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, followed TEXT, created_at TEXT, UNIQUE(follower, followed))")
    
    c.execute("CREATE TABLE IF NOT EXISTS likes (user TEXT, post_id INTEGER, created_at TEXT, UNIQUE(user, post_id))")
    
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT UNIQUE, count INTEGER DEFAULT 1, last_used TEXT)")
    
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, type TEXT, from_user TEXT, 
        post_id INTEGER, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, achievement TEXT, 
        description TEXT, reward_coins INTEGER, unlocked_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS leaderboard (
        rank INTEGER PRIMARY KEY, username TEXT UNIQUE, total_points INTEGER,
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, challenge_type TEXT,
        progress INTEGER DEFAULT 0, target INTEGER, reward_coins INTEGER,
        is_completed INTEGER DEFAULT 0, completed_at TEXT, created_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, referrer TEXT, referred TEXT, 
        created_at TEXT, is_rewarded INTEGER DEFAULT 0,
        FOREIGN KEY(referrer) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(referred) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, 
        amount INTEGER, message TEXT, created_at TEXT, is_anonymous INTEGER DEFAULT 0,
        FOREIGN KEY(from_user) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(to_user) REFERENCES users(username) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, 
        start_time TEXT, end_time TEXT, location TEXT, created_by TEXT,
        attendees_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, created_at TEXT
    )""")

    c.execute("""INSERT INTO users (username, password, bio, is_verified, avatar_color, 
                avatar_emoji, mekan_coin, level, vip_status) 
                VALUES (?, ?, ?, 2, '#1d9bf0', '👑', 999999, 100, 1)""",
             (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Sistemin Yaratıcısı"))
    
    conn.commit()
    conn.close()
    print("Veritabani ilk kez olusturuldu!")
```

def upgrade_db():
if not os.path.exists(DATABASE):
return

```
conn = sqlite3.connect(DATABASE, timeout=20)
c = conn.cursor()

new_columns = [
    ("posts", "reply_to_id", "INTEGER"),
    ("posts", "reaction", "TEXT"),
    ("posts", "post_type", "TEXT DEFAULT 'normal'"),
    ("posts", "mood_emoji", "TEXT"),
    ("posts", "is_edited", "INTEGER DEFAULT 0"),
    ("posts", "poll_options", "TEXT"),
    ("posts", "poll_votes", "TEXT"),
    ("posts", "allows_replies", "INTEGER DEFAULT 1"),
    ("posts", "media_urls", "TEXT DEFAULT '[]'"),
    ("posts", "reposts_count", "INTEGER DEFAULT 0"),
    ("posts", "shares_count", "INTEGER DEFAULT 0"),
    ("posts", "is_pinned", "INTEGER DEFAULT 0"),
    ("posts", "quote_tweet_id", "INTEGER"),
    ("users", "level", "INTEGER DEFAULT 1"),
    ("users", "exp", "INTEGER DEFAULT 0"),
    ("users", "badge_collection", "TEXT DEFAULT '[]'"),
    ("users", "is_premium", "INTEGER DEFAULT 0"),
    ("users", "avatar_emoji", "TEXT DEFAULT '🌸'"),
    ("users", "vip_status", "INTEGER DEFAULT 0"),
    ("users", "custom_status", "TEXT DEFAULT ''"),
    ("users", "status_emoji", "TEXT DEFAULT '🌱'"),
    ("users", "is_online", "INTEGER DEFAULT 0"),
    ("messages", "reaction", "TEXT"),
    ("messages", "message_type", "TEXT DEFAULT 'text'"),
    ("messages", "voice_url", "TEXT"),
    ("messages", "image_url", "TEXT"),
    ("messages", "is_pinned", "INTEGER DEFAULT 0"),
]

for table, col, col_type in new_columns:
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
    except:
        pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, type TEXT, from_user TEXT, 
        post_id INTEGER, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, achievement TEXT, 
        description TEXT, reward_coins INTEGER, unlocked_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS leaderboard (
        rank INTEGER PRIMARY KEY, username TEXT UNIQUE, total_points INTEGER,
        updated_at TEXT
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, challenge_type TEXT,
        progress INTEGER DEFAULT 0, target INTEGER, reward_coins INTEGER,
        is_completed INTEGER DEFAULT 0, completed_at TEXT, created_at TEXT,
        FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, referrer TEXT, referred TEXT, 
        created_at TEXT, is_rewarded INTEGER DEFAULT 0,
        FOREIGN KEY(referrer) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(referred) REFERENCES users(username) ON DELETE CASCADE
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, 
        amount INTEGER, message TEXT, created_at TEXT, is_anonymous INTEGER DEFAULT 0,
        FOREIGN KEY(from_user) REFERENCES users(username) ON DELETE CASCADE,
        FOREIGN KEY(to_user) REFERENCES users(username) ON DELETE CASCADE
    )""")
except:
    pass

try:
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, 
        start_time TEXT, end_time TEXT, location TEXT, created_by TEXT,
        attendees_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, created_at TEXT
    )""")
except:
    pass

conn.commit()
conn.close()
print("Veritabani basariyla guncellendi!")
```

init_db()
upgrade_db()

def login_required(f):
@wraps(f)
def decorated_function(*args, **kwargs):
if “username” not in session:
return redirect(url_for(‘home’))
return f(*args, **kwargs)
return decorated_function

def admin_required(f):
@wraps(f)
def decorated_function(*args, **kwargs):
if session.get(“username”) != ADMIN_USERNAME:
return jsonify({“success”: False, “msg”: “Sadece Faruk girebilir.”})
return f(*args, **kwargs)
return decorated_function

def create_notification(db, user, notif_type, from_user, post_id=None, content=””):
t = datetime.datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)
db.execute(“INSERT INTO notifications (user, type, from_user, post_id, content, created_at) VALUES (?, ?, ?, ?, ?, ?)”,
(user, notif_type, from_user, post_id, content, t))

def award_exp(db, username, exp_amount):
db.execute(“UPDATE users SET exp = exp + ? WHERE username = ?”, (exp_amount, username))
user = db.execute(“SELECT exp, level FROM users WHERE username = ?”, (username,)).fetchone()

```
exp_per_level = 100
new_level = (user['exp'] // exp_per_level) + 1

if new_level > user['level']:
    db.execute("UPDATE users SET level = ? WHERE username = ?", (new_level, username))
    return True
return False
```

def get_user_badges(db, username):
user = db.execute(“SELECT badge_collection FROM users WHERE username = ?”, (username,)).fetchone()
if user and user[‘badge_collection’]:
return json.loads(user[‘badge_collection’])
return []

@app.context_processor
def inject_global_data():
if “username” in session:
db = get_db()
user = session[“username”]
udata = db.execute(“SELECT * FROM users WHERE username = ?”, (user,)).fetchone()

```
    if not udata:
        session.clear()
        return dict(current_user=None)

    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE users SET last_seen = ?, is_online = 1 WHERE username = ?", (t, user))
    
    unread_notifications = db.execute("SELECT COUNT(*) as c FROM notifications WHERE user = ? AND is_read = 0", (user,)).fetchone()['c']
    unread_dms = db.execute("SELECT COUNT(*) as c FROM messages WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
    
    trends = db.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
    new_users = db.execute("SELECT username, avatar_color, avatar_emoji FROM users ORDER BY created_at DESC LIMIT 10").fetchall()
    
    leaderboard = db.execute("SELECT username, level, mekan_coin FROM users ORDER BY level DESC, mekan_coin DESC LIMIT 10").fetchall()
    
    db.commit()
    
    return dict(
        current_user=user, current_user_color=udata['avatar_color'], is_verified=udata['is_verified'], 
        ghost_mode=udata['ghost_mode'], is_private=udata['is_private'], mekan_coin=udata['mekan_coin'],
        trust_score=udata['trust_score'], trends=trends, new_users=new_users, unread_dms=unread_dms, 
        is_admin=(user==ADMIN_USERNAME), unread_notifications=unread_notifications, 
        user_level=udata['level'], user_badges=get_user_badges(db, user), leaderboard=leaderboard,
        is_premium=udata['is_premium'], vip_status=udata['vip_status'], avatar_emoji=udata['avatar_emoji'],
        custom_status=udata['custom_status'], status_emoji=udata['status_emoji']
    )
return dict(current_user=None)
```

@app.route(”/”)
def home():
if not session.get(“username”):
return render_template(“index.html”)
return render_template(“index.html”, page=“home”)

@app.route(”/<path:page>”)
def catch_all(page):
if not session.get(“username”):
return redirect(url_for(“home”))
user = session[“username”]
db = get_db()

```
if page == 'messages':
    chats = db.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ? ORDER BY created_at DESC", (user, user, user)).fetchall()
    chat_list = []
    for c in chats:
        partner = c['partner']
        last_msg = db.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id DESC LIMIT 1", (user, partner, partner, user)).fetchone()
        p_info = db.execute("SELECT avatar_color, avatar_emoji, is_verified FROM users WHERE username=?", (partner,)).fetchone()
        if p_info and last_msg:
            chat_list.append({
                "partner": partner, "avatar_color": p_info["avatar_color"], "avatar_emoji": p_info["avatar_emoji"], 
                "is_verified": p_info["is_verified"], "content": "Ses Mesaj" if last_msg["voice_url"] else "Resim" if last_msg["image_url"] else "Snap" if last_msg["is_snap"] else last_msg["content"],
                "time": last_msg["created_at"][11:16], "unread": 1 if last_msg["recipient"] == user and last_msg["is_read"] == 0 else 0
            })
    chat_list.sort(key=lambda x: x['time'], reverse=True)
    return render_template("index.html", page="messages", chat_list=chat_list)
    
if page == 'leaderboard':
    return render_template("index.html", page="leaderboard")
    
if page == 'explore':
    return render_template("index.html", page="explore")
    
if page == 'achievements':
    achievements = db.execute("SELECT * FROM achievements WHERE user = ? ORDER BY unlocked_at DESC", (user,)).fetchall()
    return render_template("index.html", page="achievements", achievements=achievements)
    
if page.startswith("profile/"):
    target = page.split("/")[1]
    profile_user = db.execute("SELECT * FROM users WHERE username = ?", (target,)).fetchone()
    if not profile_user: 
        return redirect(url_for("home"))
    
    f_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (target,)).fetchone()['c']
    is_following = db.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (user, target)).fetchone() is not None
    
    posts = db.execute("SELECT COUNT(*) as c FROM posts WHERE author = ?", (target,)).fetchone()['c']
    
    return render_template("index.html", page="profile", profile_user=profile_user, followers=f_count, 
                          is_following=is_following, user_posts=posts)
    
return redirect(url_for("home"))
```

@app.route(”/register”, methods=[“POST”])
def register():
u = request.form.get(“username”, “”).lower().strip()
p = request.form.get(“password”, “”).strip()
if len(u) > 2 and len(p) > 3:
db = get_db()
try:
avatar_emojis = [“🌸”, “🌺”, “🌼”, “🌻”, “🌷”, “🌹”, “🥀”, “🌱”, “🍀”, “☘️”, “🎀”, “⭐”]
db.execute(“INSERT INTO users (username, password, avatar_emoji, mekan_coin) VALUES (?, ?, ?, ?)”,
(u, generate_password_hash(p), random.choice(avatar_emojis), 1000))
db.commit()
session[“username”] = u
except sqlite3.IntegrityError:
pass
return redirect(url_for(“home”))

@app.route(”/login”, methods=[“POST”])
def login():
u = request.form.get(“username”, “”).lower().strip()
p = request.form.get(“password”, “”).strip()
db = get_db()
user = db.execute(“SELECT password FROM users WHERE username = ?”, (u,)).fetchone()
if user and check_password_hash(user[“password”], p):
session[“username”] = u
return redirect(url_for(“home”))

@app.route(”/logout”)
def logout():
session.clear()
return redirect(url_for(“home”))

@app.route(”/api/search”)
@login_required
def search_users():
q = request.args.get(‘q’, ‘’).strip().lower()
if not q:
return jsonify([])
db = get_db()
users = db.execute(“SELECT username, avatar_color, avatar_emoji, is_verified, level FROM users WHERE username LIKE ? LIMIT 10”, (f”%{q}%”,)).fetchall()
return jsonify([dict(u) for u in users])

@app.route(”/api/feed”)
def get_feed():
u = session.get(“username”)
if not u:
return jsonify([])
db = get_db()
posts = db.execute(”””
SELECT p.*, us.is_verified, us.avatar_color, us.avatar_emoji, us.level,
(SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count,
(SELECT COUNT(*) FROM likes WHERE post_id = p.id AND user = ?) as is_liked_by_me
FROM posts p JOIN users us ON p.author = us.username
WHERE p.is_whisper = 0 AND p.author NOT IN (SELECT blocked_users FROM users WHERE username = ?)
ORDER BY p.id DESC LIMIT 50
“””, (u, u)).fetchall()
return jsonify([dict(p) for p in posts])

@app.route(”/api/post”, methods=[“POST”])
@login_required
def create_post():
c = request.form.get(“content”, “”).strip()
mood = request.form.get(“mood_emoji”, “”)
post_type = request.form.get(“post_type”, “normal”)

```
u = session.get("username")
db = get_db()

if c:
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    tags = re.findall(r"#(\w+)", c)
    for t in tags: 
        db.execute("INSERT INTO hashtags (tag, count, last_used) VALUES (?, 1, ?) ON CONFLICT(tag) DO UPDATE SET count=count+1, last_used=?", 
                  (t, now_str, now_str))
    
    db.execute("""INSERT INTO posts (author, content, created_at, mood_emoji, post_type, hashtags) 
                 VALUES (?, ?, ?, ?, ?, ?)""", 
              (u, c, now_str, mood, post_type, json.dumps(tags)))
    
    leveled_up = award_exp(db, u, 10)
    db.execute("UPDATE users SET total_posts = total_posts + 1 WHERE username = ?", (u,))
    
    db.execute("""UPDATE challenges SET progress = progress + 1 
                 WHERE user = ? AND challenge_type = 'posts' AND is_completed = 0""", (u,))
    
    db.commit()
    
    if leveled_up:
        return jsonify({"success": True, "level_up": True})
    return jsonify({"success": True})
return jsonify({"success": False, "error": "Bos icerik!"})
```

@app.route(”/api/action/<action>/<int:post_id>”, methods=[“POST”])
@login_required
def post_action(action, post_id):
u = session.get(“username”)
db = get_db()

```
if action == "like":
    try:
        db.execute("INSERT INTO likes (user, post_id, created_at) VALUES (?, ?, ?)", 
                  (u, post_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        
        post = db.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post:
            create_notification(db, post['author'], 'like', u, post_id)
            db.execute("UPDATE users SET total_likes_received = total_likes_received + 1 WHERE username = ?", (post['author'],))
            award_exp(db, post['author'], 5)
        
    except sqlite3.IntegrityError:
        db.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (u, post_id))
        db.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
    
    db.commit()

elif action == "repost":
    try:
        db.execute("UPDATE posts SET reposts_count = reposts_count + 1 WHERE id = ?", (post_id,))
        post = db.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post:
            create_notification(db, post['author'], 'repost', u, post_id)
        db.commit()
    except:
        pass

elif action == "burn":
    db.execute("UPDATE posts SET burn_votes = burn_votes + 1 WHERE id = ?", (post_id,))
    p = db.execute("SELECT burn_votes FROM posts WHERE id = ?", (post_id,)).fetchone()
    if p and p['burn_votes'] >= 5: 
        db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    return jsonify({"success": True, "msg": "Atesle verildi!"})

return jsonify({"success": True})
```

@app.route(”/api/follow/<target>”, methods=[“POST”])
@login_required
def follow_user(target):
me = session.get(“username”)
if me == target:
return jsonify({“success”: False, “msg”: “Kendini takip edemezsin!”})
db = get_db()
is_following = db.execute(“SELECT 1 FROM follows WHERE follower = ? AND followed = ?”, (me, target)).fetchone()

```
t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if is_following:
    db.execute("DELETE FROM follows WHERE follower = ? AND followed = ?", (me, target))
    db.execute("UPDATE users SET followers_count = followers_count - 1 WHERE username = ?", (target,))
    db.execute("UPDATE users SET following_count = following_count - 1 WHERE username = ?", (me,))
    msg = "Takipten cikилdi."
else:
    db.execute("INSERT INTO follows (follower, followed, created_at) VALUES (?, ?, ?)", (me, target, t))
    db.execute("UPDATE users SET followers_count = followers_count + 1 WHERE username = ?", (target,))
    db.execute("UPDATE users SET following_count = following_count + 1 WHERE username = ?", (me,))
    create_notification(db, target, 'follow', me)
    award_exp(db, me, 5)
    msg = "Takip ediliyor!"

db.commit()
return jsonify({"success": True, "msg": msg})
```

@app.route(”/api/chat/<partner>”, methods=[“GET”, “POST”])
@login_required
def chat_api(partner):
me = session.get(“username”)
db = get_db()
t = datetime.datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)

```
if request.method == "POST":
    c = request.form.get("content", "").strip()
    snap = int(request.form.get("is_snap", 0))
    if c:
        exp_time = (datetime.datetime.now() + datetime.timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S") if snap else None
        db.execute("""INSERT INTO messages (sender, recipient, content, created_at, is_snap, expires_at) 
                     VALUES (?, ?, ?, ?, ?, ?)""", (me, partner, c, t, snap, exp_time))
        
        create_notification(db, partner, 'message', me, content=c[:30])
        award_exp(db, me, 2)
        db.commit()

db.execute("""UPDATE messages SET is_read = 1, read_at = ? 
             WHERE sender = ? AND recipient = ? AND is_read = 0""", (t, partner, me))
db.execute("DELETE FROM messages WHERE expires_at IS NOT NULL AND expires_at < ? AND is_read = 1", (t,))
db.commit()

msgs = db.execute("""SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) 
                    ORDER BY id ASC""", (me, partner, partner, me)).fetchall()
return jsonify([dict(m) for m in msgs])
```

@app.route(”/api/react_msg/<int:msg_id>”, methods=[“POST”])
@login_required
def react_msg(msg_id):
db = get_db()
msg = db.execute(“SELECT reaction FROM messages WHERE id = ?”, (msg_id,)).fetchone()
if msg:
new_reaction = None if msg[‘reaction’] else ‘❤️’
db.execute(“UPDATE messages SET reaction = ? WHERE id = ?”, (new_reaction, msg_id))
db.commit()
return jsonify({“success”: True})

@app.route(”/api/update_profile”, methods=[“POST”])
@login_required
def update_profile():
u = session.get(“username”)
b = request.form.get(“bio”, “”).strip()[:150]
c = request.form.get(“avatar_color”, “#5da399”)
e = request.form.get(“avatar_emoji”, “🌸”)
g = int(request.form.get(“ghost_mode”, 0))
p = int(request.form.get(“is_private”, 0))
n = int(request.form.get(“night_lock”, 0))
status = request.form.get(“custom_status”, “”).strip()[:50]
status_emoji = request.form.get(“status_emoji”, “🌱”)

```
db = get_db()
db.execute("""UPDATE users SET bio=?, avatar_color=?, avatar_emoji=?, ghost_mode=?, 
             is_private=?, night_lock=?, custom_status=?, status_emoji=? WHERE username=?""", 
          (b, c, e, g, p, n, status, status_emoji, u))
db.commit()
return jsonify({"success": True})
```

@app.route(”/api/send_tip/<target>”, methods=[“POST”])
@login_required
def send_tip(target):
u = session.get(“username”)
db = get_db()

```
amount = int(request.form.get("amount", 0))
message = request.form.get("message", "").strip()
is_anon = int(request.form.get("is_anonymous", 0))

me = db.execute("SELECT mekan_coin FROM users WHERE username = ?", (u,)).fetchone()

if amount <= 0 or amount > me['mekan_coin']:
    return jsonify({"success": False, "msg": "Yeterli coin yok!"})

t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
db.execute("""INSERT INTO tips (from_user, to_user, amount, message, created_at, is_anonymous) 
             VALUES (?, ?, ?, ?, ?, ?)""", (u, target, amount, message, t, is_anon))

db.execute("UPDATE users SET mekan_coin = mekan_coin - ? WHERE username = ?", (amount, u))
db.execute("UPDATE users SET mekan_coin = mekan_coin + ? WHERE username = ?", (amount, target))

from_name = "Anonim" if is_anon else u
create_notification(db, target, 'tip', from_name, content=f"{amount} coin gonderdi!")
award_exp(db, u, 10)

db.commit()
return jsonify({"success": True, "msg": f"Gonderildi!"})
```

@app.route(”/api/notifications”, methods=[“GET”])
@login_required
def get_notifications():
u = session.get(“username”)
db = get_db()

```
notifications = db.execute("""SELECT * FROM notifications WHERE user = ? 
                             ORDER BY created_at DESC LIMIT 50""", (u,)).fetchall()
return jsonify([dict(n) for n in notifications])
```

@app.route(”/api/notifications/<int:notif_id>/read”, methods=[“POST”])
@login_required
def mark_notification_read(notif_id):
db = get_db()
db.execute(“UPDATE notifications SET is_read = 1 WHERE id = ?”, (notif_id,))
db.commit()
return jsonify({“success”: True})

@app.route(”/api/leaderboard”)
def get_leaderboard():
db = get_db()
lb = db.execute(””“SELECT username, level, mekan_coin, followers_count, total_posts
FROM users ORDER BY level DESC, mekan_coin DESC LIMIT 100”””).fetchall()
return jsonify([dict(u) for u in lb])

@app.route(”/api/create_challenge”, methods=[“POST”])
@login_required
def create_daily_challenges():
u = session.get(“username”)
db = get_db()

```
challenges_list = [
    ("posts", "3 Gonderi Paylas", 100),
    ("likes", "10 Gonderi Begen", 75),
    ("follows", "5 Kiyi Takip Et", 50),
    ("messages", "5 Mesaj Gonder", 40),
]

t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for chal_type, desc, reward in challenges_list:
    existing = db.execute("""SELECT id FROM challenges WHERE user = ? AND challenge_type = ? 
                           AND date(created_at) = date('now')""", (u, chal_type)).fetchone()
    if not existing:
        db.execute("""INSERT INTO challenges (user, challenge_type, progress, target, reward_coins, created_at) 
                     VALUES (?, ?, 0, ?, ?, ?)""", 
                  (u, chal_type, 3 if chal_type == "posts" else 10 if chal_type == "likes" else 5, reward, t))

db.commit()

challenges = db.execute("""SELECT * FROM challenges WHERE user = ? 
                         AND date(created_at) = date('now') AND is_completed = 0""", (u,)).fetchall()
return jsonify([dict(c) for c in challenges])
```

@app.route(”/api/redeem_challenge/<int:challenge_id>”, methods=[“POST”])
@login_required
def redeem_challenge(challenge_id):
u = session.get(“username”)
db = get_db()

```
challenge = db.execute("SELECT * FROM challenges WHERE id = ? AND user = ?", (challenge_id, u)).fetchone()

if not challenge:
    return jsonify({"success": False, "msg": "Gorev bulunamadi!"})

if challenge['is_completed']:
    return jsonify({"success": False, "msg": "Gorev zaten tamamlandi!"})

if challenge['progress'] < challenge['target']:
    return jsonify({"success": False, "msg": f"Hedef: {challenge['target']}, Mevcut: {challenge['progress']}"})

db.execute("UPDATE users SET mekan_coin = mekan_coin + ? WHERE username = ?", 
          (challenge['reward_coins'], u))
db.execute("UPDATE challenges SET is_completed = 1, completed_at = ? WHERE id = ?",
          (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), challenge_id))

award_exp(db, u, 25)

db.commit()
return jsonify({"success": True, "msg": f"Gorev tamamlandi! {challenge['reward_coins']} coin kazandin!"})
```

@app.route(”/api/admin/god_mode”, methods=[“POST”])
@login_required
@admin_required
def god_mode_actions():
action = request.form.get(“action”)
target_user = request.form.get(“target_user”, “”).strip().lower()
db = get_db()

```
if action == "add_coin":
    amount = int(request.form.get("amount", 10000))
    db.execute("UPDATE users SET mekan_coin = mekan_coin + ? WHERE username = ?", (amount, target_user))
    msg = f"Coin verildi!"

elif action == "level_up":
    levels = int(request.form.get("levels", 1))
    db.execute("UPDATE users SET level = level + ? WHERE username = ?", (levels, target_user))
    msg = f"Seviye yukseltildi!"

elif action == "verify_user":
    db.execute("UPDATE users SET is_verified = 1 WHERE username = ?", (target_user,))
    msg = f"Dogrulandi!"

elif action == "make_vip":
    vip_days = int(request.form.get("days", 30))
    until = (datetime.datetime.now() + datetime.timedelta(days=vip_days)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE users SET vip_status = 1, vip_until = ? WHERE username = ?", (until, target_user))
    msg = f"VIP yapildi!"

elif action == "ban_user":
    if target_user == ADMIN_USERNAME: 
        return jsonify({"success": False, "msg": "Kendini silemezsin!"})
    db.execute("DELETE FROM users WHERE username = ?", (target_user,))
    msg = f"Banlamdi!"

elif action == "delete_post":
    post_id = request.form.get("post_id")
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    msg = f"Gonderi silindi!"

elif action == "reset_user":
    db.execute("UPDATE users SET mekan_coin = 1000, level = 1, exp = 0 WHERE username = ?", (target_user,))
    msg = f"Sifirlamdi!"

elif action == "announce":
    announcement = request.form.get("announcement", "")
    msg = f"Duyuru gonderildi!"

db.commit()
return jsonify({"success": True, "msg": msg})
```

if **name** == “**main**”:
app.run(debug=True, host=“0.0.0.0”, port=int(os.environ.get(“PORT”, 5000)))
