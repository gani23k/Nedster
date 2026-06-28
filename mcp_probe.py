import socket
import json

def request(sock, req):
    sock.sendall((json.dumps(req) + '\n').encode())
    res = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk: break
            res += chunk
            if b'\n' in res: break
        except socket.timeout:
            break
    return res.decode()

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(('127.0.0.1', 9876))
    
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "nedster", "version": "1.0.0"}}}
    print("Init:", request(s, init_req))
    
    s.sendall(b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')
    
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    print("Tools:", request(s, tools_req))
    s.close()
except Exception as e:
    print("Error:", e)
