#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: skyland_qinglong.py (森空岛签到-青龙面板适配版)
Author: Adapted for Qinglong
cron: 0 30 8 * * *
new Env('森空岛签到');
Update: 2026-04-27
"""

import hashlib
import hmac
import json
import logging
import os
import sys
import time
import uuid
from getpass import getpass
from urllib import parse

import requests

# 尝试导入青龙面板的notify模块，如果不存在则跳过
try:
    import notify
    NOTIFY_AVAILABLE = True
except ImportError:
    NOTIFY_AVAILABLE = False
    print("未检测到青龙面板notify模块，将跳过推送通知")

# ==================== 配置区 ====================
# 从环境变量获取配置
SKYLAND_TOKEN = os.getenv('SKYLAND_TOKEN') or os.getenv('TOKEN') or ''
SKYLAND_COOKIE = os.getenv('SKYLAND_COOKIE') or os.getenv('SKLAND_COOKIE') or ''
SKYLAND_LOGIN_MODE = (os.getenv('SKYLAND_LOGIN_MODE') or os.getenv('SKYLAND_TYPE') or '').strip().lower()
SKYLAND_PHONE = os.getenv('SKYLAND_PHONE') or ''
SKYLAND_PASSWORD = os.getenv('SKYLAND_PASSWORD') or ''
SKYLAND_CODE = os.getenv('SKYLAND_CODE') or os.getenv('SKYLAND_PHONE_CODE') or ''
SKYLAND_DID = os.getenv('SKYLAND_DID') or uuid.uuid4().hex
SKYLAND_QR_URL = os.getenv('SKYLAND_QR_URL') or 'https://web-api.skland.com/account/info/hg'
SKYLAND_QR_WAIT = int(os.getenv('SKYLAND_QR_WAIT') or '180')
SKYLAND_QR_INTERVAL = int(os.getenv('SKYLAND_QR_INTERVAL') or '2')
SKYLAND_AUTO_SAVE_TOKEN = (os.getenv('SKYLAND_AUTO_SAVE_TOKEN') or '1').strip() not in ('0', 'false', 'False', 'no')
SKYLAND_ENV_NAME = os.getenv('SKYLAND_ENV_NAME') or 'SKYLAND_TOKEN'
SKYLAND_NOTIFY = os.getenv('SKYLAND_NOTIFY') or ''

QL_URL = (os.getenv('QL_URL') or os.getenv('QL_HOST') or 'http://127.0.0.1:5700').rstrip('/')
QL_CLIENT_ID = os.getenv('QL_CLIENT_ID') or ''
QL_CLIENT_SECRET = os.getenv('QL_CLIENT_SECRET') or ''
QL_TOKEN = os.getenv('QL_TOKEN') or ''

# 消息内容
run_message = ''
account_num = 1

# 请求头配置
header = {
    'cred': '',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'X-Requested-With': 'com.hypergryph.skland'
}

header_login = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'dId': SKYLAND_DID,
    'X-Requested-With': 'com.hypergryph.skland'
}

# 签名请求头一定要这个顺序，否则失败
header_for_sign = {
    'platform': '3',
    'timestamp': '',
    'dId': '',
    'vName': '1.0.0'
}

# 参数验证的token
sign_token = ''

# API地址
sign_url_mapping = {
    'arknights': 'https://zonai.skland.com/api/v1/game/attendance',
    'endfield': 'https://zonai.skland.com/web/v1/game/endfield/attendance'
}
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
cred_code_url = "https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code"
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
token_info_url = "https://web-api.skland.com/account/info/hg"
login_code_url = "https://as.hypergryph.com/general/v1/send_phone_code"
token_phone_code_url = "https://as.hypergryph.com/user/auth/v2/token_by_phone_code"
token_password_url = "https://as.hypergryph.com/user/auth/v1/token_by_phone_password"
scan_login_url = "https://as.hypergryph.com/general/v1/gen_scan/login"
scan_status_url = "https://as.hypergryph.com/general/v1/scan_status"
token_scan_code_url = "https://as.hypergryph.com/user/auth/v1/token_by_scan_code"

app_code = '4ca99fa6b56cc2ba'

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ==================== 推送通知函数 ====================
def send_message(title: str, content: str, notify_type: str = ''):
    """
    整合消息推送
    :param title: 标题
    :param content: 内容
    :param notify_type: 推送类型
    """
    if not NOTIFY_AVAILABLE or not notify_type:
        return

    notify_type = notify_type.strip().upper()

    try:
        if notify_type == 'TG':
            notify.telegram_bot(title, content)
        elif notify_type == 'BARK':
            notify.bark(title, content)
        elif notify_type == 'DD':
            notify.dingding_bot(title, content)
        elif notify_type == 'FSKEY':
            notify.feishu_bot(title, content)
        elif notify_type == 'GOBOT':
            notify.go_cqhttp(title, content)
        elif notify_type == 'GOTIFY':
            notify.gotify(title, content)
        elif notify_type == 'IGOT':
            notify.iGot(title, content)
        elif notify_type == 'SERVERJ':
            notify.serverJ(title, content)
        elif notify_type == 'PUSHDEER':
            notify.pushdeer(title, content)
        elif notify_type == 'PUSHPLUS':
            notify.pushplus_bot(title, content)
        elif notify_type == 'QMSG':
            notify.qmsg_bot(title, content)
        elif notify_type == 'QYWXAPP':
            notify.wecom_app(title, content)
        elif notify_type == 'QYWXBOT':
            notify.wecom_bot(title, content)
        else:
            # 默认使用青龙面板的send函数
            if hasattr(notify, 'send'):
                notify.send(title, content)
    except Exception as e:
        logging.error(f'推送通知失败: {e}')


# ==================== 签名相关函数 ====================
def generate_signature(token: str, path: str, body_or_query: str):
    """
    获得签名头
    :param token: cred接口返回的token
    :param path: 请求路径（不包括网址）
    :param body_or_query: GET请求的query或POST请求的body
    :return: 计算完毕的sign和header
    """
    # 时间戳-2秒，避免服务器时间校验问题
    t = str(int(time.time()) - 2)
    token_bytes = token.encode('utf-8')
    header_ca = header_for_sign.copy()
    header_ca['timestamp'] = t
    header_ca_str = json.dumps(header_ca, separators=(',', ':'))
    s = path + body_or_query + t + header_ca_str
    hex_s = hmac.new(token_bytes, s.encode('utf-8'), hashlib.sha256).hexdigest()
    md5 = hashlib.md5(hex_s.encode('utf-8')).hexdigest()
    logging.info(f'算出签名: {md5}')
    return md5, header_ca


def get_sign_header(url: str, method: str, body, old_header: dict):
    """
    获取带签名的请求头
    """
    h = old_header.copy()
    p = parse.urlparse(url)
    if method.lower() == 'get':
        h['sign'], header_ca = generate_signature(sign_token, p.path, p.query)
    else:
        body_str = json.dumps(body) if body else ''
        h['sign'], header_ca = generate_signature(sign_token, p.path, body_str)
    h.update(header_ca)
    return h


def copy_header(cred: str):
    """
    组装请求头
    """
    v = header.copy()
    v['cred'] = cred
    return v


# ==================== 登录相关函数 ====================
def split_token_items(value: str):
    """
    拆分环境变量里的Token多账号配置
    """
    if not value:
        return []

    value = value.strip()
    if value.startswith('{'):
        return [value]

    for sep in ['\n', ';', ',']:
        if sep in value:
            return [item.strip() for item in value.split(sep) if item.strip()]

    return [value]


def split_cookie_items(value: str):
    """
    拆分环境变量里的Cookie多账号配置
    """
    if not value:
        return []

    value = value.strip()
    for sep in ['\n', '||']:
        if sep in value:
            return [item.strip() for item in value.split(sep) if item.strip()]

    return [value]


def parse_user_token(token_code: str):
    """
    解析用户token
    """
    try:
        t = json.loads(token_code)
        return t['data']['content']
    except:
        return token_code


def get_token_by_cookie(cookie: str):
    """
    通过森空岛网页登录Cookie获取用户token
    """
    headers = header_login.copy()
    headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Cookie': cookie,
        'Referer': 'https://www.skland.com/',
        'Origin': 'https://www.skland.com'
    })

    resp = requests.get(token_info_url, headers=headers, timeout=20)
    try:
        data = resp.json()
    except ValueError:
        raise Exception(f'通过Cookie获取Token失败: 接口返回非JSON内容，HTTP {resp.status_code}')

    if data.get('code') != 0:
        raise Exception(f'通过Cookie获取Token失败: {data.get("msg") or data.get("message") or data}')

    token = data.get('data', {}).get('content')
    if not token:
        raise Exception('通过Cookie获取Token失败: 返回结果中没有data.content')

    return token


def check_auth_response(resp: dict, action: str):
    """
    检查鹰角账号接口返回值
    """
    status = resp.get('status', resp.get('code'))
    if status != 0:
        raise Exception(f'{action}失败: {resp.get("msg") or resp.get("message") or resp}')


def extract_login_token(resp: dict, action: str):
    """
    从登录接口返回值中提取token
    """
    check_auth_response(resp, action)

    token = resp.get('data', {}).get('token')
    if not token:
        raise Exception(f'{action}失败: 返回结果中没有data.token')

    return token


def get_qr_image_url(content: str):
    """
    生成在线二维码图片地址
    """
    return 'https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=' + parse.quote(content, safe='')


def show_login_qr(content: str = ''):
    """
    输出第一个登录二维码，不轮询登录状态
    """
    content = content or SKYLAND_QR_URL
    print('\n请扫码打开森空岛Token获取页:')
    print(content)

    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(content)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print('当前环境没有qrcode库，使用下面的二维码图片链接:')
        print(get_qr_image_url(content))

    print('登录后页面返回JSON时，data.content就是SKYLAND_TOKEN。')


def create_scan_login():
    """
    创建鹰角扫码登录会话
    """
    resp = requests.post(scan_login_url, json={
        'appCode': app_code
    }, headers=header_login, timeout=20).json()

    check_auth_response(resp, '创建扫码登录')

    data = resp.get('data') or {}
    scan_id = data.get('scanId')
    scan_url = data.get('scanUrl')
    if not scan_id or not scan_url:
        raise Exception(f'创建扫码登录失败: 返回结果缺少scanId或scanUrl: {resp}')

    return scan_id, scan_url


def wait_scan_code(scan_id: str):
    """
    等待森空岛App扫码确认并返回scanCode
    """
    deadline = time.time() + SKYLAND_QR_WAIT

    while time.time() < deadline:
        resp = requests.get(scan_status_url, params={
            'scanId': scan_id
        }, headers=header_login, timeout=20).json()

        status = resp.get('status', resp.get('code'))
        data = resp.get('data') or {}
        scan_code = data.get('scanCode')

        if status == 0 and scan_code:
            return scan_code

        if status == 100:
            logging.info('等待扫码...')
        elif status == 101:
            logging.info('已扫码，等待在App内确认登录...')
        elif status == 102:
            raise Exception('二维码已过期，请重新运行脚本生成新的二维码')
        else:
            msg = resp.get('msg') or resp.get('message')
            logging.info(f'等待扫码状态: {status} {msg or ""}'.strip())

        time.sleep(max(SKYLAND_QR_INTERVAL, 1))

    raise Exception(f'扫码登录超时，超过 {SKYLAND_QR_WAIT} 秒未完成')


def login_by_scan_code(scan_code: str):
    """
    通过扫码确认码换取token
    """
    resp = requests.post(token_scan_code_url, json={
        'scanCode': scan_code,
        'appCode': app_code
    }, headers=header_login, timeout=20).json()

    return extract_login_token(resp, '扫码登录')


def login_by_qrcode():
    """
    通过森空岛App扫码登录并获取token
    """
    scan_id, scan_url = create_scan_login()
    logging.info(f'扫码登录ID: {scan_id}')
    show_login_qr(scan_url)
    scan_code = wait_scan_code(scan_id)
    token = login_by_scan_code(scan_code)
    logging.info('扫码登录成功，已获取Token')
    return token


def send_phone_code(phone: str):
    """
    发送手机号验证码
    """
    resp = requests.post(login_code_url, json={
        'phone': phone,
        'type': 2
    }, headers=header_login, timeout=20).json()

    check_auth_response(resp, '发送验证码')


def login_by_phone_code(phone: str, code: str):
    """
    通过手机号验证码登录并获取token
    """
    resp = requests.post(token_phone_code_url, json={
        'phone': phone,
        'code': code
    }, headers=header_login, timeout=20).json()

    return extract_login_token(resp, '手机号验证码登录')


def login_by_password(phone: str, password: str):
    """
    通过账号密码登录并获取token
    """
    resp = requests.post(token_password_url, json={
        'phone': phone,
        'password': password
    }, headers=header_login, timeout=20).json()

    return extract_login_token(resp, '账号密码登录')


def get_ql_auth_header():
    """
    获取青龙OpenAPI认证头
    """
    token = QL_TOKEN

    if not token and QL_CLIENT_ID and QL_CLIENT_SECRET:
        resp = requests.get(f'{QL_URL}/open/auth/token', params={
            'client_id': QL_CLIENT_ID,
            'client_secret': QL_CLIENT_SECRET
        }, timeout=20).json()

        if resp.get('code') not in (200, 0):
            raise Exception(f'获取青龙OpenAPI Token失败: {resp.get("message") or resp}')

        token = resp.get('data', {}).get('token')

    if not token:
        return {}

    return {'Authorization': f'Bearer {token}'}


def save_token_to_qinglong(token: str):
    """
    将扫码获取到的Token保存到青龙环境变量
    """
    if not SKYLAND_AUTO_SAVE_TOKEN:
        return False

    headers = get_ql_auth_header()
    if not headers:
        logging.info('未配置QL_TOKEN或QL_CLIENT_ID/QL_CLIENT_SECRET，跳过自动写入青龙变量')
        return False

    headers['Content-Type'] = 'application/json'

    resp = requests.post(f'{QL_URL}/open/envs', json=[{
        'name': SKYLAND_ENV_NAME,
        'value': token,
        'remarks': '森空岛扫码登录自动创建'
    }], headers=headers, timeout=20).json()

    if resp.get('code') not in (200, 0):
        raise Exception(f'写入青龙变量失败: {resp.get("message") or resp}')

    logging.info(f'已写入青龙环境变量: {SKYLAND_ENV_NAME}')
    return True


def get_token_by_login_config():
    """
    通过环境变量配置登录并获取token
    """
    mode = SKYLAND_LOGIN_MODE
    if not mode:
        if SKYLAND_PHONE and SKYLAND_PASSWORD:
            mode = 'password'
        elif SKYLAND_PHONE:
            mode = 'code'

    if mode in ('password', 'pwd', 'account'):
        if not SKYLAND_PHONE or not SKYLAND_PASSWORD:
            raise Exception('账号密码登录需要配置SKYLAND_PHONE和SKYLAND_PASSWORD')
        return [login_by_password(SKYLAND_PHONE, SKYLAND_PASSWORD)]

    if mode in ('code', 'sms', 'phone'):
        if not SKYLAND_PHONE:
            raise Exception('手机号验证码登录需要配置SKYLAND_PHONE')

        if SKYLAND_CODE:
            return [login_by_phone_code(SKYLAND_PHONE, SKYLAND_CODE)]

        send_phone_code(SKYLAND_PHONE)
        if sys.stdin.isatty():
            code = input('请输入短信验证码: ').strip()
            if not code:
                raise Exception('未输入短信验证码')
            return [login_by_phone_code(SKYLAND_PHONE, code)]

        raise Exception('验证码已发送，请把收到的验证码配置到SKYLAND_CODE后重新运行')

    if mode in ('qr', 'qrcode'):
        token = login_by_qrcode()
        try:
            save_token_to_qinglong(token)
        except Exception as e:
            logging.error(f'保存Token到青龙失败: {e}')
        return [token]

    return []


def get_token_by_interactive_login():
    """
    手动运行脚本时提供登录方式选择
    """
    if not sys.stdin.isatty():
        return []

    print('\n请选择登录方式:')
    print('1. 扫码获取Token')
    print('2. 手机号 + 验证码')
    print('3. 账号密码')
    print('4. 跳过登录')
    choice = input('请输入序号: ').strip()

    if choice == '1':
        token = login_by_qrcode()
        try:
            save_token_to_qinglong(token)
        except Exception as e:
            logging.error(f'保存Token到青龙失败: {e}')
        return [token]

    if choice == '2':
        phone = input('请输入手机号: ').strip()
        if not phone:
            raise Exception('未输入手机号')

        send_phone_code(phone)
        code = input('请输入短信验证码: ').strip()
        if not code:
            raise Exception('未输入短信验证码')
        return [login_by_phone_code(phone, code)]

    if choice == '3':
        phone = input('请输入手机号: ').strip()
        password = getpass('请输入密码: ').strip()
        if not phone or not password:
            raise Exception('手机号或密码为空')
        return [login_by_password(phone, password)]

    return []


def get_grant_code(token: str):
    """
    获取认证代码
    """
    resp = requests.post(grant_code_url, json={
        'appCode': app_code,
        'token': token,
        'type': 0
    }, headers=header_login).json()

    if resp.get('status') != 0:
        raise Exception(f'使用token获得认证代码失败: {resp.get("msg")}')
    return resp['data']['code']


def get_cred(grant: str):
    """
    获取cred
    """
    resp = requests.post(cred_code_url, json={
        'code': grant,
        'kind': 1
    }, headers=header_login).json()

    if resp['code'] != 0:
        raise Exception(f'获得cred失败: {resp.get("message")}')

    global sign_token
    sign_token = resp['data']['token']
    return resp['data']['cred']


def login_by_token(token_code: str):
    """
    通过token登录森空岛获取认证
    """
    token_code = parse_user_token(token_code)
    grant_code = get_grant_code(token_code)
    return get_cred(grant_code)


# ==================== 签到相关函数 ====================
def get_binding_list(cred: str):
    """
    获取绑定的角色列表
    """
    global run_message
    v = []

    resp = requests.get(
        binding_url,
        headers=get_sign_header(binding_url, 'get', None, copy_header(cred))
    ).json()

    if resp['code'] != 0:
        message = f"请求角色列表出现问题: {resp.get('message')}"
        run_message += message + '\n'
        logging.error(message)

        if resp.get('message') == '用户未登录':
            message = '用户登录可能失效了，请重新配置TOKEN！'
            run_message += message + '\n'
            logging.error(message)
        return v

    for i in resp['data']['list']:
        if i.get('appCode') not in ('arknights', 'endfield'):
            continue
        for j in i.get('bindingList', []):
            j['appCode'] = i['appCode']
        v.extend(i.get('bindingList', []))

    return v


def sign_for_arknights(data: dict, cred: str):
    """
    明日方舟签到
    """
    body = {
        'uid': data.get('uid'),
        'gameId': data.get('channelMasterId')
    }
    url = sign_url_mapping['arknights']

    resp = requests.post(
        url,
        headers=get_sign_header(url, 'post', body, copy_header(cred)),
        json=body
    ).json()

    game_name = data.get('gameName')
    channel = data.get('channelName')
    nickname = data.get('nickName') or ''

    if resp.get('code') != 0:
        return f'[{game_name}]角色{nickname}({channel})签到失败！原因: {resp.get("message")}'

    awards = resp['data']['awards']
    result = ''
    for j in awards:
        res = j['resource']
        result += f'{res["name"]}×{j.get("count") or 1} '

    return f'[{game_name}]角色{nickname}({channel})签到成功，获得了{result.strip()}'


def sign_for_endfield(data: dict, cred: str):
    """
    终末地签到
    """
    roles = data.get('roles', [])
    game_name = data.get('gameName')
    channel = data.get('channelName')
    results = []

    for role in roles:
        nickname = role.get('nickname') or ''
        url = sign_url_mapping['endfield']
        headers = get_sign_header(url, 'post', None, copy_header(cred))
        headers.update({
            'Content-Type': 'application/json',
            'sk-game-role': f'3_{role["roleId"]}_{role["serverId"]}',
            'referer': 'https://game.skland.com/',
            'origin': 'https://game.skland.com/'
        })

        resp = requests.post(url, headers=headers).json()

        if resp['code'] != 0:
            results.append(f'[{game_name}]角色{nickname}({channel})签到失败！原因: {resp.get("message")}')
        else:
            awards_result = []
            result_data = resp['data']
            result_info_map = result_data['resourceInfoMap']

            for a in result_data['awardIds']:
                award_id = a['id']
                awards = result_info_map[award_id]
                award_name = awards['name']
                award_count = awards['count']
                awards_result.append(f'{award_name}×{award_count}')

            results.append(f'[{game_name}]角色{nickname}({channel})签到成功，获得了: {", ".join(awards_result)}')

    return '\n'.join(results)


def do_sign(cred: str):
    """
    执行签到
    """
    global run_message, account_num

    characters = get_binding_list(cred)

    for character in characters:
        app_code = character.get('appCode')
        msg = ''

        try:
            if app_code == 'arknights':
                msg = sign_for_arknights(character, cred)
            elif app_code == 'endfield':
                msg = sign_for_endfield(character, cred)

            if msg:
                run_message += f'[账号{account_num}] {msg}\n'
                logging.info(f'[账号{account_num}] {msg}')
        except Exception as e:
            error_msg = f'[账号{account_num}] 签到异常: {str(e)}'
            run_message += error_msg + '\n'
            logging.error(error_msg)

    account_num += 1


def start(token: str):
    """
    开始签到流程
    """
    global run_message

    try:
        cred = login_by_token(token)
        do_sign(cred)
    except Exception as ex:
        error_msg = f'签到失败: {str(ex)}'
        run_message += error_msg + '\n'
        logging.error(error_msg, exc_info=True)


# ==================== 主函数 ====================
def main():
    global run_message, account_num

    logging.info('========== 森空岛签到开始 ==========')
    logging.info('项目地址: https://github.com/lTinchl/skyland-auto-sign-qinglong')

    # 获取token列表
    token_list = split_token_items(SKYLAND_TOKEN)

    # 如果未直接配置Token，则尝试用浏览器登录Cookie自动获取Token。
    if not token_list and SKYLAND_COOKIE:
        for idx, cookie in enumerate(split_cookie_items(SKYLAND_COOKIE), 1):
            try:
                logging.info(f'正在通过第 {idx} 个Cookie获取Token')
                token_list.append(get_token_by_cookie(cookie))
            except Exception as e:
                message = f'第 {idx} 个Cookie获取Token失败: {e}'
                run_message += message + '\n'
                logging.error(message)

    # 如果配置了登录方式，则通过鹰角账号登录接口自动获取Token。
    if not token_list:
        try:
            token_list = get_token_by_login_config()
        except Exception as e:
            message = f'自动登录获取Token失败: {e}'
            run_message += message + '\n'
            logging.error(message)

    # 手动运行脚本时，允许在终端选择登录方式。
    if not token_list:
        try:
            token_list = get_token_by_interactive_login()
        except Exception as e:
            message = f'交互登录获取Token失败: {e}'
            run_message += message + '\n'
            logging.error(message)

    if not token_list:
        error_msg = '没有可用TOKEN。扫码登录请把页面返回的data.content填到SKYLAND_TOKEN；也可配置SKYLAND_COOKIE，或用SKYLAND_LOGIN_MODE=password/code自动登录'
        logging.error(error_msg)
        run_message = error_msg
        send_message('森空岛签到', run_message, SKYLAND_NOTIFY)
        return

    logging.info(f'共检测到 {len(token_list)} 个账号')

    # 重置账号计数
    account_num = 1

    # 遍历所有token进行签到
    for idx, token in enumerate(token_list, 1):
        if token:
            logging.info(f'开始处理第 {idx} 个账号')
            start(token)

            # 多账号之间延迟，避免请求过快
            if idx < len(token_list):
                logging.info('等待10秒后处理下一个账号...')
                time.sleep(10)

    logging.info('========== 森空岛签到结束 ==========')

    # 发送推送通知
    if run_message:
        send_message('森空岛签到', run_message, SKYLAND_NOTIFY)
        # 青龙面板默认推送
        if NOTIFY_AVAILABLE and hasattr(notify, 'send'):
            try:
                notify.send('森空岛签到', run_message)
            except:
                pass


if __name__ == '__main__':
    main()
