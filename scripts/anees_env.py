"""Read Anees secrets from the shell env, falling back to the Windows User env (winreg). Never prints values."""
import os


def env(name, default=None):
    v = os.environ.get(name)
    if v:
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
            v, _ = winreg.QueryValueEx(k, name)
            return v or default
    except Exception:
        return default


SUPABASE_URL = env('ANEES_SUPABASE_URL', 'https://yljcbdxvnkfrwvelypfu.supabase.co')
SUPABASE_REF = SUPABASE_URL.split('//')[1].split('.')[0]
ANON_KEY = env('ANEES_SUPABASE_ANON_KEY')
SERVICE_KEY = env('ANEES_SUPABASE_SERVICE_KEY')
ACCESS_TOKEN = env('SUPABASE_ACCESS_TOKEN')
ELEVEN_KEY = env('ELEVENLABS_API_KEY')
OPENAI_KEY = env('OPENAI_API_KEY')
