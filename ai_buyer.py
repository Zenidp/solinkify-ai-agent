import time
import requests
import json
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solders.message import Message
from solders.transaction import Transaction

# ==========================================
# KONFIGURASI AGEN PEMBELI (KLIEN EKSTERNAL)
# ==========================================
MARKETPLACE_URL = "https://api.solinkify.com" # URL backend Solinkify
TARGET_ITEM_ID = "6be78db9-4490-43ec-b35a-fcca0a455dbb"
RPC_URL = "https://devnet.helius-rpc.com/?api-key=3933305d-607a-4d03-b59d-1dd12b5383a5"

# HARDCODE PRIVATE KEY DI SINI (Format Base58, biasanya berawalan angka/huruf acak panjang)
# CONTOH: "5K2... (panjang sekitar 88 karakter)"
AI_PRIVATE_KEY = "5wo15AFGfphtDi9FMJSugog1E7W2CJk8864qLTxxExXw4hwvEhy1aFtPzh9S2JJTJhLtjQRhtwJuSFYND73dhcpt"

solana_client = Client(RPC_URL)

# Memuat dompet AI secara otomatis dari Private Key
ai_wallet = Keypair.from_base58_string(AI_PRIVATE_KEY)

def buy_and_consume_data():
    print("🤖 [AI BUYER] Agen diaktifkan. Beroperasi dalam mode Otonom Penuh.")
    print(f"🔑 Wallet AI: {ai_wallet.pubkey()}")

    try:
        # Cek Saldo Awal (Opsional, hanya untuk memastikan)
        balance = solana_client.get_balance(ai_wallet.pubkey()).value
        print(f"💵 Saldo Saat Ini: {balance / 1_000_000_000} SOL")
        if balance == 0:
            print("❌ [AI BUYER] Saldo dompet AI masih 0 SOL! Isi dulu di Devnet.")
            return

        # ---------------------------------------------------------
        # FASE 1: AI BERTANYA HARGA BARANG (PING ENDPOINT)
        # ---------------------------------------------------------
        print(f"\n📡 [AI BUYER] Mengakses barang dengan ID: {TARGET_ITEM_ID}...")
        response = requests.get(f"{MARKETPLACE_URL}/api/x402/book/{TARGET_ITEM_ID}")
        
        if response.status_code != 402:
            print(f"❌ [AI BUYER] Barang tidak ditemukan atau API tidak merespons tagihan (402). Server bilang: {response.text}")
            return

        payment_details = response.json().get("payment_details")
        print(f"💰 [AI BUYER] Tagihan diterima. Total yang harus dibayar: {payment_details['seller_lamports'] + payment_details['admin_lamports']} Lamports.")

        # ---------------------------------------------------------
        # FASE 2: AI MEMBAYAR BARANG (TRANSAKSI OTOMATIS)
        # ---------------------------------------------------------
        print("\n⚡ [AI BUYER] Memproses pembayaran otomatis via Solana...")
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

        # Transaksi langsung ditandatangani oleh Private Key yang sudah di-load
        tx_response = solana_client.send_transaction(txn)
        signature = tx_response.value
        print(f"✅ [AI BUYER] Pembayaran berhasil! Bukti Bayar (Signature): {signature}")
        time.sleep(3) # Tunggu konfirmasi jaringan

        # ---------------------------------------------------------
        # FASE 3 & 4: AI MENGAMBIL BARANGNYA (DOWNLOAD LEBIH AMAN)
        # ---------------------------------------------------------
        print("\n🔓 [AI BUYER] Menyerahkan bukti bayar untuk mengambil barang...")
        headers = {'x-payment-signature': str(signature)}
        
        # Tambahkan '?email=ai@bot.com' agar backend merespons dengan JSON struktur {file_url: ...}
        claim_endpoint = f"{MARKETPLACE_URL}/api/x402/book/{TARGET_ITEM_ID}?email=ai@bot.com"
        claim_response = requests.get(claim_endpoint, headers=headers, timeout=30)
        
        if claim_response.status_code == 200:
            claim_data = claim_response.json()
            download_url = claim_data.get("file_url")
            print(f"🔗 [AI BUYER] Mendapatkan link rahasia R2...")
            
            # Download file aktual dari link R2 tersebut
            file_response = requests.get(download_url)
            
            try:
                # Coba parse sebagai JSON
                purchased_data = file_response.json()
                print("📥 [AI BUYER] Barang (JSON) berhasil diterima penuh!\n")
                
                print("================ HASIL BACAAN AI ================")
                print(json.dumps(purchased_data, indent=2))
                print("=================================================")
                
                with open("my_purchased_data.json", "w") as file:
                    json.dump(purchased_data, file, indent=2)
                print("💾 [AI BUYER] Barang telah disimpan ke 'my_purchased_data.json'. Tugas selesai.")
                
            except json.JSONDecodeError:
                # Jika yang diunduh BUKAN JSON (Misal XML Error dari Cloudflare R2)
                print("⚠️ [AI BUYER] Peringatan: Data yang diunduh BUKAN format JSON yang valid!")
                print("Sebagian isi data:", file_response.text[:200]) # Print 200 karakter pertama untuk nge-debug
                
                with open("my_purchased_data.raw", "wb") as f:
                    f.write(file_response.content)
                print("💾 [AI BUYER] Disimpan paksa sebagai 'my_purchased_data.raw' untuk kamu cek.")

        else:
            print(f"❌ [AI BUYER] Gagal mengambil barang! Server merespons: {claim_response.text}")

    except Exception as e:
        print(f"❌ [AI BUYER] Terjadi kesalahan: {str(e)}")

if __name__ == "__main__":
    buy_and_consume_data()