import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import os
import stat

# --- PAGE CONFIG ---
st.set_page_config(page_title="FB Infinite Sender", layout="centered")
st.title("Facebook Infinite Message Sender")

# --- USER INPUTS ---
# आपकी दी गई कुकी (Your specific cookie)
DEFAULT_COOKIE = "Sb=x-4VZxbqkmCAawFwsNZch1cr; m_pixel_ratio=2; ps_l=1; ps_n=1; usida=eyJ2ZXIiOjEsImlkIjoiQXNwa3poZzFqMWYwbmsiLCJ0aW1lIjoxNzM2MDIyNjM2fQ%3D%3D; oo=v1; vpd=v1%3B634x360x2; x-referer=eyJyIjoiL2NoZWNrcG9pbnQvMTUwMTA5MjgyMzUyNTI4Mi9sb2dvdXQvP25leHQ9aHR0cHMlM0ElMkYlMkZtLmZhY2Vib29rLmNvbSUyRiIsImgiOiIvY2hlY2twb2ludC8xNTAxMDkyODIzNTI1MjgyL2xvZ291dC8%2FbmV4dD1odHRwcyUzQSUyRiUyRm0uZmFjZWJvb2suY29tJTJGIiwicyI6Im0ifQ%3D%3D; pas=100018459948597%3AyY8iKAz4qS%2C61576915895165%3Ah3M07gRmIr%2C100051495735634%3AaWZGIhmpcN%2C100079959253161%3AERjtJDwIKY%2C100085135237853%3ASJzxBm80J0%2C100039111611241%3AYdPtkzDOqQ%2C61551133266466%3Aw3egO2jjPR%2C61580506865263%3AgBocX6ACyH%2C61580725287646%3Az32vfC8XFx%2C61580627947722%3NGvvqUwSjM%2C61580696818474%3AOANvC0tEZ7; locale=en_GB; c_user=61580506865263; datr=g8olaZiZYQMO7uPOZr9LIPht; xs=13%3AQoLIRrRzRReDAA%3A2%3A1764084356%3A-1%3A-1; wl_cbv=v2%3Bclient_version%3A2985%3Btimestamp%3A1764084357; fbl_st=100727294%3BT%3A29401406; fr=1DU5Jl03wP4b7GP8t.AWefU_KjBG8Z5AZgumwZsBRycYqwUkK410GOJ9ACH6HquX9_4fk.BoxuDH..AAA.0.0.BpJcqK.AWdFN0M6cD-SLsdpO8kcmDP_8_s; presence=C%7B%22lm3%22%3A%22sc.800019873203125%22%2C%22t3%22%3A%5B%7B%22o%22%3A0%2C%22i%22%3A%22g.1160300088952219%22%7D%5D%2C%22utc3%22%3A1764084412300%2C%22v%22%3A1%7D; wd=1280x2254; dpr=2"

cookie_input = st.text_area("Cookie String", value=DEFAULT_COOKIE, height=100)
target_url = st.text_input("Chat URL", value="https://www.facebook.com/messages/e2ee/t/800019873203125")
message_text = st.text_input("Message", value="Hello from Bot!")

# --- INFINITE LOOP SETTINGS ---
col1, col2 = st.columns(2)
with col1:
    enable_infinite = st.checkbox("Enable Infinite Mode (Infantry)", value=False)
with col2:
    delay_time = st.number_input("Delay (Seconds)", min_value=1, value=2)

# --- HELPER FUNCTIONS ---

def make_executable(path):
    """File ko executable banata hai (chmod +x)"""
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
        return True
    except Exception as e:
        print(f"Error setting permission: {e}")
        return False

def parse_cookies(cookie_string):
    cookies = []
    try:
        items = cookie_string.split(';')
        for item in items:
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.facebook.com'
                })
        return cookies
    except Exception:
        return []

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    
    # --- CUSTOM DRIVER PATH LOGIC ---
    # Streamlit Cloud (Linux) looks for 'chromedriver' without extension
    driver_path = "./chromedriver"
    
    if os.path.exists(driver_path):
        st.info(f"Found local driver at: {driver_path}")
        # IMPORTANT: Permission allow karna padta hai Linux par
        make_executable(driver_path)
        service = Service(executable_path=driver_path)
    else:
        st.error("Error: 'chromedriver' file not found in root directory!")
        st.stop() # Script rok do agar driver nahi mila
            
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Driver Start Error: {e}")
        return None

# --- MAIN EXECUTION ---

if st.button("Start Messaging"):
    status_box = st.empty()
    log_box = st.empty()
    
    driver = get_driver()
    
    if driver:
        try:
            status_box.text("Opening Facebook...")
            driver.get("https://www.facebook.com/")
            
            status_box.text("Setting Cookies...")
            cookies_list = parse_cookies(cookie_input)
            for cookie in cookies_list:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            status_box.text(f"Opening Chat: {target_url}")
            driver.get(target_url)
            time.sleep(10) # Initial Load Wait

            # Check Login
            if "login" in driver.current_url:
                st.error("Login Failed! Check Cookie.")
                driver.quit()
                st.stop()

            # Find Message Box
            msg_box = None
            try:
                msg_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"]')
            except:
                try:
                    msg_box = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
                except:
                    pass
            
            if msg_box:
                count = 0
                keep_running = True
                
                # --- LOOP LOGIC ---
                while keep_running:
                    try:
                        # Re-find element inside loop to avoid StaleElementReferenceException
                        # (Facebook kabhi kabhi DOM refresh karta hai)
                        try:
                            msg_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Message"]')
                        except:
                            msg_box = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')

                        msg_box.click()
                        msg_box.send_keys(message_text)
                        msg_box.send_keys(Keys.RETURN)
                        
                        count += 1
                        log_box.write(f"Messages Sent: {count} ✅")
                        
                        if not enable_infinite:
                            keep_running = False # Loop ends if infinite is OFF
                        else:
                            time.sleep(delay_time) # Wait before next message
                            
                    except Exception as loop_error:
                        st.error(f"Loop Error: {loop_error}")
                        break
                
                st.success("Task Completed.")
                
            else:
                st.error("Message Box Not Found.")
                driver.save_screenshot("error_debug.png")
                st.image("error_debug.png")

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if not enable_infinite:
                driver.quit()
                    
