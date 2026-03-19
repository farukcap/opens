<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mekan</title>
    <style>
        :root {
            --bg: #f3f4f6; --surface: #ffffff; --primary: #0f1419; 
            --text-main: #111827; --text-light: #6b7280; --border: #e5e7eb; --blue-tick: #1d9bf0;
            --radius: 16px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui, -apple-system, sans-serif; }
        body { background: var(--bg); color: var(--text-main); }
        a { text-decoration: none; color: inherit; }
        button, input, textarea { outline: none; border: none; background: transparent; font-family: inherit; }
        
        /* GİRİŞ EKRANI */
        .auth-container { display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
        .auth-box { background: var(--surface); padding: 40px; border-radius: var(--radius); width: 100%; max-width: 400px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .input-box { width: 100%; padding: 15px; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 15px; font-size: 16px; background: #f9fafb; }
        .btn-black { background: var(--primary); color: white; width: 100%; padding: 15px; border-radius: 30px; font-size: 16px; font-weight: bold; cursor: pointer; }
        
        /* ANA DÜZEN */
        .layout { display: flex; max-width: 1200px; margin: 0 auto; min-height: 100vh; justify-content: center; }
        
        /* SOL MENÜ (DESKTOP) */
        .sidebar { width: 275px; padding: 20px; position: sticky; top: 0; height: 100vh; display: flex; flex-direction: column; border-right: 1px solid var(--border); }
        .logo { font-size: 28px; font-weight: 800; margin-bottom: 20px; padding: 10px; }
        .nav-item { display: flex; align-items: center; gap: 15px; font-size: 20px; padding: 12px; border-radius: 30px; margin-bottom: 5px; font-weight: 500; width: fit-content; }
        .nav-item:hover { background: rgba(0,0,0,0.05); }
        .nav-item.active { font-weight: bold; }
        .badge { background: #ef4444; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold; margin-left: 5px; }

        /* ORTA İÇERİK */
        .main { width: 100%; max-width: 600px; border-right: 1px solid var(--border); background: var(--surface); min-height: 100vh; padding-bottom: 60px; }
        .header { padding: 15px 20px; font-size: 20px; font-weight: bold; border-bottom: 1px solid var(--border); position: sticky; top: 0; background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); z-index: 10; }
        
        /* YENİ: GERÇEK HİKAYELER (STORIES) BÖLÜMÜ */
        .stories-bar { display: flex; gap: 15px; padding: 15px 20px; border-bottom: 1px solid var(--border); overflow-x: auto; scrollbar-width: none; }
        .stories-bar::-webkit-scrollbar { display: none; }
        .story-circle { display: flex; flex-direction: column; align-items: center; gap: 5px; cursor: pointer; flex-shrink: 0; }
        .story-img { width: 60px; height: 60px; border-radius: 50%; border: 3px solid var(--blue-tick); display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; color: white; background: #9ca3af; }
        .story-add { border: 3px dashed var(--border); background: var(--surface); color: var(--primary); }

        /* YENİ: YENİ KATILANLAR BÖLÜMÜ (ANA SAYFADA GÖRÜNÜR) */
        .new-users-bar { background: #f9fafb; padding: 15px 20px; border-bottom: 1px solid var(--border); }
        .new-users-title { font-size: 14px; font-weight: bold; color: var(--text-light); margin-bottom: 10px; }
        .new-users-list { display: flex; gap: 10px; overflow-x: auto; scrollbar-width: none; }
        .new-user-card { background: var(--surface); border: 1px solid var(--border); padding: 10px; border-radius: 12px; display: flex; align-items: center; gap: 10px; min-width: 150px; flex-shrink: 0; }

        /* POST GÖNDERME KUTUSU */
        .compose { padding: 20px; border-bottom: 1px solid var(--border); display: flex; gap: 15px; }
        .avatar { width: 44px; height: 44px; border-radius: 50%; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; flex-shrink: 0; }
        .compose-input { width: 100%; border: none; resize: none; font-size: 18px; min-height: 50px; }
        
        /* POST AKIŞI */
        .post { padding: 15px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 12px; cursor: pointer; }
        .post:hover { background: #f9fafb; }
        .svg-verified { width: 18px; height: 18px; color: var(--blue-tick); margin-left: 4px; vertical-align: -3px; }
        .post-img { max-width: 100%; border-radius: 16px; margin-top: 10px; border: 1px solid var(--border); }
        .post-actions { display: flex; justify-content: space-between; max-width: 400px; margin-top: 12px; color: var(--text-light); }
        .action { cursor: pointer; padding: 5px; }

        /* MOBİL ALT MENÜ (SADECE TELEFONDA GÖRÜNÜR) */
        .mobile-nav { display: none; position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); border-top: 1px solid var(--border); justify-content: space-around; padding: 12px 0; z-index: 100; padding-bottom: env(safe-area-inset-bottom); }
        .mobile-item { font-size: 24px; color: var(--text-light); position: relative; }
        .mobile-item.active { color: var(--primary); }

        /* KUSURSUZ DM (MODAL) EKRANI */
        .dm-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100vh; background: var(--surface); z-index: 200; display: none; flex-direction: column; }
        .dm-modal.active { display: flex; }
        .dm-header { padding: 15px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 15px; font-size: 18px; font-weight: bold; background: var(--surface); }
        .dm-messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; background: var(--bg); }
        .bubble { max-width: 80%; padding: 12px 16px; border-radius: 20px; font-size: 15px; line-height: 1.4; position: relative; }
        .bubble-me { align-self: flex-end; background: var(--blue-tick); color: white; border-bottom-right-radius: 4px; }
        .bubble-them { align-self: flex-start; background: var(--surface); color: var(--text-main); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
        .dm-input-area { padding: 15px; background: var(--surface); border-top: 1px solid var(--border); display: flex; gap: 10px; align-items: center; }
        .dm-input { flex: 1; background: #f3f4f6; border-radius: 24px; padding: 12px 20px; font-size: 15px; }

        /* Story Modal */
        .story-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100vh; background: rgba(0,0,0,0.9); z-index: 300; display: none; flex-direction: column; justify-content: center; align-items: center; color: white; }
        .story-modal.active { display: flex; }
        .story-content { font-size: 24px; text-align: center; padding: 20px; max-width: 80%; word-wrap: break-word; }

        @media (max-width: 768px) {
            .sidebar { display: none; }
            .mobile-nav { display: flex; }
            .main { border-right: none; border-left: none; }
        }
    </style>
</head>
<body>

{% if not current_user %}
<div class="auth-container">
    <div class="auth-box">
        <h1 style="font-size: 40px; font-weight: 800; margin-bottom: 30px;">Mekan</h1>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div style="color:#ef4444; margin-bottom:15px; font-weight:bold;">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form action="/login" method="POST">
            <input type="text" name="username" class="input-box" placeholder="Kullanıcı Adı" required>
            <input type="password" name="password" class="input-box" placeholder="Şifre" required>
            <button class="btn-black">Giriş Yap</button>
        </form>
        <div style="margin: 20px 0; color: var(--text-light); font-size: 14px;">veya yeni hesap oluştur</div>
        <form action="/register" method="POST">
            <input type="text" name="username" class="input-box" placeholder="Kullanıcı Adı" required>
            <input type="password" name="password" class="input-box" placeholder="Şifre" required>
            <button class="btn-black" style="background: white; color: black; border: 1px solid var(--border);">Kayıt Ol</button>
        </form>
    </div>
</div>
{% else %}

<div class="layout">
    
    <nav class="sidebar">
        <div class="logo">Mekan</div>
        <a href="/" class="nav-item {% if page == 'home' %}active{% endif %}">🏠 Anasayfa</a>
        <a href="/notifications" class="nav-item {% if page == 'notifications' %}active{% endif %}">
            🔔 Bildirimler <span class="badge" style="display:{% if unread_notifs > 0 %}flex{% else %}none{% endif %};">{{ unread_notifs }}</span>
        </a>
        <a href="/messages_page" class="nav-item {% if page in ['messages', 'chat'] %}active{% endif %}">💬 Mesajlar</a>
        <a href="/profile/{{ current_user }}" class="nav-item {% if page == 'profile' and profile_user['username'] == current_user %}active{% endif %}">👤 Profilim</a>
        
        <button class="btn-black" style="padding:15px; margin-top:20px;" onclick="document.getElementById('postInput').focus()">Gönder</button>
        
        <a href="/logout" class="nav-item" style="margin-top: auto; color: #ef4444;">🚪 Çıkış Yap</a>
    </nav>

    <main class="main">
        {% if page == "home" %}
        <div class="header">Anasayfa</div>
        
        <div class="stories-bar">
            <div class="story-circle" onclick="openStoryInput()">
                <div class="story-img story-add">+</div>
                <div style="font-size:12px; font-weight:bold;">Ekle</div>
            </div>
            {% for s in stories %}
            <div class="story-circle" onclick="viewStory('{{ s['author'] }}', '{{ s['content'] }}')">
                <div class="story-img" style="background:#1d9bf0;">{{ s['author'][0].upper() }}</div>
                <div style="font-size:12px; font-weight:bold; width:60px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:center;">{{ s['author'] }}</div>
            </div>
            {% endfor %}
        </div>

        {% if new_users %}
        <div class="new-users-bar">
            <div class="new-users-title">🌟 Aramıza Yeni Katılanlar</div>
            <div class="new-users-list">
                {% for u in new_users %}
                <a href="/profile/{{ u['username'] }}" class="new-user-card">
                    <div class="avatar" style="width:32px; height:32px; font-size:14px;">{{ u['username'][0].upper() }}</div>
                    <div style="font-weight:bold; font-size:14px;">{{ u['username'] }}</div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="compose">
            <div class="avatar">{{ current_user[0].upper() }}</div>
            <div style="flex:1;">
                <textarea id="postInput" class="compose-input" placeholder="Neler oluyor?"></textarea>
                <div style="text-align:right; border-top:1px solid var(--border); padding-top:10px; margin-top:10px;">
                    <button class="btn-black" style="width:auto; padding:8px 20px;" onclick="sendPost()">Paylaş</button>
                </div>
            </div>
        </div>
        
        <div id="feed">
            {% for post in posts %}
            <div class="post">
                <a href="/profile/{{ post[1] }}"><div class="avatar">{{ post[1][0].upper() }}</div></a>
                <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 5px;">
                        <b style="font-size: 15px;"><a href="/profile/{{ post[1] }}">{{ post[1] }}</a></b>
                        {% if post[5] == 1 %} <svg viewBox="0 0 24 24" class="svg-verified"><g><path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.918-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.51 1.5 12 1.5s-2.816.917-3.337 2.25c-.416-.165-.866-.25-1.336-.25-2.21 0-3.918 1.792-3.918 4 0 .495.084.965.238 1.4-1.273.65-2.148 2.02-2.148 3.6 0 1.46.758 2.75 1.887 3.42-.08.35-.127.71-.127 1.08 0 2.21 1.71 4 3.918 4 .542 0 1.058-.12 1.526-.34.57 1.23 1.8 2.08 3.23 2.08s2.66-.85 3.23-2.08c.468.22 1.984.34 1.526.34 2.21 0 3.918-1.79 3.918-4 0-.37-.048-.73-.127-1.08 1.128-.67 1.887-1.96 1.887-3.42zm-10.15 4.39l-3.39-3.26 1.34-1.39 1.99 1.92 4.41-4.7 1.39 1.3-5.74 6.13z" fill="currentColor"></path></g></svg>
                        {% endif %}
                        <span class="timestamp" data-time="{{ post[3] }}" style="color:var(--text-light); font-size:14px; margin-left:auto;"></span>
                    </div>
                    <div class="raw-content" style="font-size: 15px; line-height: 1.5; margin-bottom: 10px;">{{ post[2] }}</div>
                    <div class="post-actions">
                        <div class="action" onclick="actionPost('like', {{ post[0] }})">❤️ <span id="l-{{post[0]}}">{{ post[4] }}</span></div>
                        {% if current_user != post[1] %}
                        <div class="action" onclick="openChat('{{ post[1] }}')">💬 DM At</div>
                        {% endif %}
                        {% if current_user == post[1] or is_admin %}
                        <div class="action" style="color:#ef4444;" onclick="deletePost({{ post[0] }})">🗑️</div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if page == "profile" %}
        <div class="header">
            <a href="/" style="margin-right:20px;">←</a> 
            <span>{{ profile_user['username'] }}</span>
        </div>
        <div style="padding: 20px; border-bottom: 1px solid var(--border); text-align: center;">
            <div class="avatar" style="width:100px; height:100px; font-size:40px; margin: 0 auto 15px;">{{ profile_user['username'][0].upper() }}</div>
            <h2 style="display:flex; align-items:center; justify-content:center; gap:5px;">
                {{ profile_user['username'] }}
                {% if profile_user['is_verified'] == 1 %}
                <svg viewBox="0 0 24 24" class="svg-verified" style="width:22px; height:22px;"><g><path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.918-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.51 1.5 12 1.5s-2.816.917-3.337 2.25c-.416-.165-.866-.25-1.336-.25-2.21 0-3.918 1.792-3.918 4 0 .495.084.965.238 1.4-1.273.65-2.148 2.02-2.148 3.6 0 1.46.758 2.75 1.887 3.42-.08.35-.127.71-.127 1.08 0 2.21 1.71 4 3.918 4 .542 0 1.058-.12 1.526-.34.57 1.23 1.8 2.08 3.23 2.08s2.66-.85 3.23-2.08c.468.22 1.984.34 1.526.34 2.21 0 3.918-1.79 3.918-4 0-.37-.048-.73-.127-1.08 1.128-.67 1.887-1.96 1.887-3.42zm-10.15 4.39l-3.39-3.26 1.34-1.39 1.99 1.92 4.41-4.7 1.39 1.3-5.74 6.13z" fill="currentColor"></path></g></svg>
                {% endif %}
            </h2>
            <div style="color:var(--text-light);">@{{ profile_user['username'] }}</div>
            <p style="margin: 15px 0;">{{ profile_user['bio'] }}</p>
            
            <div style="display:flex; justify-content:center; gap:20px; margin-bottom: 20px;">
                <div><b>{{ following }}</b> <span style="color:var(--text-light);">Takip Edilen</span></div>
                <div><b>{{ followers }}</b> <span style="color:var(--text-light);">Takipçi</span></div>
                <div>👀 <span style="color:var(--text-light);">{{ profile_user['profile_views'] }} Ziyaret</span></div>
            </div>
            
            {% if current_user != profile_user['username'] %}
                <div style="display:flex; justify-content:center; gap:10px;">
                    <button class="btn-black" style="width:auto; padding:8px 20px;" onclick="toggleFollow('{{ profile_user['username'] }}')">
                        {% if is_following %}Takibi Bırak{% else %}Takip Et{% endif %}
                    </button>
                    <button class="btn-black" style="width:auto; padding:8px 20px; background:white; color:black; border:1px solid var(--border);" onclick="openChat('{{ profile_user['username'] }}')">✉️ Mesaj</button>
                </div>
            {% endif %}
        </div>
        
        {% for post in posts %}
        <div class="post">
            <div class="avatar">{{ post[1][0].upper() }}</div>
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 5px;">
                    <b style="font-size: 15px;">{{ post[1] }}</b>
                    <span class="timestamp" data-time="{{ post[3] }}" style="color:var(--text-light); font-size:14px; margin-left:auto;"></span>
                </div>
                <div class="raw-content" style="font-size: 15px; margin-bottom: 10px;">{{ post[2] }}</div>
            </div>
        </div>
        {% endfor %}
        {% endif %}

        {% if page == "messages" %}
        <div class="header">Mesajlar</div>
        {% if not chats %}<p style="text-align:center; padding:40px; color:var(--text-light);">Sohbetin yok.</p>{% endif %}
        {% for chat in chats %}
        <div class="post" style="align-items:center;" onclick="openChat('{{ chat['partner'] }}')">
            <div class="avatar">{{ chat['partner'][0].upper() }}</div>
            <div style="font-weight:bold; font-size:18px; display:flex; align-items:center;">
                {{ chat['partner'] }}
                {% if chat['is_verified'] == 1 %}<svg viewBox="0 0 24 24" class="svg-verified" style="margin-left:5px;"><g><path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.918-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.51 1.5 12 1.5s-2.816.917-3.337 2.25c-.416-.165-.866-.25-1.336-.25-2.21 0-3.918 1.792-3.918 4 0 .495.084.965.238 1.4-1.273.65-2.148 2.02-2.148 3.6 0 1.46.758 2.75 1.887 3.42-.08.35-.127.71-.127 1.08 0 2.21 1.71 4 3.918 4 .542 0 1.058-.12 1.526-.34.57 1.23 1.8 2.08 3.23 2.08s2.66-.85 3.23-2.08c.468.22 1.984.34 1.526.34 2.21 0 3.918-1.79 3.918-4 0-.37-.048-.73-.127-1.08 1.128-.67 1.887-1.96 1.887-3.42zm-10.15 4.39l-3.39-3.26 1.34-1.39 1.99 1.92 4.41-4.7 1.39 1.3-5.74 6.13z" fill="currentColor"></path></g></svg>{% endif %}
            </div>
        </div>
        {% endfor %}
        {% endif %}

        {% if page == "notifications" %}
        <div class="header">Bildirimler</div>
        {% for n in notifs %}
        <div class="post" style="align-items:center;">
            <div style="font-size:24px;">{% if n['type']=='like' %}❤️{% elif n['type']=='follow' %}👤{% else %}✉️{% endif %}</div>
            <div>
                <b><a href="/profile/{{ n['sender'] }}">{{ n['sender'] }}</a></b> 
                {% if n['type']=='like' %} gönderini beğendi.
                {% elif n['type']=='follow' %} seni takip etmeye başladı.
                {% else %} sana mesaj gönderdi.{% endif %}
                <div class="timestamp" data-time="{{ n['created_at'] }}" style="font-size:12px; color:var(--text-light); margin-top:5px;"></div>
            </div>
        </div>
        {% endfor %}
        {% endif %}
    </main>

    <nav class="mobile-nav">
        <a href="/" class="mobile-item {% if page == 'home' %}active{% endif %}">🏠</a>
        <a href="/notifications" class="mobile-item {% if page == 'notifications' %}active{% endif %}">🔔{% if unread_notifs > 0 %}<span style="position:absolute; top:-5px; right:-10px; background:#ef4444; color:white; border-radius:50%; width:16px; height:16px; font-size:10px; display:flex; align-items:center; justify-content:center;">{{ unread_notifs }}</span>{% endif %}</a>
        <a href="/messages_page" class="mobile-item {% if page in ['messages', 'chat'] %}active{% endif %}">💬</a>
        <a href="/profile/{{ current_user }}" class="mobile-item {% if page == 'profile' %}active{% endif %}">👤</a>
    </nav>
</div>

<div class="story-modal" id="storyModal">
    <div style="position:absolute; top:20px; right:20px; font-size:30px; cursor:pointer;" onclick="closeStory()">✖</div>
    <textarea id="storyInput" placeholder="Bugün nasılsın?" style="width:80%; height:150px; font-size:30px; color:white; text-align:center; resize:none;"></textarea>
    <button class="btn-black" style="width:auto; padding:15px 40px; margin-top:20px; background:white; color:black;" onclick="sendStory()">Hikaye Ekle</button>
</div>

<div class="story-modal" id="viewStoryModal" onclick="closeStory()">
    <div style="font-weight:bold; position:absolute; top:40px; font-size:20px;" id="vsAuthor"></div>
    <div class="story-content" id="vsContent"></div>
</div>

<div class="dm-modal" id="dmModal">
    <div class="dm-header">
        <div style="cursor: pointer; padding: 5px; font-size: 24px;" onclick="closeChat()">←</div>
        <div class="avatar" style="width:36px; height:36px; font-size:14px;" id="chatAvatar"></div>
        <div id="chatTitle"></div>
    </div>
    <div class="dm-messages" id="chatBox"></div>
    <div class="dm-input-area">
        <input type="text" id="msgInput" class="dm-input" placeholder="Bir mesaj yaz..." onkeypress="if(event.key==='Enter') sendMsg()">
        <button class="btn-black" style="width:auto; padding:12px 20px;" onclick="sendMsg()">Gönder</button>
    </div>
</div>

<script>
    function formatTime(dateStr) {
        if(!dateStr) return '';
        const postDate = new Date(dateStr.replace(' ', 'T'));
        const diff = Math.floor((new Date() - postDate) / 1000);
        if(diff < 60) return "Az önce";
        if(diff < 3600) return Math.floor(diff/60) + " dk önce";
        if(diff < 86400) return Math.floor(diff/3600) + " saat önce";
        return Math.floor(diff/86400) + " gün önce";
    }

    function formatContent(text) {
        text = text.replace(/#(\w+)/g, '<span style="color:var(--blue-tick);">#$1</span>');
        text = text.replace(/(https?:\/\/[^\s]+?\.(?:jpg|jpeg|png|gif))/ig, '<br><img src="$1" class="post-img"><br>');
        return text;
    }
    
    document.querySelectorAll('.timestamp').forEach(el => el.textContent = formatTime(el.getAttribute('data-time')));
    document.querySelectorAll('.raw-content').forEach(el => el.innerHTML = formatContent(el.textContent));

    // --- HİKAYE (STORY) FONKSİYONLARI ---
    function openStoryInput() { document.getElementById('storyModal').classList.add('active'); }
    function closeStory() { 
        document.getElementById('storyModal').classList.remove('active'); 
        document.getElementById('viewStoryModal').classList.remove('active'); 
    }
    function viewStory(author, content) {
        document.getElementById('vsAuthor').textContent = author;
        document.getElementById('vsContent').textContent = content;
        document.getElementById('viewStoryModal').classList.add('active');
    }
    async function sendStory() {
        const val = document.getElementById('storyInput').value.trim();
        if(!val) return;
        const fd = new FormData(); fd.append("content", val);
        const res = await fetch("/api/post_story", { method: "POST", body: fd });
        if(res.ok) window.location.reload();
    }

    // --- AKSİYONLAR ---
    async function sendPost() {
        const val = document.getElementById('postInput').value.trim();
        if(!val) return;
        const fd = new FormData(); fd.append("content", val);
        const res = await fetch("/api/post", { method: "POST", body: fd });
        if(res.ok) window.location.reload();
    }

    async function actionPost(type, id) {
        const res = await fetch(`/api/like/${id}`, {method:"POST"});
        const data = await res.json();
        if(data.success) document.getElementById(`l-${id}`).textContent = data.count;
    }

    async function deletePost(id) {
        if(!confirm("Silinsin mi?")) return;
        await fetch(`/api/delete/${id}`, {method:"POST"}); window.location.reload();
    }
    
    async function toggleFollow(username) {
        await fetch(`/api/follow/${username}`, {method:"POST"}); window.location.reload();
    }

    // --- DM KUTUSU (TAM ÇALIŞAN SÜRÜM) ---
    const dmModal = document.getElementById('dmModal');
    const chatBox = document.getElementById('chatBox');
    let chatInterval = null;
    let currentPartner = "";
    let lastMsgs = 0;

    function openChat(partner) {
        currentPartner = partner;
        document.getElementById('chatTitle').innerHTML = partner;
        document.getElementById('chatAvatar').textContent = partner[0].toUpperCase();
        dmModal.classList.add('active');
        lastMsgs = 0;
        chatBox.innerHTML = '<div style="text-align:center; color:var(--text-light); margin-top:20px;">Bağlanıyor...</div>';
        
        loadChat();
        chatInterval = setInterval(loadChat, 1500);
    }

    function closeChat() {
        dmModal.classList.remove('active');
        clearInterval(chatInterval);
    }

    async function loadChat() {
        if(!currentPartner) return;
        const res = await fetch(`/api/chat/${currentPartner}`);
        const msgs = await res.json();

        if (msgs.length !== lastMsgs) {
            chatBox.innerHTML = '';
            if(msgs.length === 0) chatBox.innerHTML = '<div style="text-align:center; color:var(--text-light); margin-top:20px;">İlk mesajı sen at!</div>';
            
            msgs.forEach(m => {
                const isMe = m.sender === '{{ current_user }}';
                const cls = isMe ? 'bubble-me' : 'bubble-them';
                const tOnly = m.created_at.split(' ')[1].substring(0, 5);
                const ticks = isMe ? (m.is_read ? '<span style="color:#a7f3d0; margin-left:5px;">✓✓</span>' : '<span style="margin-left:5px;">✓</span>') : '';
                
                chatBox.innerHTML += `<div class="bubble ${cls}">${m.content}<div style="font-size:10px; text-align:right; margin-top:5px; opacity:0.8;">${tOnly} ${ticks}</div></div>`;
            });
            chatBox.scrollTop = chatBox.scrollHeight;
            lastMsgs = msgs.length;
        }
    }

    async function sendMsg() {
        const val = document.getElementById('msgInput').value.trim();
        if(!val) return;
        const fd = new FormData(); fd.append("content", val);
        await fetch(`/api/chat/${currentPartner}`, { method: "POST", body: fd });
        document.getElementById('msgInput').value = '';
        loadChat(); 
    }
</script>
{% endif %}
</body>
</html>
