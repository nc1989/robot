#-*- coding:utf8 -*-

import Queue
import logging
import random
import time
from threading import Thread


class Team(object):
    def __init__(self, mgr, m1, m2, groups, tasks, group_delay, reply_delay):
        self.mgr = mgr
        self.members = (m1, m2)
        self.group_tasks = {}
        for g in groups:
            self.group_tasks[g] = tasks
        self.queue = Queue.Queue(20)
        self.group_delay = group_delay
        self.reply_delay = reply_delay
        self.last_send_time = 0

    def in_team(self, qq1, qq2):
        qqs = (self.members[0].id, self.members[1].id)
        if qqs == (qq1, qq2) or qqs == (qq2, qq1):
            return True
        else:
            return False

    def send_group_msg(self, gid, task):
        for m in self.members:
            if int(task['qq']) == m.id:
                m.send_group_msg(gid, task['content'])
                return 0
        return 1

    def start(self):
        th = Thread(target=self.run)
        th.setDaemon(True)
        th.start()

    def dismiss(self):
        self.mgr.dismiss_team(self)

    def recv_msg(self, qq, msg):
        logging.info("team message: %s, %s", qq, msg.content)
        self.queue.put((qq, msg))

    def send_first_msg(self):
        items = self.group_tasks.items()
        gid, tasks = items[0]
        self.send_group_msg(gid, tasks[0])

        for gid, tasks in items[1:]:
            time.sleep(random.randint(*self.group_delay))
            self.send_group_msg(gid, tasks[0])

    def reply(self, qq, msg):
        group = msg.group
        if group not in self.group_tasks:
            return
        if msg.sender == self.group_tasks[group][0]['qq']:
            #收到的消息的发送者就是上一个任务的发送者，进行回复处理
            task = self.group_tasks[group].pop(0)
            if not self.group_tasks[group]:
                del self.group_tasks[group]
                return
            time.sleep(random.randint(*self.reply_delay))
            self.send_group_msg(group, self.group_tasks[group][0])
        else:
            logging.debug("收到其他群消息：%s, %s", msg.sender, msg.content)

    def finished(self):
        for tasks in self.group_tasks.itervalues():
            if tasks:
                return False
        return True

    def run(self):
        try:
            self.send_first_msg()
            while True:
                qq, msg = self.queue.get()
                self.reply(qq, msg)
                if self.finished():
                    logging.info('Team %s,%s job finished', self.members[0].id,
                                 self.members[1].id)
                    break
        finally:
            self.dismiss()
