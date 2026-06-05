import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale

# Pengaturan locale untuk mengenali nama bulan Indonesia
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except:
    pass # Jika sistem server tidak mendukung, kita gunakan cara manual

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
        header_row_idx = 0
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Hari Tanggal', case=False, na=False).any():
                header_row_idx = i
                break
        
        df = df_raw.iloc[header_row_idx+1:].copy()
        df.columns = df_raw.iloc[header_row_idx].astype(str).str.strip()
        df = df.reset_index(drop=True)
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except Exception as e:
        st.error(f"Error memuat data: {e}")
        return pd.DataFrame()

df = load_data()

# ==========================================
# 3. FUNGSI PENGOLAHAN TANGGAL & WAKTU
# ==========================================
def parse_date(date_str):
    """Mengubah 'Senin, 01 Juni 2026' menjadi objek date"""
    try:
        clean_str = str(date_str).split(', ')[-1].strip()
        return datetime.strptime(clean_str, '%d %B %Y').date()
    except:
        return None

if not df.empty:
    kolom_tanggal = 'Hari Tanggal' if 'Hari Tanggal' in df.columns else df.columns[0]
    df['Date_Obj'] = df[kolom_tanggal].apply(parse_date)

# ==========================================
# 4. SIDEBAR KALENDER & FILTER
# ==========================================
st.sidebar.header("⚙️ Filter Jadwal")
pilih_tanggal_dt = st.sidebar.date_input("Pilih Tanggal:", value=datetime.today())

# Filter data
df_hari_ini = df[df['Date_Obj'] == pilih_tanggal_dt].copy()

# Proses Waktu untuk Gantt Chart
if not df_hari_ini.empty:
    kolom_waktu = 'WAKTU' if 'WAKTU' in df_hari_ini.columns else 'Waktu'
    start_list, end_list = [], []
    for w in df_hari_ini[kolom_waktu]:
        try:
            m, s = str(w).upper().replace('WIB', '').replace('.', ':').split('-')
            today = datetime.today().strftime('%Y-%m-%d')
            start_list.append(pd.to_datetime(f"{today} {m.strip()}"))
            end_list.append(pd.to_datetime(f"{today} {s.strip()}"))
        except:
            start_list.append(pd.NaT); end_list.append(pd.NaT)
    df_hari_ini['Waktu_Mulai'] = start_list
    df_hari_ini['Waktu_Selesai'] = end_list
    df_hari_ini = df_hari_ini.dropna(subset=['Waktu_Mulai'])

# ==========================================
# 5. TAMPILAN DASHBOARD
# ==========================================
if df_hari_ini.empty:
    st.info(f"Tidak ada jadwal ditemukan untuk tanggal: {pilih_tanggal_dt}")
else:
    col1, col2 = st.columns(2)
    col1.metric("Total Jadwal", len(df_hari_ini))
    
    # Deteksi Bentrok
    bentrok = False
    for studio, group in df_hari_ini.groupby('STUDIO'):
        group = group.sort_values('Waktu_Mulai')
        for i in range(len(group)-1):
            if group.iloc[i+1]['Waktu_Mulai'] < group.iloc[i]['Waktu_Selesai']:
                st.error(f"⚠️ Bentrok di {studio}!")
                bentrok = True
    if not bentrok: st.success("✅ Semua jadwal aman.")

    # Timeline
    fig = px.timeline(df_hari_ini, x_start="Waktu_Mulai", x_end="Waktu_Selesai", y="STUDIO", color="PENGAJAR")
    fig.update_yaxes(autorange="reversed")
    fig.layout.xaxis.tickformat = '%H:%M'
    st.plotly_chart(fig, use_container_width=True)

    # Tabel
    st.dataframe(df_hari_ini.drop(columns=['Date_Obj', 'Waktu_Mulai', 'Waktu_Selesai'], errors='ignore'), use_container_width=True)