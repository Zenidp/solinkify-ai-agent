import streamlit as st
import time
import requests
import json
import os
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solders.message import Message
from solders.transaction import Transaction

# 1. SETUP KEAMANAN & KONFIGURASI
load_dotenv()
MARKETPLACE_URL = "https://api.solinkify.com" # URL backend Solinkify
RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")

# 2. SETUP TAMPILAN WEB (UI)
st.set_page_config(page_title="AI Agent Demo", page_icon="🤖", layout="centered")

st.title("🤖 Solinkify: Autonomous AI Buyer")
st.markdown("""
Demo interaktif ini menunjukkan skema *Machine-to-Machine* (M2M). 
Masukkan ID dataset dari Solinkify dan email kamu. Saksikan agen AI mengeksekusi pembayaran on-chain secara otonom serta langusung memproses datanya dan mengirim file aslinya ke email tujuan.
""")

# Input dari pengguna web
target_item_id = st.text_input("Masukkan Book ID (Target Data):", placeholder="Contoh: 75810dd6-2340-...")
target_email = st.text_input("Email Tujuan (Penerima File):", placeholder="email.kamu@gmail.com")

if st.button("🚀 Luncurkan Agen AI"):
    if not target_item_id or not target_email:
        st.error("Mohon masukkan Book ID dan Email Tujuan terlebih dahulu.")
        st.stop()

    # 3. SISTEM LOG TERMINAL VIRTUAL
    log_container = st.empty()
    logs_list = [] 

    def print_log(msg):
        logs_list.append(msg)
        log_container.code("\n".join(logs_list), language="bash")
        time.sleep(0.4) 

    print_log("🤖 [AI BUYER] Agen diaktifkan. Memulai inisialisasi...")

    private_key = os.getenv("AI_PRIVATE_KEY")
    if not private_key:
        print_log("❌ [SYSTEM] Error: AI_PRIVATE_KEY tidak ditemukan di file .env!")
        st.stop()

    try:
        ai_wallet = Keypair.from_base58_string(private_key)
        solana_client = Client(RPC_URL)
        print_log(f"🔑 Terhubung ke Wallet AI: {ai_wallet.pubkey()}")

        # ---------------------------------------------------------
        # FASE 1: CEK HARGA
        # ---------------------------------------------------------
        print_log(f"\n📡 Mengecek paywall untuk barang ID: {target_item_id}...")
        response = requests.get(f"{MARKETPLACE_URL}/api/x402/book/{target_item_id}")
        
        if response.status_code != 402:
            print_log(f"❌ Barang tidak ditemukan atau API tidak merespons (Status: {response.status_code}).")
            st.stop()

        payment_details = response.json().get("payment_details")
        total_lamports = payment_details['seller_lamports'] + payment_details['admin_lamports']
        
        # Konversi Lamports ke SOL
        total_sol = total_lamports / 1_000_000_000 
        print_log(f"💰 Paywall terdeteksi! Total tagihan: {total_sol} SOL.")

        # ---------------------------------------------------------
        # FASE 2: TRANSAKSI OTOMATIS
        # ---------------------------------------------------------
        print_log("\n⚡ Memproses pembayaran on-chain via Solana Devnet...")
        seller_pubkey = Pubkey.from_string(payment_details["seller_address"])
        admin_pubkey = Pubkey.from_string(payment_details["admin_address"])
        
        recent_blockhash = solana_client.get_latest_blockhash().value.blockhash
        
        ixs = [
            transfer(TransferParams(
                from_pubkey=ai_wallet.pubkey(), to_pubkey=seller_pubkey, lamports=payment_details["seller_lamports"]
            ))
        ]
        if payment_details["admin_lamports"] > 0:
            ixs.append(transfer(TransferParams(
                from_pubkey=ai_wallet.pubkey(), to_pubkey=admin_pubkey, lamports=payment_details["admin_lamports"]
            )))

        msg = Message(ixs, ai_wallet.pubkey())
        txn = Transaction([ai_wallet], msg, recent_blockhash)

        tx_response = solana_client.send_transaction(txn)
        signature = tx_response.value
        print_log(f"✅ Transaksi Berhasil! Signature: {signature}")
        
        print_log("⏳ Menunggu konfirmasi dari jaringan blockchain...")
        time.sleep(3) 

        # ---------------------------------------------------------
        # FASE 3: KLAIM DATA & KIRIM EMAIL
        # ---------------------------------------------------------
        print_log("\n🔓 Menyerahkan bukti transaksi untuk mengambil barang...")
        headers = {'x-payment-signature': str(signature)}
        
        # NOTE: Parameter email dimasukkan ke API agar backend Rust mengirim email via Resend
        claim_endpoint = f"{MARKETPLACE_URL}/api/x402/book/{target_item_id}?email={target_email}"
        claim_response = requests.get(claim_endpoint, headers=headers, timeout=30)
        
        if claim_response.status_code == 200:
            claim_data = claim_response.json()
            download_url = claim_data.get("file_url")
            print_log(f"📧 Backend mengkonfirmasi: Email berisi link Cloudflare R2 sedang dikirim ke {target_email}.")
            
            # AI tetap mendownload data ke memori sementaranya untuk dianalisis
            file_response = requests.get(download_url)
            purchased_data = file_response.json()
            print_log("📥 Proses selesai! Data berhasil diakuisisi oleh AI ke dalam memori.")
            
            # ---------------------------------------------------------
            # FASE 4: AI MENAMPILKAN DATA MENTAH (TANPA SAVE LOKAL)
            # ---------------------------------------------------------
            st.success(f"🎉 Tugas Selesai! Berikut adalah data premium mentah yang dibeli oleh AI dan dikirim langsung ke {target_email}.")
            with st.expander("Klik di sini untuk melihat format raw JSON yang di beli lalu dibaca AI"):
                st.json(purchased_data) 

            # ---------------------------------------------------------
            # FASE 5: VISUALISASI DATA (DASHBOARD AI CUACA)
            # ---------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🌤️ Oracle Weather Intelligence Report")
            st.markdown("Berikut adalah hasil dekode data cuaca terdesentralisasi yang dibeli dari jaringan Solana:")
            
            # 1. Header Informasi Provider
            product_name = purchased_data.get("product", "Unknown Oracle")
            provider = purchased_data.get("provider", "Unknown Provider")
            desc = purchased_data.get("description", "")
            
            st.info(f"**{product_name}** by {provider}\n\n_{desc}_")
            
            # 2. Key Metrics (Metadata Jaringan)
            meta = purchased_data.get("meta", {})
            st.markdown("#### 📡 Network Consensus & Reliability")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🌍 Total Lokasi", meta.get("total_feeds", 0))
            col2.metric("⚡ Uptime", meta.get("success_rate", "0%"))
            col3.metric("💻 Active Nodes", meta.get("active_nodes", 0))
            col4.metric("⏱️ Update Rate", f"{meta.get('update_interval_hours', 0)} Jam")
            
            st.markdown("---")
            st.markdown("#### 📍 Live Data Feeds")
            
            feeds = purchased_data.get("sample_feeds", [])
            
            if feeds:
                # Mengelompokkan data berdasarkan lokasi agar rapi
                locations = {}
                for feed in feeds:
                    loc = feed.get("location", "Unknown")
                    if loc not in locations:
                        locations[loc] = []
                    locations[loc].append(feed)
                    
                # Menampilkan kartu (kolom) untuk setiap lokasi
                for loc, data_list in locations.items():
                    with st.container():
                        st.markdown(f"##### 🏙️ {loc}")
                        
                        # Buat kolom dinamis sesuai jumlah parameter di lokasi tersebut
                        cols = st.columns(len(data_list))
                        
                        for i, item in enumerate(data_list):
                            param = item.get("parameter", "")
                            val = item.get("value", 0)
                            unit = item.get("unit", "")
                            raw_val = item.get("value_raw", 0)
                            scale = item.get("scale", 1)
                            
                            # Handle anomali nilai mentah yang belum dibagi scale (contoh: 298 -> 29.8 °C)
                            if val == raw_val and scale > 1:
                                val = val / scale
                                
                            # Mapping Icon sesuai parameter
                            icon = "🌡️" if param == "Temperature" else \
                                   "💧" if param == "Humidity" else \
                                   "💨" if param == "Wind Speed" else \
                                   "☁️" if param == "Cloud Cover" else "📊"
                            
                            with cols[i]:
                                # Menggunakan card styling bawaan st.metric
                                st.metric(label=f"{icon} {param}", value=f"{val} {unit}")
                                
                        timestamp = data_list[0].get('updated_at_iso', '').replace("T", " ").replace("Z", " UTC")
                        st.caption(f"⏱️ _Last updated on-chain: {timestamp}_")
                        st.write("") # Spacer
            else:
                st.info("Tidak ada data feeds cuaca yang ditemukan dalam dataset ini.")
                
            # 3. Status Node Validator (Opsional untuk kesan Web3 yang lebih kuat)
            with st.expander("Lihat Status Konsensus Node Oracle"):
                nodes = purchased_data.get("nodes", [])
                if nodes:
                    node_cols = st.columns(3) # Tampilkan 3 kolom per baris
                    for i, node in enumerate(nodes):
                        with node_cols[i % 3]:
                            status = "🟢 Active" if node.get("active") else "🔴 Offline"
                            st.markdown(f"**{node.get('id')}**")
                            st.caption(status)
                            st.write(f"Total Submits: `{node.get('submits')}`")
                            st.markdown("---")
            
        else:
            print_log(f"❌ Gagal mengambil data. Server merespons: {claim_response.text}")

    except Exception as e:
        print_log(f"❌ Terjadi kesalahan sistem: {str(e)}")