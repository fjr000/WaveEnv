"""
测试后端连接脚本。

用于独立测试后端服务是否可访问。
"""

import httpx
import sys

BACKEND_URL = "http://localhost:8000"

def test_connection():
    """测试后端连接。"""
    print(f"正在测试后端连接: {BACKEND_URL}")
    print("-" * 50)
    
    try:
        # 配置客户端，禁用代理和 SSL 验证（开发环境）
        with httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            proxies=None,  # 禁用代理
        ) as client:
            # 测试根路径（更可靠）
            print("1. 测试根路径 / ...")
            try:
                response = client.get(f"{BACKEND_URL}/")
                print(f"   状态码: {response.status_code}")
                print(f"   响应头: {dict(response.headers)}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   响应: {data}")
                        print("   ✓ 根路径正常")
                    except Exception as e:
                        print(f"   响应文本: {response.text[:200]}")
                        print(f"   ⚠ JSON 解析失败: {e}")
                        if response.status_code == 200:
                            print("   ✓ 根路径可访问（状态码 200）")
                else:
                    print(f"   响应文本: {response.text[:200]}")
                    print(f"   ✗ 根路径返回错误状态码: {response.status_code}")
            except httpx.ConnectError as e:
                print(f"   ✗ 连接失败：无法连接到服务器")
                print(f"   错误详情: {e}")
                print("   请确保后端服务已启动")
                return False
            except httpx.TimeoutException:
                print("   ✗ 连接超时")
                return False
            except Exception as e:
                print(f"   ✗ 错误: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
            
            # 测试健康检查端点
            print("\n2. 测试 /health 端点...")
            try:
                response = client.get(f"{BACKEND_URL}/health")
                print(f"   状态码: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   响应: {data}")
                        print("   ✓ /health 端点正常")
                    except:
                        print(f"   响应文本: {response.text[:200]}")
                        if response.status_code == 200:
                            print("   ✓ /health 端点可访问（状态码 200）")
                else:
                    print(f"   ✗ /health 端点返回错误状态码: {response.status_code}")
                    print(f"   响应文本: {response.text[:200]}")
            except Exception as e:
                print(f"   ✗ 错误: {type(e).__name__}: {e}")
            
            # 测试 API 文档
            print("\n3. 测试 API 文档 /docs ...")
            try:
                response = client.get(f"{BACKEND_URL}/docs")
                print(f"   状态码: {response.status_code}")
                if response.status_code == 200:
                    print("   ✓ API 文档可访问")
                else:
                    print(f"   ✗ API 文档返回错误状态码: {response.status_code}")
            except Exception as e:
                print(f"   ✗ 错误: {type(e).__name__}: {e}")
            
            print("\n" + "=" * 50)
            print("✓ 后端连接测试完成")
            return True
            
    except Exception as e:
        print(f"\n✗ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

