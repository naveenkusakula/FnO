import hashlib
import time
from urllib.parse import urlparse, parse_qs

import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from config import Config


class Auth:
    def __init__(self, config: Config):
        self.config = config

    def get_request_code(self):
        chrome_options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )

        try:
            auth_url = f"https://auth.flattrade.in/?app_key={self.config.API_KEY}"
            driver.get(auth_url)
            time.sleep(2)

            driver.find_element(By.ID, "input-19").send_keys(self.config.CLIENT_ID)
            driver.find_element(By.ID, "pwd").send_keys(self.config.PASSWORD)

            try:
                otp_button = driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'v-btn') and contains(., 'Get OTP')]",
                )
                ActionChains(driver).move_to_element(otp_button).click().perform()
                driver.find_element(By.ID, "input-49").send_keys(self.config.CLIENT_ID)
                driver.find_element(
                    By.XPATH,
                    "/html/body/div/div[3]/div/div/div[2]/form/div[2]/div/div[1]/div[1]/input",
                ).send_keys(self.config.PAN)
                send_otp_button = driver.find_element(
                    By.XPATH, "//button[.//span[text()=' Send OTP ']]"
                )
                send_otp_button.click()
            except Exception as e:
                print("Error:", e)

            user_number = int(input("Enter a OTP to continue: "))

            driver.find_element(
                By.XPATH,
                "/html/body/div/div/main/div/div/div/div/div[2]/div/div[2]/div[1]/div/form/div[3]/div/div[1]/div[1]/input",
            ).send_keys(user_number)
            sub_btn = driver.find_element(By.ID, "sbmt")
            ActionChains(driver).move_to_element(sub_btn).click().perform()
            time.sleep(4)

            redirected_url = driver.current_url
            print("Redirected URL:", redirected_url)
            parsed_url = urlparse(redirected_url)
            query_params = parse_qs(parsed_url.query)
            return query_params.get("code", [None])[0]
        finally:
            driver.quit()

    def generate_api_secret_hash(self, request_code):
        data = self.config.API_KEY + request_code + self.config.CLIENT_SECRET
        return hashlib.sha256(data.encode()).hexdigest()

    def get_api_token(self, request_code):
        api_secret_hash = self.generate_api_secret_hash(request_code)

        payload = {
            "api_key": self.config.API_KEY,
            "request_code": request_code,
            "api_secret": api_secret_hash,
        }

        response = requests.post(self.config.TOKEN_URL, json=payload)

        if response.status_code == 200:
            print("Token Response:", response.json())
            token = response.json().get("token")
            self.update_env_token(token)
            return token
        else:
            print("Error:", response.status_code, response.text)
            return None

    @staticmethod
    def update_env_token(token, env_path=".env"):
        try:
            # Try to read existing lines, or start with empty if file doesn't exist
            try:
                with open(env_path, "r") as file:
                    lines = file.readlines()
            except FileNotFoundError:
                lines = []

            token_written = False
            with open(env_path, "w") as file:
                for line in lines:
                    if line.startswith("FLATTRADE_TOKEN="):
                        file.write(f"FLATTRADE_TOKEN={token}\n")
                        token_written = True
                    else:
                        file.write(line)
                if not token_written:
                    # If token line not found, append it
                    file.write(f"FLATTRADE_TOKEN={token}\n")
        except Exception as e:
            print(f"Error updating env token: {e}")
