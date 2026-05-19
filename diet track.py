import streamlit as st
import pandas as pd
from google import genai
import json
import datetime
import uuid
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import urllib.parse
import requests

# ==========================================
# 1. KONFIGURASI AI (GEMINI) & FIREBASE
# ==========================================
# Konek ke Gemini AI Studio
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# Konek ke Firebase Firestore
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
# 2. KONFIGURASI NATIVE GOOGLE OAUTH
# ==========================================
client_id = st.secrets["GOOGLE_CLIENT_ID"]
client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]

# Menentukan Redirect URI secara dinamis
# Jika sedang dideploy di Streamlit Cloud, Anda bisa menambahkan 'REDIRECT_URI' di Secrets.
# Jika tidak ada, sistem akan otomatis menggunakan localhost agar bisa dicoba di komputer lokal.
if "REDIRECT_URI" in st.secrets:
    redirect_uri = st.secrets["REDIRECT_URI"]
else:
    redirect_uri = "http://localhost:8501"

# Inisialisasi session state untuk menyimpan profil user jika berhasil login
if "user" not in st.session_state:
    st.session_state.user = None

# Alur Kerja 1: Memeriksa apakah Google mengirimkan 'code' di URL setelah user klik login
query_params = st.query_params
if st.session_state.user is None and "code" in query_params:
    auth_code = query_params["code"]
    
    # Tukarkan Authorization Code dengan Access Token dari Google
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    with st.spinner("Sedang memverifikasi akun Google Anda..."):
        try:
            token_res = requests.post(token_url, data=token_data)
            if token_res.status_code == 200:
                tokens = token_res.json()
                access_token = tokens.get("access_token")
                
                # Minta data profil user menggunakan Access Token
                userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                userinfo_res = requests.get(userinfo_url, headers=headers)
                
                if userinfo_res.status_code == 200:
                    # Berhasil Login! Simpan info di Session State
                    st.session_state.user = userinfo_res.json()
                    # Bersihkan kode dari URL agar bersih dan tidak kadaluarsa
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Gagal mengambil informasi profil dari Google.")
            else:
                st.error("Gagal melakukan autentikasi kode dengan Google.")
        except Exception as e:
            st.error(f"Terjadi kesalahan saat autentikasi: {e}")

# Alur Kerja 2: Tampilan jika belum login
if st.session_state.user is None:
    # --- TAMPILAN LANDING PAGE JIKA BELUM LOGIN ---
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>🥗 AI Calorie Tracker</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #4CAF50;'>Pantau Nutrisi Harian Anda dengan Mudah & Cepat</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Membuat tombol url Google Auth secara manual
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": "streamlit_oauth"
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
    
    # Ilustrasi Fitur menggunakan Emoji dan Layout Streamlit
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("<h4 style='text-align: center;'>🧠 Kecerdasan AI</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Cukup ketik porsi makan Anda (misal: '1 piring nasi padang'), AI kami akan langsung menghitung estimasi kalori dan makronutrisinya.</p>", unsafe_allow_html=True)
    with col_feat2:
        st.markdown("<h4 style='text-align: center;'>💾 Simpan Permanen</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Semua data log makanan Anda tersimpan aman dan permanen di Cloud Database Firebase tanpa takut hilang ketika halaman di-refresh.</p>", unsafe_allow_html=True)
    with col_feat3:
        st.markdown("<h4 style='text-align: center;'>🔒 Akun Personal</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Masuk dengan aman menggunakan akun Google pribadi Anda untuk melihat statistik personalisasi kebutuhan kalori harian Anda.</p>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Tombol Login Google dengan style kustom yang elegan di tengah layar
    col_btn_center = st.columns([1, 2, 1])
    with col_btn_center[1]:
        st.markdown(
            f"""
            <a href="{google_auth_url}" target="_self" style="text-decoration: none;">
                <div style="background-color: #4285F4; color: white; text-align: center; padding: 12px 24px; border-radius: 5px; font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.2); cursor: pointer;">
                    🔴 Masuk Menggunakan Akun Google
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
    st.stop() # Hentikan proses eksekusi kode agar halaman utama tidak terlihat sebelum login

# Mengambil data profil dari akun Google yang telah berhasil login
user_email = st.session_state.user.get("email")
user_name = st.session_state.user.get("name")

# ==========================================
# 3. LOGIKA PERHITUNGAN KALORI (BMR & TDEE)
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
    if tujuan == "Lose Weight": return tdee - 500
    elif tujuan == "Gain Weight": return tdee + 300
    return tdee

# ==========================================
# 4. PROSES ANALISIS NUTRISI OLEH AI
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
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        teks_respons = response.text.strip()
        
        # Bersihkan pembungkus markdown JSON dari AI jika ada
        if teks_respons.startswith('```json'): 
            teks_respons = teks_respons[7:-3].strip()
        elif teks_respons.startswith('```'): 
            teks_respons = teks_respons[3:-3].strip()
            
        return json.loads(teks_respons)
    except Exception as e:
        st.error(f"Gagal memproses data makanan dengan AI. Error: {e}")
        return None

# ==========================================
# 5. SIDEBAR UNTUK PROFIL PERSONALISASI & LOGOUT
# ==========================================
st.sidebar.markdown(f"### 👤 Akun Anda")
st.sidebar.write(f"Halo, **{user_name}**!")
st.sidebar.caption(f"Email: {user_email}")

# Tombol Logout yang membersihkan sesi
if st.sidebar.button("🚪 Keluar Akun", use_container_width=True):
    st.session_state.user = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.header("⚙️ Konfigurasi Fisik")
jk = st.sidebar.selectbox("Jenis Kelamin", ["Pria", "Wanita"])
usia = st.sidebar.number_input("Usia (Tahun)", min_value=10, max_value=100, value=25)
bb = st.sidebar.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=65.0)
tb = st.sidebar.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=250.0, value=170.0)

aktivitas = st.sidebar.selectbox("Tingkat Aktivitas", [
    "Sangat Jarang Olahraga", "Jarang (1-3 hari/minggu)", "Cukup (3-5 hari/minggu)", 
    "Aktif (6-7 hari/minggu)", "Sangat Aktif (Fisik berat)"
], index=2) 

bmr = hitung_bmr(jk, bb, tb, usia)
tdee = hitung_tdee(bmr, aktivitas)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Target Kalori")
metode_target = st.sidebar.radio("Metode Target:", ["Rekomendasi AI (Otomatis)", "Input Manual (Kustom)"])

if metode_target == "Rekomendasi AI (Otomatis)":
    tujuan = st.sidebar.selectbox("Tujuan Program Anda:", ["Lose Weight", "Maintain", "Gain Weight"])
    target_kalori = hitung_target(tdee, tujuan)
else:
    target_kalori = st.sidebar.number_input("Target Kalori Kustom (kkal)", min_value=500, value=int(tdee))

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Analisis Kebutuhan")
st.sidebar.write(f"Kebutuhan kalori harian normal (**TDEE**): **{int(tdee)} kkal**.")

selisih_kalori = target_kalori - tdee
estimasi_bb_mingguan = (selisih_kalori * 7) / 7700

if selisih_kalori < -50: 
    st.sidebar.info(f"📉 Estimasi turun berat badan:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
elif selisih_kalori > 50: 
    st.sidebar.warning(f"📈 Estimasi naik berat badan:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
else: 
    st.sidebar.success(f"⚖️ Berat badan stabil.")

# ==========================================
# 6. PENARIKAN DATA SPESIFIK BERDASARKAN USER
# ==========================================
st.title("🥗 AI Calorie Tracker")

tanggal_aktif = st.date_input("📅 Pilih Tanggal Log", datetime.date.today())
tanggal_str = str(tanggal_aktif)

# Menarik data khusus hari ini DAN khusus milik email pengguna yang sedang login
log_hari_ini = []
try:
    docs = db.collection('food_logs')\
             .where('user_email', '==', user_email)\
             .where('Tanggal', '==', tanggal_str)\
             .stream()
    for doc in docs:
        log_hari_ini.append(doc.to_dict())
except Exception as e:
    st.error(f"Gagal mengambil data dari database cloud: {e}")

# ==========================================
# 7. INPUT LOG MAKANAN BARU
# ==========================================
st.markdown("### ➕ Tambah Log Makanan")

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
                    "user_email": user_email, # Melabeli log agar hanya bisa dibaca pemilik akun
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
                st.success("Log makanan berhasil tersimpan!")
                st.rerun() # Refresh instan agar data baru langsung tampil
    else:
        st.warning("Silakan ketik nama makanan terlebih dahulu.")

st.markdown("---")

# ==========================================
# 8. PANEL RINGKASAN DATA NUTRISI
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

# Progress bar pencapaian target kalori
progress_val = min(max(total_kalori / target_kalori, 0.0), 1.0)
st.progress(progress_val)

mac1, mac2, mac3 = st.columns(3)
mac1.info(f"🍚 **Karbohidrat:** {int(total_karbo)}g")
mac2.success(f"🍗 **Protein:** {int(total_protein)}g")
mac3.warning(f"🥑 **Lemak:** {int(total_lemak)}g")

st.markdown("---")

# ==========================================
# 9. DETAIL LOG MAKANAN HARIAN & FITUR HAPUS
# ==========================================
st.markdown("### 📝 Daftar Log Makanan")

if not log_hari_ini:
    st.caption("Belum ada log makanan tercatat untuk hari ini.")
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
                
                # Aksi penghapusan data secara spesifik di Firestore
                if c6.button("❌", key=f"del_{item['id']}", help="Klik untuk menghapus log"):
                    db.collection('food_logs').document(item['id']).delete()
                    st.success("Log dihapus!")
                    st.rerun() 
            st.write("")