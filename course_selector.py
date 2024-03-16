import requests
import os
import json
import re
import html
import pyquery
from lxml import etree

ORIGIN_URL = "http://202.195.102.53"
LOGIN_URL = f"{ORIGIN_URL}/loginN.aspx"
INDEX_URL = f"{ORIGIN_URL}/web_xsxk/gx_ty_xkfs_xh_sql.aspx"
# TEST_URL = f"{ORIGIN_URL}/web_xsxk/xfz_xsxk_gnxz.aspx?dm=0003-004"
TEST_URL = f"{ORIGIN_URL}/web_xsxk/xfz_xsxk_fs3_kzyxk.aspx"
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


def extract_html_info(html_text):
    def extract_args(*args):
        return args

    html_info = dict()
    init_info = eval(f"extract_args({regex_locator['init_args'].findall(html_text)[0]})")
    # init_info example: ('ScriptManager1', 'form1',
    # ['tControl_kbk_kcxz1$UpdatePanel1', '', 'tControl_kbk_kcxz1$UpdatePanel2', '',
    # 'tControl_kbk_kcxz1$UpdatePanel3', '', 'tControl_kbk_kcxz1$UpdatePanel4', '', 'tControl_kbk_kcxz1$UpdatePanel5',
    # '', 'tControl_kbk_kcxz1$UpdatePanel6', '', 'tUpdatePanel1', '', 'tUpdatePanel7', ''], [], [], 90, '')
    pq = pyquery.PyQuery(html_text)
    form_id = init_info[1]
    html_info['sm'] = init_info[0]  # ScriptManager Name
    html_info['div_html'] = dict()
    for msg in list(filter(lambda x: x, init_info[2])):
        div_id = msg.lstrip("t").replace('$', '_')
        html_info['div_html'][msg.lstrip("t")] = pq(f"#{div_id}").html()
    post_payload = dict()
    post_payload['__VIEWSTATE'] = pq(f"#{form_id} #__VIEWSTATE").attr("value")
    post_payload['__VIEWSTATEGENERATOR'] = pq(f"#{form_id} #__VIEWSTATEGENERATOR").attr("value")
    vse = pq(f"#{form_id} #__VIEWSTATEENCRYPTED")
    if vse:
        post_payload['__VIEWSTATEENCRYPTED'] = vse.attr("value")
    lsf = pq(f"#{form_id} #__LASTFOCUS")
    if lsf:
        post_payload['__LASTFOCUS'] = lsf.attr("value")
    post_payload['__ASYNCPOST'] = "true"
    html_info['post_payload'] = post_payload
    return html_info


def get_script_manager_param(html_info, target_html):
    sm_params = list()
    html_length = list()
    target_html = html.unescape(target_html.strip())
    for k, v in html_info['div_html'].items():
        if target_html in v:
            sm_params.append(k)
            html_length.append(len(v))
    if len(sm_params) == 1:
        return sm_params[0]
    else:
        return sm_params[html_length.index(min(html_length))]


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
        payload = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            'username': self.username,
            'userpasd': self.userpasd,
            'btLogin': '登录'
            }
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
        html_info = extract_html_info(response_html)
        project_lines = [html.unescape(x) for x in regex_locator["project_line_dta"].findall(response_html)]
        if project_lines:
            for line in project_lines:
                project_info = regex_locator["project_info"].findall(line)[0][2:]
                project = Project(*project_info, line, html_info)
                project.click_event(self.session)
                if not project.has_tab_info():
                    print(f"Failed to fetch tab info for {project}")
                self.projects.append(project)
            return True
        else:
            return False

    def test(self):
        response_html = self.session.get(TEST_URL).text
        html_info = extract_html_info(response_html)
        # PyQuery failed to locate the tr.dg1-item, so I use regex to locate it.
        dg1_item = regex_locator["dg1_item_dta"].findall(response_html)
        print(get_script_manager_param(html_info, dg1_item[0]))


class Control:
    def __init__(self, control_html, form_url, html_info):
        self.form_url = form_url
        target_args = regex_locator['target_args'].findall(control_html)[0]
        self.target = target_args[0]
        self.argument = target_args[1]
        sm_param = get_script_manager_param(html_info, control_html)
        self.payload = {
            html_info['sm']: f"{sm_param}|{self.target}",
            '__EVENTTARGET': self.target,
            '__EVENTARGUMENT': self.argument,
            }
        self.payload.update(html_info['post_payload'])
        self.html_info = html_info
        self.tab_url = None
        self.tab_name = None

    def __repr__(self):
        return f"<Control {self.target}|{self.argument}>"

    def click_event(self, session):
        response_html = session.post(self.form_url, data=self.payload).text
        new_tab_info = regex_locator["new_tab_info"].findall(response_html)
        course_selection_result = regex_locator["course_selection_result"].findall(response_html)
        if new_tab_info:
            new_tab_info = new_tab_info[0]
            self.tab_url = ORIGIN_URL + new_tab_info[0][2:]
            self.tab_name = new_tab_info[2]
            return None
        elif course_selection_result:
            return course_selection_result[0]

    def has_tab_info(self):
        return self.tab_url and self.tab_name


class Project(Control):
    def __init__(self, semester, code, name, start_date, end_date, comment, control_html, html_info):
        super().__init__(control_html, INDEX_URL, html_info)
        self.semester = semester
        self.code = code
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.comment = comment

    def __repr__(self):
        return f"<Project {self.name}({self.code})>"


if __name__ == "__main__":
    cczu_session = cczuSession("2300160426")
    print(cczu_session.userinfo)
    for project in cczu_session.projects:
        print(project, project.tab_name, project.tab_url)
