#-*- coding:utf8 -*-


class MessagePool(object):
    def __init__(self):
        self.msg = {}

    def pop(self, id):
        return self.msg.pop(id, None)

    def add(self, id, msg):
        if id not in self.msg:
            self.msg[id] = []
        self.msg[id].append(msg)

    def iterids(self):
        return self.msg.iterkeys()

    def size(self):
        return sum(len(v) for v in self.msg.itervalues())
