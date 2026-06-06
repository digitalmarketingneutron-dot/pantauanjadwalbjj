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
mode = st.sidebar.radio("Mode Tampilan:", [
    "Pilih Tanggal Spesifik", 
    "Pilih Rentang Tanggal", 
    "Tampilkan Semua Data"
])

if mode == "Pilih Tanggal Spesifik":
    tanggal_input = st.sidebar.date_input("Pilih Tanggal:", value=datetime.today())
    if isinstance(tanggal_input, (list, tuple)):
        pilih_tanggal_dt = tanggal_input[0] if len(tanggal_input) > 0 else datetime.today().date()
    else:
        pilih_tanggal_dt = tanggal_input
    df_filtered = df[df['Date_Obj'] == pilih_tanggal_dt].copy()

elif mode == "Pilih Rentang Tanggal":
    rentang_input = st.sidebar.date_input(
        "Pilih Rentang Tanggal:", 
        value=(datetime.today().date(), datetime.today().date() + pd.Timedelta(days=3))
    )
    if isinstance(rentang_input, (list, tuple)):
        if len(rentang_input) == 2:
            start_date, end_date = rentang_input
            df_filtered = df[(df['Date_Obj'] >= start_date) & (df['Date_Obj'] <= end_date)].copy()
        elif len(rentang_input) == 1:
            start_date = rentang_input[0]
            df_filtered = df[df['Date_Obj'] == start_date].copy()
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df[df['Date_Obj'] == rentang_input].copy()
else:
    df_filtered = df.copy()

if not df_filtered.empty:
    kolom_waktu = [col for col in df_filtered.columns if 'WAKTU' in str(col)]
    nama_kolom_waktu = kolom_waktu[0] if len(kolom_waktu) > 0 else 'WAKTU'
    
    if nama_kolom_waktu in df_filtered.columns:
        start_list, end_list = [], []
        for idx, row in df_filtered.iterrows():
            w = row[nama_kolom_waktu]
            d = row['Date_Obj']
            
            val_start = pd.NaT
            val_end = pd.NaT
            
            try:
                m, s = str(w).upper().replace('WIB', '').replace('.', ':').split('-')
                date_str = d.strftime('%Y-%m-%d') if pd.notna(d) else datetime.today().strftime('%Y-%m-%d')
                
                val_start = pd.to_datetime(f"{date_str} {m.strip()}")
                val_end = pd.to_datetime(f"{date_str} {s.strip()}")
            except:
                pass
            
            start_list.append(val_start)
            end_list.append(val_end)
                
        df_filtered['Waktu_Mulai'] = start_list
        df_filtered['Waktu_Selesai'] = end_list
        
        df_filtered = df_filtered.dropna(subset=['Waktu_Mulai', 'Waktu_Selesai'])

# ==========================================
# 5. TAMPILAN DASHBOARD
# ==========================================
if df_filtered.empty:
    st.info("Tidak ada jadwal yang valid untuk ditampilkan pada filter yang dipilih.")
else:
    st.metric("Total Jadwal Ditampilkan", len(df_filtered))
    
    k_studio = [col for col in df_filtered.columns if 'STUDIO' in str(col)]
    k_studio = k_studio[0] if k_studio else 'STUDIO'
    
    k_mapel = [col for col in df_filtered.columns if 'MAPEL' in str(col)]
    k_mapel = k_mapel[0] if k_mapel else 'MAPEL'
    
    k_pengajar = [col for col in df_filtered.columns if 'PENGAJAR' in str(col)]
    k_pengajar = k_pengajar[0] if k_pengajar else 'PENGAJAR'
    
    bentrok = False
    if k_studio in df_filtered.columns and k_mapel in df_filtered.columns:
        for (studio, tgl), group in df_filtered.groupby([k_studio, 'Date_Obj']):
            group = group.sort_values('Waktu_Mulai')
            for i in range(len(group)-1):
                if group.iloc[i+1]['Waktu_Mulai'] < group.iloc[i]['Waktu_Selesai']:
                    tgl_str = tgl.strftime('%d-%b-%Y') if pd.notna(tgl) else "Tanggal Tidak Diketahui"
                    st.error(f"⚠️ Bentrok di **{studio}** pada **{tgl_str}** antara {group.iloc[i][k_mapel]} dan {group.iloc[i+1][k_mapel]}")
                    bentrok = True
    
    if not bentrok: st.success("✅ Semua jadwal aman.")

    if k_studio in df_filtered.columns and k_pengajar in df_filtered.columns and len(df_filtered) > 0:
        if mode in ["Tampilkan Semua Data", "Pilih Rentang Tanggal"]:
            df_filtered['STUDIO_TANGGAL'] = df_filtered[k_studio].astype(str) + " (" + df_filtered['Date_Obj'].astype(str) + ")"
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
        
        # ==========================================
        # ENGINE PENGGARIS CUSTOM (TEBAL & TIPIS)
        # ==========================================
        min_time = df_filtered['Waktu_Mulai'].min()
        max_time = df_filtered['Waktu_Selesai'].max()
        
        if pd.notna(min_time) and pd.notna(max_time):
            # Membulatkan jam mulai dan selesai
            start_grid = min_time.replace(minute=0, second=0)
            end_grid = max_time.replace(minute=0, second=0) + pd.Timedelta(hours=1)
            
            # Buat rentang waktu setiap 30 menit
            grid_ticks = pd.date_range(start=start_grid, end=end_grid, freq='30min')
            
            # Membatasi jumlah tik untuk mencegah error jika data terlalu banyak (>150 blok)
            if len(grid_ticks) <= 150:
                tickvals = []
                ticktext = []
                for t in grid_ticks:
                    tickvals.append(t)
                    x_str = t.strftime("%Y-%m-%d %H:%M:%S") # Format waktu ke garis vertikal
                    
                    if t.minute == 0:
                        # SETTINGAN JAM TEPAT (8:00, 9:00): FONT TEBAL & GARIS TEBAL
                        lbl = t.strftime('%H:%M')
                        if mode != "Pilih Tanggal Spesifik" and (t.hour == 0 or t == start_grid):
                            lbl = f"{t.strftime('%d %b')} {lbl}" # Tambah info tanggal di jam pertama
                        
                        ticktext.append(f"<b><span style='font-size: 15px; color: #111111;'>{lbl}</span></b>")
                        fig.add_vline(x=x_str, line_width=2, line_color="rgba(80, 80, 80, 0.4)")
                    else:
                        # SETTINGAN JAM SETENGAH (8:30, 9:30): FONT TIPIS & GARIS PUTUS
                        ticktext.append(f"<span style='font-size: 11px; color: #999999;'>{t.strftime('%H:%M')}</span>")
                        fig.add_vline(x=x_str, line_width=1, line_dash="dot", line_color="rgba(180, 180, 180, 0.4)")
                
                # Matikan grid otomatis bawaan karena sudah digambar manual
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=tickvals,
                    ticktext=ticktext,
                    showgrid=False,
                    showline=True,
                    linewidth=2,
                    linecolor='black',
                    ticks='outside',
                    tickwidth=1,
                    ticklen=6
                )
            else:
                # Fallback aman jika data rentangnya sampai berbulan-bulan
                fig.update_xaxes(
                    tickformat='%d %b\n%H:%M' if mode != "Pilih Tanggal Spesifik" else '%H:%M',
                    showline=True, linewidth=2, linecolor='black',
                    showgrid=True, gridwidth=1, gridcolor='rgba(200,200,200,0.4)', griddash='dot',
                    dtick=1800000
                )
        
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Tabel Data")
    df_tampil = df_filtered.drop(columns=['Date_Obj', 'Waktu_Mulai', 'Waktu_Selesai', 'STUDIO_TANGGAL'], errors='ignore')
    st.dataframe(df_tampil.astype(str).replace(['nan', 'None', '<NA>', 'NaN'], '-'), use_container_width=True)