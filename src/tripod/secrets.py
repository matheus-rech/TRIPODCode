"""Credentials remain in the backend environment or the operating-system keychain."""
import os

def get_key():
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        import keyring
        key = keyring.get_password('TRIPODCode', 'openai')
    if not key:
        raise ValueError('Configure an API key in Settings')
    return key

def save_key(value):
    if not value or len(value) > 1024:
        raise ValueError('Invalid credential')
    import keyring
    backend = keyring.get_keyring()
    # Do not silently fall back to plaintext storage on headless platforms.
    if not type(backend).__module__.startswith(('keyring.backends.macOS', 'keyring.backends.SecretService', 'keyring.backends.Windows')):
        raise ValueError('A supported operating-system keychain is unavailable; use OPENAI_API_KEY in the backend environment')
    keyring.set_password('TRIPODCode', 'openai', value)
