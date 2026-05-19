import streamlit as st
import pandas as pd
from google import genai
import json
import datetime
import uuid  # Library bawaan Python untuk membuat ID unik

# ==========================================
# 1. KONFIGURASI AI (GEMINI API)
# ==========================================
# GANTI teks di bawah ini dengan API Key Anda yang valid
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# Inisialisasi Log Makanan Harian di Session State
if 'daily_log' not in st.session_state:
    st.session_state.daily_log = []

# ==========================================
# 2. LOGIKA KALKULATOR KALORI (BMR & TDEE)
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
    if tujuan == "Lose Weight": 
        return tdee - 500
    elif tujuan == "Gain Weight": 
        return tdee + 300
    return tdee

# ==========================================
# 3. FUNGSI ANALISIS MAKANAN OLEH AI 
# ==========================================
def analisa_nutrisi_ai(deskripsi_makanan):
    prompt = f"""
    Anda adalah ahli gizi. Analisis deskripsi makanan berikut: "{deskripsi_makanan}".
    Langkah 1: Perkirakan berat totalnya dalam gram berdasarkan deskripsi porsi.
    Langkah 2: Hitung estimasi kandungan nutrisi berdasarkan perkiraan gram tersebut.
    
    Wajib kembalikan HANYA dalam format JSON persis seperti struktur di bawah ini:
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
        
        if teks_respons.startswith("```json"): 
            teks_respons = teks_respons[7:-3].strip()
        elif teks_respons.startswith("```"): 
            teks_respons = teks_respons[3:-3].strip()
            
        return json.loads(teks_respons)
    except Exception as e:
        st.error(f"Gagal menganalisa. Error: {e}")
        return None

# ==========================================
# 4. PENGATURAN PROFIL & TARGET (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Profil Anda")
jk = st.sidebar.selectbox("Jenis Kelamin", ["Pria", "Wanita"])
usia = st.sidebar.number_input("Usia (Tahun)", min_value=10, max_value=100, value=25)
bb = st.sidebar.number_input("Berat Badan (kg)", min_value=30.0, max_value=200.0, value=65.0)
tb = st.sidebar.number_input("Tinggi Badan (cm)", min_value=100.0, max_value=250.0, value=170.0)

aktivitas = st.sidebar.selectbox("Tingkat Aktivitas", [
    "Sangat Jarang Olahraga", 
    "Jarang (1-3 hari/minggu)", 
    "Cukup (3-5 hari/minggu)", 
    "Aktif (6-7 hari/minggu)", 
    "Sangat Aktif (Fisik berat)"
], index=2) 

# Kalkulasi Dasar
bmr = hitung_bmr(jk, bb, tb, usia)
tdee = hitung_tdee(bmr, aktivitas)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Pengaturan Target")
metode_target = st.sidebar.radio("Pilih Metode:", ["Rekomendasi AI (Otomatis)", "Input Manual (Custom)"])

if metode_target == "Rekomendasi AI (Otomatis)":
    tujuan = st.sidebar.selectbox("Tujuan Anda:", ["Lose Weight", "Maintain", "Gain Weight"])
    target_kalori = hitung_target(tdee, tujuan)
else:
    target_kalori = st.sidebar.number_input("Masukkan Target Kalori Harian (kkal)", min_value=500, max_value=6000, value=int(tdee))

# --- ANALISIS PENURUNAN/KENAIKAN BERAT BADAN ---
st.sidebar.markdown("---")
st.sidebar.subheader("💡 Analisis Target Anda")
st.sidebar.write(f"Kebutuhan kalori harian normal Anda (**TDEE**) adalah **{int(tdee)} kkal**.")

selisih_kalori = target_kalori - tdee
# 1 kg lemak tubuh = ~7700 kkal. 
# Kalori mingguan = selisih harian * 7 hari
estimasi_bb_mingguan = (selisih_kalori * 7) / 7700

if selisih_kalori < -50:
    st.sidebar.info(f"Anda melakukan **defisit {abs(int(selisih_kalori))} kkal/hari**.\n\n📉 Estimasi penurunan berat badan:\n**{abs(estimasi_bb_mingguan):.2f} kg per minggu**.")
elif selisih_kalori > 50:
    st.sidebar.warning(f"Anda melakukan **surplus {abs(int(selisih_kalori))} kkal/hari**.\n\n📈 Estimasi kenaikan berat badan:\n**{abs(estimasi_bb_mingguan):.2f} kg per minggu**.")
else:
    st.sidebar.success(f"Target Anda setara dengan TDEE Anda.\n\n⚖️ Berat badan Anda diperkirakan akan **tetap stabil (Maintain)**.")


# ==========================================
# 5. HEADER & PILIH TANGGAL
# ==========================================
st.title("🥗 AI Calorie Tracker by Nabalilaja")

tanggal_aktif = st.date_input("📅 Pilih Tanggal Log", datetime.date.today())

st.markdown("### ➕ Tambah Log Makanan")
st.caption(f"Menambahkan catatan untuk tanggal: **{tanggal_aktif.strftime('%d %B %Y')}**")

col_input1, col_input2 = st.columns([2, 5])

with col_input1:
    waktu_makan = st.selectbox("Waktu Makan", ["Sarapan", "Makan Siang", "Makan Malam", "Camilan"])
with col_input2:
    input_makanan = st.text_input("Deskripsi Makanan & Porsi", placeholder="Contoh: 1 centong nasi dan 2 telur dadar")

if st.button("✨ Hitung & Catat dengan AI", use_container_width=True):
    if input_makanan:
        with st.spinner('AI sedang menebak porsi dan menganalisa nutrisi...'):
            hasil = analisa_nutrisi_ai(input_makanan)
            
            if hasil:
                entry = {
                    "id": str(uuid.uuid4()), # Membuat ID unik untuk keperluan Hapus data
                    "Tanggal": str(tanggal_aktif), 
                    "Waktu": waktu_makan,
                    "Makanan": input_makanan,
                    "Est. Berat (g)": float(hasil.get("estimasi_gram", 0)),
                    "Kalori": float(hasil.get("kalori", 0)),
                    "Karbo (g)": float(hasil.get("karbohidrat", 0)),
                    "Protein (g)": float(hasil.get("protein", 0)),
                    "Lemak (g)": float(hasil.get("lemak", 0))
                }
                st.session_state.daily_log.append(entry)
                st.success(f"Disimpan! AI memperkirakan porsi tersebut seberat {hasil.get('estimasi_gram')} gram.")
    else:
        st.warning("Silakan masukkan makanan terlebih dahulu.")

st.markdown("---")

# ==========================================
# 6. TAMPILAN DASHBOARD (BERDASARKAN TANGGAL)
# ==========================================
log_hari_ini = [item for item in st.session_state.daily_log if item["Tanggal"] == str(tanggal_aktif)]

st.markdown(f"### 📊 Ringkasan: {tanggal_aktif.strftime('%d %B %Y')}")

total_kalori = sum(item["Kalori"] for item in log_hari_ini)
total_karbo = sum(item["Karbo (g)"] for item in log_hari_ini)
total_protein = sum(item["Protein (g)"] for item in log_hari_ini)
total_lemak = sum(item["Lemak (g)"] for item in log_hari_ini)
sisa_kalori = target_kalori - total_kalori

col_kal1, col_kal2, col_kal3 = st.columns(3)
col_kal1.metric(label="🎯 Target (kkal)", value=int(target_kalori))
col_kal2.metric(label="🍽️ Terkonsumsi (kkal)", value=int(total_kalori))
col_kal3.metric(label="🔥 Sisa Kalori (kkal)", value=int(sisa_kalori), delta=int(sisa_kalori), delta_color="normal")

progress_val = min(max(total_kalori / target_kalori, 0.0), 1.0)
st.progress(progress_val)

mac1, mac2, mac3 = st.columns(3)
mac1.info(f"🍚 **Karbo:** {int(total_karbo)}g")
mac2.success(f"🍗 **Protein:** {int(total_protein)}g")
mac3.warning(f"🥑 **Lemak:** {int(total_lemak)}g")

st.markdown("---")

# ==========================================
# 7. LIST MAKANAN DENGAN FITUR HAPUS
# ==========================================
st.markdown("### 📝 Log Makanan")

if not log_hari_ini:
    st.caption("Belum ada catatan makanan untuk tanggal ini.")
else:
    for waktu in ["Sarapan", "Makan Siang", "Makan Malam", "Camilan"]:
        # Ambil makanan berdasarkan waktu makan di hari ini
        items_waktu = [i for i in log_hari_ini if i["Waktu"] == waktu]
        
        if items_waktu:
            st.markdown(f"**{waktu}**")
            
            # Membuat Header Tabel Kustom agar tombol Hapus sejajar
            h1, h2, h3, h4, h5, h6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
            h1.caption("Makanan")
            h2.caption("Berat (g)")
            h3.caption("Kalori")
            h4.caption("Karbo")
            h5.caption("Protein")
            h6.caption("Aksi")
            
            for item in items_waktu:
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
                c1.write(item["Makanan"])
                c2.write(f"{item['Est. Berat (g)']:.1f}")
                c3.write(f"{item['Kalori']:.1f}")
                c4.write(f"{item['Karbo (g)']:.1f}")
                c5.write(f"{item['Protein (g)']:.1f}")
                
                # Tombol Hapus (Menghapus berdasarkan ID unik)
                if c6.button("❌", key=f"del_{item['id']}", help="Hapus data ini"):
                    st.session_state.daily_log = [log for log in st.session_state.daily_log if log["id"] != item['id']]
                    st.rerun() 
            
            st.write("") # Spacer