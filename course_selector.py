import requests
import os
import json
import re
import html

ORIGIN_URL = "http://202.195.102.53"
LOGIN_URL = f"{ORIGIN_URL}/loginN.aspx"
INDEX_URL = f"{ORIGIN_URL}/web_xsxk/gx_ty_xkfs_xh_sql.aspx"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REGEX_LOCATOR_PATH = f"{BASE_DIR}/regex_locator.json"
SESSION_PATH = f"{BASE_DIR}/session.json"
ACCOUNTS_PATH = f"{BASE_DIR}/student_accounts.json"
if os.path.exists(ACCOUNTS_PATH):
    with open(ACCOUNTS_PATH) as f:
        accounts = json.load(f)
else:
    print("Missing student_accounts.json file.")
    exit(1)
if os.path.exists(REGEX_LOCATOR_PATH):
    with open(REGEX_LOCATOR_PATH) as f:
        regex_locator = json.load(f)
    for k, v in regex_locator.items():
        if k[-3:] == 'dta':
            regex_locator[k] = re.compile(v, re.DOTALL)
        else:
            regex_locator[k] = re.compile(v)
else:
    print("Missing regex_locator.json file.")
    exit(1)
if os.path.exists(SESSION_PATH):
    with open(SESSION_PATH) as f:
        session_data = json.load(f)
else:
    session_data = dict()
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
        response_html = self.session.get(ORIGIN_URL).text
        viewstate = regex_locator["viewstate"].findall(response_html)[0]  # url encoded
        viewstategenerator = regex_locator["viewstategenerator"].findall(response_html)[0]  # url encoded
        payload = {'__VIEWSTATE': viewstate,
                   '__VIEWSTATEGENERATOR': viewstategenerator,
                   'username': self.username,
                   'userpasd': self.userpasd,
                   'btLogin': '登录'}
        headers = {'Referer': 'http://202.195.102.53/', 'Content-Type': 'application/x-www-form-urlencoded'}
        response_html = self.session.post(LOGIN_URL, data=payload, headers=headers).text
        err_msg = regex_locator["err_msg"].findall(response_html)
        if err_msg:
            if err_msg[0].find("你输入的用户名称或者密码有误，请重新输入") != -1:
                print(f"{self.username}:用户名称或者密码有误")
            return False
        else:
            return True

    def update_user_info(self):
        response_html = self.session.get(INDEX_URL).text
        user_info = regex_locator["user_info"].findall(response_html)
        if user_info:
            self.userinfo = user_info[0]
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
        response_html = self.session.get(INDEX_URL).text
        viewstate = regex_locator["viewstate"].findall(response_html)[0]
        viewstategenerator = regex_locator["viewstategenerator"].findall(response_html)[0]
        viewstateencrypted = regex_locator["viewstateencrypted"].findall(response_html)[0]
        project_lines = [html.unescape(x) for x in regex_locator["project_line_dta"].findall(response_html)]
        if project_lines:
            for line in project_lines:
                project = Project(*regex_locator["project_info"].findall(line)[0], viewstate,
                                  viewstategenerator, viewstateencrypted)
                if not project.fetch_tab_info(self.session):
                    print(f"Failed to fetch tab info for {project}")
                self.projects.append(project)
            return True
        else:
            return False


class Project:
    def __init__(self, target, argument, semester, code, name, start_date, end_date, comment,
                 viewstate, viewstategenerator, viewstateencrypted=''):
        self.target = target
        self.argument = argument
        self.viewstate = viewstate
        self.viewstategenerator = viewstategenerator
        self.viewstateencrypted = viewstateencrypted
        self.semester = semester
        self.code = code
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.comment = comment
        self.tab_url = None
        self.tab_name = None

    def __repr__(self):
        return f"<Project {self.name}({self.code})>"

    def fetch_tab_info(self, session):
        payload = {'ScriptManager1': 'UpdatePanel1|' + self.target,
                    '__EVENTTARGET': self.target,
                    '__EVENTARGUMENT': self.argument,
                    '__VIEWSTATE': self.viewstate,
                    '__VIEWSTATEGENERATOR': self.viewstategenerator,
                    '__VIEWSTATEENCRYPTED': self.viewstateencrypted,
                    '__ASYNCPOST': 'true'}
        response_html = session.post(INDEX_URL, data=payload).text
        new_tab_info = regex_locator["new_tab_info"].findall(response_html)
        if new_tab_info:
            new_tab_info = new_tab_info[0]  # (tab_url,tab_code,tab_name)
            self.tab_url = ORIGIN_URL + new_tab_info[0][2:]
            self.tab_name = new_tab_info[2]
            return True
        else:
            return False


if __name__ == "__main__":
    cczu_session = cczuSession("2300160429")
    print(cczu_session.userinfo)
    for project in cczu_session.projects:
        print(project, project.tab_name, project.tab_url)
