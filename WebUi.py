import json
import os
import time
import re
import threading
import urllib.request
import urllib.error
import urllib.parse
import concurrent.futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ================= 配置与常量（唯一权威来源） =================
UI_PORT = 8888
BACKEND_API_BASE = "http://127.0.0.1:22333"

KEYS_FILE = os.path.join(".", "data", "keys.json")
HISTORY_FILE = os.path.join(".", "data", "history.json")
SESSIONS_FILE = os.path.join(".", "data", "sessions.json")

# 使用可重入锁 RLock，彻底解决多层函数调用导致的死锁问题
FILE_LOCK = threading.RLock()

MODEL_COSTS = {
    "gemini-3.1-flash-image": {"512px": 4, "1k": 6, "2k": 10, "4k": 13},
    "gemini-3-pro-image": {"1k": 10, "2k": 10, "4k": 18},
}

MODEL_DISPLAY_NAMES = {
    "gemini-3.1-flash-image": "🍌Nano Banana 2",
    "gemini-3-pro-image": "🍌Nano Banana Pro",
}

SEVEN_DAYS_SEC = 7 * 24 * 3600
# favicon / avatar 共用的 base64 图标
FAVICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAL7ElEQVRogb1aCViU1Rp+Z2EGnGEPRClZbiKIWOL1plJKAioppoaCmruZpaaWtF3NtPJW95rdXMrcN1wrb4lrKc81F27uuFBugOwDA7PALDDz3ef/z8/AOANBQt/znGfOnHnPf773O9/5znf+M6JOnTpDp9ehCekCYDyAZwF0B+AHQM5BQ4KCcPnCWYgkIsBoADp4AHUmhEVEo6Ss1O5pV7IyERLRC6iuAFykgMwL41LGIOPwUWej6gEUAMgDkAlgD4B7zoDuSvem9OYVTwdQB4CclcXvpBEv+lIifRlf/erzTx2wCfHPMpxJLeCsVHzvhtNnNlEsgi5dnCkqVro7sBgB4BqAcQAkTTGcOXUCq3BDiMV8JSe3wAE3dUIqq5jNAFkBiLB733dNWs6ZjoIu14VPm/C6P0BgnsC4Wav0+WtvZtVaDbMqV6pVRCYtXT5/hhYtepcCO3ekR/weIZtUlxHV6fgZCO/WrTUz0LhwFljQFIEUAfC7D9q49nOmlq6kgQBX59xEEFONjrasX0vp2zeSQV9ua7915dwfVb6+WAVd7Qhw/qVryQNEYjFVFt8lIou99blS/92g4pV9adpkvk9AQCeaO2c2nf/lfzTnlZcelgAJunZpTGBnSzuPHpnETGkoJ9KVEumKG9yErEQ1nPJ1ZKgqIqnUpS2UbarsqicQ1BK/ry//2bNNcB8u+pTwSnOu8o9l75GqKM9G5Z8fLWlP5bli4XVXuru/1dJOPr4+/EIlq5G5iqWaJ6BQKvnfFUoPmjBhPGVkHKRhiYPbmwDxuivd3Y+0tMPM6VOYeatL2QwQ0flTxxxwQV0CqaS4iHZs30KjRj7fngSOcAQKWtrh4ukfG9ynhm1eM6ZOcsAtf//v1Fju3r1Ls16a1h4ECjgCxpaAg4OCuMDP3IbfUY1kNVaRt7e3HY6LUmX5v7IoxRG1aHkq0ya/2B4ETByBFoE/WrpISB1KWMwnou92bXHAxQ2KFTaCCluKocrPaS8XImlL9/MJY0cJqYMIkLJuW3btc8DNnCKkGOY6W9umrbtaOkzrpSUzENO/r2DVKsGqFlIX3iaIRHY4uVxOddXlzNU4XC1zn4jwcDucq5sbzXttDkX37v3QM9AiAutXf9aQOgju8/XqlQ64KRPHC5ucyhalrmRlOuAGPBNjW+LHjx6kV199hfw7BrQPAbmrnHSq+42squEH7h3dywH78/HvH9jkiN6YN9sBt/Xr1QwnLHB+aVWW0N496TRy1CiSubq2HYHnk4axEYzlNqvm5Vx0wAUGBhLV6olquYyzRshW9Q44iVRKJk0Jn26wJLCUnSnIbCNTlH+Hvvj8MxoYG/vwBA59k97IqozAorcXOuDeTlsgDF9HZNLQ9h07ae3KTyg46DE7XMqY0Q25VH3yZ8toS5mhGkn2pSxa8t5iiuwe0XoCHh4eRGZumk1C6qDnFeT2hAexNy+d5ketLC+mqJ5RfNvenZv5tqgekTbcjwf3N6wnbTFRXb0b6RtOd3wpJTKr7ch8unyZAwFxc2FrMneacnEHDBqACBArcOanI8jNy7PDPdEzCuFP9ufrK1f8C9lXszFv7is4dPRHvm3Rm+wM4ufnh0HxCYDVBIjEgMwNRo0WZzOPAlYRoPAHFH7s3ExCKK5WAUYV37+ouNhBx2b3gakvjmUVC7GDHYCtu/Y7waXa6rn5hfznqTNZqDMZ2MAl7JA/aUIKRHIPoLqU7SdyT5w5mYm4xJGI7BGJ1LFjkTwqCeE9egEyMEMb1YCrJ6rVhfhy/WZHJZtyobCwrizy1OnZlFrNZNKqeLd6EFtZdIedBbiwmPEt35aaPJL/Xph3hzw9PUkmk1FNRSHzBW2R7dAzfcpEh+fFxcfT+nVrqby4IT3nToGtWgMfLvl7o9jPFu+BPVsdcEMS4oRNji2+A3t3kL+/H9sDLmSRVCLmcV6envTqyzNo5YpPiWoN/Fqy1FSQazMhU+nO0vPDhzJoUOyA1hHI//UysypnfXMVv/v+JTTEAfdN+mYh+JjoxpVf+La5s2fxTSeOZdhwMhd2Ovtg0UKbVfdu39CieN/qMNq/31NsBHMlI2CqJDJr+NjcPybGhpNKJeyAw2WeRNTvbyw1CAkJsSV/Vy+eo8QhCSQWi8nX14esJh2LakQUH/ds+xDYvG5Vg/twBLQNbsTJ9cu/0KyZ0+nD9xfbhTmub3BwED3amaUFs2fN4NuvXTjDf8889oOArOVTbrFY0vYEOCvZxKqzj80cidoq288LF8yj+EEDafeuHfz3pGGJtG71Srp3O4diBzxNgwez9RE38Bn+2UnPDaVNG9fzbatWfPxQyjdJgIsYbyx4jc6ePmm3vfPvfHT1rxHrSFN2365fWNeulDR8GJ366ZDdrOTeuk4fL19Kw4c/xyLMwBiyWizk6+PdPgQal8ioKFr+0Qd07fL5Rioxf9/gJKxB2L2fSxxKr89/jRKHJtCUieNsPf97/CCV3r9NmooS6h4Z1f4EGpeEhARas3oVVZUX8crE9Ovbon67t3zVEBAE/7cKL3nPnDpJC1+fTyGhoeTi0vp3SK0iUF98fHx5V5FIfn8BBgR0JLIaiKw1jklbXVWjWSWKiop06D86KorSByc0S6DZXMiZqNUV+OFgBiwWy+9iU5NHAyJXwCDcP4hEgETCPo1mQF/G66K6/xtu377r0D/J3xcjNNpmx2g1gdaI7RU8/8rYws7Srj4sYVN4A9zlCET4Yu16GAwGuyeLRCIkicRQwQeTBgz+8wmEdwtDRHR/wKJnFnfzglZdidSxL2DjutXQqSsANz8euy19r0P/NUPiIKqxoLRrH8REz4Srq9ufS+DlaZN468JQzS42JK44dOwE9uz7FjNmzUVwWA+kpS3EqhXLkZ+fb9c3pV9fpFjqUBjeH3mP9sJVaQSS5x90Oo6Ie7Gl1+nkbU2g+O51BIR0Z/k8fy/mjaGD43H0+E/N9hsX/ThWRQSi0Lc3bvg8g2xZOHIlgbild4O19DgubUiC1crWn9Ld3czNQHlbKx8/KJYpb6pkDTIvlOblNKu8t1KOf6dE4IvBrsiNegxXw6Jw1etx3JJ3QqHIDVI3CbR+iXjijRsI6hlf300lFe6eAtuSwOTxY1il1iy0iLBn/wGn2EnDgxHX3YLh4bUASpCr6IFsUSdkm3yRV+MOdbUraixiWEgEDyVBZ+oK1xeOITr2Z0irsms4AicANL3MWykdFAqMGZPMac+OjcLiW7dxm9MHJTzlgtExxTCIxVC7BKDAIsPtGivytGaoTSaYxGZA5MIf4DhDKOSEyhrA5PE0OvtHeIuFe1hrWxFImz8Hcg9/wKwVFq8Sv105ixs3bzrFT1x8C76JdXhzYzAKRL7QdzDCoqhGrVsprC5lIIkekNRCKiZ+69AaAN/Cnaje1tN69ZPQPhyBXACOcewPChfPCwvuAzJfQNmRf8iXG5xbv16MJgs2bb+J0cNu4F42QSG/DT9FCeQdiiGRVUAmN0FjrIPeZAUdGYsLmyZClX9t79ztmlwuCkGv03UR1oKyLUi4SCV4ITkZKWOTER8fjyefjMadu04v253KextGQRMhRn5VDCoqu0NVHgpPUUcUfxmHvJzzEG7zI985YM2vJ8A1pgo34qK2IFEvvj7eqFBXtrrf24dTcVWiRHlVX9wvC0bA/hW4lHkYQh40fmmGdbexFpDI5HKYzXy04G7nq4QF3WYkDAajQ1u3ro9DXdk8qfsXtXAfHoCbegtCC/JxfsumeuXT1pzWr6/SyviF3ZgAJ1kALgMYXv+njrYWsVgCVcFvmDh1Grw8vaBSlUJVXuEwiqZcg+DYPripUKN62T4Y9TWc20zbWnDia2uNHzRaN56AWHCfxvI9gB4AdrcmOn245F1knTuHGTOmw9fHt0ncyBHD+IQuNDQMS5d9gOs3crBp3Wqn2OIjd9BFJ0FVsYrTJXJzYWa6wsUFZG3IgFrzd5tIAP7cGn0QpOjghpzLWfAMCOa/V2vVOHz4MNLeetfB/7/ftwOxQ0YAujJAzL1O9MPmdWswL+2degi3o3F5NhdUTgoR0jHX5v5uo3TH/wGCaXdW0jnSAwAAAABJRU5ErkJggg=="

# 需要拦截的伪装成成功的无效链接
TARGET_ERROR_URL = [
    "https://api.imastudio.com/open/v1/tasks/create",
    "https://api.imastudio.com/open/v1/product/list?app=ima&platform=web&category=image_to_image",
]


# ================= 核心工具 =================
def load_json(filename, default_val):
    if not os.path.exists(filename):
        return default_val
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default_val
            return json.loads(content)
    except Exception as e:
        print(f"[Warn] 无法加载文件 {filename}, 将使用默认值。错误: {e}")
        return default_val


def save_json(filename, data):
    # 原子化安全写入，先转文本再写入，防止异常打断导致文件被清空变成0字节
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception as e:
        print(f"[Error] 保存文件 {filename} 失败: {e}")


def calculate_cost(model, size, n):
    cost_map = MODEL_COSTS.get(model, {})
    return cost_map.get(size, 10) * int(n)


def get_available_key(cost):
    """获取可用Key并在内存中预扣费"""
    with FILE_LOCK:
        keys = load_json(KEYS_FILE, [])
        if not keys:
            return None, 0
        if cost == 0:
            for k_obj in keys:
                if k_obj.get("points", 0) > 0:
                    return k_obj["key"], k_obj["points"]
            return keys[0]["key"], keys[0].get("points", 0)
        for k_obj in keys:
            if k_obj.get("points", 0) >= cost:
                k_obj["points"] -= cost
                save_json(KEYS_FILE, keys)
                return k_obj["key"], k_obj["points"]
        return None, 0


def refund_key(api_key, cost):
    """如果生成失败，将预扣的点数退还"""
    if cost <= 0 or not api_key:
        return
    with FILE_LOCK:
        keys = load_json(KEYS_FILE, [])
        for k_obj in keys:
            if k_obj.get("key") == api_key:
                k_obj["points"] += cost
                save_json(KEYS_FILE, keys)
                break


def clean_and_load_history():
    with FILE_LOCK:
        history = load_json(HISTORY_FILE, [])
        now = time.time()
        valid = [h for h in history if now - h.get("created_at", now) <= SEVEN_DAYS_SEC]
        if len(valid) != len(history):
            save_json(HISTORY_FILE, valid)
        return valid


def save_history(records):
    with FILE_LOCK:
        now = time.time()
        for rec in records:
            rec["created_at"] = now
            if "id" not in rec:
                rec["id"] = f"h_{int(now * 1000)}_{hash(rec.get('url', '')) % 100000}"
        history = load_json(HISTORY_FILE, [])
        for rec in reversed(records):
            history.insert(0, rec)
        save_json(HISTORY_FILE, history)


def delete_history_item(item_id):
    with FILE_LOCK:
        history = load_json(HISTORY_FILE, [])
        history = [h for h in history if h.get("id") != item_id]
        save_json(HISTORY_FILE, history)


def load_sessions():
    with FILE_LOCK:
        return load_json(SESSIONS_FILE, [])


def save_sessions(sessions):
    with FILE_LOCK:
        save_json(SESSIONS_FILE, sessions)


def create_session():
    sessions = load_sessions()
    now = time.time()
    title = time.strftime("%Y-%m-%d %H:%M", time.localtime(now))
    new_sess = {
        "id": f"sess_{int(now * 1000)}",
        "title": title,
        "created_at": now,
        "messages": [],
    }
    sessions.insert(0, new_sess)
    save_sessions(sessions)
    return new_sess


def cleanup_ghost_tasks():
    """每次启动时清理因为 CLI 服务强行中断而遗留的 'generating' 幽灵卡片"""
    with FILE_LOCK:
        sessions = load_sessions()
        ghost_count = 0
        for s in sessions:
            for msg in s.get("messages", []):
                if msg.get("status") == "generating":
                    msg["status"] = "error"
                    msg["error"] = "CLI 服务中断"

                    n = msg.get("payload", {}).get("n", 1)
                    if not msg.get("urls"):
                        msg["urls"] = [None] * n
                    if not msg.get("times"):
                        msg["times"] = [None] * n
                    if not msg.get("keys"):
                        msg["keys"] = [None] * n
                    if not msg.get("costs"):
                        msg["costs"] = [None] * n
                    if not msg.get("remains"):
                        msg["remains"] = [None] * n
                    msg["errors"] = ["CLI 服务中断"] * n

                    ghost_count += 1

        if ghost_count > 0:
            save_sessions(sessions)
            print(
                f"🔧 [System] 发现并清理了 {ghost_count} 个由于服务异常中断遗留的幽灵任务。"
            )


def extract_urls_and_parse(data):
    urls = []
    if isinstance(data, dict) and "result" in data:
        result_str = str(data["result"])
        json_blocks = re.findall(
            r'\{[^{}]*"url"\s*:\s*"https?://[^"]+?"[^{}]*\}', result_str
        )
        for jb in json_blocks:
            try:
                parsed = json.loads(jb)
                if "url" in parsed and parsed["url"].startswith("http"):
                    urls.append(parsed["url"])
            except:
                pass
        if not urls:
            found = re.findall(
                r'(https?://[^\s"\'\\}<>]+\.(?:jpeg|jpg|png|webp|gif))', result_str
            )
            urls.extend(found)
    if not urls and isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
    if not urls:
        raw = str(data)
        found = re.findall(r'(https?://[^\s"\'\\}<>]+)', raw)
        for u in found:
            if len(u) > 15:
                urls.append(u)
    return list(dict.fromkeys(urls))


def call_backend(endpoint, payload, api_key):
    url = f"{BACKEND_API_BASE}{endpoint}"
    payload["api_key"] = api_key
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body_bytes, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            body = response.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except:
                parsed = {"result": body}
            print(
                f"[Backend {response.status}] {json.dumps(parsed, indent=2, ensure_ascii=False)[:500]}"
            )
            return parsed, response.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except:
            parsed = {"error": body}
        urls = extract_urls_and_parse(parsed)
        if urls:
            parsed["extracted_urls"] = urls
            return parsed, 200
        return parsed, e.code
    except Exception as e:
        return {"error": str(e)}, 500


# ================= 后台并发增量生成任务 =================
def single_generation(payload, cost_per_image, index):
    start_t = time.time()
    # 预扣费
    api_key, remaining = get_available_key(cost_per_image)
    if not api_key:
        return {
            "error": "点数不足，无可用Key",
            "time": 0,
            "cost": 0,
            "key": "",
            "remain": 0,
            "index": index,
        }

    payload_single = dict(payload)
    payload_single["n"] = 1
    endpoint = (
        "/v1/images/generations"
        if payload_single.get("type", "text_to_image") == "text_to_image"
        else "/v1/images/edits"
    )

    res_data, status = call_backend(endpoint, payload_single, api_key)
    time_taken = round(time.time() - start_t, 1)

    if "extracted_urls" not in res_data:
        urls = extract_urls_and_parse(res_data)
    else:
        urls = res_data["extracted_urls"]

    # --- 拦截点数耗尽的假链接 ---
    if urls and any(target in urls for target in TARGET_ERROR_URL):
        refund_key(api_key, cost_per_image)  # 退还预扣的点数
        return {
            "error": "云端API KEY 过期、无效或点数不足",
            "time": time_taken,
            "cost": 0,
            "key": api_key,
            "remain": remaining + cost_per_image,
            "index": index,
        }

    if urls:
        return {
            "url": urls[0],
            "time": time_taken,
            "cost": cost_per_image,
            "key": api_key,
            "remain": remaining,
            "index": index,
        }
    else:
        err_msg = res_data.get("error", "获取图片失败")
        if isinstance(err_msg, dict):
            err_msg = json.dumps(err_msg, ensure_ascii=False)
        refund_key(api_key, cost_per_image)  # 发生其他错误也退还点数
        return {
            "error": str(err_msg),
            "time": time_taken,
            "cost": 0,
            "key": api_key,
            "remain": remaining + cost_per_image,
            "index": index,
        }


def background_generation(session_id, chat_id, payload, n):
    cost_per_image = calculate_cost(payload.get("model_id"), payload.get("size"), 1)
    completed_count = 0

    # 多线程并发，独立插槽更新
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [
            executor.submit(single_generation, payload, cost_per_image, i)
            for i in range(n)
        ]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            idx = res["index"]

            with FILE_LOCK:
                sessions = load_sessions()
                for s in sessions:
                    if s["id"] == session_id:
                        for msg in s["messages"]:
                            if msg["id"] == chat_id:
                                # 确保各个数组已就绪
                                if not msg.get("urls"):
                                    msg["urls"] = [None] * n
                                if not msg.get("times"):
                                    msg["times"] = [None] * n
                                if not msg.get("errors"):
                                    msg["errors"] = [None] * n
                                if not msg.get("keys"):
                                    msg["keys"] = [None] * n
                                if not msg.get("costs"):
                                    msg["costs"] = [None] * n
                                if not msg.get("remains"):
                                    msg["remains"] = [None] * n

                                msg["times"][idx] = res["time"]
                                msg["keys"][idx] = res.get("key", "")
                                msg["costs"][idx] = res.get("cost", 0)
                                msg["remains"][idx] = res.get("remain", 0)

                                if "url" in res:
                                    msg["urls"][idx] = res["url"]
                                else:
                                    msg["errors"][idx] = res["error"]

                                completed_count += 1
                                if completed_count == n:
                                    # 全局完成，检查状态
                                    has_success = any(
                                        u for u in msg["urls"] if u is not None
                                    )
                                    msg["status"] = (
                                        "success" if has_success else "error"
                                    )
                                break
                        break
                save_sessions(sessions)

            if "url" in res:
                save_history(
                    [{"type": payload.get("type", "text_to_image"), "url": res["url"]}]
                )


# ================= HTML =================
HTML_PAGE_RAW = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="__FAVICON_PLACEHOLDER__">
    <title>Image Studio WebUI</title>
    <style>
        :root {
            --bg: #09090b; --surface: #18181b; --surface-hover: #27272a;
            --border: #3f3f46; --border-focus: #71717a;
            --text: #fafafa; --text-muted: #a1a1aa;
            --accent: #10b981; --accent-hover: #059669;
            --radius-lg: 16px; --radius-md: 10px; --radius-sm: 6px;
        }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #52525b; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        body { background: var(--bg); color: var(--text); height: 100vh; display: flex; overflow: hidden; }

        .sidebar { width: 300px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); z-index: 10; }
        .sidebar.collapsed { margin-left: -300px; border-right: none; }
        .sidebar-header { padding: 18px 20px; font-size: 16px; font-weight: 600; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .tab-nav { display: flex; border-bottom: 1px solid var(--border); }
        .tab-btn { flex: 1; padding: 12px 6px; background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 13px; font-weight: 500; transition: 0.2s; }
        .tab-btn.active { color: var(--text); border-bottom: 2px solid var(--text); }
        .tab-content { flex: 1; overflow-y: auto; padding: 15px; display: none; }
        .tab-content.active { display: block; }

        .session-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
        .session-item { padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; transition: 0.2s; display: flex; justify-content: space-between; align-items: center; }
        .session-item.active { border-color: var(--accent); background: #1c211f; }
        .session-item:hover { border-color: var(--border-focus); }
        .session-title { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .session-actions { display: flex; gap: 4px; opacity: 0; transition: 0.2s; }
        .session-item:hover .session-actions { opacity: 1; }
        .sess-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 12px; padding: 2px; }
        .sess-btn:hover { color: var(--text); }
        .new-sess-btn { width: 100%; padding: 10px; background: var(--surface-hover); border: 1px dashed var(--border-focus); color: var(--text); border-radius: var(--radius-sm); cursor: pointer; font-size: 13px; transition: 0.2s; }
        .new-sess-btn:hover { background: var(--border); border-style: solid; }

        .filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
        .filter-btn { flex: 1; padding: 6px; background: var(--bg); border: 1px solid var(--border); color: var(--text-muted); border-radius: var(--radius-sm); cursor: pointer; font-size: 12px; transition: 0.2s; }
        .filter-btn.active { background: var(--surface-hover); color: var(--text); border-color: var(--accent); }
        .filter-btn:hover { border-color: var(--border-focus); }

        .key-input-group { display: flex; gap: 8px; margin-bottom: 15px; }
        .key-input-group input { flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 10px 12px; border-radius: var(--radius-sm); outline: none; }
        .key-input-group input:focus { border-color: var(--accent); }
        .key-input-group button { background: var(--text); color: var(--bg); border: none; padding: 0 16px; border-radius: var(--radius-sm); cursor: pointer; font-weight: 600; }
        .key-item { background: var(--bg); padding: 12px; border-radius: var(--radius-md); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; border: 1px solid var(--border); gap: 10px;}
        .key-item-str { color: var(--text-muted); font-family: monospace; word-break: break-all; flex: 1; font-size: 12px; }

        .history-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .history-item { aspect-ratio: 1; background: var(--bg); border-radius: var(--radius-md); overflow: hidden; position: relative; border: 1px solid transparent; transition: 0.2s; }
        .history-item:hover { border-color: var(--border-focus); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .history-item img { width: 100%; height: 100%; object-fit: cover; display: block; cursor: pointer; }
        .history-item .tag { position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.8); font-size: 10px; padding: 3px 6px; border-radius: 4px; }
        .history-item .hist-actions { position: absolute; top: 0; left: 0; right: 0; display: flex; justify-content: space-between; padding: 4px; opacity: 0; transition: 0.2s; }
        .history-item:hover .hist-actions { opacity: 1; }
        .hist-act-btn { width: 24px; height: 24px; border-radius: 50%; border: none; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .hist-use-btn { background: rgba(16,185,129,0.85); color: #fff; }
        .hist-del-btn { background: rgba(239,68,68,0.85); color: #fff; }

        .workspace { flex: 1; display: flex; flex-direction: column; position: relative; background: var(--bg); }
        .header-bar { padding: 15px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 15px; background: rgba(9,9,11,0.85); backdrop-filter: blur(10px); z-index: 50; position: absolute; width: 100%; }
        .icon-btn-header { background: transparent; border: none; color: var(--text); cursor: pointer; font-size: 18px; padding: 5px; border-radius: var(--radius-sm); }
        .icon-btn-header:hover { background: var(--surface); }

        .feed-container { flex: 1; overflow-y: auto; padding: 75px 20px 280px 20px; display: flex; flex-direction: column; gap: 30px; scroll-behavior: smooth; }
        .feed-placeholder { margin: auto; color: var(--border); font-size: 20px; font-weight: 600; letter-spacing: 1px; }

        .chat-card { display: flex; flex-direction: column; gap: 12px; max-width: 900px; margin: 10px auto; width: 100%; animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); position: relative; }
        
        .card-top-actions { position: absolute; top: 12px; right: 12px; display: flex; gap: 8px; opacity: 0; transition: 0.2s; z-index: 10; }
        .chat-card:hover .card-top-actions { opacity: 1; }
        .card-icon-btn { width: 32px; height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: rgba(24,24,27,0.75); color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(6px); transition: 0.2s; }
        .card-icon-btn:hover { background: var(--surface-hover); color: var(--text); border-color: var(--border-focus); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .card-icon-btn.del-btn:hover { color: #ef4444; border-color: rgba(239,68,68,0.5); background: rgba(239,68,68,0.15); }
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        .card-header { display: flex; gap: 12px; align-items: flex-start; }
        .avatar { width: 36px; height: 36px; background: var(--surface); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; border: 1px solid var(--border); flex-shrink: 0; overflow: hidden; }
        .prompt-box { background: var(--surface); padding: 14px 18px; border-radius: 0 16px 16px 16px; font-size: 14px; line-height: 1.6; border: 1px solid var(--border); width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column;}
        .card-attachments { display: flex; gap: 8px; margin-top: 10px; overflow-x: auto; padding-bottom: 5px; }
        .card-attachments img { height: 48px; width: 48px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--border); cursor: pointer; }
        
        .param-tags { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; width: 100%; align-items: center; }
        .param-tag { background: var(--bg); color: var(--text-muted); font-size: 11px; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--border); }
        
        .card-content { margin-left: 48px; }

        .result-grid { display: flex; flex-wrap: wrap; gap: 15px; }
        .img-slot { width: 200px; height: 200px; border-radius: var(--radius-lg); overflow: hidden; border: 1px solid var(--border); background: var(--surface); flex-shrink: 0; position: relative; transition: 0.3s; }
        .img-slot:hover { border-color: var(--accent); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
        .img-slot img { width: 100%; height: 100%; object-fit: cover; display: block; cursor: pointer; }
        
        .slot-time-badge { position: absolute; top: 6px; left: 6px; background: rgba(0,0,0,0.6); color: #fff; font-size: 11px; padding: 3px 6px; border-radius: 4px; backdrop-filter: blur(4px); z-index: 5; pointer-events: none; }
        
        /* 悬浮显示的卡片左下角 Key 徽章 */
        .slot-key-badge { position: absolute; bottom: 5px; left: 5px; height: 30px; display: flex; align-items: center; background: rgba(0,0,0,0.75); font-size: 11px; padding: 0 8px; border-radius: var(--radius-sm); backdrop-filter: blur(4px); z-index: 5; font-family: monospace; border: 1px solid rgba(255,255,255,0.15); opacity: 0; transition: 0.2s; white-space: nowrap; pointer-events: none; }
        .img-slot:hover .slot-key-badge { opacity: 1; }

        .img-slot .lp-inner { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
        .img-slot .lp-particles { position: absolute; inset: 0; }
        .img-slot .lp-particle { position: absolute; border-radius: 50%; opacity: 0; animation: particleGather 2.5s ease-in-out infinite; }
        .img-slot .lp-center-glow { width: 60px; height: 60px; border-radius: 50%; background: radial-gradient(circle, rgba(16,185,129,0.3) 0%, transparent 70%); animation: pulseGlow 2s ease-in-out infinite; z-index: 2; }
        .img-slot .lp-text { position: absolute; bottom: 16px; left: 0; right: 0; text-align: center; font-size: 11px; color: var(--text-muted); z-index: 3; }
        .img-slot .lp-ring { position: absolute; width: 80px; height: 80px; border: 2px solid transparent; border-top-color: var(--accent); border-radius: 50%; animation: spin 1.2s linear infinite; z-index: 2; opacity: 0.5; }
        .img-slot .slot-dl-btn { position: absolute; bottom: 5px; right: 5px; width: 30px; height: 30px; border-radius: var(--radius-sm); background: rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.15); color: #fff; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0; transition: 0.2s; backdrop-filter: blur(4px); z-index: 5; }
        .img-slot:hover .slot-dl-btn { opacity: 1; }
        .img-slot .slot-dl-btn:hover { background: rgba(16,185,129,0.8); border-color: var(--accent); transform: scale(1.1); }
        .img-slot .slot-err { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #ef4444; font-size: 12px; text-align: center; padding: 20px; line-height: 1.4; }

        @keyframes particleGather { 0% { transform: translate(var(--sx), var(--sy)) scale(0.3); opacity: 0; } 40% { opacity: 0.8; } 70% { transform: translate(0, 0) scale(1); opacity: 0.6; } 85% { transform: translate(0, 0) scale(0.5); opacity: 0.3; } 100% { transform: translate(var(--sx), var(--sy)) scale(0.3); opacity: 0; } }
        @keyframes pulseGlow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 0.9; } }

        .err-text { color: #ef4444; font-size: 13px; margin-top: 10px; display: inline-block; }

        .bottom-console-wrapper { position: absolute; bottom: 0; left: 0; width: 100%; padding: 25px 20px; background: linear-gradient(transparent, var(--bg) 90%); display: flex; justify-content: center; z-index: 20; pointer-events: none; }
        .input-console { pointer-events: auto; width: 100%; max-width: 700px; background: rgba(25, 25, 25, 0.75); backdrop-filter: blur(10px);border: 1px solid var(--border); border-radius: 20px; box-shadow: 0 12px 40px rgba(0,0,0,0.8); display: flex; flex-direction: column; padding: 14px 18px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .input-console.drag-active { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(16,185,129,0.15), 0 12px 40px rgba(0,0,0,0.8); background: #1c211f; transform: translateY(-2px); }
        .input-console:focus-within { border-color: var(--border-focus); box-shadow: 0 8px 30px rgba(0,0,0,0.8); }

        .attachments-queue { display: flex; gap: 10px; overflow-x: auto; margin-bottom: 8px; padding-bottom: 4px; }
        .attachments-queue:empty { display: none; }
        .attachment-item { position: relative; width: 64px; height: 64px; border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--border); flex-shrink: 0; animation: scaleIn 0.2s; }
        @keyframes scaleIn { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .attachment-item img { width: 100%; height: 100%; object-fit: cover; display: block; cursor: pointer; }
        .attachment-item .overlay-delete { position: absolute; inset: 0; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.2s; cursor: pointer; color: white; font-size: 16px; }
        .attachment-item:hover .overlay-delete { opacity: 1; }
        .attachment-item .upload-spinner { position: absolute; inset: 0; background: rgba(0,0,0,0.6); display: flex; justify-content: center; align-items: center; }

        textarea { background: transparent; border: none; color: var(--text); font-size: 15px; resize: none; outline: none; width: 100%; max-height: 250px; min-height: 80px; padding: 10px 0; line-height: 1.6; }
        textarea::placeholder { color: var(--border-focus); }
        .toolbar { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; gap: 10px; flex-wrap: wrap; }
        .tools-left { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

        .custom-select { position: relative; user-select: none; font-size: 13px; }
        .cs-selected { background: var(--bg); border: 1px solid var(--border); padding: 8px 14px; border-radius: 20px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: 0.2s; color: var(--text-muted); font-weight: 500; white-space: nowrap; }
        .cs-selected:hover { background: var(--surface-hover); color: var(--text); border-color: var(--border-focus); }
        .cs-selected::after { content: "▼"; font-size: 10px; color: var(--border-focus); transition: 0.2s; }
        .custom-select.open .cs-selected { border-color: var(--border-focus); color: var(--text); }
        .custom-select.open .cs-selected::after { transform: rotate(180deg); }
        .cs-options { position: absolute; bottom: calc(100% + 8px); left: 0; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: 0 10px 30px rgba(0,0,0,0.9); width: max-content; min-width: 100%; opacity: 0; visibility: hidden; transform: translateY(10px); transition: 0.2s cubic-bezier(0.16, 1, 0.3, 1); z-index: 100; overflow: hidden; padding: 4px; }
        .custom-select.open .cs-options { opacity: 1; visibility: visible; transform: translateY(0); }
        .cs-opt { padding: 8px 16px; cursor: pointer; border-radius: var(--radius-sm); transition: 0.1s; color: var(--text); white-space: nowrap; }
        .cs-opt:hover { background: var(--bg); }
        .cs-opt.active { background: var(--border); font-weight: bold; }

        .icon-btn { display: flex; align-items: center; justify-content: center; padding: 8px; border-radius: 50%; width: 36px; height: 36px; border: 1px solid transparent; background: transparent; color: var(--text-muted); cursor: pointer; transition: 0.2s; }
        .icon-btn:hover { background: var(--bg); color: var(--text); border-color: var(--border); }
        .generate-btn { background: var(--text); color: var(--bg); border: none; padding: 10px 24px; border-radius: 24px; font-weight: 600; font-size: 14px; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 12px rgba(255,255,255,0.1); display: flex; gap: 5px; align-items: center; }
        .generate-btn:hover { transform: scale(1.03); box-shadow: 0 6px 16px rgba(255,255,255,0.2); }
        .generate-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .spinner-small { width: 18px; height: 18px; border: 2px solid rgba(16,185,129,0.2); border-top: 2px solid var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }

        .lightbox-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 9999; display: none; flex-direction: column; align-items: center; justify-content: center; cursor: zoom-out; animation: lbFadeIn 0.2s; }
        .lightbox-overlay.active { display: flex; }
        @keyframes lbFadeIn { from { opacity: 0; } to { opacity: 1; } }
        .lightbox-overlay img { max-width: 92vw; max-height: 80vh; object-fit: contain; border-radius: 8px; box-shadow: 0 0 60px rgba(0,0,0,0.8); cursor: default; }
        .lightbox-url { margin-top: 12px; font-size: 11px; color: rgba(255,255,255,0.4); max-width: 90vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; user-select: all; cursor: text; }
        
        /* 全新的极简 Lightbox Key 信息药丸设计 */
        .lightbox-key { margin-top: 10px; font-size: 13px; display: none; align-items: center; gap: 14px; background: rgba(24,24,27,0.85); padding: 8px 16px; border-radius: var(--radius-sm); border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.5); backdrop-filter: blur(4px); }
        
        .lightbox-close { position: absolute; top: 20px; right: 28px; background: none; border: none; color: #fff; font-size: 32px; cursor: pointer; opacity: 0.7; transition: 0.2s; }
        .lightbox-close:hover { opacity: 1; transform: scale(1.1); }

        .scroll-top-btn { position: fixed; bottom: 24px; right: 24px; width: 40px; height: 40px; border-radius: var(--radius-sm); background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); font-size: 18px; cursor: pointer; z-index: 35; display: none; align-items: center; justify-content: center; transition: 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .scroll-top-btn:hover { background: var(--surface-hover); color: var(--text); border-color: var(--border-focus); transform: translateY(-2px); }
        .scroll-top-btn.visible { display: flex; }
        
        #promptInput:focus { border-color: var(--accent) !important; }
    </style>
</head>
<body>

<div id="confirmModal" class="lightbox-overlay" style="z-index: 10000; display: none; align-items: center; justify-content: center; cursor: default;">
    <div style="background: var(--surface); padding: 24px; border-radius: var(--radius-md); border: 1px solid var(--border); width: 320px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
        <div id="confirmTitle" style="font-size: 16px; font-weight: 600; margin-bottom: 12px; color: var(--text);">确定要删除此记录吗？</div>
        <div id="confirmMsg" style="font-size: 13px; color: var(--text-muted); margin-bottom: 24px;">删除后数据将无法恢复</div>
        <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="confirmCancelBtn" style="flex: 1; padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer; transition: 0.2s;">取消</button>
            <button id="confirmOkBtn" style="flex: 1; padding: 10px; border-radius: var(--radius-sm); border: none; background: #ef4444; color: #fff; cursor: pointer; font-weight: 600; transition: 0.2s;">确定删除</button>
        </div>
    </div>
</div>

<div id="promptModal" class="lightbox-overlay" style="z-index: 10000; display: none; align-items: center; justify-content: center; cursor: default;">
    <div style="background: var(--surface); padding: 24px; border-radius: var(--radius-md); border: 1px solid var(--border); width: 320px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
        <div id="promptTitle" style="font-size: 16px; font-weight: 600; margin-bottom: 16px; color: var(--text);">重命名</div>
        <input type="text" id="promptInput" style="width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 10px 12px; border-radius: var(--radius-sm); outline: none; margin-bottom: 24px; box-sizing: border-box; font-size: 14px;" autocomplete="off">
        <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="promptCancelBtn" style="flex: 1; padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer; transition: 0.2s;">取消</button>
            <button id="promptOkBtn" style="flex: 1; padding: 10px; border-radius: var(--radius-sm); border: none; background: var(--accent); color: #fff; cursor: pointer; font-weight: 600; transition: 0.2s;">确定 (Enter)</button>
        </div>
    </div>
</div>

<div class="lightbox-overlay" id="lightbox" onclick="closeLightbox()">
    <button class="lightbox-close" onclick="closeLightbox()">✕</button>
    <img id="lightboxImg" src="" onclick="event.stopPropagation()">
    <div class="lightbox-url" id="lightboxUrl" onclick="event.stopPropagation()"></div>
    <div class="lightbox-key" id="lightboxKey" onclick="event.stopPropagation()"></div>
</div>

<button class="scroll-top-btn" id="scrollTopBtn" onclick="scrollToTop()" title="回到顶部"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAyklEQVR4nO3WSwrCMBAG4DmOC13Zpe4t3rH5p92YiaeqotRLKFGUIrVJa2pRMzA0JAMfQx6UKMbfhVKyZpY9s5xDJKB3gEmdsC0MhdaydMIDoNekCH8VDOgKkDmzSez4U/Apy2R2r1dqOwH0YVAY0FWeb6a2zn7rY1fn9Ab86NR2ySzH57m2zqkn3IQ2rr3CqQfchnrj1BW2p9dnH+v7b097iI4XvtfmVmOSojDLQe4xj/WAcIQ5wtIdxli/PoBJA+OlUrJywjF+Li4Ur0SlSNbYGwAAAABJRU5ErkJggg==" alt="up-squared" style="width: 20px;height: 20px;"></button>

<aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <span>⚙️ 控制中心</span>
        <button class="icon-btn" style="width:28px; height:28px; font-size:12px;" onclick="toggleSidebar()">✕</button>
    </div>
    <div class="tab-nav">
        <button class="tab-btn active" onclick="switchTab('sessions')">对话</button>
        <button class="tab-btn" onclick="switchTab('history')">图库</button>
        <button class="tab-btn" onclick="switchTab('keys')">Api Key池</button>
    </div>
    <div class="tab-content active" id="tab-sessions">
        <button class="new-sess-btn" onclick="createNewSession()">＋ 新建对话</button>
        <div class="session-list" id="sessionList"></div>
    </div>
    <div class="tab-content" id="tab-history">
        <div class="filter-bar">
            <button class="filter-btn active" onclick="setGalleryFilter('all')">全部</button>
            <button class="filter-btn" onclick="setGalleryFilter('upload')">上传</button>
            <button class="filter-btn" onclick="setGalleryFilter('generate')">生成</button>
        </div>
        <div class="history-grid" id="historyGrid"></div>
    </div>
    <div class="tab-content" id="tab-keys">
        <div class="key-input-group">
            <input type="text" id="newKey" placeholder="输入新的 Key">
            <button onclick="addKey()">添加</button>
        </div>
        <div id="keyList"></div>
    </div>
</aside>

<main class="workspace">
    <div class="header-bar">
        <button class="icon-btn-header" onclick="toggleSidebar()">☰</button>
        <span style="font-weight: 600; font-size:16px;">Image Studio WebUI</span>
    </div>

    <div class="feed-container" id="chatFeed">
        <div class="feed-placeholder" id="emptyState"></div>
    </div>

    <div class="bottom-console-wrapper">
        <div class="input-console" id="dropzone">
            <div class="attachments-queue" id="attachmentsQueue"></div>
            <textarea id="prompt" rows="1" placeholder="描述你想生成的画面... (Ctrl+Enter 生成 / 可拖拽或Ctrl+V粘贴图片)"></textarea>
            <div class="toolbar">
                <div class="tools-left">
                    <input type="file" id="fileInput" accept="image/*" multiple onchange="handleFileSelect(event)" style="display:none;">
                    <button class="icon-btn" onclick="document.getElementById('fileInput').click()" title="上传参考图">📎</button>
                    <div class="custom-select" id="sel-model" data-value="">
                        <div class="cs-selected">选择模型</div>
                        <div class="cs-options" id="opt-model"></div>
                    </div>
                    <div class="custom-select" id="sel-size" data-value="">
                        <div class="cs-selected">尺寸</div>
                        <div class="cs-options" id="opt-size"></div>
                    </div>
                    <div class="custom-select" id="sel-ratio" data-value="">
                        <div class="cs-selected">比例</div>
                        <div class="cs-options" id="opt-ratio"></div>
                    </div>
                    <div class="custom-select" id="sel-n" data-value="">
                        <div class="cs-selected">数量</div>
                        <div class="cs-options" id="opt-n"></div>
                    </div>
                </div>
                <button class="generate-btn" id="generateBtn" onclick="submitTask()">
                    ✨ 生成 (<span id="costDisplay">0</span>点)
                </button>
            </div>
        </div>
    </div>
</main>

<script>
    let MODEL_COSTS = {};
    let MODEL_NAMES = {};
    let attachedUrls = [];
    
    // Sessions State
    let sessionsData = [];
    let currentSessionId = null;
    const activePolls = new Set(); 
    
    // Gallery State
    let cachedGalleryData = [];
    let currentGalleryFilter = 'all';

    const RATIO_OPTIONS = [
        {val:'1:1',label:'1:1'},{val:'3:4',label:'3:4'},{val:'4:3',label:'4:3'},
        {val:'9:16',label:'9:16'},{val:'16:9',label:'16:9'}
    ];
    const N_OPTIONS = [
        {val:'1',label:'1 张'},{val:'2',label:'2 张'},{val:'3',label:'3 张'},{val:'4',label:'4 张'}
    ];

    window.onload = async () => {
        initTextarea();
        initDropzone();
        initPasteHandler();
        await loadConfig();
        buildAllSelects();
        bindAllSelectEvents();
        restoreSidebar();
        updateCostUI();
        await loadSessionsList();
        loadGallery();
        loadKeys();
        initScrollTopBtn();
    };

    // 强力击穿浏览器缓存机制
    const fetchApi = async (url, options = {}) => {
        const separator = url.includes('?') ? '&' : '?';
        const finalUrl = `${url}${separator}t=${Date.now()}`;
        return fetch(finalUrl, options);
    };

    async function loadConfig() {
        try {
            const res = await fetchApi('/api/ui_config');
            const cfg = await res.json();
            MODEL_COSTS = cfg.model_costs || {};
            MODEL_NAMES = cfg.model_names || {};
        } catch(e) { console.error('Config load failed', e); }
    }

    function getSavedSettings() {
        try { const r = localStorage.getItem('ai_studio_settings'); return r ? JSON.parse(r) : {}; }
        catch(e) { return {}; }
    }
    function saveSettings() {
        localStorage.setItem('ai_studio_settings', JSON.stringify({
            model: document.getElementById('sel-model').dataset.value,
            size:  document.getElementById('sel-size').dataset.value,
            ratio: document.getElementById('sel-ratio').dataset.value,
            n:     document.getElementById('sel-n').dataset.value
        }));
    }

    function buildAllSelects() {
        const saved = getSavedSettings();
        const models = Object.keys(MODEL_COSTS);
        if (!models.length) return;
        const savedModel = (saved.model && MODEL_COSTS[saved.model]) ? saved.model : models[0];
        fillSelect('sel-model', 'opt-model', models.map(m => ({val:m, label:MODEL_NAMES[m]||m})), savedModel);
        const sizes = Object.keys(MODEL_COSTS[savedModel] || {});
        const savedSize = (saved.size && sizes.includes(saved.size)) ? saved.size : (sizes.includes('2k') ? '2k' : sizes[0]);
        fillSelect('sel-size', 'opt-size', sizes.map(s => ({val:s, label:s})), savedSize);
        const savedRatio = (saved.ratio && RATIO_OPTIONS.some(r => r.val === saved.ratio)) ? saved.ratio : '16:9';
        fillSelect('sel-ratio', 'opt-ratio', RATIO_OPTIONS, savedRatio);
        const savedN = (saved.n && N_OPTIONS.some(o => o.val === saved.n)) ? saved.n : '1';
        fillSelect('sel-n', 'opt-n', N_OPTIONS, savedN);
    }
    function fillSelect(selectId, optContainerId, options, activeVal) {
        const el = document.getElementById(selectId);
        const container = document.getElementById(optContainerId);
        let activeLabel = '';
        container.innerHTML = options.map(o => {
            const isActive = o.val === activeVal;
            if (isActive) activeLabel = o.label;
            return '<div class="cs-opt' + (isActive ? ' active' : '') + '" data-val="' + o.val + '">' + o.label + '</div>';
        }).join('');
        el.dataset.value = activeVal;
        el.querySelector('.cs-selected').innerText = activeLabel || activeVal;
    }
    function rebuildSizeSelect(model, preferredSize) {
        const costs = MODEL_COSTS[model];
        if (!costs) return;
        const sizes = Object.keys(costs);
        const actual = (preferredSize && sizes.includes(preferredSize)) ? preferredSize : (sizes.includes('2k') ? '2k' : sizes[0]);
        fillSelect('sel-size', 'opt-size', sizes.map(s => ({val:s, label:s})), actual);
    }
    function rebuildAllSelectsWithValues(modelId, size, ratio, n) {
        const models = Object.keys(MODEL_COSTS);
        if (!models.length) return;
        const targetModel = (modelId && MODEL_COSTS[modelId]) ? modelId : models[0];
        fillSelect('sel-model', 'opt-model', models.map(m => ({val:m, label:MODEL_NAMES[m]||m})), targetModel);
        rebuildSizeSelect(targetModel, size || '');
        fillSelect('sel-ratio', 'opt-ratio', RATIO_OPTIONS, RATIO_OPTIONS.some(r => r.val === ratio) ? ratio : '16:9');
        fillSelect('sel-n', 'opt-n', N_OPTIONS, N_OPTIONS.some(o => o.val === String(n)) ? String(n) : '1');
    }

    function bindAllSelectEvents() {
        document.addEventListener('click', () => { document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open')); });
        document.querySelectorAll('.custom-select').forEach(el => {
            el.querySelector('.cs-selected').addEventListener('click', function(e) {
                e.stopPropagation();
                const wasOpen = el.classList.contains('open');
                document.querySelectorAll('.custom-select').forEach(x => x.classList.remove('open'));
                if (!wasOpen) el.classList.add('open');
            });
            el.querySelector('.cs-options').addEventListener('click', function(e) {
                const opt = e.target.closest('.cs-opt');
                if (!opt) return;
                e.stopPropagation();
                this.querySelectorAll('.cs-opt').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
                el.querySelector('.cs-selected').innerText = opt.innerText;
                el.dataset.value = opt.dataset.val;
                el.classList.remove('open');
                if (el.id === 'sel-model') rebuildSizeSelect(opt.dataset.val, getSavedSettings().size || '');
                updateCostUI(); saveSettings();
            });
        });
    }
    function updateCostUI() {
        const model = document.getElementById('sel-model').dataset.value;
        const size = document.getElementById('sel-size').dataset.value;
        const n = document.getElementById('sel-n').dataset.value;
        const costs = MODEL_COSTS[model];
        document.getElementById('costDisplay').innerText = costs ? ((costs[size]||0) * parseInt(n||1)) : '?';
    }

    function toggleSidebar() {
        const sb = document.getElementById('sidebar');
        sb.classList.toggle('collapsed');
        localStorage.setItem('ai_sidebar', sb.classList.contains('collapsed') ? 'collapsed' : 'open');
    }
    function restoreSidebar() { if (localStorage.getItem('ai_sidebar') === 'collapsed') document.getElementById('sidebar').classList.add('collapsed'); }
    function switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.querySelector('.tab-btn[onclick="switchTab(\''+tabId+'\')"]').classList.add('active');
        document.getElementById('tab-'+tabId).classList.add('active');
    }
    function initTextarea() {
        const tx = document.getElementById('prompt');
        tx.addEventListener('input', function() { this.style.height='auto'; this.style.height=this.scrollHeight+'px'; });
        tx.addEventListener('keydown', function(e) { if (e.key==='Enter' && e.ctrlKey) { e.preventDefault(); submitTask(); } });
    }
    function initPasteHandler() {
        document.addEventListener('paste', function(e) {
            const items = e.clipboardData && e.clipboardData.items;
            if (!items) return;
            const imgs = [];
            for (let i=0; i<items.length; i++) { if (items[i].type.startsWith('image/')) { const f=items[i].getAsFile(); if(f) imgs.push(f); } }
            if (imgs.length) { e.preventDefault(); handleFiles(imgs); }
        });
    }

    function openLightbox(src, keyStr, cost, remain) { 
        document.getElementById('lightboxImg').src = src; 
        document.getElementById('lightboxUrl').innerText = src; 
        
        const keyInfoEl = document.getElementById('lightboxKey');
        if (keyStr) {
            const cNum = parseInt(cost) || 0;
            const rNum = parseInt(remain) || 0;
            const costHtml = cNum > 0 ? `<span style="color: #ef4444; font-weight: 600;">-${cNum}</span>` : '';
            const remainHtml = `<span style="color: var(--accent); font-weight: 600;">${rNum}</span>`;

            keyInfoEl.innerHTML = `<span style="color: #a1a1aa; font-family: monospace; user-select: all; cursor: text;">${escHtml(keyStr)}</span>` +
                                  (costHtml ? `<span>${costHtml}</span>` : '') +
                                  `<span>${remainHtml}</span>`;
            keyInfoEl.style.display = 'flex';
        } else {
            keyInfoEl.style.display = 'none';
        }
        
        document.getElementById('lightbox').classList.add('active'); 
    }
    
    function closeLightbox() { document.getElementById('lightbox').classList.remove('active'); }

    // ====== 统一弹窗与事件管理 ======
    let pendingConfirmAction = null;
    function showConfirm(title, message, actionFn) {
        document.getElementById('confirmTitle').innerText = title;
        document.getElementById('confirmMsg').innerText = message;
        pendingConfirmAction = actionFn;
        document.getElementById('confirmModal').style.display = 'flex';
        document.getElementById('confirmOkBtn').focus();
    }
    function closeConfirm() {
        pendingConfirmAction = null;
        document.getElementById('confirmModal').style.display = 'none';
    }
    document.getElementById('confirmCancelBtn').addEventListener('click', closeConfirm);
    document.getElementById('confirmOkBtn').addEventListener('click', () => {
        if(pendingConfirmAction) pendingConfirmAction();
        closeConfirm();
    });

    let pendingPromptAction = null;
    function showCustomPrompt(title, defaultVal, actionFn) {
        document.getElementById('promptTitle').innerText = title;
        const input = document.getElementById('promptInput');
        input.value = defaultVal;
        pendingPromptAction = actionFn;
        document.getElementById('promptModal').style.display = 'flex';
        input.focus();
        input.select();
    }
    function closePrompt() {
        pendingPromptAction = null;
        document.getElementById('promptModal').style.display = 'none';
    }
    document.getElementById('promptCancelBtn').addEventListener('click', closePrompt);
    document.getElementById('promptOkBtn').addEventListener('click', () => {
        const val = document.getElementById('promptInput').value;
        if(pendingPromptAction) pendingPromptAction(val);
        closePrompt();
    });
    
    document.addEventListener('keydown', e => {
        const confirmModal = document.getElementById('confirmModal');
        const promptModal = document.getElementById('promptModal');
        
        if (confirmModal && confirmModal.style.display === 'flex') {
            if (e.key === 'Enter') {
                e.preventDefault();
                if(pendingConfirmAction) pendingConfirmAction();
                closeConfirm();
            } else if (e.key === 'Escape') {
                closeConfirm();
            }
        } else if (promptModal && promptModal.style.display === 'flex') {
            if (e.key === 'Enter') {
                e.preventDefault();
                const val = document.getElementById('promptInput').value;
                if(pendingPromptAction) pendingPromptAction(val);
                closePrompt();
            } else if (e.key === 'Escape') {
                closePrompt();
            }
        } else if (e.key === 'Escape') {
            closeLightbox();
        }
    });

    function confirmDeleteCard(cid) {
        showConfirm("确定要删除此记录吗？", "删除后数据将无法恢复", () => deleteChatCard(cid));
    }

    function scrollFeedToBottom() { const f=document.getElementById('chatFeed'); f.scrollTop=f.scrollHeight; }
    function scrollToTop() { document.getElementById('chatFeed').scrollTo({top:0,behavior:'smooth'}); }
    function initScrollTopBtn() {
        const feed=document.getElementById('chatFeed'), btn=document.getElementById('scrollTopBtn');
        feed.addEventListener('scroll', function() { if(feed.scrollTop>400) btn.classList.add('visible'); else btn.classList.remove('visible'); });
    }

    // ====== 会话(Session)与轮询(Polling)功能 ======
    async function loadSessionsList() {
        try {
            const res = await fetchApi('/api/ui_sessions');
            sessionsData = await res.json();
            if (sessionsData.length === 0) {
                await createNewSession();
                return;
            }
            renderSessionsList();
            if (!currentSessionId || !sessionsData.find(s => s.id === currentSessionId)) {
                selectSession(sessionsData[0].id);
            } else {
                selectSession(currentSessionId);
            }
            
            sessionsData.forEach(sess => {
                sess.messages.forEach(msg => {
                    if (msg.status === 'generating') {
                        startPolling(sess.id, msg.id);
                    }
                });
            });

        } catch(e) { console.error('Failed to load sessions', e); }
    }

    function renderSessionsList() {
        const list = document.getElementById('sessionList');
        list.innerHTML = sessionsData.map(s => `
            <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" onclick="selectSession('${s.id}')">
                <div class="session-title" title="${escHtml(s.title)}">${escHtml(s.title)}</div>
                <div class="session-actions" onclick="event.stopPropagation()">
                    <button class="sess-btn" onclick="renameSession('${s.id}')" title="重命名">✏️</button>
                    <button class="sess-btn" onclick="deleteSession('${s.id}')" title="删除">🗑️</button>
                </div>
            </div>
        `).join('');
    }

    async function createNewSession() {
        try {
            const res = await fetchApi('/api/ui_sessions', { method: 'POST', body: JSON.stringify({action: 'create'})});
            const newSess = await res.json();
            sessionsData.unshift(newSess);
            renderSessionsList();
            selectSession(newSess.id);
        } catch(e) { console.error('Create session failed', e); }
    }

    function renameSession(id) {
        const sess = sessionsData.find(s => s.id === id);
        if(!sess) return;
        showCustomPrompt('请输入新的对话名称：', sess.title, async (newName) => {
            if (newName && newName.trim()) {
                sess.title = newName.trim();
                renderSessionsList();
                await fetchApi('/api/ui_sessions', { method: 'POST', body: JSON.stringify({action: 'rename', id, title: sess.title})});
            }
        });
    }

    function deleteSession(id) {
        showConfirm('确定要删除这个对话吗？', '历史记录将无法恢复', async () => {
            await fetchApi('/api/ui_sessions', { method: 'DELETE', body: JSON.stringify({id})});
            sessionsData = sessionsData.filter(s => s.id !== id);
            if (currentSessionId === id) currentSessionId = null;
            if (sessionsData.length === 0) {
                await createNewSession();
            } else {
                renderSessionsList();
                if(!currentSessionId) selectSession(sessionsData[0].id);
            }
        });
    }

    function selectSession(id) {
        currentSessionId = id;
        renderSessionsList();
        const sess = sessionsData.find(s => s.id === id);
        renderChatFeed(sess ? sess.messages : []);
        if(window.innerWidth <= 768) toggleSidebar();
    }

    function renderChatFeed(messages) {
        const feed = document.getElementById('chatFeed');
        feed.innerHTML = '';
        if (!messages || messages.length === 0) {
            feed.innerHTML = '<div class="feed-placeholder" id="emptyState"></div>';
            return;
        }
        messages.forEach(chat => {
            if (chat.status === 'generating') {
                renderPendingCard(chat);
            } else {
                let ci='';
                // 如果有URL或错误数组，则构建插槽网格，统一错误/成功的外观
                if((chat.urls && chat.urls.length > 0) || (chat.errors && chat.errors.length > 0)) {
                    ci=buildResultHTML(chat);
                } else {
                    const errStr = chat.error || '生成失败';
                    ci='<span class="err-text">'+escHtml(errStr)+'</span>';
                }
                feed.insertAdjacentHTML('beforeend', buildCardHTML(chat,ci));
            }
        });
        scrollFeedToBottom();
    }


    function initDropzone() {
        const dz=document.getElementById('dropzone'); let dc=0;
        dz.addEventListener('dragenter', e => { e.preventDefault(); dc++; dz.classList.add('drag-active'); });
        dz.addEventListener('dragover', e => e.preventDefault());
        dz.addEventListener('dragleave', e => { dc--; if(dc===0) dz.classList.remove('drag-active'); });
        dz.addEventListener('drop', e => { e.preventDefault(); dc=0; dz.classList.remove('drag-active'); if(e.dataTransfer.files.length) handleFiles(e.dataTransfer.files); });
    }
    function handleFileSelect(e) { if(e.target.files.length) handleFiles(e.target.files); e.target.value=''; }
    async function handleFiles(files) { const v=Array.from(files).filter(f=>f.type.startsWith('image/')); if(!v.length) return; await Promise.all(v.map(f=>uploadSingleFile(f))); loadGallery(); }
    async function uploadSingleFile(file) {
        return new Promise(resolve => {
            const reader=new FileReader(); const id='att_'+Date.now()+Math.floor(Math.random()*9000);
            document.getElementById('attachmentsQueue').insertAdjacentHTML('beforeend','<div class="attachment-item" id="'+id+'"><div class="upload-spinner"><div class="spinner-small"></div></div></div>');
            reader.onload = async e => {
                const b64=e.target.result.split(',')[1];
                try { const r=await fetchApi('/api/ui_upload',{method:'POST',body:JSON.stringify({image_base64:b64})}); const d=await r.json(); let url=d.url; if(!url&&d.extracted_urls&&d.extracted_urls.length) url=d.extracted_urls[0]; if(r.status===200&&url&&url.startsWith('http')){attachedUrls.push(url);renderAttachmentItem(id,url);} else document.getElementById(id)?.remove(); } catch(err){document.getElementById(id)?.remove();}
                resolve();
            }; reader.readAsDataURL(file);
        });
    }
    function renderAttachmentItem(domId,url) { const el=document.getElementById(domId); if(!el)return; const su=url.replace(/'/g,"\\'"); el.innerHTML='<img src="'+url+'" onclick="event.stopPropagation();openLightbox(\''+su+'\')"><div class="overlay-delete" onclick="removeAttachment(\''+su+"','"+domId+'\')">✕</div>'; }
    function removeAttachment(url,domId) { attachedUrls=attachedUrls.filter(u=>u!==url); document.getElementById(domId)?.remove(); }
    function appendToAttachments(url) { if(attachedUrls.includes(url))return; attachedUrls.push(url); const id='att_'+Date.now()+Math.floor(Math.random()*9000); const su=url.replace(/'/g,"\\'"); document.getElementById('attachmentsQueue').insertAdjacentHTML('beforeend','<div class="attachment-item" id="'+id+'"><img src="'+url+'" onclick="event.stopPropagation();openLightbox(\''+su+'\')"><div class="overlay-delete" onclick="removeAttachment(\''+su+"','"+id+'\')">✕</div></div>'); }
    function clearAllAttachments() { attachedUrls=[]; document.getElementById('attachmentsQueue').innerHTML=''; }
    function downloadImage(url,filename) { fetch(url).then(r=>r.blob()).then(blob=>{ const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=filename||'image.jpg'; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(a.href); }).catch(()=>window.open(url)); }
    function escHtml(s) { const d=document.createElement('div'); d.innerText=s||''; return d.innerHTML; }

    function getKeyBadgeHTML(keyStr, costNum, remainNum) {
        if (!keyStr) return '';
        const shortKey = keyStr.length > 10 ? (keyStr.substring(0,4) + '...' + keyStr.substring(keyStr.length-4)) : keyStr;
        const costHtml = costNum > 0 ? `<span style="color: #ef4444; margin-left: 6px;">-${costNum}</span>` : '';
        const remainHtml = `<span style="color: var(--accent); margin-left: 6px;">${remainNum}</span>`;
        return `<div class="slot-key-badge" title="${escHtml(keyStr)}"><span style="color: #a1a1aa;">${escHtml(shortKey)}</span>${costHtml}${remainHtml}</div>`;
    }

    function buildSlotLoading(sid) {
        const colors=['#10b981','#34d399','#6ee7b7','#a7f3d0','#059669','#047857','#065f46'];
        let particles='';
        for(let p=0;p<18;p++){
            const sx=(Math.random()-0.5)*300,sy=(Math.random()-0.5)*300,sz=4+Math.random()*8;
            const delay=(Math.random()*2).toFixed(2),dur=(2+Math.random()*1.5).toFixed(2);
            const c=colors[Math.floor(Math.random()*colors.length)];
            particles+='<div class="lp-particle" style="left:calc(50% - '+(sz/2)+'px);top:calc(50% - '+(sz/2)+'px);width:'+sz+'px;height:'+sz+'px;background:'+c+';--sx:'+sx+'px;--sy:'+sy+'px;animation-delay:'+delay+'s;animation-duration:'+dur+'s;"></div>';
        }
        return '<div class="lp-inner"><div class="lp-particles">'+particles+'</div><div class="lp-ring"></div><div class="lp-center-glow"></div><div class="lp-text" id="timer_'+sid+'">0.0s</div></div>';
    }

    function renderSlotImage(slotId, url, timeTaken, keyStr, costNum, remainNum) {
        const el = document.getElementById(slotId);
        if (!el) return;
        const su = url.replace(/'/g, "\\'");
        const sk = (keyStr||'').replace(/'/g, "\\'");
        const fname = url.split('/').pop() || 'image.jpg';
        const timeBadge = timeTaken ? `<div class="slot-time-badge">${timeTaken}s</div>` : '';
        const keyBadge = getKeyBadgeHTML(keyStr, costNum, remainNum);
        
        el.innerHTML = '<img src="'+url+'" onclick="event.stopPropagation();openLightbox(\''+su+'\', \''+sk+'\', \''+(costNum||0)+'\', \''+(remainNum||0)+'\')">' +
            timeBadge + keyBadge +
            '<button class="slot-dl-btn" onclick="event.stopPropagation();downloadImage(\''+su+"','"+fname+'\')" title="下载"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAuklEQVR4nO2RsQ3CMBBFT8AwFFAlFWEAGIKwF2IwFLpQoDABVA8FGSmCIM7JmYL4VS7+v+ezRSKDBBgBe+BGd67Arp7lI86xY6OVjoGDK+U9Xm3rZhyBiX3BagGg6LttyxKFJhwEieJXPGYtgOznYumY/0gUM3RxBqRA1chXQAIsQ4oTl5k18o+zu1Aw8QWYt3SmwDmk+E2ukdZYiHH/mj7/W1MQI7E3ohCfAnhLjXhtLC+B1Vdx5O+4A/EyVeP3ljpBAAAAAElFTkSuQmCC" alt="downloads" style="width: 17px;height: 17px;"></button>';
    }
    
    function renderSlotError(slotId, msg, timeTaken, keyStr, costNum, remainNum) {
        const el = document.getElementById(slotId);
        if (!el) return;
        const timeBadge = timeTaken ? `<div class="slot-time-badge">${timeTaken}s</div>` : '';
        const keyBadge = getKeyBadgeHTML(keyStr, costNum, remainNum);
        el.innerHTML = timeBadge + keyBadge + '<div class="slot-err">'+escHtml(msg)+'</div>';
    }

    function buildResultHTML(chatObj) {
        const urls = chatObj.urls || [];
        const times = chatObj.times || [];
        const errors = chatObj.errors || [];
        const keys = chatObj.keys || [];
        const costs = chatObj.costs || [];
        const remains = chatObj.remains || [];
        const n = chatObj.payload.n || 1;
        let imgs = '';
        
        for(let i=0; i<n; i++) {
            const kBadge = getKeyBadgeHTML(keys[i], costs[i], remains[i]);
            const tBadge = times[i] ? `<div class="slot-time-badge">${times[i]}s</div>` : '';
            const sk = (keys[i]||'').replace(/'/g, "\\'");
            const cNum = costs[i] || 0;
            const rNum = remains[i] || 0;
            
            if (urls[i]) {
                const su = urls[i].replace(/'/g, "\\'");
                const fname = urls[i].split('/').pop() || ('image_'+i+'.jpg');
                imgs += '<div class="img-slot">' +
                    '<img src="'+urls[i]+'" loading="lazy" onclick="event.stopPropagation();openLightbox(\''+su+'\', \''+sk+'\', \''+cNum+'\', \''+rNum+'\')">' +
                    tBadge + kBadge +
                    '<button class="slot-dl-btn" onclick="event.stopPropagation();downloadImage(\''+su+"','"+fname+'\')" title="下载"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAuklEQVR4nO2RsQ3CMBBFT8AwFFAlFWEAGIKwF2IwFLpQoDABVA8FGSmCIM7JmYL4VS7+v+ezRSKDBBgBe+BGd67Arp7lI86xY6OVjoGDK+U9Xm3rZhyBiX3BagGg6LttyxKFJhwEieJXPGYtgOznYumY/0gUM3RxBqRA1chXQAIsQ4oTl5k18o+zu1Aw8QWYt3SmwDmk+E2ukdZYiHH/mj7/W1MQI7E3ohCfAnhLjXhtLC+B1Vdx5O+4A/EyVeP3ljpBAAAAAElFTkSuQmCC" alt="downloads" style="width: 17px;height: 17px;"></button></div>';
            } else if (errors[i]) {
                imgs += '<div class="img-slot">' + tBadge + kBadge + '<div class="slot-err">'+escHtml(errors[i])+'</div></div>';
            } else {
                imgs += '<div class="img-slot"><div class="slot-err">未知状态</div></div>';
            }
        }
        return '<div class="result-grid">'+imgs+'</div>';
    }

    function buildCardHTML(chatObj, contentInner) {
        const p = chatObj.payload || {};
        const safePayload = encodeURIComponent(JSON.stringify(p));
        const modelLabel = MODEL_NAMES[p.model_id] || p.model_id || '?';
        let attHtml = '';
        if(p.input_images && p.input_images.length){
            attHtml = '<div class="card-attachments">' + p.input_images.map(u => {
                const su = u.replace(/'/g, "\\'");
                return '<img src="'+u+'" onclick="openLightbox(\''+su+'\')">';
            }).join('') + '</div>';
        }
        const cid = chatObj.id || ('tmp_' + Date.now());

        const topActionsHtml = `
            <div class="card-top-actions">
                <button class="card-icon-btn" onclick="reuseParams('${safePayload}')" title="复用此参数">
                    <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                </button>
                <button class="card-icon-btn del-btn" onclick="confirmDeleteCard('${cid}')" title="删除记录">
                    <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>`;

        return '<div class="chat-card" id="'+cid+'">'+
            topActionsHtml +
            '<div class="card-header"><div class="avatar"><img style="width: 100%;height: 100%" src="__FAVICON_PLACEHOLDER__"/></div><div class="prompt-box" style="display:flex; flex-direction:column;">'+
            '<div style="font-size:15px; padding-top: 10px;">'+escHtml(p.prompt||'[以图生图模式]')+'</div>'+attHtml+
            '<div class="param-tags" id="tags_'+cid+'">'+
            '<span class="param-tag">'+escHtml(modelLabel)+'</span>'+
            '<span class="param-tag">'+escHtml(p.size||'')+'</span>'+
            '<span class="param-tag">'+escHtml(p.aspect_ratio||'')+'</span>'+
            '<span class="param-tag">'+(p.n||1)+'张</span>'+
            '</div></div></div>'+
            '<div class="card-content" id="content_'+cid+'">'+contentInner+'</div></div>';
    }

    function renderPendingCard(chatObj) {
        const n = chatObj.payload.n || 1;
        const urls = chatObj.urls || [];
        const errors = chatObj.errors || [];
        const times = chatObj.times || [];
        const keys = chatObj.keys || [];
        const costs = chatObj.costs || [];
        const remains = chatObj.remains || [];
        let slotsHtml = '<div class="result-grid" id="grid_'+chatObj.id+'">';
        
        for(let i=0; i<n; i++){
            const sid = chatObj.id + '_s' + i;
            const tBadge = times[i] ? `<div class="slot-time-badge">${times[i]}s</div>` : '';
            const kBadge = getKeyBadgeHTML(keys[i], costs[i], remains[i]);
            const sk = (keys[i]||'').replace(/'/g, "\\'");
            const cNum = costs[i] || 0;
            const rNum = remains[i] || 0;
            
            if (urls[i]) {
                const su = urls[i].replace(/'/g, "\\'");
                const fname = urls[i].split('/').pop() || ('image_'+i+'.jpg');
                slotsHtml += '<div class="img-slot" id="'+sid+'">' +
                    '<img src="'+urls[i]+'" loading="lazy" onclick="event.stopPropagation();openLightbox(\''+su+'\', \''+sk+'\', \''+cNum+'\', \''+rNum+'\')">' +
                    tBadge + kBadge +
                    '<button class="slot-dl-btn" onclick="event.stopPropagation();downloadImage(\''+su+"','"+fname+'\')" title="下载"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAuklEQVR4nO2RsQ3CMBBFT8AwFFAlFWEAGIKwF2IwFLpQoDABVA8FGSmCIM7JmYL4VS7+v+ezRSKDBBgBe+BGd67Arp7lI86xY6OVjoGDK+U9Xm3rZhyBiX3BagGg6LttyxKFJhwEieJXPGYtgOznYumY/0gUM3RxBqRA1chXQAIsQ4oTl5k18o+zu1Aw8QWYt3SmwDmk+E2ukdZYiHH/mj7/W1MQI7E3ohCfAnhLjXhtLC+B1Vdx5O+4A/EyVeP3ljpBAAAAAElFTkSuQmCC" alt="downloads" style="width: 17px;height: 17px;"></button></div>';
            } else if (errors[i]) {
                slotsHtml += '<div class="img-slot" id="'+sid+'">' + tBadge + kBadge + '<div class="slot-err">'+escHtml(errors[i])+'</div></div>';
            } else {
                slotsHtml += '<div class="img-slot" id="'+sid+'">'+buildSlotLoading(sid)+'</div>';
            }
        }
        slotsHtml += '</div>';

        const feed = document.getElementById('chatFeed');
        if (!document.getElementById(chatObj.id)) {
            feed.insertAdjacentHTML('beforeend', buildCardHTML(chatObj, slotsHtml));
        }

        const startTime = chatObj.start_time || (chatObj.created_at * 1000) || Date.now();
        const timerInt = setInterval(() => {
            const cardEl = document.getElementById(chatObj.id);
            if (!cardEl) { clearInterval(timerInt); return; } 
            for(let i=0; i<n; i++) {
                const timerEl = document.getElementById('timer_' + chatObj.id + '_s' + i);
                if (timerEl) {
                    timerEl.innerText = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
                }
            }
        }, 100);
    }

    async function deleteChatCard(chatId) {
        document.getElementById(chatId)?.remove();
        await fetchApi('/api/ui_chats', {method:'DELETE', body:JSON.stringify({session_id: currentSessionId, chat_id: chatId})});
        const sess = sessionsData.find(s => s.id === currentSessionId);
        if (sess) sess.messages = sess.messages.filter(m => m.id !== chatId);

        const feed = document.getElementById('chatFeed');
        if(!feed.querySelector('.chat-card')){ 
            let e = document.getElementById('emptyState'); 
            if(!e) feed.insertAdjacentHTML('afterbegin','<div class="feed-placeholder" id="emptyState">准备就绪，请输入您的创意...</div>'); 
            else e.style.display=''; 
        }
    }

    function submitTask() {
        const prompt=document.getElementById('prompt').value.trim();
        const model=document.getElementById('sel-model').dataset.value;
        const size=document.getElementById('sel-size').dataset.value;
        const ratio=document.getElementById('sel-ratio').dataset.value;
        const n=parseInt(document.getElementById('sel-n').dataset.value);
        if(!model||!MODEL_COSTS[model]) return alert("请先选择模型");
        if(!prompt&&!attachedUrls.length) return alert("请输入创意或上传图片");
        if(!currentSessionId) return alert("请先新建对话");
        
        const empty=document.getElementById('emptyState'); 
        if(empty) empty.style.display='none';

        const taskType=attachedUrls.length>0?'image_to_image':'text_to_image';
        const payload={type:taskType,prompt,model_id:model,size,aspect_ratio:ratio,n};
        if(taskType==='image_to_image') payload.input_images=[...attachedUrls];

        const chatId='chat_'+Date.now();
        const chatObj={
            id: chatId,
            payload: payload,
            status: 'generating',
            start_time: Date.now(),
            created_at: Date.now() / 1000,
            urls: new Array(n).fill(null),
            times: new Array(n).fill(null),
            errors: new Array(n).fill(null),
            keys: new Array(n).fill(null),
            costs: new Array(n).fill(null),
            remains: new Array(n).fill(null)
        };

        const sess = sessionsData.find(s => s.id === currentSessionId);
        if (sess) sess.messages.push(chatObj);

        renderPendingCard(chatObj);
        scrollFeedToBottom();

        document.getElementById('prompt').value='';
        document.getElementById('prompt').style.height='auto';
        clearAllAttachments();
        saveSettings();

        fetchApi('/api/ui_chats', {method: 'POST', body: JSON.stringify({session_id: currentSessionId, message: chatObj})})
        .then(() => {
            return fetchApi('/api/ui_generate_async', {
                method: 'POST', 
                body: JSON.stringify({session_id: currentSessionId, chat_id: chatId, payload})
            });
        })
        .then(() => {
            startPolling(currentSessionId, chatId);
        });
    }

    function startPolling(sessId, chatId) {
        if (activePolls.has(chatId)) return;
        activePolls.add(chatId);

        const intId = setInterval(async () => {
            try {
                const res = await fetchApi(`/api/ui_chat_status?session_id=${sessId}&chat_id=${chatId}`);
                if (res.status === 200) {
                    const data = await res.json();
                    
                    const sess = sessionsData.find(s => s.id === sessId);
                    if (sess) {
                        const idx = sess.messages.findIndex(m => m.id === data.id);
                        if (idx !== -1) sess.messages[idx] = data;
                    }

                    if (currentSessionId === sessId) {
                        const n = data.payload.n || 1;
                        let anyNew = false;
                        
                        for(let i=0; i<n; i++) {
                            const sid = data.id + '_s' + i;
                            const slotEl = document.getElementById(sid);
                            if (slotEl && slotEl.querySelector('.lp-inner')) { 
                                if (data.urls && data.urls[i]) {
                                    renderSlotImage(sid, data.urls[i], data.times ? data.times[i] : null, data.keys ? data.keys[i] : null, data.costs ? data.costs[i] : null, data.remains ? data.remains[i] : null);
                                    anyNew = true;
                                } else if (data.errors && data.errors[i]) {
                                    renderSlotError(sid, data.errors[i], data.times ? data.times[i] : null, data.keys ? data.keys[i] : null, data.costs ? data.costs[i] : null, data.remains ? data.remains[i] : null);
                                    anyNew = true;
                                }
                            }
                        }

                        if (data.status !== 'generating') {
                            clearInterval(intId);
                            activePolls.delete(chatId);
                            
                            const oldCard = document.getElementById(data.id);
                            if (oldCard) {
                                let ci='';
                                if ((data.urls && data.urls.length > 0) || (data.errors && data.errors.length > 0)) {
                                    ci = buildResultHTML(data);
                                } else {
                                    const errStr = data.error || '生成失败';
                                    ci = '<span class="err-text">'+escHtml(errStr)+'</span>';
                                }
                                oldCard.outerHTML = buildCardHTML(data, ci);
                            }
                            loadGallery();
                            loadKeys();
                        } else if (anyNew) {
                            loadGallery();
                            loadKeys();
                        }
                    } else {
                        if (data.status !== 'generating') {
                            clearInterval(intId);
                            activePolls.delete(chatId);
                        }
                    }
                } else if (res.status === 404) {
                    clearInterval(intId);
                    activePolls.delete(chatId);
                }
            } catch(e) {}
        }, 2000);
    }

    function reuseParams(encoded) {
        try {
            const p=JSON.parse(decodeURIComponent(encoded));
            document.getElementById('prompt').value=p.prompt||'';
            rebuildAllSelectsWithValues(p.model_id,p.size,p.aspect_ratio,p.n);
            clearAllAttachments();
            if(p.input_images&&p.input_images.length) p.input_images.forEach(u=>appendToAttachments(u));
            updateCostUI(); document.getElementById('prompt').focus();
        } catch(e) { console.error('Reuse failed',e); }
    }

    function setGalleryFilter(type) {
        currentGalleryFilter = type;
        document.querySelectorAll('#tab-history .filter-btn').forEach(b => {
            b.classList.remove('active');
            if (
                (type === 'all' && b.innerText === '全部') ||
                (type === 'upload' && b.innerText === '上传') ||
                (type === 'generate' && b.innerText === '生成')
            ) { b.classList.add('active'); }
        });
        renderGalleryItems();
    }

    async function loadGallery() {
        try {
            const res = await fetchApi('/api/ui_history');
            cachedGalleryData = await res.json();
            renderGalleryItems();
        } catch(e) {}
    }

    function renderGalleryItems() {
        const data = cachedGalleryData.filter(item => {
            if (currentGalleryFilter === 'upload') return item.type === 'upload';
            if (currentGalleryFilter === 'generate') return item.type !== 'upload';
            return true;
        });

        document.getElementById('historyGrid').innerHTML = data.map(item => {
            const tag = item.type === 'upload' ? '📤' : '🎨'; 
            const su = (item.url || '').replace(/'/g, "\\'"); 
            const si = (item.id || '').replace(/'/g, "\\'");
            return '<div class="history-item"><img src="'+item.url+'" loading="lazy" onclick="openLightbox(\''+su+'\')"/><span class="tag">'+tag+'</span><div class="hist-actions"><button class="hist-act-btn hist-use-btn" onclick="event.stopPropagation();appendToAttachments(\''+su+'\')" title="添加到输入框">＋</button><button class="hist-act-btn hist-del-btn" onclick="event.stopPropagation();deleteGalleryItem(\''+si+'\')" title="删除">✕</button></div></div>';
        }).join('');
    }

    async function deleteGalleryItem(id) { if(!id)return; await fetchApi('/api/ui_history',{method:'DELETE',body:JSON.stringify({id})}); loadGallery(); }
    
    async function loadKeys() {
        try { const r=await fetchApi('/api/ui_keys'); const keys=await r.json(); document.getElementById('keyList').innerHTML=keys.map(k=>'<div class="key-item"><span class="key-item-str">'+k.key+'</span><div style="flex-shrink:0;"><strong style="color:var(--accent);">'+k.points+' 点</strong><button style="background:none;border:none;color:#ef4444;cursor:pointer;margin-left:12px;" onclick="deleteKey(\''+k.key+'\')">✕</button></div></div>').join(''); } catch(e) {}
    }
    async function addKey() { const k=document.getElementById('newKey').value.trim(); if(!k)return; await fetchApi('/api/ui_keys',{method:'POST',body:JSON.stringify({key:k})}); document.getElementById('newKey').value=''; loadKeys(); }
    function deleteKey(k) { 
        showConfirm('确定要删除这个 Key 吗？', '删除后如果需要使用请重新添加', async () => {
            await fetchApi('/api/ui_keys',{method:'DELETE',body:JSON.stringify({key:k})}); 
            loadKeys(); 
        });
    }
</script>
</body>
</html>"""


HTML_PAGE = HTML_PAGE_RAW.replace("__FAVICON_PLACEHOLDER__", FAVICON_B64)

# ================= HTTP 服务 =================
class UIProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, status, payload=None, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-type", ctype)
        # 强制击穿浏览器缓存机制
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

        if payload is not None:
            if "json" in ctype:
                self.wfile.write(
                    json.dumps(payload, ensure_ascii=False).encode("utf-8")
                )
            else:
                self.wfile.write(payload.encode("utf-8"))

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except:
            return None

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self._send(200, HTML_PAGE, "text/html; charset=utf-8")
        elif path == "/api/ui_keys":
            self._send(200, load_json(KEYS_FILE, []))
        elif path == "/api/ui_history":
            self._send(200, clean_and_load_history())
        elif path == "/api/ui_sessions":
            self._send(200, load_sessions())
        elif path == "/api/ui_config":
            self._send(
                200, {"model_costs": MODEL_COSTS, "model_names": MODEL_DISPLAY_NAMES}
            )
        elif path == "/api/ui_chat_status":
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            sess_id = query.get("session_id", [None])[0]
            chat_id = query.get("chat_id", [None])[0]
            if sess_id and chat_id:
                sessions = load_sessions()
                for s in sessions:
                    if s["id"] == sess_id:
                        for m in s["messages"]:
                            if m["id"] == chat_id:
                                return self._send(200, m)
            return self._send(404, {"error": "Not found"})
        else:
            self._send(404, {"error": "Not found"})

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        data = self._body()
        if path == "/api/ui_keys":
            if data:
                with FILE_LOCK:
                    keys = load_json(KEYS_FILE, [])
                    keys = [k for k in keys if k.get("key") != data.get("key")]
                    save_json(KEYS_FILE, keys)
            self._send(200, {"status": "ok"})
        elif path == "/api/ui_history":
            if data and data.get("id"):
                delete_history_item(data["id"])
            self._send(200, {"status": "ok"})
        elif path == "/api/ui_sessions":
            if data and data.get("id"):
                sessions = load_sessions()
                sessions = [s for s in sessions if s["id"] != data["id"]]
                save_sessions(sessions)
            self._send(200, {"status": "ok"})
        elif path == "/api/ui_chats":
            sess_id = data.get("session_id")
            chat_id = data.get("chat_id")
            if sess_id and chat_id:
                sessions = load_sessions()
                for s in sessions:
                    if s["id"] == sess_id:
                        s["messages"] = [
                            m for m in s["messages"] if m.get("id") != chat_id
                        ]
                        break
                save_sessions(sessions)
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        data = self._body()
        if data is None:
            return self._send(400, {"error": "Invalid JSON"})

        if path == "/api/ui_keys":
            new_key = data.get("key")
            if new_key:
                with FILE_LOCK:
                    keys = load_json(KEYS_FILE, [])
                    if not any(k.get("key") == new_key for k in keys):
                        keys.append({"key": new_key, "points": 50})
                        save_json(KEYS_FILE, keys)
            return self._send(200, {"status": "ok"})

        elif path == "/api/ui_sessions":
            action = data.get("action")
            if action == "create":
                return self._send(200, create_session())
            elif action == "rename":
                sess_id = data.get("id")
                title = data.get("title")
                if sess_id and title:
                    sessions = load_sessions()
                    for s in sessions:
                        if s["id"] == sess_id:
                            s["title"] = title
                            break
                    save_sessions(sessions)
                return self._send(200, {"status": "ok"})

        elif path == "/api/ui_chats":
            sess_id = data.get("session_id")
            msg = data.get("message")
            if sess_id and msg:
                with FILE_LOCK:
                    sessions = load_sessions()
                    for s in sessions:
                        if s["id"] == sess_id:
                            idx = next(
                                (
                                    i
                                    for i, m in enumerate(s["messages"])
                                    if m["id"] == msg["id"]
                                ),
                                -1,
                            )
                            if idx != -1:
                                s["messages"][idx] = msg
                            else:
                                s["messages"].append(msg)
                            break
                    save_sessions(sessions)
            return self._send(200, {"status": "ok"})

        elif path == "/api/ui_generate_async":
            sess_id = data.get("session_id")
            chat_id = data.get("chat_id")
            payload = data.get("payload", {})
            n = int(payload.get("n", 1))

            t = threading.Thread(
                target=background_generation, args=(sess_id, chat_id, payload, n)
            )
            t.daemon = True
            t.start()

            return self._send(200, {"status": "started"})

        elif path == "/api/ui_upload":
            api_key, _ = get_available_key(0)
            if not api_key:
                return self._send(400, {"error": "缺少 API Key 配置"})
            res_data, status = call_backend("/v1/images/upload", data, api_key)
            urls = extract_urls_and_parse(res_data)

            # --- 拦截特定的错误 URL ---
            if urls and any(target in urls for target in TARGET_ERROR_URL):
                return self._send(400, {"error": "云端API KEY 过期、无效或点数不足"})

            res_data["extracted_urls"] = urls
            res_data["url"] = urls[0] if urls else None
            if urls:
                save_history([{"type": "upload", "url": urls[0]}])
            return self._send(status, res_data)

        else:
            self._send(404, {"error": "Not found"})


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    cleanup_ghost_tasks()
    server = ThreadingHTTPServer(("0.0.0.0", UI_PORT), UIProxyHandler)
    print(f"🚀 [Image Studio WebUI] 代理服务已启动！")
    print(f"👉 访问地址: http://127.0.0.1:{UI_PORT}")
    print(f"📦 模型配置: {list(MODEL_COSTS.keys())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务关闭。")
        server.server_close()
