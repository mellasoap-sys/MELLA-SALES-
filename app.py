"""
MELLA SOAP AND DETERGENT MANUFACTURING - Sales Tracker (Streamlit)
Files needed in the repository:  app.py, logo.png, requirements.txt, .streamlit/config.toml
Default logins (change them after first login):
  executive / exec123   factory / factory123   finance / finance123   rep1 / rep123
"""
import base64
import hashlib
import html
import os
import secrets
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def find_logo():
    """logo.png, or any image in the app folder with 'logo' (or 'mella') in its name."""
    exact = os.path.join(APP_DIR, "logo.png")
    if os.path.exists(exact):
        return exact
    try:
        for fn in sorted(os.listdir(APP_DIR)):
            low = fn.lower()
            if low.endswith((".png", ".jpg", ".jpeg", ".webp")) and ("logo" in low or "mella" in low):
                return os.path.join(APP_DIR, fn)
    except OSError:
        pass
    return ""


LOGO = find_logo()
DB = os.environ.get("SALES_DB", os.path.join(APP_DIR, "sales_tracker.db"))
BANKS = ["Hibret", "Wegagen", "Coop", "CBE", "Awash", "Dashen", "Abyssinia", "Other"]
PRODUCTS = ["Big", "Small"]
ROLES = ["rep", "factory", "finance", "executive"]
CO_EN = "MELLA SOAP AND DETERGENT MANUFACTURING"
CO_AM = "መላ ሳሙና እና ዲተርጀንት ማምረቻ"
ROLE_LBL = {
    "rep": ("Sales Representative", "ሴልስ ሪፕሬዘንታቲቭ"),
    "factory": ("Factory", "ፋብሪካ"),
    "finance": ("Finance", "ፋይናንስ"),
    "executive": ("Executive", "ኤክስኪዩቲቭ"),
}

try:
    from PIL import Image
    _icon = Image.open(LOGO) if LOGO else None
except Exception:
    _icon = None
st.set_page_config(page_title="MELLA Sales", page_icon=_icon, layout="wide")

# ----------------------------------------------------------------- language
TXT = {
    "login": ("Sign in", "ግባ"),
    "login_sub": ("Welcome back. Please sign in to continue.", "እንኳን ደህና መጡ። ለመቀጠል ይግቡ።"),
    "tagline": ("Daily sales, balances and payments - in one clean place.",
                "የዕለት ሽያጭ፣ ባላንስና ክፍያ - በአንድ ንጹህ ቦታ።"),
    "hello": ("Welcome back", "እንኳን ደህና መጡ"),
    "username": ("Username", "የተጠቃሚ ስም"),
    "password": ("Password", "የይለፍ ቃል"),
    "bad_login": ("Wrong username or password", "የተጠቃሚ ስም ወይም የይለፍ ቃል ስህተት ነው"),
    "logout": ("Logout", "ውጣ"),
    "language": ("Language", "ቋንቋ"),
    "date": ("Date", "ቀን"),
    "rep": ("Sales rep", "ሴልስ ሪፕ"),
    "big": ("Big (200g)", "ቢግ (200ግ)"),
    "small": ("Small (100g)", "ስሞል (100ግ)"),
    "load_no": ("Load no.", "የጭነት ቁጥር"),
    "save": ("Save", "አስቀምጥ"),
    "saved": ("Saved ✔", "ተቀምጧል ✔"),
    "delete": ("Delete selected", "የተመረጠውን ሰርዝ"),
    "dispatch_new": ("Record a dispatch", "የተላከ ምርት መዝግብ"),
    "dispatch_list": ("Dispatch records", "የተላኩ ምርቶች ዝርዝር"),
    "dispatch": ("Factory dispatch", "ከፋብሪካ የተላከ ምርት"),
    "entry": ("Daily entry", "የዕለት ምዝገባ"),
    "history": ("My history", "ታሪኬ"),
    "received_loads": ("Goods received", "የተረከብኩት ምርት"),
    "received_hint": ("Each row is one load (1st, 2nd, 3rd...). Add as many rows as you received.",
                      "እያንዳንዱ ረድፍ አንድ ጭነት ነው (1ኛ፣ 2ኛ፣ 3ኛ...)። የተረከቡትን ያህል ረድፍ ይጨምሩ።"),
    "loads": ("Loads", "ጭነቶች"),
    "total_big": ("Total Big", "ጠቅላላ ቢግ"),
    "total_small": ("Total Small", "ጠቅላላ ስሞል"),
    "sales": ("Sales (quantity x price)", "ሽያጭ (ብዛት x ዋጋ)"),
    "sales_hint": ("Add a row for each price. Use the Note column for names like \"wossen\".",
                   "ለእያንዳንዱ ዋጋ አንድ ረድፍ ጨምሩ። በ \"ማስታወሻ\" ዓምድ እንደ \"ወሰን\" ያሉ ስሞችን ይጻፉ።"),
    "product": ("Product", "ምርት"),
    "note": ("Note (e.g. wossen)", "ማስታወሻ (ለምሳሌ ወሰን)"),
    "qty": ("Quantity", "ብዛት"),
    "price": ("Unit price", "የአንዱ ዋጋ"),
    "bank": ("Bank", "ባንክ"),
    "bank_other": ("If Other, write bank name", "ሌላ ከሆነ የባንኩን ስም ይጻፉ"),
    "paid_for": ("Deposited for / by", "ለማን / ማን አስገባ"),
    "amount": ("Amount", "መጠን"),
    "payments": ("Payments / bank deposits", "ክፍያዎች / የባንክ ገቢዎች"),
    "beginning": ("Beginning balance", "የቀድሞ ባላንስ"),
    "sales_total": ("+ Sales", "+ ሽያጭ"),
    "pay_total": ("- Payments", "- ክፍያ"),
    "final": ("= Remaining balance", "= ቀሪ ባላንስ"),
    "sold_vs_recv": ("Sold quantity differs from received quantity",
                     "የተሸጠው ብዛት ከተረከበው ጋር አይመሳሰልም"),
    "exec": ("Executive dashboard", "ኤክስኪዩቲቭ ዳሽቦርድ"),
    "fin": ("Finance dashboard", "ፋይናንስ ዳሽቦርድ"),
    "from": ("From", "ከ"),
    "to": ("To", "እስከ"),
    "all": ("All", "ሁሉም"),
    "total_sales": ("Total sales", "ጠቅላላ ሽያጭ"),
    "total_pay": ("Total payments", "ጠቅላላ ክፍያ"),
    "outstanding": ("Outstanding balance", "ጠቅላላ ቀሪ ባላንስ"),
    "issues": ("Loads with differences", "ልዩነት ያለባቸው ጭነቶች"),
    "per_rep": ("Per sales rep", "በሴልስ ሪፕ"),
    "sales_by_day": ("Sales by day", "የዕለት ሽያጭ"),
    "breakdown": ("Sales breakdown", "የሽያጭ ዝርዝር"),
    "pay_by_bank": ("Payments by bank", "ክፍያ በባንክ"),
    "recon": ("Reconciliation (factory vs rep)", "ሪኮንሲሊሽን (ፋብሪካ ከሪፕ ጋር)"),
    "status": ("Status", "ሁኔታ"),
    "factory_big": ("Factory Big", "ፋብሪካ ቢግ"),
    "rep_big": ("Rep Big", "ሪፕ ቢግ"),
    "factory_small": ("Factory Small", "ፋብሪካ ስሞል"),
    "rep_small": ("Rep Small", "ሪፕ ስሞል"),
    "diff_big": ("Diff Big", "የቢግ ልዩነት"),
    "diff_small": ("Diff Small", "የስሞል ልዩነት"),
    "opening": ("Opening balances", "የመጀመሪያ ባላንስ"),
    "opening_hint": ("Balance carried forward; counted from the start date.",
                     "ከቀድሞ የዞረ ባላንስ፤ ከመነሻ ቀን ጀምሮ ይቆጠራል።"),
    "start_date": ("Start date", "መነሻ ቀን"),
    "users": ("Users", "ተጠቃሚዎች"),
    "new_user": ("Add / reset user", "ተጠቃሚ ጨምር / የይለፍ ቃል ቀይር"),
    "full_name": ("Full name", "ሙሉ ስም"),
    "role": ("Role", "ሚና"),
    "download": ("Download CSV", "CSV አውርድ"),
    "no_data": ("No data", "መረጃ የለም"),
    "nav": ("Menu", "ምናሌ"),
    "chpw": ("Change password", "የይለፍ ቃል ቀይር"),
    "old_pw": ("Current password", "የአሁኑ የይለፍ ቃል"),
    "new_pw": ("New password", "አዲስ የይለፍ ቃል"),
    "new_pw2": ("Repeat new password", "አዲሱን የይለፍ ቃል ድገም"),
    "pw_wrong": ("Current password is wrong", "የአሁኑ የይለፍ ቃል ስህተት ነው"),
    "pw_mismatch": ("New passwords do not match", "አዲሶቹ የይለፍ ቃሎች አይመሳሰሉም"),
    "pw_short": ("Password must be at least 6 characters", "የይለፍ ቃል ቢያንስ 6 ቁምፊ መሆን አለበት"),
    "pw_same": ("New password must be different", "አዲሱ የይለፍ ቃል ከአሁኑ የተለየ መሆን አለበት"),
    "pw_done": ("Password changed ✔", "የይለፍ ቃል ተቀይሯል ✔"),
}


def T(key):
    return TXT[key][1 if st.session_state.get("lang") == "አማርኛ" else 0]


def money(x):
    return f"{x:,.0f}"


# ------------------------------------------------------------------- design
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Ethiopic:wght@400;500;600;700;800&display=swap');
:root{--blue:#0A5FD0;--blue2:#2B8CFF;--navy:#0B2545;--sky:#EAF3FF;--line:#D6E4FA;--muted:#5B6B86}
.stApp{background:radial-gradient(900px 420px at 100% -5%,#D9E9FF 0%,rgba(217,233,255,0) 70%),linear-gradient(180deg,#F4F8FF 0%,#FFFFFF 55%);color:var(--navy)}
.stApp,.stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp input,.stApp textarea,.stApp button,.stApp li,.stApp td,.stApp th{font-family:'Plus Jakarta Sans','Noto Sans Ethiopic',sans-serif !important}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu{display:none !important}
.block-container{padding-top:1.2rem;padding-bottom:4rem;max-width:1180px}

.hero{position:relative;overflow:hidden;border-radius:24px;padding:26px 30px;margin-bottom:22px;background:linear-gradient(120deg,#0B3C8C 0%,#0A5FD0 55%,#3B9BFF 100%);color:#fff;display:flex;justify-content:space-between;align-items:flex-end;gap:16px;box-shadow:0 18px 40px rgba(10,95,208,.25)}
.hero-in{position:relative;z-index:2}
.hero-sub{font-size:.9rem;opacity:.88;font-weight:600}
.hero-title{font-size:1.9rem;font-weight:800;line-height:1.25;margin-top:4px}
.hero-chip{position:relative;z-index:2;text-align:right;font-size:.8rem;font-weight:600;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);padding:8px 14px;border-radius:14px;line-height:1.5}
.hb,.bub{position:absolute;border-radius:50%;border:2px solid rgba(255,255,255,.35);background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.4),rgba(255,255,255,.03))}
.hb.b1{width:130px;height:130px;right:18%;top:-45px}.hb.b2{width:64px;height:64px;right:5%;bottom:-20px}.hb.b3{width:38px;height:38px;right:32%;bottom:12px}

.sec{margin:24px 0 10px}
.sec-t{font-size:1.05rem;font-weight:800;color:var(--navy);display:flex;align-items:center;gap:10px}
.sec-t:before{content:"";width:6px;height:18px;border-radius:4px;background:linear-gradient(180deg,var(--blue2),var(--blue))}
.sec-h{font-size:.82rem;color:var(--muted);margin:3px 0 0 16px}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:8px 0 18px}
.kpi{position:relative;overflow:hidden;background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px 18px 16px 22px;box-shadow:0 8px 22px rgba(10,95,208,.07)}
.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;background:linear-gradient(180deg,#7CB9FF,#0A5FD0)}
.kpi .l{font-size:.78rem;color:var(--muted);font-weight:700;letter-spacing:.02em}
.kpi .v{font-size:1.5rem;font-weight:800;color:var(--navy);margin-top:4px;word-break:break-word}
.kpi.primary{background:linear-gradient(135deg,#0A5FD0,#0B3C8C);border:none;box-shadow:0 14px 30px rgba(10,95,208,.28)}
.kpi.primary:before{background:rgba(255,255,255,.35)}
.kpi.primary .l{color:rgba(255,255,255,.82)}.kpi.primary .v{color:#fff}
.kpi.warn:before{background:linear-gradient(180deg,#FFC46B,#F08A00)}

div[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:0 10px 30px rgba(10,95,208,.08)}
div[data-baseweb="input"],div[data-baseweb="base-input"],div[data-baseweb="select"]>div{border-radius:12px !important}
div[data-testid="stDataFrame"],div[data-testid="stDataEditor"]{border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 6px 20px rgba(10,95,208,.06)}
div[data-testid="stAlert"]{border-radius:14px}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700;border:1px solid var(--line);padding:.5rem 1.2rem;transition:all .15s ease}
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(10,95,208,.18);border-color:var(--blue)}
button[kind="primary"],button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"]{background:linear-gradient(135deg,#2B8CFF,#0A5FD0) !important;color:#fff !important;border:none !important}

section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0A2A5E 0%,#0B4DB5 100%)}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] span,section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"]{color:#fff}
section[data-testid="stSidebar"] .logo-card{display:block;text-align:center;margin-bottom:6px}
section[data-testid="stSidebar"] .logo-card img{height:58px;margin:0 auto}
.co-s{font-size:.66rem;font-weight:700;letter-spacing:.08em;opacity:.8;text-align:center;line-height:1.5;margin:8px 0 14px;color:#fff}
.uchip{display:flex;align-items:center;gap:12px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);border-radius:16px;padding:10px 12px;margin-bottom:18px}
.av{width:38px;height:38px;border-radius:12px;background:#fff;color:#0A5FD0 !important;display:flex;align-items:center;justify-content:center;font-weight:800}
.un{font-weight:700;font-size:.92rem;color:#fff}.ur{font-size:.74rem;opacity:.8;color:#fff}
section[data-testid="stSidebar"] label[data-baseweb="radio"]>div:first-child{display:none}
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:6px}
section[data-testid="stSidebar"] label[data-baseweb="radio"]{width:100%;padding:10px 14px;border-radius:12px;background:rgba(255,255,255,.07);transition:background .15s}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{background:rgba(255,255,255,.18)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){background:#fff}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p{color:#0A3A8C !important;font-weight:800}
section[data-testid="stSidebar"] .stButton>button{width:100%;background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.3)}

.logo-card{background:#fff;border-radius:18px;padding:10px 16px;display:inline-block;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.logo-card img{display:block;height:64px;width:auto}
.login-hero{position:relative;overflow:hidden;min-height:540px;border-radius:28px;padding:38px;background:linear-gradient(150deg,#0A2A5E 0%,#0A5FD0 60%,#3B9BFF 100%);color:#fff;display:flex;flex-direction:column;justify-content:center;gap:14px;box-shadow:0 24px 50px rgba(10,95,208,.3)}
.login-hero .logo-card{align-self:flex-start}.login-hero .logo-card img{height:120px}
.lh-in{position:relative;z-index:2;display:flex;flex-direction:column;gap:14px}
.co-en{font-size:1.2rem;font-weight:800;letter-spacing:.05em;line-height:1.35}
.co-am{font-size:1.15rem;font-weight:600;opacity:.95}
.tag{opacity:.85;font-size:.95rem;margin-top:4px;max-width:420px}
.bub{animation:floaty 9s ease-in-out infinite}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-22px)}}
.login-t{font-size:1.8rem;font-weight:800;color:var(--navy);margin:34px 0 2px}
.login-s{color:var(--muted);margin-bottom:16px}

.st-key-topbar,.st-key-loginbar{margin-bottom:10px}
.st-key-topbar{background:#fff;border:1px solid var(--line);border-radius:18px;padding:8px 14px;box-shadow:0 8px 22px rgba(10,95,208,.08)}
.st-key-topbar div[data-testid="stHorizontalBlock"],.st-key-loginbar div[data-testid="stHorizontalBlock"]{flex-direction:row !important;flex-wrap:nowrap !important;align-items:center;gap:.5rem}
.st-key-topbar div[data-testid="stColumn"],.st-key-loginbar div[data-testid="stColumn"]{min-width:0 !important}
.st-key-topbar .logo-card{background:transparent;box-shadow:none;padding:0;border-radius:0}
.st-key-topbar .logo-card img{height:40px}
.st-key-topbar .stButton>button,.st-key-loginbar .stButton>button{width:100%;padding:.45rem .5rem;font-size:.85rem;white-space:nowrap}
.st-key-nav div[role="radiogroup"]{flex-direction:row !important;flex-wrap:nowrap !important;overflow-x:auto;gap:8px;padding:4px 2px 12px;scrollbar-width:none}
.st-key-nav div[role="radiogroup"]::-webkit-scrollbar{display:none}
.st-key-nav label[data-baseweb="radio"]{flex:0 0 auto;padding:9px 18px;border-radius:999px;background:#fff;border:1px solid var(--line);box-shadow:0 4px 12px rgba(10,95,208,.07);cursor:pointer}
.st-key-nav label[data-baseweb="radio"]>div:first-child{display:none}
.st-key-nav label[data-baseweb="radio"] p{white-space:nowrap;font-weight:700;color:var(--navy)}
.st-key-nav label[data-baseweb="radio"]:has(input:checked){background:linear-gradient(135deg,#2B8CFF,#0A5FD0);border-color:transparent;box-shadow:0 8px 18px rgba(10,95,208,.3)}
.st-key-nav label[data-baseweb="radio"]:has(input:checked) p{color:#fff !important;font-weight:800}

@media(max-width:640px){
.block-container{padding-left:.9rem;padding-right:.9rem}
.hero{flex-direction:column;align-items:flex-start;padding:20px}
.hero-title{font-size:1.45rem}.hero-chip{text-align:left}
.login-hero{min-height:360px;padding:24px}.login-hero .logo-card img{height:84px}
.kpi .v{font-size:1.25rem}.login-t{margin-top:12px}
}
"""


@st.cache_data
def logo_b64():
    """Logo as base64 PNG, shrunk to a web-friendly size."""
    if not LOGO:
        return ""
    try:
        import io
        from PIL import Image
        im = Image.open(LOGO).convert("RGBA")
        im.thumbnail((520, 520))
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def logo_html():
    b = logo_b64()
    if b:
        return '<div class="logo-card"><img src="data:image/png;base64,' + b + '" alt="MELLA"/></div>'
    return '<div class="logo-card"><b style="color:#0A5FD0;font-size:1.6rem">MELLA</b></div>'


def esc(s):
    return html.escape(str(s))


def sec(title, hint=""):
    h = '<div class="sec"><div class="sec-t">' + title + "</div>"
    if hint:
        h += '<div class="sec-h">' + hint + "</div>"
    st.markdown(h + "</div>", unsafe_allow_html=True)


def kpis(items):
    h = '<div class="kpis">'
    for label, value, kind in items:
        h += '<div class="kpi ' + kind + '"><div class="l">' + label + '</div><div class="v">' + str(value) + "</div></div>"
    st.markdown(h + "</div>", unsafe_allow_html=True)


def hero(user, title):
    lang = 1 if st.session_state.get("lang") == "አማርኛ" else 0
    role = ROLE_LBL[user["role"]][lang]
    today = date.today().strftime("%d %b %Y")
    st.markdown(
        '<div class="hero"><div class="hb b1"></div><div class="hb b2"></div><div class="hb b3"></div>'
        '<div class="hero-in"><div class="hero-sub">' + T("hello") + ", " + esc(user["name"]) + "</div>"
        '<div class="hero-title">' + title + "</div></div>"
        '<div class="hero-chip">' + role + "<br>" + today + "</div></div>",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- database
def conn():
    c = sqlite3.connect(DB)
    c.execute("PRAGMA foreign_keys=ON")
    return c


def q(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def run(sql, params=()):
    with conn() as c:
        c.execute(sql, params)


def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000).hex()


def upsert_user(username, name, role, pw):
    salt = secrets.token_hex(16)
    run(
        "INSERT INTO users(username,name,role,salt,pw_hash) VALUES(?,?,?,?,?) "
        "ON CONFLICT(username) DO UPDATE SET name=excluded.name, role=excluded.role, "
        "salt=excluded.salt, pw_hash=excluded.pw_hash",
        (username, name, role, salt, hash_pw(pw, salt)),
    )


@st.cache_resource
def init_db():
    with conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, name TEXT, role TEXT, salt TEXT, pw_hash TEXT);
            CREATE TABLE IF NOT EXISTS dispatch(id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, rep TEXT, load_no INTEGER, big INTEGER, small INTEGER);
            CREATE TABLE IF NOT EXISTS received(d TEXT, rep TEXT, big INTEGER, small INTEGER, PRIMARY KEY(d, rep));
            CREATE TABLE IF NOT EXISTS received_loads(d TEXT, rep TEXT, load_no INTEGER, big INTEGER, small INTEGER, PRIMARY KEY(d, rep, load_no));
            CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, rep TEXT, product TEXT, qty INTEGER, price REAL);
            CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, rep TEXT, bank TEXT, paid_for TEXT, amount REAL);
            CREATE TABLE IF NOT EXISTS opening(rep TEXT PRIMARY KEY, amount REAL, as_of TEXT);
            """
        )
        cols = [r[1] for r in c.execute("PRAGMA table_info(sales)")]
        if "note" not in cols:
            c.execute("ALTER TABLE sales ADD COLUMN note TEXT DEFAULT ''")
        if c.execute("SELECT COUNT(*) FROM received_loads").fetchone()[0] == 0:
            c.execute("INSERT OR IGNORE INTO received_loads SELECT d, rep, 1, big, small FROM received")
    if q("SELECT COUNT(*) n FROM users").n[0] == 0:
        upsert_user("executive", "Executive", "executive", "exec123")
        upsert_user("factory", "Factory", "factory", "factory123")
        upsert_user("finance", "Finance", "finance", "finance123")
        upsert_user("rep1", "Sales Rep 1", "rep", "rep123")
    return True


def reps_df():
    return q("SELECT username, name FROM users WHERE role='rep' ORDER BY name")


def name_map():
    u = q("SELECT username, name FROM users")
    return dict(zip(u.username, u.name))


def opening_of(rep):
    r = q("SELECT amount, as_of FROM opening WHERE rep=?", (rep,))
    if r.empty:
        return 0.0, "0000-01-01"
    return float(r.amount[0]), r.as_of[0]


def balance(rep, d_end, inclusive=True):
    """Opening + sales - payments from the opening start date up to d_end."""
    amt, start = opening_of(rep)
    op = "<=" if inclusive else "<"
    s = q(f"SELECT COALESCE(SUM(qty*price),0) v FROM sales WHERE rep=? AND d>=? AND d{op}?", (rep, start, d_end)).v[0]
    p = q(f"SELECT COALESCE(SUM(amount),0) v FROM payments WHERE rep=? AND d>=? AND d{op}?", (rep, start, d_end)).v[0]
    return amt + s - p


def recon_df(d1, d2, rep=None):
    """Factory dispatch vs rep received, load by load."""
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    a = q(f"SELECT d, rep, load_no, SUM(big) big_s, SUM(small) small_s FROM dispatch WHERE d BETWEEN ? AND ?{f} GROUP BY d, rep, load_no", p)
    b = q(f"SELECT d, rep, load_no, SUM(big) big_r, SUM(small) small_r FROM received_loads WHERE d BETWEEN ? AND ?{f} GROUP BY d, rep, load_no", p)
    a["load_no"] = a["load_no"].astype("int64")
    b["load_no"] = b["load_no"].astype("int64")
    m = a.merge(b, on=["d", "rep", "load_no"], how="outer")
    if m.empty:
        return m
    nums = ["big_s", "small_s", "big_r", "small_r"]
    m[nums] = m[nums].fillna(0).astype(float)
    m["diff_big"] = m.big_r - m.big_s
    m["diff_small"] = m.small_r - m.small_s
    m["status"] = ["✅" if (x == 0 and y == 0) else "⚠️" for x, y in zip(m.diff_big, m.diff_small)]
    return m.sort_values(["d", "rep", "load_no"], ascending=[False, True, True])


# --------------------------------------------------------------------- login
def toggle_lang():
    st.session_state["lang"] = "English" if st.session_state.get("lang") == "አማርኛ" else "አማርኛ"


def lang_button(key):
    label = "English" if st.session_state.get("lang") == "አማርኛ" else "አማርኛ"
    st.button(label, key=key, on_click=toggle_lang)


def do_logout():
    st.session_state.pop("user", None)
    st.session_state.pop("nav_choice", None)


def login_screen():
    bubbles = (
        '<div class="bub" style="width:150px;height:150px;right:-30px;top:-40px"></div>'
        '<div class="bub" style="width:70px;height:70px;right:22%;bottom:60px;animation-delay:-3s"></div>'
        '<div class="bub" style="width:36px;height:36px;right:12%;top:46%;animation-delay:-6s"></div>'
        '<div class="bub" style="width:100px;height:100px;left:-30px;bottom:-30px;animation-delay:-2s"></div>'
    )
    with st.container(key="loginbar"):
        _, lc = st.columns([3, 1], vertical_alignment="center")
        with lc:
            lang_button("lang_login")
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            '<div class="login-hero">' + bubbles + '<div class="lh-in">' + logo_html() +
            '<div class="co-en">' + CO_EN + '</div><div class="co-am">' + CO_AM + "</div>"
            '<div class="tag">' + T("tagline") + "</div></div></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="login-t">' + T("login") + '</div><div class="login-s">' + T("login_sub") + "</div>",
                    unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input(T("username"))
            p = st.text_input(T("password"), type="password")
            if st.form_submit_button(T("login"), type="primary"):
                r = q("SELECT * FROM users WHERE username=?", (u.strip(),))
                if not r.empty and secrets.compare_digest(hash_pw(p, r.salt[0]), r.pw_hash[0]):
                    st.session_state.user = {"username": r.username[0], "name": r.name[0], "role": r.role[0]}
                    st.rerun()
                else:
                    st.error(T("bad_login"))


# ------------------------------------------------------------------ rep pages
def page_entry(user):
    rep = user["username"]
    d = st.date_input(T("date"), date.today(), key="entry_date").isoformat()

    # ---- goods received (rep adds as many loads as needed)
    sec(T("received_loads"), T("received_hint"))
    r_old = q("SELECT big, small FROM received_loads WHERE d=? AND rep=? ORDER BY load_no", (d, rep))
    r_ed = st.data_editor(
        r_old, num_rows="dynamic", use_container_width=True, key=f"recv{d}",
        column_config={
            "big": st.column_config.NumberColumn(T("big"), min_value=0, step=10),
            "small": st.column_config.NumberColumn(T("small"), min_value=0, step=10),
        },
    )
    r_ed = r_ed.fillna(0).astype(float)
    r_ed = r_ed[(r_ed.big > 0) | (r_ed.small > 0)]
    rb, rs = int(r_ed.big.sum()), int(r_ed.small.sum())
    kpis([(T("loads"), len(r_ed), ""), (T("total_big"), rb, ""), (T("total_small"), rs, "")])

    # ---- sales
    sec(T("sales"), T("sales_hint"))
    s_old = q("SELECT product, COALESCE(note,'') AS note, qty, price FROM sales WHERE d=? AND rep=? ORDER BY id", (d, rep))
    s_ed = st.data_editor(
        s_old, num_rows="dynamic", use_container_width=True, key=f"sales{d}",
        column_config={
            "product": st.column_config.SelectboxColumn(T("product"), options=PRODUCTS, required=True),
            "note": st.column_config.TextColumn(T("note")),
            "qty": st.column_config.NumberColumn(T("qty"), min_value=0, step=1, required=True),
            "price": st.column_config.NumberColumn(T("price"), min_value=0, step=25, required=True),
        },
    )
    s_ed = s_ed.dropna(subset=["product", "qty", "price"]).copy()
    s_ed["note"] = s_ed["note"].fillna("").astype(str).str.strip()
    sales_total = float((s_ed.qty * s_ed.price).sum())
    for prod, rcv in (("Big", rb), ("Small", rs)):
        sold = int(s_ed[s_ed["product"] == prod].qty.sum())
        if sold != rcv and (sold or rcv):
            st.warning(T("sold_vs_recv") + " - " + prod + ": " + str(sold) + " / " + str(rcv))

    # ---- payments
    sec(T("payments"))
    p_old = q("SELECT bank, paid_for, amount FROM payments WHERE d=? AND rep=? ORDER BY id", (d, rep))
    p_old["bank_other"] = ""
    custom = ~p_old["bank"].isin(BANKS)
    p_old.loc[custom, "bank_other"] = p_old.loc[custom, "bank"]
    p_old.loc[custom, "bank"] = "Other"
    p_old = p_old[["bank", "bank_other", "paid_for", "amount"]]
    p_ed = st.data_editor(
        p_old, num_rows="dynamic", use_container_width=True, key=f"pay{d}",
        column_config={
            "bank": st.column_config.SelectboxColumn(T("bank"), options=BANKS, required=True),
            "bank_other": st.column_config.TextColumn(T("bank_other")),
            "paid_for": st.column_config.TextColumn(T("paid_for")),
            "amount": st.column_config.NumberColumn(T("amount"), min_value=0, step=1000, required=True),
        },
    )
    p_ed = p_ed.dropna(subset=["bank", "amount"]).copy()
    p_ed["paid_for"] = p_ed["paid_for"].fillna("").astype(str)
    p_ed["bank_other"] = p_ed["bank_other"].fillna("").astype(str).str.strip()
    p_ed["bank_final"] = [o if (b == "Other" and o) else b for b, o in zip(p_ed["bank"], p_ed["bank_other"])]
    pay_total = float(p_ed.amount.sum())

    # ---- balance
    begin = balance(rep, d, inclusive=False)
    final = begin + sales_total - pay_total
    kpis([
        (T("beginning"), money(begin), ""),
        (T("sales_total"), money(sales_total), ""),
        (T("pay_total"), money(pay_total), ""),
        (T("final"), money(final), "primary"),
    ])

    if st.button(T("save"), type="primary"):
        with conn() as c:
            c.execute("DELETE FROM received_loads WHERE d=? AND rep=?", (d, rep))
            c.executemany("INSERT INTO received_loads VALUES(?,?,?,?,?)",
                          [(d, rep, i + 1, int(r["big"]), int(r["small"])) for i, (_, r) in enumerate(r_ed.iterrows())])
            c.execute("DELETE FROM sales WHERE d=? AND rep=?", (d, rep))
            c.executemany("INSERT INTO sales(d,rep,product,note,qty,price) VALUES(?,?,?,?,?,?)",
                          [(d, rep, r["product"], r["note"], int(r["qty"]), float(r["price"])) for _, r in s_ed.iterrows()])
            c.execute("DELETE FROM payments WHERE d=? AND rep=?", (d, rep))
            c.executemany("INSERT INTO payments(d,rep,bank,paid_for,amount) VALUES(?,?,?,?,?)",
                          [(d, rep, r["bank_final"], r["paid_for"], float(r["amount"])) for _, r in p_ed.iterrows()])
        st.success(T("saved"))


def page_history(user):
    rep = user["username"]
    days = q("SELECT d FROM (SELECT d FROM sales WHERE rep=? UNION SELECT d FROM payments WHERE rep=? "
             "UNION SELECT d FROM received_loads WHERE rep=?) ORDER BY d DESC LIMIT 60", (rep, rep, rep))
    rows = []
    for d in days.d:
        s = q("SELECT COALESCE(SUM(qty*price),0) v FROM sales WHERE rep=? AND d=?", (rep, d)).v[0]
        p = q("SELECT COALESCE(SUM(amount),0) v FROM payments WHERE rep=? AND d=?", (rep, d)).v[0]
        rows.append({T("date"): d, T("beginning"): balance(rep, d, False), T("sales_total"): s,
                     T("pay_total"): p, T("final"): balance(rep, d)})
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df.style.format("{:,.0f}", subset=list(df.columns[1:])), hide_index=True, use_container_width=True)
    else:
        st.info(T("no_data"))


# ---------------------------------------------------------------- factory page
def page_dispatch(user):
    rp = reps_df()
    if rp.empty:
        st.info(T("no_data"))
        return
    sec(T("dispatch_new"))
    names = rp.set_index("username").name.to_dict()
    with st.form("dispatch", clear_on_submit=True):
        c = st.columns(5)
        d = c[0].date_input(T("date"), date.today())
        rep = c[1].selectbox(T("rep"), list(rp.username), format_func=lambda u: names[u])
        ln = c[2].number_input(T("load_no"), 1, 10, 1)
        big = c[3].number_input(T("big"), 0, step=10)
        small = c[4].number_input(T("small"), 0, step=10)
        if st.form_submit_button(T("save"), type="primary"):
            run("INSERT INTO dispatch(d,rep,load_no,big,small) VALUES(?,?,?,?,?)",
                (d.isoformat(), rep, int(ln), int(big), int(small)))
            st.success(T("saved"))
    sec(T("dispatch_list"))
    df = q("SELECT id, d, rep, load_no, big, small FROM dispatch ORDER BY d DESC, id DESC LIMIT 200")
    df.insert(0, "✔", False)
    ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=list(df.columns[1:]))
    if st.button(T("delete")):
        for i in ed[ed["✔"]].id:
            run("DELETE FROM dispatch WHERE id=?", (int(i),))
        st.rerun()


# ------------------------------------------------------- finance / executive
def date_filter():
    c = st.columns(3)
    d1 = c[0].date_input(T("from"), date.today().replace(day=1), key="f1")
    d2 = c[1].date_input(T("to"), date.today(), key="f2")
    rp = reps_df()
    names = rp.set_index("username").name.to_dict()
    rep = c[2].selectbox(T("rep"), [""] + list(rp.username), format_func=lambda u: T("all") if u == "" else names[u])
    return d1.isoformat(), d2.isoformat(), rep or None


def per_rep_table(d1, d2, rep):
    rp = reps_df()
    rows = []
    for u, n in zip(rp.username, rp.name):
        if rep and u != rep:
            continue
        s = q("SELECT COALESCE(SUM(qty*price),0) v FROM sales WHERE rep=? AND d BETWEEN ? AND ?", (u, d1, d2)).v[0]
        p = q("SELECT COALESCE(SUM(amount),0) v FROM payments WHERE rep=? AND d BETWEEN ? AND ?", (u, d1, d2)).v[0]
        rows.append({T("rep"): n, T("beginning"): balance(u, d1, False), T("sales_total"): s,
                     T("pay_total"): p, T("final"): balance(u, d2)})
    return pd.DataFrame(rows)


def show_money_table(df):
    if df.empty:
        st.info(T("no_data"))
        return
    st.dataframe(df.style.format("{:,.0f}", subset=list(df.columns[1:])), hide_index=True, use_container_width=True)


def show_recon(d1, d2, rep, r=None):
    sec(T("recon"))
    if r is None:
        r = recon_df(d1, d2, rep)
    if r.empty:
        st.info(T("no_data"))
        return
    nm = name_map()
    out = pd.DataFrame({
        T("date"): r.d, T("rep"): r.rep.map(lambda u: nm.get(u, u)), T("load_no"): r.load_no,
        T("factory_big"): r.big_s.astype(int), T("rep_big"): r.big_r.astype(int), T("diff_big"): r.diff_big.astype(int),
        T("factory_small"): r.small_s.astype(int), T("rep_small"): r.small_r.astype(int), T("diff_small"): r.diff_small.astype(int),
        T("status"): r.status,
    })
    st.dataframe(out, hide_index=True, use_container_width=True)


def page_exec(user):
    d1, d2, rep = date_filter()
    t = per_rep_table(d1, d2, rep)
    r = recon_df(d1, d2, rep)
    n_issue = 0 if r.empty else int((r.status == "⚠️").sum())
    has = not t.empty
    kpis([
        (T("total_sales"), money(t[T("sales_total")].sum()) if has else "0", ""),
        (T("total_pay"), money(t[T("pay_total")].sum()) if has else "0", ""),
        (T("outstanding"), money(t[T("final")].sum()) if has else "0", "primary"),
        (T("issues"), n_issue, "warn" if n_issue else ""),
    ])
    sec(T("per_rep"))
    show_money_table(t)
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    sd = q(f"SELECT d, SUM(qty*price) v FROM sales WHERE d BETWEEN ? AND ?{f} GROUP BY d ORDER BY d", p)
    if not sd.empty:
        sec(T("sales_by_day"))
        st.bar_chart(sd.set_index("d").v, color="#0A5FD0")
    bd = q(f"SELECT product, COALESCE(note,'') note, SUM(qty) qty, SUM(qty*price) amount FROM sales "
           f"WHERE d BETWEEN ? AND ?{f} GROUP BY product, note ORDER BY product, note", p)
    if not bd.empty:
        sec(T("breakdown"))
        bd.columns = [T("product"), T("note"), T("qty"), T("amount")]
        st.dataframe(bd.style.format("{:,.0f}", subset=[T("qty"), T("amount")]), hide_index=True, use_container_width=True)
    show_recon(d1, d2, rep, r)


def page_fin(user):
    d1, d2, rep = date_filter()
    t = per_rep_table(d1, d2, rep)
    has = not t.empty
    kpis([
        (T("total_sales"), money(t[T("sales_total")].sum()) if has else "0", ""),
        (T("total_pay"), money(t[T("pay_total")].sum()) if has else "0", ""),
        (T("outstanding"), money(t[T("final")].sum()) if has else "0", "primary"),
    ])
    sec(T("per_rep"))
    show_money_table(t)
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    pb = q(f"SELECT bank, SUM(amount) v FROM payments WHERE d BETWEEN ? AND ?{f} GROUP BY bank ORDER BY v DESC", p)
    if not pb.empty:
        sec(T("pay_by_bank"))
        st.bar_chart(pb.set_index("bank").v, color="#0A5FD0")
    sec(T("payments"))
    pay = q(f"SELECT d, rep, bank, paid_for, amount FROM payments WHERE d BETWEEN ? AND ?{f} ORDER BY d DESC, id DESC", p)
    nm = name_map()
    pay["rep"] = pay["rep"].map(lambda u: nm.get(u, u))
    pay.columns = [T("date"), T("rep"), T("bank"), T("paid_for"), T("amount")]
    st.dataframe(pay, hide_index=True, use_container_width=True)
    st.download_button(T("download"), pay.to_csv(index=False).encode("utf-8-sig"), "payments.csv", "text/csv")
    show_recon(d1, d2, rep)


def page_opening(user):
    sec(T("opening"), T("opening_hint"))
    rp = reps_df()
    for u, n in zip(rp.username, rp.name):
        amt, start = opening_of(u)
        c = st.columns([2, 2, 2, 1])
        c[0].markdown("**" + esc(n) + "**")
        a = c[1].number_input(T("amount"), value=float(amt), step=1000.0, key=f"oa{u}")
        s = c[2].date_input(T("start_date"), date.fromisoformat(start) if start > "0001" else date.today(), key=f"os{u}")
        if c[3].button(T("save"), key=f"ob{u}"):
            run("INSERT INTO opening VALUES(?,?,?) ON CONFLICT(rep) DO UPDATE SET amount=excluded.amount, as_of=excluded.as_of",
                (u, a, s.isoformat()))
            st.success(T("saved"))


def page_users(user):
    sec(T("users"))
    st.dataframe(q("SELECT username, name, role FROM users ORDER BY role, username"), hide_index=True,
                 use_container_width=True)
    sec(T("new_user"))
    with st.form("newuser", clear_on_submit=True):
        c = st.columns(4)
        u = c[0].text_input(T("username"))
        n = c[1].text_input(T("full_name"))
        r = c[2].selectbox(T("role"), ROLES)
        p = c[3].text_input(T("password"), type="password")
        if st.form_submit_button(T("save"), type="primary") and u.strip() and p:
            upsert_user(u.strip(), n.strip() or u.strip(), r, p)
            st.success(T("saved"))


def page_chpw(user):
    with st.form("chpw", clear_on_submit=True):
        old = st.text_input(T("old_pw"), type="password")
        new = st.text_input(T("new_pw"), type="password")
        new2 = st.text_input(T("new_pw2"), type="password")
        if st.form_submit_button(T("save"), type="primary"):
            r = q("SELECT salt, pw_hash FROM users WHERE username=?", (user["username"],))
            if r.empty or not secrets.compare_digest(hash_pw(old, r.salt[0]), r.pw_hash[0]):
                st.error(T("pw_wrong"))
            elif len(new) < 6:
                st.error(T("pw_short"))
            elif new != new2:
                st.error(T("pw_mismatch"))
            elif new == old:
                st.error(T("pw_same"))
            else:
                salt = secrets.token_hex(16)
                run("UPDATE users SET salt=?, pw_hash=? WHERE username=?",
                    (salt, hash_pw(new, salt), user["username"]))
                st.success(T("pw_done"))


# ----------------------------------------------------------------------- main
PAGES = {
    "rep": [("entry", page_entry), ("history", page_history), ("chpw", page_chpw)],
    "factory": [("dispatch", page_dispatch), ("chpw", page_chpw)],
    "finance": [("fin", page_fin), ("opening", page_opening), ("chpw", page_chpw)],
    "executive": [("exec", page_exec), ("fin", page_fin), ("dispatch", page_dispatch),
                  ("opening", page_opening), ("users", page_users), ("chpw", page_chpw)],
}


def main():
    init_db()
    st.session_state.setdefault("lang", "አማርኛ")
    st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)
    user = st.session_state.get("user")
    if not user:
        login_screen()
        return

    pages = PAGES[user["role"]]
    with st.container(key="topbar"):
        c1, c2, c3 = st.columns([3, 2, 2], vertical_alignment="center")
        c1.markdown(logo_html(), unsafe_allow_html=True)
        with c2:
            lang_button("lang_top")
        with c3:
            st.button(T("logout"), key="logout_btn", on_click=do_logout)
    with st.container(key="nav"):
        choice = st.radio(T("nav"), [k for k, _ in pages], format_func=T, horizontal=True,
                          label_visibility="collapsed", key="nav_choice")

    hero(user, T(choice))
    dict(pages)[choice](user)


main()
