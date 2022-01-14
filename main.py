from tkinter.messagebox import NO
from selenium import webdriver
from tempfile import mkdtemp
import time
import json
import os
from selenium.webdriver.support.ui import Select
# from chromeless import Chromeless


def get_chrome():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--lang=ja")
    prefs = {
        'profile.default_content_setting_values':
        {
            'geolocation': 1
        },

        'profile.managed_default_content_settings':
        {
            'geolocation': 1
        },
    }
    options.add_experimental_option('prefs', prefs)
    if os.path.exists("/opt/chromedriver"):
        # docker
        options.binary_location = "/opt/chrome/chrome"
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")
        chromedriver_path = "/opt/chromedriver"
    else:
        # local
        from webdriver_manager.chrome import ChromeDriverManager
        chromedriver_path = ChromeDriverManager().install()
    chrome = Chrome(chromedriver_path, options=options)
    # chrome = Chromeless(chrome_options=options)
    return chrome


def get_todays_yyyy_mm_dd():
    return time.strftime('%Y-%m-%d')


class Chrome(webdriver.Chrome):
    def find_element_by_xpath(self, xpath):
        for i in range(999):
            time.sleep(1)
            try:
                return super().find_element_by_xpath(xpath)
            except Exception:
                if i > 10:
                    raise Exception(f"Element not found: {xpath}")

    def open_todays_detail(chrome):
        url = "https://atnd.ak4.jp/attendance/"
        yyyy_mm_dd = get_todays_yyyy_mm_dd()
        print('open_todays_detail', yyyy_mm_dd)
        chrome.login(url)
        chrome.find_element_by_xpath(
            f"//a[contains(@href, '/requests/new?date={yyyy_mm_dd}') and contains(text(), '申請')]").click()
        if chrome.find_element_by_xpath("//input[@data-request-apply-date-input]").get_attribute("value") != time.strftime('%Y/%m/%d'):
            # スクロールが変で１つズレた申請ボタンを押すことがあるため再トライ
            chrome.find_element_by_xpath(
                f"//div[@class='modal__close js-modal-close' and ./following-sibling::h1[text()='申請']]").click()
            chrome.find_element_by_xpath(
                f"//a[contains(@href, '/requests/new?date={yyyy_mm_dd}') and contains(text(), '申請')]").click()

    def extra_operation_if_office(chrome):
        chrome.open_todays_detail()
        select = Select(chrome.find_element_by_xpath(
            "//select[@id='form_operations_']"))
        select.select_by_visible_text(os.environ["EXTRA_OPERATION_SELECT"])
        chrome.find_element_by_xpath(
            "//textarea[@id='form_request_attributes_staff_comment']").send_keys(os.environ["EXTRA_OPERATION_TEXT"])
        chrome.find_element_by_xpath(
            '//input[@value="確定" and @type="submit"]').click()

    def get_morning_gps(chrome):
        chrome.open_todays_detail()
        google_map_link = chrome.find_element_by_xpath(
            "//a[contains(@href, 'https://www.google.co.jp/maps') and text()='GPS']")
        latitude, longitude = map(float, google_map_link.get_attribute('href').split("q=")[
            1].split(","))
        print(latitude, longitude)
        return latitude, longitude

    def login(chrome, url=None):
        chrome.get("https://atnd.ak4.jp/login" if url is None else url)
        chrome.find_element_by_xpath("//html")  # wait loading
        if not chrome.current_url.startswith("https://atnd.ak4.jp/login"):
            return  # already logged in
        elm_ids_with_cred_envs = {
            'form_password': 'AKASHI_PASSWORD',
            'form_login_id': 'AKASHI_EMPLOYEE_ID',
            'form_company_id': 'AKASHI_COMPANY_ID',
        }
        for elm_id, env_name in elm_ids_with_cred_envs.items():
            elm = chrome.find_element_by_xpath(f"//input[@id='{elm_id}']")
            elm.send_keys(os.environ[env_name])
        chrome.find_element_by_xpath(
            '//input[@value="ログイン" and @type="submit"]').click()

    def punch(chrome, action, geo=None):
        if geo:
            chrome.execute_cdp_cmd("Page.setGeolocationOverride", {
                "latitude": float(geo[0]), "longitude": float(geo[1]), "accuracy": 0.0001})
        chrome.login("https://atnd.ak4.jp/sp/mypage/punch")
        chrome.find_element_by_xpath(
            f'//button[@data-name="{action}" and @type="submit"]').click()
        chrome.find_element_by_xpath(
            '//p[text()="本当に打刻しますか？"]/following-sibling::button[text()="OK"]').click()

    def did_work_today(chrome):
        url = "https://atnd.ak4.jp/attendance/"
        chrome.login(url)
        elm = chrome.find_element_by_xpath(
            f"//tr[@id='working_report_{time.strftime('%Y%m%d')}']/td[@data-key='result_start_time']//span")
        return False if elm.text == "--:--" else True


def handler(event=None, context=None, chrome=None):
    chrome = chrome if chrome is not None else get_chrome()
    if 'location' not in event:
        if not chrome.did_work_today():
            return "ok"
        action = "退勤"
        geo = chrome.get_morning_gps()
    else:
        action = "出勤"
        location = event['location']
        geo = {
            'office': (os.environ['OFFICE_LATITUDE'], os.environ['OFFICE_LONGITUDE']),
            'home': (os.environ['HOME_LATITUDE'], os.environ['HOME_LONGITUDE']),
        }[location]
    chrome.punch(action=action, geo=geo)
    return "ok"


if __name__ == '__main__':
    try:
        chrome = get_chrome()
        print(handler(event={
            # 'location': 'home',
            # 'location': 'office',
        }, chrome=chrome))
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        time.sleep(5)
        chrome.quit()
