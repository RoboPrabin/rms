import json
import base64
KEY = "prabinchand9878"

def _xor_bytes(data: bytes, key: str) -> bytes:
    kb = key.encode("utf-8")
    return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(data))

def encrypt_data(data: dict) -> str:
    # Serialize to UTF-8 JSON
    plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
    # XOR with key
    cipher_bytes = _xor_bytes(plaintext, KEY)
    # URL-safe base64 (includes padding for exact recovery)
    return base64.urlsafe_b64encode(cipher_bytes).decode('ascii')

def decrypt_data(token: str) -> dict:
    # Accept tokens with or without padding; add padding if missing
    # padding = '=' * (-len(token) % 4)
    # token_padded = token + padding
    cipher_bytes = base64.urlsafe_b64decode(token.encode('ascii'))
    plaintext = _xor_bytes(cipher_bytes, KEY)
    return json.loads(plaintext.decode('utf-8'))



# Example

# Example usage
if __name__ == "__main__":

    payload = {
                "auth": True,
                "user": "prabin",
                "role": "admin"
        }
    
    encrypted = encrypt_data(payload)
    print("Encrypted:", encrypted)
    
    decrypted = decrypt_data(encrypted)
    print("Decrypted:", decrypted)

