
# xtea.py — Multi-block XTEA cipher with padding
DELTA = 0x9E3779B9
NUM_ROUNDS = 32

def encrypt_block(v, k):
    v0, v1 = v
    sum = 0
    for _ in range(NUM_ROUNDS):
        v0 = (v0 + (((v1 << 4 ^ v1 >> 5) + v1) ^ (sum + k[sum & 3]))) & 0xFFFFFFFF
        sum = (sum + DELTA) & 0xFFFFFFFF
        v1 = (v1 + (((v0 << 4 ^ v0 >> 5) + v0) ^ (sum + k[(sum >> 11) & 3]))) & 0xFFFFFFFF
    return v0, v1

def decrypt_block(v, k):
    v0, v1 = v
    sum = (DELTA * NUM_ROUNDS) & 0xFFFFFFFF
    for _ in range(NUM_ROUNDS):
        v1 = (v1 - (((v0 << 4 ^ v0 >> 5) + v0) ^ (sum + k[(sum >> 11) & 3]))) & 0xFFFFFFFF
        sum = (sum - DELTA) & 0xFFFFFFFF
        v0 = (v0 - (((v1 << 4 ^ v1 >> 5) + v1) ^ (sum + k[sum & 3]))) & 0xFFFFFFFF
    return v0, v1

def pad(data, block_size=8):
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

def unpad(data):
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 8:
        return data
    return data[:-pad_len]

def bytes_to_block(b):
    return int.from_bytes(b[:4], 'little'), int.from_bytes(b[4:8], 'little')

def block_to_bytes(b):
    return b[0].to_bytes(4, 'little') + b[1].to_bytes(4, 'little')

def prepare_key(key_bytes):
    return [int.from_bytes(key_bytes[i:i+4], 'little') for i in range(0, 16, 4)]

def encrypt(data: bytes, key: bytes) -> bytes:
    k = prepare_key(key)
    padded = pad(data)
    ciphertext = b""
    for i in range(0, len(padded), 8):
        block = bytes_to_block(padded[i:i+8])
        enc = encrypt_block(block, k)
        ciphertext += block_to_bytes(enc)
    return ciphertext

def decrypt(data: bytes, key: bytes) -> bytes:
    k = prepare_key(key)
    plaintext = b""
    for i in range(0, len(data), 8):
        block = bytes_to_block(data[i:i+8])
        dec = decrypt_block(block, k)
        plaintext += block_to_bytes(dec)
    return unpad(plaintext)
