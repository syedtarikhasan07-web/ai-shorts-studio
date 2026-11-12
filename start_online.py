import subprocess
import time
import re
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"
STREAMLIT_EXE = BASE_DIR / ".venv" / "Scripts" / "streamlit.exe"
CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"

def get_short_url(long_url: str) -> str:
    """Attempts to shorten the URL via ulvis.net or tinyurl."""
    try:
        encoded = urllib.parse.quote(long_url)
        api_url = f"https://ulvis.net/api.php?url={encoded}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            short = resp.read().decode('utf-8').strip()
            if short.startswith("http"):
                return short
    except Exception:
        pass
    return long_url

def main():
    print("========================================================")
    print("           Starting AI Shorts Studio (Online)           ")
    print("========================================================")

    # 1. Start Streamlit
    print("[1/3] Launching Web UI server...")
    st_proc = subprocess.Popen(
        [str(PYTHON_EXE), "-m", "streamlit", "run", "app.py", "--server.headless=true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(3)

    # 2. Start Cloudflare Tunnel
    print("[2/3] Connecting secure public tunnel...")
    cf_proc = subprocess.Popen(
        [str(CLOUDFLARED_EXE), "tunnel", "--url", "http://localhost:8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    for line in iter(cf_proc.stdout.readline, ''):
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        print("[-] Could not detect tunnel URL. Check your internet connection.")
        return

    # 3. Shorten URL
    print("[3/3] Generating clean short web address...")
    short_url = get_short_url(tunnel_url)

    print("\n========================================================")
    print("🎉 SUCCESS! Your AI Shorts Studio is online and active!")
    print("========================================================")
    print(f"\n👉 SHORT LINK (Share with anyone):")
    print(f"   {short_url}")
    print(f"\n👉 DIRECT LINK:")
    print(f"   {tunnel_url}")
    print(f"\n👉 LOCAL PC LINK:")
    print(f"   http://localhost:8501")
    print("\n[NOTE] Keep this terminal window OPEN while sharing.")
    print("Press Ctrl+C to stop the server anytime.\n")

    try:
        cf_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping AI Shorts Studio...")
        st_proc.terminate()
        cf_proc.terminate()

if __name__ == "__main__":
    main()
