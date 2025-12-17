import threading
import uuid
import time
import os
import shutil
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

app = FastAPI()

# --- GLOBAL STORE ---
tasks = {}

# --- MODELS ---
class TaskInput(BaseModel):
    cookie: str
    url: str
    message: str
    delay: int = 2
    infinite: bool = False

# --- SELENIUM LOGIC ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Auto-detect paths (Linux/Cloud friendly)
    chromium_path = shutil.which("chromium") or "/usr/bin/chromium"
    chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(chromium_path) and os.path.exists(chromedriver_path):
        chrome_options.binary_location = chromium_path
        service = Service(chromedriver_path)
        try:
            return webdriver.Chrome(service=service, options=chrome_options)
        except:
            return None
    return None

def parse_cookies(cookie_string):
    cookies = []
    try:
        items = cookie_string.split(';')
        for item in items:
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({'name': name, 'value': value, 'domain': '.facebook.com'})
        return cookies
    except:
        return []

def worker_process(task_id, data: TaskInput):
    tasks[task_id]["status"] = "Initializing Driver..."
    driver = get_driver()
    
    if not driver:
        tasks[task_id]["status"] = "Failed: Driver Error"
        return

    try:
        driver.get("https://www.facebook.com/")
        cookies = parse_cookies(data.cookie)
        for c in cookies:
            try: driver.add_cookie(c)
            except: pass
            
        tasks[task_id]["status"] = "Navigating to Chat..."
        driver.get(data.url)
        time.sleep(8)
        
        # Popup Hunter
        try:
            btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue')]")
            for btn in btns: driver.execute_script("arguments[0].click();", btn)
        except: pass

        tasks[task_id]["status"] = "Running"
        
        while not tasks[task_id]["stop"]:
            # Logic to send message
            sent = False
            try:
                selectors = ['div[aria-label="Message"]', 'div[role="textbox"]']
                msg_box = None
                for s in selectors:
                    try: 
                        msg_box = driver.find_element(By.CSS_SELECTOR, s)
                        if msg_box: break
                    except: continue
                
                if msg_box:
                    driver.execute_script("arguments[0].focus();", msg_box)
                    actions = ActionChains(driver)
                    actions.send_keys(data.message)
                    actions.send_keys(Keys.RETURN)
                    actions.perform()
                    sent = True
            except:
                sent = False

            if sent:
                tasks[task_id]["count"] += 1
                tasks[task_id]["logs"].append(f"Sent Msg #{tasks[task_id]['count']}")
                if not data.infinite:
                    tasks[task_id]["status"] = "Completed"
                    break
                time.sleep(data.delay)
            else:
                time.sleep(5) # Retry delay
                
    except Exception as e:
        tasks[task_id]["status"] = f"Error: {str(e)}"
    finally:
        driver.quit()
        if tasks[task_id]["status"] == "Running":
            tasks[task_id]["status"] = "Stopped"

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "FB Sender API is Running 🚀"}

@app.post("/start_task")
def start_task(data: TaskInput, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "Starting",
        "count": 0,
        "logs": [],
        "stop": False
    }
    # Run in background
    background_tasks.add_task(worker_process, task_id, data)
    return {"task_id": task_id, "message": "Task Started"}

@app.get("/status/{task_id}")
def get_status(task_id: str):
    return tasks.get(task_id, {"error": "Task ID not found"})

@app.post("/stop/{task_id}")
def stop_task(task_id: str):
    if task_id in tasks:
        tasks[task_id]["stop"] = True
        return {"message": "Stop signal sent"}
    return {"error": "Invalid ID"}
