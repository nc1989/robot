#-*- coding:utf8 -*-
import json
import time
from bottle import Bottle, run, request, response, get, post
from threading import Thread
from lib.message import *

app = Bottle()
recv_msg_handler = lambda qq, msg: None
get_msg_handler = None


def start(rmh, gmh):
    if hasattr(start, "running"):  # 防止start被多次运行
        return
    global recv_msg_handler
    global get_msg_handler
    recv_msg_handler = rmh
    get_msg_handler = gmh
    start.running = True
    th = Thread(target=start_listen)
    th.setDaemon(True)  # 线程设置Daemon，随主线程自动销毁
    th.start()


def start_listen():
    u""" 线程入口，启动bottle开始监听 """
    run(app, host='0.0.0.0', port=8000)


def pack_msg(msg):
    pattern = r"<&&>%s<&>%s<&>%s"
    if msg.isgroup:
        m = pattern % ("SendClusterMessage", msg.to, msg.content)
    else:
        m = pattern % ("SendMessage", msg.to, msg.content)
    return m


@app.get('/qqplus/msg')
def get_msg():
    ret = ''
    qq = int(request.query.get('RobotQQ'))
    if callable(get_msg_handler):
        #get_msg_hanlder must return a list of lib.message_pool.SendMessage
        msgs = get_msg_handler(qq)
        if msgs:
            for m in msgs:
                ret += pack_msg(m)
    return ret


@app.post('/qqplus/msg')
def recv_msg():
    event = request.forms.get('Event', "-")
    qq = int(request.forms.get('RobotQQ'))
    if event == "KeepAlive":
        msg = AliveMessage()
    elif event == "ReceiveClusterIM":
        group = int(request.forms.get('ExternalId'))
        groupname = request.forms.get('Name')
        sender = int(request.forms.get('QQ'))
        nickname = request.forms.get('Nick')
        content = request.forms.get('Message')
        msg = GroupMessage(group, groupname, sender, nickname, content)
    elif event == "ReceiveNormalIM":
        sender = int(request.forms.get('QQ'))
        nickname = request.forms.get('NickName')
        content = request.forms.get('Message')
        msg = FriendMessage(sender, nickname, content)
    else:
        msg = UnknownMessage()
    recv_msg_handler(qq, msg)
    return ''


@app.get('/qqplus/test')
def test():
    r = [1, 3, 2]
    response.content_type = 'application/json'
    return json.dumps(r)


if __name__ == '__main__':
    start(None, None)
    time.sleep(15)
