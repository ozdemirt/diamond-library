"""
Pure-Python Localtunnel Client for DiamondLibrary.
Maintains persistent standby connections to localtunnel.me:port,
and proxies incoming HTTP requests to 127.0.0.1:8000.
"""

import os
import sys
import time
import socket
import select
import threading
import urllib.request
import json

SUBDOMAIN = "diamondlibrary"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8000
SERVER_HOST = "localtunnel.me"
POOL_SIZE = 5


def get_public_ip() -> str:
    """Fetch public IP for localtunnel bypass reminder."""
    for api in ["https://api.ipify.org", "https://ifconfig.me/ip", "https://loca.lt/mytunnelpassword"]:
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.read().decode("utf-8").strip()
        except Exception:
            pass
    return "Bilinmiyor"


def register_tunnel(subdomain: str = SUBDOMAIN) -> dict:
    """Register custom subdomain on localtunnel.me."""
    url = f"https://{SERVER_HOST}/{subdomain}"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def bridge_connection(remote_sock, local_sock, initial_data=b""):
    """Bridge data bidirectionally between remote and local sockets."""
    try:
        if initial_data:
            local_sock.sendall(initial_data)

        while True:
            r, _, _ = select.select([remote_sock, local_sock], [], [], 30)
            if not r:
                break
            if remote_sock in r:
                data = remote_sock.recv(65536)
                if not data:
                    break
                local_sock.sendall(data)
            if local_sock in r:
                data = local_sock.recv(65536)
                if not data:
                    break
                remote_sock.sendall(data)
    except Exception:
        pass
    finally:
        try:
            remote_sock.close()
        except Exception:
            pass
        try:
            local_sock.close()
        except Exception:
            pass


def handle_worker(remote_port: int):
    """Standby worker waiting for incoming remote request."""
    try:
        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        remote_sock.connect((SERVER_HOST, remote_port))

        # Wait until remote server sends HTTP request
        r, _, _ = select.select([remote_sock], [], [], 60)
        if not r:
            remote_sock.close()
            return

        initial_data = remote_sock.recv(65536)
        if not initial_data:
            remote_sock.close()
            return

        # Connect to local web server
        local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        local_sock.connect((LOCAL_HOST, LOCAL_PORT))

        bridge_connection(remote_sock, local_sock, initial_data)

    except Exception:
        pass


def run_tunnel(subdomain: str = SUBDOMAIN):
    print("=" * 80)
    print(f" 🚀  DIAMONDLIBRARY LOCALTUNNEL İSTEMCİSİ BAŞLATILIYOR  🚀")
    print("=" * 80)

    try:
        tunnel_info = register_tunnel(subdomain)
    except Exception as e:
        print(f"⚠️ '{subdomain}' alt alan adı kaydedilemedi, alternatif deneniyor... ({e})")
        subdomain = "diamond-library"
        tunnel_info = register_tunnel(subdomain)

    remote_port = tunnel_info["port"]
    tunnel_url = tunnel_info["url"]
    public_ip = get_public_ip()

    print(f"  ✓ Tünel Başarıyla Açıldı!")
    print(f"  🌐 Genel İnternet Adresi (URL) : {tunnel_url}")
    print(f"  🔑 Tünel Şifresi (Public IP)   : {public_ip}")
    print(f"  🏠 Yerel Sunucu                : http://{LOCAL_HOST}:{LOCAL_PORT}")
    print("=" * 80 + "\n")

    # Maintain pool of standby workers
    while True:
        try:
            t = threading.Thread(target=handle_worker, args=(remote_port,), daemon=True)
            t.start()
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(1)


if __name__ == "__main__":
    target_sub = sys.argv[1] if len(sys.argv) > 1 else SUBDOMAIN
    run_tunnel(target_sub)
