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
        df.columns = [str(c).strip().upper() for c in df_raw.iloc[header_row_idx]]
        df = df.reset_index(drop=True).dropna(how='all')
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except Exception as e:
        st.error(f"Error memuat data: {e}")
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
    kolom_tanggal = 'HARI TANGGAL' if 'HARI TANGGAL' in df.columns else df.columns[0]
    df['Date_Obj'] = df[kolom_tanggal].apply(parse_date_robust)

# ==========================================
# 4. SIDEBAR & FILTER
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")
mode = st.sidebar.radio("Mode Tampilan:", ["Pilih Tanggal Spesifik", "Tampilkan Semua Data"])

if mode == "Pilih Tanggal Spesifik":
    tanggal_input = st.sidebar.date_input("Pilih Tanggal:", value=datetime.today())
    if isinstance(tanggal_input, (list, tuple)):
        pilih_tanggal_dt = tanggal_input[0] if len(tanggal_input) > 0 else datetime.today().date()
    else:
        pilih_tanggal_dt = tanggal_input
        
    df_filtered = df[df['Date_Obj'] == pilih_tanggal_dt].copy()
else:
    df_filtered = df.copy()

# PENGOLAHAN WAKTU YANG AMAN UNTUK SEMUA TANGGAL
if not df_filtered.empty:
    kolom_waktu = [col for col in df_filtered.columns if 'WAKTU' in str(col)]
    nama_kolom_waktu = kolom_waktu[0] if len(kolom_waktu) > 0 else 'WAKTU'
    
    if nama_kolom_waktu in df_filtered.columns:
        start_list, end_list = [], []
        # Gunakan iterrows untuk menempelkan waktu ke tanggal aslinya masing-masing
        for idx, row in df_filtered.iterrows():
            w = row[nama_kolom_waktu]
            d = row['Date_Obj']
            try:
                m, s = str(w).upper().replace('WIB', '').replace('.', ':').split('-')
                # Pakai tanggal asli jika ada, jika tidak pakai hari ini
                date_str = d.strftime('%Y-%m-%d') if pd.notna(d) else datetime.today().strftime('%Y-%m-%d')
                
                start_list.append(pd.to_datetime(f"{date_str} {m.strip()}"))
                end_list.append(pd.to_datetime(f"{date_str} {s.strip()}"))
            except:
                start_list.append(pd.NaT); end_list.append(pd.NaT)
                
        df_filtered['Waktu_Mulai'] = start_list
        df_filtered['Waktu_Selesai'] = end_list
        
        # Buang data yang waktunya benar-benar tidak bisa dibaca (mencegah grafik crash)
        df_filtered = df_filtered.dropna(subset=['Waktu_Mulai', 'Waktu_Selesai'])

# ==========================================
# 5. TAMPILAN DASHBOARD
# ==========================================
if df_filtered.empty:
    st.info("Tidak ada jadwal yang valid untuk ditampilkan.")
else:
    st.metric("Total Jadwal Ditampilkan", len(df_filtered))
    
    # Amankan pengambilan nama kolom
    k_studio = [col for col in df_filtered.columns if 'STUDIO' in str(col)]
    k_studio = k_studio[0] if k_studio else 'STUDIO'
    
    k_mapel = [col for col in df_filtered.columns if 'MAPEL' in str(col)]
    k_mapel = k_mapel[0] if k_mapel else 'MAPEL'
    
    k_pengajar = [col for col in df_filtered.columns if 'PENGAJAR' in str(col)]
    k_pengajar = k_pengajar[0] if k_pengajar else 'PENGAJAR'
    
    # Deteksi Bentrok (Dikelompokkan berdasarkan STUDIO dan TANGGAL)
    bentrok = False
    if k_studio in df_filtered.columns and k_mapel in df_filtered.columns:
        # Group by gabungan agar hari berbeda tidak dianggap bentrok
        for (studio, tgl), group in df_filtered.groupby([k_studio, 'Date_Obj']):
            group = group.sort_values('Waktu_Mulai')
            for i in range(len(group)-1):
                if group.iloc[i+1]['Waktu_Mulai'] < group.iloc[i]['Waktu_Selesai']:
                    tgl_str = tgl.strftime('%d-%b-%Y') if pd.notna(tgl) else "Tanggal Tidak Diketahui"
                    st.error(f"⚠️ Bentrok di **{studio}** pada **{tgl_str}** antara {group.iloc[i][k_mapel]} dan {group.iloc[i+1][k_mapel]}")
                    bentrok = True
    
    if not bentrok: st.success("✅ Semua jadwal aman.")

    # ==========================================
    # VISUALISASI DENGAN TEKS & GARIS VERTIKAL
    # ==========================================
    if k_studio in df_filtered.columns and k_pengajar in df_filtered.columns and len(df_filtered) > 0:
        
        # Untuk mode semua data, kita tambahkan tanggal ke nama studio agar grafiknya jelas
        if mode == "Tampilkan Semua Data":
            df_filtered['STUDIO_TANGGAL'] = df_filtered[k_studio] + " (" + df_filtered['Date_Obj'].astype(str) + ")"
            y_axis_col = 'STUDIO_TANGGAL'
        else:
            y_axis_col = k_studio

        fig = px.timeline(
            df_filtered, 
            x_start="Waktu_Mulai", 
            x_end="Waktu_Selesai", 
            y=y_axis_col, 
            color=k_pengajar, 
            hover_name=k_mapel,
            text=k_pengajar
        )
        
        fig.update_yaxes(autorange="reversed")
        fig.update_traces(textposition='inside', insidetextanchor='middle')
        
        # Konfigurasi Sumbu X
        fig.update_xaxes(
            tickformat='%d %b\n%H:%M' if mode == "Tampilkan Semua Data" else '%H:%M',
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            griddash='dot'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # Tabel Data
    st.subheader("📋 Tabel Data")
    df_tampil = df_filtered.drop(columns=['Date_Obj', 'Waktu_Mulai', 'Waktu_Selesai', 'STUDIO_TANGGAL'], errors='ignore')
    st.dataframe(df_tampil.astype(str).replace(['nan', 'None', '<NA>', 'NaN'], '-'), use_container_width=True)