import subprocess
import re

def check_proxy_ip(proxy_ip: str, proxy_port: int) -> bool:
    """
    检查通过代理请求外部网站时，显示的IP地址是否与传入的代理IP一致。

    Args:
        proxy_ip (str): 代理服务器的IP地址。
        proxy_port (int): 代理服务器的端口。

    Returns:
        bool: 如果通过代理请求得到的IP地址与传入的proxy_ip一致，则返回True，否则返回False。
    """
    curl_command = f"curl -4 -x http://{proxy_ip}:{proxy_port} ping0.cc --connect-timeout 3 --max-time 6"

    try:
        # 执行curl命令，并捕获其输出
        # text=True 解码输出为字符串
        # capture_output=True 捕获stdout和stderr
        # check=True 如果命令返回非零退出码，则抛出CalledProcessError
        result = subprocess.run(
            curl_command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        # curl -4 ping0.cc 正常情况下只输出IP地址，所以我们直接取strip()后的结果
        retrieved_ip = result.stdout.strip()

        # 使用正则表达式验证是否是有效的IP地址
        # 简单验证IPv4格式，确保我们得到的是IP而不是其他错误信息
        ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        if ip_pattern.match(retrieved_ip):
            print(f"通过代理 {proxy_ip}:{proxy_port} 请求到的IP是: {retrieved_ip}")
            return retrieved_ip == proxy_ip
        else:
            print(f"未能从curl命令输出中提取到有效IP地址。输出: {retrieved_ip}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"执行curl命令时发生错误: {e}")
        print(f"标准输出: {e.stdout}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"发生未知错误: {e}")
        return False

if __name__ == "__main__":
    # 示例用法
    # 替换为您的代理IP和端口
    my_proxy_ip = "127.0.0.1"  # 假设您的代理IP
    my_proxy_port = 10809       # 假设您的代理端口

    if check_proxy_ip(my_proxy_ip, my_proxy_port):
        print(f"IP一致！代理 {my_proxy_ip}:{my_proxy_port} 正在正常工作并使用其IP地址。")
    else:
        print(f"IP不一致或检测失败。代理 {my_proxy_ip}:{my_proxy_port} 可能没有正确工作。")

    # 您也可以尝试一个无效的代理或者您自己的真实IP来测试
    # 例如，如果直接访问ping0.cc，会显示您的真实IP
    # 如果您没有代理服务器，可以尝试一个明显不同的IP来观察结果
    # print("\n尝试用一个不同的IP进行比较:")
    # print(check_proxy_ip("192.168.1.1", 8888)) # 假设这是一个不可能的代理IP