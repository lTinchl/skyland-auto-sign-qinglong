#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: Get_Token.py (森空岛扫码获取Token)
cron: 0 0 0 1 1 *
new Env('森空岛Token获取');
"""

import logging
import os
import sys
import time
import uuid
from getpass import getpass
from urllib import parse

import requests

APP_CODE = '4ca99fa6b56cc2ba'

SKYLAND_DID = os.getenv('SKYLAND_DID') or uuid.uuid4().hex
SKYLAND_QR_WAIT = int(os.getenv('SKYLAND_QR_WAIT') or '180')
SKYLAND_QR_INTERVAL = int(os.getenv('SKYLAND_QR_INTERVAL') or '2')
SKYLAND_ENV_NAME = os.getenv('SKYLAND_ENV_NAME') or 'SKYLAND_TOKEN'
SKYLAND_ENV_REMARKS = os.getenv('SKYLAND_ENV_REMARKS') or '森空岛Token'
SKYLAND_AUTO_SAVE_TOKEN = (os.getenv('SKYLAND_AUTO_SAVE_TOKEN') or '1').strip().lower() not in ('0', 'false', 'no')
SKYLAND_LOGIN_MODE = (os.getenv('SKYLAND_LOGIN_MODE') or '').strip()
SKYLAND_PHONE = os.getenv('SKYLAND_PHONE') or ''
SKYLAND_CODE = os.getenv('SKYLAND_CODE') or os.getenv('SKYLAND_PHONE_CODE') or ''
SKYLAND_PASSWORD = os.getenv('SKYLAND_PASSWORD') or ''

QL_URL = (os.getenv('QL_URL') or os.getenv('QL_HOST') or 'http://127.0.0.1:5700').rstrip('/')
QL_CLIENT_ID = os.getenv('QL_CLIENT_ID') or ''
QL_CLIENT_SECRET = os.getenv('QL_CLIENT_SECRET') or ''
QL_TOKEN = os.getenv('QL_TOKEN') or ''

SCAN_LOGIN_URL = 'https://as.hypergryph.com/general/v1/gen_scan/login'
SCAN_STATUS_URL = 'https://as.hypergryph.com/general/v1/scan_status'
TOKEN_SCAN_CODE_URL = 'https://as.hypergryph.com/user/auth/v1/token_by_scan_code'
SEND_PHONE_CODE_URL = 'https://as.hypergryph.com/general/v1/send_phone_code'
TOKEN_PHONE_CODE_URL = 'https://as.hypergryph.com/user/auth/v2/token_by_phone_code'
TOKEN_PASSWORD_URL = 'https://as.hypergryph.com/user/auth/v1/token_by_phone_password'

HEADER_LOGIN = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'dId': SKYLAND_DID,
    'X-Requested-With': 'com.hypergryph.skland'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def check_auth_response(resp: dict, action: str):
    status = resp.get('status', resp.get('code'))
    if status != 0:
        raise Exception(f'{action}失败: {resp.get("msg") or resp.get("message") or resp}')


def get_qr_image_url(content: str):
    return 'https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=' + parse.quote(content, safe='')


def show_login_qr(content: str):
    print('\n请使用森空岛App扫码，并在App内确认登录:')
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


def create_scan_login():
    resp = requests.post(SCAN_LOGIN_URL, json={}, headers=HEADER_LOGIN, timeout=20).json()

    check_auth_response(resp, '创建扫码登录')

    data = resp.get('data') or {}
    scan_id = data.get('scanId')
    scan_url = data.get('scanUrl')
    if not scan_id or not scan_url:
        raise Exception(f'创建扫码登录失败: 返回结果缺少scanId或scanUrl: {resp}')

    return scan_id, scan_url


def wait_scan_code(scan_id: str):
    deadline = time.time() + SKYLAND_QR_WAIT

    while time.time() < deadline:
        resp = requests.get(SCAN_STATUS_URL, params={
            'scanId': scan_id
        }, headers=HEADER_LOGIN, timeout=20).json()

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
    resp = requests.post(TOKEN_SCAN_CODE_URL, json={
        'scanCode': scan_code
    }, headers=HEADER_LOGIN, timeout=20).json()

    check_auth_response(resp, '扫码登录')

    data = resp.get('data') or {}
    token = data.get('content') or data.get('token')
    if not token:
        raise Exception(f'扫码登录失败: 返回结果中没有data.content或data.token: {resp}')

    return token


def extract_login_token(resp: dict, action: str):
    check_auth_response(resp, action)

    token = resp.get('data', {}).get('token')
    if not token:
        raise Exception(f'{action}失败: 返回结果中没有data.token: {resp}')

    return token


def send_phone_code(phone: str):
    resp = requests.post(SEND_PHONE_CODE_URL, json={
        'phone': phone,
        'type': 2
    }, headers=HEADER_LOGIN, timeout=20).json()

    check_auth_response(resp, '发送验证码')


def login_by_phone_code(phone: str, code: str):
    resp = requests.post(TOKEN_PHONE_CODE_URL, json={
        'phone': phone,
        'code': code
    }, headers=HEADER_LOGIN, timeout=20).json()

    return extract_login_token(resp, '手机号验证码登录')


def login_by_password(phone: str, password: str):
    resp = requests.post(TOKEN_PASSWORD_URL, json={
        'phone': phone,
        'password': password
    }, headers=HEADER_LOGIN, timeout=20).json()

    return extract_login_token(resp, '账号密码登录')


def get_token_by_qrcode():
    scan_id, scan_url = create_scan_login()
    logging.info(f'扫码登录ID: {scan_id}')
    show_login_qr(scan_url)

    scan_code = wait_scan_code(scan_id)
    token = login_by_scan_code(scan_code)
    logging.info('扫码登录成功，已获取Token')
    return token


def get_token_by_phone_code(phone: str = '', code: str = ''):
    phone = phone or SKYLAND_PHONE
    code = code or SKYLAND_CODE

    if not phone:
        raise Exception('手机号验证码登录需要手机号，请配置SKYLAND_PHONE或在交互模式输入')

    if not code:
        send_phone_code(phone)
        logging.info('验证码已发送')
        if sys.stdin.isatty():
            code = input('请输入短信验证码: ').strip()
        else:
            raise Exception('请把收到的验证码配置到SKYLAND_CODE后重新运行')

    if not code:
        raise Exception('未输入短信验证码')

    token = login_by_phone_code(phone, code)
    logging.info('手机号验证码登录成功，已获取Token')
    return token


def get_token_by_password(phone: str = '', password: str = ''):
    phone = phone or SKYLAND_PHONE
    password = password or SKYLAND_PASSWORD

    if not phone:
        raise Exception('账号密码登录需要手机号，请配置SKYLAND_PHONE或在交互模式输入')

    if not password and sys.stdin.isatty():
        password = getpass('请输入密码: ').strip()

    if not password:
        raise Exception('账号密码登录需要配置SKYLAND_PASSWORD或在交互模式输入')

    token = login_by_password(phone, password)
    logging.info('账号密码登录成功，已获取Token')
    return token


def choose_login_mode():
    if SKYLAND_LOGIN_MODE:
        return SKYLAND_LOGIN_MODE

    if not sys.stdin.isatty():
        return '0'

    print('\n请选择Token获取方式:')
    print('0. 森空岛App扫码')
    print('1. 手机号 + 验证码')
    print('2. 账号密码')
    choice = input('请输入序号，直接回车默认扫码: ').strip()
    return choice or '0'


def get_token():
    mode = choose_login_mode()

    if mode in ('0', 'qr', 'qrcode', ''):
        return get_token_by_qrcode()

    if mode in ('1', 'code', 'sms', 'phone'):
        phone = ''
        if sys.stdin.isatty() and not SKYLAND_PHONE:
            phone = input('请输入手机号: ').strip()
        return get_token_by_phone_code(phone)

    if mode in ('2', 'password', 'pwd', 'account'):
        phone = ''
        if sys.stdin.isatty() and not SKYLAND_PHONE:
            phone = input('请输入手机号: ').strip()
        return get_token_by_password(phone)

    raise Exception('未知登录方式。SKYLAND_LOGIN_MODE留空/0为扫码，1为验证码，2为账号密码')


def get_ql_auth_header():
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


def get_qinglong_envs(headers: dict):
    resp = requests.get(f'{QL_URL}/open/envs', params={
        'searchValue': SKYLAND_ENV_NAME
    }, headers=headers, timeout=20).json()

    if resp.get('code') not in (200, 0):
        raise Exception(f'查询青龙变量失败: {resp.get("message") or resp.get("data") or resp}')

    envs = resp.get('data') or []
    return [env for env in envs if env.get('name') == SKYLAND_ENV_NAME]


def append_token_value(old_value: str, token: str):
    values = []
    for item in (old_value or '').replace('\n', ';').replace(',', ';').split(';'):
        item = item.strip()
        if item and item not in values:
            values.append(item)

    if token not in values:
        values.append(token)

    return ';'.join(values)


def update_qinglong_env(env: dict, value: str, headers: dict):
    env_id = env.get('id') or env.get('_id')
    if not env_id:
        raise Exception(f'更新青龙变量失败: 未找到变量id: {env}')

    resp = requests.put(f'{QL_URL}/open/envs', json={
        'id': env_id,
        'name': SKYLAND_ENV_NAME,
        'value': value,
        'remarks': env.get('remarks') or SKYLAND_ENV_REMARKS
    }, headers=headers, timeout=20).json()

    if resp.get('code') not in (200, 0):
        raise Exception(f'更新青龙变量失败: {resp.get("message") or resp.get("data") or resp}')


def create_qinglong_env(token: str, headers: dict):
    resp = requests.post(f'{QL_URL}/open/envs', json=[{
        'name': SKYLAND_ENV_NAME,
        'value': token,
        'remarks': SKYLAND_ENV_REMARKS
    }], headers=headers, timeout=20).json()

    if resp.get('code') not in (200, 0):
        raise Exception(f'创建青龙变量失败: {resp.get("message") or resp.get("data") or resp}')


def save_token_to_qinglong(token: str):
    if not SKYLAND_AUTO_SAVE_TOKEN:
        return False

    headers = get_ql_auth_header()
    if not headers:
        logging.info('未配置QL_TOKEN或QL_CLIENT_ID/QL_CLIENT_SECRET，跳过自动写入青龙变量')
        return False

    headers['Content-Type'] = 'application/json'

    env_list = get_qinglong_envs(headers)
    if env_list:
        old_value = env_list[0].get('value') or ''
        new_value = append_token_value(old_value, token)
        update_qinglong_env(env_list[0], new_value, headers)
        logging.info(f'已更新青龙环境变量: {SKYLAND_ENV_NAME}')
    else:
        create_qinglong_env(token, headers)
        logging.info(f'已创建青龙环境变量: {SKYLAND_ENV_NAME}')

    return True


def print_manual_token(token: str):
    line = f'{SKYLAND_ENV_NAME}={token}'
    border = '=' * 72
    logging.warning(border)
    logging.warning('未配置青龙OpenAPI，无法自动写入变量。请复制下面这一行到青龙环境变量：')
    logging.warning(line)
    logging.warning(border)
    print('\n' + border)
    print('!!! 请复制下面这一行到青龙环境变量 !!!')
    print(line)
    print(border + '\n')


def save_or_print_token(token: str):
    try:
        if save_token_to_qinglong(token):
            return
    except Exception as e:
        logging.error(f'保存Token到青龙失败: {e}')

    print_manual_token(token)


def main():
    logging.info('========== 森空岛Token获取开始 ==========')
    token = get_token()
    save_or_print_token(token)
    logging.info('========== 森空岛Token获取结束 ==========')


if __name__ == '__main__':
    main()
