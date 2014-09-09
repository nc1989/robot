#-*- coding:utf8 -*-

import logging
import random
import time
import sys
from threading import Thread


class SendMessage(object):
    def __init__(self, sender, content, timestamp=sys.maxint):
        self.sender = sender
        self.content = content
        self.active = False
        self.timestamp = timestamp


class Team(object):
    def __init__(self, mgr, m1, m2, groups, tasks, group_delay, reply_delay):
        self.mgr = mgr
        self.members = (m1, m2)
        self.group_msg_queue = self.gen_msg_queue(groups, tasks, group_delay,
                                                  reply_delay)
        self.role_map = {'A': m1, 'B': m2}
        self.last_send_time = 0

    def gen_msg_queue(self, groups, tasks, group_delay, reply_delay):
        ret = {g: [] for g in groups}
        g_start_time = int(time.time())  # short for group start time
        for g in groups:
            timestamp = g_start_time
            for t in tasks:
                if t['qq'] not in ('A', 'B'):
                    continue
                ret[g].append(SendMessage(t['qq'], t['content'], timestamp))
                timestamp += random.randint(reply_delay)
            g_start_time += random.randint(group_delay)

        #激活所有group中的第一条消息
        for msgs in ret.itervalues():
            msgs[0].active = True

    def in_team(self, qq1, qq2):
        qqs = (self.members[0].id, self.members[1].id)
        if qqs == (qq1, qq2) or qqs == (qq2, qq1):
            return True
        else:
            return False

    def start(self):
        th = Thread(target=self.run)
        th.setDaemon(True)
        th.start()

    def dismiss(self):
        self.mgr.dismiss_team(self)

    def recv_msg(self, qq, msg):
        u""" 收到一条群消息，如果是任务队列的上一条消息，激活下一条 """
        logging.info("team message: %s, %s", qq, msg.content)
        group = msg.group
        self.group_msg_queue[group].pop(0)
        if not self.group_msg_queue[group]:
            del self.group_msg_queue[group]
            return
        self.group_msg_queue[group][0].active = True

    def reply(self):
        u""" 找到一条已激活且timestamp在当前时间之前的消息，发送 """
        try:
            gid, msg = None
            for g, msgs in self.group_msg_queue.iteritems():
                if msgs[0].active and msg[0].timestamp <= time.time():
                    gid, msg = g, msgs[0]
                    break
            self.role_map[msg.sender].send_group_msg(gid, msg.content)
        except:
            pass

    def finished(self):
        for msgs in self.group_msg_queue.itervalues():
            if msgs:
                return False
        return True

    def run(self):
        try:
            self.send_first_msg()
            while True:
                self.reply()
                if self.finished():
                    logging.info('Team %s,%s job finished', self.members[0].id,
                                 self.members[1].id)
                    break
                time.sleep(3)
        finally:
            self.dismiss()
