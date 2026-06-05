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
# 2. FUNGSI PENARIKAN DATA SUPER PINTAR
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
        
        # Hapus kolom duplikat agar tidak error di Plotly
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    except Exception as e:
        st.error(f"Gagal menarik data dari Google Sheets. Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Data kosong atau belum bisa dimuat.")
    st.stop()

# ==========================================
# 3. FUNGSI PEMROSESAN WAKTU
# ==========================================
def process_time_columns(df):
    df_clean = df.copy()
    start_times = []
    end_times = []
    
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
# 4. FILTERING SIDEBAR (DENGAN KALENDER)
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")

def convert_to_date(date_str):
    try:
        # Mengambil bagian tanggal saja (misal: "01 Juni 2026")
        date_part = str(date_str).split(', ')[1] 
        return datetime.strptime(date_part, '%d %B %Y')
    except:
        return None

kolom_tanggal = 'Hari Tanggal' if 'Hari Tanggal' in df.columns else df.columns[0]
df['Date_Obj'] = df[kolom_tanggal].apply(convert_to_date)

pilih_tanggal_dt = st.sidebar.date_input(
    "Pilih Tanggal Pantauan:",
    value=datetime.today()
)

df_hari_ini = df[df['Date_Obj'].dt.date == pilih_tanggal_dt].copy()
df_hari_ini = process_time_columns(df_hari_ini)

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 5. ENGINE DETEKSI BENTROK
# ==========================================
st.markdown(f"### Jadwal untuk: **{pilih_tanggal_dt.strftime('%d %B %Y')}**")

kolom_studio = 'STUDIO' if 'STUDIO' in df.columns else 'Studio'
kolom_mapel = 'MAPEL' if 'MAPEL' in df.columns else 'Mapel'
kolom_waktu_asli = 'WAKTU' if 'WAKTU' in df.columns else 'Waktu'
kolom_pengajar = 'PENGAJAR' if 'PENGAJAR' in df.columns else df.columns[3]

bentrok_list = []
if not df_hari_ini.empty:
    for studio, group in df_hari_ini.groupby(kolom_studio):
        group = group.sort_values(by='Waktu_Mulai')
        prev_end = pd.NaT
        prev_mapel = ""
        prev_waktu = ""
        
        for index, row in group.iterrows():
            if pd.notna(prev_end) and row['Waktu_Mulai'] < prev_end:
                bentrok_list.append({'Studio': studio, 'A1': f"{prev_mapel} ({prev_waktu})", 'A2': f"{row[kolom_mapel]} ({row[kolom_waktu_asli]})"})
            
            if pd.isna(prev_end) or row['Waktu_Selesai'] > prev_end:
                prev_end = row['Waktu_Selesai']
                prev_mapel = row[kolom_mapel]
                prev_waktu = row[kolom_waktu_asli]

if bentrok_list:
    st.error("🚨 TERDETEKSI BENTROK!")
    for b in bentrok_list:
        st.warning(f"**{b['Studio']}**: {b['A1']} vs {b['A2']}")
else:
    st.success("✅ Jadwal Aman")

# ==========================================
# 6. VISUALISASI TIMELINE
# ==========================================
if not df_hari_ini.empty:
    fig = px.timeline(df_hari_ini, x_start="Waktu_Mulai", x_end="Waktu_Selesai", y=kolom_studio, color=kolom_pengajar, hover_name=kolom_mapel)
    fig.update_yaxes(autorange="reversed")
    fig.layout.xaxis.tickformat = '%H:%M'
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. TABEL DETAIL
# ==========================================
st.subheader("📋 Detail Jadwal")
cols = ['WAKTU', 'STUDIO', 'PENGAJAR', 'MAPEL', 'KELAS']
tampil = [c for c in cols if c in df_hari_ini.columns]
st.dataframe(df_hari_ini[tampil], use_container_width=True)