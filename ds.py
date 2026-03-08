import os
import sys
import time
import ssl
import json
import random
import string
import hashlib
import threading
import re
import smtplib
import subprocess
import itertools
import traceback
from collections import defaultdict
from urllib.parse import urlparse, urlencode
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def check_and_install():
    requirements = [
        "requests",
        "psutil",
        "colorama",
        "paho-mqtt",
        "beautifulsoup4",
        "cloudscraper",
        "fake_useragent",
        "pyfiglet",
        "termcolor",
        "aiohttp",
        "websockets"
    ]
    
    missing = []
    for req in requirements:
        try:
            if req == "fake_useragent":
                __import__("fake_useragent")
            elif req == "paho-mqtt":
                __import__("paho.mqtt.client")
            elif req == "beautifulsoup4":
                __import__("bs4")
            else:
                __import__(req)
        except ImportError:
            missing.append(req)
    
    if missing:
        print(f"[!] Thiếu package: {', '.join(missing)}")
        print("[*] Đang cài đặt...")
        for pkg in missing:
            install_name = pkg
            if pkg == "fake_useragent":
                install_name = "fake-useragent"
            elif pkg == "paho-mqtt":
                install_name = "paho-mqtt"
            elif pkg == "beautifulsoup4":
                install_name = "beautifulsoup4"
            
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", install_name, "--quiet"])
                print(f"  ✓ {pkg}")
            except:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])
                    print(f"  ✓ {pkg}")
                except:
                    print(f"  ✗ {pkg}")
        
        print("[*] Khởi động lại...")
        time.sleep(2)
        os.execv(sys.executable, [sys.executable] + sys.argv)

check_and_install()

import requests
import psutil
import gc
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt
from colorama import init, Fore, Back, Style
import pyfiglet
from termcolor import colored
import cloudscraper
from fake_useragent import UserAgent
import websockets

init(autoreset=True)

cookie_attempts = defaultdict(lambda: {'count': 0, 'last_reset': time.time(), 'banned_until': 0, 'permanent_ban': False})
cookie_delays = {}
active_threads = {}
cleanup_lock = threading.Lock()
treo_tabs = {}
treo_history = []

def clr():
    os.system('cls' if os.name == 'nt' else 'clear')
def input_cookies():
    print(Fore.CYAN + "Chọn cách nhập cookie:")
    print("1. Nhập thủ công (gõ 'done' để dừng)")
    print("2. Nhập từ file (mỗi dòng 1 cookie)")
    
    choice = input(Fore.YELLOW + "Chọn: ").strip()
    
    if choice == "1":
        cookies = []
        print(Fore.GREEN + "Nhập cookie (gõ 'done' để dừng):")
        while True:
            ck = input("> ").strip()
            if ck.lower() == 'done':
                break
            if 'c_user=' in ck:
                cookies.append(ck)
        return cookies
    
    elif choice == "2":
        file_path = input(Fore.GREEN + "Nhập đường dẫn file: ").strip()
        if not os.path.exists(file_path):
            print(Fore.RED + "File không tồn tại")
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cookies = [line.strip() for line in f if line.strip() and 'c_user=' in line]
            return cookies
        except:
            return []
    
    else:
        return []

def input_tokens():
    print(Fore.CYAN + "Chọn cách nhập token:")
    print("1. Nhập thủ công (gõ 'done' để dừng)")
    print("2. Nhập từ file (mỗi dòng 1 token)")
    
    choice = input(Fore.YELLOW + "Chọn: ").strip()
    
    if choice == "1":
        tokens = []
        print(Fore.GREEN + "Nhập token (gõ 'done' để dừng):")
        while True:
            tk = input("> ").strip()
            if tk.lower() == 'done':
                break
            if tk:
                tokens.append(tk)
        return tokens
    
    elif choice == "2":
        file_path = input(Fore.GREEN + "Nhập đường dẫn file: ").strip()
        if not os.path.exists(file_path):
            print(Fore.RED + "File không tồn tại")
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tokens = [line.strip() for line in f if line.strip()]
            return tokens
        except:
            return []
    
    else:
        return []

def input_ids(prompt="ID"):
    ids = []
    print(Fore.GREEN + f"Nhập {prompt} (gõ 'done' để dừng):")
    while True:
        item = input("> ").strip()
        if item.lower() == 'done':
            break
        if item:
            ids.append(item)
    return ids

def handle_failed_connection(cookie_hash):
    global cookie_attempts
    current_time = time.time()
    if current_time - cookie_attempts[cookie_hash]['last_reset'] > 43200:
        cookie_attempts[cookie_hash]['count'] = 0
        cookie_attempts[cookie_hash]['last_reset'] = current_time
        cookie_attempts[cookie_hash]['banned_until'] = 0
    if cookie_attempts[cookie_hash]['banned_until'] > 0:
        ban_count = cookie_attempts[cookie_hash].get('ban_count', 0) + 1
        cookie_attempts[cookie_hash]['ban_count'] = ban_count
        if ban_count >= 5:
            cookie_attempts[cookie_hash]['permanent_ban'] = True
            print(f"Cookie {cookie_hash[:10]} Đã Bị Ngưng Hoạt Động Vĩnh Viễn")
            for key in list(active_threads.keys()):
                if key.startswith(cookie_hash):
                    if hasattr(active_threads[key], 'stop'):
                        active_threads[key].stop()
                    del active_threads[key]

def cleanup_global_memory():
    global active_threads, cookie_attempts
    with cleanup_lock:
        current_time = time.time()
        expired_cookies = []
        for cookie_hash, data in cookie_attempts.items():
            if data.get('permanent_ban', False) or (current_time - data.get('last_reset', 0) > 86400):
                expired_cookies.append(cookie_hash)
        for cookie_hash in expired_cookies:
            del cookie_attempts[cookie_hash]
            for key in list(active_threads.keys()):
                if key.startswith(cookie_hash):
                    if hasattr(active_threads[key], 'stop'):
                        active_threads[key].stop()
                    del active_threads[key]
        gc.collect()
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"Memory Usage: {memory_info.rss / (1024**3):.2f} GB")

def parse_cookie_string(cookie_string):
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.strip().split("=", 1)
            cookie_dict[key] = value
    return cookie_dict

def generate_offline_threading_id() -> str:
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))

def get_headers(url: str, options: dict = {}, ctx: dict = {}, customHeader: dict = {}) -> dict:
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.facebook.com/",
        "Host": urlparse(url).netloc,
        "Origin": "https://www.facebook.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
        "Connection": "keep-alive",
    }
    if "user_agent" in options:
        headers["User-Agent"] = options["user_agent"]
    for key in customHeader:
        headers[key] = customHeader[key]
    if "region" in ctx:
        headers["X-MSGR-Region"] = ctx["region"]
    return headers

def json_minimal(data):
    return json.dumps(data, separators=(",", ":"))

class Counter:
    def __init__(self, initial_value=0):
        self.value = initial_value
    def increment(self):
        self.value += 1
        return self.value
    @property
    def counter(self):
        return self.value

def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
    if '_req_counter' not in globals():
        globals()['_req_counter'] = Counter(0)
    __reg = globals()['_req_counter'].increment()
    dataForm = {}
    if requireGraphql is None:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36) 
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
        dataForm["fb_api_caller_class"] = "RelayModern"
        dataForm["fb_api_req_friendly_name"] = FBApiReqFriendlyName
        dataForm["server_timestamps"] = "true"
        dataForm["doc_id"] = str(docID)
    else:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36) 
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
    return dataForm

def mainRequests(url, data, cookies):
    return {
        "url": url,
        "data": data,
        "headers": {
            "authority": "www.facebook.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "sec-ch-ua": "\"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"108\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "x-fb-friendly-name": "FriendingCometFriendRequestsRootQueryRelayPreloader",
            "x-fb-lsd": "YCb7tYCGWDI6JLU5Aexa1-"
        },
        "cookies": parse_cookie_string(cookies),
        "verify": True
    }

def digitToChar(digit):
    if digit < 10:
        return str(digit)
    return chr(ord('a') + digit - 10)

def str_base(number, base):
    if number < 0:
        return "-" + str_base(-number, base)
    (d, m) = divmod(number, base)
    if d > 0:
        return str_base(d, base) + digitToChar(m)
    return digitToChar(m)

def generate_session_id():
    return random.randint(1, 2 ** 53)

def generate_client_id():
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)

def get_friends_list(dataFB):
    try:
        form = {
            "viewer": str(dataFB["FacebookID"]),
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/chat/user_info_all", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/chat/user_info_all",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if not data or "payload" not in data:
            raise Exception("getFriendsList returned empty object or missing payload.")
        if "error" in data:
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        friends = data["payload"]
        friend_ids = [str(user_id) for user_id in friends.keys()]
        return True, friend_ids, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Lấy được {len(friend_ids)} bạn bè."
    except Exception as e:
        return False, [], f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi khi lấy danh sách bạn bè: {str(e)}"

def tenbox(newTitle, threadID, dataFB):
    try:
        message_id = generate_offline_threading_id()
        timestamp = int(time.time() * 1000)
        form_data = {
            "client": "mercury",
            "action_type": "ma-type:log-message",
            "author": f"fbid:{dataFB['FacebookID']}",
            "thread_id": str(threadID),
            "timestamp": timestamp,
            "timestamp_relative": str(int(time.time())),
            "source": "source:chat:web",
            "source_tags[0]": "source:chat",
            "offline_threading_id": message_id,
            "message_id": message_id,
            "threading_id": generate_offline_threading_id(),
            "thread_fbid": str(threadID),
            "thread_name": str(newTitle),
            "log_message_type": "log:thread-name",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        response = requests.post(
            "https://www.facebook.com/messaging/set_thread_name/",
            data=form_data,
            headers=get_headers("https://www.facebook.com", customHeader={"Content-Length": str(len(form_data))}),
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code == 200:
            return True, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã đổi tên thành: {newTitle}"
        else:
            return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi HTTP {response.status_code} khi đổi tên."
    except Exception as e:
        return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi: {e}"

def change_nickname(nickname, thread_id, participant_id, dataFB):
    try:
        form = {
            "nickname": nickname,
            "participant_id": str(participant_id),
            "thread_or_other_fbid": str(thread_id),
            "source": "thread_settings",
            "dpr": "1",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": str_base(Counter().increment(), 36),
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/messaging/save_thread_nickname/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/messaging/save_thread_nickname/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if "error" in data:
            error_code = data.get("error")
            if error_code == 1545014:
                raise Exception("Trying to change nickname of user who isn't in thread")
            if error_code == 1357031:
                raise Exception("Thread doesn't exist or has no messages")
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        return True, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã đổi biệt danh cho user {participant_id} thành {nickname} trong box {thread_id}"
    except Exception as e:
        return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi khi đổi biệt danh cho user {participant_id}: {str(e)}"
        
def get_thread_info_graphql(thread_id, dataFB):
    try:
        form = {
            "queries": json.dumps({
                "o0": {
                    "doc_id": "3449967031715030",
                    "query_params": {
                        "id": str(thread_id),
                        "message_limit": 0,
                        "load_messages": False,
                        "load_read_receipts": False,
                        "before": None
                    }
                }
            }, separators=(",", ":")),
            "batch_name": "MessengerGraphQLThreadFetcher",
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": str_base(Counter().increment(), 36),
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/api/graphqlbatch/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/api/graphqlbatch/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        response_parts = content.split("\n")
        if not response_parts or not response_parts[0].strip():
            raise Exception("Empty response from API")
        data = json.loads(response_parts[0])
        if "error" in data:
            raise Exception(f"API Error: {data.get('errorDescription', 'Unknown error')}")
        if data.get("error_results", 0) != 0:
            raise Exception("Error results in response")
        message_thread = data["o0"]["data"]["message_thread"]
        thread_id = (message_thread["thread_key"]["thread_fbid"] 
                     if message_thread["thread_key"].get("thread_fbid") 
                     else message_thread["thread_key"]["other_user_id"])
        participant_ids = [edge["node"]["messaging_actor"]["id"] 
                          for edge in message_thread["all_participants"]["edges"]]
        return True, participant_ids, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Lấy được {len(participant_ids)} thành viên trong box {thread_id}"
    except Exception as e:
        return False, [], f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi khi lấy thông tin box {thread_id}: {str(e)}"

def create_new_group(dataFB, participant_ids, group_title):
    try:
        if not isinstance(participant_ids, list):
            raise ValueError("participant_ids should be an array.")
        if len(participant_ids) < 2:
            raise ValueError("participant_ids should have at least 2 IDs.")
        pids = [{"fbid": str(pid)} for pid in participant_ids]
        pids.append({"fbid": str(dataFB["FacebookID"])})
        form = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "MessengerGroupCreateMutation",
            "av": str(dataFB["FacebookID"]),
            "doc_id": "577041672419534",
            "variables": json.dumps({
                "input": {
                    "entry_point": "jewel_new_group",
                    "actor_id": str(dataFB["FacebookID"]),
                    "participants": pids,
                    "client_mutation_id": str(random.randint(1, 1024)),
                    "thread_settings": {
                        "name": group_title,
                        "joinable_mode": "PRIVATE",
                        "thread_image_fbid": None
                    }
                }
            }, separators=(",", ":")),
            "fb_dtsg": dataFB["fb_dtsg"],
            "jazoest": dataFB["jazoest"],
            "__user": str(dataFB["FacebookID"]),
            "__a": "1",
            "__req": "1",
            "__rev": dataFB.get("clientRevision", "1015919737")
        }
        headers = get_headers("https://www.facebook.com/api/graphql/", customHeader={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        response = requests.post(
            "https://www.facebook.com/api/graphql/",
            data=form,
            headers=headers,
            cookies=parse_cookie_string(dataFB["cookieFacebook"]),
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Error {response.status_code}")
        content = response.text.replace('for (;;);', '')
        data = json.loads(content)
        if "errors" in data:
            raise Exception(f"API Error: {data['errors'][0]['message']}")
        thread_id = data["data"]["messenger_group_thread_create"]["thread"]["thread_key"]["thread_fbid"]
        return True, thread_id, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã tạo nhóm: {group_title} (ID: {thread_id})"
    except Exception as e:
        return False, None, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi khi tạo nhóm {group_title}: {str(e)}"

def add_user_to_group(dataFB, user_ids, thread_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            if not isinstance(user_ids, list):
                user_ids = [user_ids]
            for user_id in user_ids:
                if not isinstance(user_id, (str, int)) or not str(user_id).isdigit():
                    raise ValueError(f"Invalid user_id: {user_id}. Must be a number or string of digits.")
            if not isinstance(thread_id, (str, int)) or not str(thread_id).isdigit():
                raise ValueError(f"Invalid thread_id: {thread_id}. Must be a number or string of digits.")
            message_and_otid = generate_offline_threading_id()
            form = {
                "client": "mercury",
                "action_type": "ma-type:log-message",
                "author": f"fbid:{dataFB['FacebookID']}",
                "thread_id": "",
                "timestamp": str(int(time.time() * 1000)),
                "timestamp_absolute": "Today",
                "timestamp_relative": "Just now",
                "timestamp_time_passed": "0",
                "is_unread": "false",
                "is_cleared": "false",
                "is_forward": "false",
                "is_filtered_content": "false",
                "is_filtered_content_bh": "false",
                "is_filtered_content_account": "false",
                "is_spoof_warning": "false",
                "source": "source:chat:web",
                "source_tags[0]": "source:chat",
                "log_message_type": "log:subscribe",
                "status": "0",
                "offline_threading_id": message_and_otid,
                "message_id": message_and_otid,
                "threading_id": f"<{int(time.time() * 1000)}:{message_and_otid}>",
                "manual_retry_cnt": "0",
                "thread_fbid": str(thread_id),
                "fb_dtsg": dataFB["fb_dtsg"],
                "jazoest": dataFB["jazoest"],
                "__user": str(dataFB["FacebookID"]),
                "__a": "1",
                "__req": str_base(Counter().increment(), 36),
                "__rev": dataFB.get("clientRevision", "1015919737")
            }
            for i, user_id in enumerate(user_ids):
                form[f"log_message_data[added_participants][{i}]"] = f"fbid:{user_id}"
            headers = get_headers("https://www.facebook.com/messaging/send/", customHeader={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-FB-LSD": dataFB.get("lsd", "YCb7tYCGWDI6JLU5Aexa1-"),
                "Content-Length": str(len(urlencode(form)))
            })
            print(f"[DEBUG] Attempt {attempt + 1}/{max_retries}: Adding {len(user_ids)} users to thread {thread_id}")
            response = requests.post(
                "https://www.facebook.com/messaging/send/",
                data=form,
                headers=headers,
                cookies=parse_cookie_string(dataFB["cookieFacebook"]),
                timeout=15
            )
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}: {response.text[:100]}")
            content = response.text.replace('for (;;);', '')
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise Exception(f"JSON Decode Error: {e}. Response: {content[:100]}")
            if "error" in data:
                error_msg = data.get('errorDescription', 'Unknown error')
                error_code = data.get('error', 'No error code')
                if error_code == 1545052 and attempt < max_retries - 1:
                    print(f"[WARNING] API Error 1545052 on attempt {attempt + 1}. Retrying after 10 seconds...")
                    time.sleep(10)
                    continue
                raise Exception(f"API Error {error_code}: {error_msg}")
            return True, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã thêm {len(user_ids)} người vào nhóm {thread_id}"
        except Exception as e:
            error_msg = f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi khi thêm người vào nhóm {thread_id}: {str(e)}"
            print(error_msg)
            if 'response' in locals():
                try:
                    with open('error_response.json', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print("[DEBUG] Saved error response to error_response.json")
                except:
                    pass
            if attempt == max_retries - 1:
                return False, error_msg
            time.sleep(10)
    return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Failed after {max_retries} attempts"

def change_group_name_and_add_friends(dataFB, thread_id, group_name):
    try:
        success, log = tenbox(group_name, thread_id, dataFB)
        if not success:
            return False, log
        success, friend_ids, log = get_friends_list(dataFB)
        if not success:
            return False, log
        print(log)
        batch_size = 50
        for i in range(0, len(friend_ids), batch_size):
            batch = friend_ids[i:i + batch_size]
            success, log = add_user_to_group(dataFB, batch, thread_id)
            if not success:
                return False, log
            print(log)
            time.sleep(5)
        return True, f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã đổi tên nhóm thành {group_name} và thêm {len(friend_ids)} bạn bè vào nhóm {thread_id}"
    except Exception as e:
        return False, f"❌ [{datetime.now().strftime('%H:%M:%S')}] Lỗi: {str(e)}"

def get_cookies_input():
    cookies = input_cookies()
    if not cookies:
        print("[!] Không có cookie hợp lệ")
        exit()
    return cookies

class fbTools:
    def __init__(self, dataFB, threadID="0"):
        self.threadID = threadID
        self.dataGet = None
        self.dataFB = dataFB
        self.ProcessingTime = None
        self.last_seq_id = None
    
    def getAllThreadList(self):
        dataForm = formAll(self.dataFB, requireGraphql=0)
        dataForm["queries"] = json.dumps({
            "o0": {
                "doc_id": "3336396659757871",
                "query_params": {
                    "limit": 20,
                    "before": None,
                    "tags": ["INBOX"],
                    "includeDeliveryReceipts": False,
                    "includeSeqID": True,
                }
            }
        })
        req_data = mainRequests("https://www.facebook.com/api/graphqlbatch/", dataForm, self.dataFB["cookieFacebook"])
        try:
            sendRequests = requests.post(**req_data)
        except Exception as e:
            print(f"Error in request: {e}")
            return False
        
        response_text = sendRequests.text
        self.ProcessingTime = sendRequests.elapsed.total_seconds()
        if response_text.startswith("for(;;);"):
            response_text = response_text[9:]
        if not response_text.strip():
            print("Error: Empty response from Facebook API")
            return False
        try:
            response_parts = response_text.split("\n")
            first_part = response_parts[0]
            if first_part.strip():
                response_data = json.loads(first_part)
                self.dataGet = first_part
                if "o0" in response_data and "data" in response_data["o0"] and "viewer" in response_data["o0"]["data"] and "message_threads" in response_data["o0"]["data"]["viewer"]:
                    self.last_seq_id = response_data["o0"]["data"]["viewer"]["message_threads"]["sync_sequence_id"]
                    return True
                else:
                    print("Error: Expected fields not found in response")
                    return False
            else:
                print("Error: Empty first part of response")
                return False
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Response first part: {response_parts[0][:100]}")
            return False
        except KeyError as e:
            print(f"Key Error: {e}")
            print("The expected data structure wasn't found in the response")
            return False

class MessageSender:
    def __init__(self, fbt, dataFB, fb_instance):
        self.fbt = fbt
        self.dataFB = dataFB
        self.fb_instance = fb_instance
        self.mqtt = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.syncToken = None
        self.lastSeqID = None
        self.req_callbacks = {}
        self.cookie_hash = hashlib.md5(dataFB['cookieFacebook'].encode()).hexdigest()
        self.connect_attempts = 0
        self.last_cleanup = time.time()
        self.THEMES = [
            {"id": "3650637715209675", "name": "Besties"},
            {"id": "769656934577391", "name": "Women's History Month"},
            {"id": "702099018755409", "name": "Dune: Part Two"},
            {"id": "1480404512543552", "name": "Avatar: The Last Airbender"},
            {"id": "952656233130616", "name": "J.Lo"},
            {"id": "741311439775765", "name": "Love"},
            {"id": "215565958307259", "name": "Bob Marley: One Love"},
            {"id": "194982117007866", "name": "Football"},
            {"id": "1743641112805218", "name": "Soccer"},
            {"id": "730357905262632", "name": "Mean Girls"},
            {"id": "1270466356981452", "name": "Wonka"},
            {"id": "704702021720552", "name": "Pizza"},
            {"id": "1013083536414851", "name": "Wish"},
            {"id": "359537246600743", "name": "Trolls"},
            {"id": "173976782455615", "name": "The Marvels"},
            {"id": "2317258455139234", "name": "One Piece"},
            {"id": "6685081604943977", "name": "1989"},
            {"id": "1508524016651271", "name": "Avocado"},
            {"id": "265997946276694", "name": "Loki Season 2"},
            {"id": "6584393768293861", "name": "olivia rodrigo"},
            {"id": "845097890371902", "name": "Baseball"},
            {"id": "292955489929680", "name": "Lollipop"},
            {"id": "976389323536938", "name": "Loops"},
            {"id": "810978360551741", "name": "Parenthood"},
            {"id": "195296273246380", "name": "Bubble Tea"},
            {"id": "6026716157422736", "name": "Basketball"},
            {"id": "693996545771691", "name": "Elephants & Flowers"},
            {"id": "390127158985345", "name": "Chill"},
            {"id": "365557122117011", "name": "Support"},
            {"id": "339021464972092", "name": "Music"},
            {"id": "1060619084701625", "name": "Lo-Fi"},
            {"id": "3190514984517598", "name": "Sky"},
            {"id": "627144732056021", "name": "Celebration"},
            {"id": "275041734441112", "name": "Care"},
            {"id": "3082966625307060", "name": "Astrology"},
            {"id": "539927563794799", "name": "Cottagecore"},
            {"id": "527564631955494", "name": "Ocean"},
            {"id": "230032715012014", "name": "Tie-Dye"},
            {"id": "788274591712841", "name": "Monochrome"},
            {"id": "3259963564026002", "name": "Default"},
            {"id": "724096885023603", "name": "Berry"},
            {"id": "624266884847972", "name": "Candy"},
            {"id": "273728810607574", "name": "Unicorn"},
            {"id": "262191918210707", "name": "Tropical"},
            {"id": "2533652183614000", "name": "Maple"},
            {"id": "909695489504566", "name": "Sushi"},
            {"id": "582065306070020", "name": "Rocket"},
            {"id": "557344741607350", "name": "Citrus"},
            {"id": "280333826736184", "name": "Lollipop"},
            {"id": "271607034185782", "name": "Shadow"},
            {"id": "1257453361255152", "name": "Rose"},
            {"id": "571193503540759", "name": "Lavender"},
            {"id": "2873642949430623", "name": "Tulip"},
            {"id": "3273938616164733", "name": "Classic"},
            {"id": "403422283881973", "name": "Apple"},
            {"id": "3022526817824329", "name": "Peach"},
            {"id": "672058580051520", "name": "Honey"},
            {"id": "3151463484918004", "name": "Kiwi"},
            {"id": "736591620215564", "name": "Ocean"},
            {"id": "193497045377796", "name": "Grape"},
        ]

    def set_theme(self, theme_id, thread_id, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        self.ws_task_number += 1
        if not theme_id:
            selected_theme = random.choice(self.THEMES)
            theme_id = selected_theme["id"]
            theme_name = selected_theme["name"]
        else:
            selected_theme = next((theme for theme in self.THEMES if theme["id"] == theme_id), None)
            if not selected_theme:
                print(f"Error: Theme ID {theme_id} not found in available themes")
                return False
            theme_name = selected_theme["name"]
        task_payload = {
            "thread_key": thread_id,
            "theme_fbid": theme_id,
            "source": None,
            "sync_group": 1,
            "payload": None,
        }
        task = {
            "failure_count": None,
            "label": "43",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": "thread_theme",
            "task_id": self.ws_task_number,
        }
        content = {
            "app_id": "2220391788200892",
            "payload": json.dumps({
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [task],
                "version_id": "25095469420099952",
            }, separators=(",", ":")),
            "request_id": self.ws_req_number,
            "type": 3,
        }
        if callback is not None and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            print(f"[✓] Đã thay đổi theme thành: {theme_name} (ID: {theme_id}) cho box {thread_id}")
            return True
        except Exception as e:
            print(f"Error Publishing Theme Change: {e}")
            return False
        
    def cleanup_memory(self):
        current_time = time.time()
        if current_time - self.last_cleanup > 3600:
            self.req_callbacks.clear()
            gc.collect()
            self.last_cleanup = current_time

    def get_last_seq_id(self):
        success = self.fbt.getAllThreadList()
        if success:
            self.lastSeqID = self.fbt.last_seq_id
        else:
            print("Failed To Get Last Sequence ID. Check Facebook Authentication.")
            return

    def on_disconnect(self, client, userdata, rc):
        global cookie_attempts
        print(f"Disconnected With Code {rc}")
        cookie_attempts[self.cookie_hash]['count'] += 1
        current_time = time.time()
        if current_time - cookie_attempts[self.cookie_hash]['last_reset'] > 43200:
            cookie_attempts[self.cookie_hash]['count'] = 1
            cookie_attempts[self.cookie_hash]['last_reset'] = current_time
        if cookie_attempts[self.cookie_hash]['count'] >= 20:
            print(f"Cookie {self.cookie_hash[:10]} Bị Tạm Ngưng Connect Trong 12 Giờ Vì Disconnect, Nghi Vấn: Die Cookies, Check Point")
            cookie_attempts[self.cookie_hash]['banned_until'] = current_time + 43200
            return
        if rc != 0:
            print("Attempting To Reconnect...")
            try:
                time.sleep(min(cookie_attempts[self.cookie_hash]['count'] * 2, 30))
                client.reconnect()
            except:
                print("Reconnect Failed")

    def _messenger_queue_publish(self, client, userdata, flags, rc):
        print(f"Connected To MQTT With Code: {rc}")
        if rc != 0:
            print(f"Connection Failed With Code {rc}")
            return
        topics = [("/t_ms", 0)]
        client.subscribe(topics)
        queue = {
            "sync_api_version": 10,
            "max_deltas_able_to_process": 1000,
            "delta_batch_size": 500,
            "encoding": "JSON",
            "entity_fbid": self.dataFB['FacebookID']
        }
        if self.syncToken is None:
            topic = "/messenger_sync_create_queue"
            queue["initial_titan_sequence_id"] = self.lastSeqID
            queue["device_params"] = None
        else:
            topic = "/messenger_sync_get_diffs"
            queue["last_seq_id"] = self.lastSeqID
            queue["sync_token"] = self.syncToken
        print(f"Publishing To {topic}")
        client.publish(
            topic,
            json_minimal(queue),
            qos=1,
            retain=False,
        )

    def connect_mqtt(self):
        global cookie_attempts
        if cookie_attempts[self.cookie_hash].get('permanent_ban', False):
            print(f"Cookie {self.cookie_hash[:10]} Đã Bị Ngưng Connect Vĩnh Viễn, Lí Do: Die Cookies, Check Point v.v")
            return False
        current_time = time.time()
        if current_time < cookie_attempts[self.cookie_hash].get('banned_until', 0):
            remaining = cookie_attempts[self.cookie_hash]['banned_until'] - current_time
            print(f"Cookie {self.cookie_hash[:10]} Bị Tạm Khóa, Còn {remaining/3600:.1f} Giờ")
            return False
        if not self.lastSeqID:
            print("Error: No last_seq_id Available. Cannot Connect To MQTT.")
            return False
        chat_on = json_minimal(True)
        session_id = generate_session_id()
        user = {
            "u": self.dataFB["FacebookID"],
            "s": session_id,
            "chat_on": chat_on,
            "fg": False,
            "d": generate_client_id(),
            "ct": "websocket",
            "aid": 219994525426954,
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": ["/t_ms", "/messenger_sync_get_diffs", "/messenger_sync_create_queue"],
            "pm": [],
            "dc": "",
            "no_auto_fg": True,
            "gas": None,
            "pack": [],
        }
        host = f"wss://edge-chat.messenger.com/chat?region=eag&sid={session_id}"
        options = {
            "client_id": "mqttwsclient",
            "username": json_minimal(user),
            "clean": True,
            "ws_options": {
                "headers": {
                    "Cookie": self.dataFB['cookieFacebook'],
                    "Origin": "https://www.messenger.com",
                    "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
                    "Referer": "https://www.messenger.com/",
                    "Host": "edge-chat.messenger.com",
                },
            },
            "keepalive": 10,
        }
        try:
            self.mqtt = mqtt.Client(
                client_id="mqttwsclient",
                clean_session=True,
                protocol=mqtt.MQTTv31,
                transport="websockets",
            )
            self.mqtt.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
            self.mqtt.on_connect = self._messenger_queue_publish
            self.mqtt.on_disconnect = self.on_disconnect
            self.mqtt.username_pw_set(username=options["username"])
            parsed_host = urlparse(host)
            self.mqtt.ws_set_options(
                path=f"{parsed_host.path}?{parsed_host.query}",
                headers=options["ws_options"]["headers"],
            )
            print(f"Connecting To {options['ws_options']['headers']['Host']}...")
            self.mqtt.connect(
                host=options["ws_options"]["headers"]["Host"],
                port=443,
                keepalive=options["keepalive"],
            )
            print("MQTT Connection Established")
            self.mqtt.loop_start()
            return True
        except Exception as e:
            print(f"MQTT Connection Error: {e}")
            cookie_attempts[self.cookie_hash]['count'] += 1
            return False

    def stop(self):
        if self.mqtt:
            print("Stopping MQTT Client...")
            try:
                self.mqtt.disconnect()
                self.mqtt.loop_stop()
            except:
                pass
        self.cleanup_memory()

    def sendTypingIndicatorMqtt(self, isTyping, thread_id, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        label = '3'
        is_group_thread = 1
        attribution = 0
        task_payload = {
            "thread_key": thread_id,
            "is_group_thread": is_group_thread,
            "is_typing": 1 if isTyping else 0,
            "attribution": attribution,
        }
        content = {
            "app_id": "2220391788200892",
            "payload": json.dumps({
                "label": label,
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "version": "25393437286970779",
            }, separators=(",", ":")),
            "request_id": self.ws_req_number,
            "type": 4,
        }
        if callback is not None and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
        except Exception as e:
            print(f"Error Publishing Typing Indicator: {e}")
            return False

    def createPollMqtt(self, title, options, thread_id, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        self.ws_task_number += 1
        task_payload = {
            "question_text": title,
            "thread_key": thread_id,
            "options": options,
            "sync_group": 1,
        }
        task = {
            "failure_count": None,
            "label": "163",
            "payload": json.dumps(task_payload, separators=(",", ":")),
            "queue_name": "poll_creation",
            "task_id": self.ws_task_number,
        }
        content = {
            "app_id": "2220391788200892",
            "payload": json.dumps({
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [task],
                "version_id": "7158486590867448",
            }, separators=(",", ":")),
            "request_id": self.ws_req_number,
            "type": 3,
        }
        if callback is not None and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
        except Exception as e:
            print(f"Error Publishing Poll Creation: {e}")
            return False

    def send_message(self, text=None, thread_id=None, attachment=None, mention=None, message_id=None, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        if thread_id is None:
            print("Error: Thread ID Is Required")
            return False
        if text is None and attachment is None:
            print("Error: Text Or Attachment Is Required")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        content = {
            "app_id": "2220391788200892",
            "payload": {
                "data_trace_id": None,
                "epoch_id": int(generate_offline_threading_id()),
                "tasks": [],
                "version_id": "7545284305482586",
            },
            "request_id": self.ws_req_number,
            "type": 3,
        }
        text = str(text) if text is not None else ""
        if len(text) > 0:
            self.ws_task_number += 1
            task_payload = {
                "initiating_source": 0,
                "multitab_env": 0,
                "otid": generate_offline_threading_id(),
                "send_type": 1,
                "skip_url_preview_gen": 0,
                "source": 0,
                "sync_group": 1,
                "text": text,
                "text_has_links": 0,
                "thread_id": int(thread_id),
            }
            if message_id is not None:
                if not isinstance(message_id, str):
                    raise ValueError("message_id must be a string")
                task_payload["reply_metadata"] = {
                    "reply_source_id": message_id,
                    "reply_source_type": 1,
                    "reply_type": 0,
                }
            task = {
                "failure_count": None,
                "label": "46",
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "queue_name": str(thread_id),
                "task_id": self.ws_task_number,
            }
            content["payload"]["tasks"].append(task)
        self.ws_task_number += 1
        task_mark_payload = {
            "last_read_watermark_ts": int(time.time() * 1000),
            "sync_group": 1,
            "thread_id": int(thread_id),
        }
        task_mark = {
            "failure_count": None,
            "label": "21",
            "payload": json.dumps(task_mark_payload, separators=(",", ":")),
            "queue_name": str(thread_id),
            "task_id": self.ws_task_number,
        }
        content["payload"]["tasks"].append(task_mark)
        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
        if callback is not None and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
        except Exception as e:
            print(f"Error Publishing Message: {e}")
            return False

    def send_message_with_attachment(self, text, thread_id, file_path_or_url, message_id=None, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        if thread_id is None:
            print("Error: Thread ID Is Required")
            return False
        try:
            if file_path_or_url.startswith(('http://', 'https://')):
                file_info = self.download_and_upload_file(file_path_or_url)
            else:
                file_info = self.upload_file(file_path_or_url)
            if not file_info:
                print("Failed To Upload File")
                return False
            self.cleanup_memory()
            self.ws_req_number += 1
            content = {
                "app_id": "2220391788200892",
                "payload": {
                    "data_trace_id": None,
                    "epoch_id": int(generate_offline_threading_id()),
                    "tasks": [],
                    "version_id": "7545284305482586",
                },
                "request_id": self.ws_req_number,
                "type": 3,
            }
            self.ws_task_number += 1
            task_payload = {
                "attachment_fbids": [file_info["id"]],
                "initiating_source": 0,
                "multitab_env": 0,
                "otid": generate_offline_threading_id(),
                "send_type": 3,
                "skip_url_preview_gen": 0,
                "source": 0,
                "sync_group": 1,
                "text": text,
                "text_has_links": 0,
                "thread_id": int(thread_id),
            }
            if message_id is not None:
                if not isinstance(message_id, str):
                    raise ValueError("message_id must be a string")
                task_payload["reply_metadata"] = {
                    "reply_source_id": message_id,
                    "reply_source_type": 1,
                    "reply_type": 0,
                }
            task = {
                "failure_count": None,
                "label": "46",
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "queue_name": str(thread_id),
                "task_id": self.ws_task_number,
            }
            content["payload"]["tasks"].append(task)
            self.ws_task_number += 1
            task_mark_payload = {
                "last_read_watermark_ts": int(time.time() * 1000),
                "sync_group": 1,
                "thread_id": int(thread_id),
            }
            task_mark = {
                "failure_count": None,
                "label": "21",
                "payload": json.dumps(task_mark_payload, separators=(",", ":")),
                "queue_name": str(thread_id),
                "task_id": self.ws_task_number,
            }
            content["payload"]["tasks"].append(task_mark)
            content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
            if callback is not None and callable(callback):
                self.req_callbacks[self.ws_req_number] = callback
            try:
                self.mqtt.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                return True
            except Exception as e:
                print(f"Error Publishing Message: {e}")
                return False
        except Exception as e:
            print(f"Error Sending Message With Attachment: {e}")
            return False

    def share_contact(self, text=None, sender_id=None, thread_id=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        if sender_id is None:
            print("Error: Sender ID Is Required")
            return False
        if thread_id is None:
            print("Error: Thread ID Is Required")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        self.ws_task_number += 1
        content = {
            "app_id": "2220391788200892",
            "payload": {
                "tasks": [{
                    "label": 359,
                    "payload": json.dumps({
                        "contact_id": sender_id,
                        "sync_group": 1,
                        "text": text or "",
                        "thread_id": thread_id
                    }, separators=(",", ":")),
                    "queue_name": "xma_open_contact_share",
                    "task_id": self.ws_task_number,
                    "failure_count": None,
                }],
                "epoch_id": generate_offline_threading_id(),
                "version_id": "7214102258676893",
            },
            "request_id": self.ws_req_number,
            "type": 3
        }
        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
        except Exception as e:
            print(f"Error Publishing Contact Share: {e}")
            return False

    def share_link(self, text=None, url=None, thread_id=None, callback=None):
        if self.mqtt is None:
            print("Error: Not Connected To MQTT")
            return False
        if thread_id is None:
            print("Error: Thread ID Is Required")
            return False
        self.cleanup_memory()
        self.ws_req_number += 1
        self.ws_task_number += 1
        content = {
            "app_id": "2220391788200892",
            "payload": {
                "tasks": [{
                    "label": 46,
                    "payload": json.dumps({
                        "otid": generate_offline_threading_id(),
                        "source": 524289,
                        "sync_group": 1,
                        "send_type": 6,
                        "mark_thread_read": 0,
                        "url": url or "https://www.facebook.com",
                        "text": text or "",
                        "thread_id": thread_id,
                        "initiating_source": 0
                    }, separators=(",", ":")),
                    "queue_name": str(thread_id),
                    "task_id": self.ws_task_number,
                    "failure_count": None,
                }],
                "epoch_id": generate_offline_threading_id(),
                "version_id": "7191105584331330",
            },
            "request_id": self.ws_req_number,
            "type": 3
        }
        content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
        if callback is not None and callable(callback):
            self.req_callbacks[self.ws_req_number] = callback
        try:
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
        except Exception as e:
            print(f"Error Publishing Link Share: {e}")
            return False

    def upload_file(self, file_path):
        user_id = self.fb_instance.user_id
        url = "https://www.facebook.com/ajax/mercury/upload.php"
        headers = {
            'Cookie': self.dataFB['cookieFacebook'],
            'User-Agent': 'python-http/0.27.0',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/'
        }
        params = {
            'ads_manager_write_regions': 'true',
            '__aaid': '0',
            '__user': user_id,
            '__a': '1',
            '__hs': '20207.HYP:comet_pkg.2.1...0',
            'dpr': '3',
            '__ccg': 'GOOD',
            '__rev': '1022311521',
            'fb_dtsg': self.dataFB['fb_dtsg'],
            'jazoest': self.dataFB['jazoest'],
            '__crn': 'comet.fbweb.CometHomeRoute'
        }
        mime_type = 'image/jpeg'
        if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
            mime_type = 'video/mp4'
        with open(file_path, 'rb') as file:
            files = {'farr': (file_path.split('/')[-1], file, mime_type)}
            response = requests.post(url, headers=headers, params=params, files=files)
        if response.status_code == 200:
            content = response.text.replace('for (;;);', '')
            try:
                data = json.loads(content)
                if 'payload' in data and 'metadata' in data['payload'] and '0' in data['payload']['metadata']:
                    metadata = data['payload']['metadata']['0']
                    if mime_type.startswith('video'):
                        file_id = metadata.get('video_id')
                        return {'id': file_id, 'type': 'video'}
                    else:
                        file_id = metadata.get('fbid') or metadata.get('image_id')
                        return {'id': file_id, 'type': 'image'}
                else:
                    with open('response_debug.json', 'w', encoding='utf-8') as f:
                        f.write(content)
                    raise Exception(f"JSON Structure Not As Expected. Response Saved To response_debug.json")
            except json.JSONDecodeError:
                raise Exception(f"Cannot Parse JSON From Response: {response.text}")
        else:
            raise Exception(f"Error Uploading File: {response.status_code}")

    def download_and_upload_file(self, file_url):
        user_id = self.fb_instance.user_id
        url = "https://www.facebook.com/ajax/mercury/upload.php"
        headers = {
            'Cookie': self.dataFB['cookieFacebook'],
            'User-Agent': 'python-http/0.27.0',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/'
        }
        params = {
            'ads_manager_write_regions': 'true',
            '__aaid': '0',
            '__user': user_id,
            '__a': '1',
            '__hs': '20207.HYP:comet_pkg.2.1...0',
            'dpr': '3',
            '__ccg': 'GOOD',
            '__rev': '1022311521',
            'fb_dtsg': self.dataFB['fb_dtsg'],
            'jazoest': self.dataFB['jazoest'],
            '__crn': 'comet.fbweb.CometHomeRoute'
        }
        mime_type = 'image/jpeg'
        if file_url.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
            mime_type = 'video/mp4'
        elif file_url.lower().endswith(('.png', '.gif')):
            mime_type = f'image/{file_url.split(".")[-1].lower()}'
        try:
            response = requests.get(file_url, stream=True, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Không thể tải file từ URL: {response.status_code}")
            file_name = file_url.split('/')[-1] or f"temp_{int(time.time())}.{mime_type.split('/')[-1]}"
            files = {'farr': (file_name, response.content, mime_type)}
            upload_response = requests.post(url, headers=headers, params=params, files=files)
            if upload_response.status_code == 200:
                content = upload_response.text.replace('for (;;);', '')
                try:
                    data = json.loads(content)
                    if 'payload' in data and 'metadata' in data['payload'] and '0' in data['payload']['metadata']:
                        metadata = data['payload']['metadata']['0']
                        if mime_type.startswith('video'):
                            file_id = metadata.get('video_id')
                            return {'id': file_id, 'type': 'video'}
                        else:
                            file_id = metadata.get('fbid') or metadata.get('image_id')
                            return {'id': file_id, 'type': 'image'}
                    else:
                        with open('response_debug.json', 'w', encoding='utf-8') as f:
                            f.write(content)
                        raise Exception(f"Cấu trúc JSON không như mong đợi. Phản hồi đã lưu vào response_debug.json")
                except json.JSONDecodeError:
                    raise Exception(f"Không thể phân tích JSON từ phản hồi: {upload_response.text}")
            else:
                raise Exception(f"Lỗi khi tải file lên: {upload_response.status_code}")
        except Exception as e:
            print(f"Lỗi khi tải hoặc gửi file từ URL {file_url}: {e}")
            return None

class ngquanghuyakadzi:
    def __init__(self, cookie, mqtt_broker="broker.hivemq.com", mqtt_port=1883):
        self.cookie = cookie
        self.user_id = self.id_user()
        self.fb_dtsg = None
        self.jazoest = None
        self.rev = None
        self.init_params()
        self.mqtt_client = mqtt.Client(
            client_id=f"messenger_{self.user_id}_{int(time.time())}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic_base = "messenger/spam"

    def id_user(self):
        try:
            match = re.search(r"c_user=(\d+)", self.cookie)
            if not match:
                raise Exception("Cookie không hợp lệ")
            return match.group(1)
        except Exception as e:
            raise Exception(f"Lỗi khi lấy user_id: {str(e)}")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        urls = [
            'https://www.facebook.com',
            'https://mbasic.facebook.com',
            'https://m.facebook.com'
        ]
        for url in urls:
            try:
                print(f"[*] Thử lấy fb_dtsg từ {url}")
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"[❌] Yêu cầu tới {url} thất bại, mã trạng thái: {response.status_code}")
                    continue
                fb_dtsg_patterns = [
                    r'"token":"(.*?)"',
                    r'name="fb_dtsg" value="(.*?)"',
                    r'"fb_dtsg":"(.*?)"',
                    r'fb_dtsg=([^&"]+)'
                ]
                jazoest_pattern = r'name="jazoest" value="(\d+)"'
                rev_pattern = r'"__rev":"(\d+)"'
                fb_dtsg = None
                for pattern in fb_dtsg_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        fb_dtsg = match.group(1)
                        break
                jazoest_match = re.search(jazoest_pattern, response.text)
                rev_match = re.search(rev_pattern, response.text)
                if fb_dtsg:
                    self.fb_dtsg = fb_dtsg
                    self.jazoest = jazoest_match.group(1) if jazoest_match else "22036"
                    self.rev = rev_match.group(1) if rev_match else "1015919737"
                    print(f"[✓] Lấy được fb_dtsg: {self.fb_dtsg[:20]}..., jazoest: {self.jazoest}, rev: {self.rev}")
                    return
                else:
                    print(f"[⚠] Không tìm thấy fb_dtsg trong {url}")
            except Exception as e:
                print(f"[❌] Lỗi khi truy cập {url}: {str(e)}")
                time.sleep(2)
        raise Exception("Không thể lấy được fb_dtsg từ bất kỳ URL nào")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[✓] Kết nối MQTT broker: {self.mqtt_broker}")
            client.subscribe(f"{self.mqtt_topic_base}/#", qos=1)
            print(f"[✓] Subscribe topic: {self.mqtt_topic_base}/#")
        else:
            print(f"[❌] Kết nối MQTT thất bại, mã lỗi: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"[📩] Nhận từ {topic}: {payload[:100]}")
            recipient_id = topic.split('/')[-1]
            message = json.loads(payload).get('message', '')
            if not message:
                print("[!] Nội dung rỗng, bỏ qua.")
                return
            result = self.gui_tn(recipient_id, message)
            if result.get('success'):
                print(f"[✓] Gửi thành công tới {recipient_id}")
            else:
                print(f"[×] Gửi thất bại tới {recipient_id}")
        except Exception as e:
            print(f"[!] Lỗi xử lý MQTT: {str(e)}")

    def gui_tn(self, recipient_id, message):
        if not self.fb_dtsg or not self.jazoest or not self.rev:
            self.init_params()
        timestamp = int(time.time() * 1000)
        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': str(timestamp),
            'message_id': str(timestamp),
            'ephemeral_ttl_mode': '',
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            '__rev': self.rev,
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.jazoest
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.facebook.com',
            'Referer': f'https://www.facebook.com/messages/t/{recipient_id}',
            'Cookie': self.cookie
        }
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"[❌] Gửi thất bại. Status: {response.status_code}")
                return {'success': False}
            if 'for (;;);' in response.text:
                json_data = json.loads(response.text.replace('for (;;);', ''))
                if 'error' in json_data:
                    print(f"[❌] Lỗi từ Facebook: {json_data.get('errorDescription', 'Unknown error')}")
                    return {'success': False}
            print("[✅] Gửi tin nhắn thành công.")
            return {'success': True}
        except Exception as e:
            print(f"[❌] Lỗi khi gửi: {str(e)}")
            return {'success': False}

def send_messages_with_cookie(cookies, thread_ids, message_files, delay, option=0, file_path=None, contact_uid=None, name_file=None, nickname=None):
    global cookie_attempts, active_threads
    for cookie in cookies:
        cookie_hash = hashlib.md5(cookie.encode()).hexdigest()
        if cookie_attempts[cookie_hash].get('permanent_ban', False):
            print(f"Cookie {cookie_hash[:10]} Đã Bị Ngưng Hoạt Động Vĩnh Viễn\nLí Do: Cookies Die, CheckPoint V.V")
            continue
        current_time = time.time()
        if current_time < cookie_attempts[cookie_hash].get('banned_until', 0):
            remaining = cookie_attempts[cookie_hash]['banned_until'] - current_time
            print(f"Cookie {cookie_hash[:10]} Bị Tạm Khóa, Còn {remaining/3600:.1f} Giờ\nLí Do: Checkpoint, Mõm, Cookies Die")
            continue
        try:
            fb = ngquanghuyakadzi(cookie)
            sender = MessageSender(fbTools({
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }), {
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }, fb)
            if option not in [4, 10]:
                sender.get_last_seq_id()
                if not sender.connect_mqtt():
                    handle_failed_connection(cookie_hash)
                    continue
            for thread_id in thread_ids:
                print(f"Bắt Đầu Xử Lý Cho Box: {thread_id} với Cookie: {cookie_hash[:10]}")
                active_threads[f"{cookie_hash}_{thread_id}"] = sender
                try:
                    if option == 4:
                        if not name_file:
                            print("[!] Chưa cung cấp file chứa tên nhóm (nhay.txt)")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            group_names = [line.strip() for line in f if line.strip()]
                        if not group_names:
                            print("[!] File nhay.txt không có nội dung!")
                            break
                        while True:
                            for group_name in group_names:
                                success, log = tenbox(group_name, thread_id, {
                                    "FacebookID": fb.user_id,
                                    "fb_dtsg": fb.fb_dtsg,
                                    "clientRevision": fb.rev,
                                    "jazoest": fb.jazoest,
                                    "cookieFacebook": cookie
                                })
                                print(log)
                                time.sleep(delay)
                                if time.time() - sender.last_cleanup > 600:
                                    gc.collect()
                    elif option == 7:
                        if not name_file:
                            print("[!] Chưa cung cấp file chứa tiêu đề poll (nhay.txt)")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            poll_titles = [line.strip() for line in f if line.strip()]
                        if not poll_titles:
                            print("[!] File nhay.txt không có nội dung!")
                            break
                        while True:
                            for title in poll_titles:
                                titles = title.split(',') if ',' in title else [title]
                                for single_title in titles:
                                    single_title = single_title.strip()
                                    if not single_title:
                                        continue
                                    options = ["Kael king treo việt nam", "cha kael bá rõ 🤪🤙❤️"]
                                    print(f"[*] Tạo poll với tiêu đề: {single_title} trong box {thread_id}")
                                    success = sender.createPollMqtt(single_title, options, thread_id)
                                    if success:
                                        print(f"[✓] Đã tạo poll với tiêu đề: {single_title} trong box {thread_id}")
                                    else:
                                        print(f"[❌] Tạo poll thất bại với tiêu đề: {single_title} trong box {thread_id}")
                                    time.sleep(delay)
                                if time.time() - sender.last_cleanup > 600:
                                    gc.collect()
                    elif option == 8:
                        if not name_file:
                            print("[!] Chưa cung cấp file chứa nội dung tin nhắn (nhay.txt)")
                            break
                        with open(name_file, 'r', encoding='utf-8') as f:
                            messages = [line.strip() for line in f if line.strip()]
                        if not messages:
                            print("[!] File nhay.txt không có nội dung!")
                            break
                        while True:
                            for message in messages:
                                if not message:
                                    continue
                                print(f"[*] Gửi chỉ báo đang gõ cho box {thread_id}")
                                success = sender.sendTypingIndicatorMqtt(True, thread_id)
                                if success:
                                    print(f"[✓] Đã gửi chỉ báo đang gõ cho box {thread_id}")
                                else:
                                    print(f"[❌] Gửi chỉ báo đang gõ thất bại cho box {thread_id}")
                                    continue
                                typing_duration = random.uniform(1, 3)
                                time.sleep(typing_duration)
                                print(f"[*] Gửi tin nhắn: {message} tới box {thread_id}")
                                success = sender.send_message(message, thread_id)
                                if success:
                                    print(f"[✓] Đã gửi tin nhắn tới box {thread_id}")
                                else:
                                    print(f"[❌] Gửi tin nhắn thất bại tới box {thread_id}")
                                success = sender.sendTypingIndicatorMqtt(False, thread_id)
                                if success:
                                    print(f"[✓] Đã tắt chỉ báo đang gõ cho box {thread_id}")
                                else:
                                    print(f"[❌] Tắt chỉ báo đang gõ thất bại cho box {thread_id}")
                                time.sleep(delay)
                                if time.time() - sender.last_cleanup > 600:
                                    gc.collect()
                    elif option == 9:
                        themes = sender.THEMES
                        if not themes:
                            print("[!] Danh sách theme rỗng!")
                            break
                        theme_index = 0
                        while True:
                            theme = themes[theme_index % len(themes)]
                            theme_id = theme["id"]
                            theme_name = theme["name"]
                            print(f"[*] Thay đổi theme với ID: {theme_id} ({theme_name}) cho box {thread_id}")
                            success = sender.set_theme(theme_id, thread_id)
                            if success:
                                print(f"[✓] Đã thay đổi theme thành: {theme_name} (ID: {theme_id}) cho box {thread_id}")
                            else:
                                print(f"[❌] Thay đổi theme thất bại cho box {thread_id}")
                            theme_index += 1
                            time.sleep(delay)
                            if time.time() - sender.last_cleanup > 600:
                                gc.collect()
                    elif option == 10:
                        while True:
                            print("\n" + "="*50)
                            print(f"[*] Chu kỳ đổi biệt danh mới cho box {thread_id}")
                            print("="*50)
                            nickname_input = nickname or input("[+] Nhập biệt danh muốn đặt cho tất cả thành viên (nhấn Enter để dừng):\n> ").strip()
                            if not nickname_input:
                                print("[*] Không nhập biệt danh, dừng chế độ đổi biệt danh cho box này.")
                                break
                            success, participant_ids, log = get_thread_info_graphql(thread_id, {
                                "FacebookID": fb.user_id,
                                "fb_dtsg": fb.fb_dtsg,
                                "clientRevision": fb.rev,
                                "jazoest": fb.jazoest,
                                "cookieFacebook": cookie
                            })
                            print(log)
                            if not success:
                                break
                            for participant_id in participant_ids:
                                success, log = change_nickname(nickname_input, thread_id, participant_id, {
                                    "FacebookID": fb.user_id,
                                    "fb_dtsg": fb.fb_dtsg,
                                    "clientRevision": fb.rev,
                                    "jazoest": fb.jazoest,
                                    "cookieFacebook": cookie
                                })
                                print(log)
                                time.sleep(delay)
                            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Đã hoàn tất đổi biệt danh cho tất cả thành viên trong box {thread_id}")
                    else:
                        while True:
                            content = ""
                            if message_files:
                                if len(message_files) > 1:
                                    selected = random.choice(message_files)
                                else:
                                    selected = message_files[0]
                                with open(selected, 'r', encoding='utf-8') as f:
                                    content = f.read().strip()
                            if option == 2:
                                uid_to_share = contact_uid or fb.user_id
                                sender.share_contact(content, uid_to_share, thread_id)
                            elif option == 3:
                                uid_to_share = contact_uid or fb.user_id
                                share_url = f"https://www.facebook.com/{uid_to_share}"
                                sender.share_link(content, share_url, thread_id)
                            elif option == 5:
                                if not file_path:
                                    print("[!] Chưa cung cấp URL ảnh/video")
                                    break
                                print(f"[*] Gửi ảnh/video từ URL: {file_path} tới box {thread_id}")
                                success = sender.send_message_with_attachment(content, thread_id, file_path)
                                if success:
                                    print(f"[✓] Đã gửi ảnh/video tới box {thread_id}")
                                else:
                                    print(f"[❌] Gửi ảnh/video thất bại tới box {thread_id}")
                            else:
                                sender.send_message(content, thread_id)
                            time.sleep(delay)
                            if time.time() - sender.last_cleanup > 600:
                                gc.collect()
                except KeyboardInterrupt:
                    print(f"\nDừng Xử Lý Cho Box: {thread_id}")
                    break
                finally:
                    if option not in [4, 10]:
                        sender.stop()
                    if f"{cookie_hash}_{thread_id}" in active_threads:
                        del active_threads[f"{cookie_hash}_{thread_id}"]
        except Exception as e:
            print(f"Lỗi Trong Luồng Xử Lý Với Cookie {cookie_hash[:10]}: {e}")
            handle_failed_connection(cookie_hash)
            continue
    return True

def input_with_done(prompt):
    items = []
    print(prompt)
    print("(Nhập 'done' để kết thúc nhập)")
    while True:
        item = input("> ").strip()
        if item.lower() == 'done':
            break
        if item:
            items.append(item)
    return items

def input_single_with_done(prompt):
    print(prompt)
    print("(Nhập 'done' để bỏ qua)")
    item = input("> ").strip()
    if item.lower() == 'done':
        return None
    return item

class FacebookThreadExtractor:
    def __init__(self, cookie):
        self.cookie = cookie
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        ]
        self.facebook_tokens = {}

    def get_facebook_tokens(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        sites = ['https://www.facebook.com', 'https://mbasic.facebook.com']
        for site in sites:
            try:
                response = self.session.get(site, headers=headers, timeout=10)
                c_user_match = re.search(r"c_user=(\d+)", self.cookie)
                if c_user_match:
                    self.facebook_tokens["FacebookID"] = c_user_match.group(1)
                fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text) or re.search(
                    r'name="fb_dtsg" value="(.*?)"', response.text)
                if fb_dtsg_match:
                    self.facebook_tokens["fb_dtsg"] = fb_dtsg_match.group(1)
                jazoest_match = re.search(r'jazoest=(\d+)', response.text)
                if jazoest_match:
                    self.facebook_tokens["jazoest"] = jazoest_match.group(1)
                if self.facebook_tokens.get("fb_dtsg") and self.facebook_tokens.get("jazoest"):
                    break
            except Exception:
                continue
        self.facebook_tokens.update({
            "__rev": "1015919737",
            "__req": "1b",
            "__a": "1",
            "__comet_req": "15"
        })
        return len(self.facebook_tokens) > 4

    def get_thread_list(self, limit=100):
        if not self.get_facebook_tokens():
            return {"error": "Không thể lấy token từ Facebook. Kiểm tra lại cookie."}
        form_data = {
            "av": self.facebook_tokens.get("FacebookID", ""),
            "__user": self.facebook_tokens.get("FacebookID", ""),
            "__a": self.facebook_tokens["__a"],
            "__req": self.facebook_tokens["__req"],
            "__hs": "19234.HYP:comet_pkg.2.1..2.1",
            "dpr": "1",
            "__ccg": "EXCELLENT",
            "__rev": self.facebook_tokens["__rev"],
            "__comet_req": self.facebook_tokens["__comet_req"],
            "fb_dtsg": self.facebook_tokens.get("fb_dtsg", ""),
            "jazoest": self.facebook_tokens.get("jazoest", ""),
            "lsd": "null",
            "__spin_r": self.facebook_tokens.get("client_revision", ""),
            "__spin_b": "trunk",
            "__spin_t": str(int(time.time())),
        }
        queries = {
            "o0": {
                "doc_id": "3336396659757871",
                "query_params": {
                    "limit": limit,
                    "before": None,
                    "tags": ["INBOX"],
                    "includeDeliveryReceipts": False,
                    "includeSeqID": True,
                }
            }
        }
        form_data["queries"] = json.dumps(queries)
        headers = {
            'Cookie': self.cookie,
            'User-Agent': random.choice(self.user_agents),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Origin': 'https://www.facebook.com',
            'Referer': 'https://www.facebook.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-FB-Friendly-Name': 'MessengerThreadListQuery',
            'X-FB-LSD': 'null'
        }
        try:
            response = self.session.post(
                'https://www.facebook.com/api/graphqlbatch/',
                data=form_data,
                headers=headers,
                timeout=15
            )
            if response.status_code != 200:
                return {"error": f"HTTP Error: {response.status_code}"}
            response_text = response.text.split('{"successful_results"')[0]
            data = json.loads(response_text)
            if "o0" not in data:
                return {"error": "Không tìm thấy dữ liệu thread list"}
            if "errors" in data["o0"]:
                return {"error": f"Facebook API Error: {data['o0']['errors'][0]['summary']}"}
            threads = data["o0"]["data"]["viewer"]["message_threads"]["nodes"]
            thread_list = []
            for thread in threads:
                if not thread.get("thread_key") or not thread["thread_key"].get("thread_fbid"):
                    continue
                thread_list.append({
                    "thread_id": thread["thread_key"]["thread_fbid"],
                    "thread_name": thread.get("name", "Không có tên")
                })
            return {
                "success": True,
                "thread_count": len(thread_list),
                "threads": thread_list
            }
        except json.JSONDecodeError as e:
            return {"error": f"Lỗi parse JSON: {str(e)}"}
        except Exception as e:
            return {"error": f"Lỗi không xác định: {str(e)}"}

def select_boxes_interactive(cookie, limit=50):
    print(f"\n{Fore.CYAN}Đang lấy danh sách box từ cookie...")
    extractor = FacebookThreadExtractor(cookie)
    result = extractor.get_thread_list(limit=limit)
    if "error" in result:
        print(f"{Fore.RED}❌ Lỗi: {result['error']}")
        return []
    threads = result["threads"]
    if not threads:
        print(f"{Fore.YELLOW}⚠️ Không tìm thấy box nào trong cookie này")
        return []
    print(f"{Fore.GREEN}✅ Đã lấy được {len(threads)} box")
    print(f"{Fore.CYAN}\n{'═' * 60}")
    print(f"{Fore.YELLOW}📦 DANH SÁCH BOX MESSENGER")
    print(f"{Fore.CYAN}{'═' * 60}")
    for idx, thread in enumerate(threads, 1):
        thread_id = thread["thread_id"]
        raw_name = thread.get("thread_name")
        if raw_name:
            thread_name = raw_name[:50] + "..." if len(raw_name) > 50 else raw_name
        else:
            thread_name = "Không có tên"
        print(f"{Fore.CYAN}[{idx}] {Fore.YELLOW}{thread_name}")
        print(f"{Fore.MAGENTA}   ID: {thread_id}")
        print(f"{Fore.CYAN}{'─' * 60}")
    print(f"{Fore.GREEN}\n👉 Nhập số thứ tự box cần chọn (cách nhau bằng dấu phẩy, ví dụ: 1,3,5)")
    print(f"{Fore.YELLOW}👉 Hoặc nhập 'all' để chọn tất cả box")
    print(f"{Fore.RED}👉 Nhập '0' để bỏ qua cookie này")
    choice = input(f"{Fore.CYAN}👉 Lựa chọn của bạn: ").strip()
    if choice.lower() == '0':
        print(f"{Fore.YELLOW}⏭️ Bỏ qua cookie này")
        return []
    if choice.lower() == 'all':
        selected_boxes = [thread["thread_id"] for thread in threads]
        print(f"{Fore.GREEN}✅ Đã chọn tất cả {len(selected_boxes)} box")
        return selected_boxes
    selected_boxes = []
    for num in choice.split(','):
        num = num.strip()
        if num.isdigit():
            idx = int(num) - 1
            if 0 <= idx < len(threads):
                selected_boxes.append(threads[idx]["thread_id"])
                print(f"{Fore.GREEN}✅ Đã chọn box {num}: {threads[idx].get('thread_name', 'Không có tên')[:30]}...")
            else:
                print(f"{Fore.RED}❌ Số {num} không hợp lệ")
    return selected_boxes
class KeySystem:
    KEYS = {
        "vipkeyhotwar": 9999,
        "KAELVIP24": 365,
        "MONTHVIP": 30,
        "WEEKVIP": 7,
        "TESTDAY": 1
    }
    
    @staticmethod
    def generate_random_key():
        days = random.randint(1, 30)
        key = f"RANDOM{random.randint(1000,9999)}_{days}DAYS"
        return key, days
    
    @staticmethod
    def validate_key(input_key):
        if input_key in KeySystem.KEYS:
            return True, f"✅ Key hợp lệ! Còn {KeySystem.KEYS[input_key]} ngày", KeySystem.KEYS[input_key]
        
        if input_key.startswith("RANDOM") and "_" in input_key:
            try:
                days = int(input_key.split("_")[1].replace("DAYS", ""))
                return True, f"✅ Key ngẫu nhiên hợp lệ! Còn {days} ngày", days
            except:
                pass
        
        return False, "❌ Key không hợp lệ", 0

def check_key_system():
    clr()
    ascii_art = pyfiglet.figlet_format("KAEL TOOL", font="slant")
    print(Fore.CYAN + ascii_art)
    print(Fore.YELLOW + "=" * 60)
    
    while True:
        print(Fore.CYAN + "1. Nhập key có sẵn")
        print("2. Nhận key ngẫu nhiên (1-30 ngày)")
        print("0. Thoát")
        
        choice = input(Fore.YELLOW + "Chọn: ").strip()
        
        if choice == "1":
            input_key = input(Fore.GREEN + "Nhập key: ").strip().upper()
            valid, message, days = KeySystem.validate_key(input_key)
            print(Fore.GREEN if valid else Fore.RED + message)
            
            if valid:
                time.sleep(2)
                return True
            else:
                time.sleep(2)
                
        elif choice == "2":
            key, days = KeySystem.generate_random_key()
            print(Fore.GREEN + f"Key của bạn: {key}")
            print(Fore.CYAN + f"Có hiệu lực: {days} ngày")
            
            input_key = input(Fore.GREEN + "Xác nhận nhập key trên: ").strip()
            if input_key == key:
                print(Fore.GREEN + "Kích hoạt thành công!")
                time.sleep(2)
                return True
            else:
                print(Fore.RED + "Key không khớp!")
                time.sleep(2)
                
        elif choice == "0":
            sys.exit(0)
        else:
            print(Fore.RED + "Lựa chọn không hợp lệ!")

if not check_key_system():
    sys.exit(1)

clr()

def get_fb_dtsg(cookie):
    try:
        headers={'Cookie':cookie,'User-Agent':'Mozilla/5.0'}
        res = requests.get('https://mbasic.facebook.com/profile.php', headers=headers, timeout=10)
        token = re.search(r'name="fb_dtsg" value="(.*?)"', res.text)
        return token.group(1) if token else None
    except:
        return None

def send_messenger(cookie, box_id, content):
    try:
        ts=int(time.time()*1000)
        m = re.search(r"c_user=(\d+)", cookie)
        user_id = m.group(1) if m else "0"
        fb_dtsg=get_fb_dtsg(cookie)
        data = {
            'thread_fbid': box_id,
            'action_type': 'ma-type:user-generated-message',
            'body': content,
            'client': 'mercury',
            'author': f'fbid:{user_id}',
            'timestamp': ts,
            'source': 'source:chat:web',
            'offline_threading_id': str(ts),
            'message_id': str(ts),
            '__user': user_id,
            'fb_dtsg': fb_dtsg
        }
        headers = {'Cookie':cookie,'User-Agent':'Mozilla/5.0'}
        res=requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=10)
        return res.status_code==200, res.text
    except Exception as e:
        return False, str(e)

def send_discord(token, channel_id, content):
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        data = {"content": content}
        r = requests.post(url, headers=headers, json=data, timeout=10)
        return r.status_code in (200, 201), r.text
    except Exception as e:
        return False, str(e)

def telegram_send(token, chat_id, content):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": content}
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

def send_gmail(email, password, to_email, subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email, password)
        server.sendmail(email, to_email, msg.as_string())
        server.quit()
        return True, "Gửi thành công"
    except Exception as e:
        return False, str(e)

def get_token(cookie):
    try:
        r = requests.get(f"https://adidaphat.site/facebook/tokentocookie?type=EAAD6V7&cookie={cookie}")
        return r.json().get("token")
    except: 
        return None

def save_config(mode,cfg):
    try:
        data = json.load(open("chnd.txt","r",encoding="utf-8")) if os.path.exists("chnd.txt") else {}
        data[mode]=cfg
        json.dump(data,open("chnd.txt","w",encoding="utf-8"),ensure_ascii=False,indent=2)
    except: 
        pass

def load_config(mode):
    try:
        if os.path.exists("chnd.txt"):
            return json.load(open("chnd.txt","r",encoding="utf-8")).get(mode,{})
        return {}
    except: 
        return {}

def start_treo_tab(cookie_or_auth, box_id, message, delay, app_name, task_type="Treo", silent=True):
    stop_event = threading.Event()
    def treo_worker():
        ok = 0
        fail = 0
        start_time = datetime.now()
        consecutive_fail = 0
        while not stop_event.is_set():
            try:
                success = False
                if app_name.lower() == "messenger":
                    success, _ = send_messenger(cookie_or_auth, box_id, message)
                elif app_name.lower() == "discord":
                    success, _ = send_discord(cookie_or_auth, box_id, message)
                elif app_name.lower() == "telegram":
                    success, _ = telegram_send(cookie_or_auth, box_id, message)
                else:
                    success = False
                if success:
                    ok += 1
                    consecutive_fail = 0
                else:
                    fail += 1
                    consecutive_fail += 1
                if consecutive_fail >= 5:
                    treo_tabs[threading.current_thread()]['status'] = "⚠️ Rớt (fail nhiều)"
                else:
                    treo_tabs[threading.current_thread()]['status'] = "🟢 Đang chạy"
            except Exception as e:
                fail += 1
                consecutive_fail += 1
                treo_tabs[threading.current_thread()]['status'] = f"⚠️ Lỗi: {str(e)[:50]}"
            uptime_seconds = int((datetime.now() - start_time).total_seconds())
            treo_tabs[threading.current_thread()].update({
                'ok': ok,
                'fail': fail,
                'uptime': uptime_seconds,
                'last_update': datetime.now().strftime("%H:%M:%S %d-%m-%Y")
            })
            for _ in range(max(1, int(delay*10))):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
        info = treo_tabs.get(threading.current_thread(), {}).copy()
        info['stopped_at'] = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        info['total_runtime'] = int((datetime.now() - start_time).total_seconds())
        treo_history.append(info)
    t = threading.Thread(target=treo_worker, daemon=True)
    treo_tabs[t] = {
        'app': app_name,
        'type': task_type,
        'box_id': box_id,
        'start_time': datetime.now(),
        'ok': 0,
        'fail': 0,
        'uptime': 0,
        'stop_event': stop_event,
        'status': "🟢 Đang khởi động",
        'last_update': datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    }
    t.start()
    if not silent:
        current_time = datetime.now().strftime("%H:%M:%S")
        print(Fore.GREEN + f"[{current_time}] [+] Đã khởi chạy {task_type} {app_name} cho box {box_id}")
    return t

def start_task(app_name, task_type, auth_data, box_id, send_func, messages, delay, silent=True):
    stop_event = threading.Event()
    def worker_wrapper():
        ok = 0
        fail = 0
        start_time = datetime.now()
        consecutive_fail = 0
        message_index = 0
        while not stop_event.is_set():
            try:
                if task_type == "Nhây" or task_type == "Reo" or task_type == "Nhây Tag":
                    if message_index >= len(messages):
                        message_index = 0
                    current_message = messages[message_index]
                    message_index += 1
                    success, _ = send_func(auth_data, box_id, current_message)
                    if success:
                        ok += 1
                        consecutive_fail = 0
                    else:
                        fail += 1
                        consecutive_fail += 1
                else:
                    success, _ = send_func(auth_data, box_id, messages)
                    if success:
                        ok += 1
                        consecutive_fail = 0
                    else:
                        fail += 1
                        consecutive_fail += 1
                if consecutive_fail >= 5:
                    treo_tabs[threading.current_thread()]['status'] = "⚠️ Rớt (fail nhiều)"
                else:
                    treo_tabs[threading.current_thread()]['status'] = "🟢 Đang chạy"
            except Exception as e:
                fail += 1
                consecutive_fail += 1
                treo_tabs[threading.current_thread()]['status'] = f"⚠️ Lỗi: {str(e)[:50]}"
            uptime_seconds = int((datetime.now() - start_time).total_seconds())
            treo_tabs[threading.current_thread()].update({
                'ok': ok,
                'fail': fail,
                'uptime': uptime_seconds,
                'last_update': datetime.now().strftime("%H:%M:%S %d-%m-%Y")
            })
            for _ in range(max(1, int(delay*10))):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
        info = treo_tabs.get(threading.current_thread(), {}).copy()
        info['stopped_at'] = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        info['total_runtime'] = int((datetime.now() - start_time).total_seconds())
        treo_history.append(info)
    t = threading.Thread(target=worker_wrapper, daemon=True)
    treo_tabs[t] = {
        'app': app_name,
        'type': task_type,
        'box_id': box_id,
        'start_time': datetime.now(),
        'ok': 0,
        'fail': 0,
        'uptime': 0,
        'stop_event': stop_event,
        'status': "🟢 Đang khởi động",
        'last_update': datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    }
    t.start()
    if not silent:
        current_time = datetime.now().strftime("%H:%M:%S")
        print(Fore.GREEN + f"[{current_time}] [+] Đã khởi chạy {task_type} {app_name} cho box {box_id}")
    return t

def xem_dung_treo():
    while True:
        clr()
        current_time = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        print(Fore.CYAN + "\n" + "═" * 60)
        print(Fore.CYAN + f"         DANH SÁCH TASK ĐANG CHẠY - {current_time}")
        print(Fore.CYAN + "═" * 60)
        if not treo_tabs:
            print(Fore.YELLOW + "[!] Hiện không có task nào đang chạy.")
        else:
            for i, (t, info) in enumerate(list(treo_tabs.items()), 1):
                uptime_s = int(info.get('uptime', 0))
                h, rem = divmod(uptime_s, 3600)
                m, s = divmod(rem, 60)
                uptime_str = f"{h:02}:{m:02}:{s:02}"
                status = info.get('status', '')
                last_update = info.get('last_update', 'Chưa cập nhật')
                print(Fore.CYAN + "─" * 60)
                print(Fore.GREEN + f"[{i}] {info.get('app')} | {info.get('type')} | {status}")
                print(Fore.WHITE + f"    Box ID : {info.get('box_id')}")
                print(Fore.YELLOW + f"    Uptime : {uptime_str}")
                print(Fore.CYAN + f"    OK : {info.get('ok')} | FAIL : {info.get('fail')}")
                print(Fore.MAGENTA + f"    Cập nhật: {last_update}")
            print(Fore.CYAN + "─" * 60)
        print(Fore.MAGENTA + "\nLỰA CHỌN:")
        print(Fore.YELLOW + "• Nhập số STT để dừng task cụ thể")
        print(Fore.YELLOW + "• Nhập '10' để xem lịch sử task đã dừng")
        print(Fore.YELLOW + "• Nhập 'stop all' để dừng tất cả task")
        print(Fore.YELLOW + "• Nhập '0' để quay lại menu chính")
        choice = input(Fore.YELLOW + "\n👉 Lựa chọn: ").strip()
        if choice == '0':
            clr()
            break
        if choice.lower() == 'stop all':
            current_time = datetime.now().strftime("%H:%M:%S")
            for t in list(treo_tabs.keys()):
                treo_tabs[t]['stop_event'].set()
            print(Fore.GREEN + f"[{current_time}] [✓] Đã gửi lệnh dừng tất cả task.")
            time.sleep(1.0)
            continue
        elif choice == '10':
            view_task_history()
            continue
        else:
            try:
                idx = int(choice) - 1
                keys = list(treo_tabs.keys())
                if 0 <= idx < len(keys):
                    t = keys[idx]
                    info = treo_tabs[t]
                    info['stop_event'].set()
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print(Fore.GREEN + f"[{current_time}] [✓] Đã gửi lệnh dừng task {info['app']} | {info['type']} (Box: {info['box_id']})")
                    time.sleep(0.3)
                else:
                    print(Fore.RED + "[!] Số thứ tự không hợp lệ.")
            except ValueError:
                print(Fore.RED + "[!] Vui lòng nhập số hợp lệ.")
            time.sleep(1)

def read_messages_from_files(file_list, default_file=None, read_lines=False):
    msgs = []
    files = list(file_list) if file_list else []
    if not files and default_file:
        files = [default_file]
    for fn in files:
        fn = fn.strip()
        if not fn:
            continue
        if not os.path.exists(fn):
            print(Fore.RED + f"[!] File không tồn tại: {fn}")
            continue
        try:
            with open(fn, "r", encoding="utf-8") as f:
                if read_lines:
                    lines = [line.strip() for line in f if line.strip()]
                    msgs.extend(lines)
                else:
                    content = f.read().strip()
                    if content:
                        msgs.append(content)
        except Exception as e:
            print(Fore.RED + f"[!] Lỗi đọc file {fn}: {e}")
    return msgs

def input_int(prompt, default=None):
    while True:
        s = input(Fore.YELLOW + prompt).strip()
        if s == "" and default is not None:
            return default
        try:
            return int(s)
        except:
            print(Fore.RED + "Nhập số hợp lệ!")

def transition_screen(title="KAEL"):
    clr()
    spinner = itertools.cycle(['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏'])
    sys.stdout.write(Fore.CYAN + f"Đang mở {title} ")
    sys.stdout.flush()
    for _ in range(18):
        sys.stdout.write(Fore.YELLOW + next(spinner))
        sys.stdout.flush()
        time.sleep(0.07)
        sys.stdout.write('\b')
    clr()
    big_banner = f"""
{Fore.MAGENTA}
 ██   ██  █████  ███████ ██      
 ██   ██ ██   ██ ██      ██      
 ██████  ███████ █████   ██      
 ██   ██ ██   ██ ██      ██      
 ██   ██ ██   ██ ███████ ███████  

        {Fore.CYAN}{title}
"""
    print(big_banner)
    time.sleep(0.45)

def treo_mess():
    transition_screen("TREO MESSENGER")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === TREO MESSENGER - GỬI FULL NỘI DUNG ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    box_ids = []
    for i, cookie in enumerate(cookies, 1):
        print(f"\n{Fore.CYAN}Cookie thứ {i}:")
        selected = select_boxes_interactive(cookie)
        box_ids.extend(selected)
    
    if not box_ids:
        return
    
    files = []
    while True:
        fn = input("Nhập file ngôn treo (done để xong): ").strip()
        if fn.lower() == "done": break
        if fn: files.append(fn)
    
    messages_list = read_messages_from_files(files, read_lines=False)
    if not messages_list:
        return
    
    full_message = "\n\n".join(messages_list)
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(cookies)} cookie × {len(box_ids)} box...")
    
    for ck in cookies:
        for b in box_ids:
            start_treo_tab(ck, b, full_message, delay, "Messenger", task_type="Treo", silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies) * len(box_ids)} task Treo Messenger")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def nhay_mess():
    transition_screen("NHÂY MESSENGER")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY MESSENGER - GỬI TỪNG DÒNG ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    box_ids = []
    for i, cookie in enumerate(cookies, 1):
        print(f"\n{Fore.CYAN}Cookie thứ {i}:")
        selected = select_boxes_interactive(cookie)
        box_ids.extend(selected)
    
    if not box_ids:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(cookies)} cookie × {len(box_ids)} box...")
    
    for ck in cookies:
        for b in box_ids:
            start_task("Messenger", "Nhây", ck, b, send_messenger, messages, delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies) * len(box_ids)} task Nhây Messenger")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def reo_mess():
    transition_screen("RÉO MESSENGER")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === RÉO MESSENGER - GỬI TỪNG DÒNG KÈM TÊN ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    box_ids = []
    for i, cookie in enumerate(cookies, 1):
        print(f"\n{Fore.CYAN}Cookie thứ {i}:")
        selected = select_boxes_interactive(cookie)
        box_ids.extend(selected)
    
    if not box_ids:
        return
    
    names = []
    while True:
        n = input("Nhập tên người réo (done để xong): ").strip()
        if n.lower() == "done": break
        if n: names.append(n)
    
    if not names:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    def make_send_wrapper(name):
        def send_wrapper(cookie, box_id, msg):
            body = f"{msg} {name}"
            return send_messenger(cookie, box_id, body)
        return send_wrapper
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(cookies)} cookie × {len(box_ids)} box × {len(names)} tên...")
    
    for ck in cookies:
        for b in box_ids:
            for n in names:
                start_task("Messenger", "Reo", ck, b, make_send_wrapper(n), messages, delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies) * len(box_ids) * len(names)} task Réo Messenger")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def so_mess():
    transition_screen("SỚ MESSENGER")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === SỚ MESSENGER - GỬI FULL NỘI DUNG SO.TXT ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    box_ids = []
    for i, cookie in enumerate(cookies, 1):
        print(f"\n{Fore.CYAN}Cookie thứ {i}:")
        selected = select_boxes_interactive(cookie)
        box_ids.extend(selected)
    
    if not box_ids:
        return
    
    messages_list = read_messages_from_files([], default_file="so.txt", read_lines=False)
    if not messages_list:
        return
    
    full_message = "\n\n".join(messages_list)
    delay = input_int("Nhập delay (giây): ", 5)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(cookies)} cookie × {len(box_ids)} box...")
    
    for ck in cookies:
        for b in box_ids:
            start_treo_tab(ck, b, full_message, delay, "Messenger", task_type="Sớ", silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies) * len(box_ids)} task Sớ Messenger")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def nhay_tag_mess():
    transition_screen("NHÂY TAG MESSENGER")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY TAG MESSENGER ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    box_ids = []
    for i, cookie in enumerate(cookies, 1):
        print(f"\nCookie thứ {i}:")
        selected = select_boxes_interactive(cookie)
        box_ids.extend(selected)
    
    if not box_ids:
        return
    
    print(f"\nNhập ID và tên thành viên cần tag")
    print("Định dạng: ID|TÊN (ví dụ: 1000123456789|Nguyen Van A)")
    print("Mỗi dòng 1 thành viên, để trống để kết thúc")
    members_list = []
    while True:
        input_line = input("Nhập ID|TÊN: ").strip()
        if not input_line:
            break
        if "|" in input_line:
            parts = input_line.split("|", 1)
            uid = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else f"User_{uid}"
            if uid.isdigit():
                members_list.append({
                    "id": uid,
                    "name": name
                })
                print(f"Đã thêm: {name} (ID: {uid})")
            else:
                print(f"ID phải là số: {uid}")
        else:
            print("Sai định dạng! Phải là ID|TÊN")
    
    if not members_list:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    def send_tag_messenger(cookie, box_id, content, uid, ten):
        try:
            m = re.search(r"c_user=(\d+)", cookie)
            user_id = m.group(1) if m else "0"
            headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
            res = requests.get('https://mbasic.facebook.com/profile.php', headers=headers, timeout=10)
            fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', res.text)
            fb_dtsg = fb_dtsg_match.group(1) if fb_dtsg_match else None
            if not fb_dtsg:
                return False, "Không lấy được fb_dtsg"
            ts = int(time.time() * 1000)
            if random.choice([True, False]):
                full_message = f"{ten} {content}"
                offset = 0
                length = len(ten)
            else:
                full_message = f"{content} {ten}"
                offset = len(content) + 1
                length = len(ten)
            data = {
                'thread_fbid': box_id,
                'action_type': 'ma-type:user-generated-message',
                'body': full_message,
                'client': 'mercury',
                'author': f'fbid:{user_id}',
                'timestamp': ts,
                'source': 'source:chat:web',
                'offline_threading_id': str(ts),
                'message_id': str(ts),
                '__user': user_id,
                'fb_dtsg': fb_dtsg,
                'jazoest': '22129'
            }
            data.update({
                "profile_xmd[0][id]": uid,
                "profile_xmd[0][offset]": str(offset),
                "profile_xmd[0][length]": str(length),
                "profile_xmd[0][type]": "p",
            })
            headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
            res = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers, timeout=10)
            return res.status_code == 200, res.text
        except Exception as e:
            return False, str(e)
    
    def create_send_wrapper(members):
        def send_wrapper(cookie, box_id, msg):
            member = random.choice(members)
            uid = member["id"]
            ten = member["name"]
            return send_tag_messenger(cookie, box_id, msg, uid, ten)
        return send_wrapper
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] Đang khởi chạy {len(cookies)} cookie × {len(box_ids)} box...")
    
    for cookie in cookies:
        for box_id in box_ids:
            send_func = create_send_wrapper(members_list)
            start_task("Messenger", "Nhây Tag", cookie, box_id, send_func, messages, delay, silent=False)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies) * len(box_ids)} task Nhây Tag Messenger")
    print(f"Đang tag {len(members_list)} thành viên trong {len(box_ids)} box")
    time.sleep(1)

def treo_discord():
    transition_screen("TREO DISCORD")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === TREO DISCORD - GỬI FULL NỘI DUNG ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    channels = input_ids("server/channel ID")
    if not channels:
        return
    
    files = []
    while True:
        fn = input("Nhập file ngôn treo (done để xong): ").strip()
        if fn.lower() == "done": break
        files.append(fn)
    
    messages_list = read_messages_from_files(files, read_lines=False)
    if not messages_list:
        return
    
    full_message = "\n\n".join(messages_list)
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(tokens)} token × {len(channels)} channel...")
    
    for tk in tokens:
        for ch in channels:
            start_treo_tab(tk, ch, full_message, delay, "Discord", task_type="Treo", silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(channels)} task Treo Discord")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def nhay_discord():
    transition_screen("NHÂY DISCORD")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY DISCORD - GỬI TỪNG DÒNG ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    channels = input_ids("server/channel ID")
    if not channels:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(tokens)} token × {len(channels)} channel...")
    
    for tk in tokens:
        for ch in channels:
            start_task("Discord", "Nhây", tk, ch, send_discord, messages, delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(channels)} task Nhây Discord")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def nhay_discord_tag():
    transition_screen("NHÂY TAG DISCORD")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY TAG DISCORD - GỬI TỪNG DÒNG KÈM TAG ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    channels = input_ids("server/channel ID")
    if not channels:
        return
    
    target_id = input("Nhập ID user cần tag: ").strip()
    if not target_id:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    def send_discord_tag(token, channel_id, msg):
        content = f"<@{target_id}> {msg}"
        return send_discord(token, channel_id, content)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(tokens)} token × {len(channels)} channel...")
    
    for tk in tokens:
        for ch in channels:
            start_task("Discord", "Nhây Tag", tk, ch, send_discord_tag, messages, delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(channels)} task Nhây Tag Discord")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def sotagdis():
    transition_screen("SỚ TAG DISCORD")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === SỚ TAG DISCORD ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    channels = input_ids("server/channel ID")
    if not channels:
        return
    
    tag_ids = []
    while True:
        uid = input("Nhập ID user cần tag (done để xong): ").strip()
        if uid.lower() == "done": break
        if uid: tag_ids.append(uid)
    
    tag_str = " ".join([f"<@{uid}>" for uid in tag_ids]) if tag_ids else ""
    delay = input_int("Nhập delay (giây): ", 2)
    
    filepath = "so.txt"
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Câu hỏi poll 1?\nCâu hỏi poll 2?\n")
        print(f"Đã tạo {filepath}, chỉnh nội dung rồi chạy lại.")
        return
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip()]
    
    if not lines:
        print("so.txt rỗng")
        return
    
    def make_send_for_sotag(tagstring, bodies):
        def send_sotag(token, ch, _):
            for body in bodies:
                content = f"{tagstring} {body}"
                send_discord(token, ch, content)
                time.sleep(delay)
            return True, "done"
        return send_sotag
    
    for tk in tokens:
        for ch in channels:
            start_task("Discord", "SoTag", tk, ch, make_send_for_sotag(tag_str, lines), "\n".join(lines), delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(channels)} task Sớ Tag Discord")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def polldis():
    transition_screen("POLL DISCORD")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === POLL DISCORD ===")
    
    REACTIONS = [
        "😭","🤣","💤","💦","😅","🐉","😏","🤯","👁","😪","😤","😓","🤓","😑",
        "👱‍♂️","💔","💙","💓","💘","💤","💥","💌","💢","🕳","💨","💫","☸",
        "🍀","🇻🇳","😰","🌚","🧸","👾","🐻","😱","🤔","😬","🤪","😡","⭐",
        "🙈","💫","🙊","💓","💚","💙","🧡","💜","❤️","💕","🤳","🤝","🙏"
    ]
    TIMEOUT = 5
    
    def send_message(token, channel_id, content):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "DiscordSelfBot (polldis)"
        }
        try:
            r = requests.post(url, headers=headers, json={"content": content}, timeout=TIMEOUT)
            if r.status_code in (200, 201):
                return True, r.json().get("id")
            else:
                return False, r.text[:200]
        except Exception as e:
            return False, str(e)
    
    def add_reaction(token, channel_id, message_id, emoji):
        enc = requests.utils.requote_uri(emoji)
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{enc}/@me"
        headers = {"Authorization": token, "User-Agent": "DiscordSelfBot (polldis)"}
        try:
            r = requests.put(url, headers=headers, timeout=TIMEOUT)
            return r.status_code in (204, 200)
        except:
            return False
    
    tokens = input_tokens()
    if not tokens:
        return
    
    channels = input_ids("server/channel ID")
    if not channels:
        return
    
    tag_ids = []
    while True:
        uid = input("Nhập ID user cần tag (done để xong): ").strip()
        if uid.lower() == "done": break
        if uid: tag_ids.append(uid)
    
    tag_str = " ".join([f"<@{uid}>" for uid in tag_ids]) if tag_ids else ""
    delay = input_int("Nhập delay (giây): ", 3)
    
    filepath = "nhay.txt"
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Câu hỏi poll 1?\nCâu hỏi poll 2?\n")
        print(f"Đã tạo {filepath}, chỉnh nội dung rồi chạy lại.")
        return
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip()]
    
    if not lines:
        print("nhay.txt rỗng")
        return
    
    def make_poll_worker(token, channel_id, lines_local):
        def send_poll(tok, ch, _):
            for body in lines_local:
                content = f"{tag_str} 卍ﮩ٨ـﮩﮩ٨ـ♡ﮩ٨ـﮩﮩ٨ـ☯ {body}\n> # > KAEL KING OF CODE COME TO WAR=))=))=))"
                ok, mid = send_message(token, channel_id, content)
                if ok and mid:
                    def add_reacts(mid_local):
                        for emj in REACTIONS:
                            add_reaction(token, channel_id, mid_local, emj)
                            time.sleep(0.4)
                    threading.Thread(target=add_reacts, args=(mid,), daemon=True).start()
                time.sleep(delay)
            return True, "done"
        return send_poll
    
    for tk in tokens:
        for ch in channels:
            start_task("Discord", "Poll", tk, ch, make_poll_worker(tk, ch, lines), "\n".join(lines), delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(channels)} task Poll Discord")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def treo_telegram():
    transition_screen("TREO TELEGRAM")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === TREO TELEGRAM - GỬI FULL NỘI DUNG ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    chats = input_ids("chat/group ID")
    if not chats:
        return
    
    files = []
    while True:
        fn = input("Nhập file ngôn treo (done để xong): ").strip()
        if fn.lower() == "done": break
        files.append(fn)
    
    messages_list = read_messages_from_files(files, read_lines=False)
    if not messages_list:
        return
    
    full_message = "\n\n".join(messages_list)
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(tokens)} bot × {len(chats)} chat...")
    
    for bot in tokens:
        for ch in chats:
            start_treo_tab(bot, ch, full_message, delay, "Telegram", task_type="Treo", silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(chats)} task Treo Telegram")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def nhay_telegram():
    transition_screen("NHÂY TELEGRAM")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY TELEGRAM - GỬI TỪNG DÒNG ===")
    
    tokens = input_tokens()
    if not tokens:
        return
    
    chats = input_ids("chat/group ID")
    if not chats:
        return
    
    messages = read_messages_from_files([], default_file="nhay.txt", read_lines=True)
    if not messages:
        return
    
    delay = input_int("Nhập delay (giây): ", 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Đang khởi chạy {len(tokens)} bot × {len(chats)} chat...")
    
    for bot in tokens:
        for ch in chats:
            start_task("Telegram", "Nhây", bot, ch, telegram_send, messages, delay, silent=True)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(tokens) * len(chats)} task Nhây Telegram")
    print(Fore.YELLOW + "📌 Các task đang chạy ngầm, dùng 'Xem / Dung Tab Treo' để quản lý")
    time.sleep(1)

def run_facebook_loop(post, cookies, comments, delays):
    post_id = post.split("/")[-1].split("?")[0] if "facebook.com" in post else post
    tokens=[]
    for c in cookies:
        t=get_token(c)
        if t: tokens.append(t); print(Fore.GREEN + "✅ Token ok")
        else: print(Fore.RED + "❌ Lỗi token")
    if not tokens: print(Fore.RED + "❌ Không có token!"); return
    cnt=0
    while True:
        for i,t in enumerate(tokens):
            try:
                msg=random.choice(comments)
                r=requests.post(f"https://graph.facebook.com/{post_id}/comments",data={"message":msg,"access_token":t})
                if r.status_code==200: cnt+=1; print(Fore.GREEN + f"✅ {cnt}: {msg[:60]}")
                else: print(Fore.RED + f"❌ {r.text}")
                d = delays[i] if i < len(delays) else delays[0]
                for i in range(d, 0, -1):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang chờ {i} giây", end="\r"); time.sleep(1)
                print(" " * 50, end="\r")
            except Exception as e: print(Fore.RED + f"❌ {e}")

def treo_top_facebook(use_old=False):
    transition_screen("TREO TOP FACEBOOK")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === TREO TOP FACEBOOK ===")
    cfg={}
    if use_old:
        old=load_config("treo_top")
        if old: print(Fore.GREEN + "✅ Tải cấu hình cũ!"); cfg=old
        else: print(Fore.RED + "❌ Không tìm thấy cấu hình!"); use_old=False
    if use_old and 'cookies' in cfg:
        cookies=cfg['cookies']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Cookie: {cookies[0][:40]}... (cũ)")
    else:
        ck=input_cookies()
        if not ck: return
        cookies=ck; cfg['cookies']=cookies
    if use_old and 'post_url' in cfg:
        post=cfg['post_url']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Link: {post} (cũ)")
    else:
        post = input("Nhập Link Bài Viết: ").strip()
        if not post: return
        cfg['post_url']=post
    comments=[]
    if use_old and 'files' in cfg:
        for f in cfg['files']:
            if os.path.exists(f):
                comments.append(open(f,'r',encoding='utf-8').read().strip()); print(Fore.GREEN + f"✅ {f}")
    else:
        files = []
        while True:
            f = input("Nhập tên file ngôn (done để xong): ").strip()
            if f.lower() == 'done': break
            files.append(f)
        cfg['files']=files
        for f in files:
            if os.path.exists(f):
                comments.append(open(f,'r',encoding='utf-8').read().strip()); print(Fore.GREEN + f"✅ {f}")
            else: print(Fore.RED + f"❌ {f}")
    if not comments: print(Fore.RED + "❌ Không có nội dung!"); return
    if use_old and 'delays' in cfg:
        delays=cfg['delays']
    else:
        ans = input("Delay riêng cho từng acc? (y/n): ").strip().lower()
        if ans == "y":
            delays=[]
            for i in range(len(cookies)):
                v = input(f"Delay cho acc {i+1} (giây): ").strip()
                delays.append(int(v) if v and v.isdigit() else 60)
        else:
            v = input("Delay chung (giây): ").strip()
            common=int(v) if v and v.isdigit() else 60
            delays=[common]*len(cookies)
        cfg['delays']=delays
    if not use_old: save_config("treo_top",cfg)
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Bắt đầu treo top Facebook...")
    run_facebook_loop(post, cookies, comments, cfg['delays'])

def nhay_top_facebook(use_old=False):
    transition_screen("NHÂY TOP FACEBOOK")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === NHÂY TOP FACEBOOK ===")
    cfg={}
    if use_old:
        old=load_config("nhay_top")
        if old: print(Fore.GREEN + "✅ Tải cấu hình cũ!"); cfg=old
        else: print(Fore.RED + "❌ Không tìm thấy cấu hình!"); use_old=False
    if use_old and 'cookies' in cfg:
        cookies=cfg['cookies']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Cookie: {cookies[0][:40]}... (cũ)")
    else:
        ck=input_cookies()
        if not ck: return
        cookies=ck; cfg['cookies']=cookies
    if use_old and 'post_url' in cfg:
        post=cfg['post_url']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Link: {post} (cũ)")
    else:
        post = input("Nhập Link Bài Viết: ").strip()
        if not post: return
        cfg['post_url']=post
    comments=[]
    if os.path.exists("nhay.txt"):
        try:
            comments=[line.strip() for line in open("nhay.txt",'r',encoding='utf-8') if line.strip()]
        except: comments=[]
    if use_old and 'files' in cfg and cfg['files']:
        for f in cfg['files']:
            if os.path.exists(f): comments += [line.strip() for line in open(f,'r',encoding='utf-8') if line.strip()]
    else:
        files = []
        while True:
            f = input("Nhập tên file ngôn (done để xong): ").strip()
            if f.lower() == 'done': break
            files.append(f)
        cfg['files']=files
        for f in files:
            if os.path.exists(f): comments += [line.strip() for line in open(f,'r',encoding='utf-8') if line.strip()]; print(Fore.GREEN + f"✅ {f}")
            else: print(Fore.RED + f"❌ {f}")
    comments=[c for c in comments if c]
    if not comments: print(Fore.RED + "❌ Không có nội dung (tạo nhay.txt hoặc nhập file)!"); return
    if use_old and 'delays' in cfg:
        delays=cfg['delays']
    else:
        v = input("Delay chung (giây): ").strip()
        common=int(v) if v and v.isdigit() else 30
        delays=[common]*len(cookies); cfg['delays']=delays
    if not use_old: save_config("nhay_top",cfg)
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Bắt đầu nhây top Facebook...")
    run_facebook_loop(post, cookies, comments, delays)

def so_top_facebook(use_old=False):
    transition_screen("SỚ TOP FACEBOOK")
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.CYAN + f"[{current_time}] === SỚ TOP FACEBOOK ===")
    cfg={}
    if use_old:
        old=load_config("so_top")
        if old: print(Fore.GREEN + "✅ Tải cấu hình cũ!"); cfg=old
        else: print(Fore.RED + "❌ Không tìm thấy cấu hình!"); use_old=False
    if use_old and 'cookies' in cfg:
        cookies=cfg['cookies']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Cookie: {cookies[0][:40]}... (cũ)")
    else:
        ck=input_cookies()
        if not ck: return
        cookies=ck; cfg['cookies']=cookies
    if use_old and 'post_url' in cfg:
        post=cfg['post_url']; print(f"{Fore.CYAN}[⚜️] ➜ {Fore.RESET}Link: {post} (cũ)")
    else:
        post = input("Nhập Link Bài Viết: ").strip()
        if not post: return
        cfg['post_url']=post
    comments=[]
    if os.path.exists("so.txt"):
        try:
            comments=[line.strip() for line in open("so.txt",'r',encoding='utf-8') if line.strip()]
        except: comments=[]
    if use_old and 'files' in cfg and cfg['files']:
        for f in cfg['files']:
            if os.path.exists(f): comments += [line.strip() for line in open(f,'r',encoding='utf-8') if line.strip()]
    else:
        files = []
        while True:
            f = input("Nhập tên file số (done để xong): ").strip()
            if f.lower() == 'done': break
            files.append(f)
        cfg['files']=files
        for f in files:
            if os.path.exists(f): comments += [line.strip() for line in open(f,'r',encoding='utf-8') if line.strip()]; print(Fore.GREEN + f"✅ {f}")
            else: print(Fore.RED + f"❌ {f}")
    comments=[c for c in comments if c]
    if not comments: print(Fore.RED + "❌ Không có nội dung (tạo so.txt hoặc nhập file)!"); return
    if use_old and 'delays' in cfg:
        delays=cfg['delays']
    else:
        v = input("Delay chung (giây): ").strip()
        common=int(v) if v and v.isdigit() else 45
        delays=[common]*len(cookies); cfg['delays']=delays
    if not use_old: save_config("so_top",cfg)
    current_time = datetime.now().strftime("%H:%M:%S")
    print(Fore.GREEN + f"[{current_time}] 🚀 Bắt đầu sớ top Facebook...")
    run_facebook_loop(post, cookies, comments, delays)

def get_joined_groups_share(token: str):
    url = "https://graph.facebook.com/v15.0/me/groups"
    params = {"access_token": token, "limit": "1000"}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        groups = []
        if "data" in data:
            for g in data["data"]:
                groups.append(g.get("id"))
        return groups
    except:
        return []

def share_post_to_group_share(token: str, post_id: str, group_id: str):
    url = f"https://graph.facebook.com/{group_id}/feed"
    params = {
        "access_token": token,
        "link": f"https://www.facebook.com/{post_id}"
    }
    try:
        res = requests.post(url, data=params, timeout=10)
        return res.json()
    except:
        return {"error": "Thất bại!"}

def share_facebook_worker(cookie, post_id, group_ids, delay, stop_event):
    token = get_token(cookie)
    if not token:
        return
    ok = 0
    fail = 0
    start = datetime.now()
    consecutive_fail = 0
    while not stop_event.is_set():
        random.shuffle(group_ids)
        for gid in group_ids:
            if stop_event.is_set():
                break
            result = share_post_to_group_share(token, post_id, gid)
            if "id" in result:
                ok += 1
                consecutive_fail = 0
                treo_tabs[threading.current_thread()]['status'] = "🟢 Đang share"
            else:
                fail += 1
                consecutive_fail += 1
                if consecutive_fail >= 5:
                    treo_tabs[threading.current_thread()]['status'] = "🔴 Rớt (fail nhiều)"
                else:
                    treo_tabs[threading.current_thread()]['status'] = "🟡 Lỗi tạm thời"
            treo_tabs[threading.current_thread()].update({
                'ok': ok,
                'fail': fail,
                'uptime': (datetime.now() - start).total_seconds()
            })
            for i in range(delay, 0, -1):
                if stop_event.is_set():
                    break
                time.sleep(1)

def start_share_facebook(cookie, post_id, group_ids, delay):
    stop_event = threading.Event()
    t = threading.Thread(target=share_facebook_worker, args=(cookie, post_id, group_ids, delay, stop_event), daemon=True)
    treo_tabs[t] = {
        'app': "Facebook",
        'type': "Share",
        'box_id': f"Post: {post_id}",
        'start_time': datetime.now(),
        'ok': 0,
        'fail': 0,
        'uptime': 0,
        'stop_event': stop_event,
        'status': "🟢 Đang share"
    }
    t.start()
    return t

def share_facebook():
    transition_screen("SHARE FACEBOOK")
    current_time = datetime.now().strftime('%H:%M:%S')
    print(Fore.CYAN + f"[{current_time}] === TOOL SHARE FACEBOOK ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    token = get_token(cookies[0])
    if not token:
        print(Fore.RED + "❌ Không lấy được token, vui lòng thử lại!")
        return
    
    print(Fore.CYAN + "\nVui Lòng Lựa Chọn:")
    print(Fore.YELLOW + "1. Nhập ID Nhóm Thủ Công")
    print(Fore.YELLOW + "2. Tự Động Lấy Tất Cả ID Nhóm Đã Tham Gia")
    choice = input(Fore.WHITE + "Nhập Lựa Chọn (1/2): ").strip()
    
    group_ids = []
    if choice == "1":
        group_ids = input_ids("ID Nhóm")
    elif choice == "2":
        print(Fore.CYAN + "Đang lấy danh sách nhóm...")
        group_ids = get_joined_groups_share(token)
        print(Fore.GREEN + f"✅ Đã lấy được {len(group_ids)} nhóm")
    else:
        print(Fore.RED + "❌ Lựa chọn không hợp lệ!")
        return

    if not group_ids:
        print(Fore.RED + "❌ Không có nhóm nào để share!")
        return

    post_id = input("Nhập ID Bài Viết Cần Share: ").strip()
    if not post_id:
        return

    delay = input_int("Nhập Delay Share (giây): ", 5)

    current_time = datetime.now().strftime('%H:%M:%S')
    print(Fore.GREEN + f"[{current_time}] === BẮT ĐẦU SHARE ===")

    for cookie in cookies:
        start_share_facebook(cookie, post_id, group_ids, delay)

    current_time = datetime.now().strftime('%H:%M:%S')
    print(Fore.GREEN + f"[{current_time}] [✓] Đã khởi chạy {len(cookies)} task Share Facebook")
    time.sleep(2)

def main_menu():
    while True:
        clr()
        spider_art = """
    ╔═══════════════════════════════════════════════╗
    ║            ▄▄▄▄    ▄▄▄▄   ▄▄▄▄    ▄▄▄▄        ║
    ║           ██▀▀██  ██▀▀██ ██▀▀██  ██▀▀██       ║
    ║           ██  ██  ██  ██ ██  ██  ██  ██       ║
    ║           ▀█▄▄▀█  ▀█▄▄▀█ ▀█▄▄▀█  ▀█▄▄▀█       ║
    ║            ▀▀▀▀    ▀▀▀▀   ▀▀▀▀    ▀▀▀▀        ║
    ║                                               ║
    ║           LUYỆN SAMA X HUY BAKA LÀM TOOL         ║
    ╚═══════════════════════════════════════════════╝
        """

        print(Fore.MAGENTA + spider_art)

        colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
        for i in range(3):  
            for color in colors:  
                sys.stdout.write('\r' + color + "Đang Vô Tool , đợi tí e")
                sys.stdout.flush()
                time.sleep(0.1)
        print(Style.RESET_ALL + "\n")
        
        print(Fore.CYAN + "═" * 60)
        print(Fore.YELLOW + " " * 20 + "MENU TOOL NÈ CCHO")
        print(Fore.CYAN + "═" * 60)
        
        print(Fore.GREEN + "\n🕷️ " + Fore.CYAN + "TREO MESS:" + Style.RESET_ALL)
        print(Fore.WHITE + "  ┌─[" + Fore.YELLOW + "1" + Fore.WHITE + "] Treo Messenger")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "2" + Fore.WHITE + "] Nhây Messenger")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "3" + Fore.WHITE + "] Réo Messenger")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "4" + Fore.WHITE + "] Sớ Messenger")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "5" + Fore.WHITE + "] Nhây Tag Messenger")
        print(Fore.WHITE + "  └─[" + Fore.YELLOW + "6" + Fore.WHITE + "] Chức năng nâng cao...")
        
        print(Fore.GREEN + "\n🕷️ " + Fore.CYAN + "TREO DIS:" + Style.RESET_ALL)
        print(Fore.WHITE + "  ┌─[" + Fore.YELLOW + "7" + Fore.WHITE + "] Treo Discord")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "8" + Fore.WHITE + "] Nhây Discord")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "9" + Fore.WHITE + "] Nhây Tag Discord")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "10" + Fore.WHITE + "] Sớ Tag Discord")
        print(Fore.WHITE + "  └─[" + Fore.YELLOW + "11" + Fore.WHITE + "] Poll Discord")
        
        print(Fore.GREEN + "\n🕷️ " + Fore.CYAN + "TREO TELE:" + Style.RESET_ALL)
        print(Fore.WHITE + "  ┌─[" + Fore.YELLOW + "12" + Fore.WHITE + "] Treo Telegram")
        print(Fore.WHITE + "  └─[" + Fore.YELLOW + "13" + Fore.WHITE + "] Nhây Telegram")
        
        print(Fore.GREEN + "\n🕷️ " + Fore.CYAN + "TREO TOP , FB:" + Style.RESET_ALL)
        print(Fore.WHITE + "  ┌─[" + Fore.YELLOW + "14" + Fore.WHITE + "] Treo Top Facebook")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "15" + Fore.WHITE + "] Nhây Top Facebook")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "16" + Fore.WHITE + "] Sớ Top Facebook")
        print(Fore.WHITE + "  └─[" + Fore.YELLOW + "17" + Fore.WHITE + "] Share Facebook")
        
        print(Fore.GREEN + "\n🕷️ " + Fore.CYAN + "HỆ THỐNG:" + Style.RESET_ALL)
        print(Fore.WHITE + "  ┌─[" + Fore.YELLOW + "18" + Fore.WHITE + "] Xem/Dừng Task đang chạy")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "19" + Fore.WHITE + "] Lịch sử task")
        print(Fore.WHITE + "  ├─[" + Fore.YELLOW + "20" + Fore.WHITE + "] Cleanup Memory")
        print(Fore.WHITE + "  └─[" + Fore.YELLOW + "0" + Fore.RED + "] Thoát" + Style.RESET_ALL)
        
        print(Fore.CYAN + "\n" + "═" * 60)
        
        for _ in range(2):
            sys.stdout.write(Fore.MAGENTA + "➤ " + Fore.YELLOW + "Nhập lựa chọn: ")
            sys.stdout.flush()
            time.sleep(0.2)
            sys.stdout.write('\r' + ' ' * 50)
            sys.stdout.flush()
            time.sleep(0.2)
        
        choice = input(Fore.MAGENTA + "➤ " + Fore.YELLOW + "Nhập lựa chọn: " + Style.RESET_ALL).strip()
        
        if choice == "1":
            treo_mess()
        elif choice == "2":
            nhay_mess()
        elif choice == "3":
            reo_mess()
        elif choice == "4":
            so_mess()
        elif choice == "5":
            nhay_tag_mess()
        elif choice == "6":
            advanced_messenger_menu()
        elif choice == "7":
            treo_discord()
        elif choice == "8":
            nhay_discord()
        elif choice == "9":
            nhay_discord_tag()
        elif choice == "10":
            sotagdis()
        elif choice == "11":
            polldis()
        elif choice == "12":
            treo_telegram()
        elif choice == "13":
            nhay_telegram()
        elif choice == "14":
            treo_top_facebook()
        elif choice == "15":
            nhay_top_facebook()
        elif choice == "16":
            so_top_facebook()
        elif choice == "17":
            share_facebook()
        elif choice == "18":
            xem_dung_treo()
        elif choice == "19":
            view_task_history()
        elif choice == "20":
            cleanup_global_memory()
            print(Fore.GREEN + "[✓] Đã cleanup memory!")
            time.sleep(1)
        elif choice == "0":
            clr()
            print(Fore.RED + "tan học rồi đi về đi em")
            time.sleep(1)
            sys.exit(0)
        else:
            print(Fore.RED + "❌ Lựa chọn không hợp lệ!")
            time.sleep(1)

def advanced_messenger_menu():
    clr()
    print(Fore.MAGENTA + """
    ╔══════════════════════════════════════╗
    ║   🕸️ MESSENGER VIP        ║
    ╚══════════════════════════════════════╝
    """)
    print(Fore.CYAN + "═" * 40)
    print(Fore.YELLOW + "1. NHÂY NAME BOX")
    print(Fore.YELLOW + "2. TREO POLL")
    print(Fore.YELLOW + "3. NHÂY FAKE SOẠN")
    print(Fore.YELLOW + "4. SPAM THAY NỀN")
    print(Fore.YELLOW + "5. Đổi biệt danh")
    print(Fore.YELLOW + "6. REGBOX")
    print(Fore.YELLOW + "0. Quay lại")
    print(Fore.CYAN + "═" * 40)
    
    choice = input(Fore.GREEN + "Chọn: ").strip()
    
    if choice == "1":
        run_messenger_option(4)
    elif choice == "2":
        run_messenger_option(7)
    elif choice == "3":
        run_messenger_option(8)
    elif choice == "4":
        run_messenger_option(9)
    elif choice == "5":
        run_messenger_option(10)
    elif choice == "6":
        create_group_with_friends()
    elif choice == "0":
        return

def run_messenger_option(option):
    clr()
    option_names = {
        4: "NHÂY NAME BOX",
        7: "TREO POLL", 
        8: "NHÂY FAKE SOẠN",
        9: "SPAM THAY NỀN",
        10: "ĐỔI BIỆT DANH"
    }
    print(Fore.CYAN + f"=== {option_names.get(option, 'MESSENGER VIP')} ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    thread_ids = []
    print(Fore.CYAN + "\n📦 CHỌN BOX MESSENGER:")
    print(Fore.YELLOW + "1. Nhập thủ công ID box")
    print(Fore.YELLOW + "2. Auto lấy danh sách box từ cookie")
    choice = input(Fore.GREEN + "Chọn (1/2): ").strip()
    
    if choice == "1":
        thread_ids = input_ids("ID nhóm (box)")
    elif choice == "2":
        for i, cookie in enumerate(cookies, 1):
            print(f"\n{Fore.CYAN}📋 Cookie thứ {i}:")
            selected = select_boxes_interactive(cookie)
            if selected:
                thread_ids.extend(selected)
                print(f"{Fore.GREEN}✅ Đã chọn {len(selected)} box từ cookie này")
            else:
                print(f"{Fore.YELLOW}⚠️ Không chọn box nào từ cookie này")
    else:
        print(Fore.RED + "❌ Lựa chọn không hợp lệ!")
        return
    
    if not thread_ids:
        print(Fore.RED + "❌ Không có box nào để xử lý!")
        return
    
    print(f"{Fore.GREEN}✅ Tổng cộng: {len(thread_ids)} box")
    
    delay = input_int("⏱️ Delay (giây): ", 2)
    
    name_file = None
    file_path = None
    contact_uid = None
    nickname = None
    
    if option in [4, 7, 8]:
        name_file = input("📄 Nhập file nội dung (nhay.txt): ").strip()
        if not name_file:
            name_file = "nhay.txt"
        if not os.path.exists(name_file):
            print(Fore.RED + f"❌ File {name_file} không tồn tại!")
            return
    
    if option == 5:
        file_path = input("🖼️ Nhập URL ảnh/video: ").strip()
    
    if option in [2, 3]:
        contact_uid = input("👤 Nhập UID chia sẻ (Enter để dùng UID hiện tại): ").strip()
        if not contact_uid:
            contact_uid = None
    
    if option == 10:
        nickname = input("🏷️ Nhập biệt danh muốn đặt cho thành viên: ").strip()
        if not nickname:
            print(Fore.RED + "❌ Cần nhập biệt danh!")
            return
    
    message_files = []
    if option in [0, 1, 2, 3, 5]:
        while True:
            mf = input("📄 Nhập file tin nhắn (done để xong): ").strip()
            if mf.lower() == 'done':
                break
            if mf:
                if os.path.exists(mf):
                    message_files.append(mf)
                    print(f"{Fore.GREEN}✅ Đã thêm file: {mf}")
                else:
                    print(f"{Fore.RED}❌ File không tồn tại: {mf}")
    
    print(f"\n{Fore.CYAN}🚀 Đang bắt đầu...")
    print(f"{Fore.YELLOW}📌 Cookies: {len(cookies)}")
    print(f"{Fore.YELLOW}📌 Box: {len(thread_ids)}")
    print(f"{Fore.YELLOW}⏱️ Delay: {delay} giây")
    
    send_messages_with_cookie(
        cookies, thread_ids, message_files, delay, 
        option, file_path, contact_uid, name_file, nickname
    )

def create_group_with_friends():
    clr()
    print(Fore.CYAN + "=== Regbox ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    group_title = input("Tên nhóm: ").strip()
    if not group_title:
        print(Fore.RED + "❌ Cần nhập tên nhóm!")
        return
    
    participant_ids = input_ids("ID thành viên (ít nhất 2)")
    if len(participant_ids) < 2:
        print(Fore.RED + "❌ Cần ít nhất 2 thành viên!")
        return
    
    for cookie in cookies:
        try:
            fb = ngquanghuyakadzi(cookie)
            dataFB = {
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }
            
            success, thread_id, log = create_new_group(dataFB, participant_ids, group_title)
            print(log)
            
            if success:
                print(Fore.GREEN + f"[✓] Đã tạo nhóm ID: {thread_id}")
                
                success, friend_ids, friend_log = get_friends_list(dataFB)
                print(friend_log)
                
                if success and friend_ids:
                    print(f"{Fore.CYAN}👥 Đang thêm {len(friend_ids)} bạn bè vào nhóm...")
                    batch_size = 50
                    for i in range(0, len(friend_ids), batch_size):
                        batch = friend_ids[i:i + batch_size]
                        success, add_log = add_user_to_group(dataFB, batch, thread_id)
                        print(add_log)
                        time.sleep(5)
        except Exception as e:
            print(Fore.RED + f"❌ Lỗi: {str(e)}")
    print(Fore.GREEN + "\n✅ Hoàn tất tạo nhóm!")
    time.sleep(2)
def create_group_with_friends():
    clr()
    print(Fore.CYAN + "=== Regbox ===")
    
    cookies = input_cookies()
    if not cookies:
        return
    
    group_title = input("Tên nhóm: ").strip()
    if not group_title:
        print(Fore.RED + "❌ Cần nhập tên nhóm!")
        return
    
    participant_ids = input_ids("ID thành viên (ít nhất 2)")
    if len(participant_ids) < 2:
        print(Fore.RED + "❌ Cần ít nhất 2 thành viên!")
        return
    
    for cookie in cookies:
        try:
            fb = ngquanghuyakadzi(cookie)
            dataFB = {
                "FacebookID": fb.user_id,
                "fb_dtsg": fb.fb_dtsg,
                "clientRevision": fb.rev,
                "jazoest": fb.jazoest,
                "cookieFacebook": cookie
            }
            
            success, thread_id, log = create_new_group(dataFB, participant_ids, group_title)
            print(log)
            
            if success:
                print(Fore.GREEN + f"[✓] Đã tạo nhóm ID: {thread_id}")
                
                success, friend_ids, friend_log = get_friends_list(dataFB)
                print(friend_log)
                
                if success and friend_ids:
                    batch_size = 50
                    for i in range(0, len(friend_ids), batch_size):
                        batch = friend_ids[i:i + batch_size]
                        success, add_log = add_user_to_group(dataFB, batch, thread_id)
                        print(add_log)
                        time.sleep(5)
        except Exception as e:
            print(Fore.RED + f"❌ Lỗi: {str(e)}")
    print(Fore.GREEN + "\n✅ Hoàn tất tạo nhóm!")
    time.sleep(2)

def view_task_history():
    clr()
    print(Fore.MAGENTA + """
    ╔══════════════════════════════════════╗
    ║       🕸️ LỊCH SỬ TASK 🕸️           ║
    ╚══════════════════════════════════════╝
    """)
    
    if not treo_history:
        print(Fore.YELLOW + "Chưa có task nào trong lịch sử.")
    else:
        print(Fore.CYAN + f"Tổng: {len(treo_history)} task đã dừng")
        print(Fore.CYAN + "═" * 60)
        
        for idx, task in enumerate(treo_history[-10:], 1):
            print(Fore.GREEN + f"[{idx}] {task.get('app', 'N/A')} | {task.get('type', 'N/A')}")
            print(Fore.WHITE + f"    Box: {task.get('box_id', 'N/A')}")
            print(Fore.YELLOW + f"    OK: {task.get('ok', 0)} | FAIL: {task.get('fail', 0)}")
            print(Fore.CYAN + f"    Thời gian: {task.get('total_runtime', 0)}s")
            print(Fore.MAGENTA + f"    Dừng lúc: {task.get('stopped_at', 'N/A')}")
            print(Fore.CYAN + "─" * 40)
    
    input(Fore.YELLOW + "\nNhấn Enter để tiếp tục...")

if __name__ == "__main__":
    try:
        clr()
        for i in range(3):
            for symbol in ["🕷️", "🕸️", "⚙️", "🔧", "💻"]:
                sys.stdout.write('\r' + Fore.MAGENTA + " " * 20 + f"{symbol} LÊ VĂN LUYỆN LONG TIME... {symbol}")
                sys.stdout.flush()
                time.sleep(0.1)
        
        print(Fore.GREEN + "\n\n" + "═" * 60)
        print(Fore.YELLOW + " " * 15 + "Hiệu Trưởng Sát Thần University.")
        print(Fore.GREEN + "═" * 60)
        print(Fore.CYAN + "• 1 năm ngày tao đú treo tool tri ân")
        print(Fore.CYAN + "• Author: Đấng hang băng , lê văn luyện")
        print(Fore.CYAN + f"• Time: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
        print(Fore.GREEN + "═" * 60)
        
        time.sleep(1)
        
        main_menu()
        
    except KeyboardInterrupt:
        print(Fore.RED + "\n\n🕷️  Đã dừng bởi người dùng!")
        time.sleep(1)
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"\n❌ Lỗi: {str(e)}")
        traceback.print_exc()
        input(Fore.YELLOW + "\nNhấn Enter để thoát...")
        sys.exit(1)