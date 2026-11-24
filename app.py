"""
Sales Tracker - Ajax Soap (Big 200g / Small 100g)
Streamlit app: Sales Rep, Factory, Finance, Executive logins.
Run:  pip install streamlit pandas
      streamlit run app.py
Default logins (CHANGE after first login, Executive > Users):
  executive / exec123   factory / factory123   finance / finance123   rep1 / rep123
"""
import hashlib
import os
import secrets
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB = os.environ.get("SALES_DB", "sales_tracker.db")
BANKS = ["CBE", "Awash", "Abyssinia", "Dashen", "CBO", "United", "Nib", "Abay", "Wegagen", "Other"]
PRODUCTS = ["Big", "Small"]
ROLES = ["rep", "factory", "finance", "executive"]

st.set_page_config(page_title="Sales Tracker", page_icon="🧼", layout="wide")

# ----------------------------------------------------------------- language
TXT = {
    "title": ("Sales Tracker", "የሽያጭ መከታተያ"),
    "login": ("Login", "ግባ"),
    "username": ("Username", "የተጠቃሚ ስም"),
    "password": ("Password", "የይለፍ ቃል"),
    "bad_login": ("Wrong username or password", "የተጠቃሚ ስም ወይም የይለፍ ቃል ስህተት ነው"),
    "logout": ("Logout", "ውጣ"),
    "language": ("Language", "ቋንቋ"),
    "date": ("Date", "ቀን"),
    "rep": ("Sales rep", "ሴልስ ሪፕሬዘንታቲቭ"),
    "big": ("Big (200g)", "ቢግ (200ግ)"),
    "small": ("Small (100g)", "ስሞል (100ግ)"),
    "load_no": ("Load no. (1st, 2nd...)", "የጭነት ቁጥር (1ኛ፣ 2ኛ...)"),
    "save": ("Save", "አስቀምጥ"),
    "saved": ("Saved ✔", "ተቀምጧል ✔"),
    "delete": ("Delete selected", "የተመረጠውን ሰርዝ"),
    "dispatch": ("Factory dispatch", "ከፋብሪካ የተላከ ምርት"),
    "dispatch_new": ("Record a dispatch", "የተላከ ምርት መዝግብ"),
    "dispatch_list": ("Dispatch records", "የተላኩ ምርቶች ዝርዝር"),
    "entry": ("Daily entry", "የዕለት ምዝገባ"),
    "history": ("My history", "ታሪኬ"),
    "dispatched": ("Dispatched by factory", "ከፋብሪካ የተላከ"),
    "received": ("Received by me", "የተረከብኩት"),
    "match": ("✅ Reconciled - matches factory", "✅ ከፋብሪካ ጋር ተመሳስሏል"),
    "mismatch": ("⚠️ Difference vs factory", "⚠️ ከፋብሪካ ጋር ልዩነት አለ"),
    "no_dispatch": ("No factory dispatch recorded for this day", "ለዚህ ቀን ከፋብሪካ የተመዘገበ ምርት የለም"),
    "sales": ("Sales (quantity x price)", "ሽያጭ (ብዛት x ዋጋ)"),
    "sales_hint": ("Add a row for each price (e.g. Big at 1,800 and Big at 1,775).",
                   "ለእያንዳንዱ ዋጋ አንድ ረድፍ ጨምር (ለምሳሌ ቢግ በ1,800 እና ቢግ በ1,775)።"),
    "payments": ("Payments / bank deposits", "ክፍያዎች / የባንክ ገቢዎች"),
    "product": ("Product", "ምርት"),
    "qty": ("Quantity", "ብዛት"),
    "price": ("Unit price", "የአንዱ ዋጋ"),
    "bank": ("Bank", "ባንክ"),
    "paid_for": ("Deposited for / by", "ለማን / ማን አስገባ"),
    "amount": ("Amount", "መጠን"),
    "beginning": ("Beginning balance", "የቀድሞ ባላንስ"),
    "sales_total": ("Sales total", "የሽያጭ ድምር"),
    "pay_total": ("Payments total", "የክፍያ ድምር"),
    "final": ("Remaining balance", "ቀሪ ባላንስ"),
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
    "per_rep": ("Per sales rep", "በሴልስ ሪፕ"),
    "sales_by_day": ("Sales by day", "የዕለት ሽያጭ"),
    "pay_by_bank": ("Payments by bank", "ክፍያ በባንክ"),
    "recon": ("Reconciliation (factory vs rep)", "ሪኮንሲሊሽን (ፋብሪካ ከሪፕ ጋር)"),
    "status": ("Status", "ሁኔታ"),
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
            CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, rep TEXT, product TEXT, qty INTEGER, price REAL);
            CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, rep TEXT, bank TEXT, paid_for TEXT, amount REAL);
            CREATE TABLE IF NOT EXISTS opening(rep TEXT PRIMARY KEY, amount REAL, as_of TEXT);
            """
        )
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            pass
    if q("SELECT COUNT(*) n FROM users").n[0] == 0:
        upsert_user("executive", "Executive", "executive", "exec123")
        upsert_user("factory", "Factory", "factory", "factory123")
        upsert_user("finance", "Finance", "finance", "finance123")
        upsert_user("rep1", "Sales Rep 1", "rep", "rep123")
    return True


def reps_df():
    return q("SELECT username, name FROM users WHERE role='rep' ORDER BY name")


def opening_of(rep):
    r = q("SELECT amount, as_of FROM opening WHERE rep=?", (rep,))
    if r.empty:
        return 0.0, "0000-01-01"
    return float(r.amount[0]), r.as_of[0]


def balance(rep, d_end, inclusive=True):
    """Opening + sales - payments from opening start date up to d_end."""
    amt, start = opening_of(rep)
    op = "<=" if inclusive else "<"
    s = q(f"SELECT COALESCE(SUM(qty*price),0) v FROM sales WHERE rep=? AND d>=? AND d{op}?", (rep, start, d_end)).v[0]
    p = q(f"SELECT COALESCE(SUM(amount),0) v FROM payments WHERE rep=? AND d>=? AND d{op}?", (rep, start, d_end)).v[0]
    return amt + s - p


def recon_df(d1, d2, rep=None):
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    a = q(f"SELECT d, rep, SUM(big) big_s, SUM(small) small_s FROM dispatch WHERE d BETWEEN ? AND ?{f} GROUP BY d, rep", p)
    b = q(f"SELECT d, rep, big big_r, small small_r FROM received WHERE d BETWEEN ? AND ?{f}", p)
    m = a.merge(b, on=["d", "rep"], how="outer").fillna(0)
    if m.empty:
        return m
    m["diff_big"] = m.big_r - m.big_s
    m["diff_small"] = m.small_r - m.small_s
    m["status"] = ["✅" if (x == 0 and y == 0) else "⚠️" for x, y in zip(m.diff_big, m.diff_small)]
    return m.sort_values(["d", "rep"], ascending=False)


# --------------------------------------------------------------------- login
def login_screen():
    st.title("🧼 " + T("title"))
    with st.form("login"):
        u = st.text_input(T("username"))
        p = st.text_input(T("password"), type="password")
        if st.form_submit_button(T("login")):
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

    disp = q("SELECT load_no, big, small FROM dispatch WHERE d=? AND rep=? ORDER BY load_no", (d, rep))
    sb, ss = int(disp.big.sum()), int(disp.small.sum())
    st.subheader(T("dispatched"))
    if disp.empty:
        st.info(T("no_dispatch"))
    else:
        st.dataframe(disp.rename(columns={"load_no": T("load_no"), "big": T("big"), "small": T("small")}),
                     hide_index=True, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric(T("big"), sb)
    c2.metric(T("small"), ss)

    st.subheader(T("received"))
    old = q("SELECT big, small FROM received WHERE d=? AND rep=?", (d, rep))
    c1, c2 = st.columns(2)
    rb = c1.number_input(T("big"), 0, step=10, value=int(old.big[0]) if not old.empty else 0, key=f"rb{d}")
    rs = c2.number_input(T("small"), 0, step=10, value=int(old.small[0]) if not old.empty else 0, key=f"rs{d}")
    if not disp.empty or rb or rs:
        st.success(T("match")) if (rb == sb and rs == ss) else st.warning(
            f"{T('mismatch')}: {T('big')} {rb - sb:+d}, {T('small')} {rs - ss:+d}")

    st.subheader(T("sales"))
    st.caption(T("sales_hint"))
    s_old = q("SELECT product, qty, price FROM sales WHERE d=? AND rep=? ORDER BY id", (d, rep))
    s_ed = st.data_editor(
        s_old, num_rows="dynamic", use_container_width=True, key=f"sales{d}",
        column_config={
            "product": st.column_config.SelectboxColumn(T("product"), options=PRODUCTS, required=True),
            "qty": st.column_config.NumberColumn(T("qty"), min_value=0, step=1, required=True),
            "price": st.column_config.NumberColumn(T("price"), min_value=0, step=25, required=True),
        },
    )
    s_ed = s_ed.dropna(subset=["product", "qty", "price"])
    sales_total = float((s_ed.qty * s_ed.price).sum())
    for prod, rcv in (("Big", rb), ("Small", rs)):
        sold = int(s_ed[s_ed["product"] == prod].qty.sum())
        if sold != rcv:
            st.warning(f"{T('sold_vs_recv')} - {prod}: {sold} / {rcv}")

    st.subheader(T("payments"))
    p_old = q("SELECT bank, paid_for, amount FROM payments WHERE d=? AND rep=? ORDER BY id", (d, rep))
    p_ed = st.data_editor(
        p_old, num_rows="dynamic", use_container_width=True, key=f"pay{d}",
        column_config={
            "bank": st.column_config.SelectboxColumn(T("bank"), options=BANKS, required=True),
            "paid_for": st.column_config.TextColumn(T("paid_for")),
            "amount": st.column_config.NumberColumn(T("amount"), min_value=0, step=1000, required=True),
        },
    )
    p_ed = p_ed.dropna(subset=["bank", "amount"])
    pay_total = float(p_ed.amount.sum())

    begin = balance(rep, d, inclusive=False)
    final = begin + sales_total - pay_total
    m = st.columns(4)
    m[0].metric(T("beginning"), money(begin))
    m[1].metric(T("sales_total"), money(sales_total))
    m[2].metric(T("pay_total"), money(pay_total))
    m[3].metric(T("final"), money(final))

    if st.button(T("save"), type="primary"):
        with conn() as c:
            c.execute("DELETE FROM received WHERE d=? AND rep=?", (d, rep))
            c.execute("INSERT INTO received VALUES(?,?,?,?)", (d, rep, int(rb), int(rs)))
            c.execute("DELETE FROM sales WHERE d=? AND rep=?", (d, rep))
            c.executemany("INSERT INTO sales(d,rep,product,qty,price) VALUES(?,?,?,?,?)",
                          [(d, rep, r["product"], int(r.qty), float(r.price)) for _, r in s_ed.iterrows()])
            c.execute("DELETE FROM payments WHERE d=? AND rep=?", (d, rep))
            c.executemany("INSERT INTO payments(d,rep,bank,paid_for,amount) VALUES(?,?,?,?,?)",
                          [(d, rep, r["bank"], r.paid_for or "", float(r.amount)) for _, r in p_ed.iterrows()])
        st.success(T("saved"))


def page_history(user):
    rep = user["username"]
    days = q("""SELECT d FROM (SELECT d FROM sales WHERE rep=:r UNION SELECT d FROM payments WHERE rep=:r
                UNION SELECT d FROM received WHERE rep=:r) ORDER BY d DESC LIMIT 60""".replace(":r", "?"),
             (rep, rep, rep))
    rows = []
    for d in days.d:
        s = q("SELECT COALESCE(SUM(qty*price),0) v FROM sales WHERE rep=? AND d=?", (rep, d)).v[0]
        p = q("SELECT COALESCE(SUM(amount),0) v FROM payments WHERE rep=? AND d=?", (rep, d)).v[0]
        rows.append({T("date"): d, T("beginning"): balance(rep, d, False), T("sales_total"): s,
                     T("pay_total"): p, T("final"): balance(rep, d)})
    if rows:
        st.dataframe(pd.DataFrame(rows).style.format("{:,.0f}", subset=[k for k in rows[0] if k != T("date")]),
                     hide_index=True, use_container_width=True)
    else:
        st.info(T("no_data"))


# ---------------------------------------------------------------- factory page
def page_dispatch(user):
    st.subheader(T("dispatch_new"))
    rp = reps_df()
    if rp.empty:
        st.info(T("no_data"))
        return
    with st.form("dispatch", clear_on_submit=True):
        c = st.columns(5)
        d = c[0].date_input(T("date"), date.today())
        rep = c[1].selectbox(T("rep"), rp.username, format_func=lambda u: rp.set_index("username").name[u])
        ln = c[2].number_input(T("load_no"), 1, 10, 1)
        big = c[3].number_input(T("big"), 0, step=10)
        small = c[4].number_input(T("small"), 0, step=10)
        if st.form_submit_button(T("save"), type="primary"):
            run("INSERT INTO dispatch(d,rep,load_no,big,small) VALUES(?,?,?,?,?)",
                (d.isoformat(), rep, int(ln), int(big), int(small)))
            st.success(T("saved"))
    st.subheader(T("dispatch_list"))
    df = q("SELECT id, d, rep, load_no, big, small FROM dispatch ORDER BY d DESC, id DESC LIMIT 200")
    df.insert(0, "✔", False)
    ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=df.columns[1:])
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
    opts = [""] + list(rp.username)
    names = rp.set_index("username").name.to_dict()
    rep = c[2].selectbox(T("rep"), opts, format_func=lambda u: T("all") if u == "" else names[u])
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
    st.dataframe(df.style.format("{:,.0f}", subset=df.columns[1:]), hide_index=True, use_container_width=True)


def show_recon(d1, d2, rep):
    st.subheader(T("recon"))
    r = recon_df(d1, d2, rep)
    if r.empty:
        st.info(T("no_data"))
        return
    r = r[["d", "rep", "big_s", "big_r", "diff_big", "small_s", "small_r", "diff_small", "status"]]
    r.columns = [T("date"), T("rep"), T("big") + " ⇢", T("big") + " ✓", T("diff_big"),
                 T("small") + " ⇢", T("small") + " ✓", T("diff_small"), T("status")]
    st.dataframe(r, hide_index=True, use_container_width=True)


def page_exec(user):
    d1, d2, rep = date_filter()
    t = per_rep_table(d1, d2, rep)
    sales_total = t[T("sales_total")].sum() if not t.empty else 0
    pay_total = t[T("pay_total")].sum() if not t.empty else 0
    out = t[T("final")].sum() if not t.empty else 0
    c = st.columns(3)
    c[0].metric(T("total_sales"), money(sales_total))
    c[1].metric(T("total_pay"), money(pay_total))
    c[2].metric(T("outstanding"), money(out))
    st.subheader(T("per_rep"))
    show_money_table(t)
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    sd = q(f"SELECT d, SUM(qty*price) v FROM sales WHERE d BETWEEN ? AND ?{f} GROUP BY d ORDER BY d", p)
    if not sd.empty:
        st.subheader(T("sales_by_day"))
        st.bar_chart(sd.set_index("d").v)
    show_recon(d1, d2, rep)


def page_fin(user):
    d1, d2, rep = date_filter()
    t = per_rep_table(d1, d2, rep)
    st.subheader(T("per_rep"))
    show_money_table(t)
    f = " AND rep=?" if rep else ""
    p = (d1, d2, rep) if rep else (d1, d2)
    pb = q(f"SELECT bank, SUM(amount) v FROM payments WHERE d BETWEEN ? AND ?{f} GROUP BY bank ORDER BY v DESC", p)
    if not pb.empty:
        st.subheader(T("pay_by_bank"))
        st.bar_chart(pb.set_index("bank").v)
    st.subheader(T("payments"))
    pay = q(f"SELECT d, rep, bank, paid_for, amount FROM payments WHERE d BETWEEN ? AND ?{f} ORDER BY d DESC, id DESC", p)
    st.dataframe(pay, hide_index=True, use_container_width=True)
    st.download_button(T("download"), pay.to_csv(index=False).encode("utf-8-sig"), "payments.csv", "text/csv")
    show_recon(d1, d2, rep)


def page_opening(user):
    st.subheader(T("opening"))
    st.caption(T("opening_hint"))
    rp = reps_df()
    for u, n in zip(rp.username, rp.name):
        amt, start = opening_of(u)
        c = st.columns([2, 2, 2, 1])
        c[0].write(f"**{n}**")
        a = c[1].number_input(T("amount"), value=float(amt), step=1000.0, key=f"oa{u}")
        s = c[2].date_input(T("start_date"), date.fromisoformat(start) if start > "0001" else date.today(), key=f"os{u}")
        if c[3].button(T("save"), key=f"ob{u}"):
            run("INSERT INTO opening VALUES(?,?,?) ON CONFLICT(rep) DO UPDATE SET amount=excluded.amount, as_of=excluded.as_of",
                (u, a, s.isoformat()))
            st.success(T("saved"))


def page_users(user):
    st.subheader(T("users"))
    st.dataframe(q("SELECT username, name, role FROM users ORDER BY role, username"), hide_index=True,
                 use_container_width=True)
    st.subheader(T("new_user"))
    with st.form("newuser", clear_on_submit=True):
        c = st.columns(4)
        u = c[0].text_input(T("username"))
        n = c[1].text_input(T("full_name"))
        r = c[2].selectbox(T("role"), ROLES)
        p = c[3].text_input(T("password"), type="password")
        if st.form_submit_button(T("save")) and u.strip() and p:
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
    st.sidebar.radio(T("language"), ["አማርኛ", "English"], key="lang", horizontal=True)
    user = st.session_state.get("user")
    if not user:
        login_screen()
        return
    st.sidebar.write(f"👤 **{user['name']}** ({user['role']})")
    if st.sidebar.button(T("logout")):
        st.session_state.pop("user")
        st.rerun()
    pages = PAGES[user["role"]]
    choice = st.sidebar.radio(T("nav"), [k for k, _ in pages], format_func=T)
    st.title("🧼 " + T(choice))
    dict(pages)[choice](user)


main()
