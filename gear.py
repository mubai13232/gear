#!/usr/bin/env python
"""
三齿轮 CLI — 随时录入、复盘、同步
用法:
  gear 1 <内容>    # 齿轮1：拆解逻辑
  gear 2 <内容>    # 齿轮2：洞察人性
  gear 3 <内容>    # 齿轮3：构建系统
  gear list [n]    # 最近 n 条记录（默认10）
  gear today       # 今天的记录
  gear week        # 本周复盘
  gear export      # 导出到 Obsidian 柏仓
  gear sync        # 推送到 GitHub（配置后生效）
"""
import json, sys, os
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "data.json")
OBSIDIAN_VAULT = r"E:\柏仓\齿轮记录"

GEAR_NAMES = {1: "① 拆结构", 2: "② 挖人性", 3: "③ 压产出"}
GEAR_CHEATS = {
    1: "2×2矩阵 · 剥三层 · 反事实推演",
    2: "恐惧/欲望/惯性 · 疼痛vs焦虑 · 利益地图",
    3: "框架/三句话/行动 · 决策日志 · 反馈闭环",
}

def load():
    if not os.path.exists(DATA_FILE):
        return {"entries": []}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add(gear, text):
    gear = int(gear)
    assert gear in (1, 2, 3), f"齿轮编号：1=拆结构 2=挖人性 3=压产出"
    data = load()
    entry = {
        "gear": gear,
        "text": text.strip(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["entries"].append(entry)
    save(data)
    print(f"✓ 齿轮{gear} 已记录 ({len(data['entries'])}条)")
    return entry

def cmd_list(n=10):
    data = load()
    entries = data["entries"][-n:]
    if not entries:
        print("暂无记录。用 gear 1/2/3 <内容> 开始记录。")
        return
    for e in reversed(entries):
        gear_label = GEAR_NAMES.get(e["gear"], "?")
        print(f"[{e['time']}] {gear_label}")
        print(f"  {e['text']}")
        print()

def cmd_today():
    today = datetime.now().strftime("%Y-%m-%d")
    data = load()
    entries = [e for e in data["entries"] if e["time"].startswith(today)]
    if not entries:
        print("今天还没有记录。")
        return
    print(f"今日记录（{len(entries)}条）:")
    print("=" * 40)
    for e in entries:
        print(f"[{GEAR_NAMES.get(e['gear'], '?')}] {e['text']}")
    print("=" * 40)

def cmd_week():
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    data = load()
    entries = [e for e in data["entries"] if e["time"] >= week_ago]
    if not entries:
        print("本周没有记录。")
        return
    counts = {1: 0, 2: 0, 3: 0}
    for e in entries:
        counts[e["gear"]] = counts.get(e["gear"], 0) + 1
    print(f"本周复盘（{len(entries)}条）:")
    print(f"  齿轮1 拆结构: {counts[1]}次")
    print(f"  齿轮2 挖人性: {counts[2]}次")
    print(f"  齿轮3 压产出: {counts[3]}次")
    print()
    for e in entries[-5:]:
        print(f"[{e['time']}] {GEAR_NAMES.get(e['gear'], '?')}: {e['text'][:60]}{'…' if len(e['text'])>60 else ''}")
    print()
    if counts[3] < counts[1] // 2 and counts[1] > 0:
        print("⚠️ 齿轮1拆得多，齿轮3产得少——有记得压产出。")
    if counts[1] == 0 and counts[2] == 0:
        print("💤 这周没拆也没挖——要么在休息，要么需要找个现象开拆。")

def cmd_export():
    """导出到 Obsidian 柏仓的齿轮记录文件夹"""
    data = load()
    if not data["entries"]:
        print("没有记录可导出。")
        return
    os.makedirs(OBSIDIAN_VAULT, exist_ok=True)
    # 按月份分组
    by_month = {}
    for e in data["entries"]:
        month = e["time"][:7]
        by_month.setdefault(month, []).append(e)
    total = 0
    for month, entries in sorted(by_month.items()):
        lines = [f"# 齿轮记录 · {month}\n", f"总条目：{len(entries)} 条\n"]
        counts = {1: 0, 2: 0, 3: 0}
        for e in entries:
            counts[e["gear"]] = counts.get(e["gear"], 0) + 1
        lines.append(f"齿轮1 拆结构：{counts[1]}次 | 齿轮2 挖人性：{counts[2]}次 | 齿轮3 压产出：{counts[3]}次\n")
        lines.append("---\n")
        for e in entries:
            lines.append(f"### [{e['time']}] {GEAR_NAMES.get(e['gear'], '?')}\n")
            lines.append(f"{e['text']}\n")
        filepath = os.path.join(OBSIDIAN_VAULT, f"{month}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        total += len(entries)
    print(f"✓ 已导出 {total} 条记录到 Obsidian：{OBSIDIAN_VAULT}")

def cmd_sync():
    print("GitHub 同步暂未配置。同步前会先执行 export 到 Obsidian。")
    cmd_export()

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd in ("list", "ls"):
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        cmd_list(n)
    elif cmd == "today":
        cmd_today()
    elif cmd in ("week", "w"):
        cmd_week()
    elif cmd == "export":
        cmd_export()
    elif cmd == "sync":
        cmd_sync()
    elif cmd == "serve":
        import subprocess, socket
        hostname = socket.gethostbyname(socket.gethostname())
        print(f"📡 手机在同一 WiFi 下访问：http://{hostname}:8899/gear.html")
        print(f"   Ctrl+C 停止服务")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "-m", "http.server", "8899"])
    elif cmd in ("1", "2", "3"):
        if len(args) < 2:
            print(f"齿轮{cmd}：{GEAR_CHEATS[int(cmd)]}")
            print("用法：gear 1 <你的分析内容>")
            return
        add(cmd, " ".join(args[1:]))
        print(f"  提示：{GEAR_CHEATS[int(cmd)]}")
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
