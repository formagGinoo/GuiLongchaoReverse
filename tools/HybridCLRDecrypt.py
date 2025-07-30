import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# === PARAMETERS ===
key_bytes = b"read README.md and find it"[:16]  # your key
iv = bytes([
    0x12, 0x34, 0x56, 0x78, 0x90, 0xAB, 0xCD, 0xEF,
    0x12, 0x34, 0x56, 0x78, 0x90, 0xAB, 0xCD, 0xEF
])

input_folder = ""  # folder containing encrypted .dll files
output_folder = "/DecryptedHybridCLR"  # output folder

os.makedirs(output_folder, exist_ok=True)

def aes_decrypt(ciphertext_bytes: bytes) -> bytes:
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext_bytes)
    return unpad(decrypted, AES.block_size)

def decrypt_all_dll_files():
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".dll"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            with open(input_path, "rb") as f:
                ciphertext = f.read()

            try:
                decrypted = aes_decrypt(ciphertext)
                with open(output_path, "wb") as out:
                    out.write(decrypted)
                print(f"Decrypted {filename} -> {output_path}")
            except Exception as e:
                print(f"Failed to decrypt {filename}: {e}")

if __name__ == "__main__":
    decrypt_all_dll_files()
