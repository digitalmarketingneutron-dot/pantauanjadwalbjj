import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Pantauan Jadwal", page_icon="📅", layout="wide")
st.title("📊 Dashboard Pantauan & Antisipasi Jadwal Studio")

# ==========================================
# 2. FUNGSI PENARIKAN DATA SUPER PINTAR (DENGAN CACHE)
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1wNQHGvbtB1rRq0Mjw4g00q849MTZGJE9AFqrfASyqI4"
    gid = "1652385748"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        # Baca semua data tanpa peduli letak headernya (baris judul)
        df_raw = pd.read_csv(csv_url, header=None)
        
        # Fitur Pintar: Cari baris mana yang benar-benar berisi teks "Hari Tanggal"
        header_row_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Hari Tanggal', case=False, na=False).any():
                header_row_idx = i
                break
                
        # Jadikan baris yang ditemukan tersebut sebagai nama Kolom yang sesungguhnya
        df = df_raw.iloc[header_row_idx+1:].copy()
        df.columns = df_raw.iloc[header_row_idx]
        df = df.reset_index(drop=True)
        
        # Hapus baris yang isinya kosong semua (jika ada sisa baris kosong di bawah sheet)
        df = df.dropna(how='all')
        
        # Bersihkan nama kolom dari spasi yang tidak sengaja terketik di Google Sheet
        df.columns = df.columns.astype(str).str.strip()
        
        # --- SOLUSI ERROR PLOTLY DUPLICATE ---
        # Membuang nama kolom yang sama persis (duplikat) agar Plotly bisa merender grafik
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    except Exception as e:
        st.error(f"Gagal menarik data dari Google Sheets. Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Data kosong atau belum bisa dimuat. Pastikan tabel diisi dengan benar.")
    st.stop()

# ==========================================
# 3. FUNGSI PEMROSESAN WAKTU & DETEKSI
# ==========================================
def process_time_columns(df):
    """Mengubah string '13.00-14.30 WIB' menjadi format waktu yang bisa dihitung mesin"""
    df_clean = df.copy()
    start_times = []
    end_times = []
    
    # Pastikan nama kolom menggunakan huruf besar dan tanpa spasi tersembunyi
    kolom_waktu = 'WAKTU' if 'WAKTU' in df_clean.columns else 'Waktu'
    
    for waktu in df_clean[kolom_waktu]:
        try:
            waktu_str = str(waktu).upper().replace('WIB', '').strip()
            waktu_str = waktu_str.replace('.', ':') 
            
            mulai_str, selesai_str = waktu_str.split('-')
            
            dummy_date = datetime.today().strftime('%Y-%m-%d')
            start_dt = pd.to_datetime(f"{dummy_date} {mulai_str.strip()}")
            end_dt = pd.to_datetime(f"{dummy_date} {selesai_str.strip()}")
            
            start_times.append(start_dt)
            end_times.append(end_dt)
        except:
            start_times.append(pd.NaT)
            end_times.append(pd.NaT)
            
    df_clean['Waktu_Mulai'] = start_times
    df_clean['Waktu_Selesai'] = end_times
    
    return df_clean.dropna(subset=['Waktu_Mulai', 'Waktu_Selesai'])

# ==========================================
# 4. FILTERING & SIDEBAR UI
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")

# Ambil nama kolom tanggal dengan aman
kolom_tanggal = 'Hari Tanggal' if 'Hari Tanggal' in df.columns else df.columns[0]
daftar_tanggal = df[kolom_tanggal].dropna().unique()

if len(daftar_tanggal) > 0:
    pilih_tanggal = st.sidebar.selectbox("Pilih Tanggal Pantauan:", daftar_tanggal)
else:
    st.sidebar.warning("Tidak ada data tanggal ditemukan.")
    st.stop()

df_hari_ini = df[df[kolom_tanggal] == pilih_tanggal]
df_hari_ini = process_time_columns(df_hari_ini)

if st.sidebar.button("🔄 Refresh Data Sekarang"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Aplikasi ini otomatis mendeteksi jika ada jadwal yang menggunakan studio yang sama pada jam yang saling tumpang tindih.")

# ==========================================
# 5. METRIK RINGKASAN & ENGINE DETEKSI (CLASH)
# ==========================================
st.markdown(f"### Jadwal untuk: **{pilih_tanggal}**")

total_jadwal = len(df_hari_ini)
kolom_studio = 'STUDIO' if 'STUDIO' in df.columns else 'Studio'
total_studio = df_hari_ini[kolom_studio].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("📚 Total Kelas / Jadwal", total_jadwal)
col2.metric("🎙️ Studio Terpakai", total_studio)

bentrok_list = []
kolom_mapel = 'MAPEL' if 'MAPEL' in df.columns else 'Mapel'
kolom_waktu_asli = 'WAKTU' if 'WAKTU' in df.columns else 'Waktu'

# Pengecekan Bentrok
if not df_hari_ini.empty and kolom_studio in df_hari_ini.columns:
    for studio, group in df_hari_ini.groupby(kolom_studio):
        group = group.sort_values(by='Waktu_Mulai')
        prev_end = pd.NaT
        prev_mapel = ""
        prev_waktu = ""
        
        for index, row in group.iterrows():
            curr_start = row['Waktu_Mulai']
            curr_end = row['Waktu_Selesai']
            
            if pd.notna(prev_end) and pd.notna(curr_start):
                if curr_start < prev_end:
                    bentrok_list.append({
                        'Studio': studio,
                        'Agenda 1': f"{prev_mapel} ({prev_waktu})",
                        'Agenda 2': f"{row.get(kolom_mapel, 'Kelas')} ({row.get(kolom_waktu_asli, '')})"
                    })
            
            if pd.isna(prev_end) or curr_end > prev_end:
                prev_end = curr_end
                prev_mapel = row.get(kolom_mapel, 'Kelas')
                prev_waktu = row.get(kolom_waktu_asli, '')

if bentrok_list:
    col3.metric("⚠️ Status", f"{len(bentrok_list)} Bentrok!", delta_color="inverse")
    st.error("🚨 **PERINGATAN: TERDETEKSI PENGGUNAAN STUDIO YANG BENTROK!** 🚨")
    for b in bentrok_list:
        st.warning(f"**{b['Studio']}** ➔ {b['Agenda 1']} **TABRAKAN DENGAN** {b['Agenda 2']}")
else:
    col3.metric("✅ Status", "Aman / Clear")
    st.success("✅ **Sistem Aman!** Tidak ada studio yang digunakan secara bersamaan.")

# ==========================================
# 6. VISUALISASI TIMELINE (GANTT CHART)
# ==========================================
st.markdown("---")
st.subheader("📈 Timeline Penggunaan Studio")

kolom_pengajar = 'PENGAJAR' if 'PENGAJAR' in df.columns else df.columns[3]

if not df_hari_ini.empty:
    fig = px.timeline(
        df_hari_ini, 
        x_start="Waktu_Mulai", 
        x_end="Waktu_Selesai", 
        y=kolom_studio,
        color=kolom_pengajar,
        hover_name=kolom_mapel,
        title=f"Jadwal Pemakaian Studio - {pilih_tanggal}"
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(xaxis_title="Jam", yaxis_title="Studio", height=400)
    fig.layout.xaxis.tickformat = '%H:%M'
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Tidak ada data jadwal untuk divisualisasikan pada tanggal ini.")

# ==========================================
# 7. TABEL DATA MENTAH
# ==========================================
st.markdown("---")
st.subheader("📋 Detail Data Jadwal")

# Ditulis terpisah agar tidak mudah terpotong saat proses copy-paste
daftar_kolom_utama = ['WAKTU', 'STUDIO', 'PENGAJAR', 'MAPEL', 'KELAS', 'OP ZOOM']
kolom_tampil = [k for k in daftar_kolom_utama if k in df_hari_ini.columns]

if not kolom_tampil:
    kolom_tampil = df_hari_ini.columns.tolist() # Tampilkan semua jika kolom tidak dikenali

st.dataframe(df_hari_ini[kolom_tampil], use_container_width=True)
st.caption("Aplikasi Pantauan Jadwal Otomatis")