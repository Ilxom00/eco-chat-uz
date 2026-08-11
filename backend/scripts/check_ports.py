import socket
for port in [80, 8000, 8080, 5000, 3000, 8001]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    res = s.connect_ex(('127.0.0.1', port))
    print(f"Port {port}: {res} (0 means open)")
