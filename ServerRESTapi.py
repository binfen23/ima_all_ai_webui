import json
import subprocess
import tempfile
import base64
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ================= 验证规则配置 =================
SUPPORTED_SIZES = {"512px", "1k", "2k", "4k"}
SUPPORTED_ASPECT_RATIOS = {"1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"}
SUPPORTED_N = {1, 2, 3, 4}

HOST = "0.0.0.0"
PORT = 22333

class ImageAPIHandler(BaseHTTPRequestHandler):
    
    # ---------------- 基础辅助函数 ----------------
    def _send_response(self, status_code, payload):
        """统一返回JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def _get_api_key(self, data):
        """支持从 Headers (Authorization: Bearer XXX) 或 Body 中获取 API Key"""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return data.get('api_key')

    def _read_json_body(self):
        """读取并解析 JSON Body"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        try:
            return json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return None

    def _run_cli_command(self, cmd):
        """执行本地CLI命令行并返回结果"""
        try:
            # 核心修复点：强制子进程的控制台输出使用 UTF-8，防止 GBK 遇到 Emoji 报错
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False, 
                env=env,              # 注入环境变量
                encoding="utf-8"      # 强制以 utf-8 解码 stdout/stderr
            )
            
            if result.returncode != 0:
                return self._send_response(500, {"error": "CLI execution failed", "details": result.stderr.strip()})
            
            # 尝试将 CLI 输出直接作为 JSON 解析并返回
            try:
                # 寻找输出中的合法 JSON 部分（防止有些前置日志干扰）
                out_str = result.stdout.strip()
                out_json = json.loads(out_str)
                self._send_response(200, out_json)
            except json.JSONDecodeError:
                # 若非 JSON 格式（如上传图片可能直接返回URL字符串），则包装一层
                self._send_response(200, {"result": result.stdout.strip()})
                
        except Exception as e:
            self._send_response(500, {"error": str(e)})

    # ---------------- 路由分发 ----------------
    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        data = self._read_json_body()
        if data is None: return # Error already sent

        if path == "/v1/images/generations":
            self.handle_text_to_image(data)
        elif path == "/v1/images/edits":
            self.handle_image_to_image(data)
        elif path == "/v1/images/upload":
            self.handle_upload(data)
        else:
            self._send_response(404, {"error": "Endpoint not found"})

    def do_GET(self):
        self._send_response(404, {"error": "Endpoint not found"})

    # ---------------- 业务处理 ----------------
    def handle_text_to_image(self, data):
        api_key = self._get_api_key(data)
        if not api_key: return self._send_response(401, {"error": "Missing api_key"})

        prompt = data.get("prompt")
        model_id = data.get("model_id", "doubao-seedream-4.5")
        size = data.get("size", "2k")
        n = data.get("n", 1)
        aspect_ratio = data.get("aspect_ratio", "1:1")

        if not prompt: return self._send_response(400, {"error": "Missing prompt"})
        if size not in SUPPORTED_SIZES: return self._send_response(400, {"error": f"Supported sizes: {SUPPORTED_SIZES}"})
        if n not in SUPPORTED_N: return self._send_response(400, {"error": f"Supported n: {SUPPORTED_N}"})
        if aspect_ratio not in SUPPORTED_ASPECT_RATIOS: return self._send_response(400, {"error": f"Supported aspect_ratio: {SUPPORTED_ASPECT_RATIOS}"})

        extra_params = json.dumps({"n": n, "aspect_ratio": aspect_ratio})
        
        cmd =[
            "python", "ima_create.py",
            "--api-key", api_key,
            "--task-type", "text_to_image",
            "--model-id", model_id,
            "--prompt", prompt,
            "--size", size,
            "--extra-params", extra_params,
            "--output-json"
        ]
        self._run_cli_command(cmd)

    def handle_image_to_image(self, data):
        api_key = self._get_api_key(data)
        if not api_key: return self._send_response(401, {"error": "Missing api_key"})

        prompt = data.get("prompt")
        model_id = data.get("model_id", "gemini-3.1-flash-image")
        input_images = data.get("input_images",[]) 
        size = data.get("size", "2k")
        n = data.get("n", 1)
        aspect_ratio = data.get("aspect_ratio", "1:1")

        if not prompt: return self._send_response(400, {"error": "Missing prompt"})
        if not isinstance(input_images, list) or len(input_images) == 0:
            return self._send_response(400, {"error": "Missing input_images array"})

        extra_params = json.dumps({"n": n, "aspect_ratio": aspect_ratio})
        
        cmd =[
            "python", "ima_create.py",
            "--api-key", api_key,
            "--task-type", "image_to_image",
            "--model-id", model_id,
            "--prompt", prompt,
            "--size", size,
            "--extra-params", extra_params,
            "--output-json"
        ]
        cmd.extend(["--input-images"] + input_images)
        self._run_cli_command(cmd)

    def handle_upload(self, data):
        api_key = self._get_api_key(data)
        image_base64 = data.get("image_base64")

        if not api_key: return self._send_response(401, {"error": "Missing api_key"})
        if not image_base64: return self._send_response(400, {"error": "Missing image_base64"})

        try:
            img_data = base64.b64decode(image_base64)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(img_data)
                tmp_file_path = tmp_file.name

            cmd =[
                "python", "ImaUploadImg.py",
                "--api-key", api_key,
                "--img", tmp_file_path
            ]
            
            # 同样修复这里的编码问题
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, env=env, encoding="utf-8"
            )
            os.remove(tmp_file_path)

            if result.returncode != 0:
                return self._send_response(500, {"error": "Upload failed", "details": result.stderr.strip()})
            
            out_str = result.stdout.strip()
            try:
                self._send_response(200, json.loads(out_str))
            except:
                self._send_response(200, {"url": out_str})

        except Exception as e:
            self._send_response(500, {"error": str(e)})



if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), ImageAPIHandler)
    print(f"🚀 Light-weight Multithreaded Image API Server running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        server.server_close()