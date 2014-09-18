#-*- coding:utf8 -*-

import logging
import random
import time
import sys
from threading import Thread

G_MSG_DELAY = 10


class SendMessage(object):
    def __init__(self, sender, content, timestamp=sys.maxint):
        self.pre_msg = None
        self.sender = sender
        self.content = content
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
                timestamp += random.randint(*reply_delay)
            g_start_time += random.randint(*group_delay)

        #激活所有group中的第一条消息，设置所有消息的pre_msg
        for msgs in ret.itervalues():
            for idx, msg in enumerate(msgs):
                if idx == 0:
                    continue
                msg.pre_msg = msgs[idx - 1].content
        return ret

    def is_team(self, qq1, qq2):
        qqs = (self.members[0].id, self.members[1].id)
        if qqs == (qq1, qq2) or qqs == (qq2, qq1):
            return True
        else:
            return False

    def in_team(self, qq):
        return qq in (self.members[0].id, self.members[1].id)

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
        if group not in self.group_msg_queue:
            logging.warn("group %s not in group_msg_queue!", group)
            return

        if not self.group_msg_queue[group]:
            logging.info("group %s 收到最后一条消息", group)
            return
        msg_expect = self.group_msg_queue[group][0].pre_msg
        msg_recv = msg.content
        if isinstance(msg_expect, unicode):
            msg_expect = msg_expect.encode('utf8')
        if isinstance(msg_recv, unicode):
            msg_recv = msg_recv.encode('utf8')
        if msg_expect != msg_recv:
            logging.warn("收到消息和期待消息不一致: %s != %s",
                         msg_expect, msg_recv)
            return

        self.group_msg_queue[group][0].pre_msg = None

    def get_tasks():
        return self.group_msg_queue

    def reply(self):
        u""" 找到一条已激活且timestamp在当前时间之前的消息，发送 """
        try:
            gid, msg = None, None
            for g, msgs in self.group_msg_queue.iteritems():
                if msgs[0].pre_msg is None and \
                   msgs[0].timestamp <= time.time():
                    gid, msg = g, msgs.pop(0)
                    break
            if gid and msg and self.last_send_time + G_MSG_DELAY < time.time():
                self.role_map[msg.sender].send_group_msg(gid, msg.content)
                self.last_send_time = time.time()
        except:
            pass

    def finished(self):
        for msgs in self.group_msg_queue.itervalues():
            if msgs:
                return False
        return True

    def run(self):
        try:
            while True:
                self.reply()
                if self.finished():
                    logging.info('Team %s,%s job finished', self.members[0].id,
                                 self.members[1].id)
                    break
                time.sleep(3)
        finally:
            self.dismiss()
