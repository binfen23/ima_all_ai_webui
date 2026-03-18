#!/usr/bin/env python3
"""
IMA 图片上传 CLI 版
标准 CLI 规范：日志输出到 stderr，最终 URL 输出到 stdout
"""

import argparse
import hashlib
import mimetypes
import os
import time
import uuid
import sys
import requests

# ─── 配置 ─────────────────────────────────────────────────────────────────────
IMA_UPLOAD_BASE = "https://imapi.liveme.com"  # 生产环境端点

# 公开固定的 APP 凭证 (非敏感，前端代码中可见)
APP_ID = "webAgent"
APP_KEY = "32jdskjdk320eew"

# ─── 工具函数 ─────────────────────────────────────────────────────────────────
def log(msg):
    """打印日志到标准错误 (stderr)，防止污染标准输出"""
    print(msg, file=sys.stderr)

def _gen_sign() -> tuple[str, str, str]:
    nonce = uuid.uuid4().hex[:21]  
    timestamp = str(int(time.time()))
    raw = f"{APP_ID}|{APP_KEY}|{timestamp}|{nonce}"
    sign = hashlib.sha1(raw.encode()).hexdigest().upper()
    return sign, timestamp, nonce

def get_upload_token(api_key: str, suffix: str, content_type: str) -> dict:
    sign, timestamp, nonce = _gen_sign()
    
    params = {
        "appUid": api_key,           
        "appId": APP_ID,             
        "appKey": APP_KEY,           
        "cmimToken": api_key,        
        "sign": sign,                
        "timestamp": timestamp,      
        "nonce": nonce,              
        "fService": "privite",       
        "fType": "picture",          
        "fSuffix": suffix,           
        "fContentType": content_type 
    }
    
    url = f"{IMA_UPLOAD_BASE}/api/rest/oss/getuploadtoken"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to request upload token: {e}")
        
    if result.get("code") not in (0, 200):
        raise Exception(f"Get upload token failed: {result.get('message')}")
    
    data = result.get("data", {})
    return {
        "ful": data["ful"],
        "fdl": data["fdl"],
    }

def upload_to_oss(ful_url: str, file_bytes: bytes, content_type: str) -> bool:
    headers = {"Content-Type": content_type}
    try:
        response = requests.put(ful_url, data=file_bytes, headers=headers, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"OSS upload failed: {e}")
        
    return True

def process_and_upload(image_source: str, api_key: str) -> str:
    if image_source.startswith("http://") or image_source.startswith("https://"):
        log(f"✅ Input is already a URL: {image_source}")
        return image_source
    
    if not os.path.exists(image_source):
        raise FileNotFoundError(f"Local file not found: {image_source}")
    
    with open(image_source, 'rb') as f:
        file_bytes = f.read()
        
    ext = os.path.splitext(image_source)[1].lower().lstrip('.')
    if not ext or ext not in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'):
        ext = 'jpeg'
    content_type = mimetypes.guess_type(image_source)[0] or f"image/{ext}"
    
    log(f"[*] Preparing file: {os.path.basename(image_source)}, size: {len(file_bytes)} Bytes, type: {content_type}")
    
    log("[*] Getting upload token from IMA API...")
    token = get_upload_token(api_key, ext, content_type)
    
    log("[*] Uploading image binary to OSS...")
    upload_to_oss(token["ful"], file_bytes, content_type)
    
    return token["fdl"]

# ─── 主函数 CLI 解析 ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="IMA Image Upload CLI Tool")
    parser.add_argument("--api-key", required=True, help="Your IMA API key (e.g., ima_xxx)")
    parser.add_argument("--img", required=True, help="Path to local image file or an existing image URL")
    
    args = parser.parse_args()
    
    log("=" * 60)
    log("🚀 IMA Image Uploader Started")
    log("=" * 60)
    
    try:
        cdn_url = process_and_upload(args.img, args.api_key)
        log(f"✅ Upload Successful!")
        
        # ⚠️ 关键修改：只向标准输出(stdout)打印纯 URL！没有任何多余字符！
        print(cdn_url)
        
    except Exception as e:
        log(f"\n❌ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()