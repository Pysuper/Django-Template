import json

import requests

from utils.basic import DecimalEncoder


def send_dingding(content):
    """
    发送钉钉提醒
    :param content:
    :return:
    """
    if len(content) > 200:
        content = content[0:200]

    keyword = "alita:"

    # url = 'https://oapi.dingtalk.com/robot/send?access_token=58e14d85a5a22c7cbc664a468511be088c2ee4c3b1e8f9ccdf9dc9b237ca2907'
    url = "https://oapi.dingtalk.com/robot/send?access_token=6ab2fbf60db5b4263ae08bc7a71c42b2515b6c18943519b326dca5d95e6d9849"
    json_text = {
        "msgtype": "text",
        "text": {"content": keyword + content},
        "at": {
            "atMobiles": [
                "13316990258",
            ]
        },
    }
    headers = {"Content-Type": "application/json"}
    data = json.dumps(
        json_text,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        cls=DecimalEncoder,
    )
    r = requests.post(url, data=data.encode("utf-8"), headers=headers).json()
    print(r)


# send_dingding('test')
