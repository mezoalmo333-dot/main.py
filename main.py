import time
import re
import json
import os
import html
import random
import uuid
import pickle
import csv
from io import StringIO
import cloudscraper
import requests
import phonenumbers
from phonenumbers import geocoder
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from threading import Thread, Event
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
import shutil

BOT_TOKEN ="8525050758:AAHVbXDCOWNKZoQLcHi78wB2rZ-yyZ4BpGk"
MAIN_ADMIN_ID = 8037399518

collected_codes = []

# ── Live Traffic Log ─────────────────────────────────────────────────────────
LIVE_TRAFFIC_LOG = []
LIVE_TRAFFIC_LOCK = threading.Lock()

def log_live_traffic(number, country_name=None, platform=None):
    """تسجيل OTP جديد في سجل الـ Live Traffic"""
    global LIVE_TRAFFIC_LOG
    try:
        if not country_name:
            try:
                parsed = phonenumbers.parse("+" + str(number).lstrip("+"))
                country_name = geocoder.description_for_number(parsed, "en") or "Unknown"
            except Exception:
                country_name = "Unknown"
        entry = {
            "country": country_name,
            "platform": platform or "Unknown",
            "time": datetime.now()
        }
        with LIVE_TRAFFIC_LOCK:
            LIVE_TRAFFIC_LOG.append(entry)
            if len(LIVE_TRAFFIC_LOG) > 500:
                LIVE_TRAFFIC_LOG = LIVE_TRAFFIC_LOG[-500:]
    except Exception as e:
        print(f"⚠️ log_live_traffic error: {e}")

def get_live_traffic_stats(minutes=60):
    """حساب إحصائيات الـ Live Traffic لآخر X دقائق"""
    now = datetime.now()
    cutoff = now - timedelta(minutes=minutes)
    with LIVE_TRAFFIC_LOCK:
        recent = [e for e in LIVE_TRAFFIC_LOG if e["time"] >= cutoff]
    total = len(recent)
    if total == 0:
        return total, 0, [], None, None
    country_platform = {}
    for e in recent:
        c = e.get("country") or "Unknown"
        p = e.get("platform") or "Unknown"
        if c not in country_platform:
            country_platform[c] = {}
        country_platform[c][p] = country_platform[c].get(p, 0) + 1
    country_totals = {c: sum(v.values()) for c, v in country_platform.items()}
    sorted_countries = sorted(country_totals.items(), key=lambda x: x[1], reverse=True)
    country_pcts = []
    for c, cnt in sorted_countries:
        pct = round(cnt / total * 100, 1)
        all_plts = sorted(country_platform[c].items(), key=lambda x: x[1], reverse=True)
        all_plt_names = [p for p, _ in all_plts]
        country_pcts.append((c, pct, all_plt_names))
    top_country = sorted_countries[0][0] if sorted_countries else None
    top_platform = max(country_platform[top_country], key=country_platform[top_country].get) if top_country else "Unknown"
    return total, 100, country_pcts, top_country, top_platform
# ─────────────────────────────────────────────────────────────────────────────

def create_backup(source_files, backup_dir="backups"):
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup_dir = os.path.join(backup_dir, f"backup_{timestamp}")
    os.makedirs(current_backup_dir, exist_ok=True)
    
    for file in source_files:
        if file and os.path.exists(file):
            try:
                dest_path = os.path.join(current_backup_dir, os.path.basename(file))
                if os.path.isdir(file):
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(file, dest_path)
                else:
                    shutil.copy2(file, current_backup_dir)
            except Exception as e:
                print(f"Error backing up {file}: {e}")
    
    
    zip_name = f"{current_backup_dir}.zip"
    try:
        shutil.make_archive(current_backup_dir, 'zip', current_backup_dir)
       
        shutil.rmtree(current_backup_dir)
        return zip_name
    except Exception as e:
        print(f"Error zipping backup: {e}")
        return current_backup_dir

class BackupManager:
    def create_backup(self):
        
        files_to_backup = []
        for var in ['SETTINGS_FILE', 'SESSIONS_FILE', 'USERS_FILE', 'ADMINS_FILE', 'GROUPS_FILE', 'COUNTRIES_FILE', 'CHANNELS_FILE']:
            val = globals().get(var)
            if val: files_to_backup.append(val)
        
        
        if os.path.exists("database"): files_to_backup.append("database")
        
        return create_backup(files_to_backup)
    
    def restore_backup(self, zip_path):
        return False

backup_manager = BackupManager()

def list_backups(backup_dir="backups"):
   
    if not os.path.exists(backup_dir):
        return []
    return sorted([d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))], reverse=True)


import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

SETTINGS_FILE = "ii287.json"

RETURN_OTP_ENABLED = False
RETURN_OTP_FILE = "return_otp_state.json"

def load_return_otp_state():
    global RETURN_OTP_ENABLED
    import os, json
    if os.path.exists(RETURN_OTP_FILE):
        try:
            with open(RETURN_OTP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                RETURN_OTP_ENABLED = data.get("enabled", False)
        except: pass
    return RETURN_OTP_ENABLED

def save_return_otp_state():
    import json
    with open(RETURN_OTP_FILE, 'w', encoding='utf-8') as f:
        json.dump({"enabled": RETURN_OTP_ENABLED}, f)

load_return_otp_state()

SESSIONS_FILE = "godzella.json"
def get_country_flags(country_name):
    # سيتم استخدام التعريف المتأخر في الملف الذي يحتوي على SPECIAL_FLAGS
    # هذا التعريف هنا فقط كـ placeholder لتجنب الأخطاء في البداية
    try:
        return get_country_flags_final(country_name)
    except:
        return "🌍"

def load_env():
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()



DEFAULT_SETTINGS = {
    "GROUP": {
        "name": "GROUP",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "هنا",
                "password": "هنا"
            }
        ],
        "base_url": "http://139.99.63.204",
        "login_page_url": "http://139.99.63.204/ints/login",
        "login_post_url": "http://139.99.63.204/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Fly sms": {
        "name": "Fly sms",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "modybasha12",
                "password": "PingLy111_333"
            }
        ],
        "base_url": "http://193.70.33.154",
        "login_page_url": "http://193.70.33.154/ints/login",
        "login_post_url": "http://193.70.33.154/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 60,
        "enabled": True
    },
    "Number_Panel": {
        "name": "Number Panel",
        "accounts": [
            {
                "id": "R1FQR0dBUzR2hpFrRJdXYGtRYUlkdm6Aco1PgWGEbVVSf21jcm9tYQ==",
                "api_token": "R1FQR0dBUzR2hpFrRJdXYGtRYUlkdm6Aco1PgWGEbVVSf21jcm9tYQ=="
            }
        ],
        "base_url": "http://147.135.212.197/crapi/st/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Bolt": {
        "name": "Bolt",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "mohamedessmat",
                "password": "@My2052011"
            }
        ],
        "base_url": "http://93.190.143.35/ints",
        "login_page_url": "http://93.190.143.35/ints/Login",
        "login_post_url": "http://93.190.143.35/ints/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "iVASMS": {
        "name": "iVAS SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "هنا",
                "password": "هنا",
                "api_key": "sk_4b5ff02b42635e4c4891bd5d2f8fcb7aff2f7af6d5daecf8498ba91092dfcbb6"
            }
        ],
        "api_url": "https://maroon-wombat-183778.hostingersite.com/apiivasms/api.php",
        "check_interval": 5,
        "timeout": 15,
        "enabled": True
    },
    "MSI": {
        "name": "MSI",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "MEDOX123",
                "password": "MEDOX456"
            }
        ],
        "base_url": "http://145.239.130.45/ints",
        "login_page_url": "http://145.239.130.45/ints/login",
        "login_post_url": "http://145.239.130.45/ints/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "proton SMS": {
        "name": "proton SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "MEDOX123",
                "password": "MEDOX456"
            }
        ],
        "base_url": "http://109.236.84.81/ints",
        "login_page_url": "http://109.236.84.81/ints/login",
        "login_post_url": "http://109.236.84.81/ints/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 60,
        "enabled": True
    },
    "IMS": {
        "name": "IMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "Youssef123X",
                "password": "Youssef123X"
            }
        ],
        "base_url": "http://45.82.67.20",
        "login_page_url": "http://45.82.67.20/ints/login",
        "login_post_url": "http://45.82.67.20/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "Roxy SMS": {
        "name": "Roxy SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "hsbullah",
                "password": "znbzh"
            }
        ],
        "base_url": "http://www.roxysms.net",
        "login_page_url": "http://www.roxysms.net/Login",
        "login_post_url": "http://www.roxysms.net/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True,
        "use_scraper": True
    },
    "Konekta_API": {
        "name": "Konekta API",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "RFVYRDRSQmqIh25jYW1tYmGlnV2pbf2tsZ0VkjmNgiox6coBv" 
            }
        ],
        "api_url": "http://51.77.216.195/crapi/konek/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "TimeSMS_API": {
        "name": "TimeSMS API",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "QlRYSTRSQndZiIF_VFWWiVeRkHuLhpSGWZaRhX9rbX2JklFoeoZm"
            }
        ],
        "api_url": "http://147.135.212.197/crapi/time/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Fire_SMS": {
        "name": "Fire SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "eslam852",
                "password": "sjhshs"
            }
        ],
        "base_url": "http://54.39.104.241",
        "login_page_url": "http://54.39.104.241/ints/login",
        "login_post_url": "http://54.39.104.241/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Hadi_SMS": {
        "name": "Hadi SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "Qk9TQUZBUzSGYIF0WpGCZF5oj4prl2B5emZWXmaDl3hnf4ZKi4iQaw=="
            }
        ],
        "api_url": "http://147.135.212.197/crapi/had/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
        "Seven1Tel": {
        "name": "Seven1Tel",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "ahmedmohamed",
                "password": "max112233"
            }
        ],
        "base_url": "http://94.23.120.156",
        "login_page_url": "http://94.23.120.156/ints/login",
        "login_post_url": "http://94.23.120.156/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 60,
        "enabled": True
    },
    "Gaza SMS": {
        "name": "Gaza SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "test123",
                "password": "test123"
            }
        ],
        "base_url": "http://109.236.84.81",
        "login_page_url": "http://109.236.84.81/ints/login",
        "login_post_url": "http://109.236.84.81/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Km sms": {
        "name": "Km sms",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "test123",
                "password": "test123"
            }
        ],
        "base_url": "http://93.190.143.35",
        "login_page_url": "http://93.190.143.35/ints/login",
        "login_post_url": "http://93.190.143.35/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Grand SMS": {
        "name": "Grand SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "test123",
                "password": "test123"
            }
        ],
        "base_url": "http://54.39.104.241",
        "login_page_url": "http://54.39.104.241/ints/login",
        "login_post_url": "http://54.39.104.241/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Purple SMS": {
        "name": "Purple SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "test123",
                "password": "test123"
            }
        ],
        "base_url": "http://147.135.212.197",
        "login_page_url": "http://147.135.212.197/ints/login",
        "login_post_url": "http://147.135.212.197/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Flex": {
        "name": "Flex",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "Modybasha12",
                "password": "Modybasha12"
            }
        ],
        "base_url": "http://168.119.13.175/ints",
        "login_page_url": "http://168.119.13.175/ints/login",
        "login_post_url": "http://168.119.13.175/ints/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "rsayel": {
        "name": "rsayel",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "azaa1564",
                "password": "azaa1564"
            }
        ],
        "base_url": "http://176.9.58.30",
        "login_page_url": "http://176.9.58.30/ints/login",
        "login_post_url": "http://176.9.58.30/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "ksi": {
        "name": "KSI",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "http://54.38.92.155",
        "login_page_url": "http://54.38.92.155/ints/login",
        "login_post_url": "http://54.38.92.155/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "green": {
        "name": "Green \U0001F33F",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "http://139.99.9.4",
        "login_page_url": "http://139.99.9.4/ints/login",
        "login_post_url": "http://139.99.9.4/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "grand": {
        "name": "grand",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": "",
                "api_key": ""
            }
        ],
        "base_url": "https://api.grand-panel.com",
        "login_page_url": "https://panel.grand-panel.com/login",
        "login_post_url": "https://panel.grand-panel.com/login",
        "ajax_path": "/api/v1/messages",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "IMS_New": {
        "name": "IMS Client",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "https://imssms.org",
        "login_page_url": "https://imssms.org/login",
        "login_post_url": "https://imssms.org/signin",
        "ajax_path": "/client/res/data_smscdr.php",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "MBC": {
        "name": "MBC 🅼",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "https://mbcs-ms.com",
        "login_page_url": "https://mbcs-ms.com/login",
        "login_post_url": "https://mbcs-ms.com/login",
        "messages_url": "https://mbcs-ms.com/stats/sms-cdr-stats",
        "ajax_path": "/dashboard",
        "check_interval": 16,
        "timeout": 30,
        "enabled": True
    },
    "Basha": {
        "name": "Basha",
        "accounts": [],
        "base_url": "https://basha.cc",
        "check_interval": 10,
        "timeout": 30,
        "enabled": True
    },
    "Flash_SMS": {
        "name": "Flash SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "wK4gADTYNqE_YQEvWlxdxjoGRMmoSiIFZZHwlfStzo8"
            }
        ],
        "api_url": "https://www.flashsms.space/api/cdr/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
            "Horus": {
        "name": "Horus SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "AGT-AE345R4C",
                "api_url": "http://166.1.2.92/api/messages/cdr"
            }
        ],
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Pac_Call": {
        "name": "Pac Call",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "SVFUQz1SS1J5i4R1Q05RRw=="
            }
        ],
        "base_url": "http://pscall.net",
        "api_url": "http://pscall.net/restapi/smsreport",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Squad": {
        "name": "Squad SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "mohamed1500",
                "password": "12345678"
            }
        ],
        "base_url": "http://51.77.221.209",
        "login_page_url": "http://51.77.221.209/ints/login",
        "login_post_url": "http://51.77.221.209/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "Sniper": {
        "name": "Sniper SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "mariamxemon",
                "password": "123123123"
            }
        ],
        "base_url": "http://135.125.222.224",
        "login_page_url": "http://135.125.222.224/ints/login",
        "login_post_url": "http://135.125.222.224/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 10,
        "enabled": True
    },
    "Lamix": {
        "name": "Lamix SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "http://139.99.208.63",
        "login_page_url": "http://139.99.208.63/ints/login",
        "login_post_url": "http://139.99.208.63/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 10,
        "enabled": True
    },
    "Num44": {
        "name": "44 Numbers",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "http://185.177.124.145",
        "login_page_url": "http://185.177.124.145/ints/login",
        "login_post_url": "http://185.177.124.145/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "stats_page": "/ints/agent/SMSCDRStats",
        "check_interval": 5,
        "timeout": 10,
        "enabled": True
    },
    "XAP": {
        "name": "XAP SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "",
                "password": ""
            }
        ],
        "base_url": "http://147.135.212.148",
        "login_page_url": "http://147.135.212.148/ints/login",
        "login_post_url": "http://147.135.212.148/ints/signin",
        "ajax_path": "/ints/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 10,
        "enabled": True
    },
    "EMO SMS": {
        "name": "EMO SMS",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "username": "MEDOX123",
                "password": "MEDOX123"
            }
        ],
        "base_url": "http://139.99.69.196/ints",
        "login_page_url": "http://139.99.69.196/ints/login",
        "login_post_url": "http://139.99.69.196/ints/signin",
        "ajax_path": "/agent/res/data_smscdr.php",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    },
    "PRIM-FLASH": {
        "name": "PRIM-FLASH",
        "accounts": [
            {
                "id": str(uuid.uuid4()),
                "api_token": "8lh_Z640gnECMIQGbMEUxfd6dz76DMDVTxfZegIklAg"
            }
        ],
        "api_url": "http://flashsms.space/api/cdr/viewstats",
        "check_interval": 5,
        "timeout": 30,
        "enabled": True
    }
}

def migrate_old_settings(settings):
    migrated = False
    
    # Remove old panels if they exist
    if "Konekta" in settings:
        del settings["Konekta"]
        migrated = True
    if "TimeSMS" in settings:
        del settings["TimeSMS"]
        migrated = True
    
    # Main panels list
    main_sites = ["GROUP", "Fly sms", "Number_Panel", "Bolt", "iVASMS", "MSI", "proton SMS", "IMS", "IMS_New", "Roxy SMS", "Konekta_API", "TimeSMS_API", "Fire_SMS", "Hadi_SMS", "Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "MBC", "Flash_SMS", "Horus", "Flex", "rsayel", "ksi", "green", "grand", "Squad", "Sniper", "Lamix", "Num44", "XAP", "EMO SMS", "Pac_Call", "PRIM-FLASH"]
    
    for site_key in main_sites:
        if site_key in settings:
            if "username" in settings[site_key] and "accounts" not in settings[site_key]:
                old_username = settings[site_key]["username"]
                old_password = settings[site_key]["password"]
                settings[site_key]["accounts"] = [
                    {
                        "id": str(uuid.uuid4()),
                        "username": old_username,
                        "password": old_password
                    }
                ]
                del settings[site_key]["username"]
                del settings[site_key]["password"]
                migrated = True
            
            if settings[site_key].get("check_interval", 5) == 7:
                settings[site_key]["check_interval"] = 5
                migrated = True
                print(f"✅ تحديث سرعة {site_key} من 7 إلى 5 ثواني")
    
    # إزالة اللوحات المحذوفة من الإعدادات المحفوظة
    for removed_panel in ("IMO",):
        if removed_panel in settings:
            del settings[removed_panel]
            migrated = True

    # Add missing panels
    missing_panels = {
        "iVASMS": DEFAULT_SETTINGS["iVASMS"].copy(),
        "MSI": DEFAULT_SETTINGS["MSI"].copy(),
        "proton SMS": DEFAULT_SETTINGS["proton SMS"].copy(),
        "IMS": DEFAULT_SETTINGS["IMS"].copy(),
        "IMS_New": DEFAULT_SETTINGS["IMS_New"].copy(),
        "Roxy SMS": DEFAULT_SETTINGS["Roxy SMS"].copy(),
        "Konekta_API": DEFAULT_SETTINGS["Konekta_API"].copy(),
        "TimeSMS_API": DEFAULT_SETTINGS["TimeSMS_API"].copy(),
        "Fire_SMS": DEFAULT_SETTINGS["Fire_SMS"].copy(),
        "Hadi_SMS": DEFAULT_SETTINGS["Hadi_SMS"].copy(),
        "Seven1Tel": DEFAULT_SETTINGS["Seven1Tel"].copy(),
        "Gaza SMS": DEFAULT_SETTINGS["Gaza SMS"].copy(),
        "Km sms": DEFAULT_SETTINGS["Km sms"].copy(),
        "Grand SMS": DEFAULT_SETTINGS["Grand SMS"].copy(),
        "Purple SMS": DEFAULT_SETTINGS["Purple SMS"].copy(),
        "MBC": DEFAULT_SETTINGS["MBC"].copy(),
        "Basha": DEFAULT_SETTINGS["Basha"].copy(),
        "Flash_SMS": DEFAULT_SETTINGS["Flash_SMS"].copy(),
        "Horus": DEFAULT_SETTINGS["Horus"].copy(),
        "Flex": DEFAULT_SETTINGS["Flex"].copy(),
        "rsayel": DEFAULT_SETTINGS["rsayel"].copy(),
        "ksi": DEFAULT_SETTINGS["ksi"].copy(),
        "green": DEFAULT_SETTINGS["green"].copy(),
        "grand": DEFAULT_SETTINGS["grand"].copy(),
        "Pac_Call": DEFAULT_SETTINGS["Pac_Call"].copy(),
        "Squad": DEFAULT_SETTINGS["Squad"].copy(),
        "Sniper": DEFAULT_SETTINGS["Sniper"].copy(),
        "Lamix": DEFAULT_SETTINGS["Lamix"].copy(),
        "Num44": DEFAULT_SETTINGS["Num44"].copy(),
        "XAP": DEFAULT_SETTINGS["XAP"].copy(),
        "EMO SMS": DEFAULT_SETTINGS["EMO SMS"].copy(),
        "PRIM-FLASH": DEFAULT_SETTINGS["PRIM-FLASH"].copy()
    }
    
    for panel_name, panel_config in missing_panels.items():
        if panel_name not in settings:
            settings[panel_name] = panel_config
            migrated = True
            print(f"✅ تم إضافة موقع {panel_name} للإعدادات")

    # ترقية إعدادات MBC القديمة (كانت API-token) للنظام الجديد (يوزر/باسورد)
    if "MBC" in settings and "login_page_url" not in settings["MBC"]:
        old_mbc_accounts = settings["MBC"].get("accounts", [])
        new_mbc = DEFAULT_SETTINGS["MBC"].copy()
        # لو كان فيه حساب يوزر/باسورد قديم متسجل قبل التحويل لـ API نحافظ عليه
        preserved = [a for a in old_mbc_accounts if a.get("username")]
        if preserved:
            new_mbc["accounts"] = preserved
        settings["MBC"] = new_mbc
        migrated = True
        print("✅ تم ترقية إعدادات MBC للنظام الجديد (يوزر/باسورد)")
    
    # Handle Share migration
    if "Share" in settings:
        if "proton SMS" not in settings:
            settings["proton SMS"] = settings["Share"].copy()
            settings["proton SMS"]["name"] = "proton SMS"
            migrated = True
        del settings["Share"]
        migrated = True
    
    return settings, migrated

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                settings, migrated = migrate_old_settings(settings)
                if migrated:
                    save_settings(settings)
                return settings
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def get_site_accounts(site_key):
    return SETTINGS.get(site_key, {}).get("accounts", [])

def get_main_reply_keyboard(user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Get number", style="success", icon_custom_emoji_id="6093587384954262033"),
        KeyboardButton("Live Traffic", style="primary", icon_custom_emoji_id="6154657967317717391")
    )
    markup.row(
        KeyboardButton("My Wallet", style="primary", icon_custom_emoji_id="6001287064589439895"),
        KeyboardButton("My Stats", style="primary", icon_custom_emoji_id="5465295864970878728")
    )
    markup.row(KeyboardButton("WS CHECKER", style="primary", icon_custom_emoji_id="6206493566835889826"))
    if is_admin(user_id):
        markup.row(KeyboardButton("Admin Panel"))
    return markup

def add_account(site_key, username, password):
    if site_key not in SETTINGS:
        return False
    account = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password": password
    }
    if "accounts" not in SETTINGS[site_key]:
        SETTINGS[site_key]["accounts"] = []
    SETTINGS[site_key]["accounts"].append(account)
    save_settings(SETTINGS)
    return account

def delete_account(site_key, account_id):
    global account_stop_events
    if site_key not in SETTINGS or "accounts" not in SETTINGS[site_key]:
        return False
    accounts = SETTINGS[site_key]["accounts"]
    initial_count = len(accounts)
    SETTINGS[site_key]["accounts"] = [acc for acc in accounts if acc["id"] != account_id]
    if len(SETTINGS[site_key]["accounts"]) < initial_count:
        stop_key = f"{site_key}_{account_id}"
        if stop_key in account_stop_events:
            account_stop_events[stop_key].set()
            print(f"🛑 تم إيقاف مراقبة الحساب: {stop_key}")
            del account_stop_events[stop_key]
        
        cookies_file = f"cookies_{site_key}_{account_id}.pkl"
        last_message_file = f"last_message_{site_key}_{account_id}.txt"
        sent_messages_file = f"sent_messages_{site_key}_{account_id}.json"
        
        for file_path in [cookies_file, last_message_file, sent_messages_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ تم حذف ملف: {file_path}")
                except Exception as e:
                    print(f"⚠️ خطأ في حذف {file_path}: {e}")
        
        if stop_key in account_sessions:
            del account_sessions[stop_key]
        if stop_key in account_last_seen:
            del account_last_seen[stop_key]
        
        save_settings(SETTINGS)
        return True
    return False

def get_account_by_id(site_key, account_id):
    accounts = get_site_accounts(site_key)
    for acc in accounts:
        if acc["id"] == account_id or acc["id"].startswith(account_id):
            return acc
    return None

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

SETTINGS = load_settings()
SESSIONS = load_sessions()

def get_first_account(site_key):
    accounts = get_site_accounts(site_key)
    return accounts[0] if accounts else {"username": "", "password": ""}

USERNAME = get_first_account("GROUP").get("username", "")
PASSWORD = get_first_account("GROUP").get("password", "")
BASE_URL = SETTINGS["GROUP"]["base_url"]
LOGIN_PAGE_URL = SETTINGS["GROUP"]["login_page_url"]
LOGIN_POST_URL = SETTINGS["GROUP"]["login_post_url"]
AJAX_PATH = SETTINGS["GROUP"]["ajax_path"]
HTTP_TIMEOUT = SETTINGS["GROUP"]["timeout"]
CHECK_INTERVAL = SETTINGS["GROUP"]["check_interval"]

USERNAME2 = get_first_account("Fly sms").get("username", "")
PASSWORD2 = get_first_account("Fly sms").get("password", "")
BASE_URL2 = SETTINGS["Fly sms"]["base_url"]
LOGIN_PAGE_URL2 = SETTINGS["Fly sms"]["login_page_url"]
LOGIN_POST_URL2 = SETTINGS["Fly sms"]["login_post_url"]
AJAX_PATH2 = SETTINGS["Fly sms"]["ajax_path"]
HTTP_TIMEOUT2 = SETTINGS["Fly sms"]["timeout"]
CHECK_INTERVAL2 = SETTINGS["Fly sms"]["check_interval"]

USERNAME3 = get_first_account("Number_Panel").get("username", "")
PASSWORD3 = get_first_account("Number_Panel").get("password", "")
BASE_URL3 = SETTINGS["Number_Panel"]["base_url"]
LOGIN_PAGE_URL3 = SETTINGS["Number_Panel"].get("login_page_url", "")
LOGIN_POST_URL3 = SETTINGS["Number_Panel"].get("login_post_url", "")
AJAX_PATH3 = SETTINGS["Number_Panel"].get("ajax_path", "")
HTTP_TIMEOUT3 = SETTINGS["Number_Panel"]["timeout"]
CHECK_INTERVAL3 = SETTINGS["Number_Panel"]["check_interval"]

USERNAME4 = get_first_account("Bolt").get("username", "")
PASSWORD4 = get_first_account("Bolt").get("password", "")
BASE_URL4 = SETTINGS["Bolt"]["base_url"]
LOGIN_PAGE_URL4 = SETTINGS["Bolt"]["login_page_url"]
LOGIN_POST_URL4 = SETTINGS["Bolt"]["login_post_url"]
AJAX_PATH4 = SETTINGS["Bolt"]["ajax_path"]
HTTP_TIMEOUT4 = SETTINGS["Bolt"]["timeout"]
CHECK_INTERVAL4 = SETTINGS["Bolt"]["check_interval"]

USERNAME5 = get_first_account("iVASMS").get("username", "")
PASSWORD5 = get_first_account("iVASMS").get("password", "")
IVASMS_API_URL = SETTINGS["iVASMS"].get("api_url", "https://maroon-wombat-183778.hostingersite.com/apiivasms/api.php")
IVASMS_API_KEY = get_first_account("iVASMS").get("api_key", "")
HTTP_TIMEOUT5 = SETTINGS["iVASMS"]["timeout"]
CHECK_INTERVAL5 = SETTINGS["iVASMS"]["check_interval"]
LOGIN_PAGE_URL5 = ""
LOGIN_POST_URL5 = ""
SMS_RECEIVED_URL5 = ""
GET_SMS_URL5 = ""
GET_SMS_NUMBER_URL5 = ""
GET_SMS_MESSAGE_URL5 = ""

USERNAME6 = get_first_account("MSI").get("username", "")
PASSWORD6 = get_first_account("MSI").get("password", "")
BASE_URL6 = SETTINGS["MSI"]["base_url"]
LOGIN_PAGE_URL6 = SETTINGS["MSI"]["login_page_url"]
LOGIN_POST_URL6 = SETTINGS["MSI"]["login_post_url"]
AJAX_PATH6 = SETTINGS["MSI"]["ajax_path"]
HTTP_TIMEOUT6 = SETTINGS["MSI"]["timeout"]
CHECK_INTERVAL6 = SETTINGS["MSI"]["check_interval"]

USERNAME7 = get_first_account("proton SMS").get("username", "")
PASSWORD7 = get_first_account("proton SMS").get("password", "")
BASE_URL7 = SETTINGS["proton SMS"]["base_url"]
LOGIN_PAGE_URL7 = SETTINGS["proton SMS"]["login_page_url"]
LOGIN_POST_URL7 = SETTINGS["proton SMS"]["login_post_url"]
AJAX_PATH7 = SETTINGS["proton SMS"]["ajax_path"]
HTTP_TIMEOUT7 = SETTINGS["proton SMS"]["timeout"]
CHECK_INTERVAL7 = SETTINGS["proton SMS"]["check_interval"]

USERNAME8 = get_first_account("IMS").get("username", "")
PASSWORD8 = get_first_account("IMS").get("password", "")
BASE_URL8 = SETTINGS["IMS"]["base_url"]
LOGIN_PAGE_URL8 = SETTINGS["IMS"]["login_page_url"]
LOGIN_POST_URL8 = SETTINGS["IMS"]["login_post_url"]
AJAX_PATH8 = SETTINGS["IMS"]["ajax_path"]
HTTP_TIMEOUT8 = SETTINGS["IMS"]["timeout"]
CHECK_INTERVAL8 = SETTINGS["IMS"]["check_interval"]

USERNAME_IMS_NEW = get_first_account("IMS_New").get("username", "")
PASSWORD_IMS_NEW = get_first_account("IMS_New").get("password", "")
BASE_URL_IMS_NEW = SETTINGS["IMS_New"]["base_url"]
LOGIN_PAGE_URL_IMS_NEW = SETTINGS["IMS_New"]["login_page_url"]
LOGIN_POST_URL_IMS_NEW = SETTINGS["IMS_New"]["login_post_url"]
AJAX_PATH_IMS_NEW = SETTINGS["IMS_New"]["ajax_path"]
HTTP_TIMEOUT_IMS_NEW = SETTINGS["IMS_New"]["timeout"]
CHECK_INTERVAL_IMS_NEW = SETTINGS["IMS_New"]["check_interval"]


USERNAME9 = get_first_account("Roxy SMS").get("username", "")
PASSWORD9 = get_first_account("Roxy SMS").get("password", "")
BASE_URL9 = SETTINGS["Roxy SMS"]["base_url"]
LOGIN_PAGE_URL9 = SETTINGS["Roxy SMS"]["login_page_url"]
LOGIN_POST_URL9 = SETTINGS["Roxy SMS"]["login_post_url"]
AJAX_PATH9 = SETTINGS["Roxy SMS"]["ajax_path"]
HTTP_TIMEOUT9 = SETTINGS["Roxy SMS"]["timeout"]
CHECK_INTERVAL9 = SETTINGS["Roxy SMS"]["check_interval"]

# Seven1Tel Settings
USERNAME14 = get_first_account("Seven1Tel").get("username", "")
PASSWORD14 = get_first_account("Seven1Tel").get("password", "")
BASE_URL14 = SETTINGS["Seven1Tel"].get("base_url", "")
LOGIN_PAGE_URL14 = SETTINGS["Seven1Tel"].get("login_page_url", "")
LOGIN_POST_URL14 = SETTINGS["Seven1Tel"].get("login_post_url", "")
AJAX_PATH14 = SETTINGS["Seven1Tel"].get("ajax_path", "")
HTTP_TIMEOUT14 = SETTINGS["Seven1Tel"].get("timeout", 30)
CHECK_INTERVAL14 = SETTINGS["Seven1Tel"].get("check_interval", 5)

# Gaza SMS Settings
USERNAME15 = get_first_account("Gaza SMS").get("username", "")
PASSWORD15 = get_first_account("Gaza SMS").get("password", "")
BASE_URL15 = SETTINGS["Gaza SMS"].get("base_url", "")
LOGIN_PAGE_URL15 = SETTINGS["Gaza SMS"].get("login_page_url", "")
LOGIN_POST_URL15 = SETTINGS["Gaza SMS"].get("login_post_url", "")
AJAX_PATH15 = SETTINGS["Gaza SMS"].get("ajax_path", "")
HTTP_TIMEOUT15 = SETTINGS["Gaza SMS"].get("timeout", 30)
CHECK_INTERVAL15 = SETTINGS["Gaza SMS"].get("check_interval", 5)

# Km sms Settings
USERNAME16 = get_first_account("Km sms").get("username", "")
PASSWORD16 = get_first_account("Km sms").get("password", "")
BASE_URL16 = SETTINGS["Km sms"].get("base_url", "")
LOGIN_PAGE_URL16 = SETTINGS["Km sms"].get("login_page_url", "")
LOGIN_POST_URL16 = SETTINGS["Km sms"].get("login_post_url", "")
AJAX_PATH16 = SETTINGS["Km sms"].get("ajax_path", "")
HTTP_TIMEOUT16 = SETTINGS["Km sms"].get("timeout", 30)
CHECK_INTERVAL16 = SETTINGS["Km sms"].get("check_interval", 5)

# Grand SMS Settings
USERNAME17 = get_first_account("Grand SMS").get("username", "")
PASSWORD17 = get_first_account("Grand SMS").get("password", "")
BASE_URL17 = SETTINGS["Grand SMS"].get("base_url", "")
LOGIN_PAGE_URL17 = SETTINGS["Grand SMS"].get("login_page_url", "")
LOGIN_POST_URL17 = SETTINGS["Grand SMS"].get("login_post_url", "")
AJAX_PATH17 = SETTINGS["Grand SMS"].get("ajax_path", "")
HTTP_TIMEOUT17 = SETTINGS["Grand SMS"].get("timeout", 30)
CHECK_INTERVAL17 = SETTINGS["Grand SMS"].get("check_interval", 5)

# Purple SMS Settings
USERNAME18 = get_first_account("Purple SMS").get("username", "")
PASSWORD18 = get_first_account("Purple SMS").get("password", "")
BASE_URL18 = SETTINGS["Purple SMS"].get("base_url", "")
LOGIN_PAGE_URL18 = SETTINGS["Purple SMS"].get("login_page_url", "")
LOGIN_POST_URL18 = SETTINGS["Purple SMS"].get("login_post_url", "")
AJAX_PATH18 = SETTINGS["Purple SMS"].get("ajax_path", "")
HTTP_TIMEOUT18 = SETTINGS["Purple SMS"].get("timeout", 30)
CHECK_INTERVAL18 = SETTINGS["Purple SMS"].get("check_interval", 5)

# EMO SMS Settings
USERNAME_EMO = get_first_account("EMO SMS").get("username", "")
PASSWORD_EMO = get_first_account("EMO SMS").get("password", "")
BASE_URL_EMO = SETTINGS["EMO SMS"].get("base_url", "")
LOGIN_PAGE_URL_EMO = SETTINGS["EMO SMS"].get("login_page_url", "")
LOGIN_POST_URL_EMO = SETTINGS["EMO SMS"].get("login_post_url", "")
AJAX_PATH_EMO = SETTINGS["EMO SMS"].get("ajax_path", "")
HTTP_TIMEOUT_EMO = SETTINGS["EMO SMS"].get("timeout", 30)
CHECK_INTERVAL_EMO = SETTINGS["EMO SMS"].get("check_interval", 5)

# New API panels
KONEKTA_API_TOKEN = get_first_account("Konekta_API").get("api_token", "")
KONEKTA_API_URL = SETTINGS["Konekta_API"]["api_url"]

TIMESMS_API_TOKEN = get_first_account("TimeSMS_API").get("api_token", "")
TIMESMS_API_URL = SETTINGS["TimeSMS_API"]["api_url"]

FIRE_USERNAME = get_first_account("Fire_SMS").get("username", "")
FIRE_PASSWORD = get_first_account("Fire_SMS").get("password", "")
FIRE_BASE_URL = SETTINGS["Fire_SMS"]["base_url"]
FIRE_LOGIN_PAGE_URL = SETTINGS["Fire_SMS"]["login_page_url"]
FIRE_LOGIN_POST_URL = SETTINGS["Fire_SMS"]["login_post_url"]
FIRE_AJAX_PATH = SETTINGS["Fire_SMS"]["ajax_path"]

HADI_API_TOKEN = get_first_account("Hadi_SMS").get("api_token", "")
HADI_API_URL = SETTINGS["Hadi_SMS"]["api_url"]

# MBC API Settings
API_TOKEN_MBC = get_first_account("MBC").get("api_token", "GGQZI5UVE9P4tMgy6zTzH3zURnMClFBktSSFJQwkZtk")
BASE_URL_MBC = SETTINGS["MBC"].get("api_url", "http://93.127.134.108:20190/crapi/mbc/viewstats")
HTTP_TIMEOUT_MBC = SETTINGS["MBC"].get("timeout", 30)
CHECK_INTERVAL_MBC = SETTINGS["MBC"].get("check_interval", 5)

# Flash_SMS Settings
API_TOKEN_FLASH = get_first_account("Flash_SMS").get("api_token", "wK4gADTYNqE_YQEvWlxdxjoGRMmoSiIFZZHwlfStzo8")
BASE_URL_FLASH = SETTINGS["Flash_SMS"].get("api_url", "https://www.flashsms.space/api/cdr/viewstats")
HTTP_TIMEOUT_FLASH = SETTINGS["Flash_SMS"].get("timeout", 30)
CHECK_INTERVAL_FLASH = SETTINGS["Flash_SMS"].get("check_interval", 5)

# PRIM-FLASH Settings
API_TOKEN_PRIM_FLASH = get_first_account("PRIM-FLASH").get("api_token", "")
BASE_URL_PRIM_FLASH = SETTINGS["PRIM-FLASH"].get("api_url", "http://flashsms.space/api/cdr/viewstats")
HTTP_TIMEOUT_PRIM_FLASH = SETTINGS["PRIM-FLASH"].get("timeout", 30)
CHECK_INTERVAL_PRIM_FLASH = SETTINGS["PRIM-FLASH"].get("check_interval", 5)

# Horus Settings
API_TOKEN_HORUS = get_first_account("Horus").get("api_token", "AGT-7EIS7NW4")
API_URL_HORUS = get_first_account("Horus").get("api_url", "http://166.1.2.92/api/messages/cdr")
HTTP_TIMEOUT_HORUS = SETTINGS["Horus"].get("timeout", 30)
CHECK_INTERVAL_HORUS = SETTINGS["Horus"].get("check_interval", 5)

COOKIES_FILE = "cookies.pkl"
COOKIES_FILE_SITE3 = "cookies_site3.pkl"
COOKIES_FILE_SITE4 = "cookies_site4.pkl"
COOKIES_FILE_SITE5 = "cookies_ivasms.json"
COOKIES_FILE_SITE6 = "cookies_msi.pkl"
COOKIES_FILE_SITE7 = "cookies_share.pkl"
COOKIES_FILE_SITE8 = "cookies_ims.pkl"
COOKIES_FILE_SITE9 = "cookies_roxy.pkl"
LAST_MESSAGE_FILE = "last_message.txt"
LAST_MESSAGE_FILE_SITE2 = "last_message_site2.txt"
LAST_MESSAGE_FILE_SITE3 = "last_message_site3.txt"
LAST_MESSAGE_FILE_SITE4 = "last_message_site4.txt"
LAST_MESSAGE_FILE_SITE5 = "last_message_ivasms.txt"
LAST_MESSAGE_FILE_SITE6 = "last_message_msi.txt"
LAST_MESSAGE_FILE_SITE7 = "last_message_share.txt"
LAST_MESSAGE_FILE_SITE8 = "last_message_ims.txt"
LAST_MESSAGE_FILE_SITE9 = "last_message_roxy.txt"
COOKIES_FILE_SITE_IMS_NEW = "cookies_ims_new.pkl"
LAST_MESSAGE_FILE_SITE_IMS_NEW = "last_message_ims_new.txt"

account_scrapers = {}
account_sessions = {}
account_last_seen = {}
account_stop_events = {}

IDX_DATE_SITE3 = 0
IDX_NUMBER_SITE3 = 2
IDX_SMS_SITE3 = 5

def create_session_group():
    
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    })
    return sess

session1 = create_session_group()
is_logged_in_site1 = False
bot = telebot.TeleBot(BOT_TOKEN)
last_seen_key = ""
last_seen_key_site2 = ""
last_seen_key_site3 = ""
last_seen_key_site4 = ""

account_sessions = {}

session2 = requests.Session()
session2.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL2 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8"
})
is_logged_in_site2 = False
sesskey_site2 = None

session3 = requests.Session()
session3.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site3 = False

session4 = requests.Session()
session4.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site4 = False

session6 = requests.Session()
session6.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL6 + "/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site6 = False
last_seen_key_site6 = ""

session7 = requests.Session()
session7.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL7 + "/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site7 = False
last_seen_key_site7 = ""

session8 = requests.Session()
session8.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})
is_logged_in_site8 = False
last_seen_key_site8 = ""

session9 = requests.Session()
session9.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})
is_logged_in_site9 = False
last_seen_key_site9 = ""
session_ims_new = requests.Session()
session_ims_new.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})
is_logged_in_site_ims_new = False
last_seen_key_site_ims_new = ""


session14 = requests.Session()
session14.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL14 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site14 = False
last_seen_key_site14 = ""

session15 = requests.Session()
session15.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL15 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site15 = False
last_seen_key_site15 = ""

session16 = requests.Session()
session16.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL16 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site16 = False
last_seen_key_site16 = ""

session17 = requests.Session()
session17.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL17 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site17 = False
last_seen_key_site17 = ""

session18 = requests.Session()
session18.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL18 + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site18 = False
last_seen_key_site18 = ""

# Session for EMO SMS
session_emo = requests.Session()
session_emo.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL_EMO + "/ints/agent/SMSCDRReports",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_site_emo = False
last_seen_key_site_emo = ""

# Session for Flash_SMS (API-based)
session_flash = requests.Session()
session_flash.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_flash = False
last_seen_key_flash = ""

# Session for PRIM-FLASH (API-based)
session_prim_flash = requests.Session()
session_prim_flash.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_prim_flash = False
last_seen_key_prim_flash = ""

# Session for Horus (API-based)
session_horus = requests.Session()
session_horus.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
})
is_logged_in_horus = False
last_seen_key_horus = ""

# Session for Fire_SMS (same as Bolt type)
session_fire = requests.Session()
session_fire.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})
is_logged_in_fire = False

session5 = requests.Session()
session5.verify = False
session5.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
})
is_logged_in_site5 = False
csrf_token_site5 = None
last_seen_key_site5 = ""

COUNTRIES_FILE = "countriesi.json"
CHANNELS_FILE = "channelsi.json"
USERS_FILE = "usersiy.json"
ADMINS_FILE = "admins.ijson"
BANNED_FILE = "bannedi.json"
OTP_GROUP_FILE = "otp_groupi.json"
GROUPS_FILE = "groupsi.json"
STATISTICS_FILE = "statisticsi.json"
REFERRALS_FILE = "referralsi.json"
REFERRAL_SETTINGS_FILE = "referral_settings.json"
WITHDRAWAL_REQUESTS_FILE = "withdrawal_requests.json"
WITHDRAWAL_METHODS_FILE = "withdrawal_methods.json"
WELCOME_MESSAGES_FILE = "welcome_messages.json"
NUMBERS_ADMINS_FILE = "numbers_admins.json"
COUNTRIES = {}
CHANNELS = []
USERS = {}
ADMINS = []
BANNED = []
OTP_GROUP = -1004306930423
GROUPS = []
REFERRALS = {}
NUMBERS_ADMINS = []

def load_numbers_admins():
    global NUMBERS_ADMINS
    if os.path.exists(NUMBERS_ADMINS_FILE):
        try:
            with open(NUMBERS_ADMINS_FILE, "r", encoding="utf-8") as f:
                NUMBERS_ADMINS = json.load(f)
        except:
            NUMBERS_ADMINS = []
    return NUMBERS_ADMINS

def save_numbers_admins():
    with open(NUMBERS_ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(NUMBERS_ADMINS, f, indent=2, ensure_ascii=False)

def is_numbers_admin(user_id):
    return user_id in NUMBERS_ADMINS or is_admin(user_id)

DEFAULT_REFERRAL_SETTINGS = {
    "codes_required_for_referral": 10,
    "referral_bonus": 0.05,
    "code_bonus": 0.002,
    "min_withdrawal": 5.0,
    "enabled": True
}

DEFAULT_WELCOME_MESSAGES = {
    "ar": "🌐 <b>مرحباً بك في بوت الأرقام المؤقتة!</b>\n\n📱 احصل على رقم مؤقت فوراً\n🔒 آمن وسريع\n💰 اكسب من الإحالات والأكواد\n\nاختر من القائمة:",
    "en": "🌐 <b>Welcome to Temporary Numbers Bot!</b>\n\n📱 Get a temporary number instantly\n🔒 Secure and fast\n💰 Earn from referrals and codes\n\nChoose from the menu:"
}

DEFAULT_BUTTON_LINKS = {
    "group_link": "https://t.me/+EAViSkQrDzcxMjA0",
    "channel_link": "https://t.me/ME_YT",
    "developer_link": "https://t.me/MeDo_C2"
}

BUTTON_LINKS_FILE = "button_links.json"
OTP_BUTTONS_FILE = "otp_buttons.json"

DEFAULT_OTP_BUTTONS = [
    {"name": "Bot Link", "url": "https://t.me/ms_xbot"},
    {"name": "Channel", "url": "https://t.me/ms_xch"}
]

def load_otp_buttons():
    if os.path.exists(OTP_BUTTONS_FILE):
        try:
            with open(OTP_BUTTONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_OTP_BUTTONS.copy()

def save_otp_buttons(buttons):
    with open(OTP_BUTTONS_FILE, "w", encoding="utf-8") as f:
        json.dump(buttons, f, indent=2, ensure_ascii=False)

OTP_BUTTONS = load_otp_buttons()

def format_decimal(value):
    
    if value == 0:
        return "0"
    
    formatted = f"{value:.10f}".rstrip('0').rstrip('.')
    
    if '.' in formatted:
        integer_part, decimal_part = formatted.split('.')
        if len(decimal_part) > 5:
            decimal_part = decimal_part[:5]
        return f"{integer_part}.{decimal_part}"
    return formatted

def load_button_links():
    if os.path.exists(BUTTON_LINKS_FILE):
        try:
            with open(BUTTON_LINKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_BUTTON_LINKS.copy()

def save_button_links(links):
    with open(BUTTON_LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)

BUTTON_LINKS = load_button_links()
STATISTICS = {
    "total_codes": 0,
    "codes_today": 0,
    "codes_this_week": 0,
    "codes_this_month": 0,
    "last_reset_day": None,
    "last_reset_week": None,
    "last_reset_month": None,
    "daily_history": {},
    "recent_activations": [] # List of (timestamp, country_name)
}

user_states = {}
broadcast_state = {}

TEXTS = {
    "ar": {
        "welcome": "🌐 <b>مرحباً بك في بوت الأرقام!</b>",
        "instructions": "📖 <b>دليل البوت</b>\n\n<b>📱 استلام الأكواد:</b>\n1️⃣ اضغط Get Number\n2️⃣ اختر الدولة والرقم\n3️⃣ استخدم الرقم للتسجيل\n4️⃣ الكود يصلك تلقائياً\n\n<b>💰 الأرباح:</b>\n• بونص عن كل كود\n• بونص إحالة الأصدقاء\n\n<b>💵 السحب:</b>\nفودافون كاش - USDT - Binance",
        "subscription_locked": "🔒 <b>الوصول مقفل. انضم للقنوات ثم تحقق.</b>",
        "subscription_verified": "✅ <b>تم الVerify Subscription!</b>\n\n🌐 <b>مرحباً بك في بوت الأرقام!</b>",
        "subscription_not_verified": "❌ لم تنضم لجميع القنوات بعد!",
        "choose_country": "📲 𝗚𝗲𝘁 𝗡𝘂𝗺𝗯𝗲𝗿",
        "my_account": "👤 𝗠𝘆 𝗔𝗰𝗰𝗼𝘂𝗻𝘁",
        "admin_panel": "🎛 لوحة الإدارة",
        "help": "❓ مساعدة",
        "verify_subscription": "✅ Verify Subscription",
        "banned": "You Are Banned ⚠️",
        "unauthorized": "❌ غير مصرح لك!",
        "select_country": "📱 <b>اختر المنصة:</b>",
        "back": "🔙 رجوع",
        "select_number": "📞 <b>اختر رقم لـ {country}:</b>",
        "number_locked": "⚠️ هذا الرقم مستخدم حالياً من شخص آخر. اختر رقم آخر.",
        "your_number": "📞 <b>رقمك لـ {country}:</b>\n<code>+{number}</code>\n\n⏳ <b>في انتظار الكود...</b> 📱\n\n💬 سيتم إرسال الكود هنا مباشرة!",
        "change_number": "🔄 تغيير الرقم",
        "change_country": "🌍 تغيير الدولة",
        "account_info": "👤 <b>معلومات حسابك:</b>\n\n🆔 <b>معرفك:</b> <code>{user_id_value}</code>\n📅 <b>تاريخ الانضمام:</b> {join_date}\n📊 <b>الأكواد المستلمة:</b> {activations}\n🌐 <b>اللغة:</b> {language}\n\n💡 <b>حالة رقمك:</b>\n{number_status}",
        "no_number": "❌ لا يوجد رقم حالياً",
        "has_number": "✅ رقم نشط لـ {country}",
        "change_language": "🌐 تغيير اللغة",
        "language_changed": "✅ تم تغيير اللغة إلى العربية",
        "add_channel": "➕ إضافة قناة اشتراك",
        "remove_channel": "🗑 حذف قناة",
        "statistics": "📊 الإحصائيات",
        "broadcast": "📣 إذاعة",
        "add_admin": "🔧 إضافة مشرف",
        "remove_admin": "🗑 حذف مشرف",
        "ban_user": "Ban account ",
        "unban_user": "✅ إلغاء حظر",
        "set_otp_group": "📱 تعيين مجموعة OTP",
        "close": "❌ إغلاق",
        "new_code": "🔔 <b>كود جديد!</b>\n\n📞 <b>الرقم:</b> <code>+{number}</code>\n💬 <b>الكود:</b> <code>{code}</code>\n\n⏰ <b>الوقت:</b> {time}",
        "no_countries_available": "❌ لا توجد دول متاحة حالياً!",
        "country_not_available": "❌ دولة غير متاحة!",
        "no_numbers_available": "❌ لا توجد أرقام متاحة!",
        "number_reserved": "❌ هذا الرقم محجوز حالياً!",
        "select_country_first": "❌ اختر المنصة أولاً!",
        "number_changed": "✅ تم تغيير الرقم!",
        "admin_panel_title": "🎛 <b>لوحة الإدارة</b>",
        "statistics_title": "<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>إحصائيات البوت</b>\n\n👥 <b>إجمالي المستخدمين:</b> {users_count}\n🔢 <b>إجمالي الأكواد:</b> {total_codes}\n\n📅 <b>أكواد اليوم:</b> {codes_today}\n📆 <b>أكواد هذا الأسبوع:</b> {codes_this_week}\n📊 <b>أكواد هذا الشهر:</b> {codes_this_month}",
        "broadcast_prompt": "📣 <b>إذاعة رسالة</b>\n\nأرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:",
        "broadcast_sent": "✅ <b>تم الإرسال!</b>\n\n📤 نجح: {success}\n❌ فشل: {failed}",
        "set_otp_group_prompt": "📱 <b>تعيين مجموعة OTP</b>\n\nأرسل معرف المجموعة (Group ID) التي تريد إرسال الأكواد إليها:",
        "otp_group_set": "✅ <b>تم تعيين مجموعة OTP!</b>\n\n🆔 Group ID: <code>{group_id}</code>",
        "invalid_id": "❌ معرف غير صحيح! أرسل رقم ID صحيح",
        "add_channel_id_prompt": "➕ <b>إضافة قناة اشتراك إجباري</b>\n\n⚠️ يقبل فقط القنوات (لا مجموعات)\n\nأرسل معرف أو رابط القناة:\n• @channel_name\n• https://t.me/channel_name",
        "add_channel_name_prompt": "",
        "add_channel_url_prompt": "",
        "channel_added": "✅ <b>تم إضافة القناة!</b>\n\n📢 القناة: {channel_name}\n🔗 الرابط: {channel_url}",
        "user_banned": "✅ <b>تم حظر المستخدم!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "user_unbanned": "✅ <b>تم إلغاء حظر المستخدم!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "admin_added": "✅ <b>تم إضافة المشرف!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "admin_removed": "✅ <b>تم حذف المشرف!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "channel_removed": "✅ <b>تم حذف القناة!</b>\n\n📢 القناة: {channel_name}",
        "no_channels": "⚠️ لا توجد قنوات!",
        "no_banned_users": "⚠️ لا يوجد مستخدمون محظورون!",
        "no_admins": "⚠️ لا يوجد مشرفون!",
        "owner_only": "❌ هذه الميزة للمالك فقط!",
        "ban_user_prompt": "🚫 <b>حظر مستخدم</b>\n\nأرسل معرف المستخدم (User ID) الذي تريد حظره:",
        "unban_user_prompt": "✅ <b>إلغاء حظر مستخدم</b>\n\n📋 <b>المستخدمون المحظورون:</b>\n{banned_list}\n\nأرسل معرف المستخدم لإلغاء حظره:",
        "add_moderator_prompt": "🔧 <b>إضافة مشرف</b>\n\nأرسل معرف المستخدم (User ID) الذي تريد جعله مشرفاً:",
        "remove_moderator_prompt": "🗑 <b>حذف مشرف</b>\n\n📋 <b>المشرفون الحاليون:</b>\n{admins_list}\n\nأرسل معرف المشرف لحذفه:",
        "remove_channel_prompt": "🗑 <b>حذف قناة</b>\n\n📋 <b>القنوات الحالية:</b>\n{channels_list}\n\nأرسل رقم القناة أو معرفها لحذفها:",
        "channel_not_found": "❌ قناة غير موجودة!",
        "otp_group_status": "📱 <b>مجموعة الأكواد:</b>\n{status}",
        "otp_group_set_status": "✅ مجموعة محددة: <code>{group_id}</code>",
        "otp_group_not_set": "❌ لم يتم تحديد مجموعة",
        "delete_otp_group": "🗑 حذف المجموعة",
        "otp_group_deleted": "✅ تم حذف مجموعة الأكواد!",
        "top_users": "👥 أفضل 10 مستخدمين",
        "top_users_title": "👥 <b>أفضل 10 مستخدمين</b>\n<i>حسب عدد الأكواد المستلمة</i>\n\n",
        "no_users_yet": "⚠️ لا يوجد مستخدمون بعد!",
        "user_joined": "🎉 <b>انضم مستخدم جديد!</b>\n\n👤 الاسم: {name}\n🆔 ID: <code>{user_id}</code>\n📅 الوقت: {time}",
        "edit_button_labels_ar": "🇸🇦 تعديل الأزرار بالعربية",
        "edit_button_labels_en": "🇬🇧 تعديل الأزرار بالإنجليزية",
        "edit_button_labels_lang": "🏷️ <b>تعديل أسماء الأزرار</b>\n\nاختر اللغة:",
        "edit_labels_ar_menu": "🇸🇦 <b>تعديل الأزرار بالعربية</b>\n\nاختر الزر الذي تريد تعديله:",
        "edit_labels_en_menu": "🇬🇧 <b>Edit Button Labels (English)</b>\n\nChoose the button you want to edit:",
        "edit_choose_country_ar": "تعديل \"اختر دولة\"",
        "edit_my_account_ar": "تعديل \"حسابي\"",
        "edit_help_ar": "تعديل \"𝗛𝗲𝗹𝗽❓\"",
        "edit_choose_country_en": "Edit \"Choose Country\"",
        "edit_my_account_en": "Edit \"My Account\"",
        "edit_help_en": "Edit \"Help\"",
        "send_new_label": "📝 أرسل الاسم الجديد للزر:",
        "label_updated": "✅ تم تحديث اسم الزر بنجاح!",
        "manage_otp_group": "📱 إدارة مجموعة الأكواد",
        "welcome_admin": "🌐 <b>مرحباً بك في بوت OTP!</b>\n\nاختر دولة لاستقبال رقم وانتظر الأكواد.\n\nكمشرف، يمكنك أيضاً الوصول للوحة الأدمن.",
        "choose_language": "🌍 <b>اختر اللغة / Choose Language</b>",
        "group_hello_admin": "👋 مرحباً! أنا بوت OTP.\n\n⚠️ <b>ملاحظة:</b> لا يمكن إضافة الجروبات تلقائياً.\nيجب على المشرف إضافة هذا الجروب من لوحة الأدمن.",
        "group_hello": "👋 مرحباً! أنا بوت OTP.\n\nللاستخدام، تواصل معي بشكل خاص.",
        "total_users": "👥 <b>إجمالي المستخدمين:</b>",
        "total_codes": "🔢 <b>إجمالي الأكواد:</b>",
        "codes_today": "📅 <b>أكواد اليوم:</b>",
        "codes_week": "📆 <b>أكواد هذا الأسبوع:</b>",
        "codes_month": "📊 <b>أكواد هذا الشهر:</b>",
        "users_text": "users / مستخدم",
        "developer_btn": "🆘 المطور",
        "verify_btn": "✅ تحقق",
        "select_server_title": "🖥️ <b>اختر السيرفر</b>",
        "select_server_desc": "📌 كل سيرفر يحتوي على مجموعة مختلفة من الدول والأرقام:",
        "select_server_hint": "🔻 <i>اختر السيرفر لعرض الدول المتاحة</i>",
        "select_platform_title": "📱 <b>اختر المنصة في {server}</b>",
        "select_platform_hint": "🔻 <i>اختر المنصة التي تريد استقبال أكوادها</i>",
        "no_numbers_here": "❌ <b>لا يوجد أرقام هنا</b>",
        "no_countries_title": "❌ <b>لا توجد دول متاحة</b>",
        "server_label": "🖥️ <b>السيرفر:</b>",
        "platform_label": "📱 <b>المنصة:</b>",
        "no_countries_hint": "🔻 <i>لا توجد دول متاحة لهذه المنصة في هذا السيرفر حالياً</i>",
        "available_countries_title": "🌍 <b>الدول المتاحة</b>",
        "select_country_hint": "🔻 <i>اختر الدولة التي تريد استقبال أكوادها</i>",
        "number_selected_success": "✅ <b>تم اختيار الرقم بنجاح!</b>",
        "waiting_for_code": "⏳ 𝓦𝓪𝓲𝓽𝓲𝓷𝓰 𝓯𝓸𝓻 𝓽𝓱𝓮 𝓬𝓸𝓭𝓮... 📱",
        "code_will_be_sent": "سيتم إرسال الكود لك مباشرة عند وصوله!",
        "change_number_btn": "🔄 تغيير الرقم",
        "change_country_btn": "🌍 تغيير الدولة",
        "back_to_servers": "𝗕𝗮𝗰𝗸 𝘁𝗼 𝘀𝗲𝗿𝘃𝗲𝗿𝘀",
        "error_msg": "❌ خطأ: {error}",
        "referral_success": "🎉 <b>تم تسجيلك بنجاح عبر رابط الإحالة!</b>\n\nاستمتع باستخدام البوت!"
    },
    "en": {
        "welcome": "╔════✦  𝓑𝓞𝓣𝓟  ✦════╗\n\n❖  𝗚𝗿𝗮𝗯 𝗮 𝘁𝗲𝗺𝗽𝗼𝗿𝗮𝗿𝘆 𝗻𝘂𝗺𝗯𝗲𝗿 𝗶𝗻𝘀𝘁𝗮𝗻𝘁𝗹𝘆\n❖  𝗟𝗶𝗴𝗵𝘁𝗻𝗶𝗻𝗴-𝗳𝗮𝘀𝘁 & 𝗳𝘂𝗹𝗹𝘆 𝘀𝗲𝗰𝘂𝗿𝗲\n❖  𝗪𝗼𝗿𝗸𝘀 𝗳𝗼𝗿 𝗮𝗹𝗹 𝗰𝗼𝘂𝗻𝘁𝗿𝗶𝗲𝘀\n\n•  𝗦𝗲𝗹𝗲𝗰𝘁 𝘆𝗼𝘂𝗿 𝗰𝗼𝘂𝗻𝘁𝗿𝘆\n•  𝗚𝗲𝘁 𝘆𝗼𝘂𝗿 𝗻𝘂𝗺𝗯𝗲𝗿 𝗶𝗺𝗺𝗲𝗱𝗶𝗮𝘁𝗲𝗹𝘆\n\n╚════✦  𝓑𝓞𝓣𝓟  ✦════╝",
        "instructions": "📖 <b>Bot Guide</b>\n\n<b>📱 Receiving Codes:</b>\n1️⃣ Click Get Number\n2️⃣ Choose country and number\n3️⃣ Use number to register\n4️⃣ Code arrives automatically\n\n<b>💰 Earnings:</b>\n• Bonus for each code\n• Referral bonus for friends\n\n<b>💵 Withdrawal:</b>\nVodafone Cash - USDT - Binance",
        "subscription_locked": "🔒 <b>Access locked. Join channels then verify.</b>",
        "subscription_verified": "✅ <b>Subscription verified!</b>\n\n🌐 <b>Welcome to Numbers Bot!</b>",
        "subscription_not_verified": "❌ You haven't joined all channels yet!",
        "choose_country": "📲 𝗚𝗲𝘁 𝗡𝘂𝗺𝗯𝗲𝗿",
        "my_account": "👤 𝗠𝘆 𝗔𝗰𝗰𝗼𝘂𝗻𝘁",
        "admin_panel": "🎛 Admin Panel",
        "help": "❓ Help",
        "verify_subscription": "✅ Verify Subscription",
        "banned": "🚫 You are banned from using this bot.",
        "unauthorized": "❌ Unauthorized!",
        "select_country": "🌍 <b>Select Country:</b>",
        "back": "🔙 Back",
        "select_number": "📞 <b>Select a number for {country}:</b>",
        "number_locked": "⚠️ This number is currently used by someone else. Choose another number.",
        "your_number": "📞 <b>Your number for {country}:</b>\n<code>+{number}</code>\n\n⏳ <b>Waiting for code...</b> 📱\n\n💬 Code will be sent here directly!",
        "change_number": "🔄 Change Number",
        "change_country": "🌍 Change Country",
        "account_info": "👤 <b>Your Account Info:</b>\n\n🆔 <b>ID:</b> <code>{user_id_value}</code>\n📅 <b>Join Date:</b> {join_date}\n📊 <b>Codes Received:</b> {activations}\n🌐 <b>Language:</b> {language}\n\n💡 <b>Number Status:</b>\n{number_status}",
        "no_number": "❌ No number currently",
        "has_number": "✅ Active number for {country}",
        "change_language": "🌐 Change Language",
        "language_changed": "✅ Language changed to English",
        "add_channel": "➕ Add Channel",
        "remove_channel": "🗑 Remove Channel",
        "statistics": "📊 Statistics",
        "broadcast": "📣 Broadcast",
        "add_admin": "🔧 Add Admin",
        "remove_admin": "🗑 Remove Admin",
        "ban_user": "🚫 Ban User",
        "unban_user": "✅ Unban User",
        "set_otp_group": "📱 Set OTP Group",
        "close": "❌ Close",
        "new_code": "🔔 <b>New Code!</b>\n\n📞 <b>Number:</b> <code>+{number}</code>\n💬 <b>Code:</b> <code>{code}</code>\n\n⏰ <b>Time:</b> {time}",
        "no_countries_available": "❌ No countries available!",
        "country_not_available": "❌ Country not available!",
        "no_numbers_available": "❌ No numbers available!",
        "number_reserved": "❌ This number is reserved!",
        "select_country_first": "❌ Select a country first!",
        "number_changed": "✅ Number changed!",
        "admin_panel_title": "🎛 <b>Admin Panel</b>",
        "statistics_title": "📊 <b>Bot Statistics</b>\n\n👥 <b>Total Users:</b> {users_count}\n🔢 <b>Total Codes:</b> {total_codes}\n\n📅 <b>Today's Codes:</b> {codes_today}\n📆 <b>This Week's Codes:</b> {codes_this_week}\n📊 <b>This Month's Codes:</b> {codes_this_month}",
        "broadcast_prompt": "📣 <b>Broadcast Message</b>\n\nSend the message you want to broadcast to all users:",
        "broadcast_sent": "✅ <b>Sent!</b>\n\n📤 Success: {success}\n❌ Failed: {failed}",
        "set_otp_group_prompt": "📱 <b>Set OTP Group</b>\n\nSend the Group ID where you want to receive OTP codes:",
        "otp_group_set": "✅ <b>OTP Group set!</b>\n\n🆔 Group ID: <code>{group_id}</code>",
        "invalid_id": "❌ Invalid ID! Send a valid ID number",
        "add_channel_id_prompt": "➕ <b>Add Subscription Channel</b>\n\nSend the channel ID (example: @channelname or -100...):",
        "add_channel_name_prompt": "✅ <b>Channel ID saved!</b>\n\nNow send the channel name:",
        "add_channel_url_prompt": "✅ <b>Channel name saved!</b>\n\nNow send the channel link (https://t.me/...):",
        "channel_added": "✅ <b>Channel added!</b>\n\n📢 Channel: {channel_name}\n🔗 Link: {channel_url}",
        "user_banned": "✅ <b>User banned!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "user_unbanned": "✅ <b>User unbanned!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "admin_added": "✅ <b>Admin added!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "admin_removed": "✅ <b>Admin removed!</b>\n\n🆔 User ID: <code>{target_user_id}</code>",
        "channel_removed": "✅ <b>Channel removed!</b>\n\n📢 Channel: {channel_name}",
        "no_channels": "⚠️ No channels!",
        "no_banned_users": "⚠️ No banned users!",
        "no_admins": "⚠️ No admins!",
        "owner_only": "❌ This feature is for owner only!",
        "ban_user_prompt": "🚫 <b>Ban User</b>\n\nSend the User ID you want to ban:",
        "unban_user_prompt": "✅ <b>Unban User</b>\n\n📋 <b>Banned Users:</b>\n{banned_list}\n\nSend the User ID to unban:",
        "add_moderator_prompt": "🔧 <b>Add Admin</b>\n\nSend the User ID you want to make admin:",
        "remove_moderator_prompt": "🗑 <b>Remove Admin</b>\n\n📋 <b>Current Admins:</b>\n{admins_list}\n\nSend the admin ID to remove:",
        "remove_channel_prompt": "🗑 <b>Remove Channel</b>\n\n📋 <b>Current Channels:</b>\n{channels_list}\n\nSend the channel number or ID to remove it:",
        "channel_not_found": "❌ Channel not found!",
        "otp_group_status": "📱 <b>OTP Group:</b>\n{status}",
        "otp_group_set_status": "✅ Group set: <code>{group_id}</code>",
        "otp_group_not_set": "❌ No group set",
        "delete_otp_group": "🗑 Delete Group",
        "otp_group_deleted": "✅ OTP group deleted!",
        "top_users": "👥 Top 10 Users",
        "top_users_title": "👥 <b>Top 10 Users</b>\n<i>By codes received</i>\n\n",
        "no_users_yet": "⚠️ No users yet!",
        "user_joined": "🎉 <b>New User Joined!</b>\n\n👤 Name: {name}\n🆔 ID: <code>{user_id}</code>\n📅 Time: {time}",
        "edit_button_labels_ar": "🇸🇦 Edit Arabic Buttons",
        "edit_button_labels_en": "🇬🇧 Edit English Buttons",
        "edit_button_labels_lang": "🏷️ <b>Edit Button Labels</b>\n\nChoose language:",
        "edit_labels_ar_menu": "🇸🇦 <b>تعديل الأزرار بالعربية</b>\n\nاختر الزر الذي تريد تعديله:",
        "edit_labels_en_menu": "🇬🇧 <b>Edit Button Labels (English)</b>\n\nChoose the button you want to edit:",
        "edit_choose_country_ar": "تعديل \"اختر دولة\"",
        "edit_my_account_ar": "تعديل \"حسابي\"",
        "edit_help_ar": "تعديل \"𝗛𝗲𝗹𝗽❓\"",
        "edit_choose_country_en": "Edit \"Choose Country\"",
        "edit_my_account_en": "Edit \"My Account\"",
        "edit_help_en": "Edit \"Help\"",
        "send_new_label": "📝 Send the new button name:",
        "label_updated": "✅ Button label updated successfully!",
        "manage_otp_group": "📱 Manage OTP Group",
        "welcome_admin": "🌐 <b>Welcome to OTP Bot!</b>\n\nChoose a country to receive a number and wait for OTP.\n\nAs an admin, you can also access the Admin Panel.",
        "choose_language": "🌍 <b>اختر اللغة / Choose Language</b>",
        "group_hello_admin": "👋 Hello! I'm the OTP Bot.\n\n⚠️ <b>Note:</b> Groups cannot be added automatically.\nThe admin must add this group from the admin panel.",
        "group_hello": "👋 Hello! I'm the OTP Bot.\n\nTo use me, contact me privately.",
        "total_users": "👥 <b>Total Users:</b>",
        "total_codes": "🔢 <b>Total Codes:</b>",
        "codes_today": "📅 <b>Codes Today:</b>",
        "codes_week": "📆 <b>Codes This Week:</b>",
        "codes_month": "📊 <b>Codes This Month:</b>",
        "users_text": "users",
        "developer_btn": "🆘 Developer",
        "verify_btn": "✅ Verify",
        "select_server_title": "🖥️ <b>Select Server</b>",
        "select_server_desc": "📌 Each server contains a different set of countries and numbers:",
        "select_server_hint": "🔻 <i>Select a server to view available countries</i>",
        "select_platform_title": "📱 <b>Select Platform in {server}</b>",
        "select_platform_hint": "🔻 <i>Select the platform you want to receive codes for</i>",
        "no_numbers_here": "❌ <b>No numbers available here</b>",
        "no_countries_title": "❌ <b>No countries available</b>",
        "server_label": "🖥️ <b>Server:</b>",
        "platform_label": "📱 <b>Platform:</b>",
        "no_countries_hint": "🔻 <i>No countries available for this platform in this server currently</i>",
        "available_countries_title": "🌍 <b>Available Countries</b>",
        "select_country_hint": "🔻 <i>Select the country you want to receive codes for</i>",
        "number_selected_success": "✅ <b>Number selected successfully!</b>",
        "waiting_for_code": "⏳ 𝓦𝓪𝓲𝓽𝓲𝓷𝓰 𝓯𝓸𝓻 𝓽𝓱𝓮 𝓬𝓸𝓭𝓮... 📱",
        "code_will_be_sent": "The code will be sent to you directly when it arrives!",
        "change_number_btn": "🔄 Change Number",
        "change_country_btn": "🌍 Change Country",
        "back_to_servers": "𝗕𝗮𝗰𝗸 𝘁𝗼 𝘀𝗲𝗿𝘃𝗲𝗿𝘀",
        "sticker_duration_error": "❌ Duration must be between 0.1 and 30 seconds!",
        "sticker_duration_set": "✅ <b>Sticker display duration set!</b>\n\n⏱ New duration: {duration} seconds",
        "invalid_number": "❌ Please send a valid number!\n\nExample: 0.5 or 1 or 2.5",
        "error_msg": "❌ Error: {error}",
        "referral_success": "🎉 <b>You've registered successfully via referral link!</b>\n\nEnjoy using the bot!"
    }
}

def get_user_language(user_id):
    user_data = USERS.get(str(user_id), {})
    return user_data.get("language", "ar")

def set_user_language(user_id, lang):
    if str(user_id) not in USERS:
        USERS[str(user_id)] = {}
    USERS[str(user_id)]["language"] = lang
    save_users()

def t(user_id, key):
    lang = get_user_language(user_id)
    return TEXTS.get(lang, TEXTS["ar"]).get(key, key)

def save_pickle(path, obj):
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load_pickle(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

def save_cookies():
    cookies_dict = session1.cookies.get_dict()
    save_pickle(COOKIES_FILE, cookies_dict)

def load_cookies():
    d = load_pickle(COOKIES_FILE)
    if isinstance(d, dict) and d:
        session1.cookies.update(d)
        return True
    return False

def clear_cookies():
    session1.cookies.clear()
    if os.path.exists(COOKIES_FILE):
        try:
            os.remove(COOKIES_FILE)
            return True
        except:
            return False
    return True

def save_cookies_site3():
    cookies_dict = session3.cookies.get_dict()
    save_pickle(COOKIES_FILE_SITE3, cookies_dict)
    print("[Site3/Number_Panel] 💾 تم حفظ الجلسة")

def load_cookies_site3():
    d = load_pickle(COOKIES_FILE_SITE3)
    if isinstance(d, dict) and d:
        session3.cookies.update(d)
        print("[Site3/Number_Panel] 📥 تم تحميل الجلسة المحفوظة")
        return True
    print("[Site3/Number_Panel] ⚠️ لا توجد جلسة محفوظة")
    return False

def save_cookies_site4():
    cookies_dict = session4.cookies.get_dict()
    save_pickle(COOKIES_FILE_SITE4, cookies_dict)
    print("[Site4/Bolt] 💾 تم حفظ الجلسة")

def load_cookies_site4():
    d = load_pickle(COOKIES_FILE_SITE4)
    if isinstance(d, dict) and d:
        session4.cookies.update(d)
        print("[Site4/Bolt] 📥 تم تحميل الجلسة المحفوظة")
        return True
    print("[Site4/Bolt] ⚠️ لا توجد جلسة محفوظة")
    return False

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)

def login_attempt_group():
    
    global session1, is_logged_in_site1
    
    try:
        print(f"[GROUP] 🔄 جلب صفحة تسجيل الدخول...")
        resp = session1.get(LOGIN_PAGE_URL, timeout=HTTP_TIMEOUT)
        
        if resp.status_code != 200:
            print(f"[GROUP] ⚠️ فشل فتح صفحة الدخول: {resp.status_code}")
            return False
        
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            print("[GROUP] ❌ لم يتم العثور على captcha في صفحة تسجيل الدخول")
            return False
        
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2
        print(f"[GROUP] 🧮 حل captcha: {num1} + {num2} = {captcha_answer}")
        
        payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "capt": str(captcha_answer)
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE_URL,
            "Origin": BASE_URL,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        print(f"[GROUP] 📤 إرسال طلب تسجيل الدخول لـ: {USERNAME}")
        
        resp = session1.post(LOGIN_POST_URL, data=payload, headers=headers, timeout=HTTP_TIMEOUT, allow_redirects=True)
        
        print(f"[GROUP] 📊 حالة الاستجابة: {resp.status_code}")
        
        if ("dashboard" in resp.text.lower() or 
            "logout" in resp.text.lower() or 
            "agent" in resp.url.lower() or
            "/ints/agent" in resp.url or
            resp.url != LOGIN_PAGE_URL):
            print("[GROUP] ✅ تم تسجيل الدخول بنجاح")
            is_logged_in_site1 = True
            save_cookies()
            
            print("[GROUP] 🔄 زيارة صفحة SMSCDRReports بعد تسجيل الدخول...")
            try:
                session1.get(BASE_URL + "/ints/agent/SMSCDRReports", timeout=HTTP_TIMEOUT)
                print("[GROUP] ✅ تم زيارة صفحة SMSCDRReports بنجاح")
                time.sleep(1)
            except Exception as e:
                print(f"[GROUP] ⚠️ خطأ في زيارة صفحة SMSCDRReports: {e}")
            
            return True
        else:
            print("[GROUP] ❌ فشل تسجيل الدخول")
            if "incorrect" in resp.text.lower() or "invalid" in resp.text.lower():
                print("[GROUP] ⚠️ اسم المستخدم أو كلمة المرور غير صحيحة")
            return False
            
    except requests.exceptions.Timeout:
        print(f"[GROUP] ⏱️ انتهى وقت الاتصال")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"[GROUP] 🔌 خطأ في الاتصال: {e}")
        return False
    except Exception as e:
        print(f"[GROUP] ❌ خطأ في تسجيل الدخول: {e}")
        return False

def login(max_retries=10):
    
    global session1, is_logged_in_site1
    print(f"🔐 GROUP: بدء تسجيل الدخول...")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔄 GROUP: المحاولة {attempt}/{max_retries}")
            
            if attempt > 1:
                print(f"🔄 GROUP: تجديد الجلسة...")
                session1 = create_session_group()
                time.sleep(2)
            
            if login_attempt_group():
                print(f"✅ GROUP: نجح تسجيل الدخول في المحاولة {attempt}")
                return True
            
            backoff_time = min(30, 5 * attempt)
            print(f"⏳ GROUP: الانتظار {backoff_time}s قبل المحاولة التالية...")
            time.sleep(backoff_time)
            
        except Exception as e:
            print(f"❌ GROUP (محاولة {attempt}): خطأ - {str(e)}")
            time.sleep(5)
    
    print(f"❌ GROUP: فشل تسجيل الدخول بعد {max_retries} محاولات")
    return False

def check_login_valid():
    try:
        test_url = BASE_URL + "/ints/agent/res/data_smscdr.php?per-page=10"
        ajax_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": BASE_URL + "/ints/agent/SMSCDRReports"
        }
        r = session1.get(test_url, headers=ajax_headers, timeout=15)
        if r.status_code == 200:
            if "login" in r.text.lower() or "sign in" in r.text.lower():
                return False
            if "direct script access not allowed" in r.text.lower():
                return False
            return True
        return False
    except Exception as e:
        return False


def login_ims_new(account):
    """تسجيل الدخول لـ IMS_New (نفس آلية IMS لكن بـ https)"""
    username = account.get("username", "")
    password = account.get("password", "")
    base_url = SETTINGS["IMS_New"]["base_url"]
    login_page_url = SETTINGS["IMS_New"]["login_page_url"]
    login_post_url = SETTINGS["IMS_New"]["login_post_url"]
    timeout = SETTINGS["IMS_New"]["timeout"]

    session = requests.Session()
    session.verify = False
    print(f"[IMS_New] ({username}) 🔄 محاولة تسجيل الدخول...")
    try:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        resp = session.get(login_page_url, timeout=timeout)
        soup = BeautifulSoup(resp.text, 'html.parser')

        captcha_answer = None
        patterns = [r'What is (\d+) \+ (\d+)', r'(\d+)\s*\+\s*(\d+)\s*=', r'(\d+)\s*plus\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, resp.text, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break

        if not captcha_answer:
            print(f"[IMS_New] ({username}) ⚠️ لم يتم العثور على captcha")
            return False, None

        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'}) or soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value', ''))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content', ''))
        if not csrf_token:
            m = re.search(r'''name=['"]_token['"].*?value=['"]([^'"]+)['"]''', resp.text)
            if m:
                csrf_token = m.group(1)

        login_data = {"username": username, "password": password, "capt": captcha_answer}
        if csrf_token:
            login_data["_token"] = csrf_token

        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''

        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(login_post_url, data=login_data, headers=login_headers, timeout=timeout, allow_redirects=True)
        print(f"[IMS_New] ({username}) DEBUG Final URL: {response.url}")

        if any(x in response.url.lower() for x in ["/client", "/dashboard", "/home"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[IMS_New] ({username}) ✅ تسجيل الدخول نجح")
            return True, session

        content_lower = response.text.lower()
        if "logout" in content_lower or "smscdr" in content_lower or "client" in content_lower:
            print(f"[IMS_New] ({username}) ✅ تسجيل الدخول نجح (via content)")
            return True, session

        print(f"[IMS_New] ({username}) ❌ فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[IMS_New] ({username}) ❌ خطأ: {e}")
        return False, None

def login_generic_ints(site_key, account=None):
    """Generic login function for standard /ints/ panels like Km sms, Flex, rsayel, ksi, green"""
    site_label = SETTINGS[site_key]["name"]
    print(f"[{site_label}] 🔄 محاولة تسجيل الدخول...")

    user = account.get("username") if account else SETTINGS[site_key].get("accounts", [{}])[0].get("username", "")
    pw   = account.get("password") if account else SETTINGS[site_key].get("accounts", [{}])[0].get("password", "")
    base_url = SETTINGS[site_key]["base_url"]
    login_page = SETTINGS[site_key]["login_page_url"]
    login_post = SETTINGS[site_key]["login_post_url"]
    timeout = SETTINGS[site_key].get("timeout", 30)

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": base_url + "/ints/agent/SMSCDRReports",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8"
    })

    try:
        resp = sess.get(login_page, timeout=timeout)
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        captcha = str(int(match.group(1)) + int(match.group(2))) if match else None

        payload = {'username': user, 'password': pw}
        if captcha:
            payload['capt'] = captcha

        crlf = re.search(r"name=['\"]crlf['\"].*?value=['\"]([^'\"]+)['\"]", resp.text)
        if not crlf:
            crlf = re.search(r"value=['\"]([^'\"]+)['\"].*?name=['\"]crlf['\"]", resp.text)
        if crlf:
            payload['crlf'] = crlf.group(1)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_page,
            'Origin': base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        r = sess.post(login_post, data=payload, headers=headers, timeout=timeout, allow_redirects=True)

        success = (any(k in r.text.lower() for k in ["dashboard", "logout", "agent", "reports", "smscdr"]) or
                   any(k in r.url.lower() for k in ["dashboard", "agent", "reports"]) or
                   r.url != login_page)
        if success:
            print(f"[{site_label}] ✅ تم تسجيل الدخول بنجاح")
            return sess if account else True
        else:
            print(f"[{site_label}] ❌ فشل تسجيل الدخول")
            return False
    except Exception as e:
        print(f"[{site_label}] ❌ خطأ في تسجيل الدخول: {e}")
        return False

def login_green(account):
    """تسجيل الدخول لـ Green (نفس آلية IMS - لوحة /ints/)"""
    username = account.get("username", "")
    password = account.get("password", "")
    base_url = SETTINGS["green"]["base_url"]
    login_page_url = SETTINGS["green"]["login_page_url"]
    login_post_url = SETTINGS["green"]["login_post_url"]
    timeout = SETTINGS["green"]["timeout"]

    session = requests.Session()
    session.verify = False
    print(f"[Green] ({username}) 🔄 محاولة تسجيل الدخول...")
    try:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        resp = session.get(login_page_url, timeout=timeout)
        soup = BeautifulSoup(resp.text, 'html.parser')

        captcha_answer = None
        patterns = [r'What is (\d+) \+ (\d+)', r'(\d+)\s*\+\s*(\d+)\s*=', r'(\d+)\s*plus\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, resp.text, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break

        if not captcha_answer:
            b_tags = soup.find_all('b')
            nums = []
            for b in b_tags:
                text = b.get_text().strip()
                if text.isdigit():
                    nums.append(int(text))
            if len(nums) >= 2:
                captcha_answer = str(nums[0] + nums[1])

        if not captcha_answer:
            print(f"[Green] ({username}) ⚠️ لم يتم العثور على captcha")
            return False, None

        print(f"[Green] ({username}) [*] Captcha: {captcha_answer}")

        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'}) or soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value', ''))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content', ''))

        login_data = {
            "username": username,
            "password": password,
            "capt": captcha_answer,
        }
        if csrf_token:
            login_data["_token"] = csrf_token

        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and isinstance(name, str) and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''

        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(login_post_url, data=login_data, headers=login_headers,
                                timeout=timeout, allow_redirects=True)

        print(f"[Green] ({username}) [DEBUG] Final URL: {response.url}")

        if any(x in response.url.lower() for x in ["/agent", "/dashboard", "/home"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[Green] ({username}) [+] تسجيل الدخول نجح")
            return True, session

        content_lower = response.text.lower()
        if "logout" in content_lower or "smscdr" in content_lower or "agent" in content_lower:
            print(f"[Green] ({username}) [+] تسجيل الدخول نجح (Detected via content)")
            return True, session

        print(f"[Green] ({username}) [!] فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[Green] ({username}) [!] خطأ: {e}")
        return False, None

def login_ksi(account):
    """تسجيل الدخول لـ KSI (نفس آلية IMS - لوحة /ints/)"""
    username = account.get("username", "")
    password = account.get("password", "")
    base_url = SETTINGS["ksi"]["base_url"]
    login_page_url = SETTINGS["ksi"]["login_page_url"]
    login_post_url = SETTINGS["ksi"]["login_post_url"]
    timeout = SETTINGS["ksi"]["timeout"]

    session = requests.Session()
    session.verify = False
    print(f"[KSI] ({username}) 🔄 محاولة تسجيل الدخول...")
    try:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        resp = session.get(login_page_url, timeout=timeout)
        soup = BeautifulSoup(resp.text, 'html.parser')

        captcha_answer = None
        patterns = [r'What is (\d+) \+ (\d+)', r'(\d+)\s*\+\s*(\d+)\s*=', r'(\d+)\s*plus\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, resp.text, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break

        if not captcha_answer:
            print(f"[KSI] ({username}) ⚠️ لم يتم العثور على captcha")
            return False, None

        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'}) or soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value', ''))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content', ''))
        if not csrf_token:
            m = re.search(r"name=['\"]_token['\"].*?value=['\"]([^'\"]+)['\"]", resp.text)
            if m:
                csrf_token = m.group(1)

        login_data = {"username": username, "password": password, "capt": captcha_answer}
        if csrf_token:
            login_data["_token"] = csrf_token

        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''

        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(login_post_url, data=login_data, headers=login_headers, timeout=timeout, allow_redirects=True)
        print(f"[KSI] ({username}) DEBUG Final URL: {response.url}")

        if any(x in response.url.lower() for x in ["/agent", "/dashboard", "/home"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[KSI] ({username}) ✅ تسجيل الدخول نجح")
            return True, session

        content_lower = response.text.lower()
        if "logout" in content_lower or "smscdr" in content_lower or "agent" in content_lower:
            print(f"[KSI] ({username}) ✅ تسجيل الدخول نجح (via content)")
            return True, session

        print(f"[KSI] ({username}) ❌ فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[KSI] ({username}) ❌ خطأ: {e}")
        return False, None

def login_rsayel(account):
    username = account.get("username", "")
    password = account.get("password", "")
    base_url = SETTINGS["rsayel"]["base_url"]
    login_page_url = SETTINGS["rsayel"]["login_page_url"]
    login_post_url = SETTINGS["rsayel"]["login_post_url"]
    timeout = SETTINGS["rsayel"]["timeout"]
    session = requests.Session()
    session.verify = False
    print(f"[rsayel] ({username}) 🔄 تسجيل الدخول...")
    try:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        })
        response = session.get(login_page_url, timeout=timeout)
        if response.status_code == 403:
            response = session.get(login_page_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            print(f"[rsayel] ({username}) [!] فشل فتح صفحة الدخول: {response.status_code}")
            return False, None
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value'))
        if not csrf_token:
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = str(csrf_input.get('value'))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content'))
        if not csrf_token:
            match = re.search(r"""name=["']_token["'].*?value=["']([^"']+)["']""", html_content)
            if match:
                csrf_token = match.group(1)
        captcha_answer = None
        patterns = [r'(\d+)\s*\+\s*(\d+)\s*=', r'What is (\d+) \+ (\d+)', r'(\d+)\s*plus\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break
        if not captcha_answer:
            b_tags = soup.find_all('b')
            nums = []
            for b in b_tags:
                text = b.get_text().strip()
                if text.isdigit():
                    nums.append(int(text))
            if len(nums) >= 2:
                captcha_answer = str(nums[0] + nums[1])
        if not captcha_answer:
            text = soup.get_text()
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                    break
        if not captcha_answer:
            print(f"[rsayel] ({username}) [!] لم يتم العثور على الكابتشا")
            return False, None
        print(f"[rsayel] ({username}) [*] Captcha: {captcha_answer}")
        login_data = {"username": username, "password": password, "capt": captcha_answer}
        if csrf_token:
            login_data["_token"] = csrf_token
        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and isinstance(name, str) and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''
        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = session.post(login_post_url, data=login_data, headers=login_headers, timeout=timeout, allow_redirects=True)
        print(f"[rsayel] ({username}) [DEBUG] Final URL: {response.url}")
        if any(x in response.url.lower() for x in ["/agent", "/dashboard", "/home"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[rsayel] ({username}) [+] تسجيل الدخول نجح")
            return True, session
        content_lower = response.text.lower()
        if "logout" in content_lower or "smscdr" in content_lower or "agent" in content_lower:
            print(f"[rsayel] ({username}) [+] تسجيل الدخول نجح (Detected via content)")
            return True, session
        print(f"[rsayel] ({username}) [!] فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[rsayel] ({username}) [!] خطأ: {e}")
        return False, None

def login_grand(account):
    """Login function for the 'grand' panel (API key mode, or username/password fallback)"""
    api_key = account.get("api_key", "").strip()
    if api_key:
        print(f"[grand] ({account.get('username', 'API')}) ✅ وضع API Key - لا يحتاج تسجيل دخول")
        return True, None

    username = account.get("username", "")
    password = account.get("password", "")
    base_url = "https://panel.grand-panel.com"
    login_page_url = SETTINGS["grand"]["login_page_url"]
    login_post_url = SETTINGS["grand"]["login_post_url"]
    timeout = SETTINGS["grand"]["timeout"]
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    })
    print(f"[grand] ({username}) 🔄 تسجيل الدخول بـ Username/Password...")
    try:
        response = session.get(login_page_url, timeout=timeout)
        if response.status_code != 200:
            print(f"[grand] ({username}) [!] فشل فتح صفحة الدخول: {response.status_code}")
            return False, None
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value'))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content'))
        if not csrf_token:
            match = re.search(r"""name=["']_token["'].*?value=["']([^"']+)["']""", html_content)
            if match:
                csrf_token = match.group(1)
        login_data = {"email": username, "password": password}
        if csrf_token:
            login_data["_token"] = csrf_token
        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = session.post(login_post_url, data=login_data, headers=login_headers, timeout=timeout, allow_redirects=True)
        if any(x in response.url.lower() for x in ["/dashboard", "/home", "/cdrs", "/agent"]) or \
           (response.status_code == 200 and "login" not in response.url.lower()):
            print(f"[grand] ({username}) ✅ تسجيل الدخول نجح")
            return True, session
        content_lower = response.text.lower()
        if "logout" in content_lower or "dashboard" in content_lower or "cdrs" in content_lower:
            print(f"[grand] ({username}) ✅ تسجيل الدخول نجح (via content)")
            return True, session
        print(f"[grand] ({username}) ❌ فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[grand] ({username}) ❌ خطأ: {e}")
        return False, None

def test_bolt_type_login(site_key, account):
    username = account.get("username")
    password = account.get("password")
    
   
    if site_key == "MSI":
        session_obj = session6
        base_url = BASE_URL6
        login_page = LOGIN_PAGE_URL6
        login_post = LOGIN_POST_URL6
        timeout = HTTP_TIMEOUT6
    elif site_key == "proton SMS":
        session_obj = session7
        base_url = BASE_URL7
        login_page = LOGIN_PAGE_URL7
        login_post = LOGIN_POST_URL7
        timeout = HTTP_TIMEOUT7
    elif site_key in ["IMS", "IMS_New"]:
        if site_key == "IMS":
            session_obj = session8
            base_url = BASE_URL8
            login_page = LOGIN_PAGE_URL8
            login_post = LOGIN_POST_URL8
            timeout = HTTP_TIMEOUT8
        else:  # IMS_New
            session_obj = session_ims_new
            base_url = BASE_URL_IMS_NEW
            login_page = LOGIN_PAGE_URL_IMS_NEW
            login_post = LOGIN_POST_URL_IMS_NEW
            timeout = HTTP_TIMEOUT_IMS_NEW
    elif site_key == "Fire_SMS":
        session_obj = session_fire
        base_url = FIRE_BASE_URL
        login_page = FIRE_LOGIN_PAGE_URL
        login_post = FIRE_LOGIN_POST_URL
        timeout = HTTP_TIMEOUT9
    elif site_key in ["Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex", "EMO SMS"]:
        result = login_generic_ints(site_key, account)
        return result
    elif site_key == "green":
        result, _ = login_green(account)
        return result
    elif site_key == "ksi":
        result, _ = login_ksi(account)
        return result
    elif site_key == "rsayel":
        result, _ = login_rsayel(account)
        return result
    elif site_key == "Roxy SMS":
        try:
            scraper = cloudscraper.create_scraper()
            login_url = "http://www.roxysms.net/signin"
            payload = {"username": username, "password": password}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://www.roxysms.net/Login"
            }
            resp = scraper.post(login_url, data=payload, headers=headers, timeout=20)
            if resp.status_code == 200 and ("success" in resp.text.lower() or "logout" in resp.text.lower()):
                print(f"[{site_key}] ({username}) ✅ تسجيل الدخول نجح")
                return True
            else:
                print(f"[{site_key}] ({username}) ❌ فشل تسجيل الدخول")
                return False
        except Exception as e:
            print(f"[{site_key}] ({username}) ❌ خطأ في تسجيل الدخول: {e}")
            return False
    else:
        return False

    print(f"[{site_key}] ({username}) 🔐 محاولة تسجيل الدخول (Bolt-type)...")
    
    try:
        session_obj.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
        })
        
        resp = session_obj.get(login_page, timeout=timeout)
        
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            print(f"[{site_key}] ({username}) ⚠️ لم يتم العثور على captcha")
            return False
        
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2
        
        crlf_match = re.search(r"name=['\"]crlf['\"].*?value=['\"]([^'\"]+)['\"]", resp.text)
        
        payload = {
            "username": username,
            "password": password,
            "capt": str(captcha_answer)
        }
        
        if crlf_match:
            payload["crlf"] = crlf_match.group(1)
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": login_page,
            "Origin": base_url
        }
        
        resp = session_obj.post(login_post, data=payload, headers=headers, timeout=timeout, allow_redirects=True)
        
        if ("dashboard" in resp.text.lower() or 
            "logout" in resp.text.lower() or 
            "agent" in resp.url.lower() or 
            "reports" in resp.url.lower()):
            print(f"[{site_key}] ({username}) ✅ تسجيل الدخول نجح")
            return True
        else:
            print(f"[{site_key}] ({username}) ❌ فشل تسجيل الدخول")
            return False
            
    except Exception as e:
        print(f"[{site_key}] ({username}) ❌ خطأ في تسجيل الدخول: {e}")
        return False

def extract_sms(html_text, debug_mode=False):
    soup = BeautifulSoup(html_text, "html.parser")
    messages = []
    
    table = soup.find("table", class_="table")
    if not table:
        all_tables = soup.find_all("table")
        if all_tables:
            table = all_tables[0]
        else:
            return []
        
    tbody = table.find("tbody")
    if not tbody:
        rows = table.find_all("tr")
    else:
        rows = tbody.find_all("tr")
    
    row_count = 0
    for row in rows:
        tds = row.find_all("td")
        if not tds:
            continue
        
        row_count += 1
        cols = [td.get_text(separator=" ", strip=True) for td in tds]
        
        if debug_mode and row_count <= 3:
            print(f"  صف {row_count}: {len(cols)} عمود - {cols[:8] if len(cols) > 7 else cols}")
        
        if not cols or len(cols) < 5:
            continue
        
        msg = {
            "date": cols[0] if len(cols) > 0 else "",
            "ref": cols[1] if len(cols) > 1 else "",
            "source": cols[2] if len(cols) > 2 else "",
            "client": cols[3] if len(cols) > 3 else "",
            "destination": cols[4] if len(cols) > 4 else "",
            "raw": cols[5] if len(cols) > 5 else (cols[4] if len(cols) > 4 else "")
        }
        
        if msg["date"] and msg["raw"] and len(msg["raw"]) > 3:
            messages.append(msg)
    
    return messages

def test_site_login(chat_id, site_key, account_id=None):
    global is_logged_in_site2, is_logged_in_site3, is_logged_in_site4, is_logged_in_site5, USERNAME, PASSWORD, USERNAME2, PASSWORD2, USERNAME3, PASSWORD3, USERNAME4, PASSWORD4, USERNAME5, PASSWORD5
    
    site_name = SETTINGS[site_key]["name"]
    account = get_account_by_id(site_key, account_id) if account_id else get_site_accounts(site_key)[0]
    
    if not account:
        bot.send_message(chat_id, "❌ الحساب غير موجود!", parse_mode="HTML")
        return
    
    try:
        if site_key == "IMS":
            success, _ = login_site8(account)
            if success:
                bot.send_message(
                    chat_id,
                    f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"🔓 تم تسجيل الدخول بنجاح\n"
                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ تأكد من صحة البيانات (Username, Password, Captcha)",
                    parse_mode="HTML"
                )
            return

        if site_key == "IMS_New":
            success, _ = login_ims_new(account)
            if success:
                bot.send_message(
                    chat_id,
                    f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"🔓 تم تسجيل الدخول بنجاح\n"
                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ تأكد من صحة البيانات (Username, Password, Captcha)",
                    parse_mode="HTML"
                )
            return

        if site_key == "GROUP":
            old_username, old_password = USERNAME, PASSWORD
            try:
                USERNAME = account.get("username")
                PASSWORD = account.get("password")
                
                result = login()
                
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME, PASSWORD = old_username, old_password
        
        elif site_key == "Roxy SMS":
            try:
                scraper = cloudscraper.create_scraper()
                login_url = "http://www.roxysms.net/signin"
                payload = {"username": account["username"], "password": account["password"]}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://www.roxysms.net/Login"
                }
                resp = scraper.post(login_url, data=payload, headers=headers, timeout=20)
                if resp.status_code == 200 and ("success" in resp.text.lower() or "logout" in resp.text.lower()):
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطأ في تسجيل الدخول: {e}")
            return
        
        elif site_key == "Fly sms":
            old_username, old_password = USERNAME2, PASSWORD2
            try:
                USERNAME2 = account.get("username")
                PASSWORD2 = account.get("password")
                
                is_logged_in_site2 = False
                result = login_site2()
                
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME2, PASSWORD2 = old_username, old_password
        
        elif site_key == "Number_Panel":
            old_username, old_password = USERNAME3, PASSWORD3
            try:
                USERNAME3 = account.get("username")
                PASSWORD3 = account.get("password")
                
                is_logged_in_site3 = False
                result = login_site3()
                
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME3, PASSWORD3 = old_username, old_password
        
        elif site_key == "Bolt":
            old_username, old_password = USERNAME4, PASSWORD4
            try:
                USERNAME4 = account.get("username")
                PASSWORD4 = account.get("password")
                
                is_logged_in_site4 = False
                result = login_site4()
                
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME4, PASSWORD4 = old_username, old_password
        
        elif site_key == "iVASMS":
            old_username, old_password = USERNAME5, PASSWORD5
            try:
                USERNAME5 = account.get("username")
                PASSWORD5 = account.get("password")
                
                is_logged_in_site5 = False
                result = login_site5()
                
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"🔓 تم تسجيل الدخول بنجاح\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ تحقق من اليوزر والباسورد",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME5, PASSWORD5 = old_username, old_password
        
        elif site_key in ["MSI", "proton SMS", "IMS", "IMS_New", "Fire_SMS", "Roxy SMS", "Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex", "rsayel", "ksi", "green", "EMO SMS"]:
            result = test_bolt_type_login(site_key, account)
            if result:
                SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                save_sessions(SESSIONS)
                bot.send_message(
                    chat_id,
                    f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"🔓 تم تسجيل الدخول بنجاح\n"
                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ تحقق من اليوزر والباسورد",
                    parse_mode="HTML"
                )
        elif site_key == "grand":
            api_key = account.get("api_key", "").strip()
            if api_key:
                SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                save_sessions(SESSIONS)
                bot.send_message(
                    chat_id,
                    f"✅ <b>نجح التحقق - {site_name}</b>\n\n"
                    f"🔑 وضع API Key\n"
                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
            else:
                result, _ = login_grand(account)
                if result:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"⚠️ تحقق من اليوزر والباسورد أو API Key",
                        parse_mode="HTML"
                    )
        elif site_key == "MBC":
            result, _ = login_mbc(account)
            if result:
                SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                save_sessions(SESSIONS)
                bot.send_message(
                    chat_id,
                    f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"🔓 تم تسجيل الدخول بنجاح\n"
                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ تحقق من اليوزر والباسورد",
                    parse_mode="HTML"
                )
        elif site_key == "Flash_SMS":
            api_token = account.get("api_token")
            if not api_token:
                bot.send_message(chat_id, f"❌ <b>فشل التحقق - {site_name}</b>\n\n⚠️ مفتاح API غير موجود!", parse_mode="HTML")
                return
            try:
                api_url = SETTINGS[site_key].get("api_url", "https://www.flashsms.space/api/cdr/viewstats")
                headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
                r = requests.get(api_url, headers=headers, params={"records": 1}, timeout=30)
                if r.status_code == 200:
                    SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                    save_sessions(SESSIONS)
                    bot.send_message(
                        chat_id,
                        f"✅ <b>نجح التحقق - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                        f"🔓 Bearer Token صالح ومتصل\n"
                        f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode="HTML"
                    )
                else:
                    r2 = requests.get(api_url, params={"token": api_token, "records": 1}, timeout=30)
                    if r2.status_code == 200:
                        SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
                        save_sessions(SESSIONS)
                        bot.send_message(
                            chat_id,
                            f"✅ <b>نجح التحقق - {site_name}</b> (Query Param)\n\n"
                            f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                            f"🔓 Token صالح\n"
                            f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            parse_mode="HTML"
                        )
                    else:
                        bot.send_message(
                            chat_id,
                            f"❌ <b>فشل التحقق - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                            f"⚠️ HTTP {r.status_code} (Bearer) / {r2.status_code} (Query)\n"
                            f"📝 Response: <code>{html.escape(r.text[:200])}</code>",
                            parse_mode="HTML"
                        )
            except Exception as e:
                bot.send_message(
                    chat_id,
                    f"❌ <b>خطأ في التحقق - {site_name}</b>\n\n"
                    f"⚠️ {str(e)}",
                    parse_mode="HTML"
                )
        elif site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS", "Horus", "Pac_Call", "PRIM-FLASH"]:
            api_token = account.get("api_token")
            if not api_token:
                bot.send_message(chat_id, f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n⚠️ مفتاح API غير موجود!", parse_mode="HTML")
                return
            SESSIONS[site_key] = {"logged_in": True, "time": datetime.now().isoformat()}
            save_sessions(SESSIONS)
            bot.send_message(
                chat_id,
                f"✅ <b>نجح التحقق - {site_name}</b>\n\n"
                f"👤 الحساب: <code>{account.get('api_token')[:15]}...</code>\n"
                f"🔓 مفتاح API صالح\n"
                f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="HTML"
            )
    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ <b>خطأ أثناء اختبار تسجيل الدخول - {site_name}</b>\n\n"
            f"⚠️ الخطأ: {str(e)}",
            parse_mode="HTML"
        )

def test_site_fetch(chat_id, site_key, account_id=None):
    global is_logged_in_site2, is_logged_in_site3, is_logged_in_site4, is_logged_in_site5, USERNAME, PASSWORD, USERNAME2, PASSWORD2, USERNAME3, PASSWORD3, USERNAME4, PASSWORD4, USERNAME5, PASSWORD5
    site_name = SETTINGS[site_key]["name"]
    account = get_account_by_id(site_key, account_id) if account_id else get_site_accounts(site_key)[0]
    
    if not account:
        bot.send_message(chat_id, "❌ الحساب غير موجود!", parse_mode="HTML")
        return
    
    try:
        if site_key == "GROUP":
            old_username, old_password = USERNAME, PASSWORD
            try:
                USERNAME = account.get("username")
                PASSWORD = account.get("password")
                
                if not check_login_valid():
                    print(f"[GROUP] الجلسة غير صالحة لـ {account.get('username')}، محاولة تسجيل الدخول...")
                    if not login():
                        bot.send_message(
                            chat_id,
                            f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"⚠️ يجب تسجيل الدخول أولاً قبل اختبار جلب الكود",
                            parse_mode="HTML"
                        )
                        return
                    time.sleep(2)
            
                sms_url = BASE_URL + AJAX_PATH
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": BASE_URL + "/ints/agent/SMSCDRReports"
                }
                
                r = session1.get(sms_url, headers=headers, timeout=HTTP_TIMEOUT)
                
                if r.status_code == 200:
                    messages = extract_sms(r.text)
                    if messages:
                        last_msg = messages[0]
                        otp, decoded_text = extract_from_message(last_msg.get('raw', ''))
                        
                        bot.send_message(
                            chat_id,
                            f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"📱 الرقم: <code>{last_msg.get('source', 'N/A')}</code>\n"
                            f"📝 الرسالة: {decoded_text[:100] if decoded_text else 'N/A'}...\n"
                            f"⏰ الوقت: {last_msg.get('date', 'N/A')}",
                            parse_mode="HTML"
                        )
                    else:
                        bot.send_message(
                            chat_id,
                            f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"HTTP Status: {r.status_code}",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME, PASSWORD = old_username, old_password
        
        elif site_key == "Fly sms":
            old_username, old_password = USERNAME2, PASSWORD2
            try:
                USERNAME2 = account.get("username")
                PASSWORD2 = account.get("password")
                
                if not is_logged_in_site2:
                    print(f"[Fly sms] غير مسجل دخول لـ {account.get('username')}، محاولة تسجيل الدخول...")
                    if not login_site2():
                        bot.send_message(
                            chat_id,
                            f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"⚠️ يجب تسجيل الدخول أولاً قبل اختبار جلب الكود",
                            parse_mode="HTML"
                        )
                        return
                    time.sleep(2)
                
                url = build_ajax_url_site2()
                
                data = None
                max_retries = 5
                for attempt in range(1, max_retries + 1):
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": BASE_URL2 + "/ints/agent/SMSCDRReports"
                        }
                        r = session2.get(url, timeout=HTTP_TIMEOUT2, headers=headers)
                        
                        if r.status_code in [502, 503, 504]:
                            print(f"[Fly sms] ⚠️ السيرفر مشغول ({r.status_code}) - محاولة {attempt}/{max_retries}")
                            if attempt < max_retries:
                                time.sleep(15 * attempt)
                                continue
                            else:
                                bot.send_message(
                                    chat_id,
                                    f"⚠️ <b>السيرفر مشغول - {site_name}</b>\n\n"
                                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                                    f"⏳ الخطأ: {r.status_code} - السيرفر تحت ضغط\n"
                                    f"💡 حاول مرة أخرى بعد دقيقة",
                                    parse_mode="HTML"
                                )
                                return
                        
                        if r.status_code == 200:
                            data = r.json()
                            break
                        else:
                            if attempt < max_retries:
                                time.sleep(10)
                                continue
                    except Exception as e:
                        print(f"[Fly sms] ⚠️ خطأ في المحاولة {attempt}: {e}")
                        if attempt < max_retries:
                            time.sleep(10)
                            continue
                
                if data:
                    messages = data.get("data", [])
                    if messages:
                        last_msg = messages[0]
                        sms_text = last_msg[5] if len(last_msg) > 5 else "N/A"
                        number = last_msg[2] if len(last_msg) > 2 else "N/A"
                        date_str = last_msg[0] if len(last_msg) > 0 else "N/A"
                        
                        otp, decoded_text = extract_from_message(sms_text)
                        
                        bot.send_message(
                            chat_id,
                            f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"📱 الرقم: <code>{number}</code>\n"
                            f"📝 الرسالة: {decoded_text[:100] if decoded_text else sms_text[:100]}...\n"
                            f"⏰ الوقت: {date_str}",
                            parse_mode="HTML"
                        )
                    else:
                        bot.send_message(
                            chat_id,
                            f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ فشل الاتصال بالسيرفر",
                        parse_mode="HTML"
                    )
            except Exception as e:
                bot.send_message(
                    chat_id,
                    f"❌ <b>خطأ في معالجة البيانات - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ التفاصيل: {str(e)}",
                    parse_mode="HTML"
                )
            finally:
                USERNAME2, PASSWORD2 = old_username, old_password
        
        elif site_key == "Number_Panel":
            old_username, old_password = USERNAME3, PASSWORD3
            try:
                USERNAME3 = account.get("username")
                PASSWORD3 = account.get("password")
                api_token = account.get("api_token") or SETTINGS[site_key].get("api_token")
                
                if api_token:
                    api_url = "http://147.135.212.197/crapi/st/viewstats"
                    r = session3.get(api_url, params={"token": api_token, "records": 10}, timeout=HTTP_TIMEOUT3)
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            if isinstance(data, list) and data:
                                last_msg = data[0]
                                sms_text = last_msg[2]
                                number = last_msg[1]
                                date_str = last_msg[3]
                                
                                otp, decoded_text = extract_from_message(sms_text)
                                
                                bot.send_message(
                                    chat_id,
                                    f"✅ <b>نجح جلب الكود - {site_name} (API)</b>\n\n"
                                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                                    f"📱 الرقم: <code>{number}</code>\n"
                                    f"📝 الرسالة: {decoded_text[:100] if decoded_text else sms_text[:100]}...\n"
                                    
                                    f"⏰ الوقت: {date_str}",
                                    parse_mode="HTML"
                                )
                                return
                        except Exception as e:
                            print(f"API parse error: {e}")

                if not is_logged_in_site3:
                    print(f"[Number_Panel] غير مسجل دخول لـ {account.get('username')}، محاولة تسجيل الدخول...")
                    if not login_site3():
                        bot.send_message(
                            chat_id,
                            f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"⚠️ يجب تسجيل الدخول أولاً قبل اختبار جلب الكود",
                            parse_mode="HTML"
                        )
                        return
                    time.sleep(2)
                
                url = BASE_URL3 + AJAX_PATH3
                params = {
                    "draw": 1,
                    "start": 0,
                    "length": 10
                }
                
                r = session3.get(url, params=params, timeout=HTTP_TIMEOUT3)
                
                if r.status_code == 200:
                    try:
                        data = r.json()
                        messages = data.get("data", []) or data.get("aaData", [])
                        if messages:
                            last_msg = messages[0]
                            sms_text = last_msg[IDX_SMS_SITE3] if len(last_msg) > IDX_SMS_SITE3 else "N/A"
                            number = last_msg[IDX_NUMBER_SITE3] if len(last_msg) > IDX_NUMBER_SITE3 else "N/A"
                            date_str = last_msg[IDX_DATE_SITE3] if len(last_msg) > IDX_DATE_SITE3 else "N/A"
                            
                            otp, decoded_text = extract_from_message(sms_text)
                            
                            bot.send_message(
                                chat_id,
                                f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{account.get('username')}</code>\n"
                                f"📱 الرقم: <code>{number}</code>\n"
                                f"📝 الرسالة: {decoded_text[:100] if decoded_text else sms_text[:100]}...\n"
                                f"⏰ الوقت: {date_str}",
                                parse_mode="HTML"
                            )
                        else:
                            bot.send_message(
                                chat_id,
                                f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{account.get('username')}</code>",
                                parse_mode="HTML"
                            )
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"❌ <b>خطأ في معالجة البيانات - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"⚠️ التفاصيل: {str(e)}",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"HTTP Status: {r.status_code}",
                        parse_mode="HTML"
                    )
            finally:
                USERNAME3, PASSWORD3 = old_username, old_password
        
        elif site_key == "Bolt":
            sess = requests.Session()
            sess.verify = False
            sess.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            base_url = SETTINGS[site_key].get("base_url", "")
            login_page = SETTINGS[site_key].get("login_page_url", "")
            login_post = SETTINGS[site_key].get("login_post_url", "")
            ajax_path = SETTINGS[site_key].get("ajax_path", "")
            timeout = SETTINGS[site_key].get("timeout", 30)
            username_b = account.get("username")
            password_b = account.get("password")
            try:
                resp = sess.get(login_page, timeout=timeout)
                match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
                captcha = str(int(match.group(1)) + int(match.group(2))) if match else ""
                crlf = re.search(r"name=['\"]crlf['\"].*?value=['\"]([^'\"]+)['\"]", resp.text)
                payload = {'username': username_b, 'password': password_b}
                if captcha: payload['capt'] = captcha
                if crlf: payload['crlf'] = crlf.group(1)
                headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': login_page, 'Origin': base_url}
                r = sess.post(login_post, data=payload, headers=headers, timeout=timeout, allow_redirects=True)
                success = any(k in r.text.lower() for k in ["dashboard", "logout", "agent", "smscdr"]) or any(k in r.url.lower() for k in ["agent", "reports"])
                if not success:
                    bot.send_message(chat_id, f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n👤 الحساب: <code>{username_b}</code>\n⚠️ تحقق من اليوزر والباسورد", parse_mode="HTML")
                    return
                sms_page = base_url + "/ints/agent/SMSCDRReports"
                page_resp = sess.get(sms_page, timeout=timeout)
                sesskey = None
                sk = re.search(r'sesskey=([A-Za-z0-9=]+)', page_resp.text)
                if sk: sesskey = sk.group(1)
                today = datetime.now().strftime('%Y-%m-%d')
                ajax_url = base_url + ajax_path
                if sesskey:
                    ajax_payload = {'fdate1': f'{today} 00:00:00', 'fdate2': f'{today} 23:59:59', 'frange': '', 'fclient': '', 'fnum': '', 'fcli': '', 'fgdate': '', 'fgmonth': '', 'fgrange': '', 'fgclient': '', 'fgnumber': '', 'fgcli': '', 'fg': '0', 'sesskey': sesskey}
                    ajax_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest', 'Referer': sms_page}
                    r2 = sess.get(ajax_url, params=ajax_payload, headers=ajax_headers, timeout=timeout)
                else:
                    r2 = sess.get(ajax_url, params={'draw': 1, 'start': 0, 'length': 10}, timeout=timeout)
                if r2.status_code == 200:
                    try:
                        data = r2.json()
                        rows = data.get('aaData', data.get('data', []))
                        if rows:
                            last_msg = rows[0]
                            sms_text = last_msg[5] if len(last_msg) > 5 else str(last_msg)
                            number = last_msg[2] if len(last_msg) > 2 else "N/A"
                            date_str = last_msg[0] if len(last_msg) > 0 else "N/A"
                            otp, decoded_text = extract_from_message(sms_text)
                            bot.send_message(chat_id, f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n👤 الحساب: <code>{username_b}</code>\n📱 الرقم: <code>{number}</code>\n📝 الرسالة: {(decoded_text or sms_text)[:100]}...\n⏰ الوقت: {date_str}", parse_mode="HTML")
                        else:
                            bot.send_message(chat_id, f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n👤 الحساب: <code>{username_b}</code>", parse_mode="HTML")
                    except Exception as e:
                        bot.send_message(chat_id, f"❌ <b>خطأ في معالجة البيانات - {site_name}</b>\n\n⚠️ {str(e)}", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\nHTTP Status: {r2.status_code}", parse_mode="HTML")
            except Exception as e:
                bot.send_message(chat_id, f"❌ <b>خطأ - {site_name}</b>\n\n⚠️ {str(e)}", parse_mode="HTML")
        
        elif site_key == "iVASMS":
            old_username, old_password = USERNAME5, PASSWORD5
            try:
                USERNAME5 = account.get("username")
                PASSWORD5 = account.get("password")
                
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                test_session = requests.Session()
                test_session.verify = False
                test_session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive"
                })
                
                resp = test_session.get(LOGIN_PAGE_URL5, timeout=HTTP_TIMEOUT5)
                soup = BeautifulSoup(resp.text, 'html.parser')
                csrf_input = soup.find('input', {'name': '_token'})
                if not csrf_input:
                    bot.send_message(chat_id, f"❌ <b>فشل الاتصال - {site_name}</b>\n\n⚠️ لم يتم العثور على CSRF token", parse_mode="HTML")
                    return
                
                csrf = csrf_input.get('value')
                payload = {'_token': csrf, 'email': USERNAME5, 'password': PASSWORD5}
                headers = {"Content-Type": "application/x-www-form-urlencoded", "Referer": LOGIN_PAGE_URL5}
                
                resp = test_session.post(LOGIN_POST_URL5, data=payload, headers=headers, timeout=HTTP_TIMEOUT5, allow_redirects=True)
                
                if 'portal' not in resp.url and 'login' in resp.url:
                    bot.send_message(chat_id, f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n👤 الحساب: <code>{account.get('username')}</code>", parse_mode="HTML")
                    return
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                csrf_input = soup.find('input', {'name': '_token'})
                if csrf_input:
                    csrf = csrf_input.get('value')
                
                today = date.today()
                from_date = (today - timedelta(days=7)).strftime("%d/%m/%Y")
                to_date = today.strftime("%d/%m/%Y")
                
                payload = {'from': from_date, 'to': to_date, '_token': csrf}
                headers = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Referer': SMS_RECEIVED_URL5}
                
                resp = test_session.post(GET_SMS_URL5, data=payload, headers=headers, timeout=HTTP_TIMEOUT5)
                
                if resp.status_code != 200:
                    bot.send_message(chat_id, f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\nHTTP Status: {resp.status_code}", parse_mode="HTML")
                    return
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select("div.item div.card.card-body")
                ranges = []
                for item in items:
                    onclick = item.get('onclick', '')
                    match = re.search(r"getDetials\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", str(onclick) if onclick else "")
                    if match:
                        ranges.append(match.group(1))
                
                if not ranges:
                    bot.send_message(chat_id, f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n👤 الحساب: <code>{account.get('username')}</code>", parse_mode="HTML")
                    return
                
                first_range = ranges[0]
                start_datetime = f"{today.strftime('%Y-%m-%d')} 00:00:00"
                end_datetime = f"{today.strftime('%Y-%m-%d')} 23:59:59"
                
                payload = {'_token': csrf, 'start': start_datetime, 'end': end_datetime, 'range': first_range}
                resp = test_session.post(GET_SMS_NUMBER_URL5, data=payload, headers=headers, timeout=HTTP_TIMEOUT5)
                
                numbers = []
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for item in soup.select("[onclick]"):
                        onclick = item.get('onclick', '')
                        phone_match = re.search(r"getNumber[^\(]*\(['\"]([^'\"]+)['\"]", str(onclick) if onclick else "")
                        if phone_match:
                            phone = phone_match.group(1)
                            if phone and len(phone) > 5:
                                numbers.append(phone)
                    if not numbers:
                        all_numbers = re.findall(r'["\']?(\d{10,15})["\']?', resp.text)
                        numbers.extend(all_numbers[:10])
                
                if not numbers:
                    bot.send_message(chat_id, f"⚠️ <b>لا توجد أرقام - {site_name}</b>\n\n👤 الحساب: <code>{account.get('username')}</code>\nRange: {first_range}", parse_mode="HTML")
                    return
                
                first_phone = numbers[0]
                payload = {'_token': csrf, 'start': start_datetime, 'end': end_datetime, 'Number': first_phone, 'Range': first_range}
                resp = test_session.post(GET_SMS_MESSAGE_URL5, data=payload, headers=headers, timeout=HTTP_TIMEOUT5)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    message = None
                    for selector in [".col-9.col-sm-6 p", ".col-sm-6 p"]:
                        el = soup.select_one(selector)
                        if el:
                            message = el.text.strip()
                            break
                    if not message:
                        for p in soup.find_all('p'):
                            text = p.text.strip()
                            if len(text) > 15:
                                message = text
                                break
                    
                    if message:
                        otp, decoded_text = extract_from_message(message)
                        bot.send_message(
                            chat_id,
                            f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"📱 الرقم: <code>{first_phone}</code>\n"
                            f"📝 الرسالة: {(decoded_text[:100] if decoded_text else message[:100])}...\n"
                            
                            f"📊 Ranges: {len(ranges)} | Numbers: {len(numbers)}",
                            parse_mode="HTML"
                        )
                    else:
                        bot.send_message(chat_id, f"⚠️ <b>لا توجد رسالة - {site_name}</b>\n\n📱 الرقم: {first_phone}", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, f"❌ <b>خطأ في جلب الرسالة - {site_name}</b>\n\nHTTP Status: {resp.status_code}", parse_mode="HTML")
                    
            except Exception as e:
                bot.send_message(chat_id, f"❌ <b>خطأ - {site_name}</b>\n\n⚠️ {str(e)}", parse_mode="HTML")
            finally:
                USERNAME5, PASSWORD5 = old_username, old_password
        
        elif site_key in ["MSI", "proton SMS", "IMS", "IMS_New", "Fire_SMS", "Roxy SMS", "Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex", "rsayel", "ksi", "green", "EMO SMS"]:
            session_obj = None
            base_url = None
            ajax_path = None
            timeout = None
            if site_key == "MSI":
                session_obj = session6
                base_url = BASE_URL6
                ajax_path = AJAX_PATH6
                timeout = HTTP_TIMEOUT6
            elif site_key == "proton SMS":
                session_obj = session7
                base_url = BASE_URL7
                ajax_path = AJAX_PATH7
                timeout = HTTP_TIMEOUT7
            elif site_key in ["IMS"]:
                session_obj = session8
                base_url = BASE_URL8
                ajax_path = AJAX_PATH8
                timeout = HTTP_TIMEOUT8
            elif site_key == "IMS_New":
                session_obj = session_ims_new
                base_url = BASE_URL_IMS_NEW
                ajax_path = AJAX_PATH_IMS_NEW
                timeout = HTTP_TIMEOUT_IMS_NEW
            elif site_key == "Fire_SMS":
                session_obj = session_fire
                base_url = FIRE_BASE_URL
                ajax_path = FIRE_AJAX_PATH
                timeout = HTTP_TIMEOUT9
            elif site_key in ["Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex", "rsayel", "ksi", "green"]:
                sess = login_generic_ints(site_key, account)
                if not sess:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ يجب تسجيل الدخول أولاً قبل اختبار جلب الكود",
                        parse_mode="HTML"
                    )
                    return
                session_obj = sess
                base_url = SETTINGS[site_key].get("base_url", "")
                ajax_path = SETTINGS[site_key].get("ajax_path", "")
                timeout = SETTINGS[site_key].get("timeout", 30)
            elif site_key == "Roxy SMS":
                session_obj = session9
                base_url = BASE_URL9
                ajax_path = AJAX_PATH9
                timeout = HTTP_TIMEOUT9
            
            if site_key not in ["Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex", "rsayel", "ksi", "green", "EMO SMS"]:
                result = test_bolt_type_login(site_key, account)
                if not result:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>فشل تسجيل الدخول - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"⚠️ يجب تسجيل الدخول أولاً قبل اختبار جلب الكود",
                        parse_mode="HTML"
                    )
                    return
            
            time.sleep(2)
            url = base_url + ajax_path
            params = {
                "draw": 1,
                "start": 0,
                "length": 10
            }
            
            try:
                for attempt in range(3):
                    try:
                        r = session_obj.get(url, params=params, timeout=timeout)
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                        if attempt == 2: raise
                        time.sleep(2)
                
                if r.status_code == 200:
                    try:
                        data = r.json()
                        messages = data.get("data", [])
                        if messages:
                            last_msg = messages[0]
                            sms_text = last_msg[5] if len(last_msg) > 5 else "N/A"
                            number = last_msg[2] if len(last_msg) > 2 else "N/A"
                            date_str = last_msg[0] if len(last_msg) > 0 else "N/A"
                            
                            otp, decoded_text = extract_from_message(sms_text)
                            
                            bot.send_message(
                                chat_id,
                                f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{account.get('username')}</code>\n"
                                f"📱 الرقم: <code>{number}</code>\n"
                                f"📝 الرسالة: {decoded_text[:100] if decoded_text else sms_text[:100]}...\n"
                                f"⏰ الوقت: {date_str}",
                                parse_mode="HTML"
                            )
                        else:
                            bot.send_message(
                                chat_id,
                                f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{account.get('username')}</code>",
                                parse_mode="HTML"
                            )
                    except Exception as e:
                        bot.send_message(
                            chat_id,
                            f"❌ <b>خطأ في معالجة البيانات - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{account.get('username')}</code>\n"
                            f"⚠️ التفاصيل: {str(e)}",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{account.get('username')}</code>\n"
                        f"HTTP Status: {r.status_code}",
                        parse_mode="HTML"
                    )
            except Exception as e:
                bot.send_message(
                    chat_id,
                    f"❌ <b>خطأ في الاتصال - {site_name}</b>\n\n"
                    f"👤 الحساب: <code>{account.get('username')}</code>\n"
                    f"⚠️ التفاصيل: {str(e)}",
                    parse_mode="HTML"
                )
        
        elif site_key == "grand":
            api_key = account.get("api_key", "").strip()
            try:
                if api_key:
                    today = datetime.now().strftime('%Y-%m-%d')
                    r = requests.get(
                        "https://api.grand-panel.com/api/v1/messages",
                        params={"date": today},
                        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                        timeout=30
                    )
                    if r.status_code == 200:
                        data = r.json()
                        messages = data.get("messages", [])
                        if messages:
                            last_msg = messages[0]
                            sms_text = last_msg.get("content", last_msg.get("message", "N/A"))
                            number = last_msg.get("number", last_msg.get("destination", "N/A"))
                            date_str = last_msg.get("date", "N/A")
                            otp, decoded_text = extract_from_message(sms_text)
                            bot.send_message(
                                chat_id,
                                f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                                f"📱 الرقم: <code>{number}</code>\n"
                                f"📝 الرسالة: {decoded_text[:100] if decoded_text else str(sms_text)[:100]}...\n"
                                f"⏰ الوقت: {date_str}",
                                parse_mode="HTML"
                            )
                        else:
                            bot.send_message(chat_id, f"⚠️ <b>لا توجد رسائل - {site_name}</b>", parse_mode="HTML")
                    else:
                        bot.send_message(chat_id, f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\nHTTP {r.status_code}", parse_mode="HTML")
                else:
                    result, sess = login_grand(account)
                    if not result:
                        bot.send_message(chat_id, f"❌ <b>فشل تسجيل الدخول - {site_name}</b>", parse_mode="HTML")
                        return
                    bot.send_message(chat_id, f"✅ <b>نجح تسجيل الدخول - {site_name}</b>\n\nℹ️ استخدم API Key لاختبار جلب الأكواد", parse_mode="HTML")
            except Exception as e:
                bot.send_message(chat_id, f"❌ <b>خطأ - {site_name}</b>\n{e}", parse_mode="HTML")
        elif site_key == "Flash_SMS":
            api_token = account.get("api_token")
            api_url = SETTINGS[site_key].get("api_url", "https://www.flashsms.space/api/cdr/viewstats")
            try:
                headers_bearer = {
                    "Authorization": f"Bearer {api_token}",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
                params = {"records": 10}
                r = requests.get(api_url, headers=headers_bearer, params=params, timeout=30)
                print(f"[Flash_SMS] Attempt 1 (Bearer Header) Status: {r.status_code}")
                if r.status_code in [401, 403, 400]:
                    print(f"[Flash_SMS] Bearer failed, trying query param...")
                    headers_plain = {
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                    params = {"token": api_token, "records": 10}
                    r = requests.get(api_url, headers=headers_plain, params=params, timeout=30)
                    print(f"[Flash_SMS] Attempt 2 (Query Param) Status: {r.status_code}")
                if r.status_code == 200:
                    try:
                        data = r.json()
                        print(f"[Flash_SMS] Response keys: {list(data.keys()) if isinstance(data, dict) else 'LIST'}")
                        messages = []
                        if isinstance(data, list):
                            messages = data
                        elif isinstance(data, dict):
                            if data.get("status") == "success" and data.get("data"):
                                messages = data["data"]
                            elif "records" in data:
                                messages = data["records"]
                            elif "messages" in data:
                                messages = data["messages"]
                            elif "result" in data:
                                messages = data["result"]
                            else:
                                for v in data.values():
                                    if isinstance(v, list) and len(v) > 0:
                                        messages = v
                                        break
                        if messages and len(messages) > 0:
                            last_msg = messages[0]
                            sms_text = (
                                last_msg.get("message") or 
                                last_msg.get("sms") or 
                                last_msg.get("text") or 
                                last_msg.get("body") or 
                                last_msg.get("content") or
                                (last_msg[5] if isinstance(last_msg, (list, tuple)) and len(last_msg) > 5 else "N/A")
                            )
                            number = (
                                last_msg.get("num") or 
                                last_msg.get("number") or 
                                last_msg.get("msisdn") or 
                                last_msg.get("cli") or 
                                last_msg.get("from") or 
                                last_msg.get("source") or
                                (last_msg[2] if isinstance(last_msg, (list, tuple)) and len(last_msg) > 2 else "N/A")
                            )
                            date_str = (
                                last_msg.get("dt") or 
                                last_msg.get("date") or 
                                last_msg.get("time") or 
                                last_msg.get("created_at") or
                                (last_msg[0] if isinstance(last_msg, (list, tuple)) and len(last_msg) > 0 else datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            )
                            otp, decoded_text = extract_from_message(str(sms_text))
                            bot.send_message(
                                chat_id,
                                f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                                f"📱 الرقم: <code>{number}</code>\n"
                                f"📝 الرسالة: {decoded_text[:100] if decoded_text else str(sms_text)[:100]}...\n"
                                f"⏰ الوقت: {date_str}",
                                parse_mode="HTML"
                            )
                        else:
                            bot.send_message(
                                chat_id,
                                f"⚠️ <b>لا توجد رسائل - {site_name}</b>\n\n"
                                f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                                f"📊 الـ Response وصل بس فاضي (0 records)",
                                parse_mode="HTML"
                            )
                    except Exception as e:
                        print(f"[Flash_SMS] JSON parse error: {e}")
                        print(f"[Flash_SMS] Raw response: {r.text[:500]}")
                        bot.send_message(
                            chat_id,
                            f"⚠️ <b>خطأ في قراءة البيانات - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                            f"⚠️ التفاصيل: {str(e)}\n"
                            f"📝 Raw Response (أول 500 حرف):\n<code>{html.escape(r.text[:500])}</code>",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\n\n"
                        f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                        f"HTTP Status: {r.status_code}\n"
                        f"📝 Response: <code>{html.escape(r.text[:300])}</code>",
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"[Flash_SMS] Exception: {e}")
                bot.send_message(
                    chat_id,
                    f"❌ <b>خطأ - {site_name}</b>\n\n"
                    f"⚠️ {str(e)}",
                    parse_mode="HTML"
                )
        elif site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS", "Horus", "Pac_Call", "PRIM-FLASH"]:
            api_token = account.get("api_token")
            api_url = SETTINGS[site_key].get("api_url", "")
            try:
                if site_key == "TimeSMS_API":
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    params = {'token': api_token, 'dt1': f'{today_str} 00:00:00', 'dt2': f'{today_str} 23:59:59', 'records': 10}
                else:
                    params = {'token': api_token, 'records': 10}
                r = requests.get(api_url, params=params, timeout=HTTP_TIMEOUT9)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('status') == 'success' and data.get('data'):
                        last_msg = data['data'][0]
                        sms_text = last_msg.get('message', 'N/A')
                        number = last_msg.get('num', 'N/A')
                        date_str = last_msg.get('dt', 'N/A')
                        otp, decoded_text = extract_from_message(sms_text)
                        bot.send_message(
                            chat_id,
                            f"✅ <b>نجح جلب الكود - {site_name}</b>\n\n"
                            f"👤 الحساب: <code>{api_token[:15]}...</code>\n"
                            f"📱 الرقم: <code>{number}</code>\n"
                            f"📝 الرسالة: {decoded_text[:100] if decoded_text else sms_text[:100]}...\n"
                            f"⏰ الوقت: {date_str}",
                            parse_mode="HTML"
                        )
                    else:
                        bot.send_message(chat_id, f"⚠️ <b>لا توجد رسائل - {site_name}</b>", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, f"❌ <b>خطأ في جلب البيانات - {site_name}</b>\nHTTP {r.status_code}", parse_mode="HTML")
            except Exception as e:
                bot.send_message(chat_id, f"❌ <b>خطأ - {site_name}</b>\n{e}", parse_mode="HTML")
    
    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ <b>خطأ أثناء اختبار جلب الكود - {site_name}</b>\n\n"
            f"⚠️ الخطأ: {str(e)}",
            parse_mode="HTML"
        )

def extract_sms(html_text, debug_mode=False):
    soup = BeautifulSoup(html_text, "html.parser")
    messages = []
    
    table = soup.find("table", class_="table")
    if not table:
        all_tables = soup.find_all("table")
        if all_tables:
            table = all_tables[0]
        else:
            return []
        
    tbody = table.find("tbody")
    if not tbody:
        rows = table.find_all("tr")
    else:
        rows = tbody.find_all("tr")
    
    row_count = 0
    for row in rows:
        tds = row.find_all("td")
        if not tds:
            continue
        
        row_count += 1
        cols = [td.get_text(separator=" ", strip=True) for td in tds]
        
        if debug_mode and row_count <= 3:
            print(f"  صف {row_count}: {len(cols)} عمود - {cols[:8] if len(cols) > 7 else cols}")
        
        if not cols or len(cols) < 5:
            continue
        
        msg = {
            "date": cols[0] if len(cols) > 0 else "",
            "ref": cols[1] if len(cols) > 1 else "",
            "source": cols[2] if len(cols) > 2 else "",
            "client": cols[3] if len(cols) > 3 else "",
            "destination": cols[4] if len(cols) > 4 else "",
            "raw": cols[5] if len(cols) > 5 else (cols[4] if len(cols) > 4 else "")
        }
        
        if msg["date"] and msg["raw"] and len(msg["raw"]) > 3:
            messages.append(msg)
    
    return messages

def normalize_otp_from_text(text):
    if not text: 
        return None
    
    candidates = []
    
    telegram_pattern = r'(?:telegram|تيليجرام|تلجرام)\s*(?:code|كود)?\s*[:\s]*(\d{4,6})'
    match = re.search(telegram_pattern, text, re.IGNORECASE)
    if match:
        digits = match.group(1)
        candidates.append({
            'otp': digits,
            'position': match.start(),
            'confidence': 100
        })
    
    instagram_pattern = r'(\d{3})\s+(\d{3})\s+is\s+your\s+Instagram\s+code'
    match = re.search(instagram_pattern, text, re.IGNORECASE)
    if match:
        digits = match.group(1) + match.group(2)
        candidates.append({
            'otp': f"{digits[:3]} {digits[3:]}",
            'position': match.start(),
            'confidence': 99
        })
    
    code_keyword_pattern = r'(?:code|كود|رمز|verification|تحقق)[:\s]*(\d{4,8})'
    for match in re.finditer(code_keyword_pattern, text, re.IGNORECASE):
        digits = match.group(1)
        if 4 <= len(digits) <= 8:
            candidates.append({
                'otp': digits,
                'position': match.start(),
                'confidence': 95
            })
    
    spaced_triple_pattern = r'(\d{3})\s+(\d{3})'
    for match in re.finditer(spaced_triple_pattern, text):
        digits = match.group(1) + match.group(2)
        if len(digits) == 6:
            candidates.append({
                'otp': f"{digits[:3]} {digits[3:]}",
                'position': match.start(),
                'confidence': 90
            })
    
    high_confidence_pattern = r'(\d)\s+(\d)\s+(\d)\s*-\s*(\d)\s+(\d)\s+(\d)'
    for match in re.finditer(high_confidence_pattern, text):
        digits = re.sub(r'\D', '', match.group(0))
        if len(digits) == 6:
            candidates.append({
                'otp': f"{digits[:3]} {digits[3:]}",
                'position': match.start(),
                'confidence': 85
            })
    
    spaced_digits_pattern = r'(\d)\s+(\d)\s+(\d)\s+(\d)\s+(\d)\s+(\d)'
    for match in re.finditer(spaced_digits_pattern, text):
        digits = re.sub(r'\D', '', match.group(0))
        if len(digits) == 6:
            candidates.append({
                'otp': f"{digits[:3]} {digits[3:]}",
                'position': match.start(),
                'confidence': 80
            })
    
    hyphen_pattern = r'(\d{3})\s*-\s*(\d{3})'
    for match in re.finditer(hyphen_pattern, text):
        digits = re.sub(r'\D', '', match.group(0))
        if len(digits) == 6:
            candidates.append({
                'otp': f"{digits[:3]}-{digits[3:]}",
                'position': match.start(),
                'confidence': 98
            })
    
    
    rtl_whatsapp_pattern = r'[\u200e\u200f\u202a-\u202e]?(\d{3})\s*-\s*(\d{3})'
    for match in re.finditer(rtl_whatsapp_pattern, text):
        digits = match.group(1) + match.group(2)
        if len(digits) == 6:
            candidates.append({
                'otp': f"{match.group(1)}-{match.group(2)}",
                'position': match.start(),
                'confidence': 110
            })

    six_digits_pattern = r'\b\d{6}\b'
    for match in re.finditer(six_digits_pattern, text):
        digits = match.group(0)
        candidates.append({
            'otp': f"{digits[:3]} {digits[3:]}",
            'position': match.start(),
            'confidence': 70
        })
    
    five_digits_pattern = r'\b\d{5}\b'
    for match in re.finditer(five_digits_pattern, text):
        digits = match.group(0)
        candidates.append({
            'otp': digits,
            'position': match.start(),
            'confidence': 65
        })
    
    four_digits_pattern = r'\b\d{4}\b'
    for match in re.finditer(four_digits_pattern, text):
        digits = match.group(0)
        candidates.append({
            'otp': digits,
            'position': match.start(),
            'confidence': 60
        })
    
    if candidates:
        candidates.sort(key=lambda x: (-x['confidence'], x['position']))
        return candidates[0]['otp']
    
    all_digits = re.findall(r'\d+', text)
    for digit_group in reversed(all_digits):
        if len(digit_group) >= 4:
            return digit_group
    
    return None

def extract_from_message(raw_text):
    if not raw_text: 
        return None, None
    
    decoded_text = try_decode(raw_text)
    text = html.unescape(decoded_text)
    otp = normalize_otp_from_text(text)
    
    return otp, text

def clean_number(num_str: str) -> str:
    if num_str is None:
        return ""
    if isinstance(num_str, (int, float)):
        return str(int(num_str))
    return re.sub(r'\D', '', str(num_str))

IDX_DATE_SITE2 = 0
IDX_NUMBER_SITE2 = 2
IDX_SMS_SITE2 = 5

def retry_request_site2(func, max_retries=5, retry_delay=10):
    attempt = 0
    last_error = None
    while attempt < max_retries:
        attempt += 1
        try:
            return func()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            backoff = min(60, retry_delay * attempt)
            print(f"⚠️ [Fly sms] محاولة {attempt}/{max_retries} فشلت: {type(e).__name__}")
            print(f"⏳ [Fly sms] انتظار {backoff} ثانية قبل إعادة المحاولة...")
            time.sleep(backoff)
        except requests.exceptions.HTTPError as e:
            last_error = e
            status_code = e.response.status_code if e.response else 0
            if status_code in [502, 503, 504]:
                backoff = min(60, 10 + (attempt * 5))
                print(f"⚠️ [Fly sms] خطأ {status_code} - محاولة {attempt}/{max_retries}")
                print(f"⏳ [Fly sms] السيرفر مشغول، انتظار {backoff} ثانية...")
                time.sleep(backoff)
            elif status_code == 404:
                backoff = min(60, 15 + (attempt * 5))
                print(f"⚠️ [Fly sms] خطأ 404 - محاولة {attempt}/{max_retries}")
                print(f"⏳ [Fly sms] انتظار {backoff} ثانية...")
                time.sleep(backoff)
            else:
                print(f"❌ [Fly sms] خطأ HTTP {status_code}: {e}")
                raise
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "502" in error_str or "504" in error_str or "Service" in error_str:
                last_error = e
                backoff = min(60, 10 + (attempt * 5))
                print(f"⚠️ [Fly sms] خطأ سيرفر - محاولة {attempt}/{max_retries}: {error_str[:100]}")
                print(f"⏳ [Fly sms] انتظار {backoff} ثانية...")
                time.sleep(backoff)
            elif "404" in error_str or "Not Found" in error_str:
                last_error = e
                backoff = min(60, 15 + (attempt * 5))
                print(f"⚠️ [Fly sms] خطأ 404 - محاولة {attempt}/{max_retries}")
                print(f"⏳ [Fly sms] انتظار {backoff} ثانية...")
                time.sleep(backoff)
            else:
                print(f"❌ [Fly sms] خطأ غير متوقع: {e}")
                raise
    
    print(f"❌ [Fly sms] استنفدت جميع المحاولات ({max_retries})")
    if last_error:
        raise last_error
    raise Exception("Max retries exceeded")

def try_decode_site2(raw):
    if raw is None:
        return ""
    
    if isinstance(raw, str):
        cleaned = raw.replace('\x00', '').strip()
        if cleaned:
            return cleaned
        return ""
    
    if isinstance(raw, bytes):
        b = raw
    else:
        text_str = str(raw)
        cleaned = text_str.replace('\x00', '').strip()
        if cleaned:
            return cleaned
        return ""
    
    for enc in ("utf-8", "cp1256", "windows-1256", "iso-8859-6", "utf-16-be", "utf-16-le", "latin-1"):
        try:
            s = b.decode(enc, errors='ignore')
            cleaned = s.replace('\x00', '').strip()
            if cleaned:
                return cleaned
        except:
            continue
    
    return b.decode('utf-8', errors='replace').replace('\x00', '').strip()

def clean_html_site2(text):
    if text is None or text == "":
        return ""
    try:
        text = str(text) if not isinstance(text, str) else text
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        text = text.replace('\x00', '').strip()
        return text
    except Exception as e:
        print(f"[Site2] ⚠️ خطأ في clean_html: {e} - القيمة: {repr(text)}")
        try:
            return str(text) if text else ""
        except:
            return ""


def solve_captcha_timesms(html_content):
    match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)\s*=?\s*\?', html_content)
    if match:
        n1, op, n2 = int(match.group(1)), match.group(2), int(match.group(3))
        if op == '+': return str(n1 + n2)
        elif op == '-': return str(n1 - n2)
        elif op == '*': return str(n1 * n2)
        elif op == '/': return str(n1 // n2) if n2 else '0'
    return None

def login_site10(account=None):
    global is_logged_in_site10, session10
    print("[TimeSMS] 🔄 محاولة تسجيل الدخول...")
    
    site_key = "TimeSMS"
    if account:
        user = account.get("username")
        pw = account.get("password")
        sess = requests.Session()
        sess.headers.update(session10.headers)
    else:
        user = USERNAME10
        pw = PASSWORD10
        sess = session10

    login_url = SETTINGS[site_key]["login_page_url"]
    submit_url = SETTINGS[site_key]["login_post_url"]

    try:
        resp = sess.get(login_url, timeout=15)
        captcha = solve_captcha_timesms(resp.text)
        if not captcha:
            print("[TimeSMS] ❌ فشل حل الكابتشا")
            return False
        
        data = {'username': user, 'password': pw, 'capt': captcha}
        login_resp = sess.post(submit_url, data=data, headers={'Referer': login_url}, timeout=15, allow_redirects=True)
        
        if 'login' not in str(login_resp.url).lower():
            if not account: is_logged_in_site10 = True
            print("[TimeSMS] ✅ تم تسجيل الدخول بنجاح")
            return sess if account else True
    except Exception as e:
        print(f"[TimeSMS] ❌ خطأ في تسجيل الدخول: {e}")
    return False

def get_sesskey_site2():
    """استخراج sesskey أو _token من صفحة التقارير لـ Fly sms"""
    try:
        resp = session2.get(BASE_URL2 + "/ints/agent/SMSCDRReports", timeout=HTTP_TIMEOUT2)
        if resp.status_code != 200:
            print(f"[Fly sms] ⚠️ فشل جلب صفحة التقارير: {resp.status_code}")
            return None
        
        # البحث عن sesskey في الروابط (نمط قديم)
        match = re.search(r'sesskey=([A-Za-z0-9=]+)', resp.text)
        if match:
            print(f"[Fly sms] ✅ تم استخراج sesskey: {match.group(1)[:10]}...")
            return match.group(1)
        
        # البحث عن CSRF token (نمط جديد)
        match = re.search(r'name="_token".*?value="([^"]+)"', resp.text)
        if match:
            print(f"[Fly sms] ✅ تم استخراج _token: {match.group(1)[:10]}...")
            return match.group(1)
            
        print("[Fly sms] ❌ لم يتم العثور على sesskey أو _token في صفحة التقارير")
        return None
    except Exception as e:
        print(f"[Fly sms] ❌ خطأ في جلب sesskey: {e}")
        return None

def login_site2():
    global is_logged_in_site2, sesskey_site2
    print("[Fly sms] 🔄 محاولة تسجيل الدخول...")
    
    session2.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    })
    
    def do_login():
        try:
            resp = session2.get(LOGIN_PAGE_URL2, timeout=HTTP_TIMEOUT2)
            
            if resp.status_code in [502, 503, 504]:
                print(f"[Fly sms] ⚠️ السيرفر مشغول ({resp.status_code})")
                raise requests.exceptions.HTTPError(f"{resp.status_code} Server Error", response=resp)
            
            match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
            if not match:
                print("[Fly sms] ⚠️ لم يتم العثور على captcha في صفحة تسجيل الدخول")
                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code}")
                return False
            
            num1, num2 = int(match.group(1)), int(match.group(2))
            captcha_answer = num1 + num2
            print(f"[Fly sms] 🧮 حل captcha: {num1} + {num2} = {captcha_answer}")
            
            payload = {
                "username": USERNAME2,
                "password": PASSWORD2,
                "capt": str(captcha_answer)
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": LOGIN_PAGE_URL2,
                "Origin": BASE_URL2,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            print(f"[Fly sms] 📤 إرسال طلب تسجيل الدخول لـ: {USERNAME2}")
            
            resp = session2.post(LOGIN_POST_URL2, data=payload, headers=headers, timeout=HTTP_TIMEOUT2, allow_redirects=True)
            
            print(f"[Fly sms] 📊 حالة الاستجابة: {resp.status_code}")
            
            if resp.status_code in [502, 503, 504]:
                print(f"[Fly sms] ⚠️ السيرفر مشغول ({resp.status_code})")
                raise requests.exceptions.HTTPError(f"{resp.status_code} Server Error", response=resp)
            
            if ("dashboard" in resp.text.lower() or 
                "logout" in resp.text.lower() or 
                "agent" in resp.url.lower() or
                "/ints/agent" in resp.url or
                resp.url != LOGIN_PAGE_URL2):
                print("[Fly sms] ✅ تم تسجيل الدخول بنجاح")
                is_logged_in_site2 = True
                
                # استخراج sesskey فوراً بعد تسجيل الدخول
                global sesskey_site2
                sesskey_site2 = get_sesskey_site2()
                
                return True
            else:
                print("[Fly sms] ❌ فشل تسجيل الدخول")
                if "incorrect" in resp.text.lower() or "invalid" in resp.text.lower():
                    print("[Fly sms] ⚠️ اسم المستخدم أو كلمة المرور غير صحيحة")
                return False
                
        except requests.exceptions.HTTPError as e:
            print(f"[Fly sms] ⚠️ خطأ HTTP: {e}")
            raise
        except Exception as e:
            print(f"[Fly sms] ❌ خطأ في تسجيل الدخول: {e}")
            raise
    
    try:
        return retry_request_site2(do_login, max_retries=5, retry_delay=15)
    except:
        return False

def build_ajax_url_site2(wide_range=False):
    if wide_range:
        start_date = date.today() - timedelta(days=5)
        end_date = date.today() + timedelta(days=1)
    else:
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)
    
    fdate1 = f"{start_date.strftime('%Y-%m-%d')} 00:00:00"
    fdate2 = f"{end_date.strftime('%Y-%m-%d')} 23:59:59"
    
    # بناء بيانات POST بدلاً من GET لـ Fly sms
    post_data = {
        "fdate1": fdate1,
        "fdate2": fdate2,
        "frange": "",
        "fclient": "",
        "fnum": "",
        "fcli": "",
        "fgdate": "",
        "fgmonth": "",
        "fgrange": "",
        "fgclient": "",
        "fgnumber": "",
        "fgcli": "",
        "fg": "0",
        "sesskey": sesskey_site2 if sesskey_site2 else ""
    }
    return BASE_URL2 + AJAX_PATH2, post_data

def fetch_ajax_json_site2(url_data):
    global is_logged_in_site2, sesskey_site2
    
    def do_fetch():
        global sesskey_site2
        # التأكد من وجود sesskey قبل جلب البيانات
        if not sesskey_site2:
            print("[Fly sms] ⚠️ لا يوجد sesskey متاح. محاولة استخراجه.")
            sesskey_site2 = get_sesskey_site2()
            if not sesskey_site2:
                raise Exception("Session expired")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE_URL2 + "/ints/agent/SMSCDRReports",
            "Origin": BASE_URL2
        }
        
        ajax_url, post_data = url_data
        # تحديث sesskey في البيانات قبل الإرسال
        post_data["sesskey"] = sesskey_site2 if sesskey_site2 else ""
        
        r = session2.post(ajax_url, data=post_data, timeout=HTTP_TIMEOUT2, headers=headers)
        
        if r.status_code == 403:
            raise Exception("Session expired")
        
        if r.status_code in [502, 503, 504]:
            raise requests.exceptions.HTTPError(f"{r.status_code} Server Error", response=r)
        
        if r.status_code == 401:
            raise Exception("Session expired")
        
        r.raise_for_status()
        
        try:
            data = r.json()
            if not isinstance(data, (dict, list)):
                raise Exception("Invalid JSON response")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            if "login" in r.text.lower() and r.url and "login" in r.url.lower():
                raise Exception("Session expired")
            raise
    
    try:
        return retry_request_site2(do_fetch, max_retries=5, retry_delay=10)
    except Exception as e:
        error_str = str(e)
        if "Session expired" in error_str:
            print("[Fly sms] ⚠️ انتهت صلاحية الجلسة. إعادة تسجيل الدخول...")
            is_logged_in_site2 = False
            if login_site2():
                is_logged_in_site2 = True
                try:
                    return retry_request_site2(do_fetch, max_retries=5, retry_delay=10)
                except:
                    return None
            else:
                return None
        if "503" in error_str or "502" in error_str or "504" in error_str:
            print(f"[Fly sms] ⚠️ السيرفر مشغول، المحاولة مرة أخرى بعد فترة...")
            time.sleep(30)
            try:
                return retry_request_site2(do_fetch, max_retries=3, retry_delay=15)
            except:
                return None
        print(f"[Fly sms] ❌ خطأ في جلب/تحليل AJAX: {e}")
        return None

def extract_rows_from_json_site2(j):
    if j is None:
        return []
    for key in ("data", "aaData", "rows", "aa_data"):
        if isinstance(j, dict) and key in j:
            return j[key]
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for v in j.values():
            if isinstance(v, list):
                return v
    return []

def row_to_tuple_site2(row):
    date_str = ""
    number_str = ""
    sms_str = ""
    try:
        if isinstance(row, (list, tuple)):
            if len(row) > IDX_DATE_SITE2:
                val = row[IDX_DATE_SITE2]
                date_str = clean_html_site2(str(val) if val is not None else "")
            if len(row) > IDX_NUMBER_SITE2:
                val = row[IDX_NUMBER_SITE2]
                number_str = clean_number(str(val) if val is not None else "")
            if len(row) > IDX_SMS_SITE2:
                val = row[IDX_SMS_SITE2]
                sms_str = try_decode_site2(val) if val is not None else ""
                sms_str = clean_html_site2(sms_str)
        elif isinstance(row, dict):
            for k in ("date","time","datetime","dt","created_at"):
                if k in row and not date_str:
                    val = row[k]
                    date_str = clean_html_site2(str(val) if val is not None else "")
            for k in ("number","msisdn","cli","from","sender"):
                if k in row and not number_str:
                    val = row[k]
                    number_str = clean_number(str(val) if val is not None else "")
            for k in ("sms","message","msg","body","text"):
                if k in row and not sms_str:
                    val = row[k]
                    sms_str = try_decode_site2(val) if val is not None else ""
                    sms_str = clean_html_site2(sms_str)
            if not sms_str:
                vals = list(row.values())
                if len(vals) > IDX_SMS_SITE2:
                    val = vals[IDX_SMS_SITE2]
                    sms_str = try_decode_site2(val) if val is not None else ""
                    sms_str = clean_html_site2(sms_str)
                elif vals:
                    val = vals[-1]
                    sms_str = try_decode_site2(val) if val is not None else ""
                    sms_str = clean_html_site2(sms_str)
    except Exception as e:
        print(f"[Site2] ⚠️ خطأ في row_to_tuple: {e}")
        print(f"[Site2] Row data: {row}")
    
    unique_key = f"{date_str}|{number_str}|{sms_str}"
    return date_str, number_str, sms_str, unique_key

def load_last_seen_key_site2():
    global last_seen_key_site2
    if os.path.exists(LAST_MESSAGE_FILE_SITE2):
        try:
            with open(LAST_MESSAGE_FILE_SITE2, "r", encoding="utf-8") as f:
                last_seen_key_site2 = f.read().strip()
                print(f"[Site2] 📋 تم تحميل آخر رسالة مشاهدة: {last_seen_key_site2[:50]}..." if last_seen_key_site2 else "[Site2] 📋 لا توجد رسائل سابقة")
        except:
            last_seen_key_site2 = ""
    else:
        last_seen_key_site2 = ""

def save_last_seen_key_site2():
    try:
        with open(LAST_MESSAGE_FILE_SITE2, "w", encoding="utf-8") as f:
            f.write(last_seen_key_site2)
        print(f"[Site2] 💾 تم حفظ آخر رسالة مشاهدة")
    except Exception as e:
        print(f"[Site2] ❌ خطأ في حفظ آخر رسالة: {str(e)}")

def load_data():
    global COUNTRIES, CHANNELS, USERS, ADMINS, BANNED, OTP_GROUP, GROUPS, REFERRALS, NUMBERS_ADMINS

    if os.path.exists(COUNTRIES_FILE):
        with open(COUNTRIES_FILE, "r", encoding="utf-8") as f:
            COUNTRIES = json.load(f)
        # تصحيح اسم المغرب إذا كان UNKNOWN وتصحيح Barbados
        for cid, info in COUNTRIES.items():
            if info.get("display_name") == "UNKNOWN" and (str(info.get("code")) == "212" or cid == "MA"):
                info["display_name"] = "Morocco"
            if str(info.get("code")) == "1" or info.get("display_name") == "Unknown" and str(info.get("code")) == "1":
                info["display_name"] = "Barbados"
                info["flag"] = "<tg-emoji emoji-id='5294526187165471742'>🇧🇧</tg-emoji>"

    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            CHANNELS = json.load(f)

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            USERS = json.load(f)

    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            ADMINS = json.load(f)

    if MAIN_ADMIN_ID != 0 and MAIN_ADMIN_ID not in ADMINS:
        ADMINS.append(MAIN_ADMIN_ID)
        save_admins()

    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            BANNED = json.load(f)

    if os.path.exists(OTP_GROUP_FILE):
        with open(OTP_GROUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            OTP_GROUP = data.get("group_id")

    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            GROUPS = json.load(f)
    
    if os.path.exists(REFERRALS_FILE):
        with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
            REFERRALS = json.load(f)
    
    load_numbers_admins()
    load_statistics()


def save_countries():
    with open(COUNTRIES_FILE, "w", encoding="utf-8") as f:
        json.dump(COUNTRIES, f, indent=2, ensure_ascii=False)

def save_channels():
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(CHANNELS, f, indent=2, ensure_ascii=False)

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(USERS, f, indent=2, ensure_ascii=False)

def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(ADMINS, f, indent=2, ensure_ascii=False)

def save_banned():
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(BANNED, f, indent=2, ensure_ascii=False)

def save_otp_group():
    with open(OTP_GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump({"group_id": OTP_GROUP}, f, indent=2)

def save_groups():
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(GROUPS, f, indent=2)

def cleanup_old_numbers_files(country_code):
   
    pass

def load_referrals():
    global REFERRALS
    if os.path.exists(REFERRALS_FILE):
        try:
            with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
                REFERRALS = json.load(f)
        except:
            REFERRALS = {}
    return REFERRALS

def save_referrals(data=None):
    global REFERRALS
    if data:
        REFERRALS = data
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        json.dump(REFERRALS, f, indent=2, ensure_ascii=False)

def load_referral_settings():
    if os.path.exists(REFERRAL_SETTINGS_FILE):
        try:
            with open(REFERRAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_REFERRAL_SETTINGS.copy()

def save_referral_settings(settings):
    with open(REFERRAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def load_withdrawal_requests():
    if os.path.exists(WITHDRAWAL_REQUESTS_FILE):
        try:
            with open(WITHDRAWAL_REQUESTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def save_withdrawal_requests(requests):
    with open(WITHDRAWAL_REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, indent=2, ensure_ascii=False)

DEFAULT_WITHDRAWAL_METHODS = {
    "vodafone": {"name_ar": "فودافون كاش", "name_en": "Vodafone Cash", "enabled": True, "details_ar": "رقم الهاتف", "details_en": "Phone number"},
    "usdt_trc20": {"name_ar": "USDT (TRC20)", "name_en": "USDT (TRC20)", "enabled": True, "details_ar": "عنوان محفظة TRC20", "details_en": "TRC20 wallet address"},
    "usdt_bep20": {"name_ar": "USDT (BEP20)", "name_en": "USDT (BEP20)", "enabled": True, "details_ar": "عنوان محفظة BEP20", "details_en": "BEP20 wallet address"},
    "binance_id": {"name_ar": "Binance ID", "name_en": "Binance ID", "enabled": True, "details_ar": "Binance Pay ID أو Email", "details_en": "Binance Pay ID or Email"}
}

def load_withdrawal_methods():
    if os.path.exists(WITHDRAWAL_METHODS_FILE):
        try:
            with open(WITHDRAWAL_METHODS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_WITHDRAWAL_METHODS.copy()

def save_withdrawal_methods(methods):
    with open(WITHDRAWAL_METHODS_FILE, "w", encoding="utf-8") as f:
        json.dump(methods, f, indent=2, ensure_ascii=False)

def load_welcome_messages():
    if os.path.exists(WELCOME_MESSAGES_FILE):
        try:
            with open(WELCOME_MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_WELCOME_MESSAGES.copy()

def save_welcome_messages(messages):
    with open(WELCOME_MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

def generate_referral_code(user_id):
    
    import hashlib
    hash_input = f"{user_id}_{datetime.now().timestamp()}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()

def get_user_referral_data(user_id):
    
    global REFERRALS
    REFERRALS = load_referrals()
    user_key = str(user_id)
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referral_code": generate_referral_code(user_id),
            "referred_by": None,
            "referrals": [],
            "referred_users_codes": {},
            "active_referrals": 0,
            "active_referrals_list": [],
            "codes_received": 0,
            "balance": 0.0,
            "total_earned": 0.0,
            "referral_used": False
        }
        save_referrals(REFERRALS)
    else:
        if "referral_code" not in REFERRALS[user_key]:
            REFERRALS[user_key]["referral_code"] = generate_referral_code(user_id)
            save_referrals(REFERRALS)
        if "referred_users_codes" not in REFERRALS[user_key]:
            REFERRALS[user_key]["referred_users_codes"] = {}
            save_referrals(REFERRALS)
        if "active_referrals_list" not in REFERRALS[user_key]:
            REFERRALS[user_key]["active_referrals_list"] = []
            save_referrals(REFERRALS)
    return REFERRALS[user_key]

def process_referral(user_id, referrer_id):
    
    global REFERRALS
    REFERRALS = load_referrals()
    settings = load_referral_settings()
    
    user_key = str(user_id)
    referrer_key = str(referrer_id)
    
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referred_by": referrer_key,
            "referrals": [],
            "active_referrals": 0,
            "codes_received": 0,
            "balance": 0.0,
            "total_earned": 0.0
        }
    else:
        if REFERRALS[user_key].get("referred_by"):
            return False
        REFERRALS[user_key]["referred_by"] = referrer_key
    
    if referrer_key not in REFERRALS:
        REFERRALS[referrer_key] = {
            "referred_by": None,
            "referrals": [],
            "active_referrals": 0,
            "codes_received": 0,
            "balance": 0.0,
            "total_earned": 0.0
        }
    
    if user_key not in REFERRALS[referrer_key]["referrals"]:
        REFERRALS[referrer_key]["referrals"].append(user_key)
    
    save_referrals(REFERRALS)
    return True

def add_code_bonus(user_id):
    
    global REFERRALS
    REFERRALS = load_referrals()
    settings = load_referral_settings()
    
    user_key = str(user_id)
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referred_by": None,
            "referrals": [],
            "active_referrals": 0,
            "codes_received": 0,
            "balance": 0.0,
            "total_earned": 0.0
        }
    
    REFERRALS[user_key]["codes_received"] += 1
    code_bonus = settings.get("code_bonus", 0.01)
    REFERRALS[user_key]["balance"] += code_bonus
    REFERRALS[user_key]["total_earned"] += code_bonus
    
    referrer_key = REFERRALS[user_key].get("referred_by")
    if referrer_key and referrer_key in REFERRALS:
        codes_required = settings.get("codes_required_for_referral", 3)
        user_codes = REFERRALS[user_key]["codes_received"]
        
        if user_codes == codes_required:
            REFERRALS[referrer_key]["active_referrals"] += 1
            referral_bonus = settings.get("referral_bonus", 0.50)
            REFERRALS[referrer_key]["balance"] += referral_bonus
            REFERRALS[referrer_key]["total_earned"] += referral_bonus
            
            try:
                referrer_lang = get_user_language(int(referrer_key))
                if referrer_lang == "ar":
                    notify_msg = (
                        f"🎉 <b>تهانينا! إحالة جديدة نشطة!</b>\n\n"
                        f"👤 المستخدم <code>{user_id}</code> أصبح إحالة نشطة!\n"
                        f"💰 تم إضافة <b>${referral_bonus:.2f}</b> لرصيدك!\n\n"
                        f"📊 إجمالي الإحالات النشطة: <b>{REFERRALS[referrer_key]['active_referrals']}</b>\n"
                        f"💵 رصيدك الحالي: <b>${REFERRALS[referrer_key]['balance']:.2f}</b>"
                    )
                else:
                    notify_msg = (
                        f"🎉 <b>Congratulations! New Active Referral!</b>\n\n"
                        f"👤 User <code>{user_id}</code> became an active referral!\n"
                        f"💰 <b>${referral_bonus:.2f}</b> added to your balance!\n\n"
                        f"📊 Total active referrals: <b>{REFERRALS[referrer_key]['active_referrals']}</b>\n"
                        f"💵 Your current balance: <b>${REFERRALS[referrer_key]['balance']:.2f}</b>"
                    )
                bot.send_message(int(referrer_key), notify_msg, parse_mode="HTML")
            except Exception as notify_err:
                print(f"⚠️ خطأ في إرسال إشعار الإحالة: {notify_err}")
    
    save_referrals(REFERRALS)

REFERRAL_SETTINGS = load_referral_settings()
WELCOME_MESSAGES = load_welcome_messages()

def load_statistics():
    global STATISTICS
    if os.path.exists(STATISTICS_FILE):
        try:
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
                STATISTICS = json.load(f)
        except:
            pass

def save_statistics():
    with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(STATISTICS, f, indent=2, ensure_ascii=False)

def update_statistics(country_name=None):
    global STATISTICS
    now = datetime.now()
    today = now.date().isoformat()
    week_num = now.isocalendar()[1]
    month = now.strftime('%Y-%m')
    
    if STATISTICS.get("last_reset_day") != today:
        STATISTICS["codes_today"] = 0
        STATISTICS["last_reset_day"] = today
    
    if STATISTICS.get("last_reset_week") != week_num:
        STATISTICS["codes_this_week"] = 0
        STATISTICS["last_reset_week"] = week_num
    
    if STATISTICS.get("last_reset_month") != month:
        STATISTICS["codes_this_month"] = 0
        STATISTICS["last_reset_month"] = month
    
    STATISTICS["total_codes"] += 1
    STATISTICS["codes_today"] += 1
    STATISTICS["codes_this_week"] += 1
    STATISTICS["codes_this_month"] += 1
    
    if today not in STATISTICS.get("daily_history", {}):
        if "daily_history" not in STATISTICS:
            STATISTICS["daily_history"] = {}
        STATISTICS["daily_history"][today] = 0
    STATISTICS["daily_history"][today] += 1
    
    if country_name:
        if "recent_activations" not in STATISTICS:
            STATISTICS["recent_activations"] = []
        STATISTICS["recent_activations"].append((now.timestamp(), country_name))
        # Keep only last 60 minutes of activations to be safe, though we use 10 mins for display
        one_hour_ago = (now - timedelta(hours=1)).timestamp()
        STATISTICS["recent_activations"] = [act for act in STATISTICS["recent_activations"] if act[0] > one_hour_ago]

    save_statistics()

def get_statistics_text():
    total_users = len(USERS)
    total_codes = STATISTICS.get("total_codes", 0)
    codes_today = STATISTICS.get("codes_today", 0)
    codes_week = STATISTICS.get("codes_this_week", 0)
    codes_month = STATISTICS.get("codes_this_month", 0)
    
    text = f"<tg-emoji emoji-id='5042290883949495533'>◾</tg-emoji> <b>Bot Statistics</b>\n\n"
    text += f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>Users:</b> {total_users}\n"
    text += f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>All Codes</b> {total_codes}\n\n"
    text += f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>Today Codes</b> {codes_today}\n"
    text += f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>This Weak Codes</b> {codes_week}\n"
    text += f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>This Mounth Codes</b> {codes_month}\n"
    
    return text

def is_admin(user_id):
    return user_id == MAIN_ADMIN_ID or user_id in ADMINS

def is_banned(user_id):
    return user_id in BANNED

def check_subscription(user_id):
    if not CHANNELS: return True
    if is_admin(user_id): return True
    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"⚠️ Error checking sub for {channel['id']}: {e}")
            # إذا لم يستطع البوت التحقق (بسبب نقص صلاحيات أو غيره)، نعتبره غير مشترك لضمان الاشتراك
            return False
    return True

def get_subscription_message(user_id):
    return "<b>════《 <tg-emoji emoji-id='5197288647275071607'>◾</tg-emoji> ACCESS REQUIRED 》════\nYou must join all channels below to use this bot:\nClick the buttons to join, then click Verify.</b>"

def get_full_subscription_keyboard(user_id):
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        url = ch.get('url')
        if not url:
            try:
                chat = bot.get_chat(ch['id'])
                if chat.invite_link:
                    url = chat.invite_link
                elif chat.username:
                    url = f"https://t.me/{chat.username}"
            except:
                pass
        
        if url:
            markup.add(InlineKeyboardButton(ch['name'], url=url, style="primary", icon_custom_emoji_id="5330237710655306682"))
        else:
            # إذا فشل كل شيء، نستخدم اليوزر نيم المخزن
            username = ch.get('username', '').replace('@', '')
            if username:
                markup.add(InlineKeyboardButton(ch['name'], url=f"https://t.me/{username}", style="primary", icon_custom_emoji_id="5330237710655306682"))

    markup.add(InlineKeyboardButton("✅ تم الاشتراك" if get_user_language(user_id) == "ar" else "✅ Subscribed", callback_data="check_sub", style="success"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        start(call.message)
    else: 
        bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد في جميع القنوات!", show_alert=True)
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=get_subscription_message(user_id),
                parse_mode="HTML",
                reply_markup=get_full_subscription_keyboard(user_id)
            )
        except: pass

def get_first_unjoined_channel(user_id):
    if not CHANNELS: return None
    if is_admin(user_id): return None
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel['id'], user_id).status
            if status not in ['member', 'administrator', 'creator']: return channel
        except Exception as e:
            print(f"⚠️ Error getting unjoined channel: {e}")
            return channel
    return None

def get_subscription_keyboard():

    markup = InlineKeyboardMarkup(row_width=1)

    for channel in CHANNELS:
        channel_name = channel.get("name", "Channel")
        channel_url = channel.get("url", "")
        btn = InlineKeyboardButton(f"🔗 Join {channel_name}", url=channel_url)
        markup.add(btn)

    verify_btn = InlineKeyboardButton("✅ تحقق / Verify", callback_data="verify_subscription", style="success")
    markup.add(verify_btn)

    return markup

def get_all_channels_keyboard(user_id=None):
    markup = InlineKeyboardMarkup(row_width=1)
    lang = get_user_language(user_id) if user_id else "ar"
    
    for channel in CHANNELS:
        channel_name = channel.get(f"name_{lang}", channel.get("name", "Channel"))
        channel_url = channel.get("url", "")
        markup.add(InlineKeyboardButton(f"{channel_name}", url=channel_url, icon_custom_emoji_id="5330237710655306682"))
    
    if lang == "ar":
        verify_text = "✅ Verify Subscription"
    else:
        verify_text = "✅ Verify Subscription"
        
    markup.add(InlineKeyboardButton(verify_text, callback_data="verify_subscription", style="success"))
    
    return markup

def get_single_channel_keyboard(channel, user_id=None):
    lang = get_user_language(user_id) if user_id else "ar"
    markup = InlineKeyboardMarkup()
    btn_name = channel.get(f"name_{lang}", channel.get("name", "Join 🔗"))
    markup.add(InlineKeyboardButton(btn_name, url=channel['url'], style="primary", icon_custom_emoji_id="5330237710655306682"))
    
    if lang == "ar":
        verify_text = "✅ Verify Subscription"
    else:
        verify_text = "✅ Verify Subscription"
        
    markup.add(InlineKeyboardButton(verify_text, callback_data="verify_subscription", style="success"))
    return markup

def get_all_channels_message(user_id):
    return "<b>════《 <tg-emoji emoji-id='5197288647275071607'>◾</tg-emoji> ACCESS REQUIRED 》════\nYou must join all channels below to use this bot:\nClick the buttons to join, then click Verify.</b>"

def get_subscription_message(user_id):
    return "<b>════《 <tg-emoji emoji-id='5197288647275071607'>◾</tg-emoji> ACCESS REQUIRED 》════\n\nYou must join all channels below to use this bot:\n\nClick the buttons to join, then click Verify.</b>"

def get_main_menu_lang(user_id):
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(t(user_id, "choose_country"), callback_data="choose_country"),
        InlineKeyboardButton(t(user_id, "my_account"), callback_data="my_account")
    )
    
    withdraw_text = "💰 سحب الرصيد" if lang == "ar" else "💰 Withdraw"
    help_text = "❓ مساعدة" if lang == "ar" else "❓ Help"
    markup.add(
        InlineKeyboardButton(withdraw_text, callback_data="withdraw_balance"),
        InlineKeyboardButton(help_text, callback_data="show_instructions")
    )
    
    links = load_button_links()
    dev_text = "👨‍💻 المطور" if lang == "ar" else "👨‍💻 Developer"
    markup.add(
        InlineKeyboardButton(dev_text, url=links.get("developer_link", f"tg://user?id={MAIN_ADMIN_ID}"))
    )
    return markup

def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Accounts", callback_data="admin_accounts_and_sites", style="primary", icon_custom_emoji_id="5382322671679708881")),
    markup.add(InlineKeyboardButton("Countries", callback_data="admin_countries_manage", style="primary", icon_custom_emoji_id="5381990043642502553")),
    markup.add(InlineKeyboardButton("Channels", callback_data="admin_channels_manage", style="primary", icon_custom_emoji_id="5381879959335738545")),
    markup.add(InlineKeyboardButton("Statistics", callback_data="admin_statistics", style="primary", icon_custom_emoji_id="5382054253403577563")),
    markup.add(InlineKeyboardButton("Broadcast", callback_data="admin_broadcast_menu", style="primary", icon_custom_emoji_id="5391197405553107640")),
    markup.add(InlineKeyboardButton("Manage Admins", callback_data="admin_admins_manage", style="primary", icon_custom_emoji_id="5390966190283694453")),
    markup.add(InlineKeyboardButton("Manage Ban", callback_data="admin_ban_manage", style="primary", icon_custom_emoji_id="5382132232829804982")),
    
    rotp_text = "Return OTP: ON" if RETURN_OTP_ENABLED else "Return OTP: OFF"
    rotp_style = "success" if RETURN_OTP_ENABLED else "danger"
    markup.add(InlineKeyboardButton(rotp_text, callback_data="toggle_return_otp", style=rotp_style))
    
    markup.add(InlineKeyboardButton("Back to Main Menu", callback_data="back_to_main", icon_custom_emoji_id="6206505206197261313"))
    return markup

def get_sites_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("GROUP", callback_data="site_config_GROUP", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Fly sms", callback_data="site_config_Fly sms", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Number Panel", callback_data="site_config_Number_Panel", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Bolt", callback_data="site_config_Bolt", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("IMS", callback_data="site_config_IMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("IMS Client", callback_data="site_config_IMS_New", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Roxy SMS", callback_data="site_config_Roxy SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("iVAS SMS", callback_data="site_config_iVASMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("MSI", callback_data="site_config_MSI", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("proton SMS", callback_data="site_config_proton SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    # New panels added to sites menu
    markup.add(
        InlineKeyboardButton("Konekta API", callback_data="site_config_Konekta_API", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("TimeSMS API", callback_data="site_config_TimeSMS_API", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Fire SMS", callback_data="site_config_Fire_SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Hadi SMS", callback_data="site_config_Hadi_SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    # البانلز الجديدة
    markup.add(
        InlineKeyboardButton("Seven1Tel", callback_data="site_config_Seven1Tel", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Gaza SMS", callback_data="site_config_Gaza SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Km sms", callback_data="site_config_Km sms", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Grand SMS", callback_data="site_config_Grand SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Purple SMS", callback_data="site_config_Purple SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("MBC", callback_data="site_config_MBC", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Basha", callback_data="site_config_Basha", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Flash_SMS", callback_data="site_config_Flash_SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Horus", callback_data="site_config_Horus", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Flex", callback_data="site_config_Flex", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("rsayel", callback_data="site_config_rsayel", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("KSI", callback_data="site_config_ksi", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Green 🌿", callback_data="site_config_green", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("grand", callback_data="site_config_grand", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Squad", callback_data="site_config_Squad", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Sniper", callback_data="site_config_Sniper", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Lamix", callback_data="site_config_Lamix", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Num44", callback_data="site_config_Num44", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("XAP", callback_data="site_config_XAP", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("EMO SMS", callback_data="site_config_EMO SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Pac Call", callback_data="site_config_Pac_Call", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("PRIM-FLASH", callback_data="site_config_PRIM-FLASH", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin", style="success", icon_custom_emoji_id="5994442901059276913"))
    return markup

def get_site_config_menu(site_key, account_id=None):
    site_name = SETTINGS[site_key]["name"]
    short_id = account_id[:8] if account_id else ""
    markup = InlineKeyboardMarkup(row_width=2)
    # For API panels, we don't have username/password, only token
    if site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS"]:
        markup.add(
            InlineKeyboardButton("🔐 تغيير API Token", callback_data=f"site_change_token_{site_key}_{short_id}")
        )
    else:
        markup.add(
        InlineKeyboardButton("👤 تغيير اليوزر", callback_data=f"site_change_user_{site_key}_{short_id}"),
            InlineKeyboardButton("🔑 تغيير الباسورد", callback_data=f"site_change_pass_{site_key}_{short_id}")
        )
    markup.add(
        InlineKeyboardButton("⏱ فترة البحث", callback_data=f"site_change_interval_{site_key}"),
        InlineKeyboardButton("⏳ وقت الانتظار", callback_data=f"site_change_timeout_{site_key}")
    )
    markup.add(
        InlineKeyboardButton("🔓 اختبار تسجيل الدخول", callback_data=f"site_test_login_{site_key}_{short_id}"),
        InlineKeyboardButton("📥 اختبار جلب كود", callback_data=f"site_test_fetch_{site_key}_{short_id}")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_sites_menu", style="success", icon_custom_emoji_id="5994442901059276913"))
    return markup

def get_site_accounts_selection_menu(site_key):
    site_name = SETTINGS[site_key]["name"]
    accounts = get_site_accounts(site_key)
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    for idx, account in enumerate(accounts, 1):
        username = account.get("username") or account.get("api_token", "N/A")
        account_id = account.get("id", "")
        short_id = account_id[:8] if account_id else ""
        # Truncate token for display
        if len(username) > 15:
            username = username[:12] + "..."
        buttons.append(
            InlineKeyboardButton(
                f"👤 {idx}. {username}",
                callback_data=f"select_account_config_{site_key}_{short_id}"
            )
        )
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i+1])
        else:
            markup.add(buttons[i])
    
    markup.add(InlineKeyboardButton("Back", callback_data="admin_sites_menu", style="success", icon_custom_emoji_id="5994442901059276913"))
    return markup

def get_accounts_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("GROUP", callback_data="accounts_site_GROUP", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Fly sms", callback_data="accounts_site_Fly sms", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Number Panel", callback_data="accounts_site_Number_Panel", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Bolt", callback_data="accounts_site_Bolt", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("IMS", callback_data="accounts_site_IMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("IMS Client", callback_data="accounts_site_IMS_New", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Roxy SMS", callback_data="accounts_site_Roxy SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("iVAS SMS", callback_data="accounts_site_iVASMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("MSI", callback_data="accounts_site_MSI", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("proton SMS", callback_data="accounts_site_proton SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Konekta API", callback_data="accounts_site_Konekta_API", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("TimeSMS API", callback_data="accounts_site_TimeSMS_API", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Fire SMS", callback_data="accounts_site_Fire_SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Hadi SMS", callback_data="accounts_site_Hadi_SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    # البانلز الجديدة
    markup.add(
        InlineKeyboardButton("Seven1Tel", callback_data="accounts_site_Seven1Tel", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Gaza SMS", callback_data="accounts_site_Gaza SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Km sms", callback_data="accounts_site_Km sms", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Grand SMS", callback_data="accounts_site_Grand SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Purple SMS", callback_data="accounts_site_Purple SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("MBC", callback_data="accounts_site_MBC", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Basha", callback_data="accounts_site_Basha", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Flash_SMS", callback_data="accounts_site_Flash_SMS", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Horus", callback_data="accounts_site_Horus", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Flex", callback_data="accounts_site_Flex", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("rsayel", callback_data="accounts_site_rsayel", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("KSI", callback_data="accounts_site_ksi", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Green 🌿", callback_data="accounts_site_green", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("grand", callback_data="accounts_site_grand", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Squad", callback_data="accounts_site_Squad", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Sniper", callback_data="accounts_site_Sniper", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Lamix", callback_data="accounts_site_Lamix", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("Num44", callback_data="accounts_site_Num44", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("XAP", callback_data="accounts_site_XAP", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("EMO SMS", callback_data="accounts_site_EMO SMS", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(
        InlineKeyboardButton("Pac Call", callback_data="accounts_site_Pac_Call", style="primary", icon_custom_emoji_id="5390854796011906616"),
        InlineKeyboardButton("PRIM-FLASH", callback_data="accounts_site_PRIM-FLASH", style="primary", icon_custom_emoji_id="5390854796011906616")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    return markup

def get_site_accounts_menu(site_key):
    site_name = SETTINGS[site_key]["name"]
    accounts = get_site_accounts(site_key)
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    if accounts:
        buttons = []
        for idx, account in enumerate(accounts, 1):
            username = account.get("username") or account.get("api_token", "N/A")
            account_id = account.get("id", "")
            short_id = account_id[:8] if account_id else ""
            # Truncate for display
            if len(username) > 15:
                username = username[:12] + "..."
            buttons.append(
                InlineKeyboardButton(
                    f"👤 {idx}. {username}",
                    callback_data=f"view_account_{site_key}_{short_id}"
                )
            )
        
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.add(buttons[i], buttons[i+1])
            else:
                markup.add(buttons[i])
    
    markup.add(
        InlineKeyboardButton("➕ إضافة حساب جديد", callback_data=f"add_account_{site_key}")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_accounts_menu", style="success", icon_custom_emoji_id="5994442901059276913"))
    return markup

def get_account_details_menu(site_key, account_id):
    short_id = account_id[:8] if account_id else ""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🗑 حذف الحساب", callback_data=f"delete_account_{site_key}_{short_id}"),
        InlineKeyboardButton("🔙 رجوع للحسابات", callback_data=f"accounts_site_{site_key}")
    )
    return markup

def try_decode(raw):
    if raw is None:
        return ""
    
    if isinstance(raw, str):
        
        return raw.replace('\x00', '').strip()
    
    if not isinstance(raw, bytes):
        try:
            
            return str(raw).replace('\x00', '').strip()
        except:
            return ""

  
    encodings = (
        "utf-8", 
        "utf-16", "utf-16-be", "utf-16-le",
        "cp1256", "windows-1256", "iso-8859-6", 
        "cp1251", "windows-1251", "koi8-r",    
        "latin-1", "iso-8859-1"
    )
    
    for enc in encodings:
        try:
            s = raw.decode(enc)
            
            return s.replace('\x00', '').strip()
        except:
            continue
    
    return raw.decode('utf-8', errors='replace').replace('\x00', '').strip()

def mask_number(num):
    s = str(num)
    digits = re.sub(r'\D', '', s)
    if len(digits) <= 6:
        return s
    
    if len(digits) >= 11:
        return digits[:5] + "••" + digits[-3:]
    return digits[:5] + "••" + digits[-2:]

import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_number
import pycountry

SPECIAL_FLAGS = {
    "BB": "<tg-emoji emoji-id='5294526187165471742'>🇧🇧</tg-emoji>",
    "RU": "<tg-emoji emoji-id='5294335323113807278'>🇷🇺</tg-emoji>",
    "EG": "<tg-emoji emoji-id='5293992082212409502'>🇪🇬</tg-emoji>",
    "ZA": "<tg-emoji emoji-id='5976697079739718234'>🇿🇦</tg-emoji>",
    "GR": "<tg-emoji emoji-id='5976335971774372579'>🇬🇷</tg-emoji>",
    "NL": "<tg-emoji emoji-id='5291917797692042265'>🇳🇱</tg-emoji>",
    "BE": "<tg-emoji emoji-id='5976300439509932178'>🇧🇪</tg-emoji>",
    "FR": "<tg-emoji emoji-id='5976706494308030299'>🇫🇷</tg-emoji>",
    "ES": "<tg-emoji emoji-id='5976424031488843687'>🇪🇸</tg-emoji>",
    "HU": "<tg-emoji emoji-id='5294229581018975260'>🇭🇺</tg-emoji>",
    "IT": "<tg-emoji emoji-id='5976298085867854649'>🇮🇹</tg-emoji>",
    "RO": "<tg-emoji emoji-id='5976646540859546652'>🇷🇴</tg-emoji>",
    "CH": "<tg-emoji emoji-id='5976561599291333244'>🇨🇭</tg-emoji>",
    "AT": "<tg-emoji emoji-id='5976586982548051976'>🇦🇹</tg-emoji>",
    "GB": "<tg-emoji emoji-id='5976531856642807659'>🇬🇧</tg-emoji>",
    "DK": "<tg-emoji emoji-id='5976380446160723453'>🇩🇰</tg-emoji>",
    "SE": "<tg-emoji emoji-id='5976775179425028923'>🇸🇪</tg-emoji>",
    "NO": "<tg-emoji emoji-id='5291761718580502030'>🇳🇴</tg-emoji>",
    "PL": "<tg-emoji emoji-id='5976482692152170488'>🇵🇱</tg-emoji>",
    "DE": "<tg-emoji emoji-id='5292013274815028523'>🇩🇪</tg-emoji>",
    "PE": "<tg-emoji emoji-id='5976420350701869282'>🇵🇪</tg-emoji>",
    "MX": "<tg-emoji emoji-id='5976658300480002579'>🇲🇽</tg-emoji>",
    "CU": "<tg-emoji emoji-id='5357035553508308603'>🇨🇺</tg-emoji>",
    "AR": "<tg-emoji emoji-id='5976803839741799351'>🇦🇷</tg-emoji>",
    "BR": "<tg-emoji emoji-id='5976287034917001256'>🇧🇷</tg-emoji>",
    "CL": "<tg-emoji emoji-id='5978610156957603801'>🇨🇱</tg-emoji>",
    "CO": "<tg-emoji emoji-id='5976555951409339416'>🇨🇴</tg-emoji>",
    "VE": "<tg-emoji emoji-id='5294476442854247878'>🇻🇪</tg-emoji>",
    "MY": "<tg-emoji emoji-id='5976838031976437927'>🇲🇾</tg-emoji>",
    "AU": "<tg-emoji emoji-id='5976552377996548545'>🇦🇺</tg-emoji>",
    "ID": "<tg-emoji emoji-id='5294378161117614233'>🇮🇩</tg-emoji>",
    "PH": "<tg-emoji emoji-id='5976772181537858123'>🇵🇭</tg-emoji>",
    "NZ": "<tg-emoji emoji-id='5976512722563503846'>🇳🇿</tg-emoji>",
    "SG": "<tg-emoji emoji-id='5976545437329399582'>🇸🇬</tg-emoji>",
    "TH": "<tg-emoji emoji-id='5976342573139106020'>🇹🇭</tg-emoji>",
    "JP": "<tg-emoji emoji-id='5976688764683033429'>🇯🇵</tg-emoji>",
    "KR": "<tg-emoji emoji-id='5976617773168597444'>🇰🇷</tg-emoji>",
    "VN": "<tg-emoji emoji-id='5976537109387810524'>🇻🇳</tg-emoji>",
    "CN": "<tg-emoji emoji-id='5976702693261975275'>🇨🇳</tg-emoji>",
    "TR": "<tg-emoji emoji-id='5976491638569048813'>🇹🇷</tg-emoji>",
    "IN": "<tg-emoji emoji-id='5976491823252642237'>🇮🇳</tg-emoji>",
    "PK": "<tg-emoji emoji-id='5976723210320748190'>🇵🇰</tg-emoji>",
    "AF": "<tg-emoji emoji-id='5976277263866403415'>🇦🇫</tg-emoji>",
    "LK": "<tg-emoji emoji-id='5976302702957697673'>🇱🇰</tg-emoji>",
    "MM": "<tg-emoji emoji-id='5294254478944393569'>🇲🇲</tg-emoji>",
    "IR": "<tg-emoji emoji-id='5976430585608935514'>🇮🇷</tg-emoji>",
    "MA": "<tg-emoji emoji-id='5224530035695693965'>🇲🇦</tg-emoji>",
    "DZ": "<tg-emoji emoji-id='5294048127240655242'>🇩🇿</tg-emoji>",
    "TN": "<tg-emoji emoji-id='5294484680601521871'>🇹🇳</tg-emoji>",
    "LY": "<tg-emoji emoji-id='5893101223564810175'>🇱🇾</tg-emoji>",
    "GM": "<tg-emoji emoji-id='5294399820637688352'>🇬🇲</tg-emoji>",
    "SN": "<tg-emoji emoji-id='5292087023698466689'>🇸🇳</tg-emoji>",
    "MR": "<tg-emoji emoji-id='5422465115360345921'>🇲🇷</tg-emoji>",
    "ML": "<tg-emoji emoji-id='5976768376196831695'>🇲🇱</tg-emoji>",
    "GN": "<tg-emoji emoji-id='5976350888195791241'>🇬🇳</tg-emoji>",
    "CI": "<tg-emoji emoji-id='5293991322003200135'>🇨🇮</tg-emoji>",
    "BF": "<tg-emoji emoji-id='5976557308619003946'>🇧🇫</tg-emoji>",
    "NE": "<tg-emoji emoji-id='5976647932428950438'>🇳🇪</tg-emoji>",
    "TG": "<tg-emoji emoji-id='5976576434108372678'>🇹🇬</tg-emoji>",
    "BJ": "<tg-emoji emoji-id='5293984969746566866'>🇧🇯</tg-emoji>",
    "MU": "<tg-emoji emoji-id='5976482670677333747'>🇲🇺</tg-emoji>",
    "LR": "<tg-emoji emoji-id='5976577718303595873'>🇱🇷</tg-emoji>",
    "SL": "<tg-emoji emoji-id='5976596925397342449'>🇸🇱</tg-emoji>",
    "GH": "<tg-emoji emoji-id='5294347396266873249'>🇬🇭</tg-emoji>",
    "NG": "<tg-emoji emoji-id='5294456308047563965'>🇳🇬</tg-emoji>",
    "TD": "<tg-emoji emoji-id='5979044524180117852'>🇹🇩</tg-emoji>",
    "CF": "<tg-emoji emoji-id='5976451437675156826'>🇨🇫</tg-emoji>",
    "CM": "<tg-emoji emoji-id='5976324706075154689'>🇨🇲</tg-emoji>",
    "CV": "<tg-emoji emoji-id='5976548697209575812'>🇨🇻</tg-emoji>",
    "ST": "<tg-emoji emoji-id='5976699343187482779'>🇸🇹</tg-emoji>",
    "GQ": "<tg-emoji emoji-id='5976814525620426462'>🇬🇶</tg-emoji>",
    "GA": "<tg-emoji emoji-id='5976396341834684925'>🇬🇦</tg-emoji>",
    "CG": "<tg-emoji emoji-id='5976332205088054604'>🇨🇬</tg-emoji>",
    "CD": "<tg-emoji emoji-id='5976337234494757335'>🇨🇩</tg-emoji>",
    "AO": "<tg-emoji emoji-id='5291917995260533077'>🇦🇴</tg-emoji>",
    "GW": "<tg-emoji emoji-id='5976526294660159661'>??🇼</tg-emoji>",
    "SC": "<tg-emoji emoji-id='5978929268732729465'>🇸🇨</tg-emoji>",
    "SD": "<tg-emoji emoji-id='5294177148058228060'>🇸🇩</tg-emoji>",
    "RW": "<tg-emoji emoji-id='5976558287871547862'>🇷🇼</tg-emoji>",
    "ET": "<tg-emoji emoji-id='5976492471792703601'>🇪🇹</tg-emoji>",
    "SO": "<tg-emoji emoji-id='5976732113787966649'>🇸🇴</tg-emoji>",
    "DJ": "<tg-emoji emoji-id='5976613946352736850'>🇩🇯</tg-emoji>",
    "KE": "<tg-emoji emoji-id='5292111852904416801'>🇰🇪</tg-emoji>",
    "TZ": "<tg-emoji emoji-id='5292146096678658977'>🇹🇿</tg-emoji>",
    "UG": "<tg-emoji emoji-id='5976539578994006362'>🇺🇬</tg-emoji>",
    "BI": "<tg-emoji emoji-id='5976742099586914503'>🇧🇮</tg-emoji>",
    "MZ": "<tg-emoji emoji-id='5294086708931874940'>🇲🇿</tg-emoji>",
    "ZM": "<tg-emoji emoji-id='5294100109229838880'>🇿🇲</tg-emoji>",
    "MG": "<tg-emoji emoji-id='5291991568050312348'>🇲🇬</tg-emoji>",
    "RE": "<tg-emoji emoji-id='5420322107068267129'>🇷🇪</tg-emoji>",
    "ZW": "<tg-emoji emoji-id='5294422158762592930'>🇿🇼</tg-emoji>",
    "NA": "<tg-emoji emoji-id='5976603874654426417'>🇳🇦</tg-emoji>",
    "MW": "<tg-emoji emoji-id='5341341330691863561'>🇲🇼</tg-emoji>",
    "LS": "<tg-emoji emoji-id='5976620972919232666'>🇱🇸</tg-emoji>",
    "BW": "<tg-emoji emoji-id='5976363541169445780'>🇧🇼</tg-emoji>",
    "SZ": "<tg-emoji emoji-id='5976741725924759442'>🇸🇿</tg-emoji>",
    "KM": "<tg-emoji emoji-id='5976698870741083962'>🇰🇲</tg-emoji>",
    "SH": "<tg-emoji emoji-id='5454076894997659542'>🇸🇭</tg-emoji>",
    "ER": "<tg-emoji emoji-id='5420548035232937623'>🇪🇷</tg-emoji>",
    "AW": "<tg-emoji emoji-id='5231044964212817289'>🇦🇼</tg-emoji>",
    "FO": "<tg-emoji emoji-id='5280985770188885026'>🇫🇴</tg-emoji>",
    "GL": "<tg-emoji emoji-id='5221969376193816323'>🇬🇱</tg-emoji>",
    "GI": "<tg-emoji emoji-id='5226496954623603888'>🇬🇮</tg-emoji>",
    "PT": "<tg-emoji emoji-id='5976327106961873123'>🇵🇹</tg-emoji>",
    "LU": "<tg-emoji emoji-id='5976285484433807436'>🇱🇺</tg-emoji>",
    "IE": "<tg-emoji emoji-id='5293991322003200135'>🇮🇪</tg-emoji>",
    "IS": "<tg-emoji emoji-id='5976698802021604508'>🇮🇸</tg-emoji>",
    "AL": "<tg-emoji emoji-id='5976498841229203219'>🇦🇱</tg-emoji>",
    "MT": "<tg-emoji emoji-id='5976479762984475758'>🇲🇹</tg-emoji>",
    "CY": "<tg-emoji emoji-id='5976803616403495510'>🇨🇾</tg-emoji>",
    "FI": "<tg-emoji emoji-id='5976510158468028132'>🇫🇮</tg-emoji>",
    "BG": "<tg-emoji emoji-id='5976616970009712457'>🇧🇬</tg-emoji>",
    "LT": "<tg-emoji emoji-id='5976837881652582376'>🇱🇹</tg-emoji>",
    "LV": "<tg-emoji emoji-id='5976740978600451694'>🇱🇻</tg-emoji>",
    "EE": "<tg-emoji emoji-id='5976277392715423938'>🇪🇪</tg-emoji>",
    "MD": "<tg-emoji emoji-id='5976792247625064355'>🇲🇩</tg-emoji>",
    "AM": "<tg-emoji emoji-id='5411455658186778270'>🇦🇲</tg-emoji>",
    "BY": "<tg-emoji emoji-id='5976363304946245889'>🇧🇾</tg-emoji>",
    "AD": "<tg-emoji emoji-id='5978725575613749734'>🇦🇩</tg-emoji>",
    "MC": "<tg-emoji emoji-id='5976425521842494767'>🇲🇨</tg-emoji>",
    "SM": "<tg-emoji emoji-id='5976790357839452073'>🇸🇲</tg-emoji>",
    "UA": "<tg-emoji emoji-id='5294263837678131580'>🇺🇦</tg-emoji>",
    "RS": "<tg-emoji emoji-id='5976463012612020480'>🇷🇸</tg-emoji>",
    "ME": "<tg-emoji emoji-id='5976333948844776590'>🇲🇪</tg-emoji>",
    "XK": "<tg-emoji emoji-id='5976633286590470030'>🇽🇰</tg-emoji>",
    "HR": "<tg-emoji emoji-id='5976744921380428432'>🇭🇷</tg-emoji>",
    "SI": "<tg-emoji emoji-id='5978926704637253502'>🇸🇮</tg-emoji>",
    "BA": "<tg-emoji emoji-id='5976670657100913091'>🇧🇦</tg-emoji>",
    "MK": "<tg-emoji emoji-id='5976441816948417573'>🇲🇰</tg-emoji>",
    "CZ": "<tg-emoji emoji-id='5976659369926859099'>🇨🇿</tg-emoji>",
    "SK": "<tg-emoji emoji-id='5976365662883290025'>🇸🇰</tg-emoji>",
    "LI": "<tg-emoji emoji-id='5976793342841725198'>🇱🇮</tg-emoji>",
    "FK": "<tg-emoji emoji-id='5454214681843481342'>🇫🇰</tg-emoji>",
    "BZ": "<tg-emoji emoji-id='5976828144961722583'>🇧🇿</tg-emoji>",
    "GT": "<tg-emoji emoji-id='5976766731224358097'>🇬🇹</tg-emoji>",
    "SV": "<tg-emoji emoji-id='5427301849831061043'>🇸🇻</tg-emoji>",
    "HN": "<tg-emoji emoji-id='5976504755399170515'>🇭🇳</tg-emoji>",
    "NI": "<tg-emoji emoji-id='5426842228200847679'>🇳🇮</tg-emoji>",
    "CR": "<tg-emoji emoji-id='5976659120818755766'>🇨🇷</tg-emoji>",
    "PA": "<tg-emoji emoji-id='5976690366705834196'>🇵🇦</tg-emoji>",
    "PM": "<tg-emoji emoji-id='5231258308123313128'>🇵🇲</tg-emoji>",
    "HT": "<tg-emoji emoji-id='5976439987292346381'>🇭🇹</tg-emoji>",
    "GP": "<tg-emoji emoji-id='5467664243081886165'>🇬🇵</tg-emoji>",
    "BO": "<tg-emoji emoji-id='5976750775420852685'>🇧🇴</tg-emoji>",
    "GY": "<tg-emoji emoji-id='5978986473402144429'>🇬🇾</tg-emoji>",
    "EC": "<tg-emoji emoji-id='5976442048876648469'>🇪🇨</tg-emoji>",
    "GF": "<tg-emoji emoji-id='5233523014313720667'>🇬🇫</tg-emoji>",
    "PY": "<tg-emoji emoji-id='5976609745874721028'>🇵🇾</tg-emoji>",
    "MQ": "<tg-emoji emoji-id='5976284878843418502'>🇲🇶</tg-emoji>",
    "SR": "<tg-emoji emoji-id='5976300113092417676'>🇸🇷</tg-emoji>",
    "UY": "<tg-emoji emoji-id='5976387133424803250'>🇺🇾</tg-emoji>",
    "CW": "<tg-emoji emoji-id='5233622988267472134'>🇨🇼</tg-emoji>",
    "TL": "<tg-emoji emoji-id='5291917995260533077'>🇹🇱</tg-emoji>",
    "AQ": "<tg-emoji emoji-id='5222477234601732139'>🇦🇶</tg-emoji>",
    "BN": "<tg-emoji emoji-id='5976686076033506746'>🇧🇳</tg-emoji>",
    "NR": "<tg-emoji emoji-id='5233464284930915439'>🇳🇷</tg-emoji>",
    "PG": "<tg-emoji emoji-id='5976504321607475018'>🇵🇬</tg-emoji>",
    "TO": "<tg-emoji emoji-id='5467490150877508877'>🇹🇴</tg-emoji>",
    "SB": "<tg-emoji emoji-id='5976631860661329134'>🇸🇧</tg-emoji>",
    "VU": "<tg-emoji emoji-id='5978614254356404774'>🇻🇺</tg-emoji>",
    "FJ": "<tg-emoji emoji-id='5978868701103920957'>🇫🇯</tg-emoji>",
    "PW": "<tg-emoji emoji-id='5976497857681693092'>🇵🇼</tg-emoji>",
    "WF": "<tg-emoji emoji-id='5231000034559934302'>🇼🇫</tg-emoji>",
    "CK": "<tg-emoji emoji-id='5454192094610473874'>🇨🇰</tg-emoji>",
    "NU": "<tg-emoji emoji-id='5454251094576218954'>🇳🇺</tg-emoji>",
    "WS": "<tg-emoji emoji-id='5976637886500444833'>🇼🇸</tg-emoji>",
    "KI": "<tg-emoji emoji-id='5976401719133739607'>🇰🇮</tg-emoji>",
    "NC": "<tg-emoji emoji-id='5233223766762338378'>🇳🇨</tg-emoji>",
    "TV": "<tg-emoji emoji-id='5454304115947487098'>🇹🇻</tg-emoji>",
    "PF": "<tg-emoji emoji-id='5467450310760874001'>🇵🇫</tg-emoji>",
    "TK": "<tg-emoji emoji-id='5231066898610798438'>🇹🇰</tg-emoji>",
    "FM": "<tg-emoji emoji-id='5976430375155538302'>🇫🇲</tg-emoji>",
    "MH": "<tg-emoji emoji-id='5976820856402222820'>🇲🇭</tg-emoji>",
    "KP": "<tg-emoji emoji-id='5341271404329317987'>🇰🇵</tg-emoji>",
    "HK": "<tg-emoji emoji-id='5222395857856374392'>🇭🇰</tg-emoji>",
    "MO": "<tg-emoji emoji-id='5420505321783179067'>🇲🇴</tg-emoji>",
    "KH": "<tg-emoji emoji-id='5976742700882335535'>🇰🇭</tg-emoji>",
    "LA": "<tg-emoji emoji-id='5976399640369568284'>🇱🇦</tg-emoji>",
    "BD": "<tg-emoji emoji-id='5291824687096027834'>🇧🇩</tg-emoji>",
    "TW": "<tg-emoji emoji-id='5222365101595568847'>🇹🇼</tg-emoji>",
    "MV": "<tg-emoji emoji-id='5976363386550622337'>🇲🇻</tg-emoji>",
    "LB": "<tg-emoji emoji-id='5294013428199869487'>🇱🇧</tg-emoji>",
    "JO": "<tg-emoji emoji-id='5291988613112814801'>🇯🇴</tg-emoji>",
    "SY": "<tg-emoji emoji-id='5294013428199869487'>🇸🇾</tg-emoji>",
    "IQ": "<tg-emoji emoji-id='5294325010897327367'>🇮🇶</tg-emoji>",
    "KW": "<tg-emoji emoji-id='5292066437920218075'>🇰🇼</tg-emoji>",
    "SA": "<tg-emoji emoji-id='5294163983983463099'>🇸🇦</tg-emoji>",
    "YE": "<tg-emoji emoji-id='5294058972033076492'>🇾🇪</tg-emoji>",
    "OM": "<tg-emoji emoji-id='5291813666209946812'>🇴🇲</tg-emoji>",
    "PS": "<tg-emoji emoji-id='5294289826525238172'>🇵🇸</tg-emoji>",
    "AE": "<tg-emoji emoji-id='5294314831824835370'>🇦🇪</tg-emoji>",
    "IL": "<tg-emoji emoji-id='5294069056616289553'>🇮🇱</tg-emoji>",
    "BH": "<tg-emoji emoji-id='5976668522502166844'>🇧??</tg-emoji>",
    "QA": "<tg-emoji emoji-id='5292166360334357676'>🇶🇦</tg-emoji>",
    "BT": "<tg-emoji emoji-id='5294121983498277263'>🇧🇹</tg-emoji>",
    "MN": "<tg-emoji emoji-id='5294316532631883496'>🇲🇳</tg-emoji>",
    "NP": "<tg-emoji emoji-id='5294458756178924088'>🇳🇵</tg-emoji>",
    "TJ": "<tg-emoji emoji-id='5294120269806328883'>🇹🇯</tg-emoji>",
    "TM": "<tg-emoji emoji-id='5294098958178603764'>🇹🇲</tg-emoji>",
    "AZ": "<tg-emoji emoji-id='5294323533428579078'>🇦🇿</tg-emoji>",
    "GE": "<tg-emoji emoji-id='5294349389131697267'>🇬🇪</tg-emoji>",
    "KG": "<tg-emoji emoji-id='5292091954320922577'>🇰🇬</tg-emoji>",
    "UZ": "<tg-emoji emoji-id='5294217645304864345'>🇺🇿</tg-emoji>",
    "KZ": "<tg-emoji emoji-id='5294227175837290463'>🇰🇿</tg-emoji>",
    "CA": "<tg-emoji emoji-id='5292290347450259214'>🇨🇦</tg-emoji>",
}

def get_flag(country_code):
    if not country_code: return "🌍"
    code = country_code.upper()
    if code in SPECIAL_FLAGS:
        return SPECIAL_FLAGS[code]
    return ''.join([chr(0x1F1E6 + ord(c) - ord('A')) for c in code])

def extract_tg_emoji_id(flag_str):
    import re as _re
    m = _re.search(r"emoji-id='(\d+)'", str(flag_str))
    return m.group(1) if m else None

def detect_country_from_number(number, user_id=None):
    try:
        s = str(number).strip()
        if not s.startswith('+'):
            s = '+' + s
        
       
        try:
            parsed = phonenumbers.parse(s)
        except phonenumbers.NumberParseException:
            
            parsed = phonenumbers.parse(s + "00000000")
            
        region = phonenumbers.region_code_for_number(parsed)
        if not region:
            return "Unknown", "🌍", "UN"
        
        if region == "MA":
            return "Morocco", "<tg-emoji emoji-id='5224530035695693965'>🇲🇦</tg-emoji>", "MA"
            
        if s.startswith('+1') or s.startswith('1'):
            return "Barbados", "<tg-emoji emoji-id='5294526187165471742'>🇧🇧</tg-emoji>", "BB"
            
        lang = get_user_language(user_id) if user_id else "ar"
        
       
        country_name = geocoder.description_for_number(parsed, lang)
        
       
        if not country_name or country_name == "Unknown":
            try:
                py_country = pycountry.countries.get(alpha_2=region)
                if py_country:
                    
                    country_name = py_country.name
            except:
                pass

       
        if not country_name or country_name == "Unknown":
            country_name = geocoder.description_for_number(parsed, "en")
            
        if not country_name or country_name == "Unknown":
            country_name = region

        flag = get_flag(region)
        return country_name, flag, region
    except Exception as e:
        print(f"Error detecting country: {e}")
        return "Unknown", "🌍", "UN"

def format_otp_message(number, sms_text, service_name="[TG]", otp_code=None, user_id=None):
    country_name, flag, region_code = detect_country_from_number(number, user_id)
    masked = mask_number(number)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    header = f"↠ {flag} #{region_code} {service_name} {masked}  ┨<tg-emoji emoji-id='5802950104834906444'>⚡</tg-emoji>"
    
    body = f"<blockquote>{sms_text}</blockquote>"
    time_footer = f"<blockquote>• <tg-emoji emoji-id='5413704112220949842'>⏰</tg-emoji> ~ {now_str}</blockquote>"
    
    return f"{header}\n{body}\n{time_footer}"


def detect_service(text, source_addr=None):
    if not text:
        return "<tg-emoji emoji-id='5443038326535759644'>🌎</tg-emoji>"
    t = text.lower()
    source_lower = source_addr.lower() if source_addr else ""
    
   
    if any(k in t for k in ["whatsapp", "واتساب", "واتس"]):
        return "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>"
    if any(k in t for k in ["telegram", "تيليجرام", "تلجرام"]):
        return "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>"
    if any(k in t for k in ["facebook", "فيسبوك", "meta"]):
        return "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>"
    if any(k in t for k in ["instagram", "انستقرام", "انستا"]):
        return "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>"
    if any(k in t for k in ["tiktok", "تيك توك", "تيكتوك"]):
        return "<tg-emoji emoji-id='5327982530702359565'>📱</tg-emoji>"
    if any(k in t for k in ["google", "جوجل", "gmail"]):
        return "<tg-emoji emoji-id='5359758030198031389'>📱</tg-emoji>"
    if any(k in t for k in ["imo", "ايمو"]):
        return "<tg-emoji emoji-id='5920204030570667999'>📱</tg-emoji>"
    if any(k in t for k in ["viber", "فايبر"]):
        return "VB"
    if any(k in t for k in ["snapchat", "سناب"]):
        return "<tg-emoji emoji-id='5330248916224983855'>📱</tg-emoji>"

    services = {
        "whatsapp": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>",
        "واتساب": "WS",
        "واتس": "WS",
        "facebook": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>",
        "فيسبوك": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>",
        "meta": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>",
        "instagram": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>",
        "انستقرام": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>",
        "انستا": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>",
        "telegram": "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>",
        "تيليجرام": "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>",
        "تلجرام": "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>",
        "twitter": "TW",
        "تويتر": "TW",
        "x.com": "TW",
        "snapchat": "<tg-emoji emoji-id='5330248916224983855'>📱</tg-emoji>",
        "سناب": "<tg-emoji emoji-id='5330248916224983855'>📱</tg-emoji>",
        "tiktok": "<tg-emoji emoji-id='5327982530702359565'>📱</tg-emoji>",
        "تيك توك": "<tg-emoji emoji-id='5327982530702359565'>📱</tg-emoji>",
        "google": "GG",
        "جوجل": "GG",
        "gmail": "GG",
        "linkedin": "LN",
        "لينكد": "LN",
        "discord": "DC",
        "ديسكورد": "DC",
        "uber": "UB",
        "bolt": "BT",
        "careem": "CR",
        "amazon": "AZ",
        "netflix": "<tg-emoji emoji-id='5318911503938634641'>📱</tg-emoji>",
        "spotify": "SP",
        "apple": "<tg-emoji emoji-id='5334955749409834455'>📱</tg-emoji>",
        "microsoft": "MS",
        "paypal": "<tg-emoji emoji-id='5364111181415996352'>📱</tg-emoji>",
        "binance": "BN",
        "coinbase": "CB",
    }

    for keyword, service in services.items():
        if keyword in t:
            return service
    
    for keyword, service in services.items():
        if keyword in source_lower:
            return service

    if source_addr and source_addr.strip():
        cleaned_source = source_addr.replace('#', '').strip()
        if cleaned_source:
            return cleaned_source.upper()
    return "<tg-emoji emoji-id='5443038326535759644'>🌎</tg-emoji>"

def get_country_flags_final(country_name):
    """جلب علم الدولة بناءً على اسمها بالاعتماد على SPECIAL_FLAGS"""
    if not country_name:
        return "🌍"
        
    # محاولة جلب العلم باستخدام pycountry للحصول على كود الدولة أولاً
    try:
        import pycountry
        # البحث بالاسم الإنجليزي
        country = pycountry.countries.get(name=country_name)
        if not country:
            # البحث بالاسم الشائع
            country = pycountry.countries.search_fuzzy(country_name)[0]
        
        if country:
            code = country.alpha_2
            if code in SPECIAL_FLAGS:
                return SPECIAL_FLAGS[code]
    except:
        pass

    # قائمة يدوية سريعة لبعض الأسماء العربية والإنجليزية الشائعة
    manual_flags = {
        "مصر": "<tg-emoji emoji-id='5293992082212409502'>🇪🇬</tg-emoji>", "Egypt": "<tg-emoji emoji-id='5293992082212409502'>🇪🇬</tg-emoji>",
        "السعودية": "<tg-emoji emoji-id='5294163983983463099'>🇸🇦</tg-emoji>", "Saudi Arabia": "<tg-emoji emoji-id='5294163983983463099'>🇸🇦</tg-emoji>",
        "ليبيا": "<tg-emoji emoji-id='5893101223564810175'>🇱🇾</tg-emoji>", "Libya": "<tg-emoji emoji-id='5893101223564810175'>🇱🇾</tg-emoji>",
        "الجزائر": "<tg-emoji emoji-id='5294048127240655242'>🇩🇿</tg-emoji>", "Algeria": "<tg-emoji emoji-id='5294048127240655242'>🇩🇿</tg-emoji>",
        "المغرب": "<tg-emoji emoji-id='5224530035695693965'>🇲🇦</tg-emoji>", "Morocco": "<tg-emoji emoji-id='5224530035695693965'>🇲🇦</tg-emoji>",
        "تونس": "<tg-emoji emoji-id='5294484680601521871'>🇹🇳</tg-emoji>", "Tunisia": "<tg-emoji emoji-id='5294484680601521871'>🇹🇳</tg-emoji>",
        "العراق": "<tg-emoji emoji-id='5294325010897327367'>🇮🇶</tg-emoji>", "Iraq": "<tg-emoji emoji-id='5294325010897327367'>🇮🇶</tg-emoji>",
        "الأردن": "<tg-emoji emoji-id='5291988613112814801'>🇯🇴</tg-emoji>", "Jordan": "<tg-emoji emoji-id='5291988613112814801'>🇯🇴</tg-emoji>",
        "فلسطين": "<tg-emoji emoji-id='5294289826525238172'>🇵🇸</tg-emoji>", "Palestine": "<tg-emoji emoji-id='5294289826525238172'>🇵🇸</tg-emoji>",
        "الإمارات": "<tg-emoji emoji-id='5294314831824835370'>🇦🇪</tg-emoji>", "UAE": "<tg-emoji emoji-id='5294314831824835370'>🇦🇪</tg-emoji>",
        "الكويت": "<tg-emoji emoji-id='5292066437920218075'>🇰🇼</tg-emoji>", "Kuwait": "<tg-emoji emoji-id='5292066437920218075'>🇰🇼</tg-emoji>",
        "قطر": "<tg-emoji emoji-id='5976313337254782006'>🇶🇦</tg-emoji>", "Qatar": "<tg-emoji emoji-id='5976313337254782006'>🇶🇦</tg-emoji>",
        "لبنان": "<tg-emoji emoji-id='5294013428199869487'>🇱🇧</tg-emoji>", "Lebanon": "<tg-emoji emoji-id='5294013428199869487'>🇱🇧</tg-emoji>",
        "سوريا": "<tg-emoji emoji-id='5294013428199869487'>🇸🇾</tg-emoji>", "Syria": "<tg-emoji emoji-id='5294013428199869487'>🇸🇾</tg-emoji>",
        "روسيا": "<tg-emoji emoji-id='5294335323113807278'>🇷🇺</tg-emoji>", "Russia": "<tg-emoji emoji-id='5294335323113807278'>🇷🇺</tg-emoji>",
        "Barbados": "<tg-emoji emoji-id='5294526187165471742'>🇧🇧</tg-emoji>",
        "هولندا": "<tg-emoji emoji-id='5291917797692042265'>🇳🇱</tg-emoji>", "Netherlands": "<tg-emoji emoji-id='5291917797692042265'>🇳🇱</tg-emoji>",
        "إندونيسيا": "<tg-emoji emoji-id='5294378161117614233'>🇮🇩</tg-emoji>", "Indonesia": "<tg-emoji emoji-id='5294378161117614233'>🇮🇩</tg-emoji>",
        "موزمبيق": "<tg-emoji emoji-id='5294086708931874940'>🇲🇿</tg-emoji>", "Mozambique": "<tg-emoji emoji-id='5294086708931874940'>🇲🇿</tg-emoji>",
        "مدغشقر": "<tg-emoji emoji-id='5291991568050312348'>🇲🇬</tg-emoji>", "Madagascar": "<tg-emoji emoji-id='5291991568050312348'>🇲🇬</tg-emoji>",
        "السودان": "<tg-emoji emoji-id='5294177148058228060'>🇸🇩</tg-emoji>", "Sudan": "<tg-emoji emoji-id='5294177148058228060'>🇸🇩</tg-emoji>",
    }
    
    for key, val in manual_flags.items():
        if key.lower() in country_name.lower():
            return val
            
    return "🌍"

def detect_country_code_from_file(file_path):
   
    try:
        prefixes = {}
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line: continue
            first_part = line.split()[0] if line.split() else line
            digits = ''.join(c for c in first_part if c.isdigit())
            
            if len(digits) >= 8:
               
                for i in range(1, 4):
                    prefix = digits[:i]
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        if not prefixes:
            return None
            
        
        sorted_prefixes = sorted(prefixes.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
        return sorted_prefixes[0][0] 
    except Exception as e:
        print(f"Error detecting country code: {e}")
        return None

def clean_and_filter_numbers(file_path, country_code):
    
    cleaned_numbers = []
    total_lines = 0
    rejected_lines = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            total_lines += 1

            parts = re.split(r'\s+', line)
            if not parts:
                rejected_lines += 1
                continue

            first_part = parts[0].strip()
            digits = re.sub(r'\D', '', first_part)

            if not digits:
                rejected_lines += 1
                continue

            if digits.startswith(country_code):
                cleaned_numbers.append(digits)
            else:
                rejected_lines += 1

        with open(file_path, 'w', encoding='utf-8') as f:
            for number in cleaned_numbers:
                f.write(number + '\n')

        return (len(cleaned_numbers), total_lines, rejected_lines)

    except Exception as e:
        print(f"❌ خطأ في تنظيف الملف: {e}")
        return (0, 0, 0)

def get_platform_buttons(country_name):
   
    markup = InlineKeyboardMarkup(row_width=2)
    buttons_found = False
    
    
    if country_name in COUNTRIES:
        info = COUNTRIES[country_name]
        platforms = info.get('platforms', [])
        platform_icons = {
            "Facebook": "Facebook",
            "WhatsApp": "WhatsApp",
            "Telegram": "Telegram",
            "Instagram": "Instagram",
            "Twitter": "Twitter/X",
            "TikTok": "TikTok",
            "Discord": "Discord",
            "Gmail": "Gmail"
        }
        for platform in platforms:
            display_name = platform_icons.get(platform, f"📱 {platform}")
            emoji_ids = {"Facebook": "5269427536453984598", "WhatsApp": "5271536803482981220", "Telegram": "5271801931814165886", "Instagram": "5269682734820777950", "TikTok": "5327982530702359565", "IMO": "5920204030570667999"}
            e_id = emoji_ids.get(platform)
            clean_name = display_name.split('</tg-emoji> ')[-1] if '</tg-emoji>' in display_name else display_name
            markup.add(InlineKeyboardButton(clean_name, callback_data=f"platform_{country_name}_{platform}", icon_custom_emoji_id=e_id, style="primary"))
            buttons_found = True
    else:
        
        platform_icons = {
            "Facebook": "Facebook",
            "WhatsApp": "WhatsApp",
            "Telegram": "Telegram",
            "Instagram": "Instagram",
            "Twitter": "Twitter/X",
            "TikTok": "TikTok",
            "Discord": "Discord",
            "Gmail": "Gmail"
        }
        for cid, info in COUNTRIES.items():
            if info.get("display_name") == country_name or cid == country_name:
                platforms = info.get('platforms', [])
                for platform in platforms:
                    display_name = platform_icons.get(platform, f"📱 {platform}")
                    emoji_ids = {"Facebook": "5269427536453984598", "WhatsApp": "5271536803482981220", "Telegram": "5271801931814165886", "Instagram": "5269682734820777950", "TikTok": "5327982530702359565", "IMO": "5920204030570667999"}
                    e_id = emoji_ids.get(platform)
                    markup.add(InlineKeyboardButton(display_name, callback_data=f"platform_{cid}_{platform}", icon_custom_emoji_id=e_id, style="primary"))
                    buttons_found = True

    if not buttons_found:
        return None
    
    markup.add(InlineKeyboardButton("𝗕𝗮𝗰𝗸", callback_data="choose_country"))
    return markup

def get_platforms_list(user_id=None):
    
    platform_stats = {}
    for country_id, info in COUNTRIES.items():
        platforms = info.get("platforms", [])
        count = info.get("numbers_count", 0)
        
        filename = info.get("file", "")
        if count == 0 and filename and os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    count = sum(1 for line in f if line.strip())
            except:
                pass
        
        for p in platforms:
            platform_stats[p] = platform_stats.get(p, 0) + count

    platform_icons = {
        "Facebook": "Facebook",
        "WhatsApp": "WhatsApp",
        "Telegram": "Telegram",
        "Instagram": "Instagram",
        "Twitter": "Twitter/X",
        "TikTok": "TikTok",
        "Discord": "Discord",
        "Gmail": "Gmail"
    }

    markup = InlineKeyboardMarkup(row_width=1)
    for platform, count in platform_stats.items():
        if count > 0:
            display_name = platform_icons.get(platform, f"📱 {platform}")
            emoji_ids = {"Facebook": "5269427536453984598", "WhatsApp": "5271536803482981220", "Telegram": "5271801931814165886", "Instagram": "5269682734820777950", "TikTok": "5327982530702359565", "IMO": "5920204030570667999"}
            e_id = emoji_ids.get(platform)
            # إزالة الإيموجي العادي المرفق مع IMO بحيث يظهر المخصص فقط أو النص الصافي
            clean_display_name = display_name.replace("📱 ", "").replace("📞 ", "")
            markup.add(InlineKeyboardButton(f"{clean_display_name}", callback_data=f"select_plt_{platform}", icon_custom_emoji_id=e_id, style="primary"))
    
    return markup

def get_platform_suffix(platform):
    suffixes = {
        "WhatsApp": ".WS",
        "Facebook": ".FB",
        "Instagram": ".IG",
        "Telegram": ".TG",
        "Discord": ".DC",
        "IMO": ".IM",
        "TikTok": ".TK",
        "Twitter": ".TW",
        "Gmail": ".GM"
    }
    if not platform: return ".WS"
    return suffixes.get(platform, ".WS")

def get_country_server_suffix(country_info):
    platforms = country_info.get("platforms", [])
    if not platforms:
        return ".WS"
    
    # إذا كانت الدولة تدعم منصة واحدة، نستخدم لاحقتها
    if len(platforms) == 1:
        return get_platform_suffix(platforms[0])
    
    # إذا كانت تدعم فيسبوك، نفضل .FB (حسب طلب المستخدم)
    if "Facebook" in platforms:
        return ".FB"
    # إذا كانت تدعم تليجرام
    if "Telegram" in platforms:
        return ".TG"
    # إذا كانت تدعم انستجرام
    if "Instagram" in platforms:
        return ".IG"
    # إذا كانت تدعم إيمو
    if "IMO" in platforms:
        return ".IM"
        
    return get_platform_suffix(platforms[0])

def get_countries_for_platform(platform, user_id=None):
    if user_id:
        user_data = USERS.get(str(user_id), {})
        user_data["platform"] = platform
        USERS[str(user_id)] = user_data
        save_users()
    
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=1)
    buttons = []
    
    display_name_counts = {}
    
    total_counts = {}
    for info in COUNTRIES.values():
        if platform in info.get("platforms", []):
            dname = info.get("display_name")
            total_counts[dname] = total_counts.get(dname, 0) + 1

    for cid, info in COUNTRIES.items():
        if platform in info.get("platforms", []):
            display_name = info.get("display_name", cid)
            if display_name == "UNKNOWN" and (str(info.get("code")) == "212" or cid == "MA"):
                display_name = "Morocco"
                
            flag = info.get("flag", "🌍")
            count = info.get("numbers_count", 0)
            code = info.get("code", "")
            
            filename = info.get("file", "")
            if count == 0 and filename and os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        count = sum(1 for line in f if line.strip())
                except:
                    pass

            display_name_counts[display_name] = display_name_counts.get(display_name, 0) + 1
            entry_number = display_name_counts[display_name]
            
            # صيغة المطلوب: Egypt - (عدد الارقام) - 0.0001 USD بدون لاحقة .WS
            label = f"{display_name}"
            if total_counts.get(display_name, 0) > 1:
                label += f" {entry_number}"
            
            label += f" - ({count}) - 0.0001 USD"

            emoji_id = extract_tg_emoji_id(flag)
            if not emoji_id and code:
                fresh_flag = get_flag_for_country_code(code)
                emoji_id = extract_tg_emoji_id(fresh_flag)
            try:
                emoji_id = extract_tg_emoji_id(flag)
                if not emoji_id and code:
                    fresh_flag = get_flag_for_country_code(code)
                    emoji_id = extract_tg_emoji_id(fresh_flag)
                
                if emoji_id:
                    btn = InlineKeyboardButton(label, callback_data=f"country_{cid}", icon_custom_emoji_id=emoji_id, style="primary")
                else:
                    btn = InlineKeyboardButton(f"{flag} {label}", callback_data=f"country_{cid}")
            except Exception:
                btn = InlineKeyboardButton(f"{flag} {label}", callback_data=f"country_{cid}")
            markup.add(btn)
    
    # إضافة زر الرجوع للسيرفرات
    markup.add(InlineKeyboardButton("Go Back", callback_data="back_to_main", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    return markup

def get_countries_list(user_id=None):
    
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    found = False
    
    
    display_name_counts = {}
    total_counts = {}
    for info in COUNTRIES.values():
        dname = info.get("display_name")
        total_counts[dname] = total_counts.get(dname, 0) + 1

    user_data = USERS.get(str(user_id), {})
    # platform = user_data.get("platform", "WhatsApp")
    # suffix = get_platform_suffix(platform)

    for cid, info in COUNTRIES.items():
        display_name = info.get("display_name", cid)
        if display_name == "UNKNOWN" and (str(info.get("code")) == "212" or cid == "MA"):
            display_name = "Morocco"
            
        flag = info.get("flag", "🌍")
        code = info.get("code", "??")
        count = info.get("numbers_count", 0)
        
        display_name_counts[display_name] = display_name_counts.get(display_name, 0) + 1
        entry_number = display_name_counts[display_name]
        
        # استخدام اللاحقة بناءً على المنصات المحددة لهذه الدولة
        country_suffix = get_country_server_suffix(info)
        label = f"{display_name}{country_suffix}"

        emoji_id = extract_tg_emoji_id(flag)
        if not emoji_id and code and str(code) != "??":
            fresh_flag = get_flag_for_country_code(code)
            emoji_id = extract_tg_emoji_id(fresh_flag)
        try:
            emoji_id = extract_tg_emoji_id(flag)
            if not emoji_id and code and str(code) != "??":
                fresh_flag = get_flag_for_country_code(code)
                emoji_id = extract_tg_emoji_id(fresh_flag)
            
            if emoji_id:
                btn = InlineKeyboardButton(label, callback_data=f"country_{cid}", icon_custom_emoji_id=emoji_id, style="primary")
            else:
                btn = InlineKeyboardButton(f"{flag} {label}", callback_data=f"country_{cid}")
        except Exception:
            btn = InlineKeyboardButton(f"{flag} {label}", callback_data=f"country_{cid}")
        markup.add(btn)
        found = True
    
    if found:
        # إضافة زر الرجوع للسيرفرات
        markup.add(InlineKeyboardButton("Go Back", callback_data="back_to_main", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    return markup if found else None

def get_country_buttons(user_id=None):
    return get_platforms_list(user_id)

def get_random_numbers(country_name, count=4):
    if country_name not in COUNTRIES:
        return []

    filename = COUNTRIES[country_name]["file"]

    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as f:
        numbers = list(set([line.strip() for line in f if line.strip()]))

    if not numbers:
        return []

    if len(numbers) < count:
        return numbers
    
    return random.sample(numbers, count)

def get_random_number(country_name):
    nums = get_random_numbers(country_name, 1)
    return nums[0] if nums else None

def create_message_buttons(user_id=None):
    user_id = user_id or telebot.types.User(0, False, "Dummy").id
    lang = get_user_language(user_id)
    links = load_button_links()

    markup = InlineKeyboardMarkup(row_width=1)

    change_number_text = " تغيير الرقم" if lang == "ar" else " Change Number"
    change_country_text = " تغيير الدولة" if lang == "ar" else " Change Country"
    group_link_text = " جروب البوت" if lang == "ar" else " Group Link"
    back_text = " القائمة الرئيسية" if lang == "ar" else " Back to Main"

    markup.add(InlineKeyboardButton(change_number_text, callback_data="change_number", style="success",    icon_custom_emoji_id="5465368548702446780")),
    markup.add(InlineKeyboardButton(change_country_text, callback_data="choose_country", style="primary",    icon_custom_emoji_id="5454074580010295588")),
    markup.add(InlineKeyboardButton(group_link_text, url=links.get("group_link", "https://t.me/+EAViSkQrDzcxMjA0"), style="primary",    icon_custom_emoji_id="5454386656628991407")),
    markup.add(InlineKeyboardButton(back_text, callback_data="back_to_main",    icon_custom_emoji_id="5258236805890710909"))

    return markup

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton

def create_group_otp_keyboard(otp_code=None, button_style="success"):
    otp_buttons = load_otp_buttons()  # افترض إن دي وظيفة بترجع قائمة أزرار
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    # ────────────── إعداد الإيموجي ──────────────
    OTP_EMOJI_ID = "5397731992135545615"       # إيموجي لزر OTP
    DEFAULT_EMOJI_LEFT = "5314391089514291948" # زر أول في الصف
    DEFAULT_EMOJI_RIGHT = "5974337549261347177"# زر ثاني في الصف
    
    # ────────────── زر الـ OTP ──────────────
    if otp_code and otp_code != "N/A":
        try:
            markup.add(
        InlineKeyboardButton(
        text=f" {otp_code}",
        copy_text=CopyTextButton(text=str(otp_code)),
        icon_custom_emoji_id=OTP_EMOJI_ID,
        style=button_style
                )
            )
        except Exception as e:
            print(f"خطأ في custom emoji لزر OTP: {e}")
            markup.add(
        InlineKeyboardButton(
        text=f"🔑 {otp_code}",
        callback_data=f"copy_{otp_code}",
        style=button_style
                )
            )
    
    # ────────────── الأزرار التانية (otp_buttons) ──────────────
    if otp_buttons:
        row_buttons = []
        button_index = 0
        
        for btn in otp_buttons:
            emoji_id = btn.get("emoji_id")
            
            if not emoji_id:
                # وزّع الافتراضيين حسب الترتيب
                emoji_id = DEFAULT_EMOJI_LEFT if button_index % 2 == 0 else DEFAULT_EMOJI_RIGHT
            
            try:
                # تلوين الأزرار: زر أول أزرق، زر ثاني أخضر
                btn_style = "primary" if button_index % 2 == 0 else "primary"
                
                button = InlineKeyboardButton(
                    text=f" {btn['name']}",
                    url=btn["url"],
                    icon_custom_emoji_id=emoji_id,
                    style=btn_style
                )
                row_buttons.append(button)
            except Exception as e:
                print(f"خطأ في custom emoji لزر {btn['name']}: {e}")
                row_buttons.append(
                    InlineKeyboardButton(
                        text=btn["name"],
                        url=btn["url"]
                    )
                )
            
            button_index += 1
        
        # ترتيب كل صف 2 أزرار
        for i in range(0, len(row_buttons), 2):
            chunk = row_buttons[i:i+2]
            markup.add(*chunk)
    
    # ────────────── الزر الرابع (سطر لوحده) ──────────────
    return markup if (otp_code or otp_buttons) else None


def create_private_otp_keyboard(otp_code, button_style="primary"):
    """كيبورد رسالة الخاص: زر OTP فقط، بدون Bot Link أو Channel."""
    if not otp_code or otp_code == "N/A":
        return None

    markup = InlineKeyboardMarkup(row_width=1)
    OTP_EMOJI_ID = "5397731992135545615"

    try:
        markup.add(
            InlineKeyboardButton(
                text=f" {otp_code}",
                copy_text=CopyTextButton(text=str(otp_code)),
                icon_custom_emoji_id=OTP_EMOJI_ID,
                style=button_style
            )
        )
    except Exception as e:
        print(f"خطأ في زر OTP الخاص: {e}")
        markup.add(
            InlineKeyboardButton(
                text=f"🔑 {otp_code}",
                callback_data=f"copy_{otp_code}",
                style=button_style
            )
        )

    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def handle_copy_callback(call):
    otp = call.data.split("_", 1)[1]
    
    bot.answer_callback_query(call.id, f"{otp}", show_alert=True)

def create_otp_message_keyboard(otp_code):
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    
    for btn in OTP_BUTTONS:
        markup.add(InlineKeyboardButton(btn["name"], url=btn["url"]))
    
    
    markup.add(InlineKeyboardButton("📋 Copy OTP", callback_data=f"copy_otp_{otp_code}"))
    
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_otp_"))
def copy_otp_callback(call):
    otp_code = call.data.replace("copy_otp_", "")
    bot.answer_callback_query(call.id, f"✅ Done", show_alert=False)
    bot.send_message(call.message.chat.id, f"<code>{otp_code}</code>", parse_mode="HTML")

def auto_delete_message(chat_id, message_id, delay=60):
    def delete():
        time.sleep(delay)
        try: bot.delete_message(chat_id, message_id)
        except: pass
    threading.Thread(target=delete, daemon=True).start()

def safe_send_message(chat_id, text, **kwargs):
    msg = bot.send_message(chat_id, text, **kwargs)
    if isinstance(chat_id, (int, str)) and (int(chat_id) < 0 or str(chat_id).startswith("-100")):
        auto_delete_message(int(chat_id), msg.message_id)
    return msg


original_send = bot.send_message
def hooked_send(chat_id, *args, **kwargs):
    msg = original_send(chat_id, *args, **kwargs)
    if isinstance(chat_id, (int, str)) and (int(chat_id) < 0 or str(chat_id).startswith("-100")):
        auto_delete_message(int(chat_id), msg.message_id)
    return msg
bot.send_message = hooked_send

def format_otp_message(country_name, country_flag, service_detected, number, otp, message_text, server_key="GROUP", is_group=False, show_full_number=True, user_id=None):
    
    use_shorthand = is_group or (OTP_GROUP and str(user_id) == str(OTP_GROUP))
    
    service_upper = str(service_detected).upper()
    shorthand = service_upper
    
    if use_shorthand:
        SHORTHANDS = {
            "WHATSAPP": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>",
            "TELEGRAM": "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>",
            "FACEBOOK": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>",
            "INSTAGRAM": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>",
            "TIKTOK": "<tg-emoji emoji-id='5327982530702359565'>TikTok</tg-emoji>",
            "TWITTER": "TW",
            "GOOGLE": "GG",
            "MICROSOFT": "MS",
            "NETFLIX": "<tg-emoji emoji-id='5318911503938634641'>📱</tg-emoji>",
            "STEAM": "ST",
            "SNAPCHAT": "<tg-emoji emoji-id='5330248916224983855'>📱</tg-emoji>",
            "VIBER": "VB",
            "IMO": "<tg-emoji emoji-id='5920204030570667999'>IMO</tg-emoji>",
            "WECHAT": "WC",
            "LINE": "LN",
            "DISCORD": "DC",
            "PAYPAL": "PP",
            "AMAZON": "AZ",
            "EBAY": "EB",
            "APPLE": "<tg-emoji emoji-id='5334955749409834455'>📱</tg-emoji>"
        }

        
        found = False
        for key, val in SHORTHANDS.items():
            if key in service_upper:
                shorthand = val
                found = True
                break
                
        if not found:
        
            shorthand = service_upper[:2] if len(service_upper) > 2 else service_upper
            
    service_name = f"[{shorthand}]"
    formatted = format_otp_message_v2(number, message_text, service_name, otp)
    
    if OTP_GROUP:
        try:
            
            if not use_shorthand:
               
                group_shorthand = service_upper
                SHORTHANDS = {"WHATSAPP": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>", "TELEGRAM": "<tg-emoji emoji-id='5471949924658588235'>👉</tg-emoji>", "FACEBOOK": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>", "INSTAGRAM": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>", "TIKTOK": "<tg-emoji emoji-id='5327982530702359565'>TikTok</tg-emoji>", "TWITTER": "TW"}
                for key, val in SHORTHANDS.items():
                    if key in service_upper:
                        group_shorthand = val
                        break
                if group_shorthand == service_upper: 
                    group_shorthand = service_upper[:2]
                
                group_service_name = f"[{group_shorthand}]"
                group_formatted = format_otp_message_v2(number, message_text, group_service_name, otp, is_group=True)
            else:
                group_formatted = formatted
            
            msg = original_send(OTP_GROUP, group_formatted, parse_mode="HTML", reply_markup=create_group_otp_keyboard(otp))
            auto_delete_message(OTP_GROUP, msg.message_id)
        except: pass
    return formatted

def send_fake_otp_loop():
    while True:
        try:
            if OTP_GROUP:
                global collected_codes
                if not collected_codes:
                    load_collected_codes()
                
                valid_sites = ["Fly sms", "IMS", "Hadi_SMS"]
                valid_services = ["FACEBOOK", "WHATSAPP", "TIKTOK"]
                
                filtered_codes = []
                for c in collected_codes:
                    site_match = any(s.lower() in str(c.get("site", "")).lower() for s in valid_sites)
                    service_match = any(s in str(c.get("service", "")).upper() for s in valid_services)
                    if site_match and service_match:
                        filtered_codes.append(c)
                
                if filtered_codes:
                    chosen = __import__("random").choice(filtered_codes)
                    number = chosen["number"]
                    msg_text = chosen["sms"]
                    otp = chosen["otp"]
                    service_name = chosen["service"]
                    
                    service_icons = {
                        "WHATSAPP": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>",
                        "FACEBOOK": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>",
                        "TIKTOK": "<tg-emoji emoji-id='5327982530702359565'>TikTok</tg-emoji>"
                    }
                    
                    shorthand = service_name
                    for k, v in service_icons.items():
                        if k in service_name.upper():
                            shorthand = v
                            break
                    
                    display_service = f"[{shorthand}]"
                    formatted = format_otp_message_v2(number, msg_text, display_service, otp, is_group=True)
                    
                    msg = bot.send_message(OTP_GROUP, formatted, parse_mode="HTML", reply_markup=create_group_otp_keyboard(otp))
                    auto_delete_message(OTP_GROUP, msg.message_id, delay=60)
        except Exception as e:
            print(f"Error in fake OTP loop: {e}")
        
        __import__("time").sleep(30)

# بدء خيط الأكواد العشوائية
threading.Thread(target=send_fake_otp_loop, daemon=True).start()

def detect_sms_language(text):
    try:
        text = str(text).strip()

        if not text:
            return "UNKNOWN"

        # Arabic
        if re.search(r'[\u0600-\u06FF]', text):
            return "Arabic"

        # Persian (فارسی)
        elif re.search(r'[\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
            return "Persian"

        # Russian
        elif re.search(r'[\u0400-\u04FF]', text):
            return "Russian"

        # Spanish
        elif re.search(r'[ñáéíóúü¿¡]', text.lower()):
            return "Spanish"

        # Indonesian
        elif re.search(
            r'\b(kode|verifikasi|otp|anda|untuk|dengan|nomor|masuk|login|akun)\b',
            text.lower()
        ):
            return "Indonesian"

        # English
        elif re.search(r'[a-zA-Z]', text):
            return "English"

        return "UNKNOWN"

    except Exception:
        return "UNKNOWN"


def format_otp_message_v2(number, sms_text, service_name="[TG]", otp_code=None, is_group=False):
    country_name, flag, region_code = detect_country_from_number(number)
    masked = mask_number(number)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    display_service = service_name
    if is_group:
        service_clean = str(service_name).replace("[", "").replace("]", "").upper()
        SHORTHANDS = {
            "WHATSAPP": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>", "TELEGRAM": "TG", "FACEBOOK": "<tg-emoji emoji-id='5323261730283863478'>📱</tg-emoji>", "INSTAGRAM": "<tg-emoji emoji-id='5319160079465857105'>📱</tg-emoji>", 
            "TIKTOK": "<tg-emoji emoji-id='5327982530702359565'>TikTok</tg-emoji>", "TWITTER": "TW", "GOOGLE": "GG", "MICROSOFT": "MS"
        }
        found_sh = service_clean
        for k, v in SHORTHANDS.items():
            if k in service_clean:
                found_sh = v
                break
        if found_sh == service_clean and len(found_sh) > 3:
            found_sh = found_sh[:2]
        display_service = f"[{found_sh}]"
    
    otp_display = ""
    if otp_code:
        otp_display = "" 

    language_tag = detect_sms_language(sms_text)
    line_content =f"<b> {flag} {region_code} | {service_name} +{masked} | <tg-emoji emoji-id='5388632425314140043'>◾</tg-emoji> {language_tag}</b>"

    top_bottom_line = "" 

    
    header = f"{top_bottom_line}{line_content}{top_bottom_line}"
    
    
    return f"{header}\n{otp_display}"


def format_otp_message_private(number, sms_text, service_name='[TG]', otp_code=None, user_id=None):
    country_name, flag, region_code = detect_country_from_number(number)
    user_balance = 0.0
    reward = 0.0
    if user_id:
        user_key = str(user_id)
        referrals = load_referrals()
        ref_settings = load_referral_settings()
        reward = ref_settings.get('code_bonus', 0.0001)
        if user_key in referrals:
            user_balance = referrals[user_key].get('balance', 0.0)
    service_upper = str(service_name).upper()
    platform_icons = {
        'WHATSAPP': "<tg-emoji emoji-id='5381990043642502553'>📱</tg-emoji>",
        'FACEBOOK': "<tg-emoji emoji-id='5382322671679708881'>📱</tg-emoji>",
        'PAYPAL': "<tg-emoji emoji-id='5364111181415996352'>📱</tg-emoji>",
        'ALIEXPRESS': "<tg-emoji emoji-id='5390966190283694453'>📱</tg-emoji>",
        'ALIEPRESS': "<tg-emoji emoji-id='5390966190283694453'>📱</tg-emoji>",
        'TELEGRAM': "<tg-emoji emoji-id='5381879959335738545'>📱</tg-emoji>",
        'TIKTOK': "<tg-emoji emoji-id='5390966190283694453'>📱</tg-emoji>",
        'GOOGLE': "<tg-emoji emoji-id='5359758030198031389'>📱</tg-emoji>"
    }
    DEFAULT_ICON = "<tg-emoji emoji-id='5443038326535759644'>📱</tg-emoji>"
    srv_icon = platform_icons.get(service_upper, DEFAULT_ICON)
    parts = [
        srv_icon + ' <b>' + str(service_name).title() + '</b>',
        '--------------------',
        flag + ' <code>' + str(number) + '</code>',
        "<tg-emoji emoji-id='5460978422111021593'>💵</tg-emoji> +" + f"{reward:.4f}" + " added"
    ]
    line_content = '\n'.join(parts)
    return line_content
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id

    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return

    # التعديل: إظهار رسالة الاشتراك الإجباري مباشرة عند الضغط على start
    if not check_subscription(user_id):
        bot.send_message(
            msg.chat.id,
            get_all_channels_message(user_id),
            parse_mode="HTML",
            reply_markup=get_all_channels_keyboard(user_id)
        )
        return

    first_name = msg.from_user.first_name

    welcome_text = f"""<tg-emoji emoji-id='5314391089514291948'>⚡</tg-emoji> Welcome {first_name} ! <tg-emoji emoji-id='5316892517122187402'>❔</tg-emoji>

<tg-emoji emoji-id='4990298741463319592'>🔑</tg-emoji> Premium OTP Stock Bot
<tg-emoji emoji-id='4990298741463319592'>👋</tg-emoji> Fast & Reliable Service

<tg-emoji emoji-id='5406745015365943482'>🦦</tg-emoji> Please select an option below:"""

    bot.send_message(
        msg.chat.id,
        welcome_text,
        reply_markup=get_main_reply_keyboard(user_id),
        parse_mode="HTML"
    )

    return
@bot.message_handler(commands=["getnumber"])
def getnumber_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    if not check_subscription(user_id):
        unjoined_channel = get_first_unjoined_channel(user_id)
        if unjoined_channel:
            bot.send_message(
                msg.chat.id,
                get_subscription_message_for_channel(unjoined_channel, user_id),
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel, user_id)
            )
        return
    
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    
    markup = get_country_buttons(user_id)
    if markup:
        title = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        bot.send_message(msg.chat.id, title, parse_mode="HTML", reply_markup=markup)

# @bot.message_handler(commands=["account"])
def account_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    if not check_subscription(user_id):
        unjoined_channel = get_first_unjoined_channel(user_id)
        if unjoined_channel:
            bot.send_message(
                msg.chat.id,
                get_subscription_message_for_channel(unjoined_channel, user_id),
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel, user_id)
            )
        return
    
    user_data = USERS.get(str(user_id), {})
    activations = user_data.get("activations", 0)
    join_date = user_data.get("join_date", datetime.now().strftime('%Y-%m-%d'))
    lang = get_user_language(user_id)
    
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    total_earned = referral_data.get("total_earned", 0.0)
    referrals_count = len(referral_data.get("referrals", []))
    active_referrals = referral_data.get("active_referrals", 0)
    
    selected_country = user_data.get("selected_country")
    selected_number = user_data.get("selected_number")
    
    if selected_number and selected_country:
        number_status = f"✅ رقم نشط لـ {selected_country}" if lang == "ar" else f"✅ Active number for {selected_country}"
    else:
        number_status = "❌ لا يوجد رقم حالياً" if lang == "ar" else "❌ No number currently"
    
    bot_info = bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    if lang == "ar":
        account_text = (
            f"👤 <b>معلومات حسابك:</b>\n\n"
            f"🆔 <b>معرفك:</b> <code>{user_id}</code>\n"
            f"📅 <b>تاريخ الانضمام:</b> {join_date}\n"
            f"📊 <b>الأكواد المستلمة:</b> {activations}\n"
            f"🌐 <b>اللغة:</b> العربية\n\n"
            f"💰 <b>معلومات الأرباح:</b>\n"
            f"├ 💵 الرصيد الحالي: <b>${format_decimal(balance)}</b>\n"
            f"├ 📈 إجمالي الأرباح: <b>${format_decimal(total_earned)}</b>\n"
            f"├ 👥 عدد الإحالات: <b>{referrals_count}</b>\n"
            f"└ ✅ إحالات نشطة: <b>{active_referrals}</b>\n\n"
            f"🔗 <b>رابط الإحالة:</b>\n<code>{referral_link}</code>\n\n"
            f"💡 <b>حالة رقمك:</b>\n{number_status}"
        )
    else:
        account_text = (
            f"👤 <b>Your Account Info:</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📅 <b>Join Date:</b> {join_date}\n"
            f"📊 <b>Codes Received:</b> {activations}\n"
            f"🌐 <b>Language:</b> English\n\n"
            f"💰 <b>Earnings Info:</b>\n"
            f"├ 💵 Current Balance: <b>${format_decimal(balance)}</b>\n"
            f"├ 📈 Total Earned: <b>${format_decimal(total_earned)}</b>\n"
            f"├ 👥 Total Referrals: <b>{referrals_count}</b>\n"
            f"└ ✅ Active Referrals: <b>{active_referrals}</b>\n\n"
            f"🔗 <b>Referral Link:</b>\n<code>{referral_link}</code>\n\n"
            f"💡 <b>Number Status:</b>\n{number_status}"
        )
    
    markup = InlineKeyboardMarkup(row_width=1)
    if balance >= load_referral_settings().get("min_withdrawal", 5.0):
        withdraw_text = "💰 سحب الرصيد" if lang == "ar" else "💰 Withdraw"
        markup.add(InlineKeyboardButton(withdraw_text, callback_data="withdraw_balance"))
    
    back_text = " رجوع" if lang == "ar" else " Back"
    markup.add(InlineKeyboardButton(back_text, callback_data="back_to_main",    icon_custom_emoji_id="5258236805890710909"))
    
    bot.send_message(msg.chat.id, account_text, parse_mode="HTML", reply_markup=markup)

# @bot.message_handler(commands=["help"])
def help_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    referral_bonus = settings.get("referral_bonus", 0.50)
    codes_required = settings.get("codes_required_for_referral", 3)
    min_withdrawal = settings.get("min_withdrawal", 5.0)
    
    if lang == 'ar':
        instructions_text = f"""📖 <b>دليل استخدام البوت</b>

━━━━━━ <b>📱 استلام الأكواد</b> ━━━━━━

1️⃣ <b>اختيار الدولة:</b>
   • اضغط على "Get Number"
   • اختر الدولة التي تريدها

2️⃣ <b>اختيار الرقم:</b>
   • ستظهر لك الأرقام المتاحة
   • اختر الرقم المناسب

3️⃣ <b>استلام الكود:</b>
   • استخدم الرقم للتسجيل في أي موقع/تطبيق
   • سيصلك الكود تلقائياً هنا في البوت

━━━━━━ <b>💰 نظام الأرباح</b> ━━━━━━

💎 <b>بونص الكود:</b>
   • تحصل على <b>${format_decimal(code_bonus)}</b> عن كل كود تستلمه

👥 <b>بونص الإحالة:</b>
   • شارك رابط الإحالة مع أصدقائك
   • عندما يستلم صديقك <b>{codes_required} أكواد</b>
   • تحصل على <b>${format_decimal(referral_bonus)}</b> مباشرة!

━━━━━━ <b>💵 السحب</b> ━━━━━━

💰 <b>الحد الأدنى:</b> ${format_decimal(min_withdrawal)}
📝 <b>طرق السحب:</b>
   • فودافون كاش
   • USDT (TRC20/BEP20)
   • Binance ID

━━━━━━ شكراً لثقتك ━━━━━━

🆘 للمساعدة تواصل مع المطور"""
    else:
        instructions_text = f"""📖 <b>Bot Guide</b>

━━━━━━ <b>📱 Receiving Codes</b> ━━━━━━

1️⃣ <b>Choose Country:</b>
   • Click on "Get Number"
   • Select your desired country

2️⃣ <b>Choose Number:</b>
   • Available numbers will appear
   • Select the number you want

3️⃣ <b>Receive Code:</b>
   • Use the number to register on any site/app
   • The code will arrive automatically here in the bot

━━━━━━ <b>💰 Earning System</b> ━━━━━━

💎 <b>Code Bonus:</b>
   • Earn <b>${format_decimal(code_bonus)}</b> for each code you receive

👥 <b>Referral Bonus:</b>
   • Share your referral link with friends
   • When your friend receives <b>{codes_required} codes</b>
   • You get <b>${format_decimal(referral_bonus)}</b> instantly!

━━━━━━ <b>💵 Withdrawal</b> ━━━━━━

💰 <b>Minimum:</b> ${format_decimal(min_withdrawal)}
📝 <b>Withdrawal Methods:</b>
   • Vodafone Cash
   • USDT (TRC20/BEP20)
   • Binance ID

━━━━━━ Thanks for your trust ━━━━━━

🆘 For help, contact the developer"""
    
    markup = InlineKeyboardMarkup(row_width=1)
    developer_btn_text = "🆘 Contact Developer" if lang == "en" else "🆘 تواصل مع المطور"
    markup.add(InlineKeyboardButton(developer_btn_text, url="https://t.me/S_i_V6")),
    markup.add(InlineKeyboardButton(t(user_id, "back"), callback_data="back_to_main_user"))
    
    bot.send_message(msg.chat.id, instructions_text, parse_mode="HTML", reply_markup=markup)

# @bot.message_handler(commands=["withdraw"])
def withdraw_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    if not check_subscription(user_id):
        unjoined_channel = get_first_unjoined_channel(user_id)
        if unjoined_channel:
            bot.send_message(
                msg.chat.id,
                get_subscription_message_for_channel(unjoined_channel, user_id),
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel, user_id)
            )
        return
    
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    settings = load_referral_settings()
    min_withdrawal = settings.get("min_withdrawal", 10.0)
    
    msg_text = (
        "═══《 <tg-emoji emoji-id='5332600543963522398'>▪️</tg-emoji> WITHDRAW 》═══\n\n"
        "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> Insufficient balance!\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your balance: {balance:.3f} USD\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Minimum required: {min_withdrawal} USD\n\n"
        "Earn more by referring friends!"
    )
    
    bot.send_message(msg.chat.id, msg_text, parse_mode="HTML")

# @bot.message_handler(commands=["hom"])
def hom_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    text = t(user_id, "welcome")
    if not text: text = "🌐 <b>مرحباً بك!</b>"
    bot.send_message(
        msg.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=get_main_menu_lang(user_id)
    )

# تم حذف أمر /language بناءً على طلب المستخدم
# @bot.message_handler(commands=["language"])
# def language_command(msg):
#     user_id = msg.from_user.id
#     
#     if is_banned(user_id):
#         bot.reply_to(msg, t(user_id, "banned"))
#         return
#     
#     if msg.chat.type != "private":
#         return
#     
#     markup = InlineKeyboardMarkup(row_width=2)
#     markup.add(
#         InlineKeyboardButton(" العربية", callback_data="set_lang_ar", style="primary",    icon_custom_emoji_id="5294163983983463099"),
#         InlineKeyboardButton(" English", callback_data="set_lang_en", style="primary",    icon_custom_emoji_id="5293993521026453119")
#     )
#     
#     bot.send_message(
#         msg.chat.id,
#         "<tg-emoji emoji-id='5224450179368767019'>🌎</tg-emoji> <b>Choose Language / اختر اللغة</b>",
#         parse_mode="HTML",
#         reply_markup=markup
#     )

# @bot.message_handler(commands=["bonus"])
def bonus_command(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return
    
    if msg.chat.type != "private":
        return
    
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    referral_bonus = settings.get("referral_bonus", 0.50)
    codes_required = settings.get("codes_required_for_referral", 3)
    min_withdrawal = settings.get("min_withdrawal", 5.0)
    
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    total_earned = referral_data.get("total_earned", 0.0)
    referrals_count = len(referral_data.get("referrals", []))
    active_referrals = referral_data.get("active_referrals", 0)
    
    bot_info = bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    if lang == "ar":
        bonus_text = f"""💰 <b>نظام البونص</b>

━━━━━━ <b>📊 إحصائياتك</b> ━━━━━━

💵 الرصيد الحالي: <b>${format_decimal(balance)}</b>
📈 إجمالي الأرباح: <b>${format_decimal(total_earned)}</b>
👥 عدد الإحالات: <b>{referrals_count}</b>
✅ إحالات نشطة: <b>{active_referrals}</b>

━━━━━━ <b>🎁 معدلات البونص</b> ━━━━━━

💎 بونص الكود: <b>${format_decimal(code_bonus)}</b> لكل كود
👥 بونص الإحالة: <b>${format_decimal(referral_bonus)}</b> عند {codes_required} أكواد
💰 الحد الأدنى للسحب: <b>${format_decimal(min_withdrawal)}</b>

━━━━━━ <b>🔗 رابط الإحالة</b> ━━━━━━

<code>{referral_link}</code>

شارك الرابط مع أصدقائك للحصول على بونص!"""
    else:
        bonus_text = f"""💰 <b>Bonus System</b>

━━━━━━ <b>📊 Your Stats</b> ━━━━━━

💵 Current Balance: <b>${format_decimal(balance)}</b>
📈 Total Earned: <b>${format_decimal(total_earned)}</b>
👥 Total Referrals: <b>{referrals_count}</b>
✅ Active Referrals: <b>{active_referrals}</b>

━━━━━━ <b>🎁 Bonus Rates</b> ━━━━━━

💎 Code Bonus: <b>${format_decimal(code_bonus)}</b> per code
👥 Referral Bonus: <b>${format_decimal(referral_bonus)}</b> after {codes_required} codes
💰 Min Withdrawal: <b>${format_decimal(min_withdrawal)}</b>

━━━━━━ <b>🔗 Referral Link</b> ━━━━━━

<code>{referral_link}</code>

Share this link with friends to earn bonus!"""
    
    markup = InlineKeyboardMarkup(row_width=1)
    share_text = "📤 Share Link" if lang == "en" else "📤 مشاركة الرابط"
    share_url = f"https://t.me/share/url?url={referral_link}"
    markup.add(InlineKeyboardButton(share_text, url=share_url))
    
    bot.send_message(msg.chat.id, bonus_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_lang_"))
def set_language_callback(call):
    user_id = call.from_user.id
    lang = call.data.replace("set_lang_", "")
    
    set_user_language(user_id, lang)
    
    pending_referrer = None
    if str(user_id) not in USERS:
        USERS[str(user_id)] = {"selected_country": None, "selected_number": None, "language": lang, "activations": 0, "join_date": datetime.now().strftime('%Y-%m-%d')}
    else:
        pending_referrer = USERS[str(user_id)].get("pending_referrer")
        USERS[str(user_id)]["language"] = lang
        if "activations" not in USERS[str(user_id)]:
            USERS[str(user_id)]["activations"] = 0
        if "join_date" not in USERS[str(user_id)]:
            USERS[str(user_id)]["join_date"] = datetime.now().strftime('%Y-%m-%d')
        if pending_referrer:
            del USERS[str(user_id)]["pending_referrer"]
    save_users()
    
    if pending_referrer:
        if process_referral(user_id, pending_referrer):
            try:
                referrer_lang = get_user_language(pending_referrer)
                settings = load_referral_settings()
                referral_bonus = settings.get("referral_bonus", 0.50)
                codes_required = settings.get("codes_required_for_referral", 3)
                
                user_name = call.from_user.first_name or "مستخدم"
                
                if referrer_lang == "ar":
                    notify_msg = (
                        f"🎉 <b>إحالة جديدة!</b>\n\n"
                        f"👤 المستخدم: <b>{user_name}</b>\n"
                        f"🆔 ID: <code>{user_id}</code>\n\n"
                        f"💰 <b>الربح المتوقع:</b> ${referral_bonus:.2f}\n"
                        f"📊 عند وصول {codes_required} أكواد ستصبح الإحالة نشطة!"
                    )
                else:
                    notify_msg = (
                        f"🎉 <b>New Referral!</b>\n\n"
                        f"👤 User: <b>{user_name}</b>\n"
                        f"🆔 ID: <code>{user_id}</code>\n\n"
                        f"💰 <b>Expected Profit:</b> ${referral_bonus:.2f}\n"
                        f"📊 Referral becomes active after {codes_required} codes!"
                    )
                bot.send_message(pending_referrer, notify_msg, parse_mode="HTML")
            except Exception as e:
                print(f"Error sending referral notification: {e}")
            try:
                bot.send_message(user_id, t(user_id, "referral_success"), parse_mode="HTML")
            except:
                pass
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    if not check_subscription(user_id):
        unjoined_channel = get_first_unjoined_channel(user_id)
        if unjoined_channel:
            bot.send_message(
                call.message.chat.id,
                get_subscription_message(unjoined_channel, user_id),
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel)
            )
        return
    
    first_name = call.from_user.first_name
    welcome_text = f"""<tg-emoji emoji-id='5314391089514291948'>⚡</tg-emoji> Welcome {first_name} ! <tg-emoji emoji-id='5316892517122187402'>❔</tg-emoji>

<tg-emoji emoji-id='4990298741463319592'>🔑</tg-emoji> Premium OTP Stock Bot
<tg-emoji emoji-id='4990298741463319592'>👋</tg-emoji> Fast & Reliable Service

<tg-emoji emoji-id='5406745015365943482'>🦦</tg-emoji> Please select an option below:"""

    bot.send_message(
        call.message.chat.id,
        welcome_text,
        reply_markup=get_main_reply_keyboard(user_id),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_instructions")
def show_instructions_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    referral_bonus = settings.get("referral_bonus", 0.50)
    codes_required = settings.get("codes_required_for_referral", 3)
    min_withdrawal = settings.get("min_withdrawal", 5.0)
    
    if lang == 'ar':
        instructions_text = f"""📖 <b>دليل استخدام البوت</b>

━━━━━━ <b>📱 استلام الأكواد</b> ━━━━━━

1️⃣ <b>اختيار الدولة:</b>
   • اضغط على "Get Number"
   • اختر الدولة التي تريدها

2️⃣ <b>اختيار الرقم:</b>
   • ستظهر لك الأرقام المتاحة
   • اختر الرقم المناسب

3️⃣ <b>استلام الكود:</b>
   • استخدم الرقم للتسجيل في أي موقع/تطبيق
   • سيصلك الكود تلقائياً هنا في البوت

━━━━━━ <b>💰 نظام الأرباح</b> ━━━━━━

💎 <b>بونص الكود:</b>
   • تحصل على <b>${format_decimal(code_bonus)}</b> عن كل كود تستلمه

👥 <b>بونص الإحالة:</b>
   • شارك رابط الإحالة مع أصدقائك
   • عندما يستلم صديقك <b>{codes_required} أكواد</b>
   • تحصل على <b>${referral_bonus:.2f}</b> مباشرة!

━━━━━━ <b>💵 السحب</b> ━━━━━━

💰 <b>الحد الأدنى:</b> ${min_withdrawal:.2f}
📝 <b>طرق السحب:</b>
   • فودافون كاش
   • USDT (TRC20/BEP20)
   • Binance ID

⚡ <b>خطوات السحب:</b>
   1. اذهب إلى "حسابي"
   2. اضغط "سحب الرصيد"
   3. اختر طريقة السحب
   4. أدخل بياناتك
   5. سيتم التحويل خلال 24 ساعة

━━━━━━ <b>📋 ملاحظات</b> ━━━━━━

⏰ انتظر الكود بعد طلب التحقق من الموقع
🔄 يمكنك تغيير الرقم في أي وقت
✅ الأرباح تُضاف تلقائياً لرصيدك

━━━━━━ شكراً لثقتك ━━━━━━

🆘 للمساعدة تواصل مع المطور"""
    else:
        instructions_text = f"""📖 <b>Bot Guide</b>

━━━━━━ <b>📱 Receiving Codes</b> ━━━━━━

1️⃣ <b>Choose Country:</b>
   • Click on "Get Number"
   • Select your desired country

2️⃣ <b>Choose Number:</b>
   • Available numbers will appear
   • Select the number you want

3️⃣ <b>Receive Code:</b>
   • Use the number to register on any site/app
   • The code will arrive automatically here in the bot

━━━━━━ <b>💰 Earning System</b> ━━━━━━

💎 <b>Code Bonus:</b>
   • Earn <b>${format_decimal(code_bonus)}</b> for each code you receive

👥 <b>Referral Bonus:</b>
   • Share your referral link with friends
   • When your friend receives <b>{codes_required} codes</b>
   • You get <b>${referral_bonus:.2f}</b> instantly!

━━━━━━ <b>💵 Withdrawal</b> ━━━━━━

💰 <b>Minimum:</b> ${min_withdrawal:.2f}
📝 <b>Withdrawal Methods:</b>
   • Vodafone Cash
   • USDT (TRC20/BEP20)
   • Binance ID

⚡ <b>How to Withdraw:</b>
   1. Go to "My Account"
   2. Click "Withdraw Balance"
   3. Choose withdrawal method
   4. Enter your details
   5. Transfer within 24 hours

━━━━━━ <b>📋 Notes</b> ━━━━━━

⏰ Wait for code after verification request from the site
🔄 You can change the number anytime
✅ Earnings are added automatically

━━━━━━ Thanks for your trust ━━━━━━

🆘 For help, contact the developer"""
    
    markup = InlineKeyboardMarkup(row_width=1)
    developer_btn_text = "🆘 Contact Developer" if get_user_language(user_id) == "en" else "🆘 تواصل مع المطور"
    markup.add(
        InlineKeyboardButton(developer_btn_text, url="https://t.me/D_i_V4")
    )
    markup.add(
        InlineKeyboardButton(t(user_id, "back"), callback_data="back_to_main_user")
    )
    
    bot.edit_message_text(
        instructions_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "my_account")
def my_account_callback(call):
    user_id = call.from_user.id
    
    user_data = USERS.get(str(user_id), {})
    activations = user_data.get("activations", 0)
    join_date = user_data.get("join_date", datetime.now().strftime('%Y-%m-%d'))
    lang = get_user_language(user_id)
    
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    total_earned = referral_data.get("total_earned", 0.0)
    referrals_count = len(referral_data.get("referrals", []))
    active_referrals = referral_data.get("active_referrals", 0)
    codes_received_bonus = referral_data.get("codes_received", 0)
    
    selected_country = user_data.get("selected_country")
    selected_number = user_data.get("selected_number")
    
    if selected_number and selected_country:
        number_status = f"✅ رقم نشط لـ {selected_country}" if lang == "ar" else f"✅ Active number for {selected_country}"
    else:
        number_status = "❌ لا يوجد رقم حالياً" if lang == "ar" else "❌ No number currently"
    
    bot_info = bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    if lang == "ar":
        account_text = (
            f"👤 <b>معلومات حسابك:</b>\n\n"
            f"🆔 <b>معرفك:</b> <code>{user_id}</code>\n"
            f"📅 <b>تاريخ الانضمام:</b> {join_date}\n"
            f"📊 <b>الأكواد المستلمة:</b> {activations}\n"
            f"🌐 <b>اللغة:</b> العربية\n\n"
            f"💰 <b>معلومات الأرباح:</b>\n"
            f"├ 💵 الرصيد الحالي: <b>${balance:.2f}</b>\n"
            f"├ 📈 إجمالي الأرباح: <b>${total_earned:.2f}</b>\n"
            f"├ 👥 عدد الإحالات: <b>{referrals_count}</b>\n"
            f"└ ✅ إحالات نشطة: <b>{active_referrals}</b>\n\n"
            f"🔗 <b>رابط الإحالة:</b>\n<code>{referral_link}</code>\n\n"
            f"💡 <b>حالة رقمك:</b>\n{number_status}"
        )
    else:
        account_text = (
            f"👤 <b>Your Account Info:</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📅 <b>Join Date:</b> {join_date}\n"
            f"📊 <b>Codes Received:</b> {activations}\n"
            f"🌐 <b>Language:</b> English\n\n"
            f"💰 <b>Earnings Info:</b>\n"
            f"├ 💵 Current Balance: <b>${balance:.2f}</b>\n"
            f"├ 📈 Total Earned: <b>${total_earned:.2f}</b>\n"
            f"├ 👥 Total Referrals: <b>{referrals_count}</b>\n"
            f"└ ✅ Active Referrals: <b>{active_referrals}</b>\n\n"
            f"🔗 <b>Referral Link:</b>\n<code>{referral_link}</code>\n\n"
            f"💡 <b>Number Status:</b>\n{number_status}"
        )
    
    copy_link_text = " نسخ رابط الإحالة" if lang == "ar" else " Copy Referral Link"
    share_link_text = "📤 مشاركة الرابط" if lang == "ar" else "📤 Share Link"
    share_url = f"https://t.me/share/url?url={referral_link}&text={'انضم عبر رابط الإحالة!' if lang == 'ar' else 'Join via my referral link!'}"
    
    keyboard_rows = []
    
    if balance >= load_referral_settings().get("min_withdrawal", 5.0):
        withdraw_text = "💰 سحب الرصيد" if lang == "ar" else "💰 Withdraw"
        keyboard_rows.append([{"text": withdraw_text, "callback_data": "withdraw_balance"}])
    
    bonus_info_text = "📖 نظام البونص والإحالات" if lang == "ar" else "📖 Bonus & Referral System"
    keyboard_rows.append([{"text": bonus_info_text, "callback_data": "bonus_info"}])
    
    keyboard_rows.append([
        {"text": copy_link_text, "copy_text": {"text": referral_link}},
        {"text": share_link_text, "url": share_url}
    ])
    
    keyboard_rows.append([{"text": t(user_id, "change_language"), "callback_data": "change_lang"}])
    keyboard_rows.append([{"text": t(user_id, "back"), "callback_data": "back_to_main_user"}])
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        resp = requests.post(url, json={
            "chat_id": call.message.chat.id,
            "message_id": call.message.message_id,
            "text": account_text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": keyboard_rows}
        }, timeout=10)
    except:
        markup = InlineKeyboardMarkup(row_width=2)
        if balance >= load_referral_settings().get("min_withdrawal", 5.0):
            withdraw_text = "💰 سحب الرصيد" if lang == "ar" else "💰 Withdraw"
            markup.add(InlineKeyboardButton(withdraw_text, callback_data="withdraw_balance")),
        markup.add(InlineKeyboardButton(bonus_info_text, callback_data="bonus_info")),
        markup.add(InlineKeyboardButton(t(user_id, "change_language"), callback_data="change_lang")),
        markup.add(InlineKeyboardButton(t(user_id, "back"), callback_data="back_to_main_user"))
        bot.edit_message_text(account_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "bonus_info")
def bonus_info_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    
    code_bonus = settings.get("code_bonus", 0.01)
    referral_bonus = settings.get("referral_bonus", 0.50)
    codes_required = settings.get("codes_required_for_referral", 3)
    min_withdrawal = settings.get("min_withdrawal", 5.0)
    
    if lang == "ar":
        info_text = (
            "📖 <b>نظام البونص والإحالات</b>\n\n"
            "━━━━━━ <b>كيف تربح؟</b> ━━━━━━\n\n"
            f"💎 <b>بونص الكود:</b>\n"
            f"   • تحصل على <b>${format_decimal(code_bonus)}</b> عن كل كود تستلمه\n\n"
            f"👥 <b>بونص الإحالة:</b>\n"
            f"   • شارك رابط الإحالة مع أصدقائك\n"
            f"   • عندما ينضم صديق عبر رابطك\n"
            f"   • ويستلم <b>{codes_required} أكواد</b>\n"
            f"   • تحصل على <b>${referral_bonus:.2f}</b> مباشرة!\n\n"
            "━━━━━━ <b>السحب</b> ━━━━━━\n\n"
            f"💰 <b>الحد الأدنى للسحب:</b> ${min_withdrawal:.2f}\n"
            "📝 <b>طرق السحب المتاحة:</b>\n"
            "   • فودافون كاش\n"
            "   • USDT (TRC20/BEP20)\n"
            "   • Binance ID\n\n"
            "━━━━━━ <b>ملاحظات مهمة</b> ━━━━━━\n\n"
            "✅ الأرباح تُضاف تلقائياً لرصيدك\n"
            "✅ يمكنك تتبع إحالاتك من صفحة حسابك\n"
            "✅ طلبات السحب تُعالج خلال 24 ساعة"
        )
    else:
        info_text = (
            "📖 <b>Bonus & Referral System</b>\n\n"
            "━━━━━━ <b>How to Earn?</b> ━━━━━━\n\n"
            f"💎 <b>Code Bonus:</b>\n"
            f"   • Get <b>${format_decimal(code_bonus)}</b> for each code you receive\n\n"
            f"👥 <b>Referral Bonus:</b>\n"
            f"   • Share your referral link with friends\n"
            f"   • When a friend joins via your link\n"
            f"   • And receives <b>{codes_required} codes</b>\n"
            f"   • You get <b>${referral_bonus:.2f}</b> instantly!\n\n"
            "━━━━━━ <b>Withdrawal</b> ━━━━━━\n\n"
            f"💰 <b>Minimum Withdrawal:</b> ${min_withdrawal:.2f}\n"
            "📝 <b>Available Methods:</b>\n"
            "   • Vodafone Cash\n"
            "   • USDT (TRC20/BEP20)\n"
            "   • Binance ID\n\n"
            "━━━━━━ <b>Important Notes</b> ━━━━━━\n\n"
            "✅ Earnings are added automatically to your balance\n"
            "✅ Track your referrals from your account page\n"
            "✅ Withdrawal requests are processed within 24 hours"
        )
    
    markup = InlineKeyboardMarkup()
    back_text = " رجوع" if lang == "ar" else " Back"
    markup.add(InlineKeyboardButton(back_text, callback_data="my_account",    icon_custom_emoji_id="5258236805890710909"))
    
    bot.edit_message_text(
        info_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

# تم تعطيل تغيير اللغة بناءً على طلب المستخدم
# @bot.callback_query_handler(func=lambda call: call.data == "change_lang")
# def change_language_callback(call):
#     user_id = call.from_user.id
#     
#     markup = InlineKeyboardMarkup(row_width=2)
#     markup.add(
#         InlineKeyboardButton(" العربية", callback_data="set_lang_ar", style="primary",    icon_custom_emoji_id="5294163983983463099"),
#         InlineKeyboardButton(" English", callback_data="set_lang_en", style="primary",    icon_custom_emoji_id="5293993521026453119")
#     )
#     
#     bot.edit_message_text(
#         "<tg-emoji emoji-id='5224450179368767019'>🌎</tg-emoji> <b>اختر اللغة / Choose Language</b>",
#         call.message.chat.id,
#         call.message.message_id,
#         parse_mode="HTML",
#         reply_markup=markup
#     )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main_user")
def back_to_main_user_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    
    markup = get_country_buttons(user_id)
    if markup:
        if lang == "ar":
            title = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        else:
            title = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        
        try:
            bot.edit_message_text(
                title,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except:
            pass
    else:
        try:
            text = t(user_id, "welcome")
            if not text: text = "🌐 <b>مرحباً بك!</b>"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=get_main_menu_lang(user_id)
            )
        except:
            pass

def get_single_channel_keyboard(channel, lang="ar"):
    markup = InlineKeyboardMarkup()
    btn_name = channel.get(f"name_{lang}", channel.get("name", "Join 🔗"))
    markup.add(InlineKeyboardButton(btn_name, url=channel['url'], style="primary", icon_custom_emoji_id="5330237710655306682"))
    
    verify_text = "✅ Verify Subscription"
    if lang == "en":
        verify_text = "✅ Verify Subscription"
    elif lang != "ar":
        verify_text = "✅ تحقق / Verify"
        
    markup.add(InlineKeyboardButton(verify_text, callback_data="verify_subscription", style="success"))
    return markup

def get_subscription_message_for_channel(channel, user_id):
    return "<b>════《 <tg-emoji emoji-id='5197288647275071607'>◾</tg-emoji> ACCESS REQUIRED 》════\nYou must join all channels below to use this bot:\nClick the buttons to join, then click Verify.</b>"

@bot.callback_query_handler(func=lambda call: call.data == "verify_subscription")
def verify_subscription_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    
    unjoined_channel = get_first_unjoined_channel(user_id)
    
    if unjoined_channel:
        try:
            bot.edit_message_text(
                get_subscription_message_for_channel(unjoined_channel, user_id),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel, user_id)
            )
        except:
            pass
        
        if lang == "ar":
            bot.answer_callback_query(call.id, "❌ انضم للقناة أولاً!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)

    if str(user_id) not in USERS:
        USERS[str(user_id)] = {"selected_country": None, "selected_number": None}
        save_users()

    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    markup = get_country_buttons(user_id)
    
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك بالوصول لهذه اللوحة", show_alert=True)
        return

    bot.edit_message_text(
        "Welcome to admin panel <tg-emoji emoji-id='5422439311196834318'>💡</tg-emoji>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "toggle_return_otp")
def toggle_return_otp_callback(call):
    global RETURN_OTP_ENABLED
    RETURN_OTP_ENABLED = not RETURN_OTP_ENABLED
    save_return_otp_state()
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_admin_menu())
        status_txt = "تم تفعيل Return OTP" if RETURN_OTP_ENABLED else "تم إيقاف Return OTP"
        bot.answer_callback_query(call.id, status_txt)
    except Exception as e:
        print(f"Error toggling return otp: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_accounts_and_sites")
def admin_accounts_and_sites_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" Sites Settings", callback_data="admin_sites_menu", style="primary",    icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(" Manage Accounts", callback_data="admin_accounts_menu", style="primary",    icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.edit_message_text("<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Accounts — Sites Management</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_countries_manage")
def admin_countries_manage_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Add Country", callback_data="admin_add_country", style="primary",    icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton("Remove Country", callback_data="admin_remove_country", style="primary",    icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.edit_message_text("<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Countries Management</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_channels_manage")
def admin_channels_manage_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" Add Channel", callback_data="admin_add_channel", style="primary",    icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(" Remove Channel", callback_data="admin_remove_channel", style="primary",    icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.edit_message_text("<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Channels Management</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_admins_manage")
def admin_admins_manage_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" Add Admin", callback_data="admin_add_admin", style="primary",    icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(" Remove Admin", callback_data="admin_remove_admin", style="primary",    icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.edit_message_text("<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Admins Management</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban_manage")
def admin_ban_manage_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" Ban User", callback_data="admin_ban_user", style="primary",    icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(" Unban User", callback_data="admin_unban_user", style="primary",    icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.edit_message_text("<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Ban Management</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("na_add_country_srv_"))
def na_add_country_server_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    if user_id not in user_states or user_states[user_id].get("action") != "na_add_country_server":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    server = call.data.replace("na_add_country_srv_", "")
    state = user_states[user_id]
    
    user_states[user_id] = {
        "action": "na_add_country_platforms",
        "numbers_file": state.get("numbers_file"),
        "country_code": state.get("country_code"),
        "country_name": state.get("country_name"),
        "num_cleaned": state.get("num_cleaned"),
        "server": server,
        "selected_platforms": []
    }
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Facebook", callback_data="na_add_country_plt_Facebook", icon_custom_emoji_id="5382322671679708881", style="primary"),
        InlineKeyboardButton("WhatsApp", callback_data="na_add_country_plt_WhatsApp", icon_custom_emoji_id="5381990043642502553", style="primary")
    )
    markup.add(
        InlineKeyboardButton("Telegram", callback_data="na_add_country_plt_Telegram", icon_custom_emoji_id="5381879959335738545", style="primary"),
        InlineKeyboardButton("Instagram", callback_data="na_add_country_plt_Instagram", icon_custom_emoji_id="5382054253403577563", style="primary")
    )
    markup.add(
        InlineKeyboardButton("Twitter/X", callback_data="na_add_country_plt_Twitter", icon_custom_emoji_id="5391197405553107640", style="primary"),
        InlineKeyboardButton("TikTok", callback_data="na_add_country_plt_TikTok", icon_custom_emoji_id="5390966190283694453", style="primary")
    )
    markup.add(
        InlineKeyboardButton("Discord", callback_data="na_add_country_plt_Discord", icon_custom_emoji_id="5382132232829804982", style="primary"),
        InlineKeyboardButton("Gmail", callback_data="na_add_country_plt_Gmail", icon_custom_emoji_id="5391038994274329680", style="primary")
    )
    markup.add(
        InlineKeyboardButton("🌐 All Platforms", callback_data="na_add_country_plt_ALL")
    )
    markup.add(InlineKeyboardButton("✅ Confirm & Finish", callback_data="na_add_country_finish", style="primary")),
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="numbers_admin_panel", style="danger"))
    
    server_names = {
        "GROUP": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟏",
        "Fly sms": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟐",
        "Number_Panel": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟑",
        "Bolt": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟒",
        "iVASMS": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟓",
        "MSI": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟔",
        "proton SMS": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟕",
        "IMO": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟖"
    }
    
    bot.edit_message_text(
        f"✅ <b>الخطوة 5/5 - اختيار المنصات</b>\n\n"
        f"🌍 Country: <b>{state.get('country_name')}</b>\n"
        f"🔢 Country Code: <b>{state.get('country_code')}</b>\n"
        f"🖥️ السيرفر: <b>{server_names.get(server, server)}</b>\n\n"
        f"📱 <b>Selected Platforms:</b> None\n\n"
        f"Choose the platforms these numbers work on:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "na_add_country_edit_name")
def na_add_country_edit_name_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    lang = get_user_language(user_id)
    state = user_states.get(user_id)
    if not state:
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    state["action"] = "na_add_country_edit_name_input"
    text = "📝 يرجى إرسال الاسم الجديد للدولة:" if lang == "ar" else "📝 Please send the new country name:"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("na_add_country_plt_"))
def na_add_country_platform_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    if user_id not in user_states or user_states[user_id].get("action") != "na_add_country_platforms":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    platform = call.data.replace("na_add_country_plt_", "")
    state = user_states[user_id]
    selected_platforms = state.get("selected_platforms", [])
    
    if platform == "ALL":
        selected_platforms = ["Facebook", "WhatsApp", "Telegram", "Instagram", "Twitter", "TikTok", "Discord", "Gmail"]
    elif platform in selected_platforms:
        selected_platforms.remove(platform)
    else:
        selected_platforms.append(platform)
    
    user_states[user_id]["selected_platforms"] = selected_platforms
    
    platform_icons = {
        "Facebook": "<tg-emoji emoji-id='5269427536453984598'>📘</tg-emoji>", "WhatsApp": "<tg-emoji emoji-id='5271536803482981220'>💬</tg-emoji>", "Telegram": "<tg-emoji emoji-id='5271801931814165886'>✈️</tg-emoji>",
        "Instagram": "<tg-emoji emoji-id='5269682734820777950'>📸</tg-emoji>", "Twitter": "", "TikTok": "",
        "Discord": "", "Gmail": "", "IMO": ""
    }
    
    def get_btn_text(name, icon):
        check = "🔹" if name in selected_platforms else ""
        return f"{check} {icon} {name}"
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(get_btn_text("Facebook", ""), callback_data="na_add_country_plt_Facebook", style="primary", icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(get_btn_text("WhatsApp", ""), callback_data="na_add_country_plt_WhatsApp", style="primary", icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Telegram", ""), callback_data="na_add_country_plt_Telegram", style="primary", icon_custom_emoji_id="5381879959335738545"),
        InlineKeyboardButton(get_btn_text("Instagram", ""), callback_data="na_add_country_plt_Instagram", style="primary", icon_custom_emoji_id="5382054253403577563")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Twitter", ""), callback_data="na_add_country_plt_Twitter", style="primary", icon_custom_emoji_id="5391197405553107640"),
        InlineKeyboardButton(get_btn_text("TikTok", ""), callback_data="na_add_country_plt_TikTok", style="primary", icon_custom_emoji_id="5390966190283694453")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Discord", ""), callback_data="na_add_country_plt_Discord", style="primary", icon_custom_emoji_id="5382132232829804982"),
        InlineKeyboardButton(get_btn_text("Gmail", ""), callback_data="na_add_country_plt_Gmail", style="primary", icon_custom_emoji_id="5391038994274329680"),
        InlineKeyboardButton(get_btn_text(""), callback_data="na_add_country_plt_IMO", style="primary")
    )
    markup.add(
        InlineKeyboardButton(" All Platforms", callback_data="na_add_country_plt_ALL",    icon_custom_emoji_id="5042186567783809934")
    )
    markup.add(InlineKeyboardButton(" Confirm & Finish", callback_data="na_add_country_finish",    icon_custom_emoji_id="5039844895779455925")),
    markup.add(InlineKeyboardButton(" Cancel", callback_data="numbers_admin_panel",    icon_custom_emoji_id="5039671744172917707"))
    
    
    platform_icons = {
        "Facebook": "<tg-emoji emoji-id='5269427536453984598'>📘</tg-emoji>", "WhatsApp": "<tg-emoji emoji-id='5271536803482981220'>💬</tg-emoji>", "Telegram": "<tg-emoji emoji-id='5271801931814165886'>✈️</tg-emoji>",
        "Instagram": "<tg-emoji emoji-id='5269682734820777950'>📸</tg-emoji>", "Twitter": "", "TikTok": "",
        "Discord": "", "Gmail": "", "IMO": ""
    }
    
    platforms_text = ", ".join([f"{platform_icons.get(p, '📱')} {p}" for p in selected_platforms]) if selected_platforms else "لا يوجد"
    
    bot.edit_message_text(
        f"<tg-emoji emoji-id='5769421696041753266'>◾</tg-emoji> <b>Step 5/5 — Select Platforms</b>\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <b>{state.get('country_name')} (+{state.get('country_code')})</b>\n\n"
        f"Selected: {platforms_text}\n\n"
        f"Choose the platforms:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "na_add_country_finish")
def na_add_country_finish_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    if user_id not in user_states or user_states[user_id].get("action") != "na_add_country_platforms":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    state = user_states[user_id]
    country_name = state.get("country_name")
    country_code = state.get("country_code")
    numbers_file = state.get("numbers_file")
    server = state.get("server")
    selected_platforms = state.get("selected_platforms", [])
    num_cleaned = state.get("num_cleaned", 0)
    
    if not selected_platforms:
        bot.answer_callback_query(call.id, "You Should select 1 country 💡", show_alert=True)
        return
    
    flag = get_flag_for_country_code(country_code)
    
    
    country_id = f"{country_name}_{uuid.uuid4().hex[:6]}"
    
    COUNTRIES[country_id] = {
        "display_name": country_name,
        "file": numbers_file,
        "code": country_code,
        "flag": flag,
        "server": server,
        "platforms": selected_platforms,
        "numbers_count": num_cleaned,
        "added_by": user_id,
        "added_at": datetime.now().isoformat()
    }
    save_countries()
    
    del user_states[user_id]
    
    server_names = {
        "GROUP": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟏",
        "Fly sms": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟐",
        "Number_Panel": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟑",
        "Bolt": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟒",
        "iVASMS": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟓",
        "MSI": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟔",
        "proton SMS": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟕",
        "IMO": "𝐒𝐞𝐫𝐯𝐞𝐫 𝟖"
    }
    
    platforms_text = ", ".join(selected_platforms)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Add more fiels", callback_data="admin_add_country", style="primary",    icon_custom_emoji_id="5393194986252542669"),
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        f"<b>═══《 <tg-emoji emoji-id='5764701999429849874'>◾</tg-emoji> SUCCESS 》═══</b>\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Country: <b>{country_name}</b>\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Numbers added: <b>{num_cleaned}</b>\n"
        f"<tg-emoji emoji-id='5314391089514291948'>◾</tg-emoji><b></b>\n"
        f" <tg-emoji emoji-id='6026257381678124710'>◾</tg-emoji><b> Country added successfully</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

def get_flag_for_country_code(country_code):
    try:
       
        code_str = str(country_code).replace('+', '').strip()
        if not code_str.isdigit():
            return "🌍"
            
        import phonenumbers
        from phonenumbers.phonenumberutil import region_code_for_country_code
        
       
        if code_str == "1":
            return "<tg-emoji emoji-id='5294526187165471742'>🇧🇧</tg-emoji>"
        region = region_code_for_country_code(int(code_str))
        if region and region != 'ZZ':
            return get_flag(region)
    except Exception as e:
        print(f"Error getting flag for code {country_code}: {e}")
        
    return "🌍"

@bot.callback_query_handler(func=lambda call: call.data == "na_list_countries")
def na_list_countries_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    if not COUNTRIES:
        text = "📋 <b>الدول المتاحة</b>\n\n❌ لا توجد دول مضافة بعد!"
    else:
        text = "📋 <b>الدول المتاحة</b>\n\n"
        for idx, (country_name, info) in enumerate(sorted(COUNTRIES.items()), 1):
            flag = info.get("flag", "🌍")
            server = info.get("server", "N/A")
            platforms = info.get("platforms", [])
            platforms_count = len(platforms)
            text += f"{idx}. {flag} <b>{country_name}</b> - {server} ({platforms_count} منصات)\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(" رجوع", callback_data="numbers_admin_panel",    icon_custom_emoji_id="5258236805890710909"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "na_ban_user")
def na_ban_user_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    user_states[user_id] = {"mode": "na_ban_user"}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="numbers_admin_panel"))
    
    bot.edit_message_text(
        "🚫 <b>حظر مستخدم</b>\n\n"
        "📝 أرسل معرف المستخدم (ID) الذي تريد حظره:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "na_unban_user")
def na_unban_user_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    user_states[user_id] = {"mode": "na_unban_user"}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="numbers_admin_panel"))
    
    bot.edit_message_text(
        "✅ <b>إلغاء حظر مستخدم</b>\n\n"
        "📝 أرسل معرف المستخدم (ID) الذي تريد إلغاء حظره:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "na_banned_list")
def na_banned_list_callback(call):
    user_id = call.from_user.id
    if not is_numbers_admin(user_id):
        return
    
    if not BANNED:
        text = "📊 <b>قائمة المحظورين</b>\n\n✅ لا يوجد مستخدمين محظورين!"
    else:
        text = "📊 <b>قائمة المحظورين</b>\n\n"
        for idx, banned_id in enumerate(BANNED[:50], 1):
            text += f"{idx}. <code>{banned_id}</code>\n"
        if len(BANNED) > 50:
            text += f"\n... و {len(BANNED) - 50} آخرين"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="numbers_admin_panel"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_manage_numbers_admins")
def admin_manage_numbers_admins_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك!", show_alert=True)
        return
    
    text = "🧮 <b>إدارة أدمن الأرقام</b>\n\n"
    text += f"👥 عدد أدمن الأرقام: {len(NUMBERS_ADMINS)}\n\n"
    
    if NUMBERS_ADMINS:
        text += "<b>القائمة الحالية:</b>\n"
        for idx, admin_id in enumerate(NUMBERS_ADMINS, 1):
            text += f"{idx}. <code>{admin_id}</code>\n"
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ إضافة أدمن أرقام", callback_data="add_numbers_admin"),
        InlineKeyboardButton("➖ حذف أدمن أرقام", callback_data="remove_numbers_admin")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "add_numbers_admin")
def add_numbers_admin_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"mode": "add_numbers_admin"}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_manage_numbers_admins"))
    
    bot.edit_message_text(
        "➕ <b>إضافة أدمن أرقام جديد</b>\n\n"
        "📝 أرسل معرف المستخدم (User ID) الذي تريد تعيينه كأدمن أرقام:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "remove_numbers_admin")
def remove_numbers_admin_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    if not NUMBERS_ADMINS:
        bot.answer_callback_query(call.id, "❌ لا يوجد أدمن أرقام!", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for admin_id in NUMBERS_ADMINS:
        markup.add(
        InlineKeyboardButton(
        f"🗑 حذف {admin_id}",
        callback_data=f"del_numbers_admin_{admin_id}"
            )
        )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_manage_numbers_admins"))
    
    bot.edit_message_text(
        "➖ <b>حذف أدمن أرقام</b>\n\n"
        "اختر الأدمن الذي تريد حذفه:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_numbers_admin_"))
def del_numbers_admin_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    admin_to_remove = int(call.data.replace("del_numbers_admin_", ""))
    
    if admin_to_remove in NUMBERS_ADMINS:
        NUMBERS_ADMINS.remove(admin_to_remove)
        save_numbers_admins()
        bot.answer_callback_query(call.id, f"✅ تم حذف {admin_to_remove} من أدمن الأرقام!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ الأدمن غير موجود!", show_alert=True)
    
    admin_manage_numbers_admins_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == "admin_statistics")
def admin_statistics_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    stats_text = get_statistics_text()
    bot.send_message(call.message.chat.id, stats_text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_referral_settings")
def admin_referral_settings_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    settings = load_referral_settings()
    
    text = (
        "💰 <b>إعدادات نظام الإحالات والبونص</b>\n\n"
        f"🎁 بونص الكود: <b>${settings.get('code_bonus', 0.01)}</b>\n"
        f"👥 بونص الإحالة: <b>${settings.get('referral_bonus', 0.50)}</b>\n"
        f"📊 عدد الأكواد المطلوبة للإحالة النشطة: <b>{settings.get('codes_required_for_referral', 3)}</b>\n"
        f"💵 الحد الأدنى للسحب: <b>${settings.get('min_withdrawal', 5.0)}</b>\n\n"
        "اختر الإعداد الذي تريد تعديله:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎁 بونص الكود", callback_data="edit_code_bonus"),
        InlineKeyboardButton("👥 بونص الإحالة", callback_data="edit_referral_bonus")
    )
    markup.add(
        InlineKeyboardButton("📊 أكواد الإحالة", callback_data="edit_codes_required"),
        InlineKeyboardButton("💵 حد السحب", callback_data="edit_min_withdrawal")
    )
    markup.add(
        InlineKeyboardButton("➕ إضافة رصيد لمستخدم", callback_data="admin_add_balance"),
        InlineKeyboardButton("➖ خصم رصيد من مستخدم", callback_data="admin_subtract_balance")
    )
    markup.add(
        InlineKeyboardButton("📋 طلبات السحب", callback_data="view_withdrawal_requests"),
        InlineKeyboardButton("⚙️ طرق السحب", callback_data="admin_withdrawal_methods")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_code_bonus")
def edit_code_bonus_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_code_bonus"}
    bot.send_message(
        call.message.chat.id,
        "🎁 <b>تعديل بونص الكود</b>\n\n"
        "أرسل القيمة الجديدة (مثال: 0.01 أو 0.02):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_referral_bonus")
def edit_referral_bonus_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_referral_bonus"}
    bot.send_message(
        call.message.chat.id,
        "👥 <b>تعديل بونص الإحالة</b>\n\n"
        "أرسل القيمة الجديدة (مثال: 0.50 أو 1.00):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_codes_required")
def edit_codes_required_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_codes_required"}
    bot.send_message(
        call.message.chat.id,
        "📊 <b>تعديل عدد الأكواد المطلوبة</b>\n\n"
        "أرسل العدد الجديد (مثال: 3 أو 5):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_min_withdrawal")
def edit_min_withdrawal_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_min_withdrawal"}
    bot.send_message(
        call.message.chat.id,
        "💵 <b>تعديل الحد الأدنى للسحب</b>\n\n"
        "أرسل القيمة الجديدة (مثال: 5.00 أو 10.00):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "admin_add_balance"}
    bot.send_message(
        call.message.chat.id,
        "➕ <b>إضافة رصيد لمستخدم</b>\n\n"
        "أرسل معرف المستخدم والمبلغ بالصيغة التالية:\n"
        "<code>USER_ID AMOUNT</code>\n\n"
        "مثال: <code>123456789 5.00</code>",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_subtract_balance")
def admin_subtract_balance_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "admin_subtract_balance"}
    bot.send_message(
        call.message.chat.id,
        "➖ <b>خصم رصيد من مستخدم</b>\n\n"
        "أرسل معرف المستخدم والمبلغ بالصيغة التالية:\n"
        "<code>USER_ID AMOUNT</code>\n\n"
        "مثال: <code>123456789 5.00</code>",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "view_withdrawal_requests")
def view_withdrawal_requests_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    requests = load_withdrawal_requests()
    pending_requests = [r for r in requests if r.get("status") == "pending"]
    
    if not pending_requests:
        bot.answer_callback_query(call.id, "📭 لا توجد طلبات سحب معلقة!", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for req in pending_requests[:10]:
        req_id = req.get("id", "")[:8]
        user_req_id = req.get("user_id")
        amount = req.get("amount", 0)
        markup.add(
        InlineKeyboardButton(
        f"👤 {user_req_id} | ${amount:.2f}",
        callback_data=f"view_wd_req_{req_id}"
            )
        )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_referral_settings"))
    
    bot.edit_message_text(
        f"📋 <b>طلبات السحب المعلقة</b>\n\nعدد الطلبات: {len(pending_requests)}",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_wd_req_"))
def view_wd_request_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    req_id = call.data.replace("view_wd_req_", "")
    requests = load_withdrawal_requests()
    
    req = None
    for r in requests:
        if r.get("id", "").startswith(req_id):
            req = r
            break
    
    if not req:
        bot.answer_callback_query(call.id, "❌ الطلب غير موجود!", show_alert=True)
        return
    
    target_user_id = req.get('user_id')
    target_user_data = USERS.get(str(target_user_id), {})
    target_referral_data = get_user_referral_data(target_user_id)
    
    join_date = target_user_data.get("join_date", "غير محدد")
    total_codes = target_user_data.get("activations", 0)
    total_referrals = len(target_referral_data.get("referrals", []))
    active_referrals = target_referral_data.get("active_referrals", 0)
    total_earned = target_referral_data.get("total_earned", 0.0)
    current_balance = target_referral_data.get("balance", 0.0)
    
    text = (
        f"📋 <b>تفاصيل طلب السحب</b>\n\n"
        f"🆔 معرف الطلب: <code>{req.get('id', '')[:8]}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 <b>بيانات المستخدم:</b>\n"
        f"├ 🆔 ID: <code>{target_user_id}</code>\n"
        f"├ 📅 تاريخ الانضمام: {join_date}\n"
        f"├ 📊 إجمالي الأكواد: {total_codes}\n"
        f"├ 👥 إجمالي الإحالات: {total_referrals}\n"
        f"├ ✅ إحالات نشطة: {active_referrals}\n"
        f"├ 💰 إجمالي الأرباح: ${total_earned:.2f}\n"
        f"└ 💵 الرصيد الحالي: ${current_balance:.2f}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💳 <b>تفاصيل السحب:</b>\n"
        f"├ 💵 المبلغ: <b>${req.get('amount', 0):.2f}</b>\n"
        f"├ 📝 الطريقة: {req.get('method', 'غير محدد')}\n"
        f"├ 📋 التفاصيل: <code>{req.get('details', 'غير محدد')}</code>\n"
        f"├ 📅 التاريخ: {req.get('date', 'غير محدد')}\n"
        f"└ 📊 الحالة: {req.get('status', 'pending')}"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"approve_wd_{req_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_wd_{req_id}")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="view_withdrawal_requests"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_wd_") or call.data.startswith("wd_approve_"))
def approve_withdrawal_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    if call.data.startswith("wd_approve_"):
        req_id = call.data.replace("wd_approve_", "")
    else:
        req_id = call.data.replace("approve_wd_", "")
    
    requests = load_withdrawal_requests()
    
    for i, req in enumerate(requests):
        if req.get("id", "").startswith(req_id):
            requests[i]["status"] = "approved"
            save_withdrawal_requests(requests)
            
            target_user_id = req.get("user_id")
            user_lang = get_user_language(target_user_id)
            
            try:
                if user_lang == "ar":
                    bot.send_message(
                        target_user_id,
                        f"✅ <b>تم إرسال المبلغ بنجاح!</b>\n\n"
                        f"🆔 رقم الطلب: <code>{req.get('id', '')[:8]}</code>\n"
                        f"💵 المبلغ: <b>${req.get('amount', 0):.2f}</b>\n"
                        f"📝 الطريقة: {req.get('method', '')}\n"
                        f"📋 التفاصيل: <code>{req.get('details', '')}</code>\n\n"
                        f"💰 تم تحويل المبلغ إلى حسابك بنجاح.\n"
                        f"شكراً لاستخدامك البوت! 🎉",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        target_user_id,
                        f"✅ <b>Payment sent successfully!</b>\n\n"
                        f"🆔 Request ID: <code>{req.get('id', '')[:8]}</code>\n"
                        f"💵 Amount: <b>${req.get('amount', 0):.2f}</b>\n"
                        f"📝 Method: {req.get('method', '')}\n"
                        f"📋 Details: <code>{req.get('details', '')}</code>\n\n"
                        f"💰 The amount has been successfully transferred to your account.\n"
                        f"Thank you for using the bot! 🎉",
                        parse_mode="HTML"
                    )
            except:
                pass
            
            try:
                bot.edit_message_text(
                    f"✅ <b>تم تأكيد الدفع!</b>\n\n"
                    f"🆔 رقم الطلب: <code>{req.get('id', '')[:8]}</code>\n"
                    f"👤 المستخدم: <code>{target_user_id}</code>\n"
                    f"💵 المبلغ: <b>${req.get('amount', 0):.2f}</b>\n"
                    f"📝 الطريقة: {req.get('method', '')}\n"
                    f"📋 التفاصيل: <code>{req.get('details', '')}</code>\n\n"
                    f"✅ تم إشعار المستخدم بإرسال المبلغ",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML"
                )
            except:
                bot.answer_callback_query(call.id, "✅ تم تأكيد الدفع!", show_alert=True)
            break

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_wd_") or call.data.startswith("wd_reject_"))
def reject_withdrawal_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    if call.data.startswith("wd_reject_"):
        req_id = call.data.replace("wd_reject_", "")
    else:
        req_id = call.data.replace("reject_wd_", "")
    
    requests = load_withdrawal_requests()
    
    for i, req in enumerate(requests):
        if req.get("id", "").startswith(req_id):
            requests[i]["status"] = "rejected"
            
            global REFERRALS
            REFERRALS = load_referrals()
            target_user_id = req.get("user_id")
            user_key = str(target_user_id)
            if user_key in REFERRALS:
                REFERRALS[user_key]["balance"] += req.get("amount", 0)
                save_referrals(REFERRALS)
            
            save_withdrawal_requests(requests)
            
            user_lang = get_user_language(target_user_id)
            
            try:
                if user_lang == "ar":
                    bot.send_message(
                        target_user_id,
                        f"❌ <b>تم رفض طلب السحب</b>\n\n"
                        f"🆔 رقم الطلب: <code>{req.get('id', '')[:8]}</code>\n"
                        f"💵 المبلغ: <b>${req.get('amount', 0):.2f}</b>\n\n"
                        f"تم إرجاع المبلغ إلى رصيدك.",
                        parse_mode="HTML"
                    )
                else:
                    bot.send_message(
                        target_user_id,
                        f"❌ <b>Withdrawal request rejected</b>\n\n"
                        f"🆔 Request ID: <code>{req.get('id', '')[:8]}</code>\n"
                        f"💵 Amount: <b>${req.get('amount', 0):.2f}</b>\n\n"
                        f"The amount has been returned to your balance.",
                        parse_mode="HTML"
                    )
            except:
                pass
            
            try:
                bot.edit_message_text(
                    f"❌ <b>تم رفض الطلب!</b>\n\n"
                    f"🆔 رقم الطلب: <code>{req.get('id', '')[:8]}</code>\n"
                    f"👤 المستخدم: <code>{target_user_id}</code>\n"
                    f"💵 المبلغ: <b>${req.get('amount', 0):.2f}</b>\n"
                    f"تم إرجاع المبلغ للمستخدم.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="HTML"
                )
            except:
                bot.answer_callback_query(call.id, "❌ تم رفض الطلب وإرجاع المبلغ!", show_alert=True)
            break

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawal_methods")
def admin_withdrawal_methods_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    methods = load_withdrawal_methods()
    
    text = "⚙️ <b>إدارة طرق السحب</b>\n\n"
    text += "اضغط على طريقة السحب لتفعيلها أو تعطيلها:\n\n"
    
    method_icons = {"vodafone": "💳", "usdt_trc20": "", "usdt_bep20": "🔗", "binance_id": "🅱️"}
    
    markup = InlineKeyboardMarkup(row_width=1)
    
    for method_key, method_data in methods.items():
        enabled = method_data.get("enabled", True)
        name = method_data.get("name_ar", method_key)
        icon = method_icons.get(method_key, "💰")
        status = "✅" if enabled else "❌"
        markup.add(InlineKeyboardButton(f"{status} {icon} {name}", callback_data=f"toggle_wd_method_{method_key}"))
    
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_referral_settings"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_wd_method_"))
def toggle_withdrawal_method_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    method_key = call.data.replace("toggle_wd_method_", "")
    methods = load_withdrawal_methods()
    
    if method_key in methods:
        methods[method_key]["enabled"] = not methods[method_key].get("enabled", True)
        save_withdrawal_methods(methods)
        
        status = "مفعّل ✅" if methods[method_key]["enabled"] else "معطّل ❌"
        bot.answer_callback_query(call.id, f"تم تغيير الحالة إلى: {status}", show_alert=True)
    
    admin_withdrawal_methods_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == "admin_welcome_messages")
def admin_welcome_messages_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    messages = load_welcome_messages()
    
    text = (
        "📝 <b>إعدادات رسائل الترحيب</b>\n\n"
        f"🇸🇦 <b>العربية:</b>\n{messages.get('ar', 'غير محدد')[:100]}...\n\n"
        f"🇬🇧 <b>English:</b>\n{messages.get('en', 'Not set')[:100]}...\n\n"
        "اختر اللغة لتعديل رسالة الترحيب:"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" تعديل العربية", callback_data="edit_welcome_ar", style="primary",    icon_custom_emoji_id="5294163983983463099"),
        InlineKeyboardButton(" Edit English", callback_data="edit_welcome_en", style="primary",    icon_custom_emoji_id="5293993521026453119")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_welcome_ar")
def edit_welcome_ar_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_welcome_ar"}
    messages = load_welcome_messages()
    
    bot.send_message(
        call.message.chat.id,
        f"🇸🇦 <b>تعديل رسالة الترحيب العربية</b>\n\n"
        f"الرسالة الحالية:\n<code>{messages.get('ar', '')}</code>\n\n"
        f"أرسل الرسالة الجديدة (يمكنك استخدام HTML):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_welcome_en")
def edit_welcome_en_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "edit_welcome_en"}
    messages = load_welcome_messages()
    
    bot.send_message(
        call.message.chat.id,
        f"🇬🇧 <b>Edit English Welcome Message</b>\n\n"
        f"Current message:\n<code>{messages.get('en', '')}</code>\n\n"
        f"Send the new message (HTML supported):",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_button_links")
def admin_button_links_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    links = load_button_links()
    
    text = (
        "🔗 <b>إعدادات روابط الأزرار</b>\n"
        "🔗 <b>Button Links Settings</b>\n\n"
        f"📢 <b>رابط الجروب / Group Link:</b>\n<code>{links.get('group_link', 'Not set')}</code>\n\n"
        f"📺 <b>رابط القناة / Channel Link:</b>\n<code>{links.get('channel_link', 'Not set')}</code>\n\n"
        f"👨‍💻 <b>رابط المطور / Developer Link:</b>\n<code>{links.get('developer_link', 'Not set')}</code>\n\n"
        "اختر الرابط لتعديله:\nChoose a link to edit:"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📢 تعديل رابط الجروب / Edit Group Link", callback_data="edit_link_group"),
        InlineKeyboardButton("📺 تعديل رابط القناة / Edit Channel Link", callback_data="edit_link_channel"),
        InlineKeyboardButton("👨‍💻 تعديل رابط المطور / Edit Developer Link", callback_data="edit_link_developer")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع / Back", callback_data="admin"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_link_"))
def edit_link_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    link_type = call.data.replace("edit_link_", "")
    link_names = {
        "group": ("رابط الجروب", "Group Link", "group_link"),
        "channel": ("رابط القناة", "Channel Link", "channel_link"),
        "developer": ("رابط المطور", "Developer Link", "developer_link")
    }
    
    ar_name, en_name, key = link_names.get(link_type, ("Link", "Link", "group_link"))
    links = load_button_links()
    current = links.get(key, "")
    
    user_states[user_id] = {"action": f"edit_button_link_{key}"}
    
    bot.send_message(
        call.message.chat.id,
        f"🔗 <b>تعديل {ar_name}</b>\n"
        f"🔗 <b>Edit {en_name}</b>\n\n"
        f"الرابط الحالي / Current link:\n<code>{current}</code>\n\n"
        f"أرسل الرابط الجديد / Send the new link:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_create_backup")
def admin_create_backup_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    bot.answer_callback_query(call.id, "جاري إنشاء النسخة الاحتياطية... ⏳")
    try:
        backup_file = backup_manager.create_backup()
        with open(backup_file, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        os.remove(backup_file)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ حدث خطأ أثناء إنشاء النسخة الاحتياطية: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_restore_backup")
def admin_restore_backup_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    msg = bot.send_message(call.message.chat.id, "📤 من فضلك أرسل ملف النسخة الاحتياطية (zip).")
    bot.register_next_step_handler(msg, process_restore_backup)

def process_restore_backup(message):
    if not is_admin(message.from_user.id): return
    if not message.document or not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ عذراً، يجب إرسال ملف بصيغة zip فقط.")
        return
    
    bot.reply_to(message, "جاري استعادة النسخة الاحتياطية... ⏳")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open("restore_temp.zip", 'wb') as f:
            f.write(downloaded_file)
            
        if backup_manager.restore_backup("restore_temp.zip"):
            bot.reply_to(message, "✅ تم استعادة النسخة الاحتياطية بنجاح! سيتم إعادة تحميل البيانات الآن.")
            load_data() 
        else:
            bot.reply_to(message, "❌ فشل استعادة النسخة الاحتياطية.")
        
        if os.path.exists("restore_temp.zip"):
            os.remove("restore_temp.zip")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الاستعادة: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_otp_buttons")
def admin_otp_buttons_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    text = "🔘 <b>إعدادات أزرار رسالة OTP</b>\n\n"
    if OTP_BUTTONS:
        for i, btn in enumerate(OTP_BUTTONS, 1):
            text += f"{i}. <b>{btn['name']}</b>\n   🔗 <code>{btn['url']}</code>\n\n"
    else:
        text += "لا توجد أزرار مضافة\n\n"
    
    text += "اختر الإجراء المطلوب:"
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ إضافة زر جديد", callback_data="otp_btn_add"),
        InlineKeyboardButton("✏️ تعديل زر", callback_data="otp_btn_edit_list"),
        InlineKeyboardButton("🗑 حذف زر", callback_data="otp_btn_delete_list")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "otp_btn_add")
def otp_btn_add_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    user_states[user_id] = {"action": "otp_btn_add_name"}
    
    bot.send_message(
        call.message.chat.id,
        "➕ <b>إضافة زر جديد</b>\n\n"
        "أرسل اسم الزر:\n"
        "(مثال: 𝕮𝖍𝖆𝖓𝖓𝖊𝖑 أو Channel)",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "otp_btn_edit_list")
def otp_btn_edit_list_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    if not OTP_BUTTONS:
        bot.answer_callback_query(call.id, "❌ لا توجد أزرار للتعديل!", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for i, btn in enumerate(OTP_BUTTONS):
        markup.add(InlineKeyboardButton(f"✏️ {btn['name']}", callback_data=f"otp_btn_edit_{i}")),
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_otp_buttons"))
    
    bot.edit_message_text(
        "✏️ <b>اختر الزر للتعديل:</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("otp_btn_edit_") and not call.data.startswith("otp_btn_edit_name_") and not call.data.startswith("otp_btn_edit_url_") and not call.data.startswith("otp_btn_edit_list"))
def otp_btn_edit_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    btn_idx = int(call.data.replace("otp_btn_edit_", ""))
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    if btn_idx >= len(OTP_BUTTONS):
        bot.answer_callback_query(call.id, "❌ الزر غير موجود!", show_alert=True)
        return
    
    btn = OTP_BUTTONS[btn_idx]
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f"otp_btn_edit_name_{btn_idx}"),
        InlineKeyboardButton("🔗 تغيير الرابط", callback_data=f"otp_btn_edit_url_{btn_idx}")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="otp_btn_edit_list"))
    
    bot.edit_message_text(
        f"✏️ <b>تعديل الزر:</b>\n\n"
        f"📝 <b>الاسم:</b> {btn['name']}\n"
        f"🔗 <b>الرابط:</b> <code>{btn['url']}</code>\n\n"
        f"اختر ما تريد تعديله:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("otp_btn_edit_name_"))
def otp_btn_edit_name_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    btn_idx = int(call.data.replace("otp_btn_edit_name_", ""))
    user_states[user_id] = {"action": "otp_btn_edit_name", "btn_idx": btn_idx}
    
    bot.send_message(
        call.message.chat.id,
        "✏️ أرسل الاسم الجديد للزر:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("otp_btn_edit_url_"))
def otp_btn_edit_url_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    btn_idx = int(call.data.replace("otp_btn_edit_url_", ""))
    user_states[user_id] = {"action": "otp_btn_edit_url", "btn_idx": btn_idx}
    
    bot.send_message(
        call.message.chat.id,
        "🔗 أرسل الرابط الجديد للزر:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "otp_btn_delete_list")
def otp_btn_delete_list_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    if not OTP_BUTTONS:
        bot.answer_callback_query(call.id, "❌ لا توجد أزرار للحذف!", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for i, btn in enumerate(OTP_BUTTONS):
        markup.add(InlineKeyboardButton(f"🗑 {btn['name']}", callback_data=f"otp_btn_delete_{i}")),
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_otp_buttons"))
    
    bot.edit_message_text(
        "🗑 <b>اختر الزر للحذف:</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("otp_btn_delete_") and not call.data.startswith("otp_btn_delete_list"))
def otp_btn_delete_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    btn_idx = int(call.data.replace("otp_btn_delete_", ""))
    global OTP_BUTTONS
    OTP_BUTTONS = load_otp_buttons()
    
    if btn_idx >= len(OTP_BUTTONS):
        bot.answer_callback_query(call.id, "❌ الزر غير موجود!", show_alert=True)
        return
    
    deleted_btn = OTP_BUTTONS.pop(btn_idx)
    save_otp_buttons(OTP_BUTTONS)
    
    bot.answer_callback_query(call.id, f"✅ تم حذف الزر: {deleted_btn['name']}", show_alert=True)
    
    text = "🔘 <b>إعدادات أزرار رسالة OTP</b>\n\n"
    if OTP_BUTTONS:
        for i, btn in enumerate(OTP_BUTTONS, 1):
            text += f"{i}. <b>{btn['name']}</b>\n   🔗 <code>{btn['url']}</code>\n\n"
    else:
        text += "لا توجد أزرار مضافة\n\n"
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ إضافة زر جديد", callback_data="otp_btn_add"),
        InlineKeyboardButton("✏️ تعديل زر", callback_data="otp_btn_edit_list"),
        InlineKeyboardButton("🗑 حذف زر", callback_data="otp_btn_delete_list")
    )
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_balance")
def withdraw_balance_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    settings = load_referral_settings()
    min_withdrawal = settings.get("min_withdrawal", 10.0)
    
    msg_text = (
        "═══《 <tg-emoji emoji-id='5332600543963522398'>▪️</tg-emoji> WITHDRAW 》═══\n\n"
        "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> Insufficient balance!\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your balance: {balance:.3f} USD\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Minimum required: {min_withdrawal} USD\n\n"
        "Earn more by referring friends!"
    )
    
    markup = InlineKeyboardMarkup()
    back_text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    markup.add(InlineKeyboardButton(back_text, callback_data="my_account"))
    
    bot.edit_message_text(
        msg_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_method_"))
def withdraw_method_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    method_key = call.data.replace("wd_method_", "")
    
    methods = load_withdrawal_methods()
    method_data = methods.get(method_key, {})
    
    if not method_data.get("enabled", True):
        msg = "❌ طريقة السحب هذه غير متاحة حالياً" if lang == "ar" else "❌ This withdrawal method is not available"
        bot.answer_callback_query(call.id, msg, show_alert=True)
        return
    
    method_name = method_data.get(f"name_{lang}", method_data.get("name_en", method_key))
    details_prompt = method_data.get(f"details_{lang}", method_data.get("details_en", "Account details"))
    
    user_states[user_id] = {"action": "withdraw_details", "method": method_name, "method_key": method_key}
    
    if lang == "ar":
        text = f"📝 أرسل <b>{details_prompt}</b> الخاص بك لـ {method_name}:"
    else:
        text = f"📝 Send your <b>{details_prompt}</b> for {method_name}:"
    
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_admins_menu")
def admin_admins_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔧 إضافة مشرف", callback_data="admin_add_admin"),
        InlineKeyboardButton("🗑 حذف مشرف", callback_data="admin_remove_admin")
    )
    markup.add(
        InlineKeyboardButton("Ban User", callback_data="admin_ban_user",    icon_custom_emoji_id="6087133294648890399"),
        InlineKeyboardButton("✅ إلغاء حظر", callback_data="admin_unban_user")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "👥 <b>إدارة المشرفين والمستخدمين</b>\n\nاختر الإجراء المطلوب:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_channels_menu")
def admin_channels_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_channel"),
        InlineKeyboardButton("🗑 حذف قناة", callback_data="admin_remove_channel")
    )
    markup.add(
        InlineKeyboardButton("📊 القنوات المضافة", callback_data="admin_list_channels")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "📢 <b>إدارة القنوات</b>\n\nاختر الإجراء المطلوب:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_countries_menu")
def admin_countries_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ إضافة دولة", callback_data="admin_add_country"),
        InlineKeyboardButton("➖ حذف دولة", callback_data="admin_remove_country")
    )
    markup.add(
        InlineKeyboardButton("📋 الدول المتاحة", callback_data="admin_list_countries")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "🌍 <b>إدارة الدول</b>\n\nاختر الإجراء المطلوب:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_groups_menu")
def admin_groups_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ إضافة جروب", callback_data="admin_add_group_start"),
        InlineKeyboardButton("➖ حذف جروب", callback_data="admin_remove_group")
    )
    markup.add(
        InlineKeyboardButton("📋 عرض الجروبات", callback_data="admin_list_groups")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "📱 <b>إدارة الجروبات</b>\n\nاختر الإجراء المطلوب:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "ws_checker_off")
def ws_checker_off_callback(call):
    bot.answer_callback_query(call.id, "Cheaker unavailable. Please try again later.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "wallet_withdraw_btn")
def wallet_withdraw_callback(call):
    user_id = call.from_user.id
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    settings = load_referral_settings()
    min_withdrawal = settings.get("min_withdrawal", 10.0)
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Back", callback_data="back_to_wallet", style="success", icon_custom_emoji_id="5994442901059276913"))
    msg_text = (
        "═════《 <tg-emoji emoji-id='6001287064589439895'>▪️</tg-emoji> WITHDRAW 》═════\n\n"
        "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> Insufficient balance!\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your balance: {balance:.3f} USD\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Minimum required: {min_withdrawal} USD\n\n"
        "Earn more by referring friends!"
    )
    try: bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "back_to_wallet")
def back_to_wallet_callback(call):
    user_id = call.from_user.id
    referral_data = get_user_referral_data(user_id)
    referral_settings = load_referral_settings()
    balance = referral_data.get("balance", 0.0)
    lifetime_earn = referral_data.get("lifetime_earn", balance)
    withdrawn = referral_data.get("withdrawn", 0.0)
    min_withdrawal = referral_settings.get("min_withdrawal", 0.1)
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Withdraw", callback_data="wallet_withdraw_btn", style="primary", icon_custom_emoji_id="6001287064589439895"))
    wallet_msg = (
        "---------------------------------------------\n"
        "         <tg-emoji emoji-id='6001287064589439895'>▪️</tg-emoji> MY WALLET\n"
        "---------------------------------------------\n\n"
        "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> My Balance: " + f"{balance}" + " USD\n"
        "<tg-emoji emoji-id='6032808241891644148'>▪️</tg-emoji> Lifetime Earn: " + f"{lifetime_earn}" + " USD\n\n"
        "<tg-emoji emoji-id='6028584717081645421'>▪️</tg-emoji> Min.Withdraw: " + f"{min_withdrawal}" + " USD\n"
        "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> Withdrawn: " + f"{withdrawn}" + " USD"
    )
    try: bot.edit_message_text(wallet_msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "mystats_referral_btn")
def mystats_referral_callback(call):
    user_id = call.from_user.id
    referral_data = get_user_referral_data(user_id)
    referral_settings = load_referral_settings()
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    referrals_count = len(referral_data.get("referrals", []))
    referral_bonus = referral_settings.get("referral_bonus", 0.005)
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Back", callback_data="back_to_mystats", style="success", icon_custom_emoji_id="5994442901059276913"))
    refer_msg = (
        "═══《 <tg-emoji emoji-id='5271604874419647061'>▪️</tg-emoji> REFER & EARN 》═══\n\n"
        "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your referral link:\n"
        f"<code>{referral_link}</code>\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Total referrals: {referrals_count}\n"
        f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Earn per referral: {referral_bonus} USD\n\n"
        "Share this link with friends to earn!"
    )
    try: bot.edit_message_text(refer_msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "mystats_history_btn")
def mystats_history_callback(call):
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Back", callback_data="back_to_mystats", style="success", icon_custom_emoji_id="5994442901059276913"))
    history_msg = "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> You have no withdrawal history yet."
    try: bot.edit_message_text(history_msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "back_to_mystats")
def back_to_mystats_callback(call):
    user_id = call.from_user.id
    referral_data = get_user_referral_data(user_id)
    balance = referral_data.get("balance", 0.0)
    referrals_count = len(referral_data.get("referrals", []))
    activations = referral_data.get("activations", 0)
    requests_count = referral_data.get("requests_count", activations)
    countries_used = len(referral_data.get("countries", []))
    join_date = referral_data.get("join_date", datetime.now().strftime("%Y-%m-%d"))
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Referral", callback_data="mystats_referral_btn", style="primary", icon_custom_emoji_id="5271604874419647061"),
        InlineKeyboardButton("History", callback_data="mystats_history_btn", style="primary", icon_custom_emoji_id="5803175856905917502")
    )
    stats_msg = (
        "-------------------------------------------\n"
        "         <tg-emoji emoji-id='5280655263865513608'>▪️</tg-emoji> MY STATS\n"
        "-------------------------------------------\n"
        "<tg-emoji emoji-id='6307589808424228455'>▪️</tg-emoji> My ID: " + f"{user_id}" + "\n"
        "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> My Balance: " + f"{balance}" + " USD\n"
        "<tg-emoji emoji-id='5332724926216428039'>▪️</tg-emoji> My Referrals: " + f"{referrals_count}" + "\n"
        "-------------------------------------------\n"
        "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Total requests: " + f"{requests_count}" + "\n"
        "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Numbers received: " + f"{activations}" + "\n"
        "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Countries used: " + f"{countries_used}" + "\n"
        "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Join Date: " + f"{join_date}"
    )
    try: bot.edit_message_text(stats_msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_group_start")
def admin_add_group_start_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("🔘 اختر جروب", request_chat=telebot.types.KeyboardButtonRequestChat(request_id=1, chat_is_channel=False)))
    
    bot.send_message(
        call.message.chat.id,
        "➕ <b>إضافة جروب جديد</b>\n\n"
        "إضغط على الزر بالأسفل لاختيار الجروب أو أرسل ID الجروب مباشرة:",
        parse_mode="HTML",
        reply_markup=markup
    )
    user_states[user_id] = {"action": "add_group"}

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("action") == "add_group", content_types=['text', 'chat_shared'])
def handle_add_group_message(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    group_id = None
    if message.content_type == 'chat_shared':
        group_id = message.chat_shared.chat_id
    else:
        text = message.text.strip()
        if text.startswith('-') and text[1:].isdigit() or text.isdigit():
            group_id = int(text)
    
    if group_id:
        if group_id not in GROUPS:
            GROUPS.append(group_id)
            save_groups()
            bot.send_message(message.chat.id, f"✅ تم إضافة الجروب بنجاح!\nID: <code>{group_id}</code>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(message.chat.id, "⚠️ هذا الجروب مضاف بالفعل.", reply_markup=ReplyKeyboardRemove())
        user_states[user_id] = {}
    else:
        bot.send_message(message.chat.id, "❌ ID غير صالح. يرجى إرسال ID صحيح أو اختيار جروب من الزر.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_group")
def admin_add_group_callback(call):
   
    admin_add_group_start_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_group")
def admin_remove_group_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    if not GROUPS:
        bot.answer_callback_query(call.id, "⚠️ لا توجد جروبات مضافة", show_alert=True)
        return
    
    groups_list = "\n".join([f"• <code>{gid}</code>" for gid in GROUPS])
    
    user_states[user_id] = {"action": "remove_group"}
    
    bot.send_message(
        call.message.chat.id,
        f"🗑 <b>حذف جروب</b>\n\n"
        f"<b>الجروبات المضافة:</b>\n{groups_list}\n\n"
        f"أرسل ID الجروب الذي تريد حذفه:",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("action") == "remove_group")
def handle_remove_group_message(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    try:
        group_id = int(message.text.strip())
        if group_id in GROUPS:
            GROUPS.remove(group_id)
            save_groups()
            bot.send_message(message.chat.id, f"✅ تم حذف الجروب <code>{group_id}</code> بنجاح!", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ هذا الجروب غير موجود في القائمة.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إرسال ID صحيح (رقم).")
    
    user_states[user_id] = {}

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_groups")
def admin_list_groups_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    if not GROUPS:
        bot.answer_callback_query(call.id, "⚠️ لا توجد جروبات مضافة", show_alert=True)
        return
    
    groups_text = "📋 <b>الجروبات المضافة:</b>\n\n"
    for idx, gid in enumerate(GROUPS, 1):
        try:
            chat = bot.get_chat(gid)
            groups_text += f"{idx}. <b>{chat.title}</b>\n"
            groups_text += f"   🆔 <code>{gid}</code>\n\n"
        except:
            groups_text += f"{idx}. جروب غير معروف\n"
            groups_text += f"   🆔 <code>{gid}</code>\n\n"
    
    bot.send_message(call.message.chat.id, groups_text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_menu")
def admin_broadcast_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(" Broadcast", callback_data="admin_broadcast_normal", style="primary",    icon_custom_emoji_id="6217507701228834325"),
        InlineKeyboardButton(" Forward Broadcast", callback_data="admin_broadcast_forward", style="primary",    icon_custom_emoji_id="5042334757040423886")
    )
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "<tg-emoji emoji-id='6217507701228834325'>◾</tg-emoji> <b>Broadcast System</b>\n\n"
        "Choose the broadcast type:\n\n"
        "• <b>Broadcast:</b> A new message for every user.\n"
        "• <b>Forward Broadcast:</b> Forward your message.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_normal")
def admin_broadcast_normal_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    broadcast_state[user_id] = {"type": "normal", "step": "waiting_message"}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Back", callback_data="cancel_broadcast", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='6217507701228834325'>◾</tg-emoji> <b>Broadcast</b>\n\nSend the message", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_forward")
def admin_broadcast_forward_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    broadcast_state[user_id] = {"type": "forward", "step": "waiting_message"}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Back", callback_data="cancel_broadcast", style="success", icon_custom_emoji_id="5994442901059276913"))
    bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='5042334757040423886'>◾</tg-emoji> <b>Forward Broadcast</b>\n\nSenf your message", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.from_user.id in broadcast_state and broadcast_state[msg.from_user.id].get("step") == "waiting_message", content_types=["text", "photo", "video", "document"])
def handle_broadcast_message(msg):
    user_id = msg.from_user.id
    state = broadcast_state[user_id]
    state["step"] = "confirm"
    state["message"] = msg
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Sent", callback_data="confirm_broadcast",    icon_custom_emoji_id="5039844895779455925"), InlineKeyboardButton("Cancel", callback_data="cancel_broadcast",    icon_custom_emoji_id="5039671744172917707" ))
    bot.reply_to(msg, "<tg-emoji emoji-id='5042094496569885750'>◾</tg-emoji> <b>Are you sure do you want to sent it</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_broadcast")
def confirm_broadcast_callback(call):
    user_id = call.from_user.id
    if user_id not in broadcast_state: return
    state = broadcast_state[user_id]
    msg = state["message"]
    success, failed = 0, 0
    progress = bot.send_message(call.message.chat.id ,"Please Wait <tg-emoji emoji-id='5386367538735104399'>◾</tg-emoji>")
    for uid in list(USERS.keys()):
        try:
            if state["type"] == "forward":
                bot.forward_message(int(uid), msg.chat.id, msg.message_id)
            else:
                bot.copy_message(int(uid), msg.chat.id, msg.message_id)
            success += 1
        except: failed += 1
    bot.delete_message(progress.chat.id, progress.message_id)
    bot.send_message(call.message.chat.id, f"<tg-emoji emoji-id='5039844895779455925'>◾</tg-emoji> <b>Sent!</b>\n\n<tg-emoji emoji-id='5042290883949495533'>◾</tg-emoji> Success: {success}\n<tg-emoji emoji-id='5040042498634810056'>◾</tg-emoji> Failed: {failed}", parse_mode="HTML")
    del broadcast_state[user_id]

def send_saved_message(target_bot, target_uid, saved_msg):
    
    content_type = saved_msg.get("content_type")
    
    if content_type == "text":
        target_bot.send_message(target_uid, saved_msg.get("text"), parse_mode="HTML" if saved_msg.get("has_entities") else None)
    elif content_type == "photo":
        target_bot.send_photo(target_uid, saved_msg.get("file_id"), caption=saved_msg.get("caption"))
    elif content_type == "video":
        target_bot.send_video(target_uid, saved_msg.get("file_id"), caption=saved_msg.get("caption"))
    elif content_type == "document":
        target_bot.send_document(target_uid, saved_msg.get("file_id"), caption=saved_msg.get("caption"))
    elif content_type == "audio":
        target_bot.send_audio(target_uid, saved_msg.get("file_id"), caption=saved_msg.get("caption"))
    elif content_type == "voice":
        target_bot.send_voice(target_uid, saved_msg.get("file_id"), caption=saved_msg.get("caption"))
    elif content_type == "sticker":
        target_bot.send_sticker(target_uid, saved_msg.get("file_id"))

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)
    settings = load_referral_settings()
    code_bonus = settings.get("code_bonus", 0.01)
    
    markup = get_country_buttons(user_id)
    if markup:
        if lang == "ar":
            title = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        else:
            title = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        
        try:
            bot.edit_message_text(
                title,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except:
            pass
    else:
        try:
            text = t(user_id, "welcome")
            if not text: text = "🌐 <b>مرحباً بك!</b>"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=get_main_menu_lang(user_id)
            )
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_country")
def admin_add_country_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    user_states[user_id] = {"action": "na_add_country_file"}

    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='5197269100878907942'>◾</tg-emoji> <b>Add a New Country – Step 1/3</b>\n\n"
        "<tg-emoji emoji-id='5422439311196834318'>◾</tg-emoji> Please upload the numbers file (.txt)\n\n"
        "<i>The file will be cleaned automatically, and only phone numbers will be extracted from each line.</i>",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_country")
def admin_remove_country_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    if not COUNTRIES:
        bot.answer_callback_query(call.id, "You Don't add any country ❌", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    for cid in sorted(COUNTRIES.keys()):
        info = COUNTRIES[cid]
        cname = info.get("display_name", cid)
        flag = info.get("flag", "🌍")
        count = info.get("numbers_count", 0)
        
        emoji_id = extract_tg_emoji_id(flag)
        
        if emoji_id:
            markup.add(InlineKeyboardButton(f" {cname} ({count})", callback_data=f"delete_country_btn_{cid}", icon_custom_emoji_id=emoji_id))
        else:
            markup.add(InlineKeyboardButton(f" {flag} {cname} ({count})", callback_data=f"delete_country_btn_{cid}"))
    
    markup.add(InlineKeyboardButton("Back", callback_data="admin_panel", style="success", icon_custom_emoji_id="5994442901059276913"))
    
    bot.edit_message_text(
        "<tg-emoji emoji-id='6206108815075579644'>◾</tg-emoji> <b>Deleate Country</b>\n\n Choose Country:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_country_btn_"))
def delete_country_confirm_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    
    country_name = call.data.replace("delete_country_btn_", "")
    if country_name in COUNTRIES:
        
        file_path = COUNTRIES[country_name].get("file")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        del COUNTRIES[country_name]
        save_countries()
        bot.answer_callback_query(call.id, f"✅ تم حذف {country_name} بنجاح!", show_alert=True)
        
        admin_remove_country_callback(call)
    else:
        bot.answer_callback_query(call.id, "This Country Already be deleated ✅", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_countries")
def admin_list_countries_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    if not COUNTRIES:
        bot.answer_callback_query(call.id, "⚠️ لا توجد دول مضافة حالياً", show_alert=True)
        return

    countries_text = "📋 <b>الدول المتاحة:</b>\n\n"
    for cid, info in COUNTRIES.items():
        cname = info.get("display_name", cid)
        countries_text += f"🌍 <b>{cname}</b> {info.get('flag', '🌐')}\n"
        countries_text += f"   🆔 المعرف: <code>{cid}</code>\n"
        countries_text += f"   📊 الأرقام: {info.get('numbers_count', 0)}\n"
        countries_text += f"   ⚙️ الخدمة: {info.get('service', 'N/A')}\n"
        countries_text += f"   📄 الملف: {info.get('file', 'N/A')}\n"
        if info.get('server'):
            countries_text += f"   🖥️ السيرفر: {info.get('server')}\n"
        if info.get('platforms'):
            countries_text += f"   📱 المنصات: {', '.join(info.get('platforms', []))}\n"
        countries_text += "\n"

    bot.send_message(call.message.chat.id, countries_text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_country_srv_"))
def add_country_server_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    if user_id not in user_states or user_states[user_id].get("action") != "add_country_server":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    server = call.data.replace("add_country_srv_", "")
    state = user_states[user_id]
    
    user_states[user_id] = {
        "action": "add_country_platforms",
        "temp_file": state.get("temp_file"),
        "country_code": state.get("country_code"),
        "country_name": state.get("country_name"),
        "num_cleaned": state.get("num_cleaned"),
        "server": server,
        "selected_platforms": []
    }
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("<tg-emoji emoji-id='5269427536453984598'>📘</tg-emoji> Facebook", callback_data="add_country_plt_Facebook", icon_custom_emoji_id="5382322671679708881", style="primary"),
        InlineKeyboardButton("<tg-emoji emoji-id='5271536803482981220'>💬</tg-emoji> WhatsApp", callback_data="add_country_plt_WhatsApp", icon_custom_emoji_id="5381990043642502553", style="primary")
    )
    markup.add(
        InlineKeyboardButton("<tg-emoji emoji-id='5271801931814165886'>✈️</tg-emoji> Telegram", callback_data="add_country_plt_Telegram", icon_custom_emoji_id="5381879959335738545", style="primary"),
        InlineKeyboardButton("<tg-emoji emoji-id='5269682734820777950'>📸</tg-emoji> Instagram", callback_data="add_country_plt_Instagram", icon_custom_emoji_id="5382054253403577563", style="primary")
    )
    markup.add(
        InlineKeyboardButton("Twitter/X", callback_data="add_country_plt_Twitter", icon_custom_emoji_id="5391197405553107640", style="primary"),
        InlineKeyboardButton("TikTok", callback_data="add_country_plt_TikTok", icon_custom_emoji_id="5390966190283694453", style="primary")
    )
    markup.add(
        InlineKeyboardButton("Discord", callback_data="add_country_plt_Discord", icon_custom_emoji_id="5382132232829804982", style="primary"),
        InlineKeyboardButton("Gmail", callback_data="add_country_plt_Gmail", icon_custom_emoji_id="5391038994274329680", style="primary")
    )
    markup.add(
        InlineKeyboardButton("🌐 All Platforms", callback_data="add_country_plt_ALL")
    )
    markup.add(InlineKeyboardButton("✅ Confirm & Finish", callback_data="add_country_finish")),
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_countries"))
    
    server_names = {
        "GROUP": "🏢 GROUP",
        "Fly sms": "🔷 Fly sms",
        "Number_Panel": "📱 Number Panel",
        "Bolt": "⚡ Bolt",
        "iVASMS": "🌐 iVASMS",
        "IMO": "📱 IMO"
    }
    
    bot.edit_message_text(
        f"✅ <b>الخطوة 5/5 - اختيار المنصات</b>\n\n"
        f"🌍 Country: <b>{state.get('country_name')}</b>\n"
        f"🔢 Country Code: <b>{state.get('country_code')}</b>\n"
        f"🖥️ السيرفر: <b>{server_names.get(server, server)}</b>\n\n"
        f"📱 <b>Selected Platforms:</b> None\n\n"
        f"Choose the platforms these numbers work on:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_country_plt_"))
def add_country_platform_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    if user_id not in user_states or user_states[user_id].get("action") != "add_country_platforms":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    platform = call.data.replace("add_country_plt_", "")
    state = user_states[user_id]
    selected_platforms = state.get("selected_platforms", [])
    
    if platform == "ALL":
        selected_platforms = ["Facebook", "WhatsApp", "Telegram", "Instagram", "Twitter", "TikTok", "Discord", "Gmail"]
    elif platform in selected_platforms:
        selected_platforms.remove(platform)
    else:
        selected_platforms.append(platform)
    
    user_states[user_id]["selected_platforms"] = selected_platforms
    
    platform_icons = {
        "Facebook": "<tg-emoji emoji-id='5269427536453984598'>📘</tg-emoji>", "WhatsApp": "<tg-emoji emoji-id='5271536803482981220'>💬</tg-emoji>", "Telegram": "<tg-emoji emoji-id='5271801931814165886'>✈️</tg-emoji>",
        "Instagram": "<tg-emoji emoji-id='5269682734820777950'>📸</tg-emoji>", "Twitter": "", "TikTok": "",
        "Discord": "", "Gmail": "", "IMO": ""
    }
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    def get_btn_text(name, icon):
        check = "✅" if name in selected_platforms else ""
        return f"{check} {icon} {name}"
    
    markup.add(
        InlineKeyboardButton(get_btn_text("Facebook", ""), callback_data="add_country_plt_Facebook", icon_custom_emoji_id="5382322671679708881"),
        InlineKeyboardButton(get_btn_text("WhatsApp", ""), callback_data="add_country_plt_WhatsApp", icon_custom_emoji_id="5381990043642502553")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Telegram", ""), callback_data="add_country_plt_Telegram", icon_custom_emoji_id="5381879959335738545"),
        InlineKeyboardButton(get_btn_text("Instagram", ""), callback_data="add_country_plt_Instagram", icon_custom_emoji_id="5382054253403577563")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Twitter", ""), callback_data="add_country_plt_Twitter", icon_custom_emoji_id="5391197405553107640"),
        InlineKeyboardButton(get_btn_text("TikTok", ""), callback_data="add_country_plt_TikTok", icon_custom_emoji_id="5390966190283694453")
    )
    markup.add(
        InlineKeyboardButton(get_btn_text("Discord", ""), callback_data="add_country_plt_Discord", icon_custom_emoji_id="5382132232829804982"),
        InlineKeyboardButton(get_btn_text("Gmail", ""), callback_data="add_country_plt_Gmail", icon_custom_emoji_id="5391038994274329680"),
        InlineKeyboardButton(get_btn_text("IMO", ""), callback_data="add_country_plt_IMO")
    )
    markup.add(
        InlineKeyboardButton("🌐 All Platforms", callback_data="add_country_plt_ALL")
    )
    markup.add(InlineKeyboardButton("✅ Confirm & Finish", callback_data="add_country_finish")),
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_countries"))
    
    server_names = {
        "GROUP": "🏢 GROUP",
        "Fly sms": "🔷 Fly sms",
        "Number_Panel": "📱 Number Panel",
        "Bolt": "⚡ Bolt",
        "iVASMS": "🌐 iVASMS",
        "IMO": "📱 IMO"
    }
    
   
    platform_icons = {
        "Facebook": "<tg-emoji emoji-id='5269427536453984598'>📘</tg-emoji>", "WhatsApp": "<tg-emoji emoji-id='5271536803482981220'>💬</tg-emoji>", "Telegram": "<tg-emoji emoji-id='5271801931814165886'>✈️</tg-emoji>",
        "Instagram": "<tg-emoji emoji-id='5269682734820777950'>📸</tg-emoji>", "Twitter": "", "TikTok": "",
        "Discord": "", "Gmail": "", "IMO": ""
    }
    
    platforms_text = ", ".join([f"{platform_icons.get(p, '📱')} {p}" for p in selected_platforms]) if selected_platforms else "لا يوجد"
    
    try:
        bot.edit_message_text(
            f"✅ <b>الخطوة 5/5 - اختيار المنصات</b>\n\n"
            f"🌍 Country: <b>{state.get('country_name')}</b>\n"
            f"🔢 Country Code: <b>{state.get('country_code')}</b>\n"
            f"🖥️ السيرفر: <b>{server_names.get(state.get('server'), state.get('server'))}</b>\n\n"
            f"📱 <b>Selected Platforms:</b> {platforms_text}\n\n"
            f"Choose the platforms these numbers work on:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except:
        pass
    
    bot.answer_callback_query(call.id)

def format_otp_message(number, sms_text, service_name="[TG]", otp_code=None, user_id=None, is_group=False):
    country_name, flag, region_code = detect_country_from_number(number, user_id)
    masked = mask_number(number)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
   
    service_upper = str(service_name).replace("[", "").replace("]", "").upper()
    shorthand = service_upper
    
    if is_group:
        SHORTHANDS = {
            "WHATSAPP": "<tg-emoji emoji-id='5334998226636390258'>📞</tg-emoji>",
            "TELEGRAM": "TG",
            "FACEBOOK": "FB",
            "INSTAGRAM": "IG",
            "TIKTOK": "TK",
            "TWITTER": "TW",
            "GOOGLE": "GG",
            "MICROSOFT": "MS",
            "NETFLIX": "NF",
            "STEAM": "ST",
            "SNAPCHAT": "SC",
            "VIBER": "VB",
            "IMO": "IM",
            "WECHAT": "WC",
            "LINE": "LN",
            "DISCORD": "DC",
            "PAYPAL": "PP",
            "AMAZON": "AZ",
            "EBAY": "EB",
            "APPLE": "AP"
        }

        for key, val in SHORTHANDS.items():
            if key in service_upper:
                shorthand = val
                break
                
        if shorthand == service_upper and len(shorthand) > 3:
            shorthand = shorthand[:2]
        
    service_display = f"[{shorthand}]"
    
    header = f"↠ {flag} #{region_code} {service_name} {masked}  ┨<tg-emoji emoji-id='5122933683820430249'>⚡</tg-emoji>"
    
    body = f"<blockquote>{sms_text}</blockquote>"
    time_footer = f"<blockquote>• ⏰ ~ {now_str}</blockquote>"
    
    return f"{header}\n{body}\n{time_footer}"

@bot.callback_query_handler(func=lambda call: call.data == "add_country_finish")
def add_country_finish_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    if user_id not in user_states or user_states[user_id].get("action") != "add_country_platforms":
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        return
    
    state = user_states[user_id]
    temp_file = state.get("temp_file")
    server = state.get("server")
    selected_platforms = state.get("selected_platforms", ["WhatsApp"])
    
    bot.edit_message_text("🔍 جاري فحص الملف وتحديد الدولة تلقائياً...", call.message.chat.id, call.message.message_id)
    
    prefix = detect_country_code_from_file(temp_file)
    if not prefix:
        bot.send_message(call.message.chat.id, "❌ لم أتمكن من تحديد رمز الدولة من الملف.")
        return

    country_name, flag, region_code = detect_country_from_number(prefix)
    count, total, rejected = clean_and_filter_numbers(temp_file, prefix)
    
    if count == 0:
        bot.send_message(call.message.chat.id, f"❌ الملف لا يحتوي على أرقام تبدأ بـ +{prefix}")
        return

    final_country_name = country_name
    if region_code == "EG": final_country_name = "مصر"
    
    final_filename = f"numbers_{prefix}_{uuid.uuid4().hex[:8]}.txt"
    if os.path.exists(temp_file):
        os.rename(temp_file, final_filename)

    
    unique_id = uuid.uuid4().hex[:12]
    country_id = f"{final_country_name}_{unique_id}"
    
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"numbers_{prefix}_{timestamp_str}_{unique_id}.txt"
    
    if os.path.exists(temp_file):
        
        while os.path.exists(final_filename):
            unique_id = uuid.uuid4().hex[:12]
            final_filename = f"numbers_{prefix}_{timestamp_str}_{unique_id}.txt"
            country_id = f"{final_country_name}_{unique_id}"
            
        os.rename(temp_file, final_filename)
        print(f"✅ تم حفظ الملف باسم فريد: {final_filename}")

    COUNTRIES[country_id] = {
        "display_name": final_country_name,
        "file": final_filename,
        "code": prefix,
        "flag": flag,
        "server": server,
        "platforms": selected_platforms,
        "numbers_count": count,
        "added_by": user_id,
        "added_at": datetime.now().isoformat()
    }
    
   
    with open(COUNTRIES_FILE, "w", encoding="utf-8") as f:
        json.dump(COUNTRIES, f, indent=2, ensure_ascii=False)
    
    del user_states[user_id]
    bot.send_message(
        call.message.chat.id,
        f"✅ <b>تم إضافة الدولة بنجاح!</b>\n\n"
        f"🌍 Country: {flag} {final_country_name} (#{region_code})\n"
        f"🔢 الرمز: +{prefix}\n"
        f"📱 العدد: {count} رقم\n"
        f"🖥 السيرفر: {server}\n"
        f"✨ تم التحديد تلقائياً من محتوى الملف",
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_add_channel")
def admin_add_channel_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    user_states[user_id] = {"action": "add_channel"}

    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji><b>Add New channel</b>\n\n"
        "Send link channel or user\n\n"
        "Like:\n\n"
        "<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <code>@ME_YT1</code>\n"
        "<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <code>https://t.me/ME_YT1</code>\n"
        "<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> <code>-1003243441645</code> (ID)\n\n"
        "bot should be admin in a channel",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_channel")
def admin_remove_channel_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    if not CHANNELS:
        bot.answer_callback_query(call.id, "You don't add any channel 💡ً", show_alert=True)
        return

    channels_list = "\n".join([f"{idx+1} <tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> — {ch['name']} ({ch['username']})" for idx, ch in enumerate(CHANNELS)])

    user_states[user_id] = {"action": "remove_channel"}

    bot.send_message(
        call.message.chat.id,
        f"<b>Deleate channel</b><tg-emoji emoji-id='6206108815075579644'>🗑</tg-emoji>\n\n"
        f"{channels_list}\n\n"
        f"Send channel number to deleate it .",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_channels")
def admin_list_channels_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    if not CHANNELS:
        bot.answer_callback_query(call.id, "You don't add any channel 💡", show_alert=True)
        return

    channels_text = "📊 <b>القنوات المضافة:</b>\n\n"
    for idx, ch in enumerate(CHANNELS, 1):
        channels_text += f"{idx}. 📢 <b>{ch['name']}</b>\n"
        channels_text += f"   🔗 {ch['username']}\n"
        channels_text += f"   🆔 ID: <code>{ch['id']}</code>\n\n"

    bot.send_message(call.message.chat.id, channels_text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_admin")
def admin_add_admin_callback(call):
    user_id = call.from_user.id
    if user_id != MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ عذراً، المالك فقط يمكنه إضافة مشرفين!", show_alert=True)
        return
    user_states[user_id] = {"action": "add_admin"}
    bot.send_message(call.message.chat.id, "<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji><b>Add new admin</b>\n\nSend (User ID) To ne admin", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_admin")
def admin_remove_admin_callback(call):
    user_id = call.from_user.id
    if user_id != MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ only owner can remove admins", show_alert=True)
        return
    
    admins_list = ""
    for aid in ADMINS:
        status = "( OWNER )" if aid == MAIN_ADMIN_ID else ""
        admins_list += f"• <code>{aid}</code>{status}\n"
    
    user_states[user_id] = {"action": "remove_admin"}
    bot.send_message(
        call.message.chat.id, 
        f"<tg-emoji emoji-id='6206108815075579644'>◾</tg-emoji> <b>Deleate Admine</b>\n\n<tg-emoji emoji-id='5197269100878907942'>◾</tg-emoji> <b>Admins:</b>\n{admins_list}\n\nSend the person ID", 
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban_user")
def admin_ban_user_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    user_states[user_id] = {"action": "ban_user"}

    bot.send_message(
        call.message.chat.id,
        "<tg-emoji emoji-id='6129840374971112593'>◾</tg-emoji> <b>Ban User</b>\n\n"
        "Send user ID:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_unban_user")
def admin_unban_user_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    if not BANNED:
        bot.answer_callback_query(call.id, "Not found ane ban user ✅", show_alert=True)
        return

    banned_list = "\n".join([f"• <code>{uid}</code>" for uid in BANNED])

    user_states[user_id] = {"action": "unban_user"}

    bot.send_message(
        call.message.chat.id,
        f"<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji> <b>un ban user</b>\n\n"
        f"<b>The banned accounts:</b>\n{banned_list}\n\n"
        f"Send User ID:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_otp_group")
def admin_set_otp_group_callback(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        return

    user_states[user_id] = {"action": "set_otp_group"}

    bot.send_message(
        call.message.chat.id,
        "📬 <b>تعيين مجموعة OTP</b>\n\n"
        "أرسل ID المجموعة التي سيتم إرسال رسائل OTP إليها:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_accounts_menu")
def admin_accounts_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك بالوصول", show_alert=True)
        return
    
    bot.edit_message_text(
        "<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji> <b>Manage — Account</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=get_accounts_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("accounts_site_"))
def accounts_site_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    site_key = call.data.replace("accounts_site_", "")
    site_name = SETTINGS[site_key]["name"]
    accounts = get_site_accounts(site_key)
    
    accounts_text = f"👥 <b>حسابات {site_name}</b>\n\n"
    if accounts:
        accounts_text += f"📊 عدد الحسابات: {len(accounts)}\n\n"
        for idx, account in enumerate(accounts, 1):
            username = account.get("username") or account.get("api_token", "N/A")
            if len(username) > 20:
                username = username[:15] + "..."
            accounts_text += f"{idx}. 👤 <code>{username}</code>\n"
    else:
        accounts_text += "⚠️ لا توجد حسابات مضافة\n"
    
    accounts_text += "\nاختر حساباً لعرض تفاصيله أو أضف حساباً جديداً:"
    
    bot.edit_message_text(
        accounts_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=get_site_accounts_menu(site_key)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_account_"))
def view_account_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = call.data.replace("view_account_", "")
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    
    site_key, account_id = parts[0], parts[1]
    account = get_account_by_id(site_key, account_id)
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    site_name = SETTINGS[site_key]["name"]
    full_id = account.get("id", "")
    username_or_token = account.get("username") or account.get("api_token", "N/A")
    
    account_text = (
        f"👤 <b>تفاصيل الحساب - {site_name}</b>\n\n"
    )
    
    if site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS"]:
        account_text += f"🔐 <b>API Token:</b> <code>{username_or_token[:15]}...</code>\n"
    else:
        account_text += f"📛 <b>اليوزر:</b> <code>{username_or_token}</code>\n"
        account_text += f"🔑 <b>الباسورد:</b> <code>{account.get('password', 'N/A')}</code>\n"
    
    account_text += f"🆔 <b>ID:</b> <code>{full_id[:8]}...</code>\n"
    
    bot.edit_message_text(
        account_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=get_account_details_menu(site_key, full_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_account_"))
def add_account_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    site_key = call.data.replace("add_account_", "")
    site_name = SETTINGS[site_key]["name"]
    
    if site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS"]:
        user_states[user_id] = {"action": "add_account_api_token", "site_key": site_key}
        bot.send_message(
            call.message.chat.id,
            f"➕ <b>إضافة حساب جديد - {site_name}</b>\n\n"
            f"📝 أرسل مفتاح API (API Token):",
            parse_mode="HTML"
        )
    else:
        user_states[user_id] = {"action": "add_account_username", "site_key": site_key}
        bot.send_message(
            call.message.chat.id,
            f"➕ <b>إضافة حساب جديد - {site_name}</b>\n\n"
            f"📝 الخطوة 1/2: أرسل اسم المستخدم (Username):",
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_account_"))
def delete_account_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = call.data.replace("delete_account_", "")
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    
    site_key, account_id = parts[0], parts[1]
    site_name = SETTINGS[site_key]["name"]
    account = get_account_by_id(site_key, account_id)
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    accounts = get_site_accounts(site_key)
    if len(accounts) <= 1:
        bot.answer_callback_query(
            call.id, 
            "⚠️ لا يمكن حذف الحساب الوحيد!\nيجب أن يبقى حساب واحد على الأقل لكل موقع.", 
            show_alert=True
        )
        return
    
    username_or_token = account.get("username") or account.get("api_token", "N/A")
    full_id = account.get("id", "")
    success = delete_account(site_key, full_id)
    
    if success:
        bot.answer_callback_query(call.id, f"✅ تم حذف الحساب {username_or_token[:15]}... بنجاح!", show_alert=True)
        
        accounts = get_site_accounts(site_key)
        accounts_text = f"👥 <b>حسابات {site_name}</b>\n\n"
        accounts_text += f"📊 عدد الحسابات: {len(accounts)}\n\n"
        for idx, acc in enumerate(accounts, 1):
            uname = acc.get("username") or acc.get("api_token", "N/A")
            if len(uname) > 20:
                uname = uname[:15] + "..."
            accounts_text += f"{idx}. 👤 <code>{uname}</code>\n"
        accounts_text += "\nاختر حساباً لعرض تفاصيله أو أضف حساباً جديداً:"
        
        bot.edit_message_text(
            accounts_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_site_accounts_menu(site_key)
        )
    else:
        bot.answer_callback_query(call.id, "❌ فشل حذف الحساب", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "admin_sites_menu" or call.data == "admin")
def sites_menu_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔️ غير مصرح لك بالوصول", show_alert=True)
        return
    
    if call.data == "admin":
        bot.edit_message_text(
            "Welcome to admin panel <tg-emoji emoji-id='5422439311196834318'>💡</tg-emoji>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
    else:
        bot.edit_message_text(
            "<tg-emoji emoji-id='5390854796011906616'>◾</tg-emoji>️ <b>Web — Setting</b>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_sites_menu()
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_config_"))
def site_config_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    site_key = call.data.replace("site_config_", "")
    site_config = SETTINGS.get(site_key, {})
    site_name = site_config.get("name", site_key)
    accounts = get_site_accounts(site_key)
    
    if len(accounts) > 1:
        accounts_text = f"⚙️ <b>إعدادات {site_name}</b>\n\n"
        accounts_text += f"👥 <b>عدد الحسابات:</b> {len(accounts)}\n\n"
        accounts_text += "اختر الحساب الذي تريد التحكم فيه:"
        
        bot.edit_message_text(
            accounts_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_site_accounts_selection_menu(site_key)
        )
    else:
        first_account = accounts[0] if accounts else {"username": "N/A", "password": "", "id": ""}
        account_id = first_account.get("id", "")
        username_or_token = first_account.get("username") or first_account.get("api_token", "N/A")
        
        info_text = (
            f"⚙️ <b>إعدادات {site_name}</b>\n\n"
        )
        if site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS"]:
            info_text += f"🔐 <b>API Token:</b> <code>{username_or_token[:15]}...</code>\n"
        else:
            info_text += f"👤 <b>الحساب:</b> <code>{username_or_token}</code>\n"
            info_text += f"🔑 <b>الباسورد:</b> <code>{'*' * len(first_account.get('password', ''))}</code>\n"
        info_text += f"⏱ <b>فترة البحث:</b> {site_config.get('check_interval', 0)} ثانية\n"
        info_text += f"⏳ <b>وقت الانتظار:</b> {site_config.get('timeout', 0)} ثانية\n\n"
        info_text += "اختر الإجراء المطلوب:"
        
        bot.edit_message_text(
            info_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_site_config_menu(site_key, account_id)
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_account_config_"))
def select_account_config_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = call.data.replace("select_account_config_", "")
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    
    site_key, account_id = parts[0], parts[1]
    site_config = SETTINGS.get(site_key, {})
    site_name = site_config.get("name", site_key)
    account = get_account_by_id(site_key, account_id)
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    username_or_token = account.get("username") or account.get("api_token", "N/A")
    info_text = (
        f"⚙️ <b>إعدادات {site_name}</b>\n\n"
    )
    if site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS"]:
        info_text += f"🔐 <b>API Token:</b> <code>{username_or_token[:15]}...</code>\n"
    else:
        info_text += f"👤 <b>الحساب:</b> <code>{username_or_token}</code>\n"
        info_text += f"🔑 <b>الباسورد:</b> <code>{'*' * len(account.get('password', ''))}</code>\n"
    info_text += f"⏱ <b>فترة البحث:</b> {site_config.get('check_interval', 0)} ثانية\n"
    info_text += f"⏳ <b>وقت الانتظار:</b> {site_config.get('timeout', 0)} ثانية\n\n"
    info_text += "اختر الإجراء المطلوب:"
    
    bot.edit_message_text(
        info_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=get_site_config_menu(site_key, account_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_change_user_"))
def site_change_user_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data_parts = call.data.replace("site_change_user_", "").rsplit("_", 1)
    site_key = data_parts[0]
    account_id = data_parts[1] if len(data_parts) > 1 else None

    account = get_account_by_id(site_key, account_id) if account_id else None
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    full_id = account.get("id", "")
    
    user_states[user_id] = {
        "action": "change_site_username",
        "site_key": site_key,
        "account_id": full_id
    }
    
    site_name = SETTINGS[site_key]["name"]
    bot.send_message(
        call.message.chat.id,
        f"👤 <b>تغيير اليوزر - {site_name}</b>\n\n"
        f"الحساب الحالي: <code>{account.get('username', 'N/A')}</code>\n\n"
        f"أرسل اسم المستخدم الجديد:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_change_pass_"))
def site_change_pass_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data_parts = call.data.replace("site_change_pass_", "").rsplit("_", 1)
    site_key = data_parts[0]
    account_id = data_parts[1] if len(data_parts) > 1 else None

    account = get_account_by_id(site_key, account_id) if account_id else None
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    full_id = account.get("id", "")
    
    user_states[user_id] = {
        "action": "change_site_password",
        "site_key": site_key,
        "account_id": full_id
    }
    
    site_name = SETTINGS[site_key]["name"]
    bot.send_message(
        call.message.chat.id,
        f"🔑 <b>تغيير الباسورد - {site_name}</b>\n\n"
        f"الحساب: <code>{account.get('username', 'N/A')}</code>\n\n"
        f"أرسل كلمة المرور الجديدة:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_change_token_"))
def site_change_token_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data_parts = call.data.replace("site_change_token_", "").rsplit("_", 1)
    site_key = data_parts[0]
    account_id = data_parts[1] if len(data_parts) > 1 else None

    account = get_account_by_id(site_key, account_id) if account_id else None
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    full_id = account.get("id", "")
    
    user_states[user_id] = {
        "action": "change_site_token",
        "site_key": site_key,
        "account_id": full_id
    }
    
    site_name = SETTINGS[site_key]["name"]
    bot.send_message(
        call.message.chat.id,
        f"🔐 <b>تغيير API Token - {site_name}</b>\n\n"
        f"الحساب الحالي: <code>{account.get('api_token', 'N/A')[:15]}...</code>\n\n"
        f"أرسل الـ API Token الجديد:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_change_interval_"))
def site_change_interval_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    site_key = call.data.replace("site_change_interval_", "")
    site_name = SETTINGS[site_key]["name"]
    current = SETTINGS[site_key]["check_interval"]
    
    user_states[user_id] = {"action": "change_site_interval", "site_key": site_key}
    
    bot.send_message(
        call.message.chat.id,
        f"⏱ <b>تغيير فترة البحث - {site_name}</b>\n\n"
        f"📊 الفترة الحالية: {current} ثانية\n\n"
        f"أرسل الفترة الجديدة بالثواني:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_change_timeout_"))
def site_change_timeout_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    site_key = call.data.replace("site_change_timeout_", "")
    site_name = SETTINGS[site_key]["name"]
    current = SETTINGS[site_key]["timeout"]
    
    user_states[user_id] = {"action": "change_site_timeout", "site_key": site_key}
    
    bot.send_message(
        call.message.chat.id,
        f"⏳ <b>تغيير وقت الانتظار - {site_name}</b>\n\n"
        f"📊 الوقت الحالي: {current} ثانية\n\n"
        f"أرسل الوقت الجديد بالثواني:",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_test_login_"))
def site_test_login_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data_parts = call.data.replace("site_test_login_", "").rsplit("_", 1)
    site_key = data_parts[0]
    account_id = data_parts[1] if len(data_parts) > 1 else None

    account = get_account_by_id(site_key, account_id) if account_id else None
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    username_or_token = account.get("username") or account.get("api_token", "N/A")
    bot.answer_callback_query(call.id, f"🔄 جاري اختبار تسجيل الدخول ل {username_or_token[:15]}...")
    
    site_name = SETTINGS[site_key]["name"]
    bot.send_message(
        call.message.chat.id,
        f"🔓 <b>اختبار تسجيل الدخول - {site_name}</b>\n\n"
        f"👤 الحساب: <code>{username_or_token[:15]}...</code>\n\n"
        f"⏳ جاري الاتصال والتحقق...",
        parse_mode="HTML"
    )
    
    Thread(target=test_site_login, args=(call.message.chat.id, site_key, account_id)).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("site_test_fetch_"))
def site_test_fetch_callback(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        return
    
    data_parts = call.data.replace("site_test_fetch_", "").rsplit("_", 1)
    site_key = data_parts[0]
    account_id = data_parts[1] if len(data_parts) > 1 else None

    account = get_account_by_id(site_key, account_id) if account_id else None
    
    if not account:
        bot.answer_callback_query(call.id, "❌ الحساب غير موجود", show_alert=True)
        return
    
    username_or_token = account.get("username") or account.get("api_token", "N/A")
    bot.answer_callback_query(call.id, f"🔄 جاري جلب آخر كود من {username_or_token[:15]}...")
    
    site_name = SETTINGS[site_key]["name"]
    bot.send_message(
        call.message.chat.id,
        f"📥 <b>اختبار جلب الكود - {site_name}</b>\n\n"
        f"👤 الحساب: <code>{username_or_token[:15]}...</code>\n\n"
        f"⏳ جاري جلب آخر رسالة...",
        parse_mode="HTML"
    )
    
    Thread(target=test_site_fetch, args=(call.message.chat.id, site_key, account_id)).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def country_selection_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)

    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Please subscribe to all channels first!", show_alert=True)
        return

    country_name = call.data.replace("country_", "")
    
    if country_name not in COUNTRIES:
        bot.answer_callback_query(call.id, "❌ Country not found!", show_alert=True)
        return

    country_info = COUNTRIES.get(country_name, {})
    flag = country_info.get("flag", "🌍")

    numbers = get_random_numbers(country_name, 3)

    if not numbers:
        bot.answer_callback_query(call.id, "❌ No numbers available for this country!", show_alert=True)
        return

    service_type = country_info.get("service", "WS")

    old_data = USERS.get(str(user_id), {})
    USERS[str(user_id)] = {
        "selected_country": country_name,
        "selected_numbers": numbers,
        "selected_number": numbers[0],
        "flag": flag,
        "service": service_type,
        "platform": old_data.get("platform", "WhatsApp"),
        "joined": str(datetime.now()),
        "activations": old_data.get("activations", 0),
        "language": old_data.get("language", "ar"),
        "join_date": old_data.get("join_date", datetime.now().strftime('%Y-%m-%d'))
    }
    save_users()

    bot.delete_message(call.message.chat.id, call.message.message_id)

    links = load_button_links()
    markup = InlineKeyboardMarkup(row_width=1)
    
    # إضافة الأرقام الثلاثة في أزرار نسخ
    for num in numbers:
        display_num = f'+{num.lstrip("+")}'
        
        # استخراج ID الإيموجي إذا كان موجوداً في العلم
        emoji_id = None
        if "emoji-id='" in flag:
            match = re.search(r"emoji-id='(\d+)'", flag)
            if match:
                emoji_id = match.group(1)
        
        if emoji_id:
            markup.add(InlineKeyboardButton(
                text=f" {display_num}",
                copy_text=CopyTextButton(text=display_num),
                icon_custom_emoji_id=emoji_id,
                style="primary"
            ))
        else:
            markup.add(InlineKeyboardButton(
                text=f"{flag} {display_num}",
                copy_text=CopyTextButton(text=display_num),
                style="primary"
            ))

    markup.add(InlineKeyboardButton("Change Number", callback_data="change_number", style="success", icon_custom_emoji_id="5465368548702446780")),
    markup.add(InlineKeyboardButton("Change Country", callback_data="choose_country", style="primary", icon_custom_emoji_id="5447410659077661506"))
    
    group_link_btn = InlineKeyboardButton("OTP Group", url=links.get("group_link", "https://t.me/+EAViSkQrDzcxMjA0"), icon_custom_emoji_id="6215361789538866270")
    markup.add(group_link_btn)

    _, _, region_code = detect_country_from_number(country_info.get("code", ""), user_id)
    if not region_code or region_code == "UN":
        region_code = country_info.get("code", "UN")
    platform = old_data.get("platform", country_info.get("service", "WhatsApp"))

    msg_text = (
        f"-------------------------------------------\n"
        f"{flag} {region_code} ┊ ASSIGNED FOR YOU <tg-emoji emoji-id='6183958878456126534'>🔹</tg-emoji>\n\n"
        f"<tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji> Service: {platform}\n"
        f"<tg-emoji emoji-id='6089104607328342288'>🔹</tg-emoji> Reward: 0.0001 USD"
    )
    bot.send_message(
        call.message.chat.id,
        msg_text,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "change_number")
def change_number_callback(call):
    user_id = call.from_user.id
    lang = get_user_language(user_id)

    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Please subscribe to all channels first!", show_alert=True)
        return

    user_data = USERS.get(str(user_id))
    if not user_data:
        bot.answer_callback_query(call.id, "❌ User data not found!", show_alert=True)
        return
        
    country_name = user_data.get("country") or user_data.get("selected_country")
    if not country_name:
        bot.answer_callback_query(call.id, "❌ No country selected!", show_alert=True)
        return
    numbers = get_random_numbers(country_name, 3)

    if not numbers:
        bot.answer_callback_query(call.id, "❌ No numbers available for this country!", show_alert=True)
        return

    country_info = COUNTRIES.get(country_name, {})
    service_type = country_info.get("service", "WS")
    flag = country_info.get("flag", "🌍")

    USERS[str(user_id)]["selected_numbers"] = numbers
    USERS[str(user_id)]["selected_number"] = numbers[0]
    save_users()

    links = load_button_links()
    markup = InlineKeyboardMarkup(row_width=1)
    
    # إضافة الأرقام الثلاثة في أزرار نسخ
    for num in numbers:
        display_num = f'+{num.lstrip("+")}'
        
        # استخراج ID الإيموجي إذا كان موجوداً في العلم
        emoji_id = None
        if "emoji-id='" in flag:
            match = re.search(r"emoji-id='(\d+)'", flag)
            if match:
                emoji_id = match.group(1)
        
        if emoji_id:
            markup.add(InlineKeyboardButton(
                text=f" {display_num}",
                copy_text=CopyTextButton(text=display_num),
                icon_custom_emoji_id=emoji_id,
                style="primary"
            ))
        else:
            markup.add(InlineKeyboardButton(
                text=f"{flag} {display_num}",
                copy_text=CopyTextButton(text=display_num),
                style="primary"
            ))

    markup.add(InlineKeyboardButton("Change Number", callback_data="change_number", style="success", icon_custom_emoji_id="5465368548702446780")),
    markup.add(InlineKeyboardButton("Change Country", callback_data="choose_country", style="primary", icon_custom_emoji_id="5447410659077661506"))
    
    group_link_btn = InlineKeyboardButton("OTP Group", url=links.get("group_link", "https://t.me/+EAViSkQrDzcxMjA0"), icon_custom_emoji_id="6215361789538866270")
    markup.add(group_link_btn)

    _, _, region_code = detect_country_from_number(country_info.get("code", ""), user_id)
    if not region_code or region_code == "UN":
        region_code = country_info.get("code", "UN")
    platform = user_data.get("platform", country_info.get("service", "WhatsApp"))

    msg_text = (
        f"-------------------------------------------\n"
        f"{flag} {region_code} ┊ ASSIGNED FOR YOU <tg-emoji emoji-id='6183958878456126534'>🔹</tg-emoji>\n\n"
        f"<tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji> Service: {platform}\n"
        f"<tg-emoji emoji-id='6089104607328342288'>🔹</tg-emoji> Reward: 0.0001 USD"
    )
    bot.edit_message_text(
        msg_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

    changed_text = "✅ تم تغيير الرقم!" if lang == "ar" else "✅ Number changed!"
    bot.answer_callback_query(call.id, changed_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_plt_"))
def select_platform_main_callback(call):
    user_id = call.from_user.id
    platform = call.data.replace("select_plt_", "")
    lang = get_user_language(user_id)
    
    markup = get_countries_for_platform(platform, user_id)
    if not markup:
        bot.answer_callback_query(call.id, "❌ No countries available for this platform!", show_alert=True)
        return
    
    emoji_ids = {"Facebook": "5269427536453984598", "WhatsApp": "5271536803482981220", "Telegram": "5271801931814165886", "Instagram": "5269682734820777950", "TikTok": "5327982530702359565", "IMO": "5920204030570667999"}
    e_id = emoji_ids.get(platform, "")
    emoji_tag = f"<tg-emoji emoji-id='{e_id}'>🌐</tg-emoji>" if e_id else ""
    title = f"<b>Choose country for {emoji_tag}</b>"
    bot.edit_message_text(title, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "choose_country")
def choose_country_callback(call):
    user_id = call.from_user.id

    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Please subscribe to all channels first!", show_alert=True)
        return

    # عرض قائمة الدول مباشرة كما طلب المستخدم
    markup = get_countries_list(user_id)

    if not markup:
        bot.answer_callback_query(call.id, "❌ No countries available!", show_alert=True)
        return

    lang = get_user_language(user_id)
    title = "<b><tg-emoji emoji-id='6084845507304229827'>▪️</tg-emoji> Select a country <tg-emoji emoji-id='5406745015365943482'>▪️</tg-emoji></b>"

    bot.edit_message_text(
        title,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("platform_"))
def select_platform_callback(call):
    user_id = call.from_user.id

    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Please subscribe to all channels first!", show_alert=True)
        return

    parts = call.data.split("_", 2)
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "❌ Invalid selection!", show_alert=True)
        return
    
    country_name = parts[1]
    platform = parts[2]
    
    if country_name not in COUNTRIES:
        bot.answer_callback_query(call.id, "❌ Country not found!", show_alert=True)
        return
    
    country_info = COUNTRIES[country_name]
    selected_number = get_random_number(country_name)
    
    if not selected_number:
        bot.answer_callback_query(call.id, "❌ No numbers available for this country!", show_alert=True)
        return
    
    USERS[str(user_id)] = {
        "selected_number": selected_number,
        "selected_country": country_name,
        "country": country_name,
        "platform": platform,
        "joined": str(datetime.now()),
        "activations": USERS.get(str(user_id), {}).get("activations", 0),
        "language": USERS.get(str(user_id), {}).get("language", "ar")
    }
    save_users()
    
    country_flag = country_info.get("flag", "🌍")
    display_number = f'+{selected_number.lstrip("+")}'
    user_lang = get_user_language(user_id)
    localized_country_name, _, _ = detect_country_from_number(country_info.get("code", ""), user_id)
    
    if user_lang == "ar":
        msg_text = (
            f"<tg-emoji emoji-id='5972010570340112281'>😀</tg-emoji> <b>تم اختيار الرقم بنجاح!</b>\n\n"
            f"<tg-emoji emoji-id='5224450179368767019'>🌎</tg-emoji> <b>الدولة:</b> {country_flag} {localized_country_name}\n"
            f"<tg-emoji emoji-id='5782668844061430712'>🗣</tg-emoji> <b>المنصة:</b> {platform}\n"
            f"<tg-emoji emoji-id='5453965363286925977'>📞</tg-emoji> <b>الرقم:</b> <code>{display_number}</code>\n\n"
            f"<tg-emoji emoji-id='5458603043203327669'>😀</tg-emoji> <b>ستستلم الرسائل تلقائياً عند وصولها</b>"
        )
    else:
        msg_text = (
            f"<tg-emoji emoji-id='5972010570340112281'>😀</tg-emoji> <b>Number selected successfully!</b>\n\n"
            f"<tg-emoji emoji-id='5224450179368767019'>🌎</tg-emoji> <b>Country:</b> {country_flag} {localized_country_name}\n"
            f"<tg-emoji emoji-id='5782668844061430712'>🗣</tg-emoji> <b>Platform:</b> {platform}\n"
            f"<tg-emoji emoji-id='5453965363286925977'>📞</tg-emoji> <b>Number:</b> <code>{display_number}</code>\n\n"
            f"<tg-emoji emoji-id='5458603043203327669'>😀</tg-emoji> <b>You will receive messages automatically when they arrive</b>"
        )
    
    bot.edit_message_text(
        msg_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=create_message_buttons(user_id)
    )

# @bot.message_handler(commands=["hom"])
def hom_command(msg):
    user_id = msg.from_user.id
    lang = get_user_language(user_id)
    
    
    if is_admin(user_id):
        
        settings = load_referral_settings()
        code_bonus = settings.get("code_bonus", 0.01)
        
        if lang == "ar":
            text = "<b><tg-emoji emoji-id='5341715473882955310'>🔹</tg-emoji>Select a Service:</b>"
        else:
            text = f"<tg-emoji emoji-id='5972277098830634724'>🚨</tg-emoji> <b>Choose Platform</b>"
            
        markup = get_platforms_list(user_id)
        bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=markup)
        return

    if is_banned(user_id):
        bot.reply_to(msg, t(user_id, "banned"))
        return

    text = t(user_id, "welcome")
    if not text: text = "🌐 <b>مرحباً بك!</b>"
    bot.send_message(
        msg.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=get_main_menu_lang(user_id)
    )

def process_country_code_logic(msg, user_id, country_code, state):
    
    country_code = str(country_code).replace('+', '').strip()
    
   
    import phonenumbers
    from phonenumbers import COUNTRY_CODE_TO_REGION_CODE
    
    
    potential_code = ""
    for i in range(min(len(country_code), 4), 0, -1):
        prefix = country_code[:i]
        if int(prefix) in COUNTRY_CODE_TO_REGION_CODE:
            potential_code = prefix
            break
            
    if potential_code:
        country_code = potential_code

    if not country_code.isdigit():
        bot.reply_to(msg, "❌ رمز الدولة يجب أن يحتوي على أرقام فقط!")
        return

    temp_file = state.get("temp_file")
    if not temp_file or not os.path.exists(temp_file):
        bot.reply_to(msg, "❌ لم يتم العثور على الملف! يرجى البدء من جديد.")
        if user_id in user_states: del user_states[user_id]
        return

    try:
        with open(temp_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e: 
        bot.reply_to(msg, f"❌ خطأ في قراءة الملف: {e}")
        return

    cleaned_numbers = []
    total_lines = 0
    rejected_lines = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        first_part = line.split()[0] if line.split() else line
        digits_only = ''.join(c for c in first_part if c.isdigit())

        if digits_only.startswith(country_code) and len(digits_only) >= 8:
            cleaned_numbers.append(digits_only)
        else:
            rejected_lines += 1

    num_cleaned = len(cleaned_numbers)

    if num_cleaned == 0:
        bot.reply_to(
            msg,
            f"❌ <b>لم يتم العثور على أي أرقام تبدأ برمز الدولة {country_code}!</b>\n\n"
            f"📊 إجمالي الأسطر المعالجة: {total_lines}\n"
            f"❌ أرقام مرفوضة: {rejected_lines}\n\n"
            f"<i>تأكد من جودة الملف</i>",
            parse_mode="HTML"
        )
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if user_id in user_states: del user_states[user_id]
        return

    cleanup_old_numbers_files(country_code)
    
    cleaned_filename = f"numbers_{country_code}_{uuid.uuid4().hex[:8]}.txt"
    with open(cleaned_filename, "w", encoding="utf-8") as f:
        for num in cleaned_numbers:
            f.write(num + "\n")

    if os.path.exists(temp_file):
        os.remove(temp_file)

    user_states[user_id] = {
        "action": "na_add_country_name",
        "numbers_file": cleaned_filename,
        "country_code": country_code,
        "num_cleaned": num_cleaned,
        "total_lines": total_lines,
        "rejected_lines": rejected_lines
    }

    bot.reply_to(
        msg,
        f"<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji> <b>File processed successfully</b>\n\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Total lines: <b>{total_lines}</b>\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Valid numbers: <b>{num_cleaned}</b>\n"
        f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Detected country code: <b>+{country_code}</b>\n\n"
        f"<tg-emoji emoji-id='5444989577422993015'>◾</tg-emoji> <b>Detecting country automatically...</b>",
        parse_mode="HTML"
    )

   
    country_name, flag, region_code = detect_country_from_number(country_code, user_id)
    
    
    lang = get_user_language(user_id)
    if lang == "ar":
       
        country_name_ar = geocoder.description_for_number(phonenumbers.parse("+" + country_code + "0000000"), "ar")
        if country_name_ar:
            country_name = country_name_ar

    user_states[user_id] = {
        "action": "na_add_country_platforms",
        "numbers_file": cleaned_filename,
        "country_code": country_code,
        "country_name": country_name,
        "num_cleaned": num_cleaned,
        "server": "GROUP", 
        "selected_platforms": []
    }
    
   
    lang = get_user_language(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    
    platform_icons = {
        "Facebook": "5382322671679708881",
        "WhatsApp": "5381990043642502553",
        "Telegram": "5381879959335738545",
        "Instagram": "5382054253403577563",
        "Twitter": "5391197405553107640",
        "TikTok": "5390966190283694453",
        "Discord": "5382132232829804982",
        "Gmail": "5391038994274329680"
    }
    
    for p in ["Facebook", "WhatsApp", "Telegram", "Instagram", "Twitter", "TikTok", "Discord", "Gmail"]:
        markup.add(InlineKeyboardButton(p, callback_data=f"na_add_country_plt_{p}", icon_custom_emoji_id=platform_icons.get(p), style="primary"))
    
    edit_name_text = " Edit Name"
    confirm_text = " Continue"
    
    markup.add(
        InlineKeyboardButton(edit_name_text, callback_data="na_add_country_edit_name",    icon_custom_emoji_id="4990298741463319592"),
        InlineKeyboardButton(confirm_text, callback_data="na_add_country_finish",    icon_custom_emoji_id="4990298741463319592")
    )
    
    bot.send_message(
        msg.chat.id,
        f"<tg-emoji emoji-id='5769421696041753266'>◾</tg-emoji> Country Identified: {flag}\n\n"
        f"Choose the platforms these numbers work on:",
        parse_mode="HTML",
        reply_markup=markup
    )
    return

@bot.message_handler(content_types=["text", "document", "photo", "video", "audio", "voice", "sticker"])
def handle_messages(msg):
    user_id = msg.from_user.id
    
    if msg.chat.type != "private":
        return

    if not check_subscription(user_id):
        unjoined_channel = get_first_unjoined_channel(user_id)
        if unjoined_channel:
            bot.send_message(
                msg.chat.id,
                get_subscription_message_for_channel(unjoined_channel, user_id),
                parse_mode="HTML",
                reply_markup=get_single_channel_keyboard(unjoined_channel, user_id)
            )
        return

    if msg.text == "Get number":
        return getnumber_command(msg)

    if msg.text == "WS CHECKER":
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("WS Cheker OFF", callback_data="ws_checker_off", style="primary", icon_custom_emoji_id="6206493566835889826"))
        ws_msg = (
            "═════《 <tg-emoji emoji-id='6206493566835889826'>▪️</tg-emoji> WS CHECKER 》═════\n\n"
            "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> API offline\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> WS Checker: OFF\n\n"
            "🟢 Means WhatsApp Alive\n"
            "🔵 Means WhatsApp Not Alive"
        )
        bot.send_message(msg.chat.id, ws_msg, parse_mode="HTML", reply_markup=markup)
        return

    if msg.text == "My Wallet":
        referral_data = get_user_referral_data(user_id)
        referral_settings = load_referral_settings()
        balance = referral_data.get("balance", 0.0)
        lifetime_earn = referral_data.get("lifetime_earn", balance)
        withdrawn = referral_data.get("withdrawn", 0.0)
        min_withdrawal = referral_settings.get("min_withdrawal", 0.1)
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Withdraw", callback_data="wallet_withdraw_btn", style="primary", icon_custom_emoji_id="6001287064589439895"))
        wallet_msg = (
            "---------------------------------------------\n"
            "         <tg-emoji emoji-id='6001287064589439895'>▪️</tg-emoji> MY WALLET\n"
            "---------------------------------------------\n\n"
            "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> My Balance: " + f"{balance}" + " USD\n"
            "<tg-emoji emoji-id='6032808241891644148'>▪️</tg-emoji> Lifetime Earn: " + f"{lifetime_earn}" + " USD\n\n"
            "<tg-emoji emoji-id='6028584717081645421'>▪️</tg-emoji> Min.Withdraw: " + f"{min_withdrawal}" + " USD\n"
            "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> Withdrawn: " + f"{withdrawn}" + " USD"
        )
        bot.send_message(msg.chat.id, wallet_msg, parse_mode="HTML", reply_markup=markup)
        return

    if msg.text == "My Stats":
        referral_data = get_user_referral_data(user_id)
        balance = referral_data.get("balance", 0.0)
        referrals_count = len(referral_data.get("referrals", []))
        activations = referral_data.get("activations", 0)
        requests_count = referral_data.get("requests_count", activations)
        countries_used = len(referral_data.get("countries", []))
        join_date = referral_data.get("join_date", datetime.now().strftime("%Y-%m-%d"))
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Referral", callback_data="mystats_referral_btn", style="primary", icon_custom_emoji_id="5271604874419647061"),
            InlineKeyboardButton("History", callback_data="mystats_history_btn", style="primary", icon_custom_emoji_id="5803175856905917502")
        )
        stats_msg = (
            "-------------------------------------------\n"
            "         <tg-emoji emoji-id='5280655263865513608'>▪️</tg-emoji> MY STATS\n"
            "-------------------------------------------\n"
            "<tg-emoji emoji-id='6307589808424228455'>▪️</tg-emoji> My ID: " + f"{user_id}" + "\n"
            "<tg-emoji emoji-id='6089104607328342288'>▪️</tg-emoji> My Balance: " + f"{balance}" + " USD\n"
            "<tg-emoji emoji-id='5332724926216428039'>▪️</tg-emoji> My Referrals: " + f"{referrals_count}" + "\n"
            "-------------------------------------------\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Total requests: " + f"{requests_count}" + "\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Numbers received: " + f"{activations}" + "\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Countries used: " + f"{countries_used}" + "\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Join Date: " + f"{join_date}"
        )
        bot.send_message(msg.chat.id, stats_msg, parse_mode="HTML", reply_markup=markup)
        return

    if msg.text == "Live Traffic":
        _send_live_traffic(msg.chat.id, user_id)
        return
    


    if msg.text == "Admin Panel":
        if not is_admin(user_id):
            return
        bot.send_message(
            msg.chat.id,
            "Welcome to admin panel <tg-emoji emoji-id='5422439311196834318'>💡</tg-emoji>",
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
        return

    if msg.text == "Balance":
        referral_data = get_user_referral_data(user_id)
        referral_settings = load_referral_settings()
        
        balance = referral_data.get("balance", 0.0)
        referrals_count = len(referral_data.get("referrals", []))
        min_withdrawal = referral_settings.get("min_withdrawal", 10.0)
        referral_bonus = referral_settings.get("referral_bonus", 0.005)
        
        balance_msg = (
            "════《 <tg-emoji emoji-id='6025976946083500432'>▪️</tg-emoji> BALANCE 》════\n\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your Balance: {balance} USD\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Referrals: {referrals_count}\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Min. Withdrawal: {min_withdrawal} USD\n\n"
            f"Refer and earn {referral_bonus} USD per referral!"
        )
        bot.send_message(msg.chat.id, balance_msg, parse_mode="HTML")
        return

    if msg.text == "Withdraw":
        referral_data = get_user_referral_data(user_id)
        balance = referral_data.get("balance", 0.0)
        settings = load_referral_settings()
        min_withdrawal = settings.get("min_withdrawal", 10.0)
        
        msg_text = (
            "═══《 <tg-emoji emoji-id='5332600543963522398'>▪️</tg-emoji> WITHDRAW 》═══\n\n"
            "<tg-emoji emoji-id='6032903688949862892'>▪️</tg-emoji> Insufficient balance!\n\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your balance: {balance:.3f} USD\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Minimum required: {min_withdrawal} USD\n\n"
            "Earn more by referring friends!"
        )
        bot.send_message(msg.chat.id, msg_text, parse_mode="HTML")
        return

    if msg.text == "Refer":
        referral_data = get_user_referral_data(user_id)
        referral_settings = load_referral_settings()
        
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        referrals_count = len(referral_data.get("referrals", []))
        referral_bonus = referral_settings.get("referral_bonus", 0.005)
        
        refer_msg = (
            "═══《 <tg-emoji emoji-id='5271604874419647061'>▪️</tg-emoji> REFER & EARN 》═══\n\n"
            "<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Your referral link:\n"
            f"<code>{referral_link}</code>\n\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Total referrals: {referrals_count}\n"
            f"<tg-emoji emoji-id='4990298741463319592'>▪️</tg-emoji> Earn per referral: {referral_bonus} USD\n\n"
            "Share this link with friends to earn!"
        )
        bot.send_message(msg.chat.id, refer_msg, parse_mode="HTML")
        return

    if msg.text == "Support":
        support_msg = (
            "═════《 <tg-emoji emoji-id=\"5238025132177369293\">▪️</tg-emoji> SUPPORT 》═════\n\n"
            "<tg-emoji emoji-id=\"4990298741463319592\">📞</tg-emoji> Contact: @MEDO_SX\n\n"
            "For any issues, reach out to support."
        )
        bot.send_message(msg.chat.id, support_msg, parse_mode="HTML")
        return

    if msg.text and msg.text.lower() in ["available county", "available country"]:
        if not COUNTRIES:
            bot.send_message(msg.chat.id, "Available Country Now:\n\n<tg-emoji emoji-id='6217714808846815764'>❌</tg-emoji> لا توجد دول مضافة حالياً.\n\nYou Can Get Number By Bress The button [ Get Number ] <tg-emoji emoji-id='6217630318250168874'>✨</tg-emoji>", parse_mode="HTML")
            return

        # تجميع الدول المضافة بدون تكرار حسب الاسم
        unique_countries = {}
        for cid, data in COUNTRIES.items():
            name = data.get("display_name", "Unknown")
            flag = data.get("flag", "🌐")
            if name not in unique_countries:
                unique_countries[name] = flag

        # ترتيب الدول أبجدياً
        sorted_names = sorted(unique_countries.keys())
        
        countries_list = ""
        for name in sorted_names:
            flag = unique_countries[name]
            countries_list += f" {flag} {name}\n"

        response = (
            "Available Country Now:\n\n"
            f"{countries_list}\n"
            "You Can Get Number By Bress The button [ Get Number ] <tg-emoji emoji-id='6217630318250168874'>✨</tg-emoji>"
        )
        bot.send_message(msg.chat.id, response, parse_mode="HTML")
        return
    if user_id not in user_states and user_id not in broadcast_state:
        return

    state = user_states.get(user_id, {})
    action = state.get("action")
    mode = state.get("mode")
    
    if mode == "add_numbers_admin":
        if msg.content_type != "text":
            bot.reply_to(msg, "❌ يرجى إرسال معرف رقمي!")
            return
        
        try:
            new_admin_id = int(msg.text.strip())
        except ValueError:
            bot.reply_to(msg, "❌ المعرف يجب أن يكون رقماً!")
            return
        
        if new_admin_id in NUMBERS_ADMINS:
            bot.reply_to(msg, "⚠️ هذا المستخدم أدمن أرقام بالفعل!")
        else:
            NUMBERS_ADMINS.append(new_admin_id)
            save_numbers_admins()
            bot.reply_to(msg, f"✅ تم إضافة <code>{new_admin_id}</code> كأدمن أرقام!", parse_mode="HTML")
        
        del user_states[user_id]
        return
    
    elif action == "na_add_country_edit_name_input":
        new_name = msg.text.strip()
        if not new_name:
            bot.reply_to(msg, "❌ يرجى إرسال اسم صالح!")
            return
        
        state["country_name"] = new_name
        
        lang = get_user_language(user_id)
        markup = InlineKeyboardMarkup(row_width=2)
        platforms = ["Facebook", "WhatsApp", "Telegram", "Instagram", "Twitter", "TikTok", "Discord", "Gmail"]
        for p in platforms:
            prefix = "✅ " if p in state.get("selected_platforms", []) else ""
            markup.add(InlineKeyboardButton(f"{prefix}{p}", callback_data=f"na_add_country_plt_{p}"))
        
        edit_name_text = "✏️ Edit Name"
        confirm_text = "✅ Continue"
        
        markup.add(
        InlineKeyboardButton(edit_name_text, callback_data="na_add_country_edit_name"),
            InlineKeyboardButton(confirm_text, callback_data="na_add_country_finish")
        )
        
        bot.send_message(
            msg.chat.id,
            f"✅ تم تحديث الاسم إلى: <b>{new_name}</b>\n\n"
            f"<tg-emoji emoji-id='6087133294648890399'>📱</tg-emoji> Choose the platforms these numbers work on:",
            parse_mode="HTML",
            reply_markup=markup
        )
        state["action"] = "na_add_country_platforms"
        return

    elif action == "na_add_country_paste":
        if msg.content_type != "text":
            bot.reply_to(msg, "❌ يرجى إرسال الأرقام كنص!")
            return
        
        text = msg.text.strip()
        numbers_raw = re.findall(r'\d+', text)
        
        if not numbers_raw:
            bot.reply_to(msg, "❌ لم يتم العثور على أرقام في النص المرسل!")
            return
        
        
        guessed_code = ""
        
        first_num_digits = "".join(filter(str.isdigit, numbers_raw[0])) if numbers_raw else ""
        
        if first_num_digits:
           
            for length in [3, 2, 1]:
                prefix = first_num_digits[:length]
               
                if prefix in ["966", "971", "965", "974", "973", "968", "212", "213", "216", "961", "962", "963", "964", "967", "249", "218", "222", "20", "7", "1", "44"]:
                    guessed_code = prefix
                    break
            if not guessed_code:
                guessed_code = first_num_digits[:2] 
        else:
            guessed_code = "218" 

        temp_filename = f"temp_{uuid.uuid4().hex[:8]}.txt"
        with open(temp_filename, "w", encoding="utf-8") as f:
            for num in numbers_raw:
                if len(num) >= 8:
                    f.write(num + "\n")
        
    
        state = {"temp_file": temp_filename, "paste_mode": True}
        process_country_code_logic(msg, user_id, guessed_code, state)
        return
    
    elif action == "na_add_country_file":
        if msg.content_type != "document":
            bot.reply_to(msg, "❌ يرجى إرسال ملف txt!")
            return

        try:
            file_info = bot.get_file(msg.document.file_id)
            if not file_info.file_path:
                bot.reply_to(msg, "❌ خطأ في تحميل الملف!")
                return
            downloaded_file = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.reply_to(msg, f"❌ خطأ في تحميل الملف: {e}")
            return

        temp_filename = f"temp_{uuid.uuid4().hex[:8]}.txt"
        with open(temp_filename, "wb") as f:
            f.write(downloaded_file)

        
        try:
            with open(temp_filename, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                all_numbers = re.findall(r'\d+', content)
                if all_numbers:
                   
                    likely_phones = [n for n in all_numbers if 8 <= len(n) <= 15]
                    if likely_phones:
                        
                        prefixes = {}
                        for num in likely_phones:
                           
                            for i in range(1, 4):
                                if len(num) > i:
                                    pref = num[:i]
                                    prefixes[pref] = prefixes.get(pref, 0) + 1
                        
                        
                        sorted_prefixes = sorted(prefixes.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
                        guessed_code = sorted_prefixes[0][0] if sorted_prefixes else "20"
                    else:
                        guessed_code = "20"
                else:
                    guessed_code = "20"
        except Exception as e:
            print(f"Error guessing code: {e}")
            guessed_code = "20"

        state = {"temp_file": temp_filename}
        process_country_code_logic(msg, user_id, guessed_code, state)
        return

    elif action == "na_add_country_code":
        country_code = msg.text.strip()
        process_country_code_logic(msg, user_id, country_code, state)
        return

    elif action == "na_add_country_name":
        country_name = msg.text.strip()
        numbers_file = state.get("numbers_file")
        country_code = state.get("country_code")
        num_cleaned = state.get("num_cleaned")

        user_states[user_id] = {
            "action": "na_add_country_platforms",
            "numbers_file": numbers_file,
            "country_code": country_code,
            "country_name": country_name,
            "num_cleaned": num_cleaned,
            "server": "GROUP",
            "selected_platforms": []
        }
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
        InlineKeyboardButton("Facebook", callback_data="na_add_country_plt_Facebook", icon_custom_emoji_id="5382322671679708881", style="primary"),
            InlineKeyboardButton("WhatsApp", callback_data="na_add_country_plt_WhatsApp", icon_custom_emoji_id="5381990043642502553", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Telegram", callback_data="na_add_country_plt_Telegram", icon_custom_emoji_id="5381879959335738545", style="primary"),
            InlineKeyboardButton("Instagram", callback_data="na_add_country_plt_Instagram", icon_custom_emoji_id="5382054253403577563", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Twitter/X", callback_data="na_add_country_plt_Twitter", icon_custom_emoji_id="5391197405553107640", style="primary"),
            InlineKeyboardButton("TikTok", callback_data="na_add_country_plt_TikTok", icon_custom_emoji_id="5390966190283694453", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Discord", callback_data="na_add_country_plt_Discord", icon_custom_emoji_id="5382132232829804982", style="primary"),
            InlineKeyboardButton("Gmail", callback_data="na_add_country_plt_Gmail", icon_custom_emoji_id="5391038994274329680", style="primary")
        )
        markup.add(
            InlineKeyboardButton("🌐 All Platforms", callback_data="na_add_country_plt_ALL")
        )
        markup.add(InlineKeyboardButton("✅ Confirm & Finish", callback_data="na_add_country_finish")),
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="numbers_admin_panel"))

        bot.reply_to(
            msg,
            f"✅ <b>Step 3/3 - Platform Selection</b>\n\n"
            f"🌍 Country: <b>{country_name}</b>\n"
            f"🔢 Country Code: <b>{country_code}</b>\n"
            f"📊 Numbers Count: <b>{num_cleaned}</b>\n\n"
            f"📱 <b>Selected Platforms:</b> None\n\n"
            f"Choose the platforms these numbers work on:",
            parse_mode="HTML",
            reply_markup=markup
        )
        return
    
    elif mode == "na_ban_user":
        if msg.content_type != "text":
            bot.reply_to(msg, "❌ يرجى إرسال معرف رقمي!")
            return
        
        try:
            ban_id = int(msg.text.strip())
        except ValueError:
            bot.reply_to(msg, "❌ المعرف يجب أن يكون رقماً!")
            return
        
        if ban_id in BANNED:
            bot.reply_to(msg, "This User Was Already Banned <tg-emoji emoji-id='6129840374971112593'>◾</tg-emoji>")
        else:
            BANNED.append(ban_id)
            save_banned()
            bot.reply_to(msg, f"This user eas banned <tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji> <code>{ban_id}</code>!", parse_mode="HTML")
        
        del user_states[user_id]
        return
    
    elif mode == "na_unban_user":
        if msg.content_type != "text":
            bot.reply_to(msg, "❌ يرجى إرسال معرف رقمي!")
            return
        
        try:
            unban_id = int(msg.text.strip())
        except ValueError:
            bot.reply_to(msg, "❌ المعرف يجب أن يكون رقماً!")
            return
        
        if unban_id not in BANNED:
            bot.reply_to(msg, "⚠️ هذا المستخدم غير محظور!")
        else:
            BANNED.remove(unban_id)
            save_banned()
            bot.reply_to(msg, f"✅ تم إلغاء حظر المستخدم <code>{unban_id}</code>!", parse_mode="HTML")
        
        del user_states[user_id]
        return
    
    if user_id in broadcast_state:
        bc_mode = broadcast_state[user_id].get("mode")
        
        if bc_mode == "na_global_broadcast":
            success = 0
            failed = 0
            
            for uid in USERS.keys():
                try:
                    bot.copy_message(int(uid), msg.chat.id, msg.message_id)
                    success += 1
                except:
                    failed += 1
            
            bot.reply_to(msg, f"✅ تم إرسال الإذاعة الشاملة!\n\n📊 نجح: {success}\n❌ فشل: {failed}")
            del broadcast_state[user_id]
            return

    elif action == "na_add_country_file":
        if msg.content_type != "document":
            bot.reply_to(msg, "❌ يرجى إرسال ملف txt!")
            return

        try:
            file_info = bot.get_file(msg.document.file_id)
            if not file_info.file_path:
                bot.reply_to(msg, "❌ خطأ في تحميل الملف!")
                return
            downloaded_file = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.reply_to(msg, f"❌ خطأ في تحميل الملف: {e}")
            return

        temp_filename = f"temp_{uuid.uuid4().hex[:8]}.txt"

        with open(temp_filename, "wb") as f:
            f.write(downloaded_file)

        user_states[user_id] = {"action": "na_add_country_code", "temp_file": temp_filename}

        bot.reply_to(
            msg,
            "✅ <b>تم رفع الملف بنجاح!</b>\n\n"
            "📝 <b>الخطوة 2/4</b>\n\n"
            "أرسل رمز الدولة (مثال: 20 لمصر، 7 لروسيا، 966 للسعودية)\n\n"
            "<i>سيتم الاحتفاظ فقط بالأرقام التي تبدأ برمز الدولة هذا</i>",
            parse_mode="HTML"
        )
        return

    elif action == "na_add_country_name":
        country_name = msg.text.strip()
        numbers_file = state.get("numbers_file")
        country_code = state.get("country_code")
        num_cleaned = state.get("num_cleaned")

        user_states[user_id] = {
            "action": "na_add_country_platforms",
            "numbers_file": numbers_file,
            "country_code": country_code,
            "country_name": country_name,
            "num_cleaned": num_cleaned,
            "server": "GROUP",
            "selected_platforms": []
        }
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
        InlineKeyboardButton("Facebook", callback_data="na_add_country_plt_Facebook", icon_custom_emoji_id="5382322671679708881", style="primary"),
            InlineKeyboardButton("WhatsApp", callback_data="na_add_country_plt_WhatsApp", icon_custom_emoji_id="5381990043642502553", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Telegram", callback_data="na_add_country_plt_Telegram", icon_custom_emoji_id="5381879959335738545", style="primary"),
            InlineKeyboardButton("Instagram", callback_data="na_add_country_plt_Instagram", icon_custom_emoji_id="5382054253403577563", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Twitter/X", callback_data="na_add_country_plt_Twitter", icon_custom_emoji_id="5391197405553107640", style="primary"),
            InlineKeyboardButton("TikTok", callback_data="na_add_country_plt_TikTok", icon_custom_emoji_id="5390966190283694453", style="primary")
        )
        markup.add(
        InlineKeyboardButton("Discord", callback_data="na_add_country_plt_Discord", icon_custom_emoji_id="5382132232829804982", style="primary"),
            InlineKeyboardButton("Gmail", callback_data="na_add_country_plt_Gmail", icon_custom_emoji_id="5391038994274329680", style="primary")
        )
        markup.add(
            InlineKeyboardButton("🌐 All Platforms", callback_data="na_add_country_plt_ALL")
        )
        markup.add(InlineKeyboardButton("✅ Confirm & Finish", callback_data="na_add_country_finish")),
        markup.add(InlineKeyboardButton("❌ Cancel", callback_data="numbers_admin_panel"))

        bot.reply_to(
            msg,
            f"✅ <b>Step 3/3 - Platform Selection</b>\n\n"
            f"🌍 Country: <b>{country_name}</b>\n"
            f"🔢 Country Code: <b>{country_code}</b>\n"
            f"📊 Numbers Count: <b>{num_cleaned}</b>\n\n"
            f"📱 <b>Selected Platforms:</b> None\n\n"
            f"Choose the platforms these numbers work on:",
            parse_mode="HTML",
            reply_markup=markup
        )
        return

    elif action == "remove_country":
        country_name = msg.text.strip()

        if country_name in COUNTRIES:
            country_data = COUNTRIES[country_name]
            numbers_file = country_data.get("file", "")
            
            if numbers_file and os.path.exists(numbers_file):
                try:
                    os.remove(numbers_file)
                    print(f"🗑️ تم حذف ملف الأرقام: {numbers_file}")
                except Exception as e:
                    print(f"⚠️ خطأ في حذف ملف الأرقام {numbers_file}: {e}")
            
            del COUNTRIES[country_name]
            save_countries()
            del user_states[user_id]
            
            file_status = f"\n📄 تم حذف ملف الأرقام: {numbers_file}" if numbers_file else ""
            bot.reply_to(msg, f"✅ تم حذف الدولة: {country_name}{file_status}")
        else:
            bot.reply_to(msg, f"❌ الدولة غير موجودة: {country_name}")

    elif action == "add_channel":
        try:
            channel_input = msg.text.strip()
            if channel_input.startswith("https://t.me/"):
                channel_username = "@" + channel_input.replace("https://t.me/", "")
            elif channel_input.startswith("@"):
                channel_username = channel_input
            elif channel_input.startswith("-") or channel_input.isdigit():
                channel_username = channel_input
            else:
                channel_username = "@" + channel_input

            try:
                chat = bot.get_chat(channel_username)
                channel_id = chat.id
                
                if chat.username:
                    channel_url = f"https://t.me/{chat.username}"
                else:
                    channel_url = f"https://t.me/c/{str(channel_id)[4:]}/1"

                user_states[user_id] = {
                    "action": "add_channel_name",
                    "channel_id": channel_id,
                    "channel_username": channel_username,
                    "channel_url": channel_url
                }
                bot.reply_to(msg, "<b>Send name of your channel</b>\n<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji>", parse_mode="HTML")
            except Exception as e:
                bot.reply_to(msg, f"❌ Error: {e}\n\nMake sure:\n• Bot is admin in channel\n• Link or ID is correct")
        except Exception as e:
            bot.reply_to(msg, f"❌ Error: {e}")

    elif action == "add_channel_name":
        channel_name = msg.text.strip()
        channel_id = state.get("channel_id")
        channel_username = state.get("channel_username")
        channel_url = state.get("channel_url")

        CHANNELS.append({
            "name": channel_name, 
            "name_ar": channel_name,
            "name_en": channel_name,
            "id": channel_id,
            "username": channel_username,
            "url": channel_url
        })
        save_channels()
        del user_states[user_id]

        bot.reply_to(
            msg,
            f"<tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji> <b>channel added</b>\n\n"
            f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> Name: {channel_name}\n"
            f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> User: {channel_username}\n"
            f"<tg-emoji emoji-id='4990298741463319592'>◾</tg-emoji> ID: <code>{channel_id}</code>",
            parse_mode="HTML"
        )

    elif action == "remove_channel":
        try:
            index = int(msg.text.strip()) - 1

            if 0 <= index < len(CHANNELS):
                removed = CHANNELS.pop(index)
                save_channels()
                del user_states[user_id]
                bot.reply_to(msg, f"<b>Channel deleate success:</b> {removed['name']} <tg-emoji emoji-id='6206108815075579644'>🗑</tg-emoji>", parse_mode="HTML")
            else:
                bot.reply_to(msg, "❌ Wrong number!")
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إرسال رقم صحيح!")

    elif action == "add_admin":
        if user_id != MAIN_ADMIN_ID:
            bot.reply_to(msg, "❌ عذراً، المالك فقط يمكنه إضافة مشرفين!")
            return
        try:
            new_admin_id = int(msg.text.strip())

            if new_admin_id in ADMINS:
                bot.reply_to(msg, "⚠️ هذا المستخدم مشرف بالفعل!")
                return

            ADMINS.append(new_admin_id)
            save_admins()
            del user_states[user_id]
            bot.reply_to(msg, f"New admin was added <tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji>\n\nID: <code>{new_admin_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")

    elif action == "remove_admin":
        if user_id != MAIN_ADMIN_ID:
            bot.reply_to(msg, "❌ عذراً، المالك فقط يمكنه حذف مشرفين!")
            return
        try:
            target_id = int(msg.text.strip())
            if target_id == MAIN_ADMIN_ID:
                bot.reply_to(msg, "❌ لا يمكن حذف المشرف الأساسي (المالك)!")
                return
            
            if target_id in ADMINS:
                ADMINS.remove(target_id)
                save_admins()
                del user_states[user_id]
                bot.reply_to(msg, f"Ok done <tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji>\n\nID: <code>{target_id}</code>", parse_mode="HTML")
            else:
                bot.reply_to(msg, "❌ هذا المستخدم ليس مشرفاً!")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")

    elif action == "ban_user":
        try:
            ban_user_id = int(msg.text.strip())

            if ban_user_id in ADMINS:
                bot.reply_to(msg, "You Can't Ban The Admins <tg-emoji emoji-id='6129840374971112593'>◾</tg-emoji>")
                return

            if ban_user_id in BANNED:
                bot.reply_to(msg, "⚠️ هذا المستخدم محظور بالفعل!")
                return

            BANNED.append(ban_user_id)
            save_banned()
            del user_states[user_id]
            bot.reply_to(msg, f"Ban is success <tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji>\n\nID: <code>{ban_user_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")

    elif action == "unban_user":
        try:
            unban_user_id = int(msg.text.strip())

            if unban_user_id in BANNED:
                BANNED.remove(unban_user_id)
                save_banned()
                del user_states[user_id]
                bot.reply_to(msg, f"Un ban success <tg-emoji emoji-id='6087133294648890399'>◾</tg-emoji>\n\nID: <code>{unban_user_id}</code>", parse_mode="HTML")
            else:
                bot.reply_to(msg, "❌ هذا المستخدم غير محظور!")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")

    elif action == "set_otp_group":
        global OTP_GROUP
        try:
            group_id = int(msg.text.strip())
            OTP_GROUP = group_id
            save_otp_group()
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تعيين مجموعة OTP!\n\nID: <code>{group_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")
    
    elif action == "edit_code_bonus":
        try:
            new_value = float(msg.text.strip())
            if new_value <= 0 or new_value > 10:
                bot.reply_to(msg, "❌ القيمة يجب أن تكون بين 0.01 و 10!")
                return
            settings = load_referral_settings()
            settings["code_bonus"] = new_value
            save_referral_settings(settings)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث بونص الكود إلى <b>${new_value}</b>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "edit_referral_bonus":
        try:
            new_value = float(msg.text.strip())
            if new_value <= 0 or new_value > 100:
                bot.reply_to(msg, "❌ القيمة يجب أن تكون بين 0.01 و 100!")
                return
            settings = load_referral_settings()
            settings["referral_bonus"] = new_value
            save_referral_settings(settings)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث بونص الإحالة إلى <b>${new_value}</b>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "edit_codes_required":
        try:
            new_value = int(msg.text.strip())
            if new_value < 1 or new_value > 100:
                bot.reply_to(msg, "❌ العدد يجب أن يكون بين 1 و 100!")
                return
            settings = load_referral_settings()
            settings["codes_required_for_referral"] = new_value
            save_referral_settings(settings)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث عدد الأكواد المطلوبة إلى <b>{new_value}</b>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "edit_min_withdrawal":
        try:
            new_value = float(msg.text.strip())
            if new_value <= 0 or new_value > 1000:
                bot.reply_to(msg, "❌ القيمة يجب أن تكون بين 0.01 و 1000!")
                return
            settings = load_referral_settings()
            settings["min_withdrawal"] = new_value
            save_referral_settings(settings)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث الحد الأدنى للسحب إلى <b>${new_value}</b>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "admin_add_balance":
        try:
            parts = msg.text.strip().split()
            if len(parts) != 2:
                bot.reply_to(msg, "❌ الصيغة غير صحيحة! استخدم: USER_ID AMOUNT")
                return
            target_user_id = int(parts[0])
            amount = float(parts[1])
            if amount <= 0 or amount > 10000:
                bot.reply_to(msg, "❌ المبلغ يجب أن يكون بين 0.01 و 10000!")
                return
            
            referrals_data = load_referrals()
            target_key = str(target_user_id)
            if target_key not in referrals_data:
                referrals_data[target_key] = {
                    "referred_by": None,
                    "referrals": [],
                    "active_referrals": 0,
                    "codes_received": 0,
                    "balance": 0.0,
                    "total_earned": 0.0
                }
            
            old_balance = referrals_data[target_key].get("balance", 0.0)
            referrals_data[target_key]["balance"] = old_balance + amount
            referrals_data[target_key]["total_earned"] = referrals_data[target_key].get("total_earned", 0.0) + amount
            save_referrals(referrals_data)
            del user_states[user_id]
            
            new_balance = referrals_data[target_key]["balance"]
            bot.reply_to(msg, f"✅ <b>تم إضافة الرصيد بنجاح!</b>\n\n👤 المستخدم: <code>{target_user_id}</code>\n💰 المبلغ المضاف: <b>${amount:.2f}</b>\n💵 الرصيد السابق: <b>${old_balance:.2f}</b>\n💵 الرصيد الجديد: <b>${new_balance:.2f}</b>", parse_mode="HTML")
            
            try:
                target_lang = get_user_language(target_user_id)
                if target_lang == "ar":
                    notify_msg = f"💰 <b>تم إضافة رصيد!</b>\n\nتم إضافة <b>${amount:.2f}</b> إلى رصيدك بواسطة الأدمن.\n💵 رصيدك الحالي: <b>${new_balance:.2f}</b>"
                else:
                    notify_msg = f"💰 <b>Balance Added!</b>\n\n<b>${amount:.2f}</b> has been added to your balance by admin.\n💵 Your current balance: <b>${new_balance:.2f}</b>"
                bot.send_message(target_user_id, notify_msg, parse_mode="HTML")
            except:
                pass
        except ValueError:
            bot.reply_to(msg, "❌ الصيغة غير صحيحة! استخدم: USER_ID AMOUNT\n\nمثال: 123456789 5.00")
    
    elif action == "admin_subtract_balance":
        try:
            parts = msg.text.strip().split()
            if len(parts) != 2:
                bot.reply_to(msg, "❌ الصيغة غير صحيحة! استخدم: USER_ID AMOUNT")
                return
            target_user_id = int(parts[0])
            amount = float(parts[1])
            if amount <= 0 or amount > 10000:
                bot.reply_to(msg, "❌ المبلغ يجب أن يكون بين 0.01 و 10000!")
                return
            
            referrals_data = load_referrals()
            target_key = str(target_user_id)
            if target_key not in referrals_data:
                bot.reply_to(msg, "❌ المستخدم غير موجود في نظام الإحالات!")
                del user_states[user_id]
                return
            
            old_balance = referrals_data[target_key].get("balance", 0.0)
            if amount > old_balance:
                bot.reply_to(msg, f"❌ رصيد المستخدم غير كافي!\n💵 رصيده الحالي: ${old_balance:.2f}")
                return
            
            referrals_data[target_key]["balance"] = old_balance - amount
            save_referrals(referrals_data)
            del user_states[user_id]
            
            new_balance = referrals_data[target_key]["balance"]
            bot.reply_to(msg, f"✅ <b>تم خصم الرصيد بنجاح!</b>\n\n👤 المستخدم: <code>{target_user_id}</code>\n💰 المبلغ المخصوم: <b>${amount:.2f}</b>\n💵 الرصيد السابق: <b>${old_balance:.2f}</b>\n💵 الرصيد الجديد: <b>${new_balance:.2f}</b>", parse_mode="HTML")
            
            try:
                target_lang = get_user_language(target_user_id)
                if target_lang == "ar":
                    notify_msg = f"⚠️ <b>تم خصم رصيد!</b>\n\nتم خصم <b>${amount:.2f}</b> من رصيدك بواسطة الأدمن.\n💵 رصيدك الحالي: <b>${new_balance:.2f}</b>"
                else:
                    notify_msg = f"⚠️ <b>Balance Deducted!</b>\n\n<b>${amount:.2f}</b> has been deducted from your balance by admin.\n💵 Your current balance: <b>${new_balance:.2f}</b>"
                bot.send_message(target_user_id, notify_msg, parse_mode="HTML")
            except:
                pass
        except ValueError:
            bot.reply_to(msg, "❌ الصيغة غير صحيحة! استخدم: USER_ID AMOUNT\n\nمثال: 123456789 5.00")
    
    elif action == "edit_welcome_ar":
        new_message = msg.text.strip()
        if len(new_message) < 10:
            bot.reply_to(msg, "❌ الرسالة قصيرة جداً!")
            return
        messages = load_welcome_messages()
        messages["ar"] = new_message
        save_welcome_messages(messages)
        del user_states[user_id]
        bot.reply_to(msg, "✅ تم تحديث رسالة الترحيب العربية!")
    
    elif action == "edit_welcome_en":
        new_message = msg.text.strip()
        if len(new_message) < 10:
            bot.reply_to(msg, "❌ Message is too short!")
            return
        messages = load_welcome_messages()
        messages["en"] = new_message
        save_welcome_messages(messages)
        del user_states[user_id]
        bot.reply_to(msg, "✅ English welcome message updated!")
    
    elif action and action.startswith("edit_button_link_"):
        link_key = action.replace("edit_button_link_", "")
        new_link = msg.text.strip()
        if not new_link.startswith("https://"):
            bot.reply_to(msg, "❌ الرابط يجب أن يبدأ بـ https://\n❌ Link must start with https://")
            return
        links = load_button_links()
        links[link_key] = new_link
        save_button_links(links)
        del user_states[user_id]
        bot.reply_to(msg, f"✅ تم تحديث الرابط بنجاح!\n✅ Link updated successfully!\n\n🔗 {new_link}")
    
    elif action == "otp_btn_add_name":
        btn_name = msg.text.strip()
        if len(btn_name) < 1:
            bot.reply_to(msg, "❌ اسم الزر قصير جداً!")
            return
        user_states[user_id] = {"action": "otp_btn_add_url", "btn_name": btn_name}
        bot.reply_to(msg, f"✅ اسم الزر: <b>{btn_name}</b>\n\nالآن أرسل رابط الزر:\n(مثال: https://t.me/YourChannel)", parse_mode="HTML")
    
    elif action == "otp_btn_add_url":
        btn_url = msg.text.strip()
        if not btn_url.startswith("https://"):
            bot.reply_to(msg, "❌ الرابط يجب أن يبدأ بـ https://")
            return
        btn_name = state.get("btn_name", "Button")
        otp_buttons = load_otp_buttons()
        otp_buttons.append({"name": btn_name, "url": btn_url})
        save_otp_buttons(otp_buttons)
        del user_states[user_id]
        bot.reply_to(msg, f"✅ تم إضافة الزر بنجاح!\n\n📝 الاسم: <b>{btn_name}</b>\n🔗 الرابط: {btn_url}", parse_mode="HTML")
    
    elif action == "otp_btn_edit_name":
        btn_idx = state.get("btn_idx", 0)
        new_name = msg.text.strip()
        if len(new_name) < 1:
            bot.reply_to(msg, "❌ اسم الزر قصير جداً!")
            return
        otp_buttons = load_otp_buttons()
        if btn_idx < len(otp_buttons):
            otp_buttons[btn_idx]["name"] = new_name
            save_otp_buttons(otp_buttons)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث اسم الزر إلى: <b>{new_name}</b>", parse_mode="HTML")
        else:
            bot.reply_to(msg, "❌ الزر غير موجود!")
            del user_states[user_id]
    
    elif action == "otp_btn_edit_url":
        btn_idx = state.get("btn_idx", 0)
        new_url = msg.text.strip()
        if not new_url.startswith("https://"):
            bot.reply_to(msg, "❌ الرابط يجب أن يبدأ بـ https://")
            return
        otp_buttons = load_otp_buttons()
        if btn_idx < len(otp_buttons):
            otp_buttons[btn_idx]["url"] = new_url
            save_otp_buttons(otp_buttons)
            del user_states[user_id]
            bot.reply_to(msg, f"✅ تم تحديث رابط الزر إلى:\n🔗 {new_url}", parse_mode="HTML")
        else:
            bot.reply_to(msg, "❌ الزر غير موجود!")
            del user_states[user_id]
    
    elif action == "withdraw_details":
        method = state.get("method", "Unknown")
        method_key = state.get("method_key", "unknown")
        details = msg.text.strip()
        lang = get_user_language(user_id)
        
        if len(details) < 5:
            msg_text = "❌ التفاصيل غير صحيحة!" if lang == "ar" else "❌ Invalid details!"
            bot.reply_to(msg, msg_text)
            return
        
        referral_data = get_user_referral_data(user_id)
        balance = referral_data.get("balance", 0.0)
        settings = load_referral_settings()
        min_withdrawal = settings.get("min_withdrawal", 5.0)
        
        if balance < min_withdrawal:
            msg_text = f"❌ رصيدك غير كافي! الحد الأدنى: ${min_withdrawal}" if lang == "ar" else f"❌ Insufficient balance! Minimum: ${min_withdrawal}"
            bot.reply_to(msg, msg_text)
            del user_states[user_id]
            return
        
        global REFERRALS
        REFERRALS = load_referrals()
        REFERRALS[str(user_id)]["balance"] = 0.0
        save_referrals(REFERRALS)
        
        request_id = str(uuid.uuid4())[:8]
        withdrawal_request = {
            "id": request_id,
            "user_id": user_id,
            "amount": balance,
            "method": method,
            "method_key": method_key,
            "details": details,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "status": "pending"
        }
        
        requests_list = load_withdrawal_requests()
        requests_list.append(withdrawal_request)
        save_withdrawal_requests(requests_list)
        
        del user_states[user_id]
        
        if lang == "ar":
            bot.reply_to(
                msg,
                f"✅ <b>تم إرسال طلب السحب!</b>\n\n"
                f"🆔 رقم الطلب: <code>{request_id}</code>\n"
                f"💵 المبلغ: <b>${balance:.2f}</b>\n"
                f"📝 الطريقة: {method}\n"
                f"📋 التفاصيل: <code>{details}</code>\n\n"
                f"⏳ <b>الحالة:</b> قيد المعالجة\n"
                f"سيتم إشعارك عند الموافقة أو الرفض.",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(
                msg,
                f"✅ <b>Withdrawal request submitted!</b>\n\n"
                f"🆔 Request ID: <code>{request_id}</code>\n"
                f"💵 Amount: <b>${balance:.2f}</b>\n"
                f"📝 Method: {method}\n"
                f"📋 Details: <code>{details}</code>\n\n"
                f"⏳ <b>Status:</b> Processing\n"
                f"You will be notified when approved or rejected.",
                parse_mode="HTML"
            )
        
        admin_markup = InlineKeyboardMarkup(row_width=2)
        admin_markup.add(
            InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"wd_approve_{request_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"wd_reject_{request_id}")
        )
        
        user_data_for_admin = USERS.get(str(user_id), {})
        user_referral_for_admin = get_user_referral_data(user_id)
        
        admin_join_date = user_data_for_admin.get("join_date", "غير محدد")
        admin_total_codes = user_data_for_admin.get("activations", 0)
        admin_total_referrals = len(user_referral_for_admin.get("referrals", []))
        admin_active_referrals = user_referral_for_admin.get("active_referrals", 0)
        admin_total_earned = user_referral_for_admin.get("total_earned", 0.0)
        
        admin_notification = (
            f"📋 <b>طلب سحب جديد!</b>\n\n"
            f"🆔 رقم الطلب: <code>{request_id}</code>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 <b>بيانات المستخدم:</b>\n"
            f"├ 🆔 ID: <code>{user_id}</code>\n"
            f"├ 📅 تاريخ الانضمام: {admin_join_date}\n"
            f"├ 📊 إجمالي الأكواد: {admin_total_codes}\n"
            f"├ 👥 إجمالي الإحالات: {admin_total_referrals}\n"
            f"├ ✅ إحالات نشطة: {admin_active_referrals}\n"
            f"└ 💰 إجمالي الأرباح: ${admin_total_earned:.2f}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💳 <b>تفاصيل السحب:</b>\n"
            f"├ 💵 المبلغ: <b>${balance:.2f}</b>\n"
            f"├ ?? الطريقة: {method}\n"
            f"└ 📋 التفاصيل: <code>{details}</code>\n\n"
            f"⏳ الحالة: قيد الانتظار"
        )
        
        for admin_id in ADMINS:
            try:
                bot.send_message(
                    admin_id,
                    admin_notification,
                    parse_mode="HTML",
                    reply_markup=admin_markup
                )
            except:
                pass
    
    elif action == "change_site_username":
        global USERNAME, USERNAME2, USERNAME3
        site_key = state.get("site_key")
        account_id = state.get("account_id")
        new_username = msg.text.strip()
        
        accounts = get_site_accounts(site_key)
        account_found = False
        
        for idx, acc in enumerate(accounts):
            if acc.get("id") == account_id:
                accounts[idx]["username"] = new_username
                account_found = True
                
                if idx == 0:
                    if site_key == "GROUP":
                        USERNAME = new_username
                    elif site_key == "Fly sms":
                        USERNAME2 = new_username
                    elif site_key == "Number_Panel":
                        USERNAME3 = new_username
                break
        
        if account_found:
            SETTINGS[site_key]["accounts"] = accounts
            save_settings(SETTINGS)
            
            del user_states[user_id]
            site_name = SETTINGS[site_key]["name"]
            bot.reply_to(
                msg,
                f"✅ <b>تم تحديث اليوزر - {site_name}</b>\n\n"
                f"👤 اليوزر الجديد: <code>{new_username}</code>",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(msg, "❌ الحساب غير موجود!")
    
    elif action == "change_site_token":
        site_key = state.get("site_key")
        account_id = state.get("account_id")
        new_token = msg.text.strip()
        
        accounts = get_site_accounts(site_key)
        account_found = False
        
        for idx, acc in enumerate(accounts):
            if acc.get("id") == account_id:
                accounts[idx]["api_token"] = new_token
                account_found = True
                break
        
        if account_found:
            SETTINGS[site_key]["accounts"] = accounts
            save_settings(SETTINGS)
            
            del user_states[user_id]
            site_name = SETTINGS[site_key]["name"]
            bot.reply_to(
                msg,
                f"✅ <b>تم تحديث API Token - {site_name}</b>\n\n"
                f"🔐 API Token الجديد: <code>{new_token[:15]}...</code>",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(msg, "❌ الحساب غير موجود!")
    
    elif action == "change_site_password":
        global PASSWORD, PASSWORD2, PASSWORD3
        site_key = state.get("site_key")
        account_id = state.get("account_id")
        new_password = msg.text.strip()
        
        accounts = get_site_accounts(site_key)
        account_found = False
        
        for idx, acc in enumerate(accounts):
            if acc.get("id") == account_id:
                accounts[idx]["password"] = new_password
                account_found = True
                
                if idx == 0:
                    if site_key == "GROUP":
                        PASSWORD = new_password
                    elif site_key == "Fly sms":
                        PASSWORD2 = new_password
                    elif site_key == "Number_Panel":
                        PASSWORD3 = new_password
                break
        
        if account_found:
            SETTINGS[site_key]["accounts"] = accounts
            save_settings(SETTINGS)
            
            del user_states[user_id]
            site_name = SETTINGS[site_key]["name"]
            bot.reply_to(
                msg,
                f"✅ <b>تم تحديث الباسورد - {site_name}</b>\n\n"
                f"🔑 تم حفظ كلمة المرور الجديدة",
                parse_mode="HTML"
            )
        else:
            bot.reply_to(msg, "❌ الحساب غير موجود!")
    
    elif action == "add_account_username":
        site_key = state.get("site_key")
        site_name = SETTINGS[site_key]["name"]
        new_username = msg.text.strip()
        
        if not new_username:
            bot.reply_to(msg, "❌ اسم المستخدم لا يمكن أن يكون فارغاً!")
            return
        
        if site_key == "iVASMS":
            user_states[user_id] = {
                "action": "add_account_password",
                "site_key": site_key,
                "username": new_username
            }
            bot.reply_to(
                msg,
                f"➕ <b>إضافة حساب جديد - {site_name}</b>\n\n"
                f"✅ اليوزر: <code>{new_username}</code>\n\n"
                f"📝 الخطوة 2/3: أرسل كلمة المرور (Password):",
                parse_mode="HTML"
            )
        else:
            user_states[user_id] = {
                "action": "add_account_password",
                "site_key": site_key,
                "username": new_username
            }
            bot.reply_to(
                msg,
                f"➕ <b>إضافة حساب جديد - {site_name}</b>\n\n"
                f"✅ اليوزر: <code>{new_username}</code>\n\n"
                f"📝 الخطوة 2/2: أرسل كلمة المرور (Password):",
                parse_mode="HTML"
            )
    
    elif action == "add_account_api_token":
        site_key = state.get("site_key")
        site_name = SETTINGS[site_key]["name"]
        api_token = msg.text.strip()
        
        if not api_token:
            bot.reply_to(msg, "❌ API Token لا يمكن أن يكون فارغاً!")
            return
        
        new_account = add_account(site_key, "", "")
        if new_account:
            for idx, acc in enumerate(SETTINGS[site_key]["accounts"]):
                if acc["id"] == new_account["id"]:
                    SETTINGS[site_key]["accounts"][idx]["api_token"] = api_token
                    save_settings(SETTINGS)
                    break
            
            del user_states[user_id]
            
            if SETTINGS[site_key]["enabled"]:
                new_account["api_token"] = api_token
                thread = Thread(target=start_monitoring_for_account, args=(site_key, new_account), daemon=True)
                thread.start()
                print(f"🚀 بدء مراقبة فورية للحساب الجديد: {api_token[:10]}... ({site_name})")
                
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"🔐 API Token: <code>{api_token[:15]}...</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"🚀 <b>تم بدء المراقبة فوراً!</b>",
                    parse_mode="HTML"
                )
            else:
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"🔐 API Token: <code>{api_token[:15]}...</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"⚠️ الموقع غير مفعل حالياً",
                    parse_mode="HTML"
                )
        else:
            bot.reply_to(msg, "❌ فشل إضافة الحساب!")
    
    elif action == "add_account_password":
        site_key = state.get("site_key")
        site_name = SETTINGS[site_key]["name"]
        username = state.get("username")
        password = msg.text.strip()
        
        if not password:
            bot.reply_to(msg, "❌ كلمة المرور لا يمكن أن تكون فارغة!")
            return
        
        if site_key == "iVASMS":
            user_states[user_id] = {
                "action": "add_account_api_key",
                "site_key": site_key,
                "username": username,
                "password": password
            }
            bot.reply_to(
                msg,
                f"➕ <b>إضافة حساب جديد - {site_name}</b>\n\n"
                f"✅ اليوزر: <code>{username}</code>\n"
                f"✅ الباسورد: <code>{password}</code>\n\n"
                f"📝 الخطوة 3/3: أرسل مفتاح API (API Key):",
                parse_mode="HTML"
            )
            return
        
        new_account = add_account(site_key, username, password)
        
        if new_account:
            del user_states[user_id]
            
            if SETTINGS[site_key]["enabled"]:
                thread = Thread(target=start_monitoring_for_account, args=(site_key, new_account), daemon=True)
                thread.start()
                print(f"🚀 بدء مراقبة فورية للحساب الجديد: {username} ({site_name})")
                
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"👤 اليوزر: <code>{username}</code>\n"
                    f"🔑 الباسورد: <code>{password}</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"🚀 <b>تم بدء المراقبة فوراً!</b>",
                    parse_mode="HTML"
                )
            else:
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"👤 اليوزر: <code>{username}</code>\n"
                    f"🔑 الباسورد: <code>{password}</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"⚠️ الموقع غير مفعل حالياً",
                    parse_mode="HTML"
                )
        else:
            bot.reply_to(msg, "❌ فشل إضافة الحساب!")
    
    elif action == "add_account_api_key":
        site_key = state.get("site_key")
        site_name = SETTINGS[site_key]["name"]
        username = state.get("username")
        password = state.get("password")
        api_key = msg.text.strip()
        
        if not api_key:
            bot.reply_to(msg, "❌ مفتاح API لا يمكن أن يكون فارغاً!")
            return
        
        new_account = add_account(site_key, username, password)
        
        if new_account:
            for idx, acc in enumerate(SETTINGS[site_key]["accounts"]):
                if acc["id"] == new_account["id"]:
                    SETTINGS[site_key]["accounts"][idx]["api_key"] = api_key
                    save_settings(SETTINGS)
                    break
            
            del user_states[user_id]
            
            if SETTINGS[site_key]["enabled"]:
                new_account["api_key"] = api_key
                thread = Thread(target=start_monitoring_for_account, args=(site_key, new_account), daemon=True)
                thread.start()
                print(f"🚀 بدء مراقبة فورية للحساب الجديد: {username} ({site_name})")
                
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"👤 اليوزر: <code>{username}</code>\n"
                    f"🔑 الباسورد: <code>{password}</code>\n"
                    f"🔐 مفتاح API: <code>{api_key[:10]}...</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"🚀 <b>تم بدء المراقبة فوراً!</b>",
                    parse_mode="HTML"
                )
            else:
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الحساب بنجاح - {site_name}</b>\n\n"
                    f"👤 اليوزر: <code>{username}</code>\n"
                    f"🔑 الباسورد: <code>{password}</code>\n"
                    f"🔐 مفتاح API: <code>{api_key[:10]}...</code>\n"
                    f"🆔 ID: <code>{new_account['id'][:8]}...</code>\n\n"
                    f"⚠️ الموقع غير مفعل حالياً",
                    parse_mode="HTML"
                )
        else:
            bot.reply_to(msg, "❌ فشل إضافة الحساب!")
    
    elif action == "change_site_interval":
        global CHECK_INTERVAL, CHECK_INTERVAL2, CHECK_INTERVAL3
        site_key = state.get("site_key")
        
        try:
            new_interval = int(msg.text.strip())
            
            if new_interval < 1 or new_interval > 300:
                bot.reply_to(msg, "❌ الفترة يجب أن تكون بين 1 و 300 ثانية!")
                return
            
            SETTINGS[site_key]["check_interval"] = new_interval
            save_settings(SETTINGS)
            
            if site_key == "GROUP":
                CHECK_INTERVAL = new_interval
            elif site_key == "Fly sms":
                CHECK_INTERVAL2 = new_interval
            elif site_key == "Number_Panel":
                CHECK_INTERVAL3 = new_interval
            
            del user_states[user_id]
            site_name = SETTINGS[site_key]["name"]
            bot.reply_to(
                msg,
                f"✅ <b>تم تحديث فترة البحث - {site_name}</b>\n\n"
                f"⏱ الفترة الجديدة: {new_interval} ثانية\n\n"
                f"⚠️ سيتم تطبيق التغيير في الدورة القادمة",
                parse_mode="HTML"
            )
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "change_site_timeout":
        global HTTP_TIMEOUT, HTTP_TIMEOUT2, HTTP_TIMEOUT3
        site_key = state.get("site_key")
        
        try:
            new_timeout = int(msg.text.strip())
            
            if new_timeout < 5 or new_timeout > 300:
                bot.reply_to(msg, "❌ وقت الانتظار يجب أن يكون بين 5 و 300 ثانية!")
                return
            
            SETTINGS[site_key]["timeout"] = new_timeout
            save_settings(SETTINGS)
            
            if site_key == "GROUP":
                HTTP_TIMEOUT = new_timeout
            elif site_key == "Fly sms":
                HTTP_TIMEOUT2 = new_timeout
            elif site_key == "Number_Panel":
                HTTP_TIMEOUT3 = new_timeout
            
            del user_states[user_id]
            site_name = SETTINGS[site_key]["name"]
            bot.reply_to(
                msg,
                f"✅ <b>تم تحديث وقت الانتظار - {site_name}</b>\n\n"
                f"⏳ الوقت الجديد: {new_timeout} ثانية",
                parse_mode="HTML"
            )
        except ValueError:
            bot.reply_to(msg, "❌ يرجى إدخال رقم صحيح!")
    
    elif action == "add_group":
        try:
            group_id = int(msg.text.strip())
            
            try:
                chat = bot.get_chat(group_id)
                admins = bot.get_chat_administrators(group_id)
                
                bot_is_admin = False
                for admin in admins:
                    if admin.user.id == bot.get_me().id:
                        bot_is_admin = True
                        break
                
                if not bot_is_admin:
                    bot.reply_to(msg, "❌ البوت ليس admin في هذا الجروب!")
                    return
                
                if group_id in GROUPS:
                    bot.reply_to(msg, "⚠️ هذا الجروب مضاف بالفعل!")
                    return
                
                GROUPS.append(group_id)
                save_groups()
                del user_states[user_id]
                
                bot.reply_to(
                    msg,
                    f"✅ <b>تم إضافة الجروب بنجاح!</b>\n\n"
                    f"📱 الاسم: <b>{chat.title}</b>\n"
                    f"🆔 ID: <code>{group_id}</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                bot.reply_to(msg, f"❌ خطأ: {e}\n\nتأكد أن:\n• البوت admin في الجروب\n• ID الجروب صحيح")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")
    
    elif action == "remove_group":
        try:
            group_id = int(msg.text.strip())
            
            if group_id in GROUPS:
                GROUPS.remove(group_id)
                save_groups()
                del user_states[user_id]
                bot.reply_to(msg, f"✅ تم حذف الجروب!\n\nID: <code>{group_id}</code>", parse_mode="HTML")
            else:
                bot.reply_to(msg, "❌ الجروب غير موجود!")
        except ValueError:
            bot.reply_to(msg, "❌ ID غير صحيح!")
    
    elif user_id in broadcast_state:
        state = broadcast_state[user_id]
        broadcast_type = state.get("type")
        step = state.get("step")
        
        if step != "waiting_message":
            return
        
        saved_msg = {
            "content_type": msg.content_type,
            "chat_id": msg.chat.id,
            "message_id": msg.message_id
        }
        
        if msg.content_type == "text":
            saved_msg["text"] = msg.text
            saved_msg["has_entities"] = bool(msg.entities)
        elif msg.content_type == "photo":
            saved_msg["file_id"] = msg.photo[-1].file_id
            saved_msg["caption"] = msg.caption
        elif msg.content_type == "video":
            saved_msg["file_id"] = msg.video.file_id
            saved_msg["caption"] = msg.caption
        elif msg.content_type == "document":
            saved_msg["file_id"] = msg.document.file_id
            saved_msg["caption"] = msg.caption
        elif msg.content_type == "audio":
            saved_msg["file_id"] = msg.audio.file_id
            saved_msg["caption"] = msg.caption
        elif msg.content_type == "voice":
            saved_msg["file_id"] = msg.voice.file_id
            saved_msg["caption"] = msg.caption
        elif msg.content_type == "sticker":
            saved_msg["file_id"] = msg.sticker.file_id
        
        broadcast_state[user_id]["message"] = saved_msg
        broadcast_state[user_id]["step"] = "confirm"
        
        if broadcast_type == "forward":
            broadcast_label = "📤 إعادة توجيه للمستخدمين"
        else:
            broadcast_label = "📣 مستخدمي البوت الرئيسي"
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
        InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_broadcast"),
            InlineKeyboardButton("🔙 إلغاء", callback_data="cancel_broadcast")
        )
        
        bot.reply_to(
            msg,
            f"📣 <b>تأكيد الإذاعة</b>\n\n"
            f"📍 الوجهة: {broadcast_label}\n"
            f"📝 نوع الرسالة: {msg.content_type}\n\n"
            f"⚠️ هل أنت متأكد من إرسال هذه الرسالة؟",
            parse_mode="HTML",
            reply_markup=markup
        )
    
def get_country_info(number: str):
    cleaned_num = clean_number(number)
    country_codes = detect_country_from_number(number)
    if country_codes:
        return country_codes[0], country_codes[1]
    return "Unknown", "🌐"

def normalize_number(number):

    if not number:
        return ""

    cleaned = re.sub(r'\D', '', str(number))
    return cleaned

COLLECTED_CODES_FILE = "collected_codes.json"
collected_codes = []

def load_collected_codes():
    global collected_codes
    if os.path.exists(COLLECTED_CODES_FILE):
        try:
            with open(COLLECTED_CODES_FILE, 'r', encoding='utf-8') as f:
                collected_codes = json.load(f)
        except:
            collected_codes = []
    return collected_codes

def save_collected_codes():
    with open(COLLECTED_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(collected_codes, f, indent=2, ensure_ascii=False)

def _build_live_traffic_text(user_id=None):
    """بناء نص Live Traffic بالعربي أو الانجليزي حسب لغة المستخدم"""
    lang = get_user_language(user_id) if user_id else "en"
    total, results_pct, country_pcts, top_country, top_platform = get_live_traffic_stats(minutes=60)

    now_str = datetime.now().strftime("%H:%M:%S")
    num_emojis = [
        "<tg-emoji emoji-id='6010326763861710490'>1️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010474107009766823'>2️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010323074484803109'>3️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010250708580832207'>4️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6008340663609858968'>5️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6008314305395562677'>6️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6008144065776850595'>7️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6007807516434502720'>8️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010526058934180583'>9️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010274537059390092'>🔟</tg-emoji>",
        "<tg-emoji emoji-id='6010190098002351326'>1️⃣1️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010568476031194227'>1️⃣2️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010209781837469655'>1️⃣3️⃣</tg-emoji>",
        "<tg-emoji emoji-id='6010475764867143917'>1️⃣4️⃣</tg-emoji>",
    ]

    PLATFORM_ICONS = {
        "WhatsApp":  "<tg-emoji emoji-id='5138693920284214322'>📱</tg-emoji>",
        "Facebook":  "<tg-emoji emoji-id='5136559729559995450'>📱</tg-emoji>",
        "Telegram":  "<tg-emoji emoji-id='5136828508613379215'>📱</tg-emoji>",
        "Twitter":   "<tg-emoji emoji-id='5330337435500951363'>📱</tg-emoji>",
        "TikTok":    "<tg-emoji emoji-id='6154555369138954544'>📱</tg-emoji>",
        "Instagram": "<tg-emoji emoji-id='5136634337436894358'>📱</tg-emoji>",
        "Imo":       "💬",
        "IMO":       "💬",
    }
    DEFAULT_ICON = "<tg-emoji emoji-id='5138693920284214322'>📱</tg-emoji>"

    def get_plt_icon(plt):
        return PLATFORM_ICONS.get(plt, DEFAULT_ICON)

    top_plt_icon = get_plt_icon(top_platform) if top_platform else DEFAULT_ICON

    if lang == "ar":
        lines = []
        lines.append("<tg-emoji emoji-id='5264919878082509254'>🟢</tg-emoji> <b>Live Traffic</b>\n")
        lines.append(f"<tg-emoji emoji-id='5337115387815306340'>📅</tg-emoji> <b>Window:</b> Last 60 minutes")
        lines.append(f"<tg-emoji emoji-id='5262880537416054812'>📨</tg-emoji> <b>Results Sent:</b> {total}")
        if top_country:
            top_flag = get_country_flags(top_country)
            lines.append(f"<tg-emoji emoji-id='5415655814079723871'>🏆</tg-emoji> <b>Top Country:</b> {top_flag} {top_country} {top_plt_icon}\n")
        else:
            lines.append(f"<tg-emoji emoji-id='5415655814079723871'>🏆</tg-emoji> <b>Top Country:</b> —\n")
        lines.append("<tg-emoji emoji-id='6114021507908767611'>🌍</tg-emoji> <b>Top Countries:</b>")
        if country_pcts:
            for i, (cname, pct, plts) in enumerate(country_pcts[:10]):
                emoji_num = num_emojis[i] if i < len(num_emojis) else f"{i+1}."
                flag = get_country_flags(cname)
                plt_icons = "".join(get_plt_icon(p) for p in plts)
                lines.append(f"{emoji_num} {flag} {cname} <tg-emoji emoji-id='5416117059207572332'>🔽</tg-emoji> {pct}% {plt_icons}")
        else:
            lines.append("<tg-emoji emoji-id='6269145070826426586'>📭</tg-emoji> No data in the last 60 minutes")
        lines.append(f"\n<tg-emoji emoji-id='6206118633370818254'>🕒</tg-emoji> <b>Last update: {now_str}</b>")
        refresh_btn_txt = " Refresh"

        lines = []
        lines.append("<tg-emoji emoji-id='5264919878082509254'>🟢</tg-emoji> <b>Live Traffic</b>\n")
        lines.append(f"<tg-emoji emoji-id='5337115387815306340'>📅</tg-emoji> <b>Window:</b> Last 60 minutes")
        lines.append(f"<tg-emoji emoji-id='5262880537416054812'>📨</tg-emoji> <b>Results Sent:</b> {total}")
        if top_country:
            top_flag = get_country_flags(top_country)
            lines.append(f"<tg-emoji emoji-id='5415655814079723871'>🏆</tg-emoji> <b>Top Country:</b> {top_flag} {top_country} {top_plt_icon}\n")
        else:
            lines.append(f"<tg-emoji emoji-id='5415655814079723871'>🏆</tg-emoji> <b>Top Country:</b> —\n")
        lines.append("<tg-emoji emoji-id='6114021507908767611'>🌍</tg-emoji> <b>Top Countries:</b>")
        if country_pcts:
            for i, (cname, pct, plts) in enumerate(country_pcts[:10]):
                emoji_num = num_emojis[i] if i < len(num_emojis) else f"{i+1}."
                flag = get_country_flags(cname)
                plt_icons = "".join(get_plt_icon(p) for p in plts)
                lines.append(f"{emoji_num} {flag} {cname} <tg-emoji emoji-id='5416117059207572332'>🔽</tg-emoji> {pct}% {plt_icons}")
        else:
            lines.append("<tg-emoji emoji-id='6269145070826426586'>📭</tg-emoji> No data in the last 60 minutes")
        lines.append(f"\n<tg-emoji emoji-id='6206118633370818254'>🕒</tg-emoji> <b>Last update: {now_str}</b>")
        refresh_btn_txt = " Refresh"

    return "\n".join(lines), refresh_btn_txt


def _send_live_traffic(chat_id, user_id=None):
    """إرسال رسالة Live Traffic"""
    text, refresh_btn_txt = _build_live_traffic_text(user_id)

    mu = InlineKeyboardMarkup()
    try:
        mu.add(InlineKeyboardButton(
            refresh_btn_txt,
            callback_data="live_traffic_refresh",
            icon_custom_emoji_id="5310278924616356636",
            style="danger"
        ))
    except:
        mu.add(InlineKeyboardButton(refresh_btn_txt, callback_data="live_traffic_refresh"))

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=mu)


@bot.callback_query_handler(func=lambda call: call.data == "live_traffic_refresh")
def live_traffic_refresh_cb(call):
    user_id = call.from_user.id
    if is_banned(user_id):
        bot.answer_callback_query(call.id)
        return
    lang = get_user_language(user_id)
    bot.answer_callback_query(call.id, "🔄Refreshing..." if lang == "ar" else "🔄 Refreshing...")

    text, refresh_btn_txt = _build_live_traffic_text(user_id)

    mu = InlineKeyboardMarkup()
    try:
        mu.add(InlineKeyboardButton(
            refresh_btn_txt,
            callback_data="live_traffic_refresh",
            icon_custom_emoji_id="5310278924616356636",
            style="danger"
        ))
    except:
        mu.add(InlineKeyboardButton(refresh_btn_txt, callback_data="live_traffic_refresh"))

    try:
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=mu
        )
    except Exception:
        pass


def send_otp_to_user(number, sms_text, full_number, service_name, otp_code=None, site_key=None):
    # استخراج احتياطي للخاص فقط عندما لا يصل otp_code من المصدر.
    # لا نغيّر otp_code الأصلي حتى تظل رسالة الجروب كما هي.
    private_otp_code = otp_code
    if not private_otp_code and sms_text:
        try:
            private_otp_code, _ = extract_from_message(sms_text)
        except Exception:
            private_otp_code = None

    # حفظ الكود الحقيقي إذا كان من المصادر والخدمات المطلوبة
    try:
        service_upper = str(service_name).upper()
        valid_sites = ["Fly sms", "IMS", "Hadi_SMS"]
        valid_services = ["FACEBOOK", "WHATSAPP", "TIKTOK"]
        
        is_valid_service = any(s in service_upper for s in valid_services)
        
        if site_key in valid_sites and is_valid_service:
            global collected_codes
            # نتحقق إذا كان الكود موجوداً مسبقاً لتجنب التكرار
            is_duplicate = any(c.get("otp") == otp_code and c.get("number") == full_number for c in collected_codes)
            if not is_duplicate:
                new_code = {
                    "number": full_number,
                    "sms": sms_text,
                    "service": service_upper,
                    "otp": otp_code,
                    "site": site_key,
                    "timestamp": __import__("time").time()
                }
                collected_codes.append(new_code)
                if len(collected_codes) > 200:
                    collected_codes = collected_codes[-200:]
                save_collected_codes()
    except Exception as e:
        print(f"Error saving collected code: {e}")

    # ── تسجيل في Live Traffic ────────────────────────────────────────────────
    try:
        _country_for_traffic = None
        try:
            _parsed = phonenumbers.parse("+" + str(full_number).lstrip("+"))
            _country_for_traffic = geocoder.description_for_number(_parsed, "en") or "Unknown"
        except Exception:
            _country_for_traffic = "Unknown"

        _platform_for_traffic = "Unknown"
        _sn = str(service_name or "").lower()
        if "whatsapp" in _sn or "واتساب" in _sn or "واتس" in _sn:
            _platform_for_traffic = "WhatsApp"
        elif "facebook" in _sn or "فيسبوك" in _sn or "meta" in _sn:
            _platform_for_traffic = "Facebook"
        elif "instagram" in _sn or "انستقرام" in _sn or "انستا" in _sn:
            _platform_for_traffic = "Instagram"
        elif "telegram" in _sn or "تيليجرام" in _sn or "تلجرام" in _sn:
            _platform_for_traffic = "Telegram"
        elif "tiktok" in _sn or "تيك توك" in _sn:
            _platform_for_traffic = "TikTok"
        elif "twitter" in _sn or "تويتر" in _sn or "x.com" in _sn:
            _platform_for_traffic = "Twitter"
        elif "snapchat" in _sn or "سناب" in _sn:
            _platform_for_traffic = "Snapchat"
        elif "google" in _sn or "gmail" in _sn or "جوجل" in _sn:
            _platform_for_traffic = "Google"
        elif "netflix" in _sn:
            _platform_for_traffic = "Netflix"
        elif "paypal" in _sn:
            _platform_for_traffic = "PayPal"
        elif "imo" in _sn:
            _platform_for_traffic = "IMO"
        elif sms_text:
            _st = sms_text.lower()
            if "whatsapp" in _st or "واتساب" in _st:
                _platform_for_traffic = "WhatsApp"
            elif "facebook" in _st or "فيسبوك" in _st or "meta" in _st:
                _platform_for_traffic = "Facebook"
            elif "instagram" in _st or "انستقرام" in _st:
                _platform_for_traffic = "Instagram"
            elif "telegram" in _st or "تيليجرام" in _st:
                _platform_for_traffic = "Telegram"
            elif "tiktok" in _st or "تيك توك" in _st:
                _platform_for_traffic = "TikTok"
            elif "twitter" in _st or "تويتر" in _st:
                _platform_for_traffic = "Twitter"
            elif "snapchat" in _st or "سناب" in _st:
                _platform_for_traffic = "Snapchat"
            elif "google" in _st or "gmail" in _st:
                _platform_for_traffic = "Google"
        log_live_traffic(full_number, _country_for_traffic, _platform_for_traffic)
    except Exception as _lt_err:
        print(f"⚠️ live traffic log error: {_lt_err}")
    # ────────────────────────────────────────────────────────────────────────

    normalized_incoming = normalize_number(number)
    
    group_message = format_otp_message_v2(number, sms_text, service_name, otp_code, is_group=True)
    
    sent_to_users = []
    users_copy = dict(USERS)
    for user_id_str, user_data in users_copy.items():
        selected_nums = user_data.get("selected_numbers", [])
        if not selected_nums and user_data.get("selected_number"):
            selected_nums = [user_data.get("selected_number")]
            
        if not selected_nums:
            continue

        is_match = False
        for s_num in selected_nums:
            normalized_selected = normalize_number(s_num)
            if (normalized_incoming == normalized_selected or 
                normalized_incoming.endswith(normalized_selected) or 
                normalized_selected.endswith(normalized_incoming) or
                full_number == s_num):
                is_match = True
                break

        if is_match:
            # Format private message with user_id to get balance/reward
            private_message = format_otp_message_private(number, sms_text, service_name, otp_code, user_id=int(user_id_str))
            
            try:
                priv_keyboard = create_private_otp_keyboard(private_otp_code, button_style="primary") if private_otp_code else None
                bot.send_message(
                    int(user_id_str),
                    private_message,
                    parse_mode="HTML",
                    reply_markup=priv_keyboard
                )
                print(f"✅ تم إرسال الكود للمستخدم {user_id_str} في الخاص بنجاح")
                sent_to_users.append(user_id_str)
                
                if "activations" not in USERS.get(user_id_str, {}):
                    if user_id_str in USERS:
                        USERS[user_id_str]["activations"] = 0
                if user_id_str in USERS:
                    USERS[user_id_str]["activations"] = USERS[user_id_str].get("activations", 0) + 1
                save_users()
                
                try:
                    add_code_bonus(int(user_id_str))
                except Exception as bonus_err:
                    print(f"⚠️ خطأ في إضافة بونص للمستخدم {user_id_str}: {bonus_err}")
            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id_str}: {str(e)}")

    # Find country name from the number if possible
    country_name = "Unknown"
    try:
        parsed_number = phonenumbers.parse("+" + full_number)
        country_name = geocoder.description_for_number(parsed_number, "en")
    except:
        pass
    update_statistics(country_name)
    
    # حذف رسائل الأكواد من الجروبات بعد 15 دقيقة (900 ثانية)
    GROUP_CODE_DELETE_DELAY = 15 * 60

    def schedule_group_code_deletion(sent_message):
        def delete_sent_message():
            try:
                bot.delete_message(sent_message.chat.id, sent_message.message_id)
                print(f"🗑️ تم حذف رسالة الكود من الجروب: {sent_message.chat.id}")
            except Exception as delete_error:
                print(f"⚠️ تعذر حذف رسالة الكود من الجروب {getattr(sent_message.chat, 'id', 'unknown')}: {delete_error}")

        deletion_timer = threading.Timer(GROUP_CODE_DELETE_DELAY, delete_sent_message)
        deletion_timer.daemon = True
        deletion_timer.start()

    sent_groups = set()
    msg_to_group = group_message
    
    group_keyboard = create_group_otp_keyboard(otp_code, button_style="success")
    private_keyboard = create_private_otp_keyboard(private_otp_code, button_style="primary")
    
    if OTP_GROUP and OTP_GROUP not in sent_groups:
        try:
            sent_message = bot.send_message(OTP_GROUP, msg_to_group, parse_mode="HTML", disable_web_page_preview=True, reply_markup=group_keyboard)
            schedule_group_code_deletion(sent_message)
            sent_groups.add(OTP_GROUP)
            print(f"✅ تم الإرسال لمجموعة OTP_GROUP: {OTP_GROUP}")
            

        except Exception as e:
            print(f"❌ خطأ إرسال لمجموعة OTP: {str(e)}")
    
    if not GROUPS and os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, "r") as f:
                loaded_groups = json.load(f)
                for g in loaded_groups:
                    if g not in GROUPS:
                        GROUPS.append(g)
        except:
            pass

    groups_copy = list(GROUPS)
    for gid in groups_copy:
        if gid not in sent_groups:
            try:
                sent_message = bot.send_message(gid, msg_to_group, parse_mode="HTML", disable_web_page_preview=True, reply_markup=group_keyboard)
                schedule_group_code_deletion(sent_message)
                sent_groups.add(gid)
                print(f"✅ تم الإرسال لمجموعة من القائمة: {gid}")
            except Exception as e:
                print(f"❌ خطأ إرسال لمجموعة {gid}: {str(e)}")

    return sent_to_users


def load_last_seen_key():
    global last_seen_key
    if os.path.exists(LAST_MESSAGE_FILE):
        try:
            with open(LAST_MESSAGE_FILE, "r", encoding="utf-8") as f:
                last_seen_key = f.read().strip()
                print(f"📋 تم تحميل آخر رسالة مشاهدة: {last_seen_key[:50]}..." if last_seen_key else "📋 لا توجد رسائل سابقة")
        except:
            last_seen_key = ""
    else:
        last_seen_key = ""

def save_last_seen_key():
    try:
        with open(LAST_MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write(last_seen_key)
        print(f"💾 تم حفظ آخر رسالة مشاهدة")
    except Exception as e:
        print(f"❌ خطأ في حفظ آخر رسالة: {str(e)}")

def print_monitoring_box(site_name, username, status_icon, status_text):
    box_width = 45
    box = f"\n╔{'═' * box_width}\n  📍 {site_name}  •  👤 {username}\n  {status_icon} {status_text}\n╚{'═' * box_width}"
    print(box)

def login_site3():
    global is_logged_in_site3
    print("[Site3/Number_Panel] 🔄 محاولة تسجيل الدخول...")
    
    try:
        session3.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
        })
        
        resp = session3.get(LOGIN_PAGE_URL3, timeout=HTTP_TIMEOUT3)
        print(f"[Site3/Number_Panel] 📄 حالة GET: {resp.status_code}")
        
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            print("[Site3/Number_Panel] ⚠️ لم يتم العثور على captcha في الصفحة")
            print(f"[Site3/Number_Panel] 📋 عينة من المحتوى: {resp.text[:500]}")
            return False
        
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2
        print(f"[Site3/Number_Panel] 🧮 حل captcha: {num1} + {num2} = {captcha_answer}")
        
        payload = {
            "username": USERNAME3,
            "password": PASSWORD3,
            "capt": str(captcha_answer)
        }
        
        if "crlf" in resp.text:
            crlf_match = re.search(r"name='crlf' value='([^']+)'", resp.text)
            if crlf_match:
                payload["crlf"] = crlf_match.group(1)
                print(f"[Site3/Number_Panel] 🔑 استخراج crlf token")
        
        csrf_token = get_csrf_token_np(resp.text)
        if csrf_token:
            payload["_token"] = csrf_token
            print(f"[Site3/Number_Panel] 🔑 استخراج CSRF Token")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE_URL3,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": BASE_URL3
        }
        
        print(f"[Site3/Number_Panel] 📤 إرسال طلب تسجيل الدخول لـ: {USERNAME3}")
        resp = session3.post(LOGIN_POST_URL3, data=payload, headers=headers, timeout=HTTP_TIMEOUT3, allow_redirects=True)
        
        print(f"[Site3/Number_Panel] 📊 حالة POST: {resp.status_code}")
        print(f"[Site3/Number_Panel] 🔗 URL النهائي: {resp.url}")
        
        if ("dashboard" in resp.text.lower() or 
            "logout" in resp.text.lower() or 
            "agent" in resp.url.lower() or
            "reports" in resp.url.lower() or
            "smscdr" in resp.text.lower() or
            "signin" in resp.text.lower() or
            "dashboard" in resp.url.lower() or
            resp.url != LOGIN_PAGE_URL3):
            print("[Site3/Number_Panel] ✅ تم تسجيل الدخول بنجاح")
            is_logged_in_site3 = True
            save_cookies_site3()
            return True
        else:
            print("[Site3/Number_Panel] ❌ فشل تسجيل الدخول")
            if "incorrect" in resp.text.lower() or "invalid" in resp.text.lower():
                print("[Site3/Number_Panel] ⚠️ اسم المستخدم أو كلمة المرور غير صحيحة")
            return False
    except Exception as e:
        print(f"[Site3/Number_Panel] ❌ خطأ في تسجيل الدخول: {e}")
        import traceback
        traceback.print_exc()
        return False

def build_ajax_url_site3(wide_range=False):
    if wide_range:
        start_date = date.today() - timedelta(days=5)
        end_date = date.today() + timedelta(days=1)
    else:
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)
    
    fdate1 = f"{start_date.strftime('%Y-%m-%d')} 00:00:00"
    fdate2 = f"{end_date.strftime('%Y-%m-%d')} 23:59:59"
    
    return {
        'url': BASE_URL3 + AJAX_PATH3,
        'params': {
            'fdate1': fdate1,
            'fdate2': fdate2,
            'sEcho': '1',
            'iDisplayStart': '0',
            'iDisplayLength': '50000',
            'iSortCol_0': '0',
            'sSortDir_0': 'desc'
        }
    }

def extract_rows_from_json_site3(j):
    if j is None:
        return []
    for key in ("data", "aaData", "rows"):
        if isinstance(j, dict) and key in j:
            return j[key]
    return j if isinstance(j, list) else []

def row_to_tuple_site3(row):
    date_str = clean_html_site2(row[0]) if len(row) > 0 else ""
    number = clean_number(row[2]) if len(row) > 2 else ""
    sms = clean_html_site2(row[5]) if len(row) > 5 else ""
    key = f"{date_str}|{number}|{sms}"
    return date_str, number, sms, key

def fetch_ajax_data_np(account_session, site_key, account):
    try:
        api_token = account.get("api_token") or account.get("id")
        if not api_token or api_token == "Api Token":
            return {"aaData": []}, False
            
        api_url = "http://147.135.212.197/crapi/st/viewstats"
        params = {"token": api_token, "records": 50}
        
        
        r = account_session.get(api_url, params=params, timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            
            if isinstance(data, list):
                formatted_rows = []
                for item in data:
                    if isinstance(item, list) and len(item) >= 4:
                        row = [None] * 6
                        row[0] = item[3] 
                        row[1] = item[0] 
                        row[2] = item[1] 
                        row[5] = item[2] 
                        formatted_rows.append(row)
                return {"aaData": formatted_rows}, False
        else:
            print(f"[Number_Panel] API Status Error: {r.status_code}")
        return {"aaData": []}, False
    except Exception as e:
        print(f"[Number_Panel] API Exception: {e}")
        return None, False

def sms_loop_for_number_panel_account(site_key, account):
    account_id = account.get("id")
    api_token = account.get("api_token") or account_id
    site_name = SETTINGS[site_key]["name"]
    check_interval = SETTINGS[site_key].get("check_interval", 5)
    
    account_session = requests.Session()
    account_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    
    safe_id = "".join(x for x in api_token if x.isalnum())[:15]
    last_message_file = f"last_message_{site_key}_{safe_id}.txt"
    last_seen_key_local = ""
    
    if os.path.exists(last_message_file):
        try:
            with open(last_message_file, "r", encoding="utf-8") as f:
                last_seen_key_local = f.read().strip()
        except: pass

    print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "🌐", "بدء المراقبة عبر API...")
    
    while True:
        try:
            j, _ = fetch_ajax_data_np(account_session, site_key, {"api_token": api_token})
            rows = extract_rows_from_json_site3(j)
            
            if rows:
                valid_rows = []
                for row in rows:
                    if isinstance(row, list) and len(row) > 5:
                        date_str = clean_html_site2(row[0])
                        number = clean_number(row[2])
                        sms = clean_html_site2(row[5])
                        service_name_api = clean_html_site2(row[1]) if row[1] else ""
                        key = f"{date_str}|{number}|{sms}"
                        if date_str and number and sms:
                            valid_rows.append((date_str, number, sms, key, service_name_api))
                
                if valid_rows:
                    def get_dt(r):
                        try: return datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
                        except: return datetime.min
                    
                    valid_rows.sort(key=get_dt, reverse=True)
                    
                    if not last_seen_key_local:
                        
                        r = valid_rows[0]
                        date_str, number, sms, key, s_name = r
                        otp_val, sms_text = extract_from_message(sms)
                        display_name = f"[{s_name}]" if s_name else f"{detect_service(sms)}"
                        send_otp_to_user(clean_number(number), sms_text, number, display_name, otp_val, site_key='Fly sms')
                        
                        last_seen_key_local = key
                        with open(last_message_file, "w", encoding="utf-8") as f:
                            f.write(last_seen_key_local)
                        print(f"[{site_name}] Initialized and sent latest code: {last_seen_key_local[:20]}...")
                    else:
                        new_msgs = []
                        for r in valid_rows:
                            if r[3] == last_seen_key_local:
                                break
                            new_msgs.append(r)
                        
                        if new_msgs:
                            new_msgs.reverse() 
                            for r in new_msgs:
                                date_str, number, sms, key, s_name = r
                                otp_val, sms_text = extract_from_message(sms)
                                display_name = f"[{s_name}]" if s_name else f"{detect_service(sms)}"
                                send_otp_to_user(clean_number(number), sms_text, number, display_name, otp_val, site_key='Fly sms')
                                last_seen_key_local = key
                            
                            with open(last_message_file, "w", encoding="utf-8") as f:
                                f.write(last_seen_key_local)
            
            time.sleep(check_interval)
        except Exception as e:
            print(f"[{site_name}] Loop Error: {e}")
            time.sleep(10)


def login_site4():
    global is_logged_in_site4
    print("[Site4/Bolt] 🔄 محاولة تسجيل الدخول...")
    
    try:
        session4.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"
        })
        
        resp = session4.get(LOGIN_PAGE_URL4, timeout=HTTP_TIMEOUT4)
        print(f"[Site4/Bolt] 📄 حالة GET: {resp.status_code}")
        
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            print("[Site4/Bolt] ⚠️ لم يتم العثور على captcha في الصفحة")
            print(f"[Site4/Bolt] 📋 عينة من المحتوى: {resp.text[:500]}")
            return False
        
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2
        print(f"[Site4/Bolt] 🧮 حل captcha: {num1} + {num2} = {captcha_answer}")
        
        crlf_match = re.search(r"name='crlf' value='([^']+)'", resp.text)
        
        payload = {
            "username": USERNAME4,
            "password": PASSWORD4,
            "capt": str(captcha_answer)
        }
        
        if crlf_match:
            payload["crlf"] = crlf_match.group(1)
            print(f"[Site4/Bolt] 🔑 استخراج crlf token")
        else:
            print(f"[Site4/Bolt] ⚠️ لم يتم العثور على crlf token")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE_URL4,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": BASE_URL4
        }
        
        print(f"[Site4/Bolt] 📤 إرسال طلب تسجيل الدخول لـ: {USERNAME4}")
        resp = session4.post(LOGIN_POST_URL4, data=payload, headers=headers, timeout=HTTP_TIMEOUT4, allow_redirects=True)
        
        print(f"[Site4/Bolt] 📊 حالة POST: {resp.status_code}")
        print(f"[Site4/Bolt] 🔗 URL النهائي: {resp.url}")
        
        if ("dashboard" in resp.text.lower() or 
            "logout" in resp.text.lower() or 
            "agent" in resp.url.lower() or 
            "reports" in resp.url.lower() or
            resp.url != LOGIN_PAGE_URL4):
            print("[Site4/Bolt] ✅ تسجيل الدخول نجح")
            is_logged_in_site4 = True
            save_cookies_site4()
            return True
        else:
            print("[Site4/Bolt] ❌ فشل تسجيل الدخول")
            if "incorrect" in resp.text.lower() or "invalid" in resp.text.lower():
                print("[Site4/Bolt] ⚠️ اسم المستخدم أو كلمة المرور غير صحيحة")
            return False
            
    except Exception as e:
        print(f"[Site4/Bolt] ❌ خطأ في تسجيل الدخول: {e}")
        import traceback
        traceback.print_exc()
        return False

def build_ajax_url_site4(start_date=None, end_date=None, wide_range=False):
    if wide_range:
        start_date = date.today() - timedelta(days=7)
        end_date = date.today() + timedelta(days=1)
    else:
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today() + timedelta(days=1)
    
    fdate1 = f"{start_date.strftime('%Y-%m-%d')} 00:00:00"
    fdate2 = f"{end_date.strftime('%Y-%m-%d')} 23:59:59"
    
    return {
        'url': BASE_URL4 + AJAX_PATH4,
        'params': {
            'fdate1': fdate1,
            'fdate2': fdate2,
            'frange': '',
            'fclient': '',
            'fnum': '',
            'fcli': '',
            'fgdate': '',
            'fgmonth': '',
            'fgrange': '',
            'fgclient': '',
            'fgnumber': '',
            'fgcli': '',
            'fg': '0',
            'sEcho': '1',
            'iColumns': '8',
            'sColumns': '',
            'iDisplayStart': '0',
            'iDisplayLength': '100',
            'mDataProp_0': '0',
            'mDataProp_1': '1',
            'mDataProp_2': '2',
            'mDataProp_3': '3',
            'mDataProp_4': '4',
            'mDataProp_5': '5',
            'mDataProp_6': '6',
            'mDataProp_7': '7',
            'sSearch': '',
            'bRegex': 'false',
            'iSortCol_0': '0',
            'sSortDir_0': 'desc',
            'iSortingCols': '1'
        }
    }

def fetch_ajax_json_site4(url_dict, retry_count=0):
    global is_logged_in_site4
    
    ajax_headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': BASE_URL4 + "/agent/SMSCDRReports"
    }
    
    try:
        print(f"[Site4/Bolt] 📡 إرسال طلب AJAX إلى: {url_dict['url']}")
        r = session4.post(url_dict['url'], data=url_dict['params'], headers=ajax_headers, timeout=HTTP_TIMEOUT4)
        print(f"[Site4/Bolt] 📊 حالة API: {r.status_code}, URL: {r.url[:80]}")
        
        if r.status_code == 403 or (r.status_code == 200 and 'login' in r.url.lower()):
            is_logged_in_site4 = False
            print("[Site4/Bolt] 🔄 انتهت الجلسة - إعادة تسجيل الدخول...")
            if login_site4():
                is_logged_in_site4 = True
                save_cookies_site4()
                r = session4.post(url_dict['url'], data=url_dict['params'], headers=ajax_headers, timeout=HTTP_TIMEOUT4)
                print(f"[Site4/Bolt] 📊 حالة API بعد إعادة التسجيل: {r.status_code}")
            else:
                return None
        
        r.raise_for_status()
        data = r.json()
        print(f"[Site4/Bolt] 🔎 نوع البيانات: {type(data)}, حجم: {len(str(data))}")
        
        if data:
            rows_count = 0
            if isinstance(data, dict):
                print(f"[Site4/Bolt] 🔑 مفاتيح JSON: {list(data.keys())[:10]}")
                for key in ("data", "aaData", "rows"):
                    if key in data and isinstance(data[key], list):
                        rows_count = len(data[key])
                        print(f"[Site4/Bolt] ✅ وجدنا {rows_count} رسالة في '{key}'")
                        break
            elif isinstance(data, list):
                rows_count = len(data)
                print(f"[Site4/Bolt] ✅ القائمة تحتوي على {rows_count} عنصر")
            
            if rows_count == 0:
                print(f"[Site4/Bolt] ⚠️ الاستجابة فارغة: {str(data)[:300]}")
        else:
            print(f"[Site4/Bolt] ⚠️ البيانات None أو فارغة")
        
        return data if isinstance(data, (dict, list)) else None
    except Exception as e:
        print(f"[Site4/Bolt] ❌ خطأ في جلب البيانات: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_rows_from_json_site4(j):
    if j is None:
        return []
    for key in ("data", "aaData", "rows"):
        if isinstance(j, dict) and key in j:
            return j[key]
    return j if isinstance(j, list) else []

def is_hotmelo_message(message):
    message_lower = message.lower()
    hotmelo_keywords = ["hotmelo", "hot melo", "hot-melo", "hotmelon"]
    return any(keyword in message_lower for keyword in hotmelo_keywords)

def filter_hotmelo_messages_site4(rows):
    IDX_DATE_SITE4 = 0
    IDX_NUMBER_SITE4 = 2
    IDX_SMS_SITE4 = 5
    
    hotmelo_messages = []
    other_messages = []
    
    for row in rows:
        if isinstance(row, list) and len(row) > IDX_SMS_SITE4:
            date_val = clean_html_site2(row[IDX_DATE_SITE4])
            number_val = clean_number(row[IDX_NUMBER_SITE4])
            sms_val = clean_html_site2(row[IDX_SMS_SITE4]) if row[IDX_SMS_SITE4] else ""
            
            if (date_val and '-' in date_val and ':' in date_val and 
                number_val and len(number_val) >= 10 and 
                sms_val and len(sms_val) > 5):
                
                if is_hotmelo_message(sms_val):
                    hotmelo_messages.append(row)
                else:
                    other_messages.append(row)
    
    return hotmelo_messages + other_messages

def row_to_tuple_site4(row):
    IDX_DATE_SITE4 = 0
    IDX_NUMBER_SITE4 = 2
    IDX_SMS_SITE4 = 5
    
    date_str = clean_html_site2(row[IDX_DATE_SITE4]) if len(row) > IDX_DATE_SITE4 else ""
    number = clean_number(row[IDX_NUMBER_SITE4]) if len(row) > IDX_NUMBER_SITE4 else ""
    sms = clean_html_site2(row[IDX_SMS_SITE4]) if len(row) > IDX_SMS_SITE4 else ""
    key = f"{date_str}|{number}|{sms}"
    return date_str, number, sms, key

def load_last_seen_key_site4():
    global last_seen_key_site4
    if os.path.exists(LAST_MESSAGE_FILE_SITE4):
        with open(LAST_MESSAGE_FILE_SITE4, "r", encoding="utf-8") as f:
            last_seen_key_site4 = f.read().strip()
            print(f"[Site4/Bolt] 📋 تم تحميل آخر رسالة: {last_seen_key_site4[:50]}...")

def save_last_seen_key_site4():
    with open(LAST_MESSAGE_FILE_SITE4, "w", encoding="utf-8") as f:
        f.write(last_seen_key_site4)

def verify_session_site4():
    try:
        test_url = build_ajax_url_site4(wide_range=False)
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL4 + "/agent/SMSCDRReports"
        }
        r = session4.post(test_url['url'], data=test_url['params'], headers=ajax_headers, timeout=HTTP_TIMEOUT4)
        
        if r.status_code == 403 or 'login' in r.url.lower():
            return False
        
        r.raise_for_status()
        return True
    except:
        return False

def verify_session_site3():
    try:
        test_url = build_ajax_url_site3(wide_range=False)
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL3 + "/agent/SMSCDRReports"
        }
        r = session3.post(test_url['url'], data=test_url['params'], headers=ajax_headers, timeout=HTTP_TIMEOUT3)
        
        if r.status_code == 403 or 'login' in r.url.lower():
            return False
        
        r.raise_for_status()
        return True
    except:
        return False

def login_site5():
    
    global is_logged_in_site5, csrf_token_site5
    print("[iVASMS] 🔄 محاولة تسجيل الدخول...")
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = session5.get(LOGIN_PAGE_URL5, timeout=HTTP_TIMEOUT5)
        print(f"[iVASMS] 📄 حالة GET: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_input = soup.find('input', {'name': '_token'})
        if not csrf_input:
            print("[iVASMS] ⚠️ لم يتم العثور على CSRF token")
            return False
        
        csrf = csrf_input.get('value')
        if not csrf:
            print("[iVASMS] ⚠️ CSRF token فارغ")
            return False
        print(f"[iVASMS] 🔑 استخراج CSRF token: {csrf[:20] if len(str(csrf)) > 20 else csrf}...")
        
        payload = {
            '_token': csrf,
            'email': USERNAME5,
            'password': PASSWORD5,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE_URL5,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        print(f"[iVASMS] 📤 إرسال طلب تسجيل الدخول لـ: {USERNAME5}")
        resp = session5.post(LOGIN_POST_URL5, data=payload, headers=headers, timeout=HTTP_TIMEOUT5, allow_redirects=True)
        
        print(f"[iVASMS] 📊 حالة POST: {resp.status_code}")
        print(f"[iVASMS] 🔗 URL النهائي: {resp.url}")
        
        if 'portal' in resp.url or (resp.status_code == 200 and 'login' not in resp.url):
            print("[iVASMS] ✅ تسجيل الدخول نجح")
            is_logged_in_site5 = True
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_token'})
            if csrf_input:
                csrf_token_site5 = csrf_input.get('value')
            
            return True
        else:
            print("[iVASMS] ❌ فشل تسجيل الدخول")
            return False
            
    except Exception as e:
        print(f"[iVASMS] ❌ خطأ في تسجيل الدخول: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_session_site5():
    
    global csrf_token_site5
    try:
        resp = session5.get(SMS_RECEIVED_URL5, timeout=HTTP_TIMEOUT5)
        if 'login' in resp.url.lower():
            return False
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token_site5 = csrf_input.get('value')
            return True
        return False
    except:
        return False

def get_csrf_token_site5():
    
    global csrf_token_site5
    try:
        resp = session5.get(SMS_RECEIVED_URL5, timeout=HTTP_TIMEOUT5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token_site5 = csrf_input.get('value')
            return True
    except Exception as e:
        print(f"[iVASMS] ❌ خطأ في جلب CSRF token: {e}")
    return False

def sms_loop_for_ivasms_account(site_key, account):
    
    global account_stop_events
    account_id = account.get("id")
    username = account.get("username")
    password = account.get("password")
    api_key = account.get("api_key", "")
    site_name = SETTINGS[site_key]["name"]
    
    stop_key = f"{site_key}_{account_id}"
    account_stop_events[stop_key] = Event()
    stop_event = account_stop_events[stop_key]
    
    API_URL = SETTINGS[site_key].get("api_url", "https://maroon-wombat-183778.hostingersite.com/apiivasms/api.php")
    HTTP_TIMEOUT5 = SETTINGS[site_key]["timeout"]
    CHECK_INTERVAL5 = SETTINGS[site_key]["check_interval"]
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    sent_messages_local = set()
    message_lock = threading.Lock()
    
    def load_sent_messages():
        nonlocal sent_messages_local
        sent_file = f"sent_messages_{site_key}_{account_id}.json"
        if os.path.exists(sent_file):
            try:
                with open(sent_file, 'r') as f:
                    sent_messages_local = set(json.load(f))
            except:
                sent_messages_local = set()
    
    def save_sent_messages():
        sent_file = f"sent_messages_{site_key}_{account_id}.json"
        try:
            msgs = list(sent_messages_local)[-500:]
            with open(sent_file, 'w') as f:
                json.dump(msgs, f)
        except Exception as e:
            print(f"[{site_name}] ({username}) ❌ خطأ في حفظ الرسائل المرسلة: {e}")
    
    def fetch_sms_via_api():
        try:
            params = {
                'api_key': api_key,
                'username': username,
                'password': password,
                '_t': int(time.time() * 1000)
            }
            resp = requests.get(API_URL, params=params, timeout=HTTP_TIMEOUT5, verify=False)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get('success') and data.get('codes'):
                        return data['codes']
                    elif data.get('success'):
                        return []
                    else:
                        error_msg = data.get('error', data.get('message', 'Unknown error'))
                        print(f"[{site_name}] ({username}) ⚠️ API خطأ: {error_msg}")
                        return []
                except json.JSONDecodeError:
                    print(f"[{site_name}] ({username}) ⚠️ استجابة غير صالحة JSON")
                    return []
            else:
                print(f"[{site_name}] ({username}) ❌ حالة الاستجابة: {resp.status_code}")
                return []
        except Exception as e:
            print(f"[{site_name}] ({username}) ❌ خطأ في جلب البيانات: {e}")
            return []
    
    if not api_key:
        print_monitoring_box(site_name, username, "❌", "مفتاح API غير موجود!")
        return
    
    print_monitoring_box(site_name, username, "🌐", "بدء المراقبة عبر API...")
    load_sent_messages()
    print(f"[{site_name}] ({username}) ✅ بدء المراقبة كل {CHECK_INTERVAL5} ثانية... (API مفعل)")
    
    while not stop_event.is_set():
        try:
            if stop_event.is_set():
                break
                
            messages = fetch_sms_via_api()
            
            if stop_event.is_set():
                break
            
            new_count = 0
            for msg in messages:
                if stop_event.is_set():
                    break
                
                phone = msg.get('phone', msg.get('number', ''))
                message_text = msg.get('message', msg.get('sms', msg.get('text', '')))
                msg_time = msg.get('time', msg.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
                if not phone or not message_text:
                    continue
                    
                msg_key = f"{phone}|{message_text[:50]}"
                
                if msg_key not in sent_messages_local:
                    otp_val, sms_text = extract_from_message(message_text)
                    service_name = f"{detect_service(message_text)}"
                    send_otp_to_user(clean_number(phone), sms_text, phone, service_name, otp_val)
                    if True:
                        print(f"✅ {site_name} ({username}): تم إرسال الكود لـ {mask_number(phone)}")
                    
                    sent_messages_local.add(msg_key)
                    new_count += 1
            
            if new_count > 0:
                save_sent_messages()
                print(f"[{site_name}] ({username}) 📨 تم إرسال {new_count} رسالة جديدة")
            else:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            
        except Exception as e:
            if stop_event.is_set():
                break
            print_monitoring_box(site_name, username, "❌", f"خطأ غير متوقع: {str(e)}")
            time.sleep(10)
        
        if stop_event.wait(CHECK_INTERVAL5):
            break
    
    print(f"[{site_name}] ({username}) 🛑 تم إيقاف المراقبة بنجاح")

def sms_loop_requests_based(site_key, account):
    
    global account_stop_events
    
    def _debug_log(msg):
        if site_key in ["MSI", "Seven1Tel"]:
            line = f"[{datetime.now().strftime('%H:%M:%S')}] [{site_key}] {msg}"
            print(line)
            try:
                with open("debug_panels.log", "a", encoding="utf-8") as _f:
                    _f.write(line + "\n")
            except:
                pass
    
    account_id = account.get("id")
    username = account.get("username")
    password = account.get("password")
    site_name = SETTINGS[site_key]["name"]
    
    stop_key = f"{site_key}_{account_id}"
    account_stop_events[stop_key] = Event()
    stop_event = account_stop_events[stop_key]
    
    BASE_URL = SETTINGS[site_key]["base_url"]
    if not BASE_URL.startswith("http"):
        BASE_URL = "http://" + BASE_URL.lstrip(":")
    
    LOGIN_PAGE_URL = SETTINGS[site_key]["login_page_url"]
    LOGIN_POST_URL = SETTINGS[site_key]["login_post_url"]
    AJAX_PATH = SETTINGS[site_key].get("ajax_path", "/agent/res/data_smscdr.php")
    CHECK_INTERVAL = SETTINGS[site_key]["check_interval"]
    TIMEOUT_LOCAL = SETTINGS[site_key].get("timeout", 60)
    
    if "/ints" in BASE_URL:
        AJAX_URL = BASE_URL + AJAX_PATH
    elif "/ints" in AJAX_PATH:
        AJAX_URL = BASE_URL + AJAX_PATH
    else:
        AJAX_URL = BASE_URL + AJAX_PATH
    
    print(f"[{site_name}] ({username}) 🔗 AJAX URL: {AJAX_URL}")
    
    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    sent_messages_file = f"sent_messages_{site_key}_{account_id}.json"
    last_seen_key_local = ""
    sent_messages_local = set()
    session = requests.Session()
    session.verify = False
    is_logged_in = False
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    })
    
    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except:
                last_seen_key_local = ""
    
    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except:
            pass
    
    def load_sent_messages():
        nonlocal sent_messages_local
        if os.path.exists(sent_messages_file):
            try:
                with open(sent_messages_file, 'r') as f:
                    sent_messages_local = set(json.load(f))
            except:
                sent_messages_local = set()
    
    def save_sent_messages():
        try:
            msgs = list(sent_messages_local)[-500:]
            with open(sent_messages_file, 'w') as f:
                json.dump(msgs, f)
        except:
            pass
    
    def login():
        nonlocal is_logged_in
        print(f"[{site_name}] ({username}) 🔐 تسجيل الدخول...")
        _debug_log(f"🔐 بدء تسجيل الدخول - LOGIN_PAGE_URL={LOGIN_PAGE_URL}")
        
        try:
            resp = session.get(LOGIN_PAGE_URL, timeout=TIMEOUT_LOCAL)
            _debug_log(f"GET login page -> status={resp.status_code}, final_url={resp.url}, len={len(resp.text)}")
            
            if resp.status_code != 200:
                print(f"[{site_name}] ({username}) ⚠️ فشل فتح صفحة الدخول: {resp.status_code}")
                _debug_log(f"⚠️ فشل فتح صفحة الدخول: {resp.status_code}")
                return False
            
            match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
            if not match:
                match = re.search(r'(\d+)\s*\+\s*(\d+)', resp.text)
            
            if not match:
                print(f"[{site_name}] ({username}) ⚠️ لم يتم العثور على Captcha، محاولة بدون captcha...")
                captcha_answer = ""
                _debug_log("⚠️ مفيش captcha اتلاقى - هيحاول بدونها")
            else:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                print(f"[{site_name}] ({username}) 🧮 Captcha: {match.group(1)} + {match.group(2)} = {captcha_answer}")
                _debug_log(f"🧮 Captcha: {match.group(1)} + {match.group(2)} = {captcha_answer}")
            
            crlf_match = re.search(r"name=['\"]crlf['\"].*?value=['\"]([^'\"]+)['\"]", resp.text)
            if not crlf_match:
                crlf_match = re.search(r"value=['\"]([^'\"]+)['\"].*?name=['\"]crlf['\"]", resp.text)
            
            payload = {
                'username': username,
                'password': password,
            }
            if captcha_answer:
                payload['capt'] = captcha_answer
            
            if crlf_match and site_key != "Fly sms":
                payload['crlf'] = crlf_match.group(1)
                print(f"[{site_name}] ({username}) 🔑 تم استخراج crlf token")
                _debug_log(f"🔑 crlf token: {crlf_match.group(1)}")
            else:
                _debug_log("⚠️ مفيش crlf token اتلاقى")
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': LOGIN_PAGE_URL,
            }
            
            if site_key != "Fly sms":
                headers.update({
                    'Origin': BASE_URL.rstrip('/'),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                })
            
            resp = session.post(LOGIN_POST_URL, data=payload, headers=headers, timeout=TIMEOUT_LOCAL, allow_redirects=True)
            
            print(f"[{site_name}] ({username}) 📊 Response URL: {resp.url}")
            _debug_log(f"POST {LOGIN_POST_URL} payload_keys={list(payload.keys())} -> status={resp.status_code}, final_url={resp.url}, len={len(resp.text)}")
            _debug_log(f"أول 300 حرف من الرد: {resp.text[:300]!r}")
            
            # تحسين كشف نجاح الدخول لـ Fly sms وباقي اللوحات
            success_keywords = ["dashboard", "logout", "agent", "reports", "smscdr"]
            is_success = any(kw in resp.text.lower() for kw in success_keywords) or \
                         any(kw in resp.url.lower() for kw in success_keywords) or \
                         resp.url != LOGIN_PAGE_URL
            
            if is_success:
                print(f"[{site_name}] ({username}) ✅ تسجيل الدخول نجح")
                _debug_log("✅ تسجيل الدخول نجح (success_keywords/url_changed)")
                is_logged_in = True
                return True
            
            if 'dashboard' in resp.text.lower() or 'logout' in resp.text.lower() or 'reports' in resp.url.lower():
                print(f"[{site_name}] ({username}) ✅ تسجيل الدخول نجح (dashboard detected)")
                is_logged_in = True
                return True
            
            if resp.url != LOGIN_PAGE_URL and 'login' not in resp.url.lower():
                print(f"[{site_name}] ({username}) ✅ تسجيل الدخول نجح (redirected)")
                is_logged_in = True
                return True
            
            sms_page_path = AJAX_PATH.rsplit("/", 2)[0] + "/SMSCDRReports" if "/res/" in AJAX_PATH else ("/agent/SMSCDRReports" if "/ints" in BASE_URL else "/ints/agent/SMSCDRReports")
            test_resp = session.get(BASE_URL.rstrip('/') + sms_page_path, timeout=15)
            _debug_log(f"محاولة تحقق أخيرة: GET {BASE_URL.rstrip('/') + sms_page_path} -> status={test_resp.status_code}, final_url={test_resp.url}")
            if test_resp.status_code == 200 and 'login' not in test_resp.url.lower():
                print(f"[{site_name}] ({username}) ✅ تسجيل الدخول نجح (verified)")
                is_logged_in = True
                return True
            
            print(f"[{site_name}] ({username}) ❌ فشل تسجيل الدخول")
            _debug_log("❌ فشل تسجيل الدخول - كل محاولات الكشف فشلت")
            return False
            
        except Exception as e:
            print(f"[{site_name}] ({username}) ❌ خطأ في تسجيل الدخول: {e}")
            _debug_log(f"❌ Exception أثناء تسجيل الدخول: {e}")
            return False
    
    def get_sesskey_from_page(html_text):
        match = re.search(r'sesskey=([A-Za-z0-9=]+)', html_text)
        if match:
            return ("sesskey", match.group(1))
        match = re.search(r'csstr=([A-Za-z0-9]+)', html_text)
        if match:
            return ("csstr", match.group(1))
        return None
    
    current_sesskey = None
    
    def fetch_sms_data():
        nonlocal is_logged_in, current_sesskey
        
        sms_page_path = AJAX_PATH.rsplit("/", 2)[0] + "/SMSCDRReports" if "/res/" in AJAX_PATH else ("/agent/SMSCDRReports" if "/ints" in BASE_URL else "/ints/agent/SMSCDRReports")
        referer_url = BASE_URL.rstrip('/') + sms_page_path
        
        if site_key in ["GROUP", "Fly sms", "hadi", "fire", "Seven1Tel", "Gaza SMS", "Bolt", "Km sms", "Purple SMS", "MSI", "Flex"]:
            for retry in range(3):
                try:
                    page_resp = session.get(referer_url, timeout=TIMEOUT_LOCAL)
                    _debug_log(f"GET {referer_url} -> status={page_resp.status_code}, final_url={page_resp.url}, len={len(page_resp.text)}")
                    
                    if page_resp.status_code == 200:
                        if 'login' in page_resp.text.lower() and 'password' in page_resp.text.lower():
                            soup = BeautifulSoup(page_resp.text, 'html.parser')
                            login_form = soup.find('input', {'name': 'password'})
                            if login_form:
                                is_logged_in = False
                                _debug_log("⚠️ الصفحة رجعت فورم تسجيل دخول - الجلسة منتهية، هيعيد الدخول")
                                print(f"[{site_name}] ({username}) ⚠️ الجلسة انتهت، إعادة تسجيل الدخول...")
                                return []
                        
                        sess_result = get_sesskey_from_page(page_resp.text)
                        if not sess_result and site_key in ["Fly sms", "fire"]:
                            # محاولة استخراج sesskey من أي رابط في الصفحة
                            match = re.search(r'sesskey=([A-Za-z0-9=]+)', page_resp.text)
                            if match:
                                sess_result = ("sesskey", match.group(1))
                                print(f"[{site_name}] ({username}) 🔑 تم استخراج sesskey (طريقة بديلة)")
                        
                        if not sess_result:
                            _debug_log(f"⚠️ مفيش sesskey/csstr اتلاقى في الصفحة. أول 300 حرف: {page_resp.text[:300]!r}")
                        
                        if sess_result:
                            key_name, sesskey = sess_result
                            current_sesskey = sesskey
                            _debug_log(f"🔑 تم استخراج {key_name}={sesskey}")
                            print(f"[{site_name}] ({username}) 🔑 تم استخراج {key_name}")
                            
                            today = datetime.now().strftime('%Y-%m-%d')
                            ajax_url = BASE_URL + AJAX_PATH
                            
                            payload = {
                                'fdate1': f'{today} 00:00:00',
                                'fdate2': f'{today} 23:59:59',
                                'frange': '',
                                'fclient': '',
                                'fnum': '',
                                'fcli': '',
                                'fgdate': '',
                                'fgmonth': '',
                                'fgrange': '',
                                'fgclient': '',
                                'fgnumber': '',
                                'fgcli': '',
                                'fg': '0',
                                key_name: sesskey
                            }
                            
                            ajax_headers = {
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'X-Requested-With': 'XMLHttpRequest',
                                'Referer': referer_url,
                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                            }
                            
                            if site_key in ["Fly sms", "fire", "Seven1Tel"]:
                                ajax_resp = session.post(ajax_url, data=payload, headers=ajax_headers, timeout=TIMEOUT_LOCAL)
                            else:
                                ajax_resp = session.get(ajax_url, params=payload, headers=ajax_headers, timeout=TIMEOUT_LOCAL)
                            
                            _debug_log(f"AJAX {ajax_url} -> status={ajax_resp.status_code}, len={len(ajax_resp.text)}, أول 300 حرف: {ajax_resp.text[:300]!r}")
                            
                            if ajax_resp.status_code == 200:
                                try:
                                    data = ajax_resp.json()
                                    if 'aaData' in data:
                                        rows = data['aaData']
                                        if rows:
                                            print(f"[{site_name}] ({username}) ✅ تم جلب {len(rows)} رسالة عبر AJAX")
                                            return rows
                                    elif isinstance(data, list):
                                        if data:
                                            print(f"[{site_name}] ({username}) ✅ تم جلب {len(data)} رسالة عبر AJAX")
                                            return data
                                except:
                                    pass
                        
                        soup = BeautifulSoup(page_resp.text, 'html.parser')
                        table = soup.find('table')
                        if table:
                            tbody = table.find('tbody')
                            rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                            data_rows = []
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 6:
                                    data_rows.append([cell.get_text(strip=True) for cell in cells])
                            if data_rows:
                                print(f"[{site_name}] ({username}) 📄 استخدام HTML parsing كبديل")
                                return data_rows
                        return []
                        
                    elif page_resp.status_code in [502, 503, 504]:
                        if retry < 2:
                            print(f"[{site_name}] ({username}) ⚠️ السيرفر مشغول ({page_resp.status_code}) - محاولة {retry+1}/3...")
                            time.sleep(3 + retry * 2)
                            continue
                        print(f"[{site_name}] ({username}) ⚠️ السيرفر مشغول ({page_resp.status_code})")
                        return []
                    else:
                        print(f"[{site_name}] ({username}) ⚠️ HTTP {page_resp.status_code}")
                        return []
                    
                except Exception as e:
                    if retry < 2 and ('Connection' in str(e) or 'Timeout' in str(e)):
                        time.sleep(2)
                        continue
                    print(f"[{site_name}] ({username}) ❌ خطأ في جلب البيانات: {e}")
                    is_logged_in = False
                    return []
            return []
        
        for retry in range(3):
            try:
                headers = {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': referer_url,
                    'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
                }
                
                today = datetime.now()
                start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
                end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                
                payload = {
                    'fdate1': f'{start_date} 00:00:00',
                    'fdate2': f'{end_date} 23:59:59',
                    'frange': '',
                    'fclient': '',
                    'fnum': '',
                    'fcli': '',
                    'fgdate': '',
                    'fgmonth': '',
                    'fgrange': '',
                    'fgclient': '',
                    'fgnumber': '',
                    'fgcli': '',
                    'fg': '0',
                    'sEcho': '1',
                    'iColumns': '8',
                    'sColumns': '',
                    'iDisplayStart': '0',
                    'iDisplayLength': '100',
                    'mDataProp_0': '0',
                    'mDataProp_1': '1',
                    'mDataProp_2': '2',
                    'mDataProp_3': '3',
                    'mDataProp_4': '4',
                    'mDataProp_5': '5',
                    'mDataProp_6': '6',
                    'mDataProp_7': '7',
                    'sSearch': '',
                    'bRegex': 'false',
                    'iSortCol_0': '0',
                    'sSortDir_0': 'desc',
                    'iSortingCols': '1'
                }
                
                resp = session.post(AJAX_URL, data=payload, headers=headers, timeout=TIMEOUT_LOCAL)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        for key in ['data', 'aaData', 'rows']:
                            if key in data and isinstance(data[key], list):
                                return data[key]
                        is_logged_in = False
                    except Exception as je:
                        if 'login' in resp.text.lower() or 'signin' in resp.text.lower():
                            is_logged_in = False
                            print(f"[{site_name}] ({username}) ⚠️ الجلسة انتهت، إعادة تسجيل الدخول...")
                        else:
                            try:
                                soup = BeautifulSoup(resp.text, 'html.parser')
                                table = soup.find('table')
                                if table:
                                    tbody = table.find('tbody')
                                    rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                                    data_rows = []
                                    for row in rows:
                                        cells = row.find_all('td')
                                        if len(cells) >= 6:
                                            data_rows.append([cell.get_text(strip=True) for cell in cells])
                                    if data_rows:
                                        print(f"[{site_name}] ({username}) 📄 استخدام HTML parsing")
                                        return data_rows
                            except:
                                pass
                elif resp.status_code == 503:
                    if retry < 2:
                        time.sleep(3 + retry * 2)
                        continue
                    print(f"[{site_name}] ({username}) ⚠️ السيرفر مشغول (503) - جاري المحاولة بطريقة بديلة...")
                    try:
                        page_resp = session.get(referer_url, timeout=TIMEOUT_LOCAL)
                        if page_resp.status_code == 200:
                            soup = BeautifulSoup(page_resp.text, 'html.parser')
                            table = soup.find('table')
                            if table:
                                tbody = table.find('tbody')
                                rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                                data_rows = []
                                for row in rows:
                                    cells = row.find_all('td')
                                    if len(cells) >= 6:
                                        data_rows.append([cell.get_text(strip=True) for cell in cells])
                                if data_rows:
                                    print(f"[{site_name}] ({username}) 📄 استخدام HTML parsing (بديل)")
                                    return data_rows
                    except Exception as html_e:
                        print(f"[{site_name}] ({username}) ⚠️ فشل HTML parsing: {html_e}")
                else:
                    print(f"[{site_name}] ({username}) ⚠️ HTTP {resp.status_code}")
                
                return []
                
            except Exception as e:
                if retry < 2 and ('Connection' in str(e) or 'Timeout' in str(e)):
                    time.sleep(2)
                    continue
                print(f"[{site_name}] ({username}) ❌ خطأ في جلب البيانات: {e}")
                is_logged_in = False
                return []
        return []
    
    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة بـ Requests (خفيف وسريع)...")
    _debug_log(f"🚀 بدء الـ thread - username={username}")
    
    load_last_seen()
    load_sent_messages()
    
    if not login():
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول الأولي")
        _debug_log("❌ فشل تسجيل الدخول الأولي - الـ thread هيقف تمامًا هنا")
        return
    
    errors = 0
    print(f"[{site_name}] ({username}) ✅ بدء المراقبة كل {CHECK_INTERVAL} ثانية...")
    
    while not stop_event.is_set():
        try:
            if stop_event.is_set():
                break
            
            if not is_logged_in:
                if not login():
                    _debug_log("⏳ فشل إعادة تسجيل الدخول - هينتظر 30 ثانية ويحاول تاني")
                    time.sleep(30)
                    continue
            
            raw_data = fetch_sms_data()
            
            _debug_log(f"عدد الصفوف الخام المستلمة: {len(raw_data) if raw_data else 0}")
            if raw_data:
                for _dbg_row in raw_data[:5]:
                    _debug_log(f"صف خام: {_dbg_row}")
            
            if not raw_data:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                data = []
                for row in raw_data:
                    if isinstance(row, list) and len(row) >= 6:
                        # Fly sms أحياناً بتغير ترتيب الأعمدة، فبنتأكد من سحب البيانات صح
                        if site_key == "Fly sms":
                            date_str = str(row[0]).strip() if row[0] else ""
                            number = re.sub(r'\D', '', str(row[2])) if row[2] else ""
                            # في Fly sms الرسالة أحياناً تكون في العمود 5 أو 6
                            sms = str(row[5]).strip() if len(row) > 5 and row[5] else ""
                            if not sms and len(row) > 6:
                                sms = str(row[6]).strip()
                        else:
                            date_str = str(row[0]).strip() if row[0] else ""
                            number = re.sub(r'\D', '', str(row[2])) if row[2] else ""
                            sms = str(row[5]).strip() if row[5] else ""
                        
                        _debug_log(f"date={date_str!r} number={number!r} sms={sms!r}")
                        
                        if date_str and number and len(number) >= 7 and sms:
                            
                            skip_row = False
                            # فلترة أقل تشدداً لـ Fly sms و MSI/Seven1Tel لضمان وصول الأكواد
                            if site_key in ["Fly sms", "MSI", "Seven1Tel"]:
                                # تم تعطيل الفلترة لـ Seven1Tel لضمان وصول جميع الأكواد
                                if site_key != "Seven1Tel" and any(x in sms.lower() for x in ["currency", "payout", "nan%", "100%", "0.008"]):
                                    skip_row = True
                                    _debug_log(f"❌ اتفلترت بسبب كلمة ممنوعة (فلتر مخفف): {sms!r}")
                            else:
                                if any(x in sms.lower() for x in ["currency", "payout", "nan%", "100%", "0.008", "my payout", "client payout", "range", "number", "cli", "client"]):
                                    skip_row = True
                            
                            if not skip_row and site_key not in ["Fly sms", "MSI", "Seven1Tel"]:
                                if sms.count(',') >= 5 and ('%' in sms or 'nan' in sms.lower()):
                                    _debug_log(f"❌ اتفلترت بسبب فاصلة/نسبة: {sms!r}")
                                    skip_row = True
                            
                            if not skip_row:
                                otp_val, _ = extract_from_message(sms)
                                if not otp_val and len(sms) < 5:
                                    _debug_log(f"❌ اتفلترت لعدم وجود كود ورسالة قصيرة: {sms!r}")
                                    skip_row = True
                            
                            if not skip_row:
                                data.append({'date': date_str, 'number': number, 'sms': sms})
                        elif site_key in ["MSI", "Seven1Tel"]:
                            _debug_log("❌ اتفلترت لنقص بيانات (date/number/sms فاضيين أو الرقم أقصر من 7 أرقام)")
                
                if not data:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
                else:
                    data.sort(key=lambda x: x['date'], reverse=False) 
                    
                    new_messages = []
                    for msg in data:
                        key = f"{msg['date']}|{msg['number']}"
                        # Fly sms أحياناً بتبعت الرسايل بترتيب عشوائي، فبنعتمد على الـ sent_messages_local أكتر
                        if site_key == "Fly sms":
                            # بنعمل مفتاح فريد أكتر بالرسالة نفسها عشان لو الرقم جاله كودين ورا بعض
                            unique_key = f"{msg['date']}|{msg['number']}|{msg['sms'][:20]}"
                            if unique_key not in sent_messages_local:
                                new_messages.append(msg)
                                sent_messages_local.add(unique_key)
                        else:
                            if key == last_seen_key_local:
                                new_messages = [] 
                                continue
                            if key not in sent_messages_local:
                                new_messages.append(msg)
                    
                    if new_messages:
                        print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")
                        
                        
                        for msg in new_messages:
                            date_str = msg['date']
                            number = msg['number']
                            sms = msg['sms']
                            
                            otp_val, sms_text = extract_from_message(sms)
                            service_name = f"{detect_service(sms)}"
                            formatted_msg = format_otp_message_v2(number, sms_text, service_name, otp_val)
                            
                            if otp_val:
                                print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                            send_otp_to_user(clean_number(number), sms_text, number, service_name, otp_val)
                            
                            if site_key == "Fly sms":
                                # المفتاح الفريد تم إضافته بالفعل فوق
                                last_seen_key_local = f"{date_str}|{number}"
                            else:
                                key = f"{date_str}|{number}"
                                sent_messages_local.add(key)
                                last_seen_key_local = key
                        
                        save_last_seen()
                        save_sent_messages()
                    else:
                        print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            
            errors = 0
            
        except Exception as e:
            errors += 1
            print_monitoring_box(site_name, username, "❌", f"خطأ ({errors}/5): {str(e)[:40]}")
            if errors >= 5:
                print(f"[{site_name}] ({username}) 🔄 إعادة تسجيل الدخول...")
                if login():
                    errors = 0
                else:
                    time.sleep(30)
            time.sleep(5)
        
        if stop_event.wait(CHECK_INTERVAL):
            break
    
    print(f"[{site_name}] ({username}) 🛑 تم إيقاف المراقبة")

def login_site8(account):
    username = account.get("username")
    password = account.get("password")
    
    session = requests.Session()
    session.verify = False
    
    # login_site8 مخصصة فقط لحسابات IMS من نوع agent (45.82.67.20)
    # ومش بتمر من هنا خالص، فمفيش داعي لأي تحويل لدومين تاني هنا
    login_page_url = LOGIN_PAGE_URL8
    timeout_val = HTTP_TIMEOUT8

    print(f"[IMS Agent] ({username}) 🔄 تسجيل الدخول...")
    try:
       
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        })
        
        response = session.get(login_page_url, timeout=timeout_val)
        if response.status_code == 403:
            
            response = session.get(LOGIN_PAGE_URL8, timeout=HTTP_TIMEOUT8, headers={"User-Agent": "Mozilla/5.0"})
        
        if response.status_code != 200:
            print(f"[Site8/IMS] ({username}) [!] فشل فتح صفحة الدخول: {response.status_code}")
            return False, None
        
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value'))
        if not csrf_token:
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = str(csrf_input.get('value'))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content'))
        if not csrf_token:
            match = re.search(r'name=["\']_token["\'].*?value=["\']([^"\']+)["\']', html_content)
            if match:
                csrf_token = match.group(1)
        
        if csrf_token:
            print(f"[Site8/IMS] ({username}) [*] CSRF Token: {csrf_token[:20]}...")
        
        
        captcha_answer = None
        
        patterns = [
            r'(\d+)\s*\+\s*(\d+)\s*=', 
            r'What is (\d+) \+ (\d+)', 
            r'(\d+)\s*plus\s*(\d+)'
        ]
        
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break
        
        
        if not captcha_answer:
            b_tags = soup.find_all('b')
            nums = []
            for b in b_tags:
                text = b.get_text().strip()
                if text.isdigit():
                    nums.append(int(text))
            if len(nums) >= 2:
                captcha_answer = str(nums[0] + nums[1])
        
        if not captcha_answer:
            
            text = soup.get_text()
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                    break
        
        if not captcha_answer:
            print(f"[Site8/IMS] ({username}) [!] لم يتم العثور على الكابتشا")
            return False, None
        
        print(f"[Site8/IMS] ({username}) [*] Captcha: {captcha_answer}")
        
        login_data = {
            "username": username,
            "password": password,
            "capt": captcha_answer,
        }
        
        if csrf_token:
            login_data["_token"] = csrf_token
        
        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and isinstance(name, str) and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''

        
        login_headers = {
            "Referer": LOGIN_PAGE_URL8,
            "Origin": BASE_URL8,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(
            LOGIN_POST_URL8,
            data=login_data,
            headers=login_headers,
            timeout=HTTP_TIMEOUT8,
            allow_redirects=True
        )
        
        print(f"[Site8/IMS] ({username}) [DEBUG] Final URL: {response.url}")
        
        if any(x in response.url.lower() for x in ["/agent", "/dashboard", "/home"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[Site8/IMS] ({username}) [+] تسجيل الدخول نجح (Landed on: {response.url})")
            return True, session
        
        content_lower = response.text.lower()
        if "logout" in content_lower or "smscdr" in content_lower or "agent" in content_lower:
            print(f"[Site8/IMS] ({username}) [+] تسجيل الدخول نجح (Detected via content)")
            return True, session

        print(f"[Site8/IMS] ({username}) [!] فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[Site8/IMS] ({username}) [!] خطأ في تسجيل الدخول: {e}")
        return False, None

def sms_loop_for_ims_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())
    
    session = requests.Session()
    session.verify = False
    is_logged_in = False
    
    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""
    
    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass
    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")
    
    success, new_session = login_site8(account)
    if success:
        session = new_session
        is_logged_in = True
    else:
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")
    
    load_last_seen()
    errors = 0
    
    while not stop_event.is_set():
        try:
            
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                print(f"[Site8/IMS] ({username}) 🔑 تم اكتشاف تغيير كلمة المرور، جاري إعادة الدخول...")
                password = current_account.get("password")
                success, new_session = login_site8(current_account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    is_logged_in = False
                    time.sleep(30)
                    continue

            if not is_logged_in:
                success, new_session = login_site8(current_account or account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    time.sleep(30)
                    continue

            today = datetime.now().strftime('%Y-%m-%d')
            
            codes_html = ""
            try:
                resp_codes = session.get(BASE_URL8 + "/ints/agent/SMSCDRReports", timeout=HTTP_TIMEOUT8)
                codes_html = resp_codes.text
                if 'login' in resp_codes.url.lower():
                    is_logged_in = False
                    continue
            except Exception as e:
                print(f"[Site8/IMS] ({username}) [!] Error loading codes page: {e}")
                is_logged_in = False
                continue

            sesskey = ""
            sesskey_match = re.search(r'sesskey=([A-Za-z0-9=]+)', codes_html)
            if sesskey_match:
                sesskey = sesskey_match.group(1)
            else:
                is_logged_in = False
                continue

            params = {
                'fdate1': f'{today} 00:00:00',
                'fdate2': f'{today} 23:59:59',
                'frange': '', 'fclient': '', 'fnum': '', 'fcli': '',
                'fgdate': '', 'fgmonth': '', 'fgrange': '', 'fgclient': '',
                'fgnumber': '', 'fgcli': '', 'fg': '0', 'sesskey': sesskey
            }

            ajax_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': BASE_URL8 + "/ints/agent/SMSCDRReports"
            }
            
            r = session.get("http://45.82.67.20/ints/agent/res/data_smscdr.php", params=params, headers=ajax_headers, timeout=HTTP_TIMEOUT8)
            
            if r.status_code != 200 or 'login' in r.url.lower():
                is_logged_in = False
                continue

            data_json = r.json()
            if data_json.get('aaData'):
                rows = data_json['aaData']
            else:
                rows = data_json if isinstance(data_json, list) else []
            
            if not rows:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                
                try:
                    rows.sort(key=lambda x: str(x[0]) if isinstance(x, list) and len(x) > 0 else "", reverse=True)
                except:
                    pass

                new_messages = []
                for row in rows:
                    if isinstance(row, list) and len(row) >= 6:
                        date_str = str(row[0]).strip()
                        number = re.sub(r'\D', '', str(row[2]))
                        sms = str(row[5]).strip()
                        
                        
                        if sms.count(',') > 3 or sms.count('%') > 1 or 'NAN%' in sms:
                            continue
                        
                        
                        if re.match(r'^[\d.,%|NAN/]+$', sms):
                            continue
                            
                        key = f"{date_str}|{number}"
                        if key == last_seen_key_local: break
                        new_messages.append({'date': date_str, 'number': number, 'sms': sms})
                
                if new_messages:
                    
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    
                    print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")
                   
                    
                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg['sms'])
                        
                        
                        service_name = f"{detect_service(sms_text)}"
                        formatted_msg = format_otp_message_v2(msg['number'], sms_text, service_name, otp_val)
                        
                        print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                        
                        success = False
                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val, site_key='IMS')
                                success = True
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35 
                                    match = re.search(r'after (\d+)', str(e))
                                    if match: wait_time = int(match.group(1)) + 2
                                    print(f"⚠️ Telegram 429 (Flood Control): Waiting {wait_time}s...")
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            
            errors = 0
        except Exception as e:
            errors += 1
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break


def sms_loop_for_green_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())

    session = requests.Session()
    session.verify = False
    is_logged_in = False

    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")

    success, new_session = login_green(account)
    if success:
        session = new_session
        is_logged_in = True
    else:
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")

    load_last_seen()
    errors = 0
    base_url = SETTINGS[site_key]["base_url"]
    ajax_path = SETTINGS[site_key]["ajax_path"]
    timeout = SETTINGS[site_key]["timeout"]

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                print(f"[Green] ({username}) 🔑 تغيير كلمة المرور، إعادة الدخول...")
                password = current_account.get("password")
                success, new_session = login_green(current_account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    is_logged_in = False
                    time.sleep(30)
                    continue

            if not is_logged_in:
                success, new_session = login_green(current_account or account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    time.sleep(30)
                    continue

            today = datetime.now().strftime('%Y-%m-%d')

            codes_html = ""
            try:
                resp_codes = session.get(base_url + "/ints/agent/SMSCDRReports", timeout=timeout)
                codes_html = resp_codes.text
                if 'login' in resp_codes.url.lower():
                    is_logged_in = False
                    continue
            except Exception as e:
                print(f"[Green] ({username}) [!] Error loading codes page: {e}")
                is_logged_in = False
                continue

            sesskey = ""
            sesskey_match = re.search(r'sesskey=([A-Za-z0-9=]+)', codes_html)
            if sesskey_match:
                sesskey = sesskey_match.group(1)
            else:
                is_logged_in = False
                continue

            params = {
                'fdate1': f'{today} 00:00:00',
                'fdate2': f'{today} 23:59:59',
                'frange': '', 'fclient': '', 'fnum': '', 'fcli': '',
                'fgdate': '', 'fgmonth': '', 'fgrange': '', 'fgclient': '',
                'fgnumber': '', 'fgcli': '', 'fg': '0', 'sesskey': sesskey
            }

            ajax_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': base_url + "/ints/agent/SMSCDRReports"
            }

            r = session.get(base_url + ajax_path, params=params, headers=ajax_headers, timeout=timeout)

            if r.status_code != 200 or 'login' in r.url.lower():
                is_logged_in = False
                continue

            data_json = r.json()
            if data_json.get('aaData'):
                rows = data_json['aaData']
            else:
                rows = data_json if isinstance(data_json, list) else []

            if not rows:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                try:
                    rows.sort(key=lambda x: str(x[0]) if isinstance(x, list) and len(x) > 0 else "", reverse=True)
                except:
                    pass

                new_messages = []
                for row in rows:
                    if isinstance(row, list) and len(row) >= 6:
                        date_str = str(row[0]).strip()
                        number = re.sub(r'\D', '', str(row[2]))
                        sms = str(row[5]).strip()

                        if sms.count(',') > 3 or sms.count('%') > 1 or 'NAN%' in sms:
                            continue
                        if re.match(r'^[\d.,%|NAN/]+$', sms):
                            continue

                        key = f"{date_str}|{number}"
                        if key == last_seen_key_local:
                            break
                        new_messages.append({'date': date_str, 'number': number, 'sms': sms})

                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")

                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg['sms'])
                        service_name = f"{detect_service(msg['sms'])}"
                        format_otp_message_v2(msg['number'], sms_text, service_name, otp_val)
                        if otp_val:
                            print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val)
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35
                                    match = re.search(r'after (\d+)', str(e))
                                    if match: wait_time = int(match.group(1)) + 2
                                    print(f"⚠️ Telegram 429: Waiting {wait_time}s...")
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")

            errors = 0
        except Exception as e:
            errors += 1
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break

def sms_loop_for_ksi_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())

    session = requests.Session()
    session.verify = False
    is_logged_in = False

    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")

    success, new_session = login_ksi(account)
    if success:
        session = new_session
        is_logged_in = True
    else:
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")

    load_last_seen()
    errors = 0

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                print(f"[KSI] ({username}) 🔑 تغيير كلمة المرور، إعادة الدخول...")
                password = current_account.get("password")
                success, new_session = login_ksi(current_account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    is_logged_in = False
                    time.sleep(30)
                    continue

            if not is_logged_in:
                success, new_session = login_ksi(current_account or account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    time.sleep(30)
                    continue

            today = datetime.now().strftime('%Y-%m-%d')
            base_url_ksi = SETTINGS["ksi"]["base_url"]

            codes_html = ""
            try:
                resp_codes = session.get(base_url_ksi + "/ints/agent/SMSCDRReports", timeout=SETTINGS["ksi"]["timeout"])
                codes_html = resp_codes.text
                if 'login' in resp_codes.url.lower():
                    is_logged_in = False
                    continue
            except Exception as e:
                print(f"[KSI] ({username}) [!] Error loading codes page: {e}")
                is_logged_in = False
                continue

            sesskey = ""
            sesskey_match = re.search(r'sesskey=([A-Za-z0-9=]+)', codes_html)
            if sesskey_match:
                sesskey = sesskey_match.group(1)
            else:
                is_logged_in = False
                continue

            params = {
                'fdate1': f'{today} 00:00:00',
                'fdate2': f'{today} 23:59:59',
                'frange': '', 'fclient': '', 'fnum': '', 'fcli': '',
                'fgdate': '', 'fgmonth': '', 'fgrange': '', 'fgclient': '',
                'fgnumber': '', 'fgcli': '', 'fg': '0', 'sesskey': sesskey
            }

            ajax_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': base_url_ksi + "/ints/agent/SMSCDRReports"
            }

            ajax_url = base_url_ksi + SETTINGS["ksi"]["ajax_path"]
            r = session.get(ajax_url, params=params, headers=ajax_headers, timeout=SETTINGS["ksi"]["timeout"])

            if r.status_code != 200 or 'login' in r.url.lower():
                is_logged_in = False
                continue

            data_json = r.json()
            if data_json.get('aaData'):
                rows = data_json['aaData']
            else:
                rows = data_json if isinstance(data_json, list) else []

            if not rows:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                try:
                    rows.sort(key=lambda x: str(x[0]) if isinstance(x, list) and len(x) > 0 else "", reverse=True)
                except:
                    pass

                new_messages = []
                for row in rows:
                    if isinstance(row, list) and len(row) >= 6:
                        date_str = str(row[0]).strip()
                        number = re.sub(r'\D', '', str(row[2]))
                        sms = str(row[5]).strip()

                        if sms.count(',') > 3 or sms.count('%') > 1 or 'NAN%' in sms:
                            continue
                        if re.match(r'^[\d.,%|NAN/]+$', sms):
                            continue

                        key = f"{date_str}|{number}"
                        if key == last_seen_key_local:
                            break
                        new_messages.append({'date': date_str, 'number': number, 'sms': sms})

                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")

                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg['sms'])
                        service_name = f"{detect_service(msg['sms'])}"
                        format_otp_message_v2(msg['number'], sms_text, service_name, otp_val)
                        if otp_val:
                            print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val)
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35
                                    match = re.search(r'after (\d+)', str(e))
                                    if match:
                                        wait_time = int(match.group(1)) + 2
                                    print(f"⚠️ Telegram 429 Flood Control: Waiting {wait_time}s...")
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")

            errors = 0
        except Exception as e:
            errors += 1
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break

def sms_loop_for_rsayel_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())
    session = requests.Session()
    session.verify = False
    is_logged_in = False
    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")
    success, new_session = login_rsayel(account)
    if success:
        session = new_session
        is_logged_in = True
    else:
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")

    load_last_seen()
    errors = 0
    base_url = SETTINGS[site_key]["base_url"]
    ajax_path = SETTINGS[site_key]["ajax_path"]
    timeout = SETTINGS[site_key]["timeout"]

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                password = current_account.get("password")
                success, new_session = login_rsayel(current_account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    is_logged_in = False
                    time.sleep(30)
                    continue
            if not is_logged_in:
                success, new_session = login_rsayel(current_account or account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    time.sleep(30)
                    continue
            today = datetime.now().strftime('%Y-%m-%d')
            codes_html = ""
            try:
                resp_codes = session.get(base_url + "/ints/agent/SMSCDRReports", timeout=timeout)
                codes_html = resp_codes.text
                if 'login' in resp_codes.url.lower():
                    is_logged_in = False
                    continue
            except Exception as e:
                print(f"[rsayel] ({username}) [!] Error loading codes page: {e}")
                is_logged_in = False
                continue
            sesskey = ""
            sesskey_match = re.search(r'sesskey=([A-Za-z0-9=]+)', codes_html)
            if sesskey_match:
                sesskey = sesskey_match.group(1)
            else:
                is_logged_in = False
                continue
            params = {
                'fdate1': f'{today} 00:00:00',
                'fdate2': f'{today} 23:59:59',
                'frange': '', 'fclient': '', 'fnum': '', 'fcli': '',
                'fgdate': '', 'fgmonth': '', 'fgrange': '', 'fgclient': '',
                'fgnumber': '', 'fgcli': '', 'fg': '0', 'sesskey': sesskey
            }
            ajax_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': base_url + "/ints/agent/SMSCDRReports"
            }
            r = session.get(base_url + ajax_path, params=params, headers=ajax_headers, timeout=timeout)
            if r.status_code != 200 or 'login' in r.url.lower():
                is_logged_in = False
                continue
            data_json = r.json()
            rows = data_json.get('aaData', data_json if isinstance(data_json, list) else [])
            if not rows:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                try:
                    rows.sort(key=lambda x: str(x[0]) if isinstance(x, list) and len(x) > 0 else "", reverse=True)
                except: pass
                new_messages = []
                for row in rows:
                    if isinstance(row, list) and len(row) >= 6:
                        date_str = str(row[0]).strip()
                        number = re.sub(r'\D', '', str(row[2]))
                        sms = str(row[5]).strip()
                        if sms.count(',') > 3 or sms.count('%') > 1 or 'NAN%' in sms:
                            continue
                        if re.match(r'^[\d.,%|NAN/]+$', sms):
                            continue
                        key = f"{date_str}|{number}"
                        if key == last_seen_key_local: break
                        new_messages.append({'date': date_str, 'number': number, 'sms': sms})
                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")
                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg['sms'])
                        service_name = f"{detect_service(msg['sms'])}"
                        format_otp_message_v2(msg['number'], sms_text, service_name, otp_val)
                        if otp_val:
                            print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val)
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35
                                    match = re.search(r'after (\d+)', str(e))
                                    if match: wait_time = int(match.group(1)) + 2
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            errors = 0
        except Exception as e:
            errors += 1
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)
        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break

def sms_loop_for_grand_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username", "API")
    password = account.get("password", "")
    api_key = account.get("api_key", "").strip()
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())

    session = None
    is_logged_in = False
    use_api = bool(api_key)

    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")

    if use_api:
        print_monitoring_box(site_name, username, "🔑", "وضع API Key")
        is_logged_in = True
    else:
        success, new_session = login_grand(account)
        if success:
            session = new_session
            is_logged_in = True
        else:
            print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")

    load_last_seen()
    errors = 0
    api_base = "https://api.grand-panel.com"
    timeout = SETTINGS[site_key]["timeout"]

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account:
                new_api_key = current_account.get("api_key", "").strip()
                if new_api_key != api_key:
                    api_key = new_api_key
                    use_api = bool(api_key)
                    is_logged_in = use_api
                if not use_api and current_account.get("password") != password:
                    password = current_account.get("password")
                    success, new_session = login_grand(current_account)
                    if success:
                        session = new_session
                        is_logged_in = True
                    else:
                        is_logged_in = False
                        time.sleep(30)
                        continue

            if not is_logged_in:
                if use_api:
                    is_logged_in = True
                else:
                    success, new_session = login_grand(current_account or account)
                    if success:
                        session = new_session
                        is_logged_in = True
                    else:
                        time.sleep(30)
                        continue

            today = datetime.now().strftime('%Y-%m-%d')
            rows = []

            if use_api:
                try:
                    api_headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json"
                    }
                    r = requests.get(
                        f"{api_base}/api/v1/messages",
                        params={"date": today},
                        headers=api_headers,
                        timeout=timeout,
                        verify=False
                    )
                    if r.status_code == 401:
                        print(f"[grand] ({username}) ❌ API Key غير صحيح (401)")
                        time.sleep(60)
                        continue
                    if r.status_code != 200:
                        print(f"[grand] ({username}) [!] API error: {r.status_code}")
                        time.sleep(15)
                        continue
                    data_json = r.json()
                    rows = data_json.get("messages", [])
                    print(f"[grand-API] ({username}) 📡 total={data_json.get('total', len(rows))}")
                except Exception as e:
                    print(f"[grand-API] ({username}) ❌ خطأ: {e}")
                    time.sleep(15)
                    continue
            else:
                try:
                    panel_base = "https://panel.grand-panel.com"
                    ajax_headers = {
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": panel_base + "/dashboard"
                    }
                    r = session.get(
                        panel_base + "/cdrs",
                        params={"start": 0, "length": 50,
                                "date_from": f"{today} 00:00:00",
                                "date_to": f"{today} 23:59:59"},
                        headers=ajax_headers,
                        timeout=timeout
                    )
                    if r.status_code != 200 or "login" in r.url.lower():
                        is_logged_in = False
                        continue
                    data_json = r.json()
                    rows = data_json.get("data", data_json.get("aaData", []))
                except Exception as e:
                    print(f"[grand-session] ({username}) [!] Error: {e}")
                    is_logged_in = False
                    continue

            if not rows:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                try:
                    rows.sort(key=lambda x: x.get("date", "") if isinstance(x, dict) else "", reverse=True)
                except: pass

                new_messages = []
                for row in rows:
                    if isinstance(row, dict):
                        date_str = str(row.get("date", "")).strip()
                        number   = re.sub(r'\D', '', str(row.get("number", row.get("destination", ""))))
                        sms      = str(row.get("content", row.get("message", row.get("sms", "")))).strip()
                    elif isinstance(row, list) and len(row) >= 6:
                        date_str = str(row[0]).strip()
                        number   = re.sub(r'\D', '', str(row[2]))
                        sms      = str(row[5]).strip()
                    else:
                        continue

                    if not sms or not number:
                        continue
                    if re.match(r'^[\d.,%|NAN/]+$', sms):
                        continue

                    key = f"{date_str}|{number}"
                    if key == last_seen_key_local:
                        break
                    new_messages.append({"date": date_str, "number": number, "sms": sms})

                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")
                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg["sms"])
                        service_name = f"{detect_service(msg['sms'])}"
                        if otp_val:
                            print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")
                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg["number"]), sms_text, msg["number"], service_name, otp_val)
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35
                                    match = re.search(r'after (\d+)', str(e))
                                    if match: wait_time = int(match.group(1)) + 2
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")

            errors = 0
        except Exception as e:
            errors += 1
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break

# ─────────────────────────── Flash SMS panel (flashsms.space) ────────────────────────────
def sms_loop_for_prim_flash_account(site_key, account):
    """Monitor loop for PRIM-FLASH API with Bearer token authentication."""
    stop_key = f"{site_key}_{account.get('id', '')}"
    stop_event = account_stop_events.get(stop_key)
    if stop_event is None:
        stop_event = Event()
        account_stop_events[stop_key] = stop_event

    api_token = account.get("api_token", "")
    api_url = SETTINGS[site_key].get("api_url", "http://flashsms.space/api/cdr/viewstats")
    check_interval = SETTINGS[site_key].get("check_interval", 5)
    timeout = SETTINGS[site_key].get("timeout", 30)

    sent_messages_file = f"sent_messages_{site_key}_{account.get('id', '')}.json"
    sent_messages = set()
    if os.path.exists(sent_messages_file):
        try:
            with open(sent_messages_file, "r", encoding="utf-8") as f:
                sent_messages = set(json.load(f))
        except:
            sent_messages = set()

    print(f"[PRIM-FLASH] 🚀 بدء المراقبة لـ {account.get('id', '')[:8]}...")

    while not stop_event.is_set():
        try:
            # Attempt 1: Bearer Token
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            r = requests.get(api_url, headers=headers, params={"records": 50}, timeout=timeout)

            # Attempt 2: Fallback to query param
            if r.status_code in [401, 403, 400]:
                r = requests.get(api_url, params={"token": api_token, "records": 50}, timeout=timeout)

            if r.status_code == 200:
                try:
                    data = r.json()

                    # Handle different response formats
                    messages = []
                    if isinstance(data, list):
                        messages = data
                    elif isinstance(data, dict):
                        if data.get("status") == "success" and data.get("data"):
                            messages = data["data"]
                        elif "records" in data:
                            messages = data["records"]
                        elif "messages" in data:
                            messages = data["messages"]
                        elif "result" in data:
                            messages = data["result"]
                        else:
                            for v in data.values():
                                if isinstance(v, list) and len(v) > 0:
                                    messages = v
                                    break

                    for msg in messages:
                        sms_text = (
                            msg.get("message") or 
                            msg.get("sms") or 
                            msg.get("text") or 
                            msg.get("body") or 
                            msg.get("content") or
                            (msg[5] if isinstance(msg, (list, tuple)) and len(msg) > 5 else "")
                        )
                        number = (
                            msg.get("num") or 
                            msg.get("number") or 
                            msg.get("msisdn") or 
                            msg.get("cli") or 
                            msg.get("from") or 
                            msg.get("source") or
                            (msg[2] if isinstance(msg, (list, tuple)) and len(msg) > 2 else "")
                        )
                        date_str = (
                            msg.get("dt") or 
                            msg.get("date") or 
                            msg.get("time") or 
                            msg.get("created_at") or
                            (msg[0] if isinstance(msg, (list, tuple)) and len(msg) > 0 else "")
                        )

                        if not sms_text or not number:
                            continue

                        unique_key = f"{date_str}|{number}|{sms_text}"
                        if unique_key in sent_messages:
                            continue

                        sent_messages.add(unique_key)
                        try:
                            with open(sent_messages_file, "w", encoding="utf-8") as f:
                                json.dump(list(sent_messages), f)
                        except:
                            pass

                        otp, decoded_text = extract_from_message(str(sms_text))
                        service_detected = detect_service(decoded_text, "")

                        formatted = format_otp_message(
                            number=str(number),
                            sms_text=str(decoded_text or sms_text),
                            service_name=service_detected,
                            otp_code=otp,
                            user_id=None
                        )

                        if OTP_GROUP and RETURN_OTP_ENABLED:
                            try:
                                msg_obj = bot.send_message(
                                    OTP_GROUP, formatted,
                                    parse_mode="HTML",
                                    reply_markup=create_group_otp_keyboard(otp)
                                )
                                auto_delete_message(OTP_GROUP, msg_obj.message_id)
                            except Exception as e:
                                print(f"[PRIM-FLASH] Error sending to group: {e}")

                        try:
                            parsed_num = phonenumbers.parse("+" + str(number).lstrip("+"))
                            country_name = geocoder.description_for_number(parsed_num, "en") or "Unknown"
                        except:
                            country_name = "Unknown"
                        log_live_traffic(number, country_name, str(service_detected))

                        update_statistics(country_name)

                except Exception as e:
                    print(f"[PRIM-FLASH] Error parsing response: {e}")
            else:
                print(f"[PRIM-FLASH] HTTP Error: {r.status_code}")

        except Exception as e:
            print(f"[PRIM-FLASH] Monitor error: {e}")

        for _ in range(check_interval):
            if stop_event.is_set():
                break
            time.sleep(1)

    print(f"[PRIM-FLASH] 🛑 تم إيقاف المراقبة لـ {account.get('id', '')[:8]}")

def sms_loop_for_flash_sms_account(site_key, account):
    """Monitor loop for Flash SMS API with Bearer token authentication."""
    stop_key = f"{site_key}_{account.get('id', '')}"
    stop_event = account_stop_events.get(stop_key)
    if stop_event is None:
        stop_event = Event()
        account_stop_events[stop_key] = stop_event

    api_token = account.get("api_token", "")
    api_url = SETTINGS[site_key].get("api_url", "https://www.flashsms.space/api/cdr/viewstats")
    check_interval = SETTINGS[site_key].get("check_interval", 5)
    timeout = SETTINGS[site_key].get("timeout", 30)
    
    sent_messages_file = f"sent_messages_{site_key}_{account.get('id', '')}.json"
    sent_messages = set()
    if os.path.exists(sent_messages_file):
        try:
            with open(sent_messages_file, "r", encoding="utf-8") as f:
                sent_messages = set(json.load(f))
        except:
            sent_messages = set()

    print(f"[Flash_SMS] 🚀 بدء المراقبة لـ {account.get('id', '')[:8]}...")
    
    while not stop_event.is_set():
        try:
            # ── Attempt 1: Bearer Token ──
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            r = requests.get(api_url, headers=headers, params={"records": 50}, timeout=timeout)
            
            # ── Attempt 2: Fallback to query param ──
            if r.status_code in [401, 403, 400]:
                r = requests.get(api_url, params={"token": api_token, "records": 50}, timeout=timeout)
            
            if r.status_code == 200:
                try:
                    data = r.json()
                    
                    # Handle different response formats
                    messages = []
                    if isinstance(data, list):
                        messages = data
                    elif isinstance(data, dict):
                        if data.get("status") == "success" and data.get("data"):
                            messages = data["data"]
                        elif "records" in data:
                            messages = data["records"]
                        elif "messages" in data:
                            messages = data["messages"]
                        elif "result" in data:
                            messages = data["result"]
                        else:
                            for v in data.values():
                                if isinstance(v, list) and len(v) > 0:
                                    messages = v
                                    break
                    
                    for msg in messages:
                        sms_text = (
                            msg.get("message") or 
                            msg.get("sms") or 
                            msg.get("text") or 
                            msg.get("body") or 
                            msg.get("content") or
                            (msg[5] if isinstance(msg, (list, tuple)) and len(msg) > 5 else "")
                        )
                        number = (
                            msg.get("num") or 
                            msg.get("number") or 
                            msg.get("msisdn") or 
                            msg.get("cli") or 
                            msg.get("from") or 
                            msg.get("source") or
                            (msg[2] if isinstance(msg, (list, tuple)) and len(msg) > 2 else "")
                        )
                        date_str = (
                            msg.get("dt") or 
                            msg.get("date") or 
                            msg.get("time") or 
                            msg.get("created_at") or
                            (msg[0] if isinstance(msg, (list, tuple)) and len(msg) > 0 else "")
                        )
                        
                        if not sms_text or not number:
                            continue
                        
                        unique_key = f"{date_str}|{number}|{sms_text}"
                        if unique_key in sent_messages:
                            continue
                        
                        sent_messages.add(unique_key)
                        try:
                            with open(sent_messages_file, "w", encoding="utf-8") as f:
                                json.dump(list(sent_messages), f)
                        except:
                            pass
                        
                        otp, decoded_text = extract_from_message(str(sms_text))
                        service_detected = detect_service(decoded_text, "")
                        
                        formatted = format_otp_message(
                            number=str(number),
                            sms_text=str(decoded_text or sms_text),
                            service_name=service_detected,
                            otp_code=otp,
                            user_id=None
                        )
                        
                        if OTP_GROUP and RETURN_OTP_ENABLED:
                            try:
                                msg_obj = bot.send_message(
                                    OTP_GROUP, formatted,
                                    parse_mode="HTML",
                                    reply_markup=create_group_otp_keyboard(otp)
                                )
                                auto_delete_message(OTP_GROUP, msg_obj.message_id)
                            except Exception as e:
                                print(f"[Flash_SMS] Error sending to group: {e}")
                        
                        try:
                            parsed_num = phonenumbers.parse("+" + str(number).lstrip("+"))
                            country_name = geocoder.description_for_number(parsed_num, "en") or "Unknown"
                        except:
                            country_name = "Unknown"
                        log_live_traffic(number, country_name, str(service_detected))
                        
                        update_statistics(country_name)
                        
                except Exception as e:
                    print(f"[Flash_SMS] Error parsing response: {e}")
            else:
                print(f"[Flash_SMS] HTTP Error: {r.status_code}")
                
        except Exception as e:
            print(f"[Flash_SMS] Monitor error: {e}")
        
        for _ in range(check_interval):
            if stop_event.is_set():
                break
            time.sleep(1)
    
    print(f"[Flash_SMS] 🛑 تم إيقاف المراقبة لـ {account.get('id', '')[:8]}")

def start_monitoring_for_account(site_key, account):
    
    if site_key == "Number_Panel":
        sms_loop_for_number_panel_account(site_key, account)
    elif site_key == "iVASMS":
        sms_loop_for_ivasms_account(site_key, account)
    elif site_key == "IMS":
        sms_loop_for_ims_account(site_key, account)
    elif site_key == "Roxy SMS":
        sms_loop_for_roxy_account(site_key, account)
    elif site_key == "Flash_SMS":
        sms_loop_for_flash_sms_account(site_key, account)
    elif site_key == "PRIM-FLASH":
        sms_loop_for_prim_flash_account(site_key, account)
    elif site_key in ["Konekta_API", "TimeSMS_API", "Hadi_SMS", "Horus", "Pac_Call", "PRIM-FLASH"]:
        sms_loop_for_api_panel(site_key, account)
    elif site_key == "MBC":
        sms_loop_for_mbc_account(site_key, account)
    elif site_key in ["Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "Flex"]:
        # استخدام الدالة العامة للبانلز الجديدة
        sms_loop_requests_based(site_key, account)
    elif site_key == "green":
        sms_loop_for_green_account(site_key, account)
    elif site_key == "ksi":
        sms_loop_for_ksi_account(site_key, account)
    elif site_key == "rsayel":
        sms_loop_for_rsayel_account(site_key, account)
    elif site_key == "grand":
        sms_loop_for_grand_account(site_key, account)
    elif site_key == "Basha":
        sms_loop_for_basha_account(site_key, account)
    else:
        sms_loop_requests_based(site_key, account)

# ─────────────────────────── Basha panel (basha.cc) ────────────────────────────
_BASHA_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_BASHA_BASE_HEADERS = {
    "User-Agent":      _BASHA_UA,
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection":      "keep-alive",
}

_BASHA_AJAX_HEADERS = {
    "User-Agent":       _BASHA_UA,
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Accept-Language":  "en-US,en;q=0.9",
    "Accept-Encoding":  "gzip, deflate",
    "X-Requested-With": "XMLHttpRequest",
    "Connection":       "keep-alive",
}

_BASHA_LOGIN_PAGE_SIGNALS = [
    "sign in", "signin", "please sign",
    "log in", "please login",
    "authentication required", "session expired",
    "unauthorized", "access denied",
]


def _basha_session():
    s = requests.Session()
    s.headers.update(_BASHA_BASE_HEADERS)
    return s


def _basha_is_session_expired(resp):
    if resp.status_code in (401, 403):
        return True
    final_url = str(resp.url).lower()
    if any(x in final_url for x in ["/login", "/signin", "/sign-in", "/auth/login"]):
        return True
    if resp.history:
        last_url = str(resp.history[-1].url).lower()
        if (any(x in last_url for x in ["/login", "/signin", "/sign-in"])
                and "json" not in resp.headers.get("Content-Type", "").lower()):
            page = resp.text[:1500].lower()
            if "<html" in page and any(w in page for w in ["sign in", "please login", "signin"]):
                return True
    ct = resp.headers.get("Content-Type", "").lower()
    if "json" not in ct:
        text_low = resp.text[:3000].lower()
        if ("<html" in text_low or "<form" in text_low):
            if any(w in text_low for w in _BASHA_LOGIN_PAGE_SIGNALS):
                return True
    return False


def _basha_classify(resp):
    if _basha_is_session_expired(resp):
        return "login_page"
    ct = resp.headers.get("Content-Type", "").lower()
    text = resp.text.strip()
    if not text:
        return "empty"
    if "json" in ct or text.startswith("[") or text.startswith("{"):
        return "json"
    return "html_other"


def basha_login(email, pw, url="https://basha.cc"):
    url = (url or "https://basha.cc").rstrip("/")
    s = _basha_session()
    try:
        r = s.get(f"{url}/login", timeout=25, allow_redirects=True)
    except Exception as e:
        raise Exception(f"server unreachable: {e}")

    if r.status_code in (403, 401):
        raise Exception(f"IP blocked (HTTP {r.status_code})")

    csrf = ""
    m = re.search(r'name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']', r.text)
    if m:
        csrf = m.group(1)
    else:
        m = re.search(r'name=["\']_token["\'][^>]+value=["\']([^"\']+)["\']', r.text)
        if m:
            csrf = m.group(1)

    xsrf_cookie = s.cookies.get("XSRF-TOKEN")

    post_data = {"email": email, "password": pw, "remember": "on"}
    if csrf:
        post_data["_token"] = csrf

    headers = {**_BASHA_BASE_HEADERS,
               "Referer": f"{url}/login",
               "Content-Type": "application/x-www-form-urlencoded",
               "Origin": url}
    if xsrf_cookie:
        try:
            from urllib.parse import unquote as _unquote
            headers["X-XSRF-TOKEN"] = _unquote(xsrf_cookie)
        except Exception:
            pass

    try:
        r2 = s.post(f"{url}/login", data=post_data, headers=headers,
                    allow_redirects=True, timeout=20)
    except Exception as e:
        raise Exception(f"login POST failed: {e}")

    final_url = str(r2.url).lower()
    if "/login" in final_url:
        low = r2.text.lower()
        if "these credentials do not match" in low or "invalid" in low or "incorrect" in low:
            raise Exception("login failed — invalid email/password")
        raise Exception("login failed — redirected back to login page")

    logger_msg = f"[Basha] ✅ تسجيل دخول ناجح: {email}"
    print(logger_msg)
    return s, "home", url


def _basha_parse_table(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    table = None
    for t in soup.find_all("table"):
        thead = t.find("thead")
        head_txt = thead.get_text(" ", strip=True).lower() if thead else ""
        if "destination" in head_txt and "message" in head_txt:
            table = t
            break
    if table is None:
        return None, {"table_found": False}

    headers = []
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(" ", strip=True).lower() for th in thead.find_all("th")]

    def _idx(*keywords):
        for i, h in enumerate(headers):
            if any(k in h for k in keywords):
                return i
        return None

    i_range = _idx("range")
    i_dest = _idx("destination")
    i_src = _idx("source")
    i_msg = _idx("message")

    tbody = table.find("tbody") or table
    trs = tbody.find_all("tr")

    out = []
    for tr in trs:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if not cells:
            continue
        number = cells[i_dest] if i_dest is not None and i_dest < len(cells) else ""
        sender = cells[i_src] if i_src is not None and i_src < len(cells) else ""
        message = cells[i_msg] if i_msg is not None and i_msg < len(cells) else ""
        range_name = cells[i_range] if i_range is not None and i_range < len(cells) else ""
        number = re.sub(r"\D", "", number)
        if not number or not message:
            continue
        out.append({
            "number": number,
            "cli": sender or range_name,
            "sms": html.unescape(message),
        })
    return out, {"table_found": True, "headers": headers, "tr_count": len(trs)}


def _basha_parse_json(text):
    try:
        js = json.loads(text)
    except Exception:
        return []
    rows = js.get("data") if isinstance(js, dict) else (js if isinstance(js, list) else [])
    out = []
    for row in rows or []:
        if isinstance(row, dict):
            number = re.sub(r"\D", "", str(
                row.get("destination_number") or row.get("destination") or
                row.get("number") or row.get("msisdn") or ""))
            sender = str(row.get("source_number") or row.get("source") or
                         row.get("sender") or row.get("cli") or "")
            message = str(row.get("message_text") or row.get("message") or
                          row.get("text") or row.get("sms") or "")
        elif isinstance(row, list) and len(row) >= 4:
            number = re.sub(r"\D", "", str(row[1]))
            sender = str(row[2])
            message = str(row[3])
        else:
            continue
        if not number or not message:
            continue
        out.append({"number": number, "cli": sender, "sms": html.unescape(message)})
    return out


def _basha_parse_csv(text):
    out = []
    try:
        reader = csv.reader(StringIO(text))
        header = next(reader, None)
        if not header:
            return out
        head_low = [h.strip().lower() for h in header]

        def _idx(*keywords):
            for i, h in enumerate(head_low):
                if any(k in h for k in keywords):
                    return i
            return None

        i_dest = _idx("destination")
        i_src = _idx("source")
        i_msg = _idx("message")
        for row in reader:
            if not row:
                continue
            number = re.sub(r"\D", "", row[i_dest]) if i_dest is not None and i_dest < len(row) else ""
            sender = row[i_src] if i_src is not None and i_src < len(row) else ""
            message = row[i_msg] if i_msg is not None and i_msg < len(row) else ""
            if not number or not message:
                continue
            out.append({"number": number, "cli": sender, "sms": html.unescape(message)})
    except Exception:
        return out
    return out


def _basha_resolve_messages(s, page_html, base_url, page_url):
    dt_params = {
        "draw": "1", "start": "0", "length": "100",
        "search[value]": "", "search[regex]": "false",
    }

    bundle_srcs = re.findall(r'<script[^>]+src="([^"]+/build/assets/[^"]+\.js)"', page_html)
    for src in bundle_srcs[:3]:
        try:
            rb = s.get(src, timeout=15, headers={**_BASHA_BASE_HEADERS, "Referer": page_url})
        except Exception:
            continue
        body = rb.text
        for m in re.finditer(r'["\'](/[a-zA-Z0-9_\-/]*messages?[a-zA-Z0-9_\-/]*)["\']', body):
            cand = m.group(1)
            if cand.rstrip("/") == "/my/messages":
                continue
            cand_url = cand if cand.startswith("http") else base_url.rstrip("/") + "/" + cand.lstrip("/")
            try:
                rj = s.get(cand_url, params=dt_params,
                           headers={**_BASHA_AJAX_HEADERS, "Referer": page_url}, timeout=15)
            except Exception:
                continue
            if _basha_classify(rj) == "json":
                out = _basha_parse_json(rj.text)
                if out:
                    return out

    for suffix in ("/data", "-data", "/ajax", "/list", "/table", "/datatable", "/get"):
        cand_url = page_url + suffix
        try:
            rj = s.get(cand_url, params=dt_params,
                       headers={**_BASHA_AJAX_HEADERS, "Referer": page_url}, timeout=15)
        except Exception:
            continue
        if _basha_classify(rj) == "json":
            out = _basha_parse_json(rj.text)
            if out:
                return out

    today = datetime.utcnow().date()
    date_from = (today - timedelta(days=30)).isoformat()
    date_to = today.isoformat()
    csv_param_sets = [
        {"from": date_from, "to": date_to},
        {"date_from": date_from, "date_to": date_to},
        {"start_date": date_from, "end_date": date_to},
        {"from_date": date_from, "to_date": date_to},
    ]
    for suffix in ("/download", "/export", "/csv", "/export-csv", "/download-csv"):
        cand_url = page_url + suffix
        for params in csv_param_sets:
            try:
                rc = s.get(cand_url, params=params,
                           headers={**_BASHA_BASE_HEADERS, "Referer": page_url}, timeout=15)
            except Exception:
                continue
            ctype = rc.headers.get("Content-Type", "").lower()
            text = rc.text.strip()
            if rc.status_code == 200 and text and (("," in text.splitlines()[0]) if text.splitlines() else False) \
                    and ("csv" in ctype or "destination" in text.lower()[:400] or "range" in text.lower()[:400]):
                out = _basha_parse_csv(text)
                if out:
                    return out
            break

    return None


def basha_fetch(session_info, url="https://basha.cc"):
    if not (isinstance(session_info, tuple) and len(session_info) == 3
            and hasattr(session_info[0], "cookies")):
        return []
    s, _path, _url = session_info
    url = (_url or url or "https://basha.cc").rstrip("/")
    page_url = f"{url}/my/messages"

    try:
        r = s.get(page_url, timeout=20, allow_redirects=True,
                  headers={**_BASHA_BASE_HEADERS, "Referer": f"{url}/home"})
    except Exception as e:
        err = str(e)
        if any(x in err for x in ["NewConnection", "ConnectionError", "Failed to establish", "Max retries"]):
            return []
        raise

    if str(r.url).lower().rstrip("/").endswith("/login"):
        return None  # session expired

    rows, debug = _basha_parse_table(r.text)

    if not rows:
        found = _basha_resolve_messages(s, r.text, url, page_url)
        if found is not None:
            return found
        return []

    return rows or []


def sms_loop_for_basha_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    email = account.get("username")  # بيستخدم حقل username كـ email
    password = account.get("password")
    base_url = SETTINGS[site_key].get("base_url", "https://basha.cc")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())

    session_info = None
    is_logged_in = False

    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except:
                pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except:
            pass

    print_monitoring_box(site_name, email, "🚀", "بدء المراقبة...")

    try:
        session_info = basha_login(email, password, base_url)
        is_logged_in = True
    except Exception as e:
        print_monitoring_box(site_name, email, "❌", f"فشل تسجيل الدخول: {e}")

    load_last_seen()
    errors = 0

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                print(f"[{site_name}] ({email}) 🔑 تم اكتشاف تغيير كلمة المرور، جاري إعادة الدخول...")
                password = current_account.get("password")
                try:
                    session_info = basha_login(email, password, base_url)
                    is_logged_in = True
                except Exception as e:
                    is_logged_in = False
                    print(f"[{site_name}] ({email}) ❌ فشل إعادة الدخول: {e}")
                    time.sleep(30)
                    continue

            if not is_logged_in:
                try:
                    session_info = basha_login(email, password, base_url)
                    is_logged_in = True
                except Exception as e:
                    print(f"[{site_name}] ({email}) ❌ فشل تسجيل الدخول: {e}")
                    time.sleep(30)
                    continue

            try:
                rows = basha_fetch(session_info, base_url)
            except Exception as e:
                print(f"[{site_name}] ({email}) ⚠️ خطأ أثناء الجلب: {e}")
                is_logged_in = False
                time.sleep(10)
                continue

            if rows is None:
                # الجلسة انتهت - نعيد تسجيل الدخول
                is_logged_in = False
                continue

            if not rows:
                print_monitoring_box(site_name, email, "📭", "لا توجد أكواد")
            else:
                new_messages = []
                for row in rows:
                    number = row.get("number", "")
                    sms = row.get("sms", "")
                    cli = row.get("cli", "")
                    if not number or not sms:
                        continue
                    key = f"{number}|{sms}"
                    if key == last_seen_key_local:
                        break
                    new_messages.append({"number": number, "sms": sms, "cli": cli})

                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['number']}|{new_messages[0]['sms']}"
                    save_last_seen()

                    print(f"[{site_name}] ({email}) 📨 {len(new_messages)} رسالة جديدة")

                    for msg in reversed(new_messages):
                        otp_val, sms_text = extract_from_message(msg["sms"])
                        service_name = f"{detect_service(sms_text)}"

                        print(f"🔑 {site_name} ({email}): لقيت كود {otp_val}")

                        for retry in range(3):
                            try:
                                send_otp_to_user(clean_number(msg["number"]), sms_text, msg["number"], service_name, otp_val, site_key=site_key)
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 35
                                    match = re.search(r'after (\d+)', str(e))
                                    if match:
                                        wait_time = int(match.group(1)) + 2
                                    print(f"⚠️ Telegram 429 (Flood Control): Waiting {wait_time}s...")
                                    time.sleep(wait_time)
                                else:
                                    print(f"❌ Error sending: {e}")
                                    break
                else:
                    print_monitoring_box(site_name, email, "📭", "لا توجد أكواد جديدة")

            errors = 0
        except Exception as e:
            errors += 1
            print(f"[{site_name}] ({email}) ⚠️ خطأ عام: {e}")
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 10)):
            break

# ═══════════════════════════════════════════════════
# MBC 🅼 - دالة تسجيل الدخول والمراقبة (mbcs-ms.com)
# ═══════════════════════════════════════════════════
def login_mbc(account):
    """تسجيل الدخول لـ MBC (لوحة IPRN Billing & Softswitch - كابتشا رياضية)"""
    username = account.get("username", "")
    password = account.get("password", "")
    base_url = SETTINGS["MBC"]["base_url"]
    login_page_url = SETTINGS["MBC"]["login_page_url"]
    login_post_url = SETTINGS["MBC"]["login_post_url"]
    timeout = SETTINGS["MBC"]["timeout"]

    session = requests.Session()
    session.verify = False
    print(f"[MBC] ({username}) 🔄 محاولة تسجيل الدخول...")
    try:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        resp = session.get(login_page_url, timeout=timeout)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # الكابتشا شكلها "9 + 3 = ?"
        captcha_answer = None
        patterns = [r'(\d+)\s*\+\s*(\d+)\s*=\s*\?', r'What is (\d+) \+ (\d+)', r'(\d+)\s*\+\s*(\d+)\s*=', r'(\d+)\s*plus\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, resp.text, re.IGNORECASE)
            if match:
                captcha_answer = str(int(match.group(1)) + int(match.group(2)))
                break

        if not captcha_answer:
            b_tags = soup.find_all(['b', 'strong', 'span', 'label'])
            nums = []
            for tag in b_tags:
                text = tag.get_text().strip()
                if text.isdigit():
                    nums.append(int(text))
            if len(nums) >= 2:
                captcha_answer = str(nums[0] + nums[1])

        if not captcha_answer:
            print(f"[MBC] ({username}) ⚠️ لم يتم العثور على captcha")
            return False, None

        print(f"[MBC] ({username}) [*] Captcha: {captcha_answer}")

        # CSRF token
        csrf_token = None
        csrf_input = soup.find('input', {'name': '_token'}) or soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = str(csrf_input.get('value', ''))
        if not csrf_token:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = str(csrf_meta.get('content', ''))

        login_data = {
            "username": username,
            "password": password,
            "capt": captcha_answer,
            "captcha": captcha_answer,
            "answer": captcha_answer,
        }
        if csrf_token:
            login_data["_token"] = csrf_token

        form = soup.find('form')
        if form:
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and isinstance(name, str) and name not in login_data:
                    login_data[name] = str(value) if value is not None else ''

        login_headers = {
            "Referer": login_page_url,
            "Origin": base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(login_post_url, data=login_data, headers=login_headers,
                                timeout=timeout, allow_redirects=True)

        print(f"[MBC] ({username}) [DEBUG] Final URL: {response.url}")

        if any(x in response.url.lower() for x in ["/dashboard", "/home", "/agent", "/panel"]) or \
           (response.status_code == 200 and "login" not in response.url.lower() and "signin" not in response.url.lower()):
            print(f"[MBC] ({username}) [+] تسجيل الدخول نجح")
            return True, session

        content_lower = response.text.lower()
        if "logout" in content_lower or "dashboard" in content_lower:
            print(f"[MBC] ({username}) [+] تسجيل الدخول نجح (Detected via content)")
            return True, session

        print(f"[MBC] ({username}) [!] فشل تسجيل الدخول")
        return False, None
    except Exception as e:
        print(f"[MBC] ({username}) [!] خطأ: {e}")
        return False, None


def _mbc_parse_row(cells_text):
    """استخراج الرقم والرسالة والتاريخ وCLI من صف جدول MBC
    ترتيب الأعمدة: Date | Range | Number | CLI | Client | SMS | Currency | My Payout | Client Payout"""
    if len(cells_text) >= 6:
        date_str = cells_text[0].strip()
        number = re.sub(r'\D', '', cells_text[2])
        cli = cells_text[3].strip() if len(cells_text) > 3 else ""
        message = cells_text[5].strip()
        if number and message and 8 <= len(number) <= 15:
            return date_str, number, message, cli

    # فولباك: لو الترتيب اتغير بأي شكل، دور بشكل مرن
    number = ""
    date_str = ""
    for cell in cells_text:
        if not date_str and re.search(r'\d{4}-\d{2}-\d{2}', cell):
            date_str = cell
        digits = re.sub(r'\D', '', cell)
        if not number and 8 <= len(digits) <= 15:
            number = digits
    candidates = [c for c in cells_text if c != number and c != date_str and len(c) > 3]
    message = max(candidates, key=len) if candidates else ""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cli = cells_text[3].strip() if len(cells_text) > 3 else ""
    return date_str, number, message, cli


def sms_loop_for_mbc_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())

    session = requests.Session()
    session.verify = False
    is_logged_in = False

    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""

    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass

    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")

    success, new_session = login_mbc(account)
    if success:
        session = new_session
        is_logged_in = True
    else:
        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول")

    load_last_seen()
    errors = 0
    messages_url = "https://mbcs-ms.com/stats/sms-cdr-stats"
    timeout = SETTINGS[site_key]["timeout"]

    while not stop_event.is_set():
        try:
            current_account = get_account_by_id(site_key, account_id)
            if current_account and current_account.get("password") != password:
                print(f"[MBC] ({username}) 🔑 تغيير كلمة المرور، إعادة الدخول...")
                password = current_account.get("password")
                success, new_session = login_mbc(current_account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    is_logged_in = False
                    time.sleep(30)
                    continue

            if not is_logged_in:
                success, new_session = login_mbc(current_account or account)
                if success:
                    session = new_session
                    is_logged_in = True
                else:
                    time.sleep(30)
                    continue

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Accept': 'application/json, text/javascript, text/html, */*; q=0.9',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': messages_url
            }

            try:
                resp = session.get(messages_url, headers=headers, timeout=timeout)
            except Exception as e:
                print(f"[MBC] ({username}) [!] Error loading messages page: {e}")
                is_logged_in = False
                continue

            if resp.status_code != 200 or 'login' in resp.url.lower():
                print(f"[MBC] ({username}) [!] فشل تحميل الرسائل - status={resp.status_code} url={resp.url}")
                is_logged_in = False
                continue

            rows = []
            data_json = None
            try:
                data_json = resp.json()
                if isinstance(data_json, dict):
                    for _k in ('aaData', 'data', 'records', 'result', 'results', 'sms', 'messages', 'rows', 'list'):
                        _v = data_json.get(_k)
                        if isinstance(_v, list) and _v:
                            rows = _v
                            break
                elif isinstance(data_json, list):
                    rows = data_json
            except Exception:
                rows = []

            new_messages = []
            seen_keys_this_cycle = set()
            if rows:
                for row in rows:
                    if isinstance(row, list) and len(row) >= 3:
                        cells_text = [str(c).strip() for c in row]
                        date_str, number, sms, cli = _mbc_parse_row(cells_text)
                    elif isinstance(row, dict):
                        number = ""
                        date_str = ""
                        sms = ""
                        cli = ""
                        for _k in ('number', 'msisdn', 'sender', 'from', 'phone', 'cli'):
                            if row.get(_k):
                                number = re.sub(r'\D', '', str(row.get(_k)))
                                break
                        for _k in ('message', 'sms', 'content', 'text', 'body'):
                            if row.get(_k):
                                sms = str(row.get(_k))
                                break
                        for _k in ('date', 'datetime', 'created_at', 'time', 'date_time'):
                            if row.get(_k):
                                date_str = str(row.get(_k))
                                break
                        for _k in ('cli', 'client_id', 'service', 'app'):
                            if row.get(_k):
                                cli = str(row.get(_k))
                                break
                        if not date_str:
                            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        continue

                    if not number or not sms:
                        continue
                    key = f"{date_str}|{number}"
                    if key == last_seen_key_local:
                        break
                    if key in seen_keys_this_cycle:
                        continue
                    seen_keys_this_cycle.add(key)
                    new_messages.append({'date': date_str, 'number': number, 'sms': sms, 'cli': cli})
            else:
                # Fallback: تحليل جدول HTML
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = None
                all_tables = soup.find_all('table')
                for _t in all_tables:
                    _header_cells = _t.find_all(['th', 'td'], limit=10)
                    _header_text = " ".join(c.get_text(strip=True).lower() for c in _header_cells)
                    if 'number' in _header_text and ('message' in _header_text or 'sms' in _header_text):
                        table = _t
                        break
                if table is None and all_tables:
                    table = max(all_tables, key=lambda t: len(t.find_all('tr')))

                if table:
                    tbody = table.find('tbody')
                    table_rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                    for row in table_rows:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue
                        cells_text = [cell.get_text(strip=True) for cell in cells]
                        date_str, number, sms, cli = _mbc_parse_row(cells_text)
                        if not number or not sms:
                            continue
                        key = f"{date_str}|{number}"
                        if key == last_seen_key_local:
                            break
                        if key in seen_keys_this_cycle:
                            continue
                        seen_keys_this_cycle.add(key)
                        new_messages.append({'date': date_str, 'number': number, 'sms': sms, 'cli': cli})

            if not new_messages:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
            else:
                last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                save_last_seen()
                print(f"[{site_name}] ({username}) 📨 {len(new_messages)} رسالة جديدة")

                for msg in reversed(new_messages):
                    otp_val, sms_text = extract_from_message(msg['sms'])
                    _cli = msg.get('cli', '')
                    service_name = f"{detect_service(f'{sms_text} {_cli}'.strip())}"
                    print(f"🔑 {site_name} ({username}): لقيت كود {otp_val}")

                    for retry in range(3):
                        try:
                            send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val, site_key=site_key)
                            break
                        except Exception as e:
                            if "429" in str(e):
                                wait_time = 35
                                m429 = re.search(r'after (\d+)', str(e))
                                if m429:
                                    wait_time = int(m429.group(1)) + 2
                                print(f"⚠️ Telegram 429 (Flood Control): Waiting {wait_time}s...")
                                time.sleep(wait_time)
                            else:
                                print(f"❌ Error sending: {e}")
                                break

            errors = 0
        except Exception as e:
            errors += 1
            print(f"[MBC] ({username}) ⚠️ خطأ عام: {e}")
            if errors >= 5:
                is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 16)):
            break

def sms_loop_for_api_panel(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    api_token = account.get("api_token")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())
    check_interval = SETTINGS[site_key].get("check_interval", 5)
    api_url = SETTINGS[site_key]["api_url"]
    
    sent_messages_local = set()
    sent_messages_file = f"sent_messages_{site_key}_{account_id}.json"
    
    def load_sent_messages():
        nonlocal sent_messages_local
        if os.path.exists(sent_messages_file):
            try:
                with open(sent_messages_file, 'r') as f:
                    sent_messages_local = set(json.load(f))
            except:
                sent_messages_local = set()
    
    def save_sent_messages():
        try:
            msgs = list(sent_messages_local)[-500:]
            with open(sent_messages_file, 'w') as f:
                json.dump(msgs, f)
        except:
            pass
    
    load_sent_messages()
    print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "🌐", f"بدء المراقبة عبر API... ({check_interval}s)")
    
    while not stop_event.is_set():
        try:
            params = {'token': api_token, 'records': 50}
            # For TimeSMS_API, we need date range
            if site_key == "TimeSMS_API":
                today = datetime.now()
                start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
                params['dt1'] = f'{start_date} 00:00:00'
                params['dt2'] = f'{end_date} 23:59:59'
            
            r = requests.get(api_url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'success' and data.get('data'):
                    new_messages = []
                    for msg in data['data']:
                        msg_num = msg.get('num', '')
                        msg_text = msg.get('message', '')
                        msg_date = msg.get('dt', '')
                        if not msg_num or not msg_text:
                            continue
                        msg_key = f"{msg_date}|{msg_num}|{msg_text[:50]}"
                        if msg_key not in sent_messages_local:
                            new_messages.append({'number': msg_num, 'sms': msg_text, 'date': msg_date})
                            sent_messages_local.add(msg_key)
                    
                    if new_messages:
                        print(f"[{site_name}] 📨 {len(new_messages)} رسالة جديدة")
                        save_sent_messages()
                        for msg in new_messages:
                            otp_val, sms_text = extract_from_message(msg['sms'])
                            service_name = f"{detect_service(sms_text)}"
                            send_otp_to_user(clean_number(msg['number']), sms_text, msg['number'], service_name, otp_val, site_key=site_key)
                    else:
                        print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "📭", "لا توجد أكواد جديدة")
                else:
                    print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "⚠️", "استجابة API فارغة")
            else:
                print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "❌", f"HTTP {r.status_code}")
        except Exception as e:
            print_monitoring_box(site_name, f"TOKEN: {api_token[:10]}...", "❌", f"خطأ: {str(e)[:30]}")
        
        if stop_event.wait(check_interval):
            break
    
    print(f"[{site_name}] 🛑 تم إيقاف المراقبة")

def sms_loop_for_roxy_account(site_key, account):
    site_name = SETTINGS[site_key]["name"]
    username = account.get("username")
    password = account.get("password")
    account_id = account.get("id")
    stop_event = account_stop_events.get(f"{site_key}_{account_id}", Event())
    
    scraper = cloudscraper.create_scraper()
    is_logged_in = False
    
    last_message_file = f"last_message_{site_key}_{account_id}.txt"
    last_seen_key_local = ""
    
    def load_last_seen():
        nonlocal last_seen_key_local
        if os.path.exists(last_message_file):
            try:
                with open(last_message_file, "r", encoding="utf-8") as f:
                    last_seen_key_local = f.read().strip()
            except: pass
    def save_last_seen():
        try:
            with open(last_message_file, "w", encoding="utf-8") as f:
                f.write(last_seen_key_local)
        except: pass

    print_monitoring_box(site_name, username, "🚀", "بدء المراقبة...")
    load_last_seen()
    
    login_url = "http://www.roxysms.net/signin"
    ajax_url = "http://www.roxysms.net/agent/res/data_smscdr.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://www.roxysms.net/agent/SMSCDRReports"
    }
    
    while not stop_event.is_set():
        try:
            if not is_logged_in:
                payload = {"username": username, "password": password}
                try:
                    login_resp = scraper.post(login_url, data=payload, headers=headers, timeout=30)
                    if login_resp.status_code == 200 and ("success" in login_resp.text.lower() or "logout" in login_resp.text.lower()):
                        is_logged_in = True
                        print_monitoring_box(site_name, username, "✅", "تم تسجيل الدخول بنجاح")
                    else:
                        print_monitoring_box(site_name, username, "❌", "فشل تسجيل الدخول، إعادة المحاولة...")
                        time.sleep(30)
                        continue
                except Exception as e:
                    print(f"[{site_name}] Login Error: {e}")
                    time.sleep(30)
                    continue

            today = datetime.now().strftime('%Y-%m-%d')
            params = {
                'fdate1': f'{today} 00:00:00',
                'fdate2': f'{today} 23:59:59',
                'fg': '0'
            }
            
            try:
                r = scraper.get(ajax_url, params=params, headers=headers, timeout=30)
                
                if r.status_code != 200 or 'login' in r.url.lower():
                    is_logged_in = False
                    continue

                data = r.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"[{site_name}] Connection issue, retrying: {e}")
                is_logged_in = False
                time.sleep(10)
                continue
            except Exception as e:
                print(f"[{site_name}] Request Error: {e}")
                is_logged_in = False
                time.sleep(10)
                continue
            rows = data.get('aaData', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            
            if rows:
                new_messages = []
                for row in rows:
                    if isinstance(row, list) and len(row) >= 6:
                        d_str, num, msg_txt = str(row[0]), re.sub(r'\D', '', str(row[2])), str(row[5])
                        
                        if msg_txt == "$" or len(msg_txt) < 2:
                            
                            for idx in [4, 6, 3]: 
                                if len(row) > idx:
                                    potential_msg = str(row[idx]).strip()
                                    if potential_msg and potential_msg != "$":
                                        msg_txt = potential_msg
                                        break
                        
                        key = f"{d_str}|{num}"
                        if key == last_seen_key_local: break
                        new_messages.append({'date': d_str, 'number': num, 'sms': msg_txt})
                
                if new_messages:
                    last_seen_key_local = f"{new_messages[0]['date']}|{new_messages[0]['number']}"
                    save_last_seen()
                    
                    
                    for msg in reversed(new_messages):
                        otp_val, clean_sms = extract_from_message(msg['sms'])
                        service_name = f"{detect_service(clean_sms)}"
                        formatted = format_otp_message_v2(msg['number'], clean_sms, service_name, otp_val)
                        send_otp_to_user(clean_number(msg['number']), clean_sms, msg['number'], service_name, otp_val)
                else:
                    print_monitoring_box(site_name, username, "📭", "لا توجد أكواد جديدة")
            else:
                print_monitoring_box(site_name, username, "📭", "لا توجد أكواد")
                
        except Exception as e:
            print(f"[{site_name}] Error: {e}")
            is_logged_in = False
            time.sleep(10)

        if stop_event.wait(SETTINGS[site_key].get("check_interval", 5)):
            break

if __name__ == "__main__":
    load_data()
    
    monitoring_threads = []
    print("🚀 بدء تشغيل نظام المراقبة متعدد الحسابات...")
    
    for site_key in ["GROUP", "Fly sms", "Number_Panel", "Bolt", "iVASMS", "MSI", "proton SMS", "IMS", "Roxy SMS", "Konekta_API", "TimeSMS_API", "Fire_SMS", "Hadi_SMS", "Seven1Tel", "Gaza SMS", "Km sms", "Grand SMS", "Purple SMS", "MBC", "Basha", "Flash_SMS", "Horus", "Flex", "rsayel", "ksi", "green", "grand", "Squad", "Sniper", "Lamix", "Num44", "XAP", "EMO SMS", "Pac_Call"]:
        if SETTINGS[site_key]["enabled"]:
            accounts = get_site_accounts(site_key)
            site_name = SETTINGS[site_key]["name"]
            
            if accounts:
                print(f"\n📋 {site_name}: وجدت {len(accounts)} حساب")
                for account in accounts:
                    username = account.get('username') or account.get('api_token', 'N/A')
                    thread = Thread(target=start_monitoring_for_account, args=(site_key, account), daemon=True)
                    monitoring_threads.append(thread)
                    thread.start()
                    print(f"  ✅ بدء مراقبة: {username[:15]}...")
            else:
                print(f"  ⚠️ {site_name}: لا توجد حسابات")
    
    print(f"\n🎯 إجمالي Threads النشطة: {len(monitoring_threads)}")
    
    import requests
    try:
        bot_token = BOT_TOKEN
        delete_webhook_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook?drop_pending_updates=true"
        response = requests.get(delete_webhook_url)
        print(f"🔄 تم حذف webhook وتنظيف التحديثات المعلقة: {response.json()}")
    except Exception as e:
        print(f"⚠️ خطأ في حذف webhook: {e}")
    
    print("\n✨ البوت جاهز للعمل!\n")
    
    try:
        from telebot.types import BotCommand
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("getnumber", "Get Number"),
        ]
        bot.set_my_commands(commands)
        print("✅ تم تسجيل الأوامر بنجاح!")
    except Exception as e:
        print(f"⚠️ خطأ في تسجيل الأوامر: {e}")
    
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"🚀 محاولة بدء polling (محاولة {attempt + 1}/{max_retries})...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
            break
        except Exception as e:
            if "409" in str(e) or "Conflict" in str(e):
                if attempt < max_retries - 1:
                    print(f"⚠️ تعارض polling (409) - إعادة المحاولة بعد {retry_delay} ثواني...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ فشل بدء البوت بعد {max_retries} محاولات!")
                    raise
            else:
                raise
