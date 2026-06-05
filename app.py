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
# 2. FUNGSI PENARIKAN DATA (DENGAN CACHE)
# ==========================================
# Data diperbarui otomatis setiap 1 menit (60 detik)
@st.cache_data(ttl=60)
def load_data():
    # URL Ekspor CSV dari Google Sheets Anda
    sheet_id = "1wNQHGvbtB1rRq0Mjw4g00q849MTZGJE9AFqrfASyqI4"
    gid = "1652385748"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
        # Hapus baris yang kosong semua
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Gagal menarik data dari Google Sheets. Pastikan akses link terbuka (Anyone with the link). Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# ==========================================
# 3. FUNGSI PEMROSESAN WAKTU & DETEKSI
# ==========================================
def process_time_columns(df):
    """Mengubah kolom string '13.00-14.30 WIB' menjadi datetime untuk kalkulasi"""
    df_clean = df.copy()
    
    # Inisialisasi list untuk menyimpan hasil parsing
    start_times = []
    end_times = []
    
    for waktu in df_clean['WAKTU']:
        try:
            # Membersihkan teks
            waktu_str = str(waktu).upper().replace('WIB', '').strip()
            waktu_str = waktu_str.replace('.', ':') # ubah 13.00 jadi 13:00
            
            mulai_str, selesai_str = waktu_str.split('-')
            
            # Kita gunakan tanggal dummy hari ini hanya untuk keperluan kalkulasi grafik (Timeline)
            dummy_date = datetime.today().strftime('%Y-%m-%d')
            start_dt = pd.to_datetime(f"{dummy_date} {mulai_str.strip()}")
            end_dt = pd.to_datetime(f"{dummy_date} {selesai_str.strip()}")
            
            start_times.append(start_dt)
            end_times.append(end_dt)
        except:
            # Jika format salah/kosong
            start_times.append(pd.NaT)
            end_times.append(pd.NaT)
            
    df_clean['Waktu_Mulai'] = start_times
    df_clean['Waktu_Selesai'] = end_times
    
    # Hapus baris yang gagal di-parsing waktunya
    return df_clean.dropna(subset=['Waktu_Mulai', 'Waktu_Selesai'])

# ==========================================
# 4. FILTERING & SIDEBAR UI
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")

# Filter Tanggal (Unik dari data)
daftar_tanggal = df['Hari Tanggal'].dropna().unique()
if len(daftar_tanggal) > 0:
    pilih_tanggal = st.sidebar.selectbox("Pilih Tanggal Pantauan:", daftar_tanggal)
else:
    st.sidebar.warning("Tidak ada data tanggal ditemukan.")
    st.stop()

# Filter data berdasarkan tanggal terpilih
df_hari_ini = df[df['Hari Tanggal'] == pilih_tanggal]
df_hari_ini = process_time_columns(df_hari_ini)

# Tombol Refresh Manual
if st.sidebar.button("🔄 Refresh Data Sekarang"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("Aplikasi ini otomatis mendeteksi jika ada dua jadwal atau lebih yang menggunakan studio yang sama pada jam yang saling tumpang tindih.")

# ==========================================
# 5. METRIK RINGKASAN
# ==========================================
st.markdown(f"### Jadwal untuk: **{pilih_tanggal}**")

total_jadwal = len(df_hari_ini)
total_studio = df_hari_ini['STUDIO'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("📚 Total Kelas / Jadwal", total_jadwal)
col2.metric("🎙️ Studio Terpakai", total_studio)

# ==========================================
# 6. ENGINE DETEKSI BENTROK (CLASH DETECTION)
# ==========================================
bentrok_list = []

# Kelompokkan per Studio
for studio, group in df_hari_ini.groupby('STUDIO'):
    # Urutkan berdasarkan waktu mulai
    group = group.sort_values(by='Waktu_Mulai')
    
    prev_end = pd.NaT
    prev_mapel = ""
    prev_waktu = ""
    
    for index, row in group.iterrows():
        curr_start = row['Waktu_Mulai']
        curr_end = row['Waktu_Selesai']
        
        # Logika Bentrok: Waktu mulai kelas ini lebih kecil dari waktu selesai kelas sebelumnya
        if pd.notna(prev_end) and pd.notna(curr_start):
            if curr_start < prev_end:
                bentrok_list.append({
                    'Studio': studio,
                    'Agenda 1': f"{prev_mapel} ({prev_waktu})",
                    'Agenda 2': f"{row['MAPEL']} ({row['WAKTU']})"
                })
        
        # Update pointer (ambil waktu selesai yang paling lama)
        if pd.isna(prev_end) or curr_end > prev_end:
            prev_end = curr_end
            prev_mapel = row['MAPEL']
            prev_waktu = row['WAKTU']

# Tampilkan Hasil Deteksi
if bentrok_list:
    col3.metric("⚠️ Status", f"{len(bentrok_list)} Bentrok!", delta_color="inverse")
    st.error("🚨 **PERINGATAN: TERDETEKSI PENGGUNAAN STUDIO YANG BENTROK!** 🚨")
    for b in bentrok_list:
        st.warning(f"**{b['Studio']}** ➔ {b['Agenda 1']} **TABRAKAN DENGAN** {b['Agenda 2']}")
else:
    col3.metric("✅ Status", "Aman / Clear")
    st.success("✅ **Sistem Aman!** Tidak ada studio yang digunakan secara bersamaan.")

# ==========================================
# 7. VISUALISASI TIMELINE (GANTT CHART)
# ==========================================
st.markdown("---")
st.subheader("📈 Timeline Penggunaan Studio")

if not df_hari_ini.empty:
    # Membuat visualisasi Timeline menggunakan Plotly
    fig = px.timeline(
        df_hari_ini, 
        x_start="Waktu_Mulai", 
        x_end="Waktu_Selesai", 
        y="STUDIO",
        color="PENGAJAR", # Warna dibedakan per pengajar
        hover_name="MAPEL",
        hover_data={"Waktu_Mulai": False, "Waktu_Selesai": False, "WAKTU": True, "KELAS": True},
        title=f"Jadwal Pemakaian Studio - {pilih_tanggal}"
    )
    fig.update_yaxes(autorange="reversed") # Agar studio berurut dari atas ke bawah
    fig.update_layout(
        xaxis_title="Jam",
        yaxis_title="Studio",
        showlegend=True,
        height=400
    )
    # Format sumbu X hanya menampilkan jam
    fig.layout.xaxis.tickformat = '%H:%M'
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Tidak ada data jadwal untuk divisualisasikan pada tanggal ini.")

# ==========================================
# 8. TABEL DATA MENTAH
# ==========================================
st.markdown("---")
st.subheader("📋 Detail Data Jadwal")
# Tampilkan tabel yang lebih bersih, hilangkan kolom dummy kalkulasi
kolom_tampil = ['WAKTU', 'STUDIO', 'PENGAJAR', 'MAPEL', 'KELAS', 'OP ZOOM', 'LINK ZOOM']
st.dataframe(df_hari_ini[kolom_tampil], use_container_width=True)

st.caption("Aplikasi Pantauan Jadwal Otomatis © 2024")