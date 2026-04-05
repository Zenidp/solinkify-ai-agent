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
MARKETPLACE_URL = "http://localhost:8080" # URL Backend Solinkify-mu
RPC_URL = "https://api.devnet.solana.com"

# 2. SETUP TAMPILAN WEB (UI)
st.set_page_config(page_title="AI Agent Demo", page_icon="🤖", layout="centered")

st.title("🤖 Solinkify: Autonomous AI Buyer")
st.markdown("""
Demo interaktif ini menunjukkan skema *Machine-to-Machine* (M2M). 
Masukkan ID dataset dan Email penerima. AI akan membayar secara on-chain, memproses datanya di sini, dan mengirim file aslinya ke emailmu tanpa menyimpannya di folder lokal.
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
        print_log(f"💰 Paywall terdeteksi! Total tagihan: {total_lamports} Lamports.")

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
            st.success(f"🎉 Tugas Selesai! File BUKAN disimpan di folder lokal, melainkan dikirim langsung ke {target_email}.")
            with st.expander("Klik di sini untuk melihat format raw JSON yang dibaca AI"):
                st.json(purchased_data) 

            # ---------------------------------------------------------
            # FASE 5: VISUALISASI DATA (DASHBOARD AI)
            # ---------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🧠 AI Market Intelligence Report (Hasil Analisis)")
            st.markdown("Berikut adalah hasil visualisasi dari data yang baru saja dibeli:")
            
            dataset_name = purchased_data.get("dataset_name", "Unknown Dataset")
            accuracy = purchased_data.get("accuracy_rating", 0)
            
            col1, col2 = st.columns(2)
            col1.metric(label="Sumber Dataset", value=dataset_name)
            col2.metric(label="Tingkat Akurasi AI", value=f"{accuracy * 100}%")
            
            st.markdown("#### 💡 Rekomendasi Aksi Pasar")
            
            tokens_data = purchased_data.get("data", [])
            
            if tokens_data:
                cols = st.columns(len(tokens_data))
                
                for i, item in enumerate(tokens_data):
                    with cols[i]:
                        st.subheader(f"🪙 {item['token']}")
                        
                        sentiment = item["sentiment"].lower()
                        action = item["action"].upper()
                        
                        if sentiment == "bullish":
                            st.success(f"📈 {sentiment.upper()} ➔ **{action}**")
                        elif sentiment == "bearish":
                            st.error(f"📉 {sentiment.upper()} ➔ **{action}**")
                        else:
                            st.warning(f"➖ {sentiment.upper()} ➔ **{action}**")
                        
                        st.write(f"**Target Harga:** ${item['target_price']}")
                        st.write(f"**Keyakinan:** {int(item['confidence'] * 100)}%")
                        st.progress(item['confidence'])
            else:
                st.info("Tidak ada data token yang ditemukan dalam dataset ini.")
            
        else:
            print_log(f"❌ Gagal mengambil data. Server merespons: {claim_response.text}")

    except Exception as e:
        print_log(f"❌ Terjadi kesalahan sistem: {str(e)}")