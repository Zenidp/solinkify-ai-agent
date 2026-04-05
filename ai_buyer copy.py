import time
import requests
import json
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solana.transaction import Transaction

# ==========================================
# KONFIGURASI AGEN PEMBELI (KLIEN EKSTERNAL)
# ==========================================
MARKETPLACE_URL = "https://api.solinkify.com" # URL backend Solinkify
TARGET_ITEM_ID = "75810dd6-2340-491a-b968-022ec2c0f30c"
RPC_URL = "https://devnet.helius-rpc.com/?api-key=3933305d-607a-4d03-b59d-1dd12b5383a5"

solana_client = Client(RPC_URL)
ai_wallet = Keypair() # Wallet milik si AI (Pembeli)

def buy_and_consume_data():
    print("🤖 [AI BUYER] Agen diaktifkan. Mencari data target...")
    print(f"🔑 Wallet AI: {ai_wallet.pubkey()}")
    print("⚠️ Isi saldo Devnet ke wallet di atas sekarang! (Jeda 15 detik...)")
    time.sleep(15)

    try:
        # ---------------------------------------------------------
        # FASE 1: AI BERTANYA HARGA BARANG (PING ENDPOINT)
        # ---------------------------------------------------------
        print(f"\n📡 [AI BUYER] Mengakses barang dengan ID: {TARGET_ITEM_ID}...")
        response = requests.get(f"{MARKETPLACE_URL}/api/x402/book/{TARGET_ITEM_ID}")
        
        if response.status_code != 402:
            print("❌ [AI BUYER] Barang tidak ditemukan atau API tidak merespons tagihan (402).")
            return

        payment_details = response.json().get("payment_details")
        print(f"💰 [AI BUYER] Tagihan diterima. Total yang harus dibayar: {payment_details['seller_lamports'] + payment_details['admin_lamports']} Lamports.")

        # ---------------------------------------------------------
        # FASE 2: AI MEMBAYAR BARANG (TRANSAKSI SOLANA)
        # ---------------------------------------------------------
        print("\n⚡ [AI BUYER] Memproses pembayaran via dompet Solana...")
        seller_pubkey = Pubkey.from_string(payment_details["seller_address"])
        admin_pubkey = Pubkey.from_string(payment_details["admin_address"])
        
        recent_blockhash = solana_client.get_latest_blockhash().value.blockhash
        txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=ai_wallet.pubkey())
        
        # Bayar ke Penjual
        txn.add(transfer(TransferParams(
            from_pubkey=ai_wallet.pubkey(), to_pubkey=seller_pubkey, lamports=payment_details["seller_lamports"]
        )))
        
        # Bayar Fee Platform
        if payment_details["admin_lamports"] > 0:
            txn.add(transfer(TransferParams(
                from_pubkey=ai_wallet.pubkey(), to_pubkey=admin_pubkey, lamports=payment_details["admin_lamports"]
            )))

        txn.sign(ai_wallet)
        tx_response = solana_client.send_transaction(txn)
        signature = tx_response.value
        print(f"✅ [AI BUYER] Pembayaran berhasil! Bukti Bayar (Signature): {signature}")
        time.sleep(3) # Tunggu blockchain settle

        # ---------------------------------------------------------
        # FASE 3: AI MENGAMBIL BARANGNYA (DOWNLOAD)
        # ---------------------------------------------------------
        print("\n🔓 [AI BUYER] Menyerahkan bukti bayar untuk mengambil barang...")
        headers = {'x-payment-signature': str(signature)}
        claim_response = requests.get(f"{MARKETPLACE_URL}/api/x402/book/{TARGET_ITEM_ID}", headers=headers, timeout=30)
        
        if claim_response.status_code == 200:
            purchased_data = claim_response.json()
            print("📥 [AI BUYER] Barang (JSON) berhasil diterima penuh!\n")
            
            # ---------------------------------------------------------
            # FASE 4: AI BEBAS MELAKUKAN APAPUN PADA BARANG TERSEBUT
            # ---------------------------------------------------------
            print("================ HASIL BACAAN AI ================")
            # Sebagai contoh: AI hanya mencetak datanya atau menyimpannya
            print(json.dumps(purchased_data, indent=2))
            print("=================================================")
            
            # AI menyimpannya ke memori lokal miliknya sendiri
            with open("my_purchased_data.json", "w") as file:
                json.dump(purchased_data, file, indent=2)
            print("💾 [AI BUYER] Barang telah disimpan ke 'my_purchased_data.json'. Tugas selesai.")

        else:
            print(f"❌ [AI BUYER] Gagal mengambil barang! Server merespons: {claim_response.text}")

    except Exception as e:
        print(f"❌ [AI BUYER] Terjadi kesalahan: {str(e)}")

if __name__ == "__main__":
    buy_and_consume_data()