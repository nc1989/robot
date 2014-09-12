#!/usr/bin/env python
#-*- coding:utf8 -*-

import os
import sys
import time
import logging
import json
from lib import qqplus
from lib.robot import Robot
from lib import net_command
from lib.message import GroupMessage
from lib.team import Team


# decorator for net command executer
def check_qq(func):
    def new_func(self, data):
        qq = int(data.get('qq', None))
        if qq not in self.robot_pool:
            logging.warning("QQ %s not in robot pool!", qq)
            return 1, "QQ %s not in robot pool!" % qq
        elif not self.robot_pool[qq].isalive():
            logging.warning("QQ %s is not alive!", qq)
            return 1, "QQ %s is not alive!" % qq
        else:
            return func(self, data)
    return new_func


class RobotManager(object):
    def __init__(self, config):
        self.robot_pool = {}
        self.teams = []
        self.init(config)

    def init(self, config):
        if not os.path.isfile(config):
            logging.error("File %s do not exist!", config)
            sys.exit(1)
        with open(config) as ifd:
            for line in ifd:
                if line.startswith('#'):
                    continue
                qq, host, port = line.strip().split()[:3]
                self.robot_pool[int(qq)] = Robot(int(qq), host, int(port))

    def start(self):
        qqplus.start(self.recv_msg, self.get_msg)
        net_command.start(self)

    def recv_msg(self, qq, msg):
        #如果是群消息，要做一些特殊处理
        #比如：
        #1. 配对工作的时候，机器人的消息要交给队友处理
        #2. 非配对工作的时候，自己机器人发的群消息，不需要交给其他人处理
        if isinstance(msg, GroupMessage):
            if qq == msg.sender:
                #忽略自己发的群消息
                return
            team = None
            for tm in self.teams:
                if tm.is_team(qq, msg.sender):
                    team = tm
                    break
            if team:
                team.recv_msg(qq, msg)
                return

            if msg.sender in self.robot_pool:
                return

        if qq not in self.robot_pool:
            logging.warning("QQ %s not in robot pool!", qq)
            return
        self.robot_pool[qq].recv_msg(msg)

    def get_msg(self, qq):
        return None

    def dismiss_team(self, team):
        self.teams.remove(team)

    def in_team(self, qq):
        for t in self.teams:
            if t.in_team(qq):
                return True
        return False

    # net command executer
    @check_qq
    def login(self, data):
        qq = int(data.get('qq', None))
        if self.robot_pool[qq].isalive():
            return 0
        else:
            return 1, "QQ %s is not alive" % qq

    @check_qq
    def send_friend_msg(self, data):
        qq = int(data.get('qq', None))
        fid = data.get('id', None)
        msg = data.get('msg', None)
        if fid and msg:
            self.robot_pool[qq].send_friend_msg(fid, msg)
            return 0
        else:
            logging.warning("id %s or msg %s is empty", fid, msg)
            return 1, "fid %s or msg %s is empty" % (fid, msg)

    @check_qq
    def send_friends_msg(self, data):
        qq = int(data.get('qq', None))
        delay_min = int(data.get('delay_min', 3))
        delay_max = int(data.get('delay_max', 9))
        msg = data.get('msg', None)
        fids = data.get('fids', None)
        if fids:
            fids = fids.split(',')
        if msg:
            self.robot_pool[qq].send_friends_msg(msg, fids,
                                                 (delay_min, delay_max))
            return 0
        else:
            logging.warning("msg is empty")
            return 1, "msg is empty"

    @check_qq
    def send_group_msg(self, data):
        qq = int(data.get('qq', None))
        gid = data.get('id', None)
        msg = data.get('msg', None)
        if gid and msg:
            self.robot_pool[qq].send_group_msg(gid, msg)
            return 0
        else:
            logging.warning("id %s or msg %s is empty", gid, msg)
            return 1, "fid %s or msg %s is empty" % (gid, msg)

    @check_qq
    def send_groups_msg(self, data):
        qq = int(data.get('qq', None))
        delay_min = int(data.get('delay_min', 20))
        delay_max = int(data.get('delay_max', 40))
        msgs = data.get('msgs', None)
        gids = data.get('gids', None)
        if gids:
            gids = gids.split(',')
        else:
            gids = self.robot_pool[qq].get_groups()

        conflict_qqs = data.get('conflict_qqs', [])
        if conflict_qqs:
            conflict_qqs = [int(q) for q in conflict_qqs.split(',')]
            conflict_groups = set()
            for q in conflict_qqs:
                if q in self.robot_pool:
                    if q == qq:
                        continue
                    groups = self.robot_pool[q].get_groups()
                    conflict_groups = conflict_groups.union(groups)
            gids = [g for g in gids if g not in conflict_groups]

        if msgs:
            msgs = msgs.split(',')
            self.robot_pool[qq].send_groups_msg(msgs, gids,
                                                (delay_min, delay_max))
            return 0
        else:
            logging.warning("msg is empty")
            return 1, "msg is empty"

    def set_keywords(self, data):
        qqs = data.get('qqs', '')
        kws = data.get('kws', '')
        logging.debug('set keywords: %s for: %s', kws, qqs)
        if qqs == '':
            return 1, "qqs is empty"
        if kws:
            kwl = kws.split(',')
        else:
            kwl = []
        qq_list = qqs.split(',')
        for qq in qq_list:
            if not qq.isdigit():
                logging.warning('QQ %s is not number', qq)
                continue
            qq = int(qq)
            if qq in self.robot_pool:
                self.robot_pool[qq].set_keywords(kwl)
        return 0

    def get_status(self, data):
        qqs = data.get('qqs', '')
        logging.debug('get status for: %s', qqs)
        if qqs == '':
            return 1, 'qqs is empty'
        qq_list = qqs.split(',')
        ret = []
        for qq in qq_list:
            if not qq.isdigit():
                logging.warning('QQ %s is not number', qq)
                continue
            qq = int(qq)
            if qq not in self.robot_pool:
                continue
            d = {
                'qq': qq,
                'nick': self.robot_pool[qq].nickname,
                'status': int(not self.robot_pool[qq].isalive()),
            }
            ret.append(d)
        return ret

    def get_friend_msg(self, data):
        qqs = data.get('qqs', None)
        if not qqs:
            return 1, "qqs is empty"
        msgs = []
        for qq in qqs.split(','):
            if not qq.isdigit():
                logging.warning('QQ %s is not number', qq)
                continue
            qq = int(qq)
            if qq in self.robot_pool:
                msgs.append(self.robot_pool[qq].get_friend_msg())
        return msgs

    def get_group_msg(self, data):
        qqs = data.get('qqs', None)
        if not qqs:
            return 1, "qqs is empty"
        msgs = []
        for qq in qqs.split(','):
            if not qq.isdigit():
                logging.warning('QQ %s is not number', qq)
                continue
            qq = int(qq)
            if qq in self.robot_pool:
                msgs.append(self.robot_pool[qq].get_group_msg())
        return msgs

    def team_work(self, data):
        qqs = data.get('qqs', None)
        groups = data.get('groups', None)
        if not qqs or not groups:
            return 1, "qqs or groups is empty"
        qq1, qq2 = [int(q) for q in qqs.split(',')[:2]]
        groups = [int(g) for g in groups.split(',')]
        if qq1 not in self.robot_pool or \
           qq2 not in self.robot_pool:
            return 1, "some one qq not in robot pool"

        if self.in_team(qq1) or self.in_team(qq2):
            return 1, "at least one qq already in a team"
        tasks = json.loads(data.get('tasks', '[]'))
        if not tasks:
            return 1, "empty tasks"
        group_delay = (int(data.get('group_delay_min', 20)),
                       int(data.get('group_delay_max', 40)))
        reply_delay = (int(data.get('reply_delay_min', 10)),
                       int(data.get('reply_delay_max', 20)))
        qq1 = self.robot_pool[qq1]
        qq2 = self.robot_pool[qq2]
        t = Team(self, qq1, qq2, groups, tasks, group_delay, reply_delay)
        self.teams.append(t)
        t.start()
        return 0

    def get_common_groups(self, data):
        qqs = data.get('qqs', None)
        if not qqs:
            return 1, "qqs is empty"
        qq1, qq2 = [int(q) for q in qqs.split(',')[:2]]
        if qq1 not in self.robot_pool or \
           qq2 not in self.robot_pool:
            return 1, "some one qq not in robot pool"
        return self.robot_pool[qq1].get_common_groups(self.robot_pool[qq2])

    def make_teams(self, data):
        qqs = data.get('qqs', None)
        if not qqs:
            return 1, "qqs is empty"
        qqs = [int(qq) for qq in qqs.split(',') if int(qq) in self.robot_pool]
        ret = []
        while True:
            if len(qqs) < 2:
                break
            qq1 = qqs.pop(0)
            groups, index = [], 0  # max group number
            for i, qq in enumerate(qqs):
                grps = self.robot_pool[qq1].get_common_groups(
                    self.robot_pool[qq])
                if len(grps) > len(groups):
                    groups = grps
                    index = i
            d = {
                'qq1': qq1,
                'qq2': qqs.pop(index),
                'groups': groups,
            }
            ret.append(d)
        return ret

    def get_teams(self, data):
        ret = [{'qq1': t.members[0].id, 'qq2': t.members[1].id}
               for t in self.teams]
        return ret

if __name__ == '__main__':
    #设置log输出文件名、格式
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S',
        filename='mgr.log',
        filemode='w')

    #设置屏幕log输出
    #console = logging.StreamHandler()
    #console.setLevel(logging.INFO)
    #formatter = logging.Formatter(
    #    '%(asctime)s %(levelname)-8s %(message)s',
    #    datefmt='%m-%d %H:%M:%S')
    #console.setFormatter(formatter)
    #logging.getLogger('').addHandler(console)

    #启动robot manager
    robot_mgr = RobotManager('./robot_list')
    robot_mgr.start()
