#-*- coding:utf8 -*-
import requests
import json
import logging
from bottle import Bottle, run, request, response, get, post

app = Bottle()
watcher = None

class ObjectEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


def start(robot_mgr):
    global watcher
    watcher = robot_mgr
    run(app, host='0.0.0.0', port=8001)


@app.post('/net_command')
def dispatch():
    data = request.forms
    cmd = data.get('cmd', None)
    if cmd and hasattr(watcher, cmd):
        executer = getattr(watcher, cmd)
        ret = executer(data)
    else:
        logging.warning("command %s not found!", cmd)
        ret = 1, "command %s not found!" % cmd
    response.content_type = 'application/json'
    if isinstance(ret, int):
        r = {"status": ret}
    elif isinstance(ret, (list, dict)):
        r = ret
    elif isinstance(ret, tuple):
        r = {"status": ret[0], "err_msg": ret[1]}
    else:
        r = {"status": 1, "err_msg": "unknown error!"}
    return json.dumps(r, cls=ObjectEncoder)
