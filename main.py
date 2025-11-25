from flask import Flask, render_template_string, request, Response, stream_with_context
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import logging

# Flask App Setup
app = Flask(__name__)

# Logger ko shant karne ke liye
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- SINGLE FILE HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB Auto Sender (Headless)</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; padding: 20px; }
        .main-box { max-width: 700px; margin: 0 auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #4267B2; margin-bottom: 20px; }
        
        .form-group { margin-bottom: 15px; }
        label { font-weight: 600; display: block; margin-bottom: 5px; color: #333; }
        input[type="text"], input[type="number"], textarea {
            width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-size: 14px;
        }
        textarea { resize: vertical; }
        
        button {
            width: 100%; padding: 12px; background-color: #4267B2; color: white; border: none; 
            border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s;
        }
        button:hover { background-color: #365899; }
        button:disabled { background-color: #9cb4d8; cursor: not-allowed; }

        .log-box {
            margin-top: 25px; background: #1e1e1e; color: #00ff00; padding: 15px; 
            height: 300px; overflow-y: auto; border-radius: 5px; font-family: monospace; font-size: 13px;
            border: 2px solid #333;
        }
        .log-line { margin-bottom: 4px; border-bottom: 1px solid #333; padding-bottom: 2px; }
        .error { color: #ff4444; }
        .info { color: #00ccff; }
    </style>
</head>
<body>

<div class="main-box">
    <h2>📨 Facebook Auto Sender (No-GUI)</h2>
    
    <form id="autoForm">
        <div class="form-group">
            <label>🍪 Paste Cookies (JSON Format)</label>
            <textarea name="cookies" rows="4" placeholder='[{"domain": ".facebook.com", ...}]' required></textarea>
        </div>

        <div class="form-group">
            <label>🔗 Chat Link (Messenger URL)</label>
            <input type="text" name="url" placeholder="https://www.facebook.com/messages/t/1000xxxx" required>
        </div>

        <div class="form-group">
            <label>💬 Messages (Ek line me ek message)</label>
            <textarea name="messages" rows="5" placeholder="Hello bro&#10;Kaisa hai?&#10;Call me" required></textarea>
        </div>

        <div class="form-group">
            <label>⏱ Delay (Seconds)</label>
            <input type="number" name="delay" value="5" min="1" required>
        </div>

        <button type="submit" id="btnStart">🚀 Start Sending</button>
    </form>

    <div class="log-box" id="logs">
        <div class="log-line">Waiting to start...</div>
    </div>
</div>

<script>
    const form = document.getElementById('autoForm');
    const logsDiv = document.getElementById('logs');
    const btn = document.getElementById('btnStart');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI Reset
        btn.disabled = true;
        btn.innerText = "Running Background Task...";
        logsDiv.innerHTML = "<div class='log-line info'>System initialized...</div>";

        const formData = new FormData(form);

        try {
            const response = await fetch('/run_bot', {
                method: 'POST',
                body: formData
            });

            // Reading Stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                // Split lines incase multiple logs come together
                const lines = chunk.split("\\n"); 
                
                lines.forEach(line => {
                    if(line.trim() !== "") {
                        const div = document.createElement('div');
                        div.className = 'log-line';
                        
                        if(line.includes("Error") || line.includes("Failed")) div.classList.add('error');
                        else if(line.includes("Success") || line.includes("Sent")) div.classList.add('info');
                        
                        div.innerText = line;
                        logsDiv.appendChild(div);
                        logsDiv.scrollTop = logsDiv.scrollHeight; // Auto Scroll
                    }
                });
            }

        } catch (err) {
            logsDiv.innerHTML += `<div class='log-line error'>❌ Network Error: ${err.message}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerText = "🚀 Start Sending";
            logsDiv.innerHTML += "<div class='log-line'>🛑 Process Finished.</div>";
        }
    });
</script>

</body>
</html>
"""

# --- SELENIUM BOT LOGIC ---
def get_headless_driver():
    chrome_options = Options()
    
    # Ye settings Chrome ko bina open kiye chalayengi (Headless)
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    
    # User agent change karna zaruri hai taki FB bot detect na kare
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    # Driver Manager automatically driver download karega
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/run_bot', methods=['POST'])
def run_bot():
    cookies_raw = request.form.get('cookies')
    chat_url = request.form.get('url')
    msgs_raw = request.form.get('messages')
    delay = int(request.form.get('delay'))

    def generate_updates():
        driver = None
        try:
            yield "⚙️ Launching Invisible Chrome Driver...\n"
            driver = get_headless_driver()
            
            yield "🌍 Opening Facebook Login Page...\n"
            driver.get("https://www.facebook.com/")
            time.sleep(2)

            # --- Cookie Logic ---
            try:
                yield "🍪 Injecting Cookies...\n"
                cookies = json.loads(cookies_raw)
                for ck in cookies:
                    # SameSite error fix karne ke liye
                    if 'sameSite' in ck: del ck['sameSite'] 
                    ck["domain"] = ".facebook.com"
                    try:
                        driver.add_cookie(ck)
                    except:
                        pass
                
                yield "🔄 Refreshing Session...\n"
                driver.refresh()
                time.sleep(4)
            except Exception as e:
                yield f"❌ Cookie Error: JSON format check karo. ({str(e)})\n"
                return

            # --- Chat Navigation ---
            yield f"🔗 Going to Chat: {chat_url}\n"
            driver.get(chat_url)
            time.sleep(6)

            # Check karo login hua ya nahi
            if "login" in driver.current_url:
                yield "❌ Error: Cookies expire ho gayi hain ya login fail hua.\n"
                return

            msg_list = msgs_raw.split('\n')
            yield f"✅ Ready to send {len(msg_list)} messages.\n"

            for i, msg in enumerate(msg_list):
                msg = msg.strip()
                if not msg: continue
                
                try:
                    # Message Box dhoondhna (XPath for generic FB Messenger)
                    # Ye XPath flexible hai jo 'paragraph' ya 'textbox' role dhoondta hai
                    text_box = driver.find_element(By.XPATH, "//div[@role='textbox'] | //div[@aria-label='Message'] | //p[contains(@class, 'notranslate')]")
                    
                    text_box.click()
                    text_box.send_keys(msg)
                    time.sleep(1)
                    
                    # Enter press karna
                    text_box.send_keys("\ue007") 
                    
                    yield f"🟢 [{i+1}] Sent: {msg}\n"
                    time.sleep(delay)
                    
                except Exception as e:
                    yield f"⚠️ Failed to send '{msg}': {str(e)}\n"
                    # Agar element nahi mila to retry ke liye thoda wait
                    time.sleep(2)

            yield "🎉 All messages processed successfully!\n"

        except Exception as e:
            yield f"❌ Critical Error: {str(e)}\n"
        finally:
            if driver:
                driver.quit()
                yield "🛑 Driver Closed.\n"

    return Response(stream_with_context(generate_updates()), mimetype='text/plain')

if __name__ == '__main__':
    # Browser automatically nahi khulega, manually link open karein
    print("--------------------------------------------------")
    print("Server Started! Open this link in your browser:")
    print("http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', port=5000, debug=False)
