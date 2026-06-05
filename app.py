import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Pantauan Jadwal", page_icon="📅", layout="wide")
st.title("📊 Dashboard Pantauan & Antisipasi Jadwal Studio")

# ==========================================
# 2. FUNGSI LOAD DATA
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1wNQHGvbtB1rRq0Mjw4g00q849MTZGJE9AFqrfASyqI4"
    gid = "1652385748"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df_raw = pd.read_csv(csv_url, header=None)
        # Cari baris header
        header_row_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Hari Tanggal', case=False, na=False).any():
                header_row_idx = i
                break
        df = df_raw.iloc[header_row_idx+1:].copy()
        df.columns = df_raw.iloc[header_row_idx].astype(str).str.strip()
        df = df.reset_index(drop=True).dropna(how='all')
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except Exception as e:
        st.error(f"Error memuat: {e}")
        return pd.DataFrame()

df = load_data()

# ==========================================
# 3. PENGOLAHAN TANGGAL & WAKTU
# ==========================================
def parse_date_robust(date_val):
    match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', str(date_val))
    if match:
        months = {'januari':1, 'februari':2, 'maret':3, 'april':4, 'mei':5, 'juni':6, 
                  'juli':7, 'agustus':8, 'september':9, 'oktober':10, 'november':11, 'desember':12}
        d, m, y = match.groups()
        if m.lower() in months:
            return datetime(int(y), months[m.lower()], int(d)).date()
    return None

if not df.empty:
    kolom_tanggal = 'Hari Tanggal' if 'Hari Tanggal' in df.columns else df.columns[0]
    df['Date_Obj'] = df[kolom_tanggal].apply(parse_date_robust)

# ==========================================
# 4. SIDEBAR & FILTER
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")
mode = st.sidebar.radio("Mode Tampilan:", ["Pilih Tanggal Spesifik", "Tampilkan Semua Data"])

if mode == "Pilih Tanggal Spesifik":
    pilih_tanggal_dt = st.sidebar.date_input("Pilih Tanggal:", value=datetime.today())
    df_filtered = df[df['Date_Obj'] == pilih_tanggal_dt].copy()
else:
    df_filtered = df.copy()

# Proses Waktu
if not df_filtered.empty:
    kolom_waktu = 'WAKTU' if 'WAKTU' in df_filtered.columns else 'Waktu'
    start_list, end_list = [], []
    for w in df_filtered[kolom_waktu]:
        try:
            m, s = str(w).upper().replace('WIB', '').replace('.', ':').split('-')
            today = datetime.today().strftime('%Y-%m-%d')
            start_list.append(pd.to_datetime(f"{today} {m.strip()}"))
            end_list.append(pd.to_datetime(f"{today} {s.strip()}"))
        except:
            start_list.append(pd.NaT); end_list.append(pd.NaT)
    df_filtered['Waktu_Mulai'] = start_list
    df_filtered['Waktu_Selesai'] = end_list
    df_filtered = df_filtered.dropna(subset=['Waktu_Mulai'])

# ==========================================
# 5. TAMPILAN DASHBOARD
# ==========================================
if df_filtered.empty:
    st.info("Tidak ada jadwal ditemukan.")
else:
    st.metric("Total Jadwal Ditampilkan", len(df_filtered))
    
    # Deteksi Bentrok
    bentrok = False
    for studio, group in df_filtered.groupby('STUDIO'):
        group = group.sort_values('Waktu_Mulai')
        for i in range(len(group)-1):
            if group.iloc[i+1]['Waktu_Mulai'] < group.iloc[i]['Waktu_Selesai']:
                st.error(f"⚠️ Bentrok di Studio: {studio}")
                bentrok = True
    if not bentrok: st.success("✅ Semua jadwal aman.")

    # Visualisasi
    fig = px.timeline(df_filtered, x_start="Waktu_Mulai", x_end="Waktu_Selesai", y="STUDIO", color="PENGAJAR", hover_name="MAPEL")
    fig.update_yaxes(autorange="reversed")
    fig.layout.xaxis.tickformat = '%H:%M'
    st.plotly_chart(fig, use_container_width=True)

    # Tabel dengan pembersihan data
    st.subheader("📋 Tabel Data")
    # Drop kolom bantu, lalu ubah semua NaN menjadi '-' dan paksa jadi string agar JSON aman
    df_tampil = df_filtered.drop(columns=['Date_Obj', 'Waktu_Mulai', 'Waktu_Selesai'], errors='ignore')
    st.dataframe(df_tampil.fillna("-").astype(str), use_container_width=True)