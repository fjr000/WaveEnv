"""简单测试后端连接"""
import httpx
import socket

BACKEND_URL = "http://localhost:8000"

def test_connection():
    print(f"Testing backend connection: {BACKEND_URL}")
    print("-" * 50)
    
    # 1. 测试端口连接
    print("1. Testing port connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", 8000))
        sock.close()
        if result == 0:
            print("   ✓ Port 8000 is open")
        else:
            print(f"   ✗ Port 8000 is closed (result: {result})")
            return
    except Exception as e:
        print(f"   ✗ Socket error: {e}")
        return
    
    # 2. 测试 HTTP 连接 (localhost)
    print("\n2. Testing HTTP connection (localhost)...")
    try:
        with httpx.Client(timeout=5.0, proxies=None) as client:
            response = client.get(f"{BACKEND_URL}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
                print("   ✓ Connection successful")
            else:
                print(f"   ✗ Unexpected status: {response.status_code}")
    except httpx.ConnectError as e:
        print(f"   ✗ Connection error: {e}")
    except httpx.TimeoutException:
        print("   ✗ Timeout")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
    
    # 3. 测试 HTTP 连接 (127.0.0.1)
    print("\n3. Testing HTTP connection (127.0.0.1)...")
    alt_url = BACKEND_URL.replace("localhost", "127.0.0.1")
    try:
        with httpx.Client(timeout=5.0, proxies=None) as client:
            response = client.get(f"{alt_url}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
                print("   ✓ Connection successful")
            else:
                print(f"   ✗ Unexpected status: {response.status_code}")
    except httpx.ConnectError as e:
        print(f"   ✗ Connection error: {e}")
    except httpx.TimeoutException:
        print("   ✗ Timeout")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
    
    # 4. 测试健康检查端点
    print("\n4. Testing health endpoint...")
    try:
        with httpx.Client(timeout=5.0, proxies=None) as client:
            response = client.get(f"{BACKEND_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
                print("   ✓ Health check successful")
            else:
                print(f"   ✗ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_connection()

