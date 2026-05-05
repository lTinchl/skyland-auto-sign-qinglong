# 森空岛签到 - 青龙面板版

用于森空岛绑定角色签到，支持明日方舟和终末地。项目拆分为两个脚本：

- `Get_Token.py`：获取 `SKYLAND_TOKEN`
- `Auto_Sign.py`：使用 `SKYLAND_TOKEN` 执行签到

## 依赖

```bash
pip install requests
```

如果希望在终端里直接显示二维码：

```bash
pip install qrcode
```

未安装 `qrcode` 时，脚本会输出二维码图片链接。

## 青龙面板使用

### 1. 获取 Token

先运行 `Get_Token.py`。

默认方式是森空岛 App 扫码：

```env
SKYLAND_LOGIN_MODE=0
```

也可以不填 `SKYLAND_LOGIN_MODE`，默认就是扫码。

手机号验证码：

```env
SKYLAND_LOGIN_MODE=1
SKYLAND_PHONE=手机号
SKYLAND_CODE=短信验证码
```

账号密码：

```env
SKYLAND_LOGIN_MODE=2
SKYLAND_PHONE=手机号
SKYLAND_PASSWORD=密码
```

扫码成功或登录成功后，如果没有配置青龙 OpenAPI，日志会高亮输出：

```env
SKYLAND_TOKEN=xxxx
```

把这一行复制到青龙环境变量即可。

### 2. 自动写入青龙变量

如果希望 `Get_Token.py` 自动创建或更新 `SKYLAND_TOKEN` 环境变量，需要配置青龙 OpenAPI：

```env
QL_CLIENT_ID=青龙应用client_id
QL_CLIENT_SECRET=青龙应用client_secret
```

或直接配置：

```env
QL_TOKEN=青龙OpenAPI token
```

可选：

```env
QL_URL=http://127.0.0.1:5700
SKYLAND_ENV_NAME=SKYLAND_TOKEN
```

### 3. 签到

配置好 `SKYLAND_TOKEN` 后，运行 `Auto_Sign.py`。

`Auto_Sign.py` 只负责签到，不负责登录或扫码。没有 Token 时会提示先运行 `Get_Token.py`。

## 多账号

多账号只需要配置多个 `SKYLAND_TOKEN`，支持换行、分号、逗号分隔：

```env
SKYLAND_TOKEN=token1
token2
token3
```

或：

```env
SKYLAND_TOKEN=token1;token2;token3
```

获取多个账号 Token 时，重复运行 `Get_Token.py`，分别扫码或登录不同账号。

如果配置了青龙 OpenAPI，脚本会自动把新 Token 追加到同一个 `SKYLAND_TOKEN` 变量里，而不是创建多个同名变量。同名变量在青龙运行时通常只会导出其中一个，不适合多账号。

如果之前生成过错误的短 Token，请删除旧的同名 `SKYLAND_TOKEN` 变量后重新运行 `Get_Token.py`。

## 物理机运行

在本地电脑直接运行：

```bash
python Get_Token.py
```

未设置 `SKYLAND_LOGIN_MODE` 时，会显示菜单：

```text
0. 森空岛App扫码
1. 手机号 + 验证码
2. 账号密码
```

获取 Token 后，再运行：

```bash
python Auto_Sign.py
```

本地运行时也可以用环境变量配置 `SKYLAND_TOKEN`。

## 常用配置

```env
# Token获取方式：0或不填=扫码，1=手机号验证码，2=账号密码
SKYLAND_LOGIN_MODE=0

# 扫码等待时间，单位秒
SKYLAND_QR_WAIT=180

# 扫码状态查询间隔，单位秒
SKYLAND_QR_INTERVAL=2

# 签到推送类型，依赖青龙notify
SKYLAND_NOTIFY=
```

## 青龙定时

`Auto_Sign.py` 默认定时：

```text
0 30 8 * * *
```

`Get_Token.py` 默认定时写成每年 1 月 1 日，仅用于让青龙能合法添加任务；不建议日常自动执行。需要新增或刷新账号 Token 时，手动运行它即可。
