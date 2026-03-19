from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v99-godmode"

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
        last_seen TEXT, is_verified INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, 
        last_login_date TEXT, profile_views INTEGER DEFAULT 0, mood TEXT DEFAULT '✨ Yeni',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, 
        created_at TEXT, likes_count INTEGER DEFAULT 0, retweets_count INTEGER DEFAULT 0, 
        replies_count INTEGER DEFAULT 0, views_count INTEGER DEFAULT 0)""")
    
    c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, author TEXT, content TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS retweets (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS post_views (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, post_id INTEGER, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE, count INTEGER DEFAULT 1)")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio, is_verified, mood) VALUES (?, ?, ?, 1, '👑 Kurucu')", 
                 (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu"))
    conn.commit(); conn.close()

init_db()

@app.context_processor
def inject_global_data():
    if "username" in session:
        conn = get_db()
        user = session["username"]
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        user_data = conn.execute("SELECT * FROM users WHERE username = ?", (user,)).fetchone()
        streak = 0
        if user_data:
            last_date = user_data['last_login_date']
            streak = user_data['streak'] if user_data['streak'] else 0
            if last_date != date_str:
                if last_date == (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d"): streak += 1
                else: streak = 1
                conn.execute("UPDATE users SET streak = ?, last_login_date = ? WHERE username = ?", (streak, date_str, user))
        
        conn.execute("UPDATE users SET last_seen = ? WHERE username = ?", (time_str, user))
        
        # 4. Özellik: Yeni Katılanlar (Her yerde çekiliyor)
        new_users = conn.execute("SELECT username, is_verified FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 5", (user,)).fetchall()
        top_users = conn.execute("SELECT u.username, u.is_verified, u.mood, (SELECT COUNT(*) FROM follows WHERE followed = u.username) as followers FROM users u WHERE u.username != ? ORDER BY followers DESC LIMIT 5", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        unread_notifs = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        
        conn.commit(); conn.close()
        
        return dict(
            current_user=user, 
            current_user_verified=user_data['is_verified'] if user_data else 0,
            current_user_mood=user_data['mood'] if user_data else '',
            current_user_streak=streak,
            new_users=new_users,
            top_users=top_users, 
            trends=trends, 
            unread_notifs=unread_notifs,
            is_admin=(user==ADMIN_USERNAME)
        )
    return dict(current_user=None)

def notify(recipient, sender, n_type, post_id=0):
    if recipient != sender:
        conn = get_db()
        conn.execute("INSERT INTO notifications (recipient, sender, type, post_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                     (recipient, sender, n_type, post_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()

@app.route("/")
def home():
    if not session.get("username"): return render_template("index.html")
    conn = get_db()
    posts = conn.execute("SELECT p.*, u.is_verified, u.mood FROM posts p JOIN users u ON p.author = u.username ORDER BY p.id DESC LIMIT 50").fetchall()
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

    posts = conn.execute("SELECT p.*, u.is_verified, u.mood FROM posts p JOIN users u ON p.author = u.username WHERE author = ? ORDER BY p.id DESC", (username,)).fetchall()
    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone() is not None
    followers = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']
    following = conn.execute("SELECT COUNT(*) as c FROM follows WHERE follower = ?", (username,)).fetchone()['c']
    conn.close()
    return render_template("index.html", page="profile", profile_user=user, posts=posts, followers=followers, following=following, is_following=is_following)

@app.route("/messages_page")
def messages_page():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    chats = conn.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ?", (session["username"], session["username"], session["username"])).fetchall()
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

@app.route("/bookmarks")
def bookmarks():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    posts = conn.execute("SELECT p.*, u.is_verified, u.mood FROM posts p JOIN bookmarks b ON p.id = b.post_id JOIN users u ON p.author = u.username WHERE b.user = ? ORDER BY b.id DESC", (session["username"],)).fetchall()
    conn.close()
    return render_template("index.html", page="bookmarks", posts=posts)

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    if len(username) < 3 or not username.isalnum():
        flash("Sadece harf ve rakam (Min 3 karakter)"); return redirect(url_for("home"))
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

@app.route("/api/update_mood", methods=["POST"])
def update_mood():
    if "username" not in session: return jsonify({"error": "Giriş yapın"})
    conn = get_db()
    conn.execute("UPDATE users SET mood = ? WHERE username = ?", (request.form.get("mood", "✨ Yeni"), session["username"]))
    conn.commit(); conn.close()
    return redirect(url_for("profile", username=session["username"]))

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
        for tag in re.findall(r"#(\w+)", content):
            if conn.execute("SELECT id FROM hashtags WHERE tag = ?", (tag,)).fetchone():
                conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
            else: conn.execute("INSERT INTO hashtags (tag) VALUES (?)", (tag,))
        conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    return jsonify({"success": True})

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

@app.route("/api/action/<action_type>/<int:post_id>", methods=["POST"])
def post_action(action_type, post_id):
    if "username" not in session: return jsonify({"error": "Hata"})
    conn = get_db()
    if action_type == "bookmark":
        if conn.execute("SELECT 1 FROM bookmarks WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone():
            conn.execute("DELETE FROM bookmarks WHERE user = ? AND post_id = ?", (session["username"], post_id))
        else: conn.execute("INSERT INTO bookmarks (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.commit(); conn.close()
        return jsonify({"success": True})

    table, col = ("likes", "likes_count") if action_type == "like" else ("retweets", "retweets_count")
    if conn.execute(f"SELECT 1 FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id)).fetchone():
        conn.execute(f"DELETE FROM {table} WHERE user = ? AND post_id = ?", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} - 1 WHERE id = ?", (post_id,))
    else:
        conn.execute(f"INSERT INTO {table} (user, post_id) VALUES (?, ?)", (session["username"], post_id))
        conn.execute(f"UPDATE posts SET {col} = {col} + 1 WHERE id = ?", (post_id,))
        if action_type == "like": 
            post = conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,)).fetchone()
            if post: notify(post["author"], session["username"], "like", post_id)
                
    count = conn.execute(f"SELECT {col} FROM posts WHERE id = ?", (post_id,)).fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({"success": True, "count": count})

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
        notify(username, session["username"], "follow")
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    conn = get_db()
    users = conn.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 5", (f"%{q}%",)).fetchall()
    conn.close()
    return jsonify([u["username"] for u in users])

@app.route("/api/check_notifications")
def check_notifications():
    if "username" not in session: return jsonify({"count": 0})
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (session["username"],)).fetchone()['c']
    conn.close()
    return jsonify({"count": count})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
