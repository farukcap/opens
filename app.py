from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bizim-mekan-super-secret-key-2024-faruk"

ADMIN_USERNAME = "faruk"
ADMIN_PASSWORD = "faruk4848"

DATABASE = "mekan.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE NOT NULL, 
                  password TEXT NOT NULL,
                  bio TEXT DEFAULT '',
                  followers_count INTEGER DEFAULT 0,
                  following_count INTEGER DEFAULT 0,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  author TEXT NOT NULL, 
                  content TEXT NOT NULL, 
                  created_at TEXT NOT NULL,
                  likes_count INTEGER DEFAULT 0,
                  retweets_count INTEGER DEFAULT 0,
                  FOREIGN KEY(author) REFERENCES users(username) ON DELETE CASCADE)""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  is_read INTEGER DEFAULT 0,
                  FOREIGN KEY(sender) REFERENCES users(username) ON DELETE CASCADE,
                  FOREIGN KEY(recipient) REFERENCES users(username) ON DELETE CASCADE)""")

    c.execute("""CREATE TABLE IF NOT EXISTS likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user TEXT NOT NULL,
                  post_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(user, post_id),
                  FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE,
                  FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)""")

    c.execute("""CREATE TABLE IF NOT EXISTS retweets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user TEXT NOT NULL,
                  post_id INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(user, post_id),
                  FOREIGN KEY(user) REFERENCES users(username) ON DELETE CASCADE,
                  FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)""")

    c.execute("""CREATE TABLE IF NOT EXISTS blocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  blocker TEXT NOT NULL,
                  blocked TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(blocker, blocked),
                  FOREIGN KEY(blocker) REFERENCES users(username) ON DELETE CASCADE,
                  FOREIGN KEY(blocked) REFERENCES users(username) ON DELETE CASCADE)""")

    c.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if not c.fetchone():
        hashli_sifre = generate_password_hash(ADMIN_PASSWORD)
        c.execute("INSERT INTO users (username, password, bio) VALUES (?, ?, ?)", 
                 (ADMIN_USERNAME, hashli_sifre, "Bizim Mekan Admin"))

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    try:
        if session.get("username"):
            conn = get_db_connection()
            c = conn.cursor()
            
            c.execute("""SELECT p.id, p.author, p.content, p.created_at, 
                         p.likes_count, p.retweets_count, u.bio
                         FROM posts p
                         JOIN users u ON p.author = u.username
                         ORDER BY p.id DESC LIMIT 200""")
            posts = c.fetchall()
            
            c.execute("SELECT username, bio, followers_count FROM users WHERE username != ? ORDER BY followers_count DESC", 
                     (session["username"],))
            all_users = c.fetchall()
            
            conn.close()
            
            current_user = session.get("username")
            is_admin = current_user == ADMIN_USERNAME
            
            return render_template("index.html", posts=posts, all_users=all_users,
                                 current_user=current_user, is_admin=is_admin)
        else:
            return render_template("index.html")
            
    except Exception as e:
        print(f"Error home: {e}")
        return redirect(url_for("home"))

@app.route("/register", methods=["POST"])
def register():
    try:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Kullanici adi ve sifre bos olamaz!")
            return redirect(url_for("home"))
        
        if len(username) < 2:
            flash("Kullanici adi en az 2 karakter olmali!")
            return redirect(url_for("home"))
        
        if len(password) < 4:
            flash("Sifre en az 4 karakter olmali!")
            return redirect(url_for("home"))
        
        hashed = generate_password_hash(password)
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                     (username, hashed))
            conn.commit()
            session["username"] = username
            flash(f"Hosgeldin {username}!")
        except sqlite3.IntegrityError:
            flash("Bu kullanici adi zaten alinmis!")
        finally:
            conn.close()
        
        return redirect(url_for("home"))
    except Exception as e:
        print(f"Error register: {e}")
        flash("Kayit hatasi!")
        return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    try:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Kullanici adi ve sifre bos olamaz!")
            return redirect(url_for("home"))
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            flash(f"Hosgeldin {username}!")
        else:
            flash("Kullanici adi veya sifre yanlis!")
        
        return redirect(url_for("home"))
    except Exception as e:
        print(f"Error login: {e}")
        flash("Giris hatasi!")
        return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Cikis yapildi!")
    return redirect(url_for("home"))

@app.route("/post", methods=["POST"])
def create_post():
    try:
        if "username" not in session:
            return jsonify({"error": "Lutfen giris yap"}), 401
        
        content = request.form.get("content", "").strip()
        
        if not content or len(content) == 0:
            return jsonify({"error": "Mesaj bos olamaz"}), 400
        
        if len(content) > 500:
            return jsonify({"error": "Mesaj 500 karakterden fazla olamaz"}), 400
        
        created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO posts (author, content, created_at) VALUES (?, ?, ?)", 
                 (session["username"], content, created_at))
        post_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "id": post_id,
            "author": session["username"],
            "content": content,
            "created_at": created_at,
            "likes_count": 0,
            "retweets_count": 0
        }), 201
    except Exception as e:
        print(f"Error create_post: {e}")
        return jsonify({"error": "Gonderme hatasi"}), 500

@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    try:
        if "username" not in session:
            return jsonify({"error": "Lutfen giris yap"}), 401
        
        current_user = session["username"]
        is_admin = current_user == ADMIN_USERNAME
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT author FROM posts WHERE id = ?", (post_id,))
        post = c.fetchone()
        
        if not post:
            return jsonify({"error": "Gonderi bulunamadi"}), 404
        
        # Sadece admin veya postun kendi yazarı silebilir
        if not is_admin and post["author"] != current_user:
            return jsonify({"error": "Yetkiniz yok"}), 403
        
        c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Error delete_post: {e}")
        return jsonify({"error": "Silme hatasi"}), 500

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    try:
        if "username" not in session:
            return jsonify({"error": "Lutfen giris yap"}), 401
        
        username = session["username"]
        created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
        if c.fetchone():
            c.execute("DELETE FROM likes WHERE user = ? AND post_id = ?", (username, post_id))
            c.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
            action = "unliked"
        else:
            c.execute("INSERT INTO likes (user, post_id, created_at) VALUES (?, ?, ?)", 
                     (username, post_id, created_at))
            c.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            action = "liked"
        
        c.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,))
        likes = c.fetchone()["likes_count"]
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "action": action, "likes_count": likes}), 200
    except Exception as e:
        print(f"Error like_post: {e}")
        return jsonify({"error": "Like hatasi"}), 500

@app.route("/retweet/<int:post_id>", methods=["POST"])
def retweet_post(post_id):
    try:
        if "username" not in session:
            return jsonify({"error": "Lutfen giris yap"}), 401
        
        username = session["username"]
        created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT id FROM retweets WHERE user = ? AND post_id = ?", (username, post_id))
        if c.fetchone():
            c.execute("DELETE FROM retweets WHERE user = ? AND post_id = ?", (username, post_id))
            c.execute("UPDATE posts SET retweets_count = retweets_count - 1 WHERE id = ?", (post_id,))
            action = "unretweeted"
        else:
            c.execute("INSERT INTO retweets (user, post_id, created_at) VALUES (?, ?, ?)", 
                     (username, post_id, created_at))
            c.execute("UPDATE posts SET retweets_count = retweets_count + 1 WHERE id = ?", (post_id,))
            action = "retweeted"
        
        c.execute("SELECT retweets_count FROM posts WHERE id = ?", (post_id,))
        retweets = c.fetchone()["retweets_count"]
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "action": action, "retweets_count": retweets}), 200
    except Exception as e:
        print(f"Error retweet_post: {e}")
        return jsonify({"error": "Retweet hatasi"}), 500

@app.route("/messages")
def messages():
    try:
        if "username" not in session:
            return redirect(url_for("home"))
        
        username = session["username"]
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""SELECT DISTINCT 
                     CASE WHEN sender = ? THEN recipient ELSE sender END as other_user
                     FROM messages
                     WHERE sender = ? OR recipient = ?
                     ORDER BY created_at DESC""", (username, username, username))
        conversations = c.fetchall()
        
        conn.close()
        
        return render_template("messages.html", conversations=conversations, current_user=username)
    except Exception as e:
        print(f"Error messages: {e}")
        return redirect(url_for("home"))

@app.route("/message/<username>")
def view_conversation(username):
    try:
        if "username" not in session:
            return redirect(url_for("home"))
        
        current_user = session["username"]
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""SELECT sender, recipient, content, created_at 
                     FROM messages
                     WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
                     ORDER BY created_at ASC""", 
                 (current_user, username, username, current_user))
        messages_list = c.fetchall()
        
        c.execute("UPDATE messages SET is_read = 1 WHERE recipient = ? AND sender = ?", 
                 (current_user, username))
        conn.commit()
        conn.close()
        
        return render_template("conversation.html", other_user=username, 
                             messages=messages_list, current_user=current_user)
    except Exception as e:
        print(f"Error view_conversation: {e}")
        return redirect(url_for("messages"))

@app.route("/send_message", methods=["POST"])
def send_message():
    try:
        if "username" not in session:
            return jsonify({"error": "Lutfen giris yap"}), 401
        
        sender = session["username"]
        recipient = request.form.get("recipient", "").strip()
        content = request.form.get("content", "").strip()
        
        if not recipient or not content:
            return jsonify({"error": "Alici ve mesaj bos olamaz"}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (recipient,))
        if not c.fetchone():
            return jsonify({"error": "Kullanici bulunamadi"}), 404
        
        created_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        c.execute("INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)", 
                 (sender, recipient, content, created_at))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "created_at": created_at}), 201
    except Exception as e:
        print(f"Error send_message: {e}")
        return jsonify({"error": "Mesaj gonderme hatasi"}), 500

@app.route("/profile/<username>")
def profile(username):
    try:
        if "username" not in session:
            return redirect(url_for("home"))
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT username, bio, followers_count, following_count, created_at FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if not user:
            return redirect(url_for("home"))
        
        c.execute("SELECT id, author, content, created_at, likes_count, retweets_count FROM posts WHERE author = ? ORDER BY id DESC", (username,))
        posts = c.fetchall()
        
        conn.close()
        
        current_user = session.get("username")
        
        return render_template("profile.html", user=user, posts=posts, current_user=current_user)
    except Exception as e:
        print(f"Error profile: {e}")
        return redirect(url_for("home"))

@app.errorhandler(404)
def not_found(e):
    return "Sayfa bulunamadi", 404

@app.errorhandler(500)
def server_error(e):
    return "Sunucu hatasi", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
