"""
Mella Soap & Detergent — Sales & Inventory Management System
==============================================================
A single-file Streamlit ERP application backed by Google Sheets.

Design goals of this rewrite:
- Same four role-based logins as before (nothing removed).
- Works cleanly on both phone and desktop browsers.
- Login happens once per session (no re-typing the password on every click).
- Fewer, safer writes to Google Sheets (no more clear-then-multi-append).
- Defensive number parsing so the app never crashes on odd sheet data.
- Cached reads (with a manual "Refresh" button) so the app feels fast.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mella Soap & Detergent — Management System",
    layout="wide",
    page_icon="🧼",
    initial_sidebar_state="expanded",
)

# Light touch of CSS so buttons/inputs are comfortable to tap on a phone.
st.markdown(
    """
    <style>
        .stButton > button, .stFormSubmitButton > button {
            width: 100%;
            padding: 0.6rem 1rem;
            font-weight: 600;
            border-radius: 8px;
        }
        div[data-testid="stMetric"] {
            background: #f7f7f9;
            border-radius: 10px;
            padding: 0.8rem;
        }
        @media (max-width: 640px) {
            h1 { font-size: 1.4rem !important; }
            h2 { font-size: 1.15rem !important; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

SHEET_SALES = "Sales_Tracker"
SHEET_INVENTORY = "Inventory_Dispatch"
SHEET_SETTINGS = "System_Settings"

SALES_COLUMNS = [
    "Sales Date", "Truck Code", "Received 200g Ctn", "Received 100g Ctn",
    "Sold 200g Ctn", "Sold 100g Ctn", "Total Sales ETB", "Deposited ETB",
    "Bank Name", "Variance ETB", "Status", "Remarks",
]
INVENTORY_COLUMNS = ["Date", "Select Truck", "200g Cartons Sent", "100g Cartons Sent", "Remarks"]

ROLES = {
    "Executive Dashboard": {"icon": "📈", "secret_key": "PASSWORD_EXEC", "default": "exec123"},
    "Inventory Dispatch Department": {"icon": "🏭", "secret_key": "PASSWORD_INV", "default": "inv123"},
    "Sales Department (Robel)": {"icon": "💰", "secret_key": "PASSWORD_ROBEL", "default": "robel123"},
    "System Settings & Data Audit": {"icon": "⚙️", "secret_key": "PASSWORD_SETTINGS", "default": "settings123"},
}

DEFAULT_PRICE_200G = 1800.0
DEFAULT_PRICE_100G = 1750.0
DEFAULT_TRUCKS = ["TRUCK-01 (Aklilu Assefa)", "TRUCK-02 (Zemen)"]
DEFAULT_BANKS = [
    "Commercial Bank of Ethiopia (CBE)", "Awash Bank", "Dashen Bank",
    "Wegagen Bank", "Hibret Bank", "Bank of Abyssinia", "Abay Bank",
]


# ---------------------------------------------------------------------------
# HELPERS — safe number parsing so a stray blank cell never crashes the app
# ---------------------------------------------------------------------------
def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# DOWNLOADS — export any table to CSV or Excel, straight from the browser
# ---------------------------------------------------------------------------
def _to_excel_bytes(df, sheet_label="Data"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_label[:31])
    return buffer.getvalue()


def download_buttons(df, filename_stem, key_prefix):
    """Renders a CSV + Excel download button pair for the given DataFrame."""
    if df is None or df.empty:
        return
    col1, col2 = st.columns(2)
    col1.download_button(
        "⬇️ Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{filename_stem}.csv",
        mime="text/csv",
        key=f"{key_prefix}_csv",
        use_container_width=True,
    )
    col2.download_button(
        "⬇️ Download Excel",
        data=_to_excel_bytes(df, filename_stem),
        file_name=f"{filename_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{key_prefix}_xlsx",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Authenticate with Google Sheets once per app session (cached)."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scope)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_gspread_client()
    return client.open_by_url(st.secrets["google_sheet_url"])


def get_worksheet(sheet_name):
    """Always-fresh worksheet handle, used right before any write."""
    return get_spreadsheet().worksheet(sheet_name)


@st.cache_data(ttl=30, show_spinner=False)
def load_sheet(sheet_name):
    """Cached read — refreshed every 30s, or instantly via the Refresh button."""
    ws = get_spreadsheet().worksheet(sheet_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def refresh_data():
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=30, show_spinner=False)
def load_settings():
    """Returns (price_200g, price_100g, truck_options, bank_options)."""
    df = load_sheet(SHEET_SETTINGS)
    price_200g, price_100g = DEFAULT_PRICE_200G, DEFAULT_PRICE_100G
    trucks, banks = list(DEFAULT_TRUCKS), list(DEFAULT_BANKS)

    if not df.empty and {"Setting", "Value"}.issubset(df.columns):
        lookup = dict(zip(df["Setting"], df["Value"]))
        price_200g = safe_float(lookup.get("price_200g"), DEFAULT_PRICE_200G)
        price_100g = safe_float(lookup.get("price_100g"), DEFAULT_PRICE_100G)
        if lookup.get("trucks"):
            trucks = [t.strip() for t in str(lookup["trucks"]).split(",") if t.strip()]
        if lookup.get("banks"):
            banks = [b.strip() for b in str(lookup["banks"]).split(",") if b.strip()]

    return price_200g, price_100g, trucks, banks


def append_row_safely(sheet_name, row_values):
    ws = get_worksheet(sheet_name)
    ws.append_row(row_values, value_input_option="USER_ENTERED")


def save_settings(price_200g, price_100g, trucks_str, banks_str):
    """Rewrites the settings sheet in a single call (safer than clear + N appends)."""
    ws = get_worksheet(SHEET_SETTINGS)
    values = [
        ["Setting", "Value"],
        ["price_200g", str(price_200g)],
        ["price_100g", str(price_100g)],
        ["trucks", trucks_str],
        ["banks", banks_str],
    ]
    ws.clear()
    ws.update(range_name="A1", values=values, value_input_option="USER_ENTERED")


# ---------------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------------
def check_password(role, entered_password):
    cfg = ROLES[role]
    expected = st.secrets.get(cfg["secret_key"], cfg["default"])
    return entered_password == expected


def show_login():
    st.title("🧼 Mella Soap & Detergent")
    st.caption("Sales & Inventory Management System")
    st.markdown("---")

    left, right = st.columns([1, 1]) if st.session_state.get("_wide", True) else (st.container(), None)
    with left:
        st.subheader("🔐 Sign in")
        role = st.selectbox(
            "Department",
            list(ROLES.keys()),
            format_func=lambda r: f"{ROLES[r]['icon']}  {r}",
        )
        password = st.text_input("Password", type="password")
        login_clicked = st.button("Log in", type="primary")

        if login_clicked:
            if check_password(role, password):
                st.session_state.authenticated = True
                st.session_state.role = role
                st.rerun()
            else:
                st.error("❌ Incorrect password for this department.")


def show_logout_control():
    with st.sidebar:
        st.success(f"Signed in as **{st.session_state.role}**")
        if st.button("🔄 Refresh data"):
            refresh_data()
        if st.button("🚪 Log out"):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.rerun()


# ---------------------------------------------------------------------------
# MODULE 1 — EXECUTIVE DASHBOARD
# ---------------------------------------------------------------------------
def module_executive_dashboard():
    st.header("📈 Executive Summary & Financial Analytics")

    df_sales = load_sheet(SHEET_SALES)
    df_inv = load_sheet(SHEET_INVENTORY)

    total_sales = safe_float(df_sales["Total Sales ETB"].apply(safe_float).sum()) if "Total Sales ETB" in df_sales else 0.0
    total_deposits = safe_float(df_sales["Deposited ETB"].apply(safe_float).sum()) if "Deposited ETB" in df_sales else 0.0
    total_variance = safe_float(df_sales["Variance ETB"].apply(safe_float).sum()) if "Variance ETB" in df_sales else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"{total_sales:,.2f} ETB")
    col2.metric("Total Bank Deposits", f"{total_deposits:,.2f} ETB")
    col3.metric(
        "Net Variance",
        f"{total_variance:,.2f} ETB",
        delta=f"{total_variance:,.2f} ETB",
        delta_color="inverse" if total_variance < 0 else "normal",
    )

    st.markdown("---")
    tab1, tab2 = st.tabs(["📋 Sales & Reconciliation Ledger", "🚛 Inventory Dispatch History"])
    with tab1:
        if not df_sales.empty:
            st.dataframe(df_sales, use_container_width=True, hide_index=True)
            download_buttons(df_sales, "mella_sales_ledger", "exec_sales")
        else:
            st.info("No sales records yet.")
    with tab2:
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
            download_buttons(df_inv, "mella_inventory_dispatch", "exec_inv")
        else:
            st.info("No dispatch records yet.")

    if not df_sales.empty or not df_inv.empty:
        st.markdown("---")
        st.subheader("📦 Full Backup (both ledgers, one file)")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            if not df_sales.empty:
                df_sales.to_excel(writer, index=False, sheet_name="Sales_Tracker")
            if not df_inv.empty:
                df_inv.to_excel(writer, index=False, sheet_name="Inventory_Dispatch")
        st.download_button(
            "⬇️ Download Full Backup (Excel, all sheets)",
            data=buffer.getvalue(),
            file_name=f"mella_full_backup_{datetime.today().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# MODULE 2 — INVENTORY DISPATCH
# ---------------------------------------------------------------------------
def module_inventory_dispatch(truck_options):
    st.header("🏭 Factory Inventory Dispatch")

    with st.form("inventory_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dispatch_date = st.date_input("Dispatch Date", datetime.today())
            truck = st.selectbox("Vehicle / Fleet Code", truck_options)
        with col2:
            qty_200g = st.number_input("200g Cartons Dispatched", min_value=0, step=1)
            qty_100g = st.number_input("100g Cartons Dispatched", min_value=0, step=1)
        remarks = st.text_area("Remarks / Logistics Notes")

        if st.form_submit_button("🚀 Submit Dispatch Entry", type="primary"):
            append_row_safely(SHEET_INVENTORY, [
                dispatch_date.strftime("%Y-%m-%d"), truck, int(qty_200g), int(qty_100g), remarks,
            ])
            st.success("✅ Dispatch record saved.")
            refresh_data()

    st.markdown("---")
    st.subheader("Recent Dispatches")
    df_inv = load_sheet(SHEET_INVENTORY)
    if not df_inv.empty:
        st.dataframe(df_inv.tail(10), use_container_width=True, hide_index=True)
        download_buttons(df_inv, "mella_inventory_dispatch", "inv_module")
    else:
        st.info("No dispatch records yet.")


# ---------------------------------------------------------------------------
# MODULE 3 — SALES DEPARTMENT
# ---------------------------------------------------------------------------
def module_sales_department(truck_options, bank_options, price_200g, price_100g):
    st.header("💰 Sales Execution & Bank Reconciliation")

    with st.form("sales_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sales_date = st.date_input("Sales Date", datetime.today())
            truck = st.selectbox("Vehicle / Fleet Code", truck_options)
            recv_200g = st.number_input("Received 200g Cartons", min_value=0, step=1)
            recv_100g = st.number_input("Received 100g Cartons", min_value=0, step=1)
        with col2:
            sold_200g = st.number_input("Sold 200g Cartons", min_value=0, step=1)
            sold_100g = st.number_input("Sold 100g Cartons", min_value=0, step=1)
            deposited = st.number_input("Deposited Bank Amount (ETB)", min_value=0.0, step=100.0)
            bank = st.selectbox("Destination Bank", bank_options)
        remarks = st.text_area("Notes")

        calc_total_sales = (sold_200g * price_200g) + (sold_100g * price_100g)
        calc_variance = deposited - calc_total_sales
        status = "Balanced" if calc_variance == 0 else ("Shortage" if calc_variance < 0 else "Overage")

        st.caption(f"Calculated total sales: **{calc_total_sales:,.2f} ETB**  |  Status preview: **{status}**")

        if st.form_submit_button("💾 Save Sales Record", type="primary"):
            if sold_200g > recv_200g or sold_100g > recv_100g:
                st.error("❌ Sold quantity cannot exceed received quantity. Please check the entry.")
            else:
                append_row_safely(SHEET_SALES, [
                    sales_date.strftime("%Y-%m-%d"), truck, int(recv_200g), int(recv_100g),
                    int(sold_200g), int(sold_100g), float(calc_total_sales),
                    float(deposited), bank, float(calc_variance), status, remarks,
                ])
                st.success("✅ Sales record saved.")
                refresh_data()

    st.markdown("---")
    st.subheader("Recent Sales")
    df_sales = load_sheet(SHEET_SALES)
    if not df_sales.empty:
        st.dataframe(df_sales.tail(10), use_container_width=True, hide_index=True)
        download_buttons(df_sales, "mella_sales_ledger", "sales_module")
    else:
        st.info("No sales records yet.")


# ---------------------------------------------------------------------------
# MODULE 4 — SYSTEM SETTINGS & DATA AUDIT
# ---------------------------------------------------------------------------
def module_settings(price_200g, price_100g, truck_options, bank_options):
    st.header("⚙️ System Configuration & Data Audit")

    tab_config, tab_edit_sales, tab_edit_inv = st.tabs(
        ["⚙️ Prices & Fleet", "✏️ Audit Sales Ledger", "✏️ Audit Inventory Dispatches"]
    )

    with tab_config:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Unit Selling Prices")
            new_p200 = st.number_input("200g Carton Price (ETB)", value=price_200g, step=50.0)
            new_p100 = st.number_input("100g Carton Price (ETB)", value=price_100g, step=50.0)
        with col2:
            st.subheader("Fleet & Banks")
            trucks_str = st.text_input("Registered Trucks (comma-separated)", value=", ".join(truck_options))
            banks_str = st.text_input("Registered Banks (comma-separated)", value=", ".join(bank_options))

        if st.button("💾 Save Configuration", type="primary"):
            save_settings(new_p200, new_p100, trucks_str, banks_str)
            st.success("✅ Configuration updated.")
            refresh_data()

    with tab_edit_sales:
        _audit_sales_ledger(truck_options, bank_options, price_200g, price_100g)

    with tab_edit_inv:
        _audit_inventory_ledger(truck_options)


def _audit_sales_ledger(truck_options, bank_options, price_200g, price_100g):
    st.subheader("Sales Records — Edit or Delete")
    df = load_sheet(SHEET_SALES)
    if df.empty:
        st.info("No sales records yet.")
        return

    df = df.reindex(columns=SALES_COLUMNS, fill_value="")
    df["Sheet_Row_ID"] = range(2, len(df) + 2)

    download_buttons(df.drop(columns=["Sheet_Row_ID"]), "mella_sales_ledger", "audit_sales")
    st.markdown("---")

    selected_id = st.selectbox(
        "Select entry to edit",
        options=df["Sheet_Row_ID"],
        format_func=lambda rid: (
            f"Row {rid} | {df.loc[df.Sheet_Row_ID == rid, 'Sales Date'].values[0]} | "
            f"{df.loc[df.Sheet_Row_ID == rid, 'Truck Code'].values[0]} | "
            f"{df.loc[df.Sheet_Row_ID == rid, 'Deposited ETB'].values[0]} ETB"
        ),
    )
    row = df.loc[df.Sheet_Row_ID == selected_id].iloc[0]
    st.warning(f"⚠️ Editing sheet row **{selected_id}**")

    with st.form("edit_sales_form"):
        col1, col2 = st.columns(2)
        with col1:
            e_date = st.text_input("Date (YYYY-MM-DD)", value=str(row["Sales Date"]))
            e_truck = st.selectbox("Truck", truck_options,
                                    index=truck_options.index(row["Truck Code"]) if row["Truck Code"] in truck_options else 0)
            e_recv_200 = st.number_input("Received 200g", value=safe_int(row["Received 200g Ctn"]), step=1)
            e_recv_100 = st.number_input("Received 100g", value=safe_int(row["Received 100g Ctn"]), step=1)
        with col2:
            e_sold_200 = st.number_input("Sold 200g", value=safe_int(row["Sold 200g Ctn"]), step=1)
            e_sold_100 = st.number_input("Sold 100g", value=safe_int(row["Sold 100g Ctn"]), step=1)
            e_dep = st.number_input("Deposited ETB", value=safe_float(row["Deposited ETB"]), step=100.0)
            e_bank = st.selectbox("Bank", bank_options,
                                   index=bank_options.index(row["Bank Name"]) if row["Bank Name"] in bank_options else 0)
        e_remarks = st.text_area("Remarks", value=str(row["Remarks"]))

        e_total = (e_sold_200 * price_200g) + (e_sold_100 * price_100g)
        e_variance = e_dep - e_total
        e_status = "Balanced" if e_variance == 0 else ("Shortage" if e_variance < 0 else "Overage")

        col_update, col_delete = st.columns(2)
        do_update = col_update.form_submit_button("🔄 Apply Update", type="primary")
        do_delete = col_delete.form_submit_button("🗑️ Delete Row")

        if do_update:
            get_worksheet(SHEET_SALES).update(
                range_name=f"A{selected_id}:L{selected_id}",
                values=[[e_date, e_truck, int(e_recv_200), int(e_recv_100), int(e_sold_200), int(e_sold_100),
                          float(e_total), float(e_dep), e_bank, float(e_variance), e_status, e_remarks]],
            )
            st.success(f"✅ Row {selected_id} updated.")
            refresh_data()

        if do_delete:
            get_worksheet(SHEET_SALES).delete_rows(int(selected_id))
            st.success("🗑️ Row deleted.")
            refresh_data()


def _audit_inventory_ledger(truck_options):
    st.subheader("Inventory Dispatch Records — Edit or Delete")
    df = load_sheet(SHEET_INVENTORY)
    if df.empty:
        st.info("No dispatch records yet.")
        return

    df = df.reindex(columns=INVENTORY_COLUMNS, fill_value="")
    df["Sheet_Row_ID"] = range(2, len(df) + 2)

    download_buttons(df.drop(columns=["Sheet_Row_ID"]), "mella_inventory_dispatch", "audit_inv")
    st.markdown("---")

    selected_id = st.selectbox(
        "Select entry to edit",
        options=df["Sheet_Row_ID"],
        format_func=lambda rid: (
            f"Row {rid} | {df.loc[df.Sheet_Row_ID == rid, 'Date'].values[0]} | "
            f"{df.loc[df.Sheet_Row_ID == rid, 'Select Truck'].values[0]} | "
            f"200g: {df.loc[df.Sheet_Row_ID == rid, '200g Cartons Sent'].values[0]}"
        ),
    )
    row = df.loc[df.Sheet_Row_ID == selected_id].iloc[0]
    st.warning(f"⚠️ Editing sheet row **{selected_id}**")

    with st.form("edit_inv_form"):
        col1, col2 = st.columns(2)
        with col1:
            ei_date = st.text_input("Date (YYYY-MM-DD)", value=str(row["Date"]))
            ei_truck = st.selectbox("Truck", truck_options,
                                     index=truck_options.index(row["Select Truck"]) if row["Select Truck"] in truck_options else 0)
        with col2:
            ei_qty_200 = st.number_input("200g Cartons", value=safe_int(row["200g Cartons Sent"]), step=1)
            ei_qty_100 = st.number_input("100g Cartons", value=safe_int(row["100g Cartons Sent"]), step=1)
        ei_remarks = st.text_area("Remarks", value=str(row["Remarks"]))

        col_update, col_delete = st.columns(2)
        do_update = col_update.form_submit_button("🔄 Apply Update", type="primary")
        do_delete = col_delete.form_submit_button("🗑️ Delete Row")

        if do_update:
            get_worksheet(SHEET_INVENTORY).update(
                range_name=f"A{selected_id}:E{selected_id}",
                values=[[ei_date, ei_truck, int(ei_qty_200), int(ei_qty_100), ei_remarks]],
            )
            st.success(f"✅ Row {selected_id} updated.")
            refresh_data()

        if do_delete:
            get_worksheet(SHEET_INVENTORY).delete_rows(int(selected_id))
            st.success("🗑️ Row deleted.")
            refresh_data()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None

    if not st.session_state.authenticated:
        show_login()
        return

    show_logout_control()
    price_200g, price_100g, truck_options, bank_options = load_settings()

    st.title("🧼 Mella Soap & Detergent — Management System")
    st.markdown("---")

    role = st.session_state.role
    if role == "Executive Dashboard":
        module_executive_dashboard()
    elif role == "Inventory Dispatch Department":
        module_inventory_dispatch(truck_options)
    elif role == "Sales Department (Robel)":
        module_sales_department(truck_options, bank_options, price_200g, price_100g)
    elif role == "System Settings & Data Audit":
        module_settings(price_200g, price_100g, truck_options, bank_options)


if __name__ == "__main__":
    main()
