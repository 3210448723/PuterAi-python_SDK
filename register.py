# 用浏览器访问 https://puter.com/ 会自动生成一个 token：其中有一个请求 https://puter.com/signup 会自动创建一个临时账户，获取其返回值字典中的token字段即可，将其写入.env文件中API_TOKEN="your_token"
import asyncio
from playwright.async_api import async_playwright

async def get_signup_token():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 创建全新环境，添加更真实的浏览器设置
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        page = await context.new_page()
        token = None

        async def handle_response(response):
            nonlocal token
            if response.url == "https://puter.com/signup" and response.request.method == "POST":
                print(f"检测到 signup 响应，状态码: {response.status}")
                try:
                    # 先获取响应文本
                    response_text = await response.text()
                    print(f"响应内容: {response_text[:500]}...")  # 只打印前500字符

                    # 如果响应是：You are not allowed to sign up
                    # 说明该ip已被限制注册
                    if "You are not allowed to sign up" in response_text:
                        token = -1  # 设置为 -1 表示注册失败
                        return
                    
                    # 如果状态码是 200-299，尝试解析 JSON
                    if 200 <= response.status < 300:
                        response_data = await response.json()
                        token = response_data.get("token")
                        print(f"成功获取到 token: {token}")
                    else:
                        print(f"请求失败，状态码: {response.status}")
                        
                except Exception as e:
                    print(f"处理响应失败: {e}")
            elif "signup" in response.url:
                print(f"其他 signup 相关请求: {response.url}, 状态码: {response.status}")

        page.on("response", handle_response)
        
        print("正在访问 https://puter.com/...")
        await page.goto("https://puter.com/", wait_until="networkidle", timeout=1000*120)  # 增加超时时间到120秒
        
        # 等待页面完全加载
        await asyncio.sleep(3)
        
        # 尝试触发注册流程，可能需要点击某些按钮或等待更长时间
        print("等待自动注册流程...")
        await asyncio.sleep(10)  # 增加等待时间
        
        await browser.close()
        
        # 将 token 写入 .env 文件
        if token and token != -1:
            with open('.env', 'w') as f:
                f.write(f'API_TOKEN="{token}"\n')
            print(f"Token 已写入 .env 文件: {token}")
        elif token == -1:
            print("注册失败，未获取到有效的 token。请更换 IP 后重试。")
            return -1
        else:
            print("未获取到 token")
            
        return token

if __name__ == "__main__":
    token = asyncio.run(get_signup_token())
    if token and token != -1:
        print("Token:", token)
        exit(0)  # 成功退出
    elif token == -1:
        print("注册被限制，退出程序")
        exit(1)  # 注册被限制，返回错误码1
    else:
        print("注册失败，未知错误")
        exit(2)  # 其他错误，返回错误码2