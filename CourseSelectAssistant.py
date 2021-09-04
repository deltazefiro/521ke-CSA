
desc = """
【521ke Course Select Assistant】

本脚本仅供编程学习交流使用，严禁用于商业用途，请于24小时内删除！
程序使用单线程进行选课请求，以尽量减小对选课网站造成的影响
项目仓库: https://github.com/233a344a455/521ke-CSA

【本脚本无法保证自动选课一定成功！】

@Author: DeltaZero
@Time: 2021/09/04
@Version: 0.3
"""


SCHOOL_ID = '' # 请填写此项，可以通过抓包获取
TIME_OFFSET = -3 # 开始选课后几秒发起选课请求，若为负值表示提前发起选课请求的秒数


import base64
import logging
import re
import subprocess
import time
from datetime import datetime
import requests
import simplejson
import os

logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', level='INFO')
logger = logging.getLogger('521CSA')

# Ignore system proxy
session = requests.Session()
session.trust_env = False

def get_cookies(username: str, password: str) -> requests.sessions.RequestsCookieJar:
    url = "https://www.521ke.com/sso/doStudNoAjaxLogin"
    data = {'schoId': SCHOOL_ID, 'userName': username, 'password': password}

    r = session.post(url, data=data)

    if not r.json()['success']:
        logger.error("登录失败: " + r.json()['message'])
        os.system("pause")
        exit(1)
    else:
        logger.info("登录成功!")
        return r.cookies


def get_basic_info(cookies: requests.sessions.RequestsCookieJar):
    url = "https://www.521ke.com/electiveCourse/studentChoice"
    r = session.get(url, cookies=cookies).text
    name = re.findall(r"<span id='stuName'>(.*?)<\/span>", r)[0]
    class_ = re.findall(r"<span id='className'>，班级：(.*?)<\/span>", r)[0]
    configId = re.findall(r'var currConfigId = "(.*?)";', r)[0]
    startTime = re.findall("""showChoicetimesHtmlInfo\("(.*?)年(.*?)月(.*?)日 (.*?)时(.*?)分",""", r)[0]

    logger.info(f"学生姓名: {name}, 班级: {class_}")
    return configId, datetime(*[int(i) for i in startTime])


def get_courses_list(cookies: requests.sessions.RequestsCookieJar, configId: str):
    url = f"https://www.521ke.com/electiveCourse/getStuCourseDefault/{configId}"
    r = session.get(url, cookies=cookies)
    try:
        return [(i['subN'] + ' ' + i['tName'], i['subid']) for i in r.json()['optCourseSubjectlist']]
    except KeyError:
        logger.error("获取选课列表失败，请稍后重试")
        os.system("pause")
        exit(1)


def elect_course(configId: str, courseId: str, cookies: requests.sessions.RequestsCookieJar):
    url = f"https://www.521ke.com/electiveCourse/addSelCourseLockStudVer/{configId}/{courseId}/1"

    while True:
        r = session.post(url, data={}, cookies=cookies)
        try:
            if r.status_code != 200:
                logger.warning(f"服务器响应错误! StatusCode:{r.status_code}")

            state = r.json()['success']

            if state == 'success':
                logger.info('选课成功！')
                return
            elif state == 'error0':
                logger.warning("未到选课时间！【请勿关闭程序】将在选课时间开始后自动选课")
                time.sleep(0.3)
            elif state == 'error1':
                logger.info("选课已完成！")
                return
            elif state == 'error4':
                logger.error("选课失败: 选课人数已满")
                return
            else:
                logger.warning("其它错误: " + r.json()['success'])
                time.sleep(0.3)

        except simplejson.errors.JSONDecodeError:
            logger.error('Cookie 无效')
            return


if __name__ == '__main__':

    print(desc)

    username = input("输入学号: ").strip()
    password = input("输入密码: ").strip()
    print('')

    cookies = get_cookies(username, password)
    configId, startTime = get_basic_info(cookies)
    courseList = get_courses_list(cookies, configId)

    print("\n选课列表:")
    for idx, (courseName, _) in enumerate(courseList):
        print(f"    [{idx + 1}] {courseName}")
    idx = int(input("\n请输入课程编号: ").strip()) - 1

    try:
        courseId = courseList[idx][1]
    except IndexError:
        logger.error("无效的序号输入！")
        os.system("pause")
        exit(1)
    logger.info(f"已选择{courseList[idx][0]}，CourseId: {courseId}")

    if startTime > datetime.now():
        waitTime = (startTime - datetime.now()).seconds + TIME_OFFSET
    else:
        waitTime = 0

    logger.info(f"开始选课时间: {startTime.strftime('%y-%m-%d %I:%M:%S')}，将在选课开始" + \
                f"{'前' if TIME_OFFSET < 0 else '后'}{abs(TIME_OFFSET)}开始请求")

    while waitTime > 0:
        logger.info(f"开始选课时间: {startTime.strftime('%y-%m-%d %I:%M:%S')}, "
                    f"现在时间: {datetime.now().strftime('%y-%m-%d %I:%M:%S')}, "
                    f"将在 {waitTime}s 后开始请求，【等待期间请勿关闭窗口】！")
        time.sleep(min(waitTime, 10))
        waitTime -= 10

    logger.warning("开始发送选课请求...")

    elect_course(configId, courseId, cookies)
    os.system("pause")
