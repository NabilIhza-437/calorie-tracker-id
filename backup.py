import streamlit as st
import pandas as pd
from google import genai
import json
import datetime
import uuid
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import hashlib
import os

# ==========================================
# 0. VALIDASI SECRETS (PENCEGAH EROR KEYERROR)
# ==========================================
# Daftar kunci rahasia yang wajib ada di Streamlit Secrets
# Sekarang kita hanya butuh Gemini API Key dan Firebase Database saja! Jauh lebih ringkas!
kunci_wajib = ["GEMINI_API_KEY", "FIREBASE_JSON"]
kunci_hilang = [k for k in kunci_wajib if k not in st.secrets]

if kunci_hilang:
    st.error("⚠️ **Pemberitahuan: Konfigurasi Secrets Belum Lengkap!**")
    st.markdown(
        """
        Aplikasi tidak dapat dijalankan karena beberapa kunci rahasia belum dimasukkan atau format TOML Anda salah pada panel **Secrets Streamlit Cloud**:
        """
    )
    for k in kunci_hilang:
        st.markdown(f"- ❌ Kunci **`{k}`** tidak ditemukan.")
        
    st.markdown("---")
    st.warning("💡 **Cara Memperbaiki:**")
    st.markdown(
        """
        1. Buka dasbor **Streamlit Cloud**, klik tombol titik tiga (**...**) di sebelah aplikasi Anda, lalu pilih **Settings > Secrets**.
        2. Pastikan semua kunci di atas sudah ditulis dengan benar.
        3. Pastikan format penulisannya menggunakan tanda kutip, seperti:
           ```toml
           GEMINI_API_KEY = "kunci_gemini_anda"
           
           FIREBASE_JSON = \"\"\"
           {
             "type": "service_account",
             ...
           }
           \"\"\"
           ```
        4. Jika sudah benar namun tetap error, silakan klik tombol **Reboot App** di menu Streamlit Cloud untuk memulai ulang sistem.
        """
    )
    st.stop()

# ==========================================
# 1. KONFIGURASI AI (GEMINI) & FIREBASE
# ==========================================
# Ambil API KEY Gemini dari Streamlit Secrets
API_KEY = st.secrets["GEMINI_API_KEY"].strip()

# Set kunci API ke Environment Variable sistem agar dibaca otomatis secara aman oleh SDK Google GenAI
os.environ["GEMINI_API_KEY"] = API_KEY

# Hubungkan ke Gemini AI Studio secara aman tanpa argument-mapping bypass
client = genai.Client()

# Hubungkan ke Firebase Firestore
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["FIREBASE_JSON"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Error menghubungkan ke Firebase: {e}. Pastikan konfigurasi FIREBASE_JSON di Secrets sudah benar.")

# Inisialisasi Database Firestore
db = firestore.client()

# ==========================================
# 2. SISTEM KEAMANAN & PASSWORD HASHING
# ==========================================
def enkripsi_password(password):
    """Menyandikan kata sandi menggunakan SHA-256 untuk menjaga keamanan privasi pengguna."""
    return hashlib.sha256(password.encode()).hexdigest()

# Inisialisasi session state untuk melacak akun aktif
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 3. TAMPILAN LANDING PAGE & AUTENTIKASI MANDIRI
# ==========================================
if st.session_state.user is None:
    # --- TAMPILAN JIKA BELUM LOGIN ---
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>🥗 AI Calorie Tracker</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #4CAF50;'>Pantau Nutrisi Harian Anda dengan Mudah & Cepat</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Layout pembagian fitur aplikasi
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("<h4 style='text-align: center;'>🧠 Kecerdasan AI</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Cukup ketik porsi makan Anda (misal: '1 piring nasi padang'), AI kami akan langsung menghitung estimasi kalori dan makronutrisinya.</p>", unsafe_allow_html=True)
    with col_feat2:
        st.markdown("<h4 style='text-align: center;'>💾 Simpan Cloud</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Semua data log makanan Anda tersimpan aman dan permanen di Cloud Database Firebase tanpa takut hilang ketika halaman di-refresh.</p>", unsafe_allow_html=True)
    with col_feat3:
        st.markdown("<h4 style='text-align: center;'>🔒 Akun Mandiri</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Daftar dan masuk menggunakan akun kustom Anda sendiri untuk memisahkan data makanan pribadi secara aman.</p>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Form Autentikasi (Masuk & Daftar)
    col_form_center = st.columns([1, 2, 1])
    with col_form_center[1]:
        tab_login, tab_register = st.tabs(["🔑 Masuk Akun", "📝 Daftar Akun Baru"])
        
        # --- TAB LOGIN ---
        with tab_login:
            st.markdown("<h4 style='text-align: center; margin-bottom: 15px;'>Silakan Masuk</h4>", unsafe_allow_html=True)
            login_email = st.text_input("Alamat Email", key="login_email_input", placeholder="contoh@email.com").strip().lower()
            login_pass = st.text_input("Kata Sandi", key="login_pass_input", type="password", placeholder="Masukkan kata sandi")
            
            if st.button("Masuk Sekarang", use_container_width=True, type="primary"):
                if login_email and login_pass:
                    with st.spinner("Memverifikasi akun Anda..."):
                        try:
                            # Cari user di Firestore berdasarkan email
                            user_doc = db.collection('users').document(login_email).get()
                            if user_doc.exists:
                                user_data = user_doc.to_dict()
                                # Bandingkan hash password
                                if user_data.get("password") == enkripsi_password(login_pass):
                                    st.session_state.user = {
                                        "email": user_data.get("email"),
                                        "name": user_data.get("name")
                                    }
                                    st.success(f"Berhasil masuk! Selamat datang kembali, {user_data.get('name')}.")
                                    st.rerun()
                                else:
                                    st.error("Kata sandi yang Anda masukkan salah!")
                            else:
                                st.error("Akun email tersebut belum terdaftar. Silakan daftar akun baru terlebih dahulu!")
                        except Exception as e:
                            st.error(f"Gagal melakukan proses masuk: {e}")
                else:
                    st.warning("Mohon isi email dan kata sandi Anda!")
                    
        # --- TAB REGISTER (DAFTAR) ---
        with tab_register:
            st.markdown("<h4 style='text-align: center; margin-bottom: 15px;'>Buat Akun Baru</h4>", unsafe_allow_html=True)
            reg_name = st.text_input("Nama Lengkap Anda", placeholder="Contoh: Nabil Ihza").strip()
            reg_email = st.text_input("Alamat Email Baru", placeholder="contoh@email.com").strip().lower()
            reg_pass = st.text_input("Buat Kata Sandi Baru", type="password", placeholder="Minimal 6 karakter")
            
            if st.button("Daftar & Buat Akun", use_container_width=True):
                if reg_name and reg_email and reg_pass:
                    if len(reg_pass) < 6:
                        st.error("Kata sandi minimal harus terdiri dari 6 karakter!")
                    else:
                        with st.spinner("Mendaftarkan akun Anda ke database..."):
                            try:
                                # Periksa apakah email sudah terdaftar
                                user_check = db.collection('users').document(reg_email).get()
                                if user_check.exists:
                                    st.error("Email tersebut sudah terdaftar! Silakan gunakan email lain atau langsung masuk.")
                                else:
                                    # Simpan data user baru dengan password terenkripsi
                                    new_user_data = {
                                        "name": reg_name,
                                        "email": reg_email,
                                        "password": enkripsi_password(reg_pass),
                                        "dibuat_pada": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    db.collection('users').document(reg_email).set(new_user_data)
                                    st.success("Akun berhasil dibuat! Silakan masuk pada tab 'Masuk Akun'.")
                            except Exception as e:
                                st.error(f"Gagal mendaftarkan akun baru: {e}")
                else:
                    st.warning("Mohon lengkapi seluruh formulir pendaftaran!")
        
        st.markdown("<p style='text-align: center; color: gray; margin: 20px 0 10px 0;'>Atau gunakan mode cepat jika ingin mencoba langsung:</p>", unsafe_allow_html=True)
        if st.button("👥 Masuk sebagai Tamu (Mode Cepat)", use_container_width=True):
            st.session_state.user = {
                "email": "tamu@calorietracker.com",
                "name": "Tamu Spesial"
            }
            st.rerun()
            
    st.stop() # Hentikan proses eksekusi kode agar halaman utama tidak terlihat sebelum login

# Mengambil data profil dari sesi yang aktif
user_email = st.session_state.user.get("email")
user_name = st.session_state.user.get("name")

# ==========================================
# 4. LOGIKA PERHITUNGAN KALORI (BMR & TDEE)
# ==========================================
def hitung_bmr(jk, bb, tb, usia):
    if jk == "Pria": 
        return (10 * bb) + (6.25 * tb) - (5 * usia) + 5
    else: 
        return (10 * bb) + (6.25 * tb) - (5 * usia) - 161

def hitung_tdee(bmr, tingkat_aktivitas):
    faktor = {
        "Sangat Jarang Olahraga": 1.2,
        "Jarang (1-3 hari/minggu)": 1.375,
        "Cukup (3-5 hari/minggu)": 1.55,
        "Aktif (6-7 hari/minggu)": 1.725,
        "Sangat Aktif (Fisik berat)": 1.9
    }
    return bmr * faktor[tingkat_aktivitas]

def hitung_target(tdee, tujuan):
    if tujuan == "Menurunkan Berat Badan": return tdee - 500
    elif tujuan == "Menaikkan Berat Badan": return tdee + 300
    return tdee

# ==========================================
# 5. PROSES ANALISIS NUTRISI OLEH AI (DENGAN SISTEM CADANGAN)
# ==========================================
def analisa_nutrisi_ai(deskripsi_makanan):
    prompt = f"""
    Anda adalah seorang ahli gizi profesional. Silakan analisis deskripsi makanan berikut ini: "{deskripsi_makanan}".
    Langkah 1: Tentukan estimasi total berat porsi makanan tersebut dalam gram.
    Langkah 2: Berikan rincian estimasi energi (dalam kalori), karbohidrat, protein, dan lemak dalam gram.
    
    Wajib kembalikan HANYA dalam format data JSON mentah seperti berikut ini tanpa pembungkus lainnya:
    {{
        "estimasi_gram": 0.0,
        "kalori": 0.0,
        "karbohidrat": 0.0,
        "protein": 0.0,
        "lemak": 0.0
    }}
    """
    
    # Mencoba beberapa alternatif model demi menghindari Error NoneType / Pembatasan Akun
    model_alternatif = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    response = None
    eror_terakhir = ""
    
    for nama_model in model_alternatif:
        try:
            res = client.models.generate_content(
                model=nama_model,
                contents=prompt,
            )
            if res and hasattr(res, 'text') and res.text:
                response = res
                break
        except Exception as e:
            eror_terakhir = str(e)
            continue
            
    if response is None:
        st.error(f"Gagal menghubungi kecerdasan AI. Detail kendala: {eror_terakhir if eror_terakhir else 'Respon kosong dari API'}")
        return None
        
    try:
        teks_respons = response.text.strip()
        
        # Bersihkan pembungkus markdown JSON dari AI jika ada
        if teks_respons.startswith('```json'): 
            teks_respons = teks_respons[7:-3].strip()
        elif teks_respons.startswith('```'): 
            teks_respons = teks_respons[3:-3].strip()
            
        return json.loads(teks_respons)
    except Exception as e:
        st.error(f"Gagal memproses data makanan dengan AI. Gagal mengurai JSON: {e}")
        return None

# ==========================================
# 6. MEMUAT KONFIGURASI FISIK DARI DATABASE FIRESTORE
# ==========================================
# Ambil data profil fisik user dari document users jika ada
user_profile = {}
try:
    user_doc = db.collection('users').document(user_email).get()
    if user_doc.exists:
        user_profile = user_doc.to_dict()
except Exception as e:
    st.sidebar.error(f"Gagal mengambil profil fisik dari Cloud: {e}")

# Definisikan daftar opsi statis
daftar_aktivitas = [
    "Sangat Jarang Olahraga", "Jarang (1-3 hari/minggu)", "Cukup (3-5 hari/minggu)", 
    "Aktif (6-7 hari/minggu)", "Sangat Aktif (Fisik berat)"
]
daftar_tujuan = ["Menurunkan Berat Badan", "Menjaga Berat Badan", "Menaikkan Berat Badan"]

# Tentukan nilai default form dari database atau gunakan fallback standar jika kosong
default_jk_idx = 0 if user_profile.get("jenis_kelamin", "Pria") == "Pria" else 1
default_usia = int(user_profile.get("usia", 25))
default_bb = float(user_profile.get("berat_badan", 65.0))
default_tb = float(user_profile.get("tinggi_badan", 170.0))

saved_aktivitas = user_profile.get("aktivitas", "Cukup (3-5 hari/minggu)")
default_akt_idx = daftar_aktivitas.index(saved_aktivitas) if saved_aktivitas in daftar_aktivitas else 2

saved_metode = user_profile.get("metode_target", "Rekomendasi AI (Otomatis)")
default_metode_idx = 0 if saved_metode == "Rekomendasi AI (Otomatis)" else 1

saved_tujuan = user_profile.get("tujuan", "Menjaga Berat Badan")
default_tujuan_idx = daftar_tujuan.index(saved_tujuan) if saved_tujuan in daftar_tujuan else 1

default_custom_target = int(user_profile.get("custom_target_kalori", 2000))

# INISIALISASI VARIABEL TUJUAN SECARA AMAN (Pencegah NameError)
tujuan = saved_tujuan

# ==========================================
# 7. SIDEBAR UNTUK PROFIL PERSONALISASI & KELUAR
# ==========================================
st.sidebar.markdown(f"### 👤 Akun Anda")
st.sidebar.write(f"Selamat datang, **{user_name}**!")
st.sidebar.caption(f"Email: {user_email}")

# Tombol Logout yang membersihkan sesi
if st.sidebar.button("🚪 Keluar Akun", use_container_width=True):
    st.session_state.user = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.header("⚙️ Konfigurasi Fisik")
jk = st.sidebar.selectbox("Jenis Kelamin", ["Pria", "Wanita"], index=default_jk_idx)
usia = st.sidebar.number_input("Umur (Tahun)", min_value=10, max_value=100, value=default_usia)
bb = st.sidebar.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=default_bb)
tb = st.sidebar.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=250.0, value=default_tb)

aktivitas = st.sidebar.selectbox("Tingkat Aktivitas", daftar_aktivitas, index=default_akt_idx) 

bmr = hitung_bmr(jk, bb, tb, usia)
tdee = hitung_tdee(bmr, aktivitas)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Target Kalori")
metode_target = st.sidebar.radio("Metode Target:", ["Rekomendasi AI (Otomatis)", "Input Manual (Kustom)"], index=default_metode_idx)

if metode_target == "Rekomendasi AI (Otomatis)":
    tujuan = st.sidebar.selectbox("Tujuan Program Anda:", daftar_tujuan, index=default_tujuan_idx)
    target_kalori = hitung_target(tdee, tujuan)
else:
    target_kalori = st.sidebar.number_input("Target Kalori Kustom (kkal)", min_value=500, value=default_custom_target)

# Tombol Simpan Konfigurasi Fisik
st.sidebar.markdown("---")
if st.sidebar.button("💾 Simpan Profil Fisik", use_container_width=True, type="primary"):
    try:
        db.collection('users').document(user_email).set({
            "jenis_kelamin": jk,
            "usia": int(usia),
            "berat_badan": float(bb),
            "tinggi_badan": float(tb),
            "aktivitas": aktivitas,
            "metode_target": metode_target,
            "tujuan": tujuan, # Sekarang selalu aman karena sudah memiliki nilai inisialisasi default
            "custom_target_kalori": int(target_kalori) if metode_target != "Rekomendasi AI (Otomatis)" else default_custom_target
        }, merge=True)
        st.sidebar.success("Profil fisik berhasil disimpan permanen!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Gagal menyimpan ke cloud: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Analisis Kebutuhan")
st.sidebar.write(f"Kebutuhan kalori harian normal (**TDEE**): **{int(tdee)} kkal**.")

selisih_kalori = target_kalori - tdee
estimasi_bb_mingguan = (selisih_kalori * 7) / 7700

if selisih_kalori < -50: 
    st.sidebar.info(f"📉 Estimasi penurunan berat:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
elif selisih_kalori > 50: 
    st.sidebar.warning(f"📈 Estimasi kenaikan berat:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
else: 
    st.sidebar.success(f"⚖️ Berat badan stabil.")

# ==========================================
# 8. PENARIKAN DATA SPESIFIK COCOK DENGAN USER
# ==========================================
st.title("🥗 AI Calorie Tracker")

tanggal_aktif = st.date_input("📅 Pilih Tanggal Log", datetime.date.today())
tanggal_str = str(tanggal_aktif)

# Menarik data khusus hari ini dan khusus milik email pengguna yang sedang login
log_hari_ini = []
try:
    docs = db.collection('food_logs')\
             .where('user_email', '==', user_email)\
             .where('Tanggal', '==', tanggal_str)\
             .stream()
    for doc in docs:
        log_hari_ini.append(doc.to_dict())
except Exception as e:
    st.error(f"Gagal menarik data dari database cloud: {e}")

# ==========================================
# 9. INPUT LOG MAKANAN BARU
# ==========================================
st.markdown("### ➕ Tambahkan Log Makanan")

col_input1, col_input2 = st.columns([2, 5])
with col_input1:
    waktu_makan = st.selectbox("Waktu Makan", ["Sarapan", "Makan Siang", "Makan Malam", "Camilan"])
with col_input2:
    input_makanan = st.text_input("Deskripsi Makanan & Porsi", placeholder="Contoh: 1 mangkok bakso campur")

if st.button("✨ Hitung & Catat dengan AI", use_container_width=True):
    if input_makanan:
        with st.spinner('AI sedang menganalisis nutrisi makanan...'):
            hasil = analisa_nutrisi_ai(input_makanan)
            if hasil:
                doc_id = str(uuid.uuid4())
                entry = {
                    "id": doc_id, 
                    "user_email": user_email, # Menjaga data agar hanya bisa dibaca oleh pemilik akun
                    "Tanggal": tanggal_str, 
                    "Waktu": waktu_makan,
                    "Makanan": input_makanan,
                    "Est. Berat (g)": float(hasil.get("estimasi_gram", 0)),
                    "Kalori": float(hasil.get("kalori", 0)),
                    "Karbo (g)": float(hasil.get("karbohidrat", 0)),
                    "Protein (g)": float(hasil.get("protein", 0)),
                    "Lemak (g)": float(hasil.get("lemak", 0))
                }
                # Menyimpan data permanen ke Firestore
                db.collection('food_logs').document(doc_id).set(entry)
                st.success("Log makanan berhasil disimpan!")
                st.rerun() # Refresh agar data langsung muncul
    else:
        st.warning("Silakan ketik nama makanan terlebih dahulu.")

st.markdown("---")

# ==========================================
# 10. PANEL RINGKASAN DATA NUTRISI
# ==========================================
st.markdown(f"### 📊 Ringkasan Nutrisi Hari Ini: {tanggal_aktif.strftime('%d %B %Y')}")

total_kalori = sum(item["Kalori"] for item in log_hari_ini)
total_karbo = sum(item["Karbo (g)"] for item in log_hari_ini)
total_protein = sum(item["Protein (g)"] for item in log_hari_ini)
total_lemak = sum(item["Lemak (g)"] for item in log_hari_ini)
sisa_kalori = target_kalori - total_kalori

col_kal1, col_kal2, col_kal3 = st.columns(3)
col_kal1.metric(label="🎯 Target (kkal)", value=int(target_kalori))
col_kal2.metric(label="🍽️ Terkonsumsi (kkal)", value=int(total_kalori))
col_kal3.metric(label="🔥 Sisa Kuota (kkal)", value=int(sisa_kalori), delta=int(sisa_kalori), delta_color="normal")

# Progress bar target kalori
progress_val = min(max(total_kalori / target_kalori, 0.0), 1.0)
st.progress(progress_val)

mac1, mac2, mac3 = st.columns(3)
mac1.info(f"🍚 **Karbohidrat:** {int(total_karbo)}g")
mac2.success(f"🍗 **Protein:** {int(total_protein)}g")
mac3.warning(f"🥑 **Lemak:** {int(total_lemak)}g")

st.markdown("---")

# ==========================================
# 11. DETAIL LOG MAKANAN HARIAN & FITUR HAPUS
# ==========================================
st.markdown("### 📝 Daftar Log Makanan")

if not log_hari_ini:
    st.caption("Belum ada daftar log makanan tercatat untuk hari ini.")
else:
    for waktu in ["Sarapan", "Makan Siang", "Makan Malam", "Camilan"]:
        items_waktu = [i for i in log_hari_ini if i["Waktu"] == waktu]
        
        if items_waktu:
            st.markdown(f"**{waktu}**")
            h1, h2, h3, h4, h5, h6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
            h1.caption("Nama Makanan"); h2.caption("Berat(g)"); h3.caption("Kalori"); h4.caption("Karbo"); h5.caption("Protein"); h6.caption("Hapus")
            
            for item in items_waktu:
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
                c1.write(item["Makanan"])
                c2.write(f"{item['Est. Berat (g)']:.1f}")
                c3.write(f"{item['Kalori']:.1f}")
                c4.write(f"{item['Karbo (g)']:.1f}")
                c5.write(f"{item['Protein (g)']:.1f}")
                
                # Fitur menghapus data dari Firestore
                if c6.button("❌", key=f"del_{item['id']}", help="Klik untuk menghapus log"):
                    db.collection('food_logs').document(item['id']).delete()
                    st.success("Log berhasil dihapus!")
                    st.rerun() 
            st.write("")