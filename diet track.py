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
# 0. GLOBAL PRESTIGE STYLING (THEME INJECTION)
# ==========================================
st.set_page_config(page_title="KaloriAI — Smart Calorie Tracker", page_icon="🥗", layout="wide")

# Injeksi CSS Kustom untuk Merombak Total UI Sesuai kalori_main.html
# dan menipiskan padding/margin yang berlebihan
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    
    /* Perubahan Latar Belakang Global */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0D0F14 !important;
        color: #F1F5F9 !important;
        font-family: 'Sora', sans-serif !important;
    }
    
    /* Penyesuaian Ruang Kosong (Blank Space) Global */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    h1, h2, h3 {
        margin-bottom: 0.5rem !important;
        margin-top: 0.5rem !important;
    }

    hr {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161921 !important;
        border-right: 1px solid #2D3748 !important;
    }
    
    /* Desain Elemen Input & Tombol */
    div[data-baseweb="input"], div[data-baseweb="select"], .stNumberInput input {
        background-color: #1E2330 !important;
        border: 1px solid #2D3748 !important;
        color: #F1F5F9 !important;
        border-radius: 8px !important;
    }
    
    .stButton button {
        background: linear-gradient(135deg, #4ADE80 0%, #22D3EE 100%) !important;
        color: #0D0F14 !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(74, 222, 128, 0.3) !important;
    }
    
    /* Desain Tab Kustom */
    div[data-testid="stTabs"] button {
        color: #64748B !important;
        font-weight: 500 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #4ADE80 !important;
        border-bottom-color: #4ADE80 !important;
    }
    
    /* Custom Card Containers */
    .cyber-card {
        background-color: #161921;
        border: 1px solid #2D3748;
        border-radius: 12px;
        padding: 15px; /* Disesuaikan agar lebih tipis */
        margin-bottom: 15px; /* Disesuaikan agar lebih tipis */
    }
    
    .metric-number {
        font-family: 'Space Mono', monospace;
        font-size: 1.8rem; /* Sedikit dikecilkan agar proporsional */
        font-weight: 700;
        margin-top: 5px;
    }
    
    /* Tweak for warning box */
    div[data-testid="stAlert"] {
        padding: 10px 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. KONFIGURASI SECRETS & BACKEND VALIDATION
# ==========================================
kunci_wajib = ["GEMINI_API_KEY", "FIREBASE_JSON"]
kunci_hilang = [k for k in kunci_wajib if k not in st.secrets]

if kunci_hilang:
    st.error("⚠️ **Pemberitahuan: Konfigurasi Secrets Belum Lengkap!**")
    st.stop()

# Set kunci API ke Environment Variable sistem secara aman
API_KEY = st.secrets["GEMINI_API_KEY"].strip()
os.environ["GEMINI_API_KEY"] = API_KEY
client = genai.Client()

# Hubungkan ke Firebase Firestore
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["FIREBASE_JSON"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Error Firebase: {e}")

db = firestore.client()

# Hashing Kata Sandi
def enkripsi_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# 2. HALAMAN LOGIN & DAFTAR (CYBERPUNK THEME)
# ==========================================
if st.session_state.user is None:
    # Menghapus <br> yang berlebihan
    st.markdown("<h1 style='text-align: center; font-size: 3rem; font-weight:700; background: linear-gradient(to right, #4ADE80, #22D3EE); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🥗 KaloriAI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B; font-size: 1rem;'>Smart Calorie Tracker — Generasi Terbaru Pengawal Nutrisi Anda</p>", unsafe_allow_html=True)
    
    col_form_center = st.columns([1, 1.8, 1])
    with col_form_center[1]:
        st.markdown("<div class='cyber-card'>", unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["🔑 Masuk Sistem", "📝 Registrasi Akun"])
        
        with tab_login:
            login_email = st.text_input("Alamat Email", key="login_email_input", placeholder="nama@email.com").strip().lower()
            login_pass = st.text_input("Kata Sandi", key="login_pass_input", type="password", placeholder="••••••••")
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Akses Dashboard", use_container_width=True, type="primary"):
                if login_email and login_pass:
                    try:
                        user_doc = db.collection('users').document(login_email).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            if user_data.get("password") == enkripsi_password(login_pass):
                                st.session_state.user = {
                                    "email": user_data.get("email"),
                                    "name": user_data.get("name")
                                }
                                st.success("Autentikasi berhasil!")
                                st.rerun()
                            else:
                                st.error("Kata sandi salah!")
                        else:
                            st.error("Email belum terdaftar.")
                    except Exception as e:
                        st.error(f"Gagal masuk: {e}")
                else:
                    st.warning("Formulir wajib diisi!")
                    
        with tab_register:
            reg_name = st.text_input("Nama Lengkap", placeholder="Nabil Ihza").strip()
            reg_email = st.text_input("Email Baru", placeholder="nama@email.com").strip().lower()
            reg_pass = st.text_input("Buat Kata Sandi", type="password", placeholder="Minimal 6 karakter")
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Buat Akun Baru", use_container_width=True):
                if reg_name and reg_email and reg_pass:
                    if len(reg_pass) < 6:
                        st.error("Kata sandi terlalu pendek!")
                    else:
                        try:
                            user_check = db.collection('users').document(reg_email).get()
                            if user_check.exists:
                                st.error("Email sudah digunakan!")
                            else:
                                new_user_data = {
                                    "name": reg_name,
                                    "email": reg_email,
                                    "password": enkripsi_password(reg_pass),
                                    "dibuat_pada": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                db.collection('users').document(reg_email).set(new_user_data)
                                st.success("Registrasi sukses! Silakan beralih ke tab Masuk.")
                        except Exception as e:
                            st.error(f"Gagal registrasi: {e}")
                else:
                    st.warning("Lengkapi data Anda!")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Mengambil data sesi yang aktif
user_email = st.session_state.user.get("email")
user_name = st.session_state.user.get("name")

# ==========================================
# 3. KEBUTUHAN KALORI & LOAD PROFILE (FIRESTORE)
# ==========================================
user_profile = {}
try:
    user_doc = db.collection('users').document(user_email).get()
    if user_doc.exists:
        user_profile = user_doc.to_dict()
except Exception as e:
    st.error(f"Gagal memuat profil: {e}")

def hitung_bmr(jk, bb, tb, usia):
    if jk == "Pria": return (10 * bb) + (6.25 * tb) - (5 * usia) + 5
    return (10 * bb) + (6.25 * tb) - (5 * usia) - 161

def hitung_tdee(bmr, tingkat_aktivitas):
    faktor = {
        "Sangat Jarang Olahraga": 1.2,
        "Jarang (1-3 hari/minggu)": 1.375,
        "Cukup (3-5 hari/minggu)": 1.55,
        "Aktif (6-7 hari/minggu)": 1.725,
        "Sangat Aktif (Fisik berat)": 1.9
    }
    return bmr * faktor.get(tingkat_aktivitas, 1.55)

def hitung_target(tdee, tujuan):
    if tujuan == "Menurunkan Berat Badan": return tdee - 500
    elif tujuan == "Menaikkan Berat Badan": return tdee + 300
    return tdee

daftar_aktivitas = ["Sangat Jarang Olahraga", "Jarang (1-3 hari/minggu)", "Cukup (3-5 hari/minggu)", "Aktif (6-7 hari/minggu)", "Sangat Aktif (Fisik berat)"]
daftar_tujuan = ["Menurunkan Berat Badan", "Menjaga Berat Badan", "Menaikkan Berat Badan"]

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

# ==========================================
# 4. SIDEBAR SETTINGS & PROFILE CONFIG
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color:#4ADE80; font-weight:700;'>⚙️ Konfigurasi</h2>", unsafe_allow_html=True)
    st.markdown("---")
    jk = st.selectbox("Jenis Kelamin", ["Pria", "Wanita"], index=default_jk_idx)
    usia = st.number_input("Umur (Tahun)", min_value=10, max_value=100, value=default_usia)
    bb = st.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=default_bb)
    tb = st.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=250.0, value=default_tb)
    aktivitas = st.selectbox("Tingkat Aktivitas", daftar_aktivitas, index=default_akt_idx)
    
    bmr = hitung_bmr(jk, bb, tb, usia)
    tdee = hitung_tdee(bmr, aktivitas)
    
    st.markdown("---")
    metode_target = st.radio("Metode Kebutuhan Target:", ["Rekomendasi AI (Otomatis)", "Input Manual (Kustom)"], index=default_metode_idx)
    
    if metode_target == "Rekomendasi AI (Otomatis)":
        tujuan_program = st.selectbox("Tujuan Program:", daftar_tujuan, index=default_tujuan_idx)
        target_kalori = hitung_target(tdee, tujuan_program)
    else:
        target_kalori = st.number_input("Batas Kalori Kustom (kkal)", min_value=500, value=default_custom_target)
        tujuan_program = saved_tujuan
        
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("💾 Simpan Profil Fisik", use_container_width=True, type="primary"):
        try:
            db.collection('users').document(user_email).set({
                "jenis_kelamin": jk,
                "usia": int(usia),
                "berat_badan": float(bb),
                "tinggi_badan": float(tb),
                "aktivitas": aktivitas,
                "metode_target": metode_target,
                "tujuan": tujuan_program,
                "custom_target_kalori": int(target_kalori)
            }, merge=True)
            st.success("Profil tersimpan permanen!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menyimpan: {e}")
            
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Keluar Akun", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# ==========================================
# 5. HEADER UTAMA (MODERN PREMIUM HEADER PILL)
# ==========================================
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; background-color: #161921; padding: 12px 20px; border-radius: 12px; border: 1px solid #2D3748; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 24px;">🥗</span>
        <div>
            <div style="font-weight: 700; font-size: 18px; color: #4ADE80; letter-spacing: 0.5px; line-height: 1.2;">KaloriAI</div>
            <div style="font-size: 11px; color: #64748B;">Smart Calorie Tracker</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 15px;">
        <div style="display: flex; align-items: center; gap: 8px; background: #1E2330; padding: 5px 12px; border-radius: 20px; border: 1px solid #2D3748;">
            <div style="background: #4ADE80; color: #0D0F14; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px;">{user_name[0].upper() if user_name else 'U'}</div>
            <span style="font-size: 13px; font-weight: 500; color: #F1F5F9;">{user_name}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. PENARIKAN DATA LOG MAKANAN HARIAN
# ==========================================
tanggal_aktif = st.date_input("📅 Pilih Tanggal Analisis", datetime.date.today())
tanggal_str = str(tanggal_aktif)

log_hari_ini = []
try:
    docs = db.collection('food_logs').where('user_email', '==', user_email).where('Tanggal', '==', tanggal_str).stream()
    for doc in docs:
        log_hari_ini.append(doc.to_dict())
except Exception as e:
    st.error(f"Gagal menarik log database: {e}")

total_kalori = sum(item["Kalori"] for item in log_hari_ini)
total_karbo = sum(item["Karbo (g)"] for item in log_hari_ini)
total_protein = sum(item["Protein (g)"] for item in log_hari_ini)
total_lemak = sum(item["Lemak (g)"] for item in log_hari_ini)
sisa_kalori = target_kalori - total_kalori

# Perhitungan Estimasi Proyeksi Berat Badan Per Minggu
selisih_kalori = target_kalori - tdee
estimasi_bb_mingguan = (selisih_kalori * 7) / 7700

# ==========================================
# 7. DASHBOARD SUMMARY CARDS (CYBER THEME METRICS)
# ==========================================
st.markdown("<h3 style='font-size:1.2rem; font-weight:600; color:#F1F5F9; margin-bottom:10px;'>📊 Ringkasan Nutrisi</h3>", unsafe_allow_html=True)

m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.markdown(f"""
    <div class='cyber-card' style='border-left: 4px solid #22D3EE;'>
        <div style='color: #64748B; font-size: 0.8rem; font-weight: 500;'>TARGET KEBUTUHAN</div>
        <div class='metric-number' style='color: #22D3EE;'>{int(target_kalori)} <span style='font-size:0.9rem; color:#64748B;'>kkal</span></div>
    </div>
    """, unsafe_allow_html=True)
with m_col2:
    st.markdown(f"""
    <div class='cyber-card' style='border-left: 4px solid #4ADE80;'>
        <div style='color: #64748B; font-size: 0.8rem; font-weight: 500;'>TOTAL TERKONSUMSI</div>
        <div class='metric-number' style='color: #4ADE80;'>{int(total_kalori)} <span style='font-size:0.9rem; color:#64748B;'>kkal</span></div>
    </div>
    """, unsafe_allow_html=True)
with m_col3:
    warna_sisa = "#4ADE80" if sisa_kalori >= 0 else "#F87171"
    st.markdown(f"""
    <div class='cyber-card' style='border-left: 4px solid {warna_sisa};'>
        <div style='color: #64748B; font-size: 0.8rem; font-weight: 500;'>SISA KUOTA KALORI</div>
        <div class='metric-number' style='color: {warna_sisa};'>{int(sisa_kalori)} <span style='font-size:0.9rem; color:#64748B;'>kkal</span></div>
    </div>
    """, unsafe_allow_html=True)

# Custom Progress Bar Neon
progress_percent = min(max(total_kalori / target_kalori, 0.0), 1.0) * 100
warna_bar = "#4ADE80" if total_kalori <= target_kalori else "#F87171"
st.markdown(f"""
<div style="width: 100%; background-color: #1E2330; border-radius: 20px; height: 8px; margin-bottom: 15px; border: 1px solid #2D3748; overflow: hidden;">
    <div style="width: {progress_percent}%; background: {warna_bar}; height: 100%; border-radius: 20px; transition: width 0.5s ease-in-out;"></div>
</div>
""", unsafe_allow_html=True)

# WARNING: Pesan Motivasi Jika Melebihi Batas Kalori
if sisa_kalori < 0:
    st.markdown(f"""
    <div style='background-color: rgba(248, 113, 113, 0.1); border: 1px solid #F87171; border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; display: flex; align-items: flex-start; gap: 12px;'>
        <div style='font-size: 1.5rem; line-height: 1;'>⚠️</div>
        <div>
            <div style='color: #F87171; font-weight: 600; font-size: 0.95rem; margin-bottom: 4px;'>Ups, Kalori Harian Telah Terlampaui!</div>
            <div style='color: #E2E8F0; font-size: 0.85rem; line-height: 1.4;'>
                Kamu sudah melewati batas target sebesar <b>{abs(int(sisa_kalori))} kkal</b> hari ini. 
                Jangan menyerah! 💪 Besok adalah hari baru untuk memulai kembali dengan pilihan makanan yang lebih sehat. Ingat, perjalanan menuju tubuh ideal adalah marathon, bukan lari sprint!
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Row Makronutrisi & Estimasi Mingguan
mac1, mac2, mac3, mac4 = st.columns(4)
with mac1:
    st.markdown(f"<div class='cyber-card' style='padding: 12px; text-align: center;'><span style='color:#64748B; font-size:0.75rem;'>🍚 KARBOHIDRAT</span><br><b style='color:#F1F5F9; font-size:1.1rem; font-family:Space Mono;'>{int(total_karbo)}g</b></div>", unsafe_allow_html=True)
with mac2:
    st.markdown(f"<div class='cyber-card' style='padding: 12px; text-align: center;'><span style='color:#64748B; font-size:0.75rem;'>🍗 PROTEIN</span><br><b style='color:#4ADE80; font-size:1.1rem; font-family:Space Mono;'>{int(total_protein)}g</b></div>", unsafe_allow_html=True)
with mac3:
    st.markdown(f"<div class='cyber-card' style='padding: 12px; text-align: center;'><span style='color:#64748B; font-size:0.75rem;'>🥑 LEMAK</span><br><b style='color:#F59E0B; font-size:1.1rem; font-family:Space Mono;'>{int(total_lemak)}g</b></div>", unsafe_allow_html=True)
with mac4:
    if estimasi_bb_mingguan < -0.01:
        status_bb = f"<span style='color:#4ADE80; font-weight:700;'>📉 Turun {abs(estimasi_bb_mingguan):.2f} kg</span>"
    elif estimasi_bb_mingguan > 0.01:
        status_bb = f"<span style='color:#F87171; font-weight:700;'>📈 Naik {abs(estimasi_bb_mingguan):.2f} kg</span>"
    else:
        status_bb = "<span style='color:#22D3EE; font-weight:700;'>⚖️ Stabil</span>"
    st.markdown(f"<div class='cyber-card' style='padding: 12px; text-align: center;'><span style='color:#64748B; font-size:0.75rem;'>🔮 PROYEKSI MINGGUAN</span><br><b style='font-size:0.9rem;'>{status_bb}</b></div>", unsafe_allow_html=True)

# ==========================================
# 8. AGEN AI CORE ENGINE LOGIC
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
    model_alternatif = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    response = None
    eror_terakhir = ""
    for nama_model in model_alternatif:
        try:
            res = client.models.generate_content(model=nama_model, contents=prompt)
            if res and hasattr(res, 'text') and res.text:
                response = res
                break
        except Exception as e:
            eror_terakhir = str(e)
            continue
            
    if response is None:
        st.error(f"Gagal menghubungi Agen AI: {eror_terakhir}")
        return None
        
    try:
        teks_respons = response.text.strip()
        if teks_respons.startswith('```json'): 
            teks_respons = teks_respons[7:-3].strip()
        elif teks_respons.startswith('```'): 
            teks_respons = teks_respons[3:-3].strip()
            
        return json.loads(teks_respons)
    except Exception as e:
        return None

# ==========================================
# 9. INTEGRASI INPUT MAKANAN BARU & CATATAN AI
# ==========================================
st.markdown("---")
st.markdown("<h3 style='font-size:1.2rem; font-weight:600; color:#F1F5F9; margin-bottom:10px;'>➕ Log Asupan Baru</h3>", unsafe_allow_html=True)

st.markdown("<div class='cyber-card'>", unsafe_allow_html=True)
col_in1, col_in2 = st.columns([1.5, 4])
with col_in1:
    waktu_makan = st.selectbox("Waktu Asupan", ["Sarapan", "Makan Siang", "Makan Malam", "Camilan"])
with col_in2:
    input_makanan = st.text_input("Makanan & Porsi", placeholder="Misal: 1 piring nasi goreng dengan telur mata sapi")

if st.button("⚡ Hitung & Simpan via KaloriAI Engine", use_container_width=True):
    if input_makanan:
        with st.spinner('Menghitung kandungan gizi via Agen AI...'):
            hasil = analisa_nutrisi_ai(input_makanan)
            if hasil:
                doc_id = str(uuid.uuid4())
                entry = {
                    "id": doc_id,
                    "user_email": user_email,
                    "Tanggal": tanggal_str,
                    "Waktu": waktu_makan,
                    "Makanan": input_makanan,
                    "Est. Berat (g)": float(hasil.get("estimasi_gram", 0)),
                    "Kalori": float(hasil.get("kalori", 0)),
                    "Karbo (g)": float(hasil.get("karbohidrat", 0)),
                    "Protein (g)": float(hasil.get("protein", 0)),
                    "Lemak (g)": float(hasil.get("lemak", 0))
                }
                db.collection('food_logs').document(doc_id).set(entry)
                st.success("Nutrisi berhasil dicatat!")
                st.rerun()
    else:
        st.warning("Isi deskripsi makanan terlebih dahulu!")
st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 10. DAFTAR LOG MAKANAN HARIAN & FITUR HAPUS
# ==========================================
st.markdown("---")
st.markdown("<h3 style='font-size:1.2rem; font-weight:600; color:#F1F5F9; margin-bottom:10px;'>📝 Daftar Menu Hari Ini</h3>", unsafe_allow_html=True)

if not log_hari_ini:
    st.caption("Belum ada asupan makanan yang tercatat pada tanggal ini.")
else:
    for waktu in ["Sarapan Pagi", "Makan Siang", "Makan Malam", "Camilan"]:
        items_waktu = [i for i in log_hari_ini if i["Waktu"] == waktu]
        if items_waktu:
            st.markdown(f"<div style='color:#22D3EE; font-weight:600; margin-top:5px; margin-bottom:5px; font-size: 0.9rem;'>⏱️ {waktu}</div>", unsafe_allow_html=True)
            for item in items_waktu:
                st.markdown(f"<div class='cyber-card' style='padding: 10px 15px; margin-bottom: 8px;'>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5, c6 = st.columns([4, 1.2, 1.2, 1.2, 1.2, 0.6])
                c1.markdown(f"<span style='font-size:0.9rem; font-weight:500;'>{item['Makanan']}</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:#64748B; font-size:0.75rem;'>Berat:</span> <br><b style='font-family:Space Mono; font-size:0.9rem;'>{item['Est. Berat (g)']:.0f}g</b>", unsafe_allow_html=True)
                c3.markdown(f"<span style='color:#22D3EE; font-size:0.75rem;'>Kalori:</span> <br><b style='font-family:Space Mono; color:#22D3EE; font-size:0.9rem;'>{item['Kalori']:.0f}k</b>", unsafe_allow_html=True)
                c4.markdown(f"<span style='color:#64748B; font-size:0.75rem;'>K:</span> <br><b style='font-family:Space Mono; font-size:0.9rem;'>{item['Karbo (g)']:.0f}g</b>", unsafe_allow_html=True)
                c5.markdown(f"<span style='color:#4ADE80; font-size:0.75rem;'>P:</span> <br><b style='font-family:Space Mono; color:#4ADE80; font-size:0.9rem;'>{item['Protein (g)']:.0f}g</b>", unsafe_allow_html=True)
                
                with c6:
                    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                    if st.button("❌", key=f"del_{item['id']}", help="Hapus log makanan ini"):
                        try:
                            db.collection('food_logs').document(item['id']).delete()
                            st.success("Log dihapus!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus: {e}")
                st.markdown("</div>", unsafe_allow_html=True)