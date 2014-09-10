#-*- coding:utf8 -*-
import requests
import json
import time
import random
import logging
from lib.message import *
from lib.message_pool import MessagePool

MSG_POST_URL = 'http://192.168.217.190:8000/robot/publish_msg_2_node'


class Robot(object):
    def __init__(self, id, host, port):
        self.id = id
        self.url = "http://{0}/qqplus{1}/?key=abc123&a=<%26%26>".format(
            host, port)
        self.nickname = self._get_nickname()
        self.groups = self._get_groups()
        self.friends = self._get_friends()
        self.last_active = time.time()
        self.msg_handlers = {
            FriendMessage: self.friend_msg_handler,
            GroupMessage: self.group_msg_handler,
            AliveMessage: self.alive_msg_handler,
            UnknownMessage: self.unknown_msg_handler,
        }
        self.friend_msg_pool = MessagePool()  # TODO:设定大小
        self.group_msg_pool = MessagePool()  # TODO:设定大小
        self.kwl = []

    def _get_friends(self):
        url = "{0}<%26%26>GetFriends".format(self.url)
        res = json.loads(requests.get(url).content)
        if res['desc'] != 'ok':
            logging.warning("GetFriends command failed!")
        result = res['result']
        ret = []
        if len(result) > 0:
            for r in result[0]:
                ret.append((r['QQ'], r['NickName'], r['Remark']))
        return ret

    def _get_groups(self):
        url = "{0}<%26%26>GetClusters".format(self.url)
        res = json.loads(requests.get(url).content)
        if res['desc'] != 'ok':
            logging.warning("GetClusters command failed!")
        result = res['result']
        ret = {}
        if len(result) > 0:
            for r in result[0]:
                ret[int(r['ExternalId'])] = r['Name']
        return ret

    def has_group(self, gid):
        return gid in self.groups

    @staticmethod
    def _encode_msg(msg):
        if isinstance(msg, unicode):
            msg = msg.encode('gbk')
        else:
            msg = msg.decode('utf8').encode('gbk')
        return msg

    def _get_nickname(self):
        url = "{0}GetClusters".format(self.url)
        ret = requests.get(url)
        res = json.loads(ret.content)
        if res['desc'] != 'ok':
            logging.warning("GetClusters command failed!")
        result = res['result']
        if len(result) > 0 and len(result[0]) > 0:
            members = result[0][0]['members']
            for m in members:
                if m['QQ'] == self.id:
                    return m['Nick']

    def send_friend_msg(self, fid, msg):
        url = "{0}SendMessage<%26>{1}<%26>{2}".format(
            self.url, fid, self._encode_msg(msg))
        logging.debug("SEND MSG TO: %s", url)
        requests.get(url)

    def send_group_msg(self, gid, msg):
        url = "{0}SendClusterMessage<%26>{1}<%26>{2}".format(
            self.url, gid, self._encode_msg(msg))
        logging.debug("SEND GROUP MSG TO: %s", url)
        requests.get(url)

    def _do_send_friends_msg(self, msg, fids, delay_range):
        if not fids:
            fids = [f[0] for f in self.friends]

        for fid in fids:
            self.send_friend_msg(fid, msg)
            time.sleep(random.randint(*delay_range))

    def send_friends_msg(self, msg, fids, delay_range):
        th = Thread(target=self._do_send_friends_msg,
                    args=(msg, fids, delay_range))
        th.setDaemon(True)
        th.start()

    def _do_send_groups_msg(self, msg, gids, delay_range):
        if not gids:
            gids = [g for g in self.groups.iterkeys()]

        if isinstance(msg, list):
            for gid in gids:
                self.send_group_msg(gid, random.choice(msg))
                time.sleep(random.randint(*delay_range))
        else:
            for gid in gids:
                self.send_group_msg(gid, msg)
                time.sleep(random.randint(*delay_range))

    def send_groups_msg(self, msg, gids, delay_range):
        th = Thread(target=self._do_send_groups_msg,
                    args=(msg, gids, delay_range))
        th.setDaemon(True)
        th.start()

    def set_keywords(self, kwl):
        self.kwl = kwl

    def get_common_groups(self, another):
        groups1 = set(self.groups.iterkeys())
        groups2 = set(another.groups.iterkeys())
        groups = groups1.intersection(groups2)
        return [{'group': g, 'groupname': self.groups[g]} for g in groups]

    def _update_status(self):
        logging.debug('QQ: %s 还活着，请大人放心', self.id)
        self.last_active = time.time()

    def isalive(self):
        #三分钟内收到过alive消息认为该qq状态是alive
        return (time.time() - self.last_active) < 180

    def update_msg_number(self):
        #通知web，有好友、群消息数目有更新
        data = {
            'qq': self.id,
            'fmsgn': self.friend_msg_pool.size(),
            'gmsgn': self.group_msg_pool.size(),
        }
        requests.post(MSG_POST_URL, data=data)

    def friend_msg_handler(self, msg):
        logging.debug('QQ: %s, 收到好友<%s(%s)>的消息: %s',
                      self.id, msg.nickname, msg.sender, msg.content)
        self.friend_msg_pool.add(msg.sender, msg)
        self.update_msg_number()

    def group_msg_handler(self, msg):
        logging.debug('QQ: %s, 收到群<%s(%s)>中<%s(%s)>发的消息: %s',
                      self.id, msg.groupname, msg.group, msg.nickname,
                      msg.sender, msg.content)
        for kw in self.kwl:
            if msg.content.find(kw) >= 0:
                logging.info("命中kw!!!")
                self.group_msg_pool.add(msg.group, msg)
                self.update_msg_number()
                break

    def alive_msg_handler(self, msg):
        self._update_status()

    def unknown_msg_handler(self, msg):
        logging.dbug('报告大人，QQ: %s收到无法解析的三体人消息', self.id)

    def recv_msg(self, msg):
        self.msg_handlers[msg.__class__](msg)

    def get_friend_msg(self):
        ret = {"qq": self.id, "nick": self.nickname, 'msg': []}
        ids = [i for i in self.friend_msg_pool.iterids()]
        for id in ids:
            msgs = self.friend_msg_pool.pop(id)
            if not msgs:
                continue
            d = {
                'sender': msgs[0].sender,
                'nick': msgs[0].nickname,
                'msg': [],
            }
            for m in msgs:
                d['msg'].append({'time': m.time, 'content': m.content})
            ret['msg'].append(d)
        self.update_msg_number()
        return ret

    def get_group_msg(self):
        ret = {"qq": self.id, "nick": self.nickname, 'msg': []}
        ids = [i for i in self.group_msg_pool.iterids()]
        for id in ids:
            msgs = self.group_msg_pool.pop(id)
            if not msgs:
                continue
            d = {
                'sender': msgs[0].sender,
                'nick': msgs[0].nickname,
                'group': msgs[0].group,
                'groupname': msgs[0].groupname,
                'msg': [],
            }
            for m in msgs:
                d['msg'].append({'time': m.time, 'content': m.content})
            ret['msg'].append(d)
        self.update_msg_number()
        return ret

if __name__ == '__main__':
    r = Robot(2195356784, '10.128.39.41', 8080)
    r.send_friend_msg(2035322454, '今天晚上去哪玩呢？')
    time.sleep(3)
    r.send_group_msg(247501737, '今天晚上去哪玩呢？')
