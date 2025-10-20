import time
import jwt
from config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

try:
    app_id = settings.GITHUB_APP_ID
    private_key = settings.private_key_bytes

    try:
        serialization.load_pem_private_key(
            private_key,
            password=None,
            backend=default_backend()
        )
        print("Successfully loaded private key with cryptography.")
    except Exception as e:
        print(f"Failed to load private key with cryptography: {e}")
        raise

    now = int(time.time())
    
    payload = {
        'iat': now,
        'exp': now + (10 * 60),
        'iss': app_id
    }
    
    # Encode the JWT
    jwt_token = jwt.encode(
        payload,
        private_key,
        algorithm='RS256'
    )
    
    print("Successfully created JWT token:")
    print(jwt_token)
    
    print("\nJWT token created successfully! This token can be used for GitHub API calls.")

except Exception as e:
    print(f"Failed to create JWT token: {e}")
    if 'private_key' in locals():
        print(f"Key type: {type(private_key).__name__}")
        print(f"Key length: {len(private_key) if hasattr(private_key, '__len__') else 'N/A'}")
    raise

