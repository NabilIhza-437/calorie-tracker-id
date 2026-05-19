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
# Nyambungkeun ka Gemini AI Studio
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# Nyambungkeun ka Firebase Firestore
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["FIREBASE_JSON"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Éror nyambungkeun ka Firebase: {e}. Pastikeun konfigurasi FIREBASE_JSON di Secrets parantos leres.")

# Inisialisasi Database Firestore
db = firestore.client()

# ==========================================
# 2. KONFIGURASI NATIVE GOOGLE OAUTH
# ==========================================
client_id = st.secrets["GOOGLE_CLIENT_ID"]
client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]

# Nangtukeun Redirect URI sacara dinamis
if "REDIRECT_URI" in st.secrets:
    redirect_uri = st.secrets["REDIRECT_URI"]
else:
    redirect_uri = "http://localhost:8501"

# Inisialisasi session state kanggo nyimpen profil pangguna upami hasil lebet
if "user" not in st.session_state:
    st.session_state.user = None

# Alur Kerja 1: Mariksa naha Google ngintunkeun 'code' dina URL sabada pangguna klik lebet
query_params = st.query_params
if st.session_state.user is None and "code" in query_params:
    auth_code = query_params["code"]
    
    # Tukeurkeun Authorization Code sareng Access Token ti Google
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    with st.spinner("Nuju mariksa akun Google Anjeun..."):
        try:
            token_res = requests.post(token_url, data=token_data)
            if token_res.status_code == 200:
                tokens = token_res.json()
                access_token = tokens.get("access_token")
                
                # Nyuhunkeun data profil pangguna nganggo Access Token
                userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                userinfo_res = requests.get(userinfo_url, headers=headers)
                
                if userinfo_res.status_code == 200:
                    # Hasil Lebet! Simpen info dina Session State
                    st.session_state.user = userinfo_res.json()
                    # Bersihkeun kode tina URL supados bersih sareng teu kadaluarsa
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Gagal nyandak inpormasi profil ti Google.")
            else:
                st.error("Gagal ngalakukeun autentikasi kode sareng Google.")
        except Exception as e:
            st.error(f"Aya kasalahan nalika autentikasi: {e}")

# Alur Kerja 2: Tampilan upami teu acan lebet
if st.session_state.user is None:
    # --- TAMPILAN LANDING PAGE UPAMI TEU ACAN LEBET ---
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>🥗 Panitén Kalori AI</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #4CAF50;'>Pantau Nutrisi Poéan Anjeun kalayan Gampang & Gancang</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Ngadamel tombol url Google Auth sacara manual
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": "streamlit_oauth"
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
    
    # Ilustrasi Fitur nganggo Emoji sareng Layout Streamlit
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("<h4 style='text-align: center;'>🧠 Kacerdasan AI</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Cukup ketik porsi tuang Anjeun (misal: '1 piring nasi padang'), AI kami bakal langsung ngitung estimasi kalori sareng makronutrisina.</p>", unsafe_allow_html=True)
    with col_feat2:
        st.markdown("<h4 style='text-align: center;'>💾 Simpen Permanén</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Sadayana data log dahareun Anjeun disimpen aman sareng permanén di Cloud Database Firebase tanpa sieun ical nalika halaman di-refresh.</p>", unsafe_allow_html=True)
    with col_feat3:
        st.markdown("<h4 style='text-align: center;'>🔒 Akun Personal</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.9rem; color: gray;'>Lebet kalayan aman ngagunakeun akun Google pribadi Anjeun kanggo ningal statistik personalisasi kabutuhan kalori poéan Anjeun.</p>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Tombol Login Google
    col_btn_center = st.columns([1, 2, 1])
    with col_btn_center[1]:
        st.markdown(
            f"""
            <a href="{google_auth_url}" target="_self" style="text-decoration: none;">
                <div style="background-color: #4285F4; color: white; text-align: center; padding: 12px 24px; border-radius: 5px; font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.2); cursor: pointer;">
                    🔴 Lebet Ngagunakeun Akun Google
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
    st.stop() # Hentikeun proses eksekusi kode supados halaman utama teu katingal sateuacan lebet

# Nyandak data profil ti akun Google anu parantos lebet
user_email = st.session_state.user.get("email")
user_name = st.session_state.user.get("name")

# ==========================================
# 3. LOGIKA NGITUNG KALORI (BMR & TDEE)
# ==========================================
def hitung_bmr(jk, bb, tb, usia):
    if jk == "Pria": 
        return (10 * bb) + (6.25 * tb) - (5 * usia) + 5
    else: 
        return (10 * bb) + (6.25 * tb) - (5 * usia) - 161

def hitung_tdee(bmr, tingkat_aktivitas):
    faktor = {
        "Sangat Jarang Olahraga": 1.2,
        "Jarang (1-3 dinten/minggu)": 1.375,
        "Cekap (3-5 dinten/minggu)": 1.55,
        "Aktif (6-7 dinten/minggu)": 1.725,
        "Aktif pisan (Fisik beurat)": 1.9
    }
    return bmr * faktor[tingkat_aktivitas]

def hitung_target(tdee, tujuan):
    if tujuan == "Ngirangan Beurat Badan": return tdee - 500
    elif tujuan == "Nambihan Beurat Badan": return tdee + 300
    return tdee

# ==========================================
# 4. PROSES ANALISIS NUTRISI KU AI
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
        
        # Bersihkeun pembungkus markdown JSON ti AI upami aya
        if teks_respons.startswith('```json'): 
            teks_respons = teks_respons[7:-3].strip()
        elif teks_respons.startswith('```'): 
            teks_respons = teks_respons[3:-3].strip()
            
        return json.loads(teks_respons)
    except Exception as e:
        st.error(f"Gagal ngolah data dahareun ku AI. Éror: {e}")
        return None

# ==========================================
# 5. SIDEBAR KANGGO PROFIL PERSONALISASI & KELUAR
# ==========================================
st.sidebar.markdown(f"### 👤 Akun Anjeun")
st.sidebar.write(f"Wilujeng sumping, **{user_name}**!")
st.sidebar.caption(f"Email: {user_email}")

# Tombol Logout anu ngabersihkeun sési
if st.sidebar.button("🚪 Kaluar Akun", use_container_width=True):
    st.session_state.user = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.header("⚙️ Konfigurasi Fisik")
jk = st.sidebar.selectbox("Jenis Kelamin", ["Pria", "Wanita"])
usia = st.sidebar.number_input("Umur (Taun)", min_value=10, max_value=100, value=25)
bb = st.sidebar.number_input("Beurat Badan (kg)", min_value=30.0, max_value=200.0, value=65.0)
tb = st.sidebar.number_input("Jangkung Badan (cm)", min_value=100.0, max_value=250.0, value=170.0)

aktivitas = st.sidebar.selectbox("Tingkat Aktivitas", [
    "Sangat Jarang Olahraga", "Jarang (1-3 dinten/minggu)", "Cekap (3-5 dinten/minggu)", 
    "Aktif (6-7 dinten/minggu)", "Aktif pisan (Fisik beurat)"
], index=2) 

bmr = hitung_bmr(jk, bb, tb, usia)
tdee = hitung_tdee(bmr, aktivitas)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Target Kalori")
metode_target = st.sidebar.radio("Metode Target:", ["Rekomendasi AI (Otomatis)", "Input Manual (Kustom)"])

if metode_target == "Rekomendasi AI (Otomatis)":
    tujuan = st.sidebar.selectbox("Tujuan Program Anjeun:", ["Ngirangan Beurat Badan", "Ngajaga Beurat Badan", "Nambihan Beurat Badan"])
    target_kalori = hitung_target(tdee, tujuan)
else:
    target_kalori = st.sidebar.number_input("Target Kalori Kustom (kkal)", min_value=500, value=int(tdee))

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Analisis Kabutuhan")
st.sidebar.write(f"Kabutuhan kalori dinten harian normal (**TDEE**): **{int(tdee)} kkal**.")

selisih_kalori = target_kalori - tdee
estimasi_bb_mingguan = (selisih_kalori * 7) / 7700

if selisih_kalori < -50: 
    st.sidebar.info(f"📉 Estimasi lungsurna beurat:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
elif selisih_kalori > 50: 
    st.sidebar.warning(f"📈 Estimasi naékna beurat:\n**{abs(estimasi_bb_mingguan):.2f} kg / minggu**.")
else: 
    st.sidebar.success(f"⚖️ Beurat badan stabil.")

# ==========================================
# 6. NYANDAK DATA SPESIFIK COCOG SARENG PANGGUNA
# ==========================================
st.title("🥗 Panitén Kalori AI")

tanggal_aktif = st.date_input("📅 Pilih Tanggal Log", datetime.date.today())
tanggal_str = str(tanggal_aktif)

# Nyandak data khusus dinten ieu sareng khusus kagungan email pangguna anu nuju lebet
log_hari_ini = []
try:
    docs = db.collection('food_logs')\
             .where('user_email', '==', user_email)\
             .where('Tanggal', '==', tanggal_str)\
             .stream()
    for doc in docs:
        log_hari_ini.append(doc.to_dict())
except Exception as e:
    st.error(f"Gagal nyandak data tina database cloud: {e}")

# ==========================================
# 7. INPUT LOG DAHAREUN ENGGAL
# ==========================================
st.markdown("### ➕ Tambahkeun Log Dahareun")

col_input1, col_input2 = st.columns([2, 5])
with col_input1:
    waktu_makan = st.selectbox("Waktos Tuang", ["Sasarap", "Dahar Beurang", "Dahar Peuting", "Camilan"])
with col_input2:
    input_makanan = st.text_input("Pedaran Dahareun & Porsi", placeholder="Contoh: 1 mangkok bakso campur")

if st.button("✨ Itung & Catet ku AI", use_container_width=True):
    if input_makanan:
        with st.spinner('AI nuju nganalisis nutrisi dahareun...'):
            hasil = analisa_nutrisi_ai(input_makanan)
            if hasil:
                doc_id = str(uuid.uuid4())
                entry = {
                    "id": doc_id, 
                    "user_email": user_email, # Ngajagi data supados mung tiasa dibaca ku nu gaduh akun
                    "Tanggal": tanggal_str, 
                    "Waktu": waktu_makan,
                    "Makanan": input_makanan,
                    "Est. Berat (g)": float(hasil.get("estimasi_gram", 0)),
                    "Kalori": float(hasil.get("kalori", 0)),
                    "Karbo (g)": float(hasil.get("karbohidrat", 0)),
                    "Protein (g)": float(hasil.get("protein", 0)),
                    "Lemak (g)": float(hasil.get("lemak", 0))
                }
                # Nyimpen data permanen ka Firestore
                db.collection('food_logs').document(doc_id).set(entry)
                st.success("Log dahareun parantos kasimpen!")
                st.rerun() # Refresh supados data langsung katingal
    else:
        st.warning("Mangga ketik nami dahareun sateuacanna.")

st.markdown("---")

# ==========================================
# 8. PANEL RINGKESAN DATA NUTRISI
# ==========================================
st.markdown(f"### 📊 Ringkesan Nutrisi Dinten Ieu: {tanggal_aktif.strftime('%d %B %Y')}")

total_kalori = sum(item["Kalori"] for item in log_hari_ini)
total_karbo = sum(item["Karbo (g)"] for item in log_hari_ini)
total_protein = sum(item["Protein (g)"] for item in log_hari_ini)
total_lemak = sum(item["Lemak (g)"] for item in log_hari_ini)
sisa_kalori = target_kalori - total_kalori

col_kal1, col_kal2, col_kal3 = st.columns(3)
col_kal1.metric(label="🎯 Target (kkal)", value=int(target_kalori))
col_kal2.metric(label="🍽️ Parantos Dituang (kkal)", value=int(total_kalori))
col_kal3.metric(label="🔥 Sésa Kuota (kkal)", value=int(sisa_kalori), delta=int(sisa_kalori), delta_color="normal")

# Progress bar target kalori
progress_val = min(max(total_kalori / target_kalori, 0.0), 1.0)
st.progress(progress_val)

mac1, mac2, mac3 = st.columns(3)
mac1.info(f"🍚 **Karbohidrat:** {int(total_karbo)}g")
mac2.success(f"🍗 **Protein:** {int(total_protein)}g")
mac3.warning(f"🥑 **Lemak:** {int(total_lemak)}g")

st.markdown("---")

# ==========================================
# 9. DETAIL LOG DAHAREUN DINTENAN & FITUR HAPUS
# ==========================================
st.markdown("### 📝 Daptar Log Dahareun")

if not log_hari_ini:
    st.caption("Teu acan aya daptar log dahareun dinten ieu.")
else:
    for waktu in ["Sasarap", "Dahar Beurang", "Dahar Peuting", "Camilan"]:
        items_waktu = [i for i in log_hari_ini if i["Waktu"] == waktu]
        
        if items_waktu:
            st.markdown(f"**{waktu}**")
            h1, h2, h3, h4, h5, h6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
            h1.caption("Nami Dahareun"); h2.caption("Beurat(g)"); h3.caption("Kalori"); h4.caption("Karbo"); h5.caption("Protein"); h6.caption("Hapus")
            
            for item in items_waktu:
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
                c1.write(item["Makanan"])
                c2.write(f"{item['Est. Berat (g)']:.1f}")
                c3.write(f"{item['Kalori']:.1f}")
                c4.write(f"{item['Karbo (g)']:.1f}")
                c5.write(f"{item['Protein (g)']:.1f}")
                
                # Fitur mupus data tina Firestore
                if c6.button("❌", key=f"del_{item['id']}", help="Klik kanggo mupus log"):
                    db.collection('food_logs').document(item['id']).delete()
                    st.success("Log parantos dihapus!")
                    st.rerun() 
            st.write("")