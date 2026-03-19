from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, datetime, re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mekan-v40-final"

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
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT, likes_count INTEGER DEFAULT 0, retweets_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0, views_count INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, recipient TEXT, content TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower TEXT, followed TEXT, UNIQUE(follower, followed))")
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, sender TEXT, type TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE, count INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")
    c.execute("CREATE TABLE IF NOT EXISTS post_views (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, post_id INTEGER, UNIQUE(user, post_id))")

    if not c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone():
        c.execute("INSERT INTO users (username, password, bio, is_verified, mood) VALUES (?, ?, ?, 1, '👑 Kurucu')", (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), "Mekan Kurucusu"))
    conn.commit(); conn.close()

init_db()

@app.context_processor
def inject_global_data():
    if "username" in session:
        conn = get_db()
        user = session["username"]
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET last_seen = ? WHERE username = ?", (time_str, user))
        unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE recipient = ? AND is_read = 0", (user,)).fetchone()['c']
        new_users_list = conn.execute("SELECT username, is_verified FROM users WHERE username != ? ORDER BY created_at DESC LIMIT 10", (user,)).fetchall()
        top_users = conn.execute("SELECT u.username, u.is_verified, (SELECT COUNT(*) FROM follows WHERE followed = u.username) as followers FROM users u WHERE u.username != ? ORDER BY followers DESC LIMIT 5", (user,)).fetchall()
        trends = conn.execute("SELECT tag, count FROM hashtags ORDER BY count DESC LIMIT 5").fetchall()
        user_data = conn.execute("SELECT is_verified FROM users WHERE username = ?", (user,)).fetchone()
        conn.commit(); conn.close()
        return dict(current_user=user, is_verified=user_data['is_verified'] if user_data else 0, unread_notifs=unread, new_users=new_users_list, top_users=top_users, trends=trends, is_admin=(user==ADMIN_USERNAME))
    return dict(current_user=None)

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
    posts = conn.execute("SELECT p.*, u.is_verified FROM posts p JOIN users u ON p.author = u.username WHERE author = ? ORDER BY p.id DESC", (username,)).fetchall()
    is_following = conn.execute("SELECT 1 FROM follows WHERE follower = ? AND followed = ?", (session["username"], username)).fetchone() is not None
    f_count = conn.execute("SELECT COUNT(*) as c FROM follows WHERE followed = ?", (username,)).fetchone()['c']
    conn.close()
    return render_template("index.html", page="profile", profile_user=user, posts=posts, followers=f_count, is_following=is_following)

@app.route("/messages_page")
def messages_page():
    if not session.get("username"): return redirect(url_for("home"))
    conn = get_db()
    chats = conn.execute("SELECT DISTINCT CASE WHEN sender = ? THEN recipient ELSE sender END as partner FROM messages WHERE sender = ? OR recipient = ?", (session["username"], session["username"], session["username"])).fetchall()
    conn.close()
    return render_template("index.html", page="messages", chats=chats)

@app.route("/api/chat/<partner>", methods=["GET", "POST"])
def chat_api(partner):
    me = session.get("username")
    conn = get_db()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", (me, partner, content, t))
            conn.execute("INSERT INTO notifications (recipient, sender, type, created_at) VALUES (?, ?, 'message', ?)", (partner, me, t))
            conn.commit()
    conn.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND recipient = ?", (partner, me))
    conn.commit()
    msgs = conn.execute("SELECT * FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY id ASC", (me, partner, partner, me)).fetchall()
    conn.close()
    return jsonify([dict(m) for m in msgs])

@app.route("/api/post", methods=["POST"])
def create_post():
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, t))
        for tag in re.findall(r"#(\w+)", content):
            conn.execute("INSERT OR IGNORE INTO hashtags (tag) VALUES (?)", (tag,))
            conn.execute("UPDATE hashtags SET count = count + 1 WHERE tag = ?", (tag,))
        conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/post_story", methods=["POST"])
def api_story():
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        conn.execute("INSERT INTO stories (author, content, created_at) VALUES (?, ?, ?)", (session["username"], content, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/action/<type>/<int:id>", methods=["POST"])
def api_action(type, id):
    conn = get_db()
    if type == "like":
        conn.execute("INSERT OR IGNORE INTO likes (user, post_id) VALUES (?, ?)", (session["username"], id))
        conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (id,))
    elif type == "delete":
        conn.execute("DELETE FROM posts WHERE id = ?", (id,))
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/register", methods=["POST"])
def register():
    u, p = request.form.get("username").lower(), request.form.get("password")
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, generate_password_hash(p)))
        conn.commit(); session["username"] = u
    except: flash("İsim alınmış!")
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    u, p = request.form.get("username").lower(), request.form.get("password")
    conn = get_db()
    user = conn.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p): session["username"] = u
    else: flash("Hatalı!")
    return redirect(url_for("home"))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
