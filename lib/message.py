#-*- coding:utf8 -*-
import time


class UnknownMessage(object):
    def __init__(self):
        pass


class AliveMessage(object):
    ''' short name for receive message '''
    def __init__(self):
        pass


class FriendMessage(object):
    def __init__(self, sender, nickname, content):
        self.time = int(time.time())
        self.sender = sender
        self.nickname = nickname
        self.content = content


class GroupMessage(object):
    def __init__(self, group, groupname, sender, nickname, content):
        self.time = int(time.time())
        self.group = group
        self.groupname = groupname
        self.sender = sender
        self.nickname = nickname
        self.content = content

