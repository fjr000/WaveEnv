"""清理未正确关闭的连接"""
import subprocess
import re
import sys

def get_connections_by_state(state="CLOSE_WAIT"):
    """获取指定状态的连接"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="gbk"  # Windows 中文环境使用 GBK 编码
        )
        
        connections = []
        for line in result.stdout.split('\n'):
            if state in line and ':8000' in line:
                # 提取 PID
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    connections.append((line.strip(), pid))
        return connections
    except Exception as e:
        print(f"Error getting connections: {e}")
        return []

def kill_process(pid):
    """终止指定 PID 的进程"""
    try:
        subprocess.run(["taskkill", "/F", "/PID", pid], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        print(f"Error killing process {pid}: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Connection Cleanup Script")
    print("=" * 60)
    print()
    
    # 检查各种异常状态的连接
    states = ["CLOSE_WAIT", "FIN_WAIT_2", "TIME_WAIT"]
    
    all_connections = {}
    for state in states:
        connections = get_connections_by_state(state)
        if connections:
            all_connections[state] = connections
            print(f"{state} connections (port 8000): {len(connections)}")
            for conn, pid in connections[:5]:  # 只显示前5个
                print(f"  PID {pid}: {conn[:80]}")
            if len(connections) > 5:
                print(f"  ... and {len(connections) - 5} more")
            print()
    
    if not all_connections:
        print("No abnormal connections found on port 8000.")
        print("All connections appear to be in normal state.")
        return
    
    # 统计需要清理的 PID
    pids_to_kill = set()
    for state, connections in all_connections.items():
        for _, pid in connections:
            pids_to_kill.add(pid)
    
    print(f"\nTotal unique PIDs to clean: {len(pids_to_kill)}")
    print(f"PIDs: {', '.join(sorted(pids_to_kill))}")
    print()
    
    # 询问是否清理
    response = input("Do you want to kill these processes? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # 清理进程
    print("\nCleaning up processes...")
    success_count = 0
    failed_count = 0
    
    for pid in sorted(pids_to_kill):
        print(f"  Killing PID {pid}...", end=" ")
        if kill_process(pid):
            print("OK")
            success_count += 1
        else:
            print("FAILED")
            failed_count += 1
    
    print(f"\nCleanup complete: {success_count} succeeded, {failed_count} failed")
    print("\nNote: If the backend server was killed, please restart it.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)

