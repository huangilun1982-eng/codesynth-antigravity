import sqlite3
import time
import sys
import traceback
import os
import json
import shutil
import subprocess
import google.generativeai as genai
import pygetwindow as gw
import pyautogui
from PIL import Image

# ==========================================
# 0. 設定與工具
# ==========================================
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return None

app_config = load_config()
GOOGLE_API_KEY = app_config.get("GOOGLE_API_KEY", "") if app_config else ""
CURRENT_MODEL_NAME = app_config.get("MODEL_NAME", "gemini-1.5-flash") if app_config else "gemini-1.5-flash"

def set_ai_model(model_name):
    global CURRENT_MODEL_NAME
    CURRENT_MODEL_NAME = model_name
    print(f"[System] AI Model switched to: {CURRENT_MODEL_NAME}")

def get_available_models():
    if not GOOGLE_API_KEY: return ["gemini-1.5-flash (No Key)"]
    genai.configure(api_key=GOOGLE_API_KEY)
    models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                models.append(name)
    except: return ["gemini-1.5-flash", "gemini-1.5-pro"]
    
    priority = ["gemini-1.5-flash", "gemini-1.5-pro"]
    sorted_models = []
    for p in priority:
        for m in models:
            if p in m and "latest" in m: sorted_models.append(m)
    for m in models:
        if m not in sorted_models: sorted_models.append(m)
    return sorted_models if sorted_models else ["gemini-1.5-flash"]

# ==========================================
# 1. 資料庫模組
# ==========================================
def init_project_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS components
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, version TEXT, code TEXT, description TEXT, created_at TIMESTAMP)''')
    c.execute("SELECT count(*) FROM components")
    if c.fetchone()[0] == 0:
        initial_data = [("Main", "v1", "print('Hello CodeSynth!')", "專案入口", time.time())]
        c.executemany("INSERT INTO components (name, version, code, description, created_at) VALUES (?,?,?,?,?)", initial_data)
        conn.commit()
    conn.close()

def get_component_names(db_path):
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("SELECT DISTINCT name FROM components ORDER BY name")
    names = [r[0] for r in c.fetchall()]; conn.close(); return names

def get_versions(db_path, comp_name):
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("SELECT version, description FROM components WHERE name=? ORDER BY created_at DESC", (comp_name,))
    return c.fetchall()

def get_component_code(db_path, name, version):
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("SELECT code FROM components WHERE name=? AND version=?", (name, version))
    res = c.fetchone(); conn.close(); return res[0] if res else None

def save_new_version(db_path, name, new_version, code, desc):
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("INSERT INTO components (name, version, code, description, created_at) VALUES (?,?,?,?,?)", 
              (name, new_version, code, desc, time.time())); conn.commit(); conn.close()

def generate_history_report(db_path):
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("SELECT name, version, description, created_at FROM components ORDER BY created_at DESC")
    records = c.fetchall(); conn.close()
    report = f"# 專案歷程\nDB: {db_path}\n" + "="*50 + "\n"
    for n, v, d, t in records: report += f"● {time.strftime('%Y-%m-%d %H:%M', time.localtime(t))} - {n}({v}): {d}\n"
    return report

# ==========================================
# 2. AI 核心 (v11.0: 專案經理邏輯)
# ==========================================
def ask_gemini_to_plan_task(db_path, user_instruction):
    """
    (v11.0 新增) 讀取專案結構，判斷使用者的指令應該針對哪個檔案，或是需要重構
    """
    if not GOOGLE_API_KEY: return {"type": "ERROR", "reason": "No API Key"}
    
    # 1. 取得所有檔案清單與描述 (不讀完整代碼，省 Token)
    conn = sqlite3.connect(db_path); c = conn.cursor()
    c.execute("SELECT DISTINCT name FROM components")
    names = [r[0] for r in c.fetchall()]
    
    file_list_str = ""
    for name in names:
        versions = get_versions(db_path, name)
        desc = versions[0][1] if versions else "無描述"
        file_list_str += f"- {name}: {desc}\n"
    conn.close()

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    
    prompt = f"""
    你是一個 Python 專案經理。
    
    【當前專案檔案列表】
    {file_list_str}

    【使用者指令】
    "{user_instruction}"

    【任務】
    請分析使用者的指令，判斷應該執行什麼操作。
    
    回傳 JSON 格式 (不要 Markdown):
    {{
        "type": "EDIT" (修改現有檔案) 或 "REFACTOR" (涉及新增/刪除/拆分檔案) 或 "CHAT" (閒聊或無法執行),
        "target_file": "檔案名稱 (如果是 EDIT)",
        "reason": "用繁體中文解釋你的判斷邏輯 (這段話會顯示給使用者看)"
    }}
    """
    try:
        res = model.generate_content(prompt)
        text = res.text.strip()
        if "```json" in text: text = text.replace("```json", "").replace("```", "").strip()
        if "{" in text: text = text[text.find("{"):text.rfind("}")+1]
        return json.loads(text)
    except Exception as e:
        return {"type": "ERROR", "reason": f"規劃失敗: {str(e)}"}

def ask_gemini_to_edit(current_code, user_instruction):
    if not GOOGLE_API_KEY: return (False, "API Key Missing")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    prompt = f"Code:\n```python\n{current_code}\n```\nInstr:{user_instruction}\nTask:Return modified python code only."
    try:
        res = model.generate_content(prompt); text = res.text.strip()
        if "```python" in text: return (True, text.split("```python")[1].split("```")[0].strip())
        return (False, text)
    except Exception as e: return (False, str(e))

def ask_gemini_to_refactor(db_path, instruction):
    if not GOOGLE_API_KEY: return (False, "API Key Missing")
    all_code = ""
    for n in get_component_names(db_path):
        vs = get_versions(db_path, n)
        if vs: all_code += f"--- FILE: {n} ---\n{get_component_code(db_path, n, vs[0][0])}\n\n"
    
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    prompt = f"Project:\n{all_code}\nInstr:{instruction}\nTask:Refactor. Return JSON list: [{{'name':'...', 'code':'...', 'desc':'...'}}]"
    try:
        res = model.generate_content(prompt); text = res.text.strip()
        if "```json" in text: text = text.replace("```json", "").replace("```", "").strip()
        if "[" in text: text = text[text.find("["):text.rfind("]")+1]
        return (True, json.loads(text))
    except Exception as e: return (False, str(e))

def ask_gemini_to_init_project(goal):
    if not GOOGLE_API_KEY: return None
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    prompt = f"Goal:\"{goal}\". Return JSON list: [{{'name':'Main', 'code':'...', 'desc':'...'}}]"
    try:
        res = model.generate_content(prompt); text = res.text.strip()
        if "```json" in text: text = text.replace("```json", "").replace("```", "").strip()
        if "[" in text: text = text[text.find("["):text.rfind("]")+1]
        return json.loads(text)
    except: return None

def capture_error_scene(project_dir):
    s_dir = os.path.join(project_dir, "screenshots")
    if not os.path.exists(s_dir): os.makedirs(s_dir)
    time.sleep(1)
    try:
        aw = gw.getActiveWindow()
        if aw and aw.size[0]>0:
            img = pyautogui.screenshot(region=(aw.topleft[0], aw.topleft[1], aw.size[0], aw.size[1]))
            img.thumbnail((1024,1024)); fn = os.path.join(s_dir, f"crash_{int(time.time())}.png"); img.save(fn)
            return fn, aw.title
    except: pass
    return None, None

def ask_gemini_to_fix(image_path, error_log, current_bad_code):
    if not GOOGLE_API_KEY: return None
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    f = genai.upload_file(path=image_path)
    while f.state.name == "PROCESSING": time.sleep(1); f = genai.get_file(f.name)
    prompt = f"Log:{error_log}\nCode:\n```python\n{current_bad_code}\n```\nFix code. Return pure python."
    try: return model.generate_content([f, prompt]).text.replace("```python", "").replace("```", "").strip()
    except: return None

def ask_gemini_to_diagnose_system_crash(tb):
    if not GOOGLE_API_KEY: return "No API Key"
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(CURRENT_MODEL_NAME)
    return model.generate_content(f"Crash Traceback:\n{tb}\nExplain simply in Traditional Chinese.").text

# ==========================================
# 3. 執行引擎
# ==========================================
def run_assembly(db_path, selection):
    t_dir = os.path.join(os.path.dirname(db_path), "_sim_temp")
    if os.path.exists(t_dir): 
        try: shutil.rmtree(t_dir)
        except: pass
    os.makedirs(t_dir)
    
    m_script = None; bad_code = ""
    for n, v in selection.items():
        code = get_component_code(db_path, n, v)
        if not code: return False, f"缺件: {n}-{v}", None
        fn = "main.py" if n.lower()=="main" else (n if n.endswith(".py") else f"{n}.py")
        if n.lower()=="main": m_script=fn
        with open(os.path.join(t_dir, fn), "w", encoding="utf-8") as f: f.write(code)
        if n!="Main": bad_code = code
    
    if not m_script: return False, "No Main", None
    
    try:
        p = subprocess.Popen([sys.executable, m_script], cwd=t_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(timeout=10)
        if p.returncode == 0: return True, out, None
        else: return False, f"Exit Code {p.returncode}:\n{err}\n{out}", bad_code
    except Exception as e: return False, str(e), bad_code

def export_files(db_path, folder, selection):
    if not os.path.exists(folder): os.makedirs(folder)
    cnt = 0
    for n, v in selection.items():
        c = get_component_code(db_path, n, v)
        if c:
            fn = n if n.endswith(".py") else f"{n}.py"
            with open(os.path.join(folder, fn), "w", encoding="utf-8") as f: f.write(c)
            cnt+=1
    return f"已匯出 {cnt} 檔"
