#!/usr/bin/env python
"""
gear_server — 本地 API 服务器
为齿轮工具提供 AI 分析接口（DeepSeek）
"""
import json, os, sys, http.server, socketserver, urllib.request, urllib.error
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8899
DATA_DIR = Path(__file__).parent

PROMPTS = {
    1: """你是一个拆解逻辑的教练。用户给了一个现象，请用三齿轮框架中的【齿轮1：拆解逻辑】帮他分析。

要求：
1. 用2×2矩阵分析（明确横轴和纵轴是什么，四个象限各代表什么）
2. 剥三层（现象层 → 结构层 → 根因/人性层）
3. 做反事实推演（去掉或反转一个关键变量，结构会怎样变化）

格式要求：
- 简洁，每部分2-3句话
- 使用中文
- 最后以"💡 思考题"结尾

用户输入的现象：""",

    2: """你是一个洞察人性的教练。用户给了一个行为观察，请用三齿轮框架中的【齿轮2：洞察人性】帮他分析。

要求：
1. 判断驱动力：恐惧/欲望/惯性，哪个是主要的
2. 定位到疼痛vs焦虑象限（可量化+现在发生=疼痛，最值钱）
3. 画利益地图：显性利益（嘴上说的）vs 隐性利益（实际在意的）
4. 校验问题：他为什么没做我建议的事？

格式要求：
- 简洁，每部分2-3句话
- 使用中文
- 最后以"💡 思考题"结尾

用户输入的观察：""",

    3: """你是一个构建系统的教练。用户给了一个洞察/判断，请用三齿轮框架中的【齿轮3：构建系统】帮他产出。

要求：
1. 建议产出形态：框架/行动/决策日志/产品化方案
2. 给出具体的产出建议
3. 设计反馈闭环：接下来怎么做、什么信号验证

格式要求：
- 简洁，每部分2-3句话
- 使用中文
- 最后以"💡 思考题"结尾

用户输入的洞察：""",
}

def get_api_key():
    """从环境变量或 bashrc 读取 API Key"""
    key = os.environ.get("OPENAI_API_KEY", "")
    if key and len(key) > 10:
        return key
    bashrc = Path.home() / ".bashrc"
    if bashrc.exists():
        for line in bashrc.read_text().splitlines():
            if line.startswith("export OPENAI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip("'\"")
                if val and len(val) > 10:
                    return val
    return ""

API_KEY = get_api_key()
API_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
MODEL = "deepseek-chat"

class GearHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/analyze":
            self.handle_analyze()
        elif self.path == "/api/compare":
            self.handle_compare()
        else:
            self.send_error(404)

    def handle_analyze(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            gear = body.get("gear")
            text = body.get("text", "").strip()
            if gear not in (1, 2, 3) or not text:
                self.send_json({"error": "gear(1/2/3) 和 text 必填"}, 400)
                return
            if not API_KEY:
                self.send_json({"analysis": "⚠️ 未检测到 API Key\n终端执行: `export OPENAI_API_KEY='你的key'` 后重启 `gear serve`"})
                return
            analysis = self.call_deepseek(gear, text)
            self.send_json({"analysis": analysis})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_compare(self):
        """对比用户的表达和AI的分析"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            user_text = body.get("user_text", "").strip()
            ai_text = body.get("ai_text", "").strip()
            if not user_text or not ai_text:
                self.send_json({"error": "user_text 和 ai_text 必填"}, 400)
                return
            if not API_KEY:
                self.send_json({"comparison": "⚠️ 未检测到 API Key"})
                return
            prompt = f"""请对比以下两份分析，指出差异和改进建议。

【AI 的分析】
{ai_text}

【用户的表达】
{user_text}

请从以下三个方面给出反馈：
1. 用户抓住了哪些要点，漏掉了哪些？
2. 用户的优势和需要提升的地方分别是什么？
3. 具体建议：下次可以怎么改进？

格式简洁，中文，以"💪 你的优势"和"🎯 可以提升"两部分呈现。"""
            data = json.dumps({"model": MODEL, "messages": [
                {"role": "system", "content": "你是三齿轮框架的教练，帮助用户提升结构化思维能力。"},
                {"role": "user", "content": prompt}
            ], "temperature": 0.7, "max_tokens": 600}).encode("utf-8")
            req = urllib.request.Request(
                f"{API_BASE}/chat/completions",
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            comparison = result["choices"][0]["message"]["content"]
            self.send_json({"comparison": comparison})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def call_deepseek(self, gear, text):
        prompt = PROMPTS.get(gear, "") + text
        data = json.dumps({"model": MODEL, "messages": [
            {"role": "system", "content": "你是三齿轮框架的训练教练。帮助用户用结构化思维分析问题。"},
            {"role": "user", "content": prompt}
        ], "temperature": 0.7, "max_tokens": 800}).encode("utf-8")
        req = urllib.request.Request(
            f"{API_BASE}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")[:300]
            return f"⚠️ API 请求失败 (HTTP {e.code}): {error_body}"
        except Exception as e:
            return f"⚠️ 请求异常: {str(e)}"

    def send_json(self, obj, status=200):
        self.send_response(status)
        self.send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        if "api" in str(args[0]):
            print(f"[gear] {args[0]} {args[1]} {args[2]}")


def main():
    import socket
    os.chdir(DATA_DIR)
    hostname = socket.gethostbyname(socket.gethostname())
    print(f"📡 齿轮服务器启动")
    if API_KEY:
        print(f"   AI 分析: ✅ DeepSeek 已连接")
    else:
        print(f"   AI 分析: ⚠️ 未配置 Key")
    print(f"   电脑: http://localhost:{PORT}/gear.html")
    print(f"   手机: http://{hostname}:{PORT}/gear.html（同一WiFi）")
    print(f"   Ctrl+C 停止\n")
    with socketserver.TCPServer((HOST, PORT), GearHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")

if __name__ == "__main__":
    main()
