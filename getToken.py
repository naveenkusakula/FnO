import hashlib
import time
from urllib.parse import urlparse, parse_qs

import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from config import FlattradeConfig


class FlattradeAuth:
    def __init__(self, config: FlattradeConfig):
        self.config = config

    def get_request_code(self):
        chrome_options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        try:
            auth_url = f"https://auth.flattrade.in/?app_key={self.config.API_KEY}"
            driver.get(auth_url)
            time.sleep(2)

            driver.find_element(By.ID, "input-19").send_keys(self.config.CLIENT_ID)
            driver.find_element(By.ID, "pwd").send_keys(self.config.PASSWORD)
            
            try:
                otp_button = driver.find_element(By.XPATH, "//button[contains(@class, 'v-btn') and contains(., 'Get OTP')]")
                ActionChains(driver).move_to_element(otp_button).click().perform()
                driver.find_element(By.ID, "input-48").send_keys(self.config.CLIENT_ID)
                driver.find_element(By.XPATH, "/html/body/div/div[3]/div/div/div[2]/form/div[2]/div/div[1]/div[1]/input").send_keys(self.config.PAN)
                send_otp_button = driver.find_element(By.XPATH, "//button[.//span[text()=' Send OTP ']]")
                send_otp_button.click()
            except Exception as e:
                print("Error:", e)

            user_number = int(input("Enter a OTP to continue: "))

            driver.find_element(By.XPATH, "/html/body/div/div/main/div/div/div/div/div[2]/div/div[2]/div[1]/div/form/div[3]/div/div[1]/div[1]/input").send_keys(user_number)
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
            "api_secret": api_secret_hash
        }

        response = requests.post(self.config.TOKEN_URL, json=payload)

        if response.status_code == 200:
            print("Token Response:", response.json())
            return response.json().get("token")
        else:
            print("Error:", response.status_code, response.text)
            return None


class FlattradeAPI:
    def __init__(self, config: FlattradeConfig, auth_token: str):
        self.config = config
        self.auth_token = auth_token

    def get_positions(self):
        """
        Fetches current positions from Flattrade using the provided auth token.
        """
        payload = f"jData={{\n\t\"uid\": \"{self.config.CLIENT_ID}\",\n\t\"actid\": \"{self.config.CLIENT_ID}\"\n}}&jKey={self.auth_token}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.0.1"
        }

        response = requests.request("POST", self.config.POSITIONS_URL, data=payload, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching positions: {response.status_code}, {response.text}")
            return None


def main():
    config = FlattradeConfig()
    
    # Validate that all required environment variables are set
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure all required environment variables are set in your .env file")
        return
    
    if config.FINAL_TOKEN:
        final_token = config.FINAL_TOKEN
        print("Using existing token:", final_token)
    else:
        auth = FlattradeAuth(config)
        request_code = auth.get_request_code()
        print("Authorization Code:", request_code)
        final_token = auth.get_api_token(request_code)
        print("Final Token:", final_token)
    
    # Get positions using the token
    api = FlattradeAPI(config, final_token)
    positions = api.get_positions()
    
    if positions:
        print("Current Positions:", positions)
    else:
        print("Failed to fetch positions.")


if __name__ == "__main__":
    main()