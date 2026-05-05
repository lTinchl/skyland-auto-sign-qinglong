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
import time
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
SKYLAND_NOTIFY = os.getenv('SKYLAND_NOTIFY') or ''

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


def parse_user_token(token_code: str):
    """
    解析用户token
    """
    try:
        t = json.loads(token_code)
        return t['data']['content']
    except:
        return token_code


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

    if not token_list:
        error_msg = '没有设置TOKEN，请先运行Get_Token.py获取并创建SKYLAND_TOKEN'
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
