import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_calendar import calendar # Library baru

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Pantauan Jadwal", page_icon="📅", layout="wide")
st.title("📊 Dashboard Pantauan & Antisipasi Jadwal Studio")

# ==========================================
# 2. FUNGSI PENARIKAN DATA
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1wNQHGvbtB1rRq0Mjw4g00q849MTZGJE9AFqrfASyqI4"
    gid = "1652385748"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df_raw = pd.read_csv(csv_url, header=None)
        header_row_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Hari Tanggal', case=False, na=False).any():
                header_row_idx = i
                break
        df = df_raw.iloc[header_row_idx+1:].copy()
        df.columns = df_raw.iloc[header_row_idx]
        df = df.reset_index(drop=True)
        df = df.dropna(how='all')
        df.columns = df.columns.astype(str).str.strip()
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except:
        return pd.DataFrame()

df = load_data()

# ==========================================
# 3. SIDEBAR KALENDER INTERAKTIF
# ==========================================
st.sidebar.header("📅 Kalender Jadwal")

# Opsi Kalender
calendar_options = {
    "editable": False,
    "selectable": True,
    "headerToolbar": {
        "left": "prev,next",
        "center": "title",
        "right": "today"
    },
    "initialView": "dayGridMonth",
    "initialDate": datetime.today().strftime("%Y-%m-%d"), # Otomatis ke tanggal hari ini
}

# Tampilkan kalender
state = calendar(options=calendar_options)

# Ambil tanggal yang diklik user, atau default ke hari ini
if state.get("selectedDay"):
    selected_date = state["selectedDay"]
else:
    selected_date = datetime.today().strftime("%Y-%m-%d")

st.sidebar.markdown("---")

# ==========================================
# 4. FILTERING & LOGIKA JADWAL
# ==========================================
# (Logika deteksi bentrok dan visualisasi tetap sama seperti sebelumnya...)
# ... [Sisipkan sisa kode pemrosesan data di sini] ...

# Pastikan Anda memfilter df berdasarkan tanggal yang dipilih dari kalender
# Catatan: Karena format tanggal di Sheet mungkin "Senin, 01 Juni 2026", 
# pastikan logika pencocokan string-nya sesuai dengan data di Sheet Anda.