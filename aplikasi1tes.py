import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Family Finance", page_icon="👨‍👩‍👧‍👦", layout="wide")

# --- 1. KONEKSI KE GOOGLE SHEETS ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/1JznUhueIF3ZMbqB5DNKH9Lrtwjry5YGpSwfAgglhDwE/edit#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_transaksi = conn.read(spreadsheet=URL_SHEET, worksheet="Transaksi", ttl=0).dropna(how="all")
    df_kantong = conn.read(spreadsheet=URL_SHEET, worksheet="Kantong", ttl=0).dropna(how="all")
    df_anggota = conn.read(spreadsheet=URL_SHEET, worksheet="Anggota", ttl=0).dropna(how="all")
except Exception as e:
    st.error(f"Koneksi gagal. Detail error dari Google: {e}")
    st.stop()

# Memastikan tipe data kolom angka benar
if not df_transaksi.empty:
    df_transaksi["Jumlah"] = pd.to_numeric(df_transaksi["Jumlah"], errors="coerce").fillna(0)
else:
    df_transaksi = pd.DataFrame(columns=["Tanggal", "Pengguna", "Tipe", "Kategori", "Jumlah"])

if not df_kantong.empty:
    df_kantong["Target Dana"] = pd.to_numeric(df_kantong["Target Dana"], errors="coerce").fillna(0)
    df_kantong["Terkumpul"] = pd.to_numeric(df_kantong["Terkumpul"], errors="coerce").fillna(0)
else:
    df_kantong = pd.DataFrame(columns=["Nama Kantong", "Pemilik", "Target Dana", "Terkumpul"])

# Amankan kolom password di dataframe anggota
if "Password" not in df_anggota.columns:
    df_anggota["Password"] = ""

# --- LOGIKA DINAMIS ANGGOTA KELUARGA ---
if not df_anggota.empty:
    LIST_USER = df_anggota["Nama Anggota"].dropna().astype(str).tolist()
    # Membuat kamus data (dictionary) untuk mencocokkan username dan password
    KREDENSIAL = dict(zip(df_anggota["Nama Anggota"].astype(str), df_anggota["Password"].astype(str)))
else:
    LIST_USER = ["Suami", "Istri"]
    KREDENSIAL = {"Suami": "123", "Istri": "123"}

LIST_USER_LENGKAP = LIST_USER + ["Keluarga (Bersama)"]


# ==========================================
# SYSTEM SISTEM LOGIN (SESSION STATE)
# ==========================================
if "login_sukses" not in st.session_state:
    st.session_state["login_sukses"] = False
    st.session_state["user_aktif"] = ""

# JIKA BELUM LOGIN, TAMPILKAN HALAMAN LOGIN
if not st.session_state["login_sukses"]:
    st.container()
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    
    with col_l2:
        st.write("")
        st.write("")
        st.markdown("<h1 style='text-align: center;'>🔐 Login Family Finance</h1>", unsafe_allow_html=True)
        st.write("Silakan masukkan nama anggota dan password Anda untuk mengakses cloud keuangan keluarga.")
        
        with st.form("form_login"):
            input_user = st.selectbox("Pilih Nama Anggota:", LIST_USER)
            input_pass = st.text_input("Masukkan Password:", type="password")
            tombol_login = st.form_submit_button("Masuk ke Dashboard")
            
        if tombol_login:
            # Validasi kecocokan password dari Google Sheets
            if input_user in KREDENSIAL and input_pass == KREDENSIAL[input_user]:
                st.session_state["login_sukses"] = True
                st.session_state["user_aktif"] = input_user
                st.success(f"Selamat datang kembali, {input_user}!")
                st.rerun()
            else:
                st.error("Password yang Anda masukkan salah. Silakan coba lagi.")
    st.stop()  # Menghentikan kode di sini agar halaman utama tidak bocor sebelum login


# ==========================================
# JIKA SUDAH LOGIN, TAMPILKAN SELURUH APLIKASI
# ==========================================

# --- 2. LOGIKA HITUNG SALDO KANTONG (REAL-TIME) ---
DAFTAR_KANTONG = {}
MAP_PEMILIK_KANTONG = {}
isi_kantong = {}

for _, row in df_kantong.iterrows():
    if pd.notna(row["Nama Kantong"]):
        nama_k = row["Nama Kantong"]
        DAFTAR_KANTONG[nama_k] = float(row["Target Dana"])
        MAP_PEMILIK_KANTONG[nama_k] = row["Pemilik"]
        
        buku_kantong = df_transaksi[df_transaksi["Kategori"] == nama_k]
        plus = buku_kantong[buku_kantong["Tipe"] == "Alokasi Masuk"]["Jumlah"].sum()
        minus = buku_kantong[buku_kantong["Tipe"] == "Pengeluaran (Dari Kantong)"]["Jumlah"].sum()
        isi_kantong[nama_k] = float(plus - minus)

if not DAFTAR_KANTONG:
    DAFTAR_KANTONG = {"Kantong Operasional Bersama": 0}
    MAP_PEMILIK_KANTONG["Kantong Operasional Bersama"] = "Keluarga (Bersama)"
    isi_kantong["Kantong Operasional Bersama"] = 0.0

for idx, row in df_kantong.iterrows():
    nama_k = row["Nama Kantong"]
    if nama_k in isi_kantong:
        df_kantong.loc[idx, "Terkumpul"] = isi_kantong[nama_k]

# --- 3. NAVIGASI HALAMAN TABS ---
tab_dashboard, tab_pengaturan = st.tabs([
    "👨‍👩‍👧‍👦 Dashboard & Laporan Keluarga", 
    "⚙️ Pengaturan Struktur (Kantong & Anggota)"
])

# ==========================================
# HALAMAN 1: DASHBOARD & LAPORAN INTEGRASI
# ==========================================
with tab_dashboard:
    # Menampilkan info user yang sedang login di pojok atas beserta tombol logout
    kl_judul, kl_logout = st.columns([4, 1])
    with kl_judul:
        st.title("👨‍👩‍👧‍👦 Family Finance: Hub Dashboard Utama")
    with kl_logout:
        st.write(f"👤 Login sebagai: **{st.session_state['user_aktif']}**")
        if st.button("🚪 Keluar (Logout)"):
            st.session_state["login_sukses"] = False
            st.session_state["user_aktif"] = ""
            st.rerun()
            
    st.write("Sistem Pencatatan Konsolidasi Finansial Rumah Tangga Real-Time")
    
    total_masuk_fam = float(df_transaksi[df_transaksi["Tipe"] == "Pemasukan"]["Jumlah"].sum())
    total_keluar_fam = float(df_transaksi[df_transaksi["Tipe"] == "Pengeluaran"]["Jumlah"].sum())
    total_dialokasikan_fam = sum(isi_kantong.values())
    saldo_bebas_fam = total_masuk_fam - total_keluar_fam - total_dialokasikan_fam

    # SECTION 1: NERACA GABUNGAN KELUARGA
    st.subheader("🏠 1. Estimasi Neraca Gabungan Keluarga")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Pemasukan Keluarga", f"Rp {total_masuk_fam:,.0f}")
    k2.metric("Total Pengeluaran Umum", f"Rp {total_keluar_fam:,.0f}")
    k3.metric("Saldo Bebas Bersama", f"Rp {saldo_bebas_fam:,.0f}", 
              delta="Surplus" if saldo_bebas_fam >= 0 else "Defisit!", delta_color="normal" if saldo_bebas_fam >= 0 else "inverse")
    
    st.divider()

    # SECTION 2: ANALISIS PERSONAL & SIMULASI SALDO DINAMIS
    st.subheader("👤 2. Pusat Analisis & Simulasi Saldo Anggota")
    
    # Otomatis mengarahkan ke nama user yang sedang login, namun tetap bisa melihat anggota lain
    idx_default = LIST_USER.index(st.session_state["user_aktif"]) if st.session_state["user_aktif"] in LIST_USER else 0
    pilihan_user = st.selectbox("Pilih Nama Anggota Keluarga untuk Dilihat:", LIST_USER, index=idx_default)
    
    df_user_transaksi = df_transaksi[df_transaksi["Pengguna"] == pilihan_user]
    pemasukan_pers = float(df_user_transaksi[df_user_transaksi["Tipe"] == "Pemasukan"]["Jumlah"].sum())
    pengeluaran_pers = float(df_user_transaksi[df_user_transaksi["Tipe"] == "Pengeluaran"]["Jumlah"].sum())
    
    total_alokasi_dilakukan_pers = float(df_user_transaksi[df_user_transaksi["Tipe"] == "Alokasi Masuk"]["Jumlah"].sum())
    saldo_simulasi_bebas = pemasukan_pers - pengeluaran_pers - total_alokasi_dilakukan_pers
    
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric(f"Pemasukan {pilihan_user}", f"Rp {pemasukan_pers:,.0f}")
    kp2.metric(f"Pengeluaran {pilihan_user}", f"Rp {pengeluaran_pers:,.0f}")
    kp3.metric(f"Total Alokasi Keluar", f"Rp {total_alokasi_dilakukan_pers:,.0f}")
    kp4.metric(f"Simulasi Saldo Bebas {pilihan_user}", f"Rp {saldo_simulasi_bebas:,.0f}",
               delta="Aman" if saldo_simulasi_bebas >= 0 else "Overbudget!",
               delta_color="normal" if saldo_simulasi_bebas >= 0 else "inverse")
    
    st.write(f"**🎯 Status Kantong Target Pribadi {pilihan_user}:**")
    ada_kantong_pers = False
    for kantong, target in DAFTAR_KANTONG.items():
        if target > 0 and MAP_PEMILIK_KANTONG.get(kantong) == pilihan_user:
            ada_kantong_pers = True
            terkumpul = isi_kantong.get(kantong, 0)
            persen = min(float(terkumpul / target), 1.0)
            st.write(f"- {kantong} (Terkumpul: Rp {terkumpul:,.0f} / Target: Rp {target:,.0f})")
            st.progress(persen)
    if not ada_kantong_pers: 
        st.info(f"Belum ada kantong target khusus milik {pilihan_user}.")
        
    st.divider()

    # SECTION 3: FORM INPUT DATA & GRAFIK
    st.subheader("➕ 3. Input Aktivitas & Visualisasi Distribusi Dana")
    KOL_KIRI, KOL_KANAN = st.columns([1, 1.5])

    with KOL_KIRI:
        with st.form("form_keuangan_fam", clear_on_submit=True):
            # Otomatis mengunci nama pencatat sesuai dengan akun yang login agar praktis
            idx_pencatat = LIST_USER_LENGKAP.index(st.session_state["user_aktif"]) if st.session_state["user_aktif"] in LIST_USER_LENGKAP else 0
            siapa = st.selectbox("Siapa yang mencatat?", LIST_USER_LENGKAP, index=idx_pencatat)
            tipe = st.selectbox("Jenis Aktivitas:", ["Pemasukan", "Pengeluaran", "Alokasi Masuk", "Pengeluaran (Dari Kantong)"])
            
            if tipe in ["Alokasi Masuk", "Pengeluaran (Dari Kantong)"]:
                kategori = st.selectbox("Pilih Kantong Target:", list(DAFTAR_KANTONG.keys()))
            else:
                kategori = st.text_input("Keterangan Kategori / Urusan:", placeholder="Misal: Gaji, Belanja Sayur, Bensin")
                
            jumlah = st.number_input("Jumlah Uang (Rp):", min_value=0, step=50000)
            tombol_simpan = st.form_submit_button("Simpan ke Cloud Keluarga")

        if tombol_simpan and jumlah > 0 and kategori != "":
            waktu = datetime.now().strftime("%Y-%m-%d %H:%M")
            baris_baru = pd.DataFrame([[waktu, siapa, tipe, kategori, jumlah]], columns=["Tanggal", "Pengguna", "Tipe", "Kategori", "Jumlah"])
            df_update_transaksi = pd.concat([df_transaksi, baris_baru], ignore_index=True)
            
            for idx, row in df_kantong.iterrows():
                nk = row["Nama Kantong"]
                buku_k = df_update_transaksi[df_update_transaksi["Kategori"] == nk]
                p = buku_k[buku_k["Tipe"] == "Alokasi Masuk"]["Jumlah"].sum()
                m = buku_k[buku_k["Tipe"] == "Pengeluaran (Dari Kantong)"]["Jumlah"].sum()
                df_kantong.loc[idx, "Terkumpul"] = float(p - m)

            conn.update(spreadsheet=URL_SHEET, worksheet="Transaksi", data=df_update_transaksi)
            conn.update(spreadsheet=URL_SHEET, worksheet="Kantong", data=df_kantong)
            st.success(f"Sukses mencatat data untuk {siapa}!")
            st.rerun()

    with KOL_KANAN:
        data_pie = []
        for k, v in isi_kantong.items():
            if v > 0: data_pie.append({"Komponen": f"[{MAP_PEMILIK_KANTONG.get(k, 'Keluarga')}] {k}", "Jumlah": v})
        if saldo_bebas_fam > 0:
            data_pie.append({"Komponen": "Saldo Bebas Bersama", "Jumlah": saldo_bebas_fam})
            
        if data_pie:
            df_pie = pd.DataFrame(data_pie)
            fig = px.pie(df_pie, values="Jumlah", names="Komponen", hole=0.4, title="Distribusi Alokasi Dana Gabungan")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data alokasi dana.")

    st.divider()
    
    # SECTION 4: PROGRESS BARS BERSAMA
    st.subheader("🎯 4. Progres Kantong Target Bersama (Keluarga)")
    ada_kantong_fam = False
    for kantong, target in DAFTAR_KANTONG.items():
        if target > 0 and MAP_PEMILIK_KANTONG.get(kantong) == "Keluarga (Bersama)":
            ada_kantong_fam = True
            terkumpul = isi_kantong.get(kantong, 0)
            persen = min(float(terkumpul / target), 1.0)
            st.write(f"**{kantong}** (Terkumpul: Rp {terkumpul:,.0f} / Target: Rp {target:,.0f})")
            st.progress(persen)
    if not ada_kantong_fam: st.info("Belum ada target kantong khusus keluarga.")

    st.divider()
    
    # SECTION 5: JURNAL TRANSAKSI UTAMA
    st.subheader("📜 5. Buku Kas Jurnal Transaksi Keluarga (Bisa Edit/Hapus)")
    df_transaksi_diedit = st.data_editor(
        df_transaksi.sort_values(by="Tanggal", ascending=False), 
        num_rows="dynamic", 
        use_container_width=True, 
        key="editor_transaksi_fam",
        column_config={
            "Pengguna": st.column_config.SelectboxColumn(
                "Pengguna",
                options=LIST_USER_LENGKAP,
                required=True
            ),
            "Tipe": st.column_config.SelectboxColumn(
                "Tipe",
                options=["Pemasukan", "Pengeluaran", "Alokasi Masuk", "Pengeluaran (Dari Kantong)"],
                required=True
            )
        }
    )
    
    if st.button("💾 Simpan Perubahan Tabel Transaksi"):
        for idx, row in df_kantong.iterrows():
            nk = row["Nama Kantong"]
            buku_k = df_transaksi_diedit[df_transaksi_diedit["Kategori"] == nk]
            p = buku_k[buku_k["Tipe"] == "Alokasi Masuk"]["Jumlah"].sum()
            m = buku_k[buku_k["Tipe"] == "Pengeluaran (Dari Kantong)"]["Jumlah"].sum()
            df_kantong.loc[idx, "Terkumpul"] = float(p - m)
            
        conn.update(spreadsheet=URL_SHEET, worksheet="Transaksi", data=df_transaksi_diedit)
        conn.update(spreadsheet=URL_SHEET, worksheet="Kantong", data=df_kantong)
        st.success("Database Transaksi & Saldo Kantong Berhasil Diperbarui!")
        st.rerun()

# ==========================================
# HALAMAN 2: MANAGEMENT STRUKTUR (KANTONG & ANGGOTA)
# ==========================================
with tab_pengaturan:
    st.title("⚙️ Pusat Pengaturan Aplikasi Keluarga")
    st.write("Kelola struktur penyimpanan uang dan manifestasi daftar anggota keluarga Anda secara live.")
    
    KOL_KANTONG_MGT, KOL_ANGGOTA_MGT = st.columns(2)
    
    with KOL_KANTONG_MGT:
        st.header("🗂️ 1. Manajemen Struktur Kantong")
        with st.form("form_kantong_fam", clear_on_submit=True):
            nama_baru = st.text_input("Nama Kantong Target Baru:", placeholder="Misal: Tabungan Laptop, Dana Darurat")
            pemilik_baru = st.selectbox("Siapa Pemilik Kantong Ini?", LIST_USER_LENGKAP)
            target_baru = st.number_input("Target Dana (Rp):", min_value=0, step=500000)
            tombol_kantong = st.form_submit_button("Tambah Kantong")
            
        if tombol_kantong and nama_baru != "":
            if not df_kantong.empty and nama_baru in df_kantong["Nama Kantong"].values:
                df_kantong.loc[df_kantong["Nama Kantong"] == nama_baru, "Pemilik"] = pemilik_baru
                df_kantong.loc[df_kantong["Nama Kantong"] == nama_baru, "Target Dana"] = target_baru
            else:
                baris_kantong = pd.DataFrame([[nama_baru, pemilik_baru, target_baru, 0]], columns=["Nama Kantong", "Pemilik", "Target Dana", "Terkumpul"])
                df_kantong = pd.concat([df_kantong, baris_kantong], ignore_index=True)
            
            conn.update(spreadsheet=URL_SHEET, worksheet="Kantong", data=df_kantong)
            st.success(f"Sukses menyimpan Kantong '{nama_baru}'!")
            st.rerun()
            
        st.write("##### Daftar Kantong Aktif (Bisa Edit/Hapus Baris):")
        df_kantong_diedit = st.data_editor(
            df_kantong, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="editor_kantong_fam",
            column_config={
                "Pemilik": st.column_config.SelectboxColumn(
                    "Pemilik",
                    options=LIST_USER_LENGKAP,
                    required=True
                )
            }
        )
        if st.button("💾 Simpan Perubahan Daftar Kantong"):
            conn.update(spreadsheet=URL_SHEET, worksheet="Kantong", data=df_kantong_diedit)
            st.success("Daftar Kantong Berhasil Sinkron!")
            st.rerun()

    with KOL_ANGGOTA_MGT:
        st.header("👥 2. Manajemen Anggota & Password")
        st.write("Tabel ini mengatur nama pengguna sekaligus kunci password masuk halaman web.")
        
        # Tabel anggota sekarang menampilkan kolom Password juga agar bisa dikelola langsung
        df_anggota_diedit = st.data_editor(df_anggota, num_rows="dynamic", use_container_width=True, key="editor_anggota_mgt")
        
        if st.button("💾 Simpan Perubahan Anggota & Password"):
            conn.update(spreadsheet=URL_SHEET, worksheet="Anggota", data=df_anggota_diedit)
            st.success("Daftar Anggota Keluarga & Kredensial Berhasil Diperbarui!")
            st.rerun()