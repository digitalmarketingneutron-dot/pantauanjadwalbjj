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
        
        # PEMBERSIHAN NAMA KOLOM MAKSIMAL (Mencegah KeyError)
        # Semua spasi di awal/akhir dihapus & dipaksa jadi HURUF BESAR
        df.columns = df_raw.iloc[header_row_idx].astype(str).str.strip().str.upper()
        
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
        months = {'JANUARI':1, 'FEBRUARI':2, 'MARET':3, 'APRIL':4, 'MEI':5, 'JUNI':6, 
                  'JULI':7, 'AGUSTUS':8, 'SEPTEMBER':9, 'OKTOBER':10, 'NOVEMBER':11, 'DESEMBER':12}
        d, m, y = match.groups()
        if m.upper() in months:
            return datetime(int(y), months[m.upper()], int(d)).date()
    return None

if not df.empty:
    # Mengambil nama kolom tanggal dengan aman
    kolom_tanggal = 'HARI TANGGAL' if 'HARI TANGGAL' in df.columns else df.columns[0]
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
    # Pencarian kolom 'WAKTU' secara dinamis
    kolom_waktu = [col for col in df_filtered.columns if 'WAKTU' in col]
    kolom_waktu = kolom_waktu[0] if len(kolom_waktu) > 0 else df_filtered.columns[6]
    
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
    
    # Amankan pengambilan nama kolom untuk grafik & grup
    k_studio = [col for col in df_filtered.columns if 'STUDIO' in col]
    k_studio = k_studio[0] if k_studio else df_filtered.columns[7]
    
    k_mapel = [col for col in df_filtered.columns if 'MAPEL' in col]
    k_mapel = k_mapel[0] if k_mapel else df_filtered.columns[4]
    
    k_pengajar = [col for col in df_filtered.columns if 'PENGAJAR' in col]
    k_pengajar = k_pengajar[0] if k_pengajar else df_filtered.columns[3]
    
    # Deteksi Bentrok
    bentrok = False
    for studio, group in df_filtered.groupby(k_studio):
        group = group.sort_values('Waktu_Mulai')
        for i in range(len(group)-1):
            if group.iloc[i+1]['Waktu_Mulai'] < group.iloc[i]['Waktu_Selesai']:
                st.error(f"⚠️ Bentrok di Studio: {studio} antara {group.iloc[i][k_mapel]} dan {group.iloc[i+1][k_mapel]}")
                bentrok = True
    if not bentrok: st.success("✅ Semua jadwal aman.")

    # Visualisasi
    fig = px.timeline(df_filtered, x_start="Waktu_Mulai", x_end="Waktu_Selesai", y=k_studio, color=k_pengajar, hover_name=k_mapel)
    fig.update_yaxes(autorange="reversed")
    fig.layout.xaxis.tickformat = '%H:%M'
    st.plotly_chart(fig, use_container_width=True)

    # Tabel Data
    st.subheader("📋 Tabel Data")
    df_tampil = df_filtered.drop(columns=['Date_Obj', 'Waktu_Mulai', 'Waktu_Selesai'], errors='ignore')
    # Membersihkan karakter kosong (NaN, None) yang dibaca dari Google Sheets menjadi '-'
    st.dataframe(df_tampil.astype(str).replace(['nan', 'None', '<NA>'], '-'), use_container_width=True)