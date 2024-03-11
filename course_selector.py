import requests
import os
import json
from lxml import etree
from urllib.parse import quote as quote_legacy

ORIGIN_URL = "http://202.195.102.53"
LOGIN_URL = f"{ORIGIN_URL}/loginN.aspx"
PROJECT_MENU_URL = f"{ORIGIN_URL}/web_xsxk/gx_ty_xkfs_xh_sql.aspx"
PROJECT_OPTIONS_MENU_URL = f"{ORIGIN_URL}/web_xsxk/xfz_xsxk_gnxz.aspx"
VIEWSTATE_XPATH = '//*[@id="__VIEWSTATE"]/@value'
VIEWSTATEGENERATOR_XPATH = '//*[@id="__VIEWSTATEGENERATOR"]/@value'
ERRMSG_XPATH = '//*[@id="lblMsg"]/text()'
USERINFO_XPATH = '//*[@id="LabXsxx"]/text()'
TABLE_LINES_XPATH_0 = '//*[@id="UpdatePanel1"]//tr'  # projects
TABLE_UNIT_XPATH_0 = '//th/text()'
TABLE_UNIT_XPATH_1 = '//td/text()'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SESSION_PATH = f"{BASE_DIR}/session.json"
ACCOUNTS_PATH = f"{BASE_DIR}/student_accounts.json"
if os.path.exists(ACCOUNTS_PATH):
    with open(ACCOUNTS_PATH) as f:
        accounts = json.load(f)
else:
    print("Missing student_accounts.json file.")
    exit(1)
if os.path.exists(SESSION_PATH):
    with open(SESSION_PATH) as f:
        session_data = json.load(f)
else:
    session_data = dict()
quote = lambda s: quote_legacy(s, safe="")
get_userpasd = lambda username: accounts.get(username)


class cczuSession:
    def __init__(self, username):
        self.userinfo = None
        self.username = username
        self.userpasd = get_userpasd(username)
        self.projects = list()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                                                   + '(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'})
        if self.load_session() and self.update_user_info():
            self.update_projects()
        else:
            if self.login():
                self.save_session()
                self.update_user_info()
                self.update_projects()
            else:
                print(f'登录失败,用户名:{self.username},密码:{self.userpasd}')


    def login(self):
        headers = {'Referer': 'http://202.195.102.53/'}
        response_html = etree.HTML(self.session.get(ORIGIN_URL).text)
        viewstate = quote(response_html.xpath(VIEWSTATE_XPATH)[0])  # url encoded
        viewstategenerator = quote(response_html.xpath(VIEWSTATEGENERATOR_XPATH)[0])  # url encoded
        payload = f"__VIEWSTATE={viewstate}&__VIEWSTATEGENERATOR={viewstategenerator}&username={self.username}&userpasd={self.userpasd}&btLogin=%E7%99%BB%E5%BD%95"
        headers = {'Referer': 'http://202.195.102.53/', 'Content-Type': 'application/x-www-form-urlencoded'}
        response_html = etree.HTML(self.session.post(LOGIN_URL, data=payload, headers=headers).text)
        if response_html.xpath(ERRMSG_XPATH):
            if response_html.xpath(ERRMSG_XPATH)[0].find("你输入的用户名称或者密码有误，请重新输入") != -1:
                print(f"{ self.username }:用户名称或者密码有误")
            return False
        else:
            return True

    def update_user_info(self):
        response_html = etree.HTML(self.session.get(PROJECT_MENU_URL).text)
        userinfo_div_list = response_html.xpath(USERINFO_XPATH)
        if userinfo_div_list:
            self.userinfo = userinfo_div_list[0]
            return True
        else:
            return False

    def save_session(self):
        global session_data
        session_data[self.username] = {"cookies": self.session.cookies.get_dict()}
        with open(SESSION_PATH, "w") as f:
            json.dump(session_data, f)
        return True

    def load_session(self):
        global session_data
        if session_data.get(self.username):
            self.session.cookies.update(session_data[self.username]["cookies"])
            return True
        else:
            return False

    def update_projects(self):
        self.projects = list()
        response_html = etree.HTML(self.session.get(PROJECT_MENU_URL).text)
        table_lines = response_html.xpath(TABLE_LINES_XPATH_0)
        if table_lines:
            # table_headers = table_lines[0].xpath(TABLE_UNIT_XPATH_0)
            # if table_headers:
            #     for table_header in table_headers[1:-1]:
            #         print(table_header, end=" | ")
            #     else:
            #         print(table_headers[-1])
            for table_line in table_lines[1:]:
                table_units = list()
                table_units_raw = table_line.xpath(TABLE_UNIT_XPATH_1)
                if table_units_raw:
                    for table_unit_raw in table_units_raw[1:]:
                        if table_unit_raw.find('\r\n') == -1:
                            table_units.append(table_unit_raw)
                    if table_units:
                        project = Project(table_units[0], table_units[1], table_units[2], table_units[3],
                                          table_units[4], table_units[5])
                        self.projects.append(project)
                        # for table_unit in table_units[:-1]:
                        #     print(table_unit, end=" | ")
                        # else:
                        #     print(table_units[-1])
            if len(self.projects):
                return True
            else:
                return False


class Project:
    def __init__(self, semester, code, name, start_date, end_date, comment):
        self.semester = semester
        self.code = code
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.comment = comment

    def __repr__(self):
        return f"<Project {self.name}({self.code})>"


if __name__ == "__main__":
    cczu_session = cczuSession("2300160429")
    print(cczu_session.userinfo)
    for project in cczu_session.projects:
        print(project)
