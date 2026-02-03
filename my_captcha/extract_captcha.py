import easyocr
import time
import numpy as np
import cv2
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from utils.helper import show_message
    
def extract_captcha(driver:webdriver.Chrome):
    reader = easyocr.Reader(['en'])
    show_message("Locating captcha element . . . .")
    captcha_element = driver.find_element(By.CSS_SELECTOR, 'img.captcha-image-dimension')
    captcha_url = captcha_element.get_attribute('src')
    show_message(f"Captcha URL: {captcha_url}")

    script = """
        var callback = arguments[arguments.length - 1];
        var blobUrl = arguments[0];
        fetch(blobUrl).then(res => res.blob()).then(blob => {
            var reader = new FileReader();
            reader.onloadend = function() {
                callback(reader.result);
            };
            reader.readAsDataURL(blob);
        });
    """
    base64_image = driver.execute_async_script(script, captcha_url)
    base64_data = base64_image.split(",")[1]
    image_bytes = np.frombuffer(base64.b64decode(base64_data), np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

    show_message("Processing image...")
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    results = reader.readtext(thresh, detail=0, paragraph=False)
    filtered = [text.strip() for text in results if text.strip()]
    final_result = ''.join(filtered)
    show_message(f"✅ Captcha Text: {final_result}")
    return final_result
