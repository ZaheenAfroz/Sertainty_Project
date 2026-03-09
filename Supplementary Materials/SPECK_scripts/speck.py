# speck.py - Multi-block SPECK-128/128 (ECB-style)

# SPECK is a lightweight block cipher developed by NSA. 
# This implementation uses a 128-bit key and 128-bit block size (SPECK-128/128).
# Each block is split into two 64-bit words (x, y) and the key into two 64-bit words.

def rol(x, k):
    """Left rotate a 64-bit integer `x` by `k` bits."""
    return ((x << k) & 0xFFFFFFFFFFFFFFFF) | (x >> (64 - k))

def ror(x, k):
    """Right rotate a 64-bit integer `x` by `k` bits."""
    return (x >> k) | ((x << (64 - k)) & 0xFFFFFFFFFFFFFFFF)

def encrypt_block(p, k):
    """
    Encrypt a single 128-bit block using SPECK-128/128.

    Args:
        p (tuple): Plaintext block as a tuple of two 64-bit integers.
        k (list): Expanded round keys (list of 32 64-bit keys).

    Returns:
        tuple: Encrypted block as two 64-bit integers.
    """
    x, y = p
    for i in range(32):
        x = ror(x, 8)
        x = (x + y) & 0xFFFFFFFFFFFFFFFF
        x ^= k[i]
        y = rol(y, 3)
        y ^= x
    return x, y

def decrypt_block(c, k):
    """
    Decrypt a single 128-bit block using SPECK-128/128.

    Args:
        c (tuple): Ciphertext block as a tuple of two 64-bit integers.
        k (list): Expanded round keys (list of 32 64-bit keys).

    Returns:
        tuple: Decrypted block as two 64-bit integers.
    """
    x, y = c
    for i in reversed(range(32)):
        y ^= x
        y = ror(y, 3)
        x ^= k[i]
        x = (x - y) & 0xFFFFFFFFFFFFFFFF
        x = rol(x, 8)
    return x, y

def expand_key(key):
    """
    Expand a 128-bit key into 32 round keys for encryption/decryption.

    Args:
        key (list): List of two 64-bit integers [k0, k1].

    Returns:
        list: List of 32 round keys (64-bit each).
    """
    m = 32  # Number of rounds
    k = [0] * m
    l = [key[1]]
    k[0] = key[0]
    for i in range(m - 1):
        l_next = (rol(l[i], 3) + k[i]) & 0xFFFFFFFFFFFFFFFF
        l_next ^= i
        k[i + 1] = ror(k[i], 8) ^ l_next
        l.append(l_next)
    return k

def pad(data, block_size=16):
    """
    Pad the plaintext to make it a multiple of block size (PKCS#7 style).

    Args:
        data (bytes): Original plaintext.
        block_size (int): Size of one block in bytes.

    Returns:
        bytes: Padded data.
    """
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

def unpad(data):
    """
    Remove padding from decrypted data.

    Args:
        data (bytes): Padded plaintext.

    Returns:
        bytes: Unpadded plaintext.
    """
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        return data
    return data[:-pad_len]

def bytes_to_block(data):
    """
    Convert 16 bytes into two 64-bit integers.

    Args:
        data (bytes): 16-byte data block.

    Returns:
        tuple: Two 64-bit integers.
    """
    return int.from_bytes(data[:8], 'little'), int.from_bytes(data[8:16], 'little')

def block_to_bytes(block):
    """
    Convert a tuple of two 64-bit integers back to 16-byte data.

    Args:
        block (tuple): Tuple of two 64-bit integers.

    Returns:
        bytes: 16-byte representation.
    """
    return block[0].to_bytes(8, 'little') + block[1].to_bytes(8, 'little')

def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt a plaintext of arbitrary length using SPECK-128/128 (ECB mode).

    Args:
        plaintext (bytes): Plaintext data to encrypt.
        key (bytes): 16-byte (128-bit) encryption key.

    Returns:
        bytes: Ciphertext.
    """
    key_parts = [int.from_bytes(key[0:8], 'little'), int.from_bytes(key[8:16], 'little')]
    k = expand_key(key_parts)
    padded = pad(plaintext)
    ciphertext = b""
    for i in range(0, len(padded), 16):
        block = bytes_to_block(padded[i:i+16])
        enc_block = encrypt_block(block, k)
        ciphertext += block_to_bytes(enc_block)
    return ciphertext

def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypt ciphertext using SPECK-128/128 (ECB mode).

    Args:
        ciphertext (bytes): Encrypted data.
        key (bytes): 16-byte (128-bit) decryption key.

    Returns:
        bytes: Decrypted plaintext.
    """
    key_parts = [int.from_bytes(key[0:8], 'little'), int.from_bytes(key[8:16], 'little')]
    k = expand_key(key_parts)
    plaintext = b""
    for i in range(0, len(ciphertext), 16):
        block = bytes_to_block(ciphertext[i:i+16])
        dec_block = decrypt_block(block, k)
        plaintext += block_to_bytes(dec_block)
    return unpad(plaintext)
