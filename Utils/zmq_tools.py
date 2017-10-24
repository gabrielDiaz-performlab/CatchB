﻿'''
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2017  Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
'''


'''
This file contains convenience classes for communication with
the Pupil IPC Backbone.
'''

import logging
import msgpack as serializer
import zmq
from zmq.utils.monitor import recv_monitor_message
# import ujson as serializer # uncomment for json serialization

assert zmq.__version__ > '15.1'


class ZMQ_handler(logging.Handler):
    '''
    A handler that sends log records as serialized strings via zmq
    '''
    def __init__(self, ctx, ipc_pub_url):
        super().__init__()
        self.socket = Msg_Dispatcher(ctx, ipc_pub_url)

    def emit(self, record):
        self.socket.send('logging.{0}'.format(record.levelname.lower()),
                         record.__dict__)


class Msg_Receiver(object):
    '''
    Recv messages on a sub port.
    Not threadsafe. Make a new one for each thread
    __init__ will block until connection is established.
    '''
    def __init__(self, ctx, url, topics=(), block_until_connected=True):
        self.socket = zmq.Socket(ctx, zmq.SUB)
        assert type(topics) != str

        if block_until_connected:
            # connect node and block until a connecetion has been made
            monitor = self.socket.get_monitor_socket()
            self.socket.connect(url)
            while True:
                status = recv_monitor_message(monitor)
                if status['event'] == zmq.EVENT_CONNECTED:
                    break
                elif status['event'] == zmq.EVENT_CONNECT_DELAYED:
                    pass
                else:
                    raise Exception("ZMQ connection failed")
            self.socket.disable_monitor()
        else:
            self.socket.connect(url)

        for t in topics:
            self.subscribe(t)

    def subscribe(self, topic):
        self.socket.subscribe(topic)

    def unsubscribe(self, topic):
        self.socket.unsubscribe(topic)

    def recv(self):
        '''Recv a message with topic, payload.

        Topic is a utf-8 encoded string. Returned as unicode object.
        Payload is a msgpack serialized dict. Returned as a python dict.

        Any addional message frames will be added as a list
        in the payload dict with key: '__raw_data__' .
        '''
        topic = self.socket.recv_string()
        payload = serializer.loads(self.socket.recv(), encoding='utf-8')
        extra_frames = []
        while self.socket.get(zmq.RCVMORE):
            extra_frames.append(self.socket.recv())
        if extra_frames:
            payload['__raw_data__'] = extra_frames
        return topic, payload

    @property
    def new_data(self):
        return self.socket.get(zmq.EVENTS)

    def __del__(self):
        self.socket.close()


class Msg_Streamer(object):
    '''
    Send messages on fast and efficiat but without garatees.
    Not threadsave. Make a new one for each thread
    '''
    def __init__(self, ctx, url):
        self.socket = zmq.Socket(ctx, zmq.PUB)
        self.socket.connect(url)

    def send(self, topic, payload):
        '''Send a message with topic, payload
`
        Topic is a unicode string. It will be sent as utf-8 encoded byte array.
        Payload is a python dict. It will be sent as a msgpack serialized dict.

        If payload has the key '__raw_data__'
        we pop if of the payload and send its raw contents as extra frames
        everything else need to be serializable
        the contents of the iterable in '__raw_data__'
        require exposing the pyhton memoryview interface.
        '''
        if '__raw_data__' not in payload:
            self.socket.send_string(topic, flags=zmq.SNDMORE)
            self.socket.send(serializer.dumps(payload, use_bin_type=True))
        else:
            extra_frames = payload.pop('__raw_data__')
            assert(isinstance(extra_frames, (list, tuple)))
            self.socket.send_string(topic, flags=zmq.SNDMORE)
            self.socket.send(serializer.dumps(payload), flags=zmq.SNDMORE)
            for frame in extra_frames[:-1]:
                self.socket.send(frame, flags=zmq.SNDMORE, copy=True)
            self.socket.send(extra_frames[-1], copy=True)

    def __del__(self):
        self.socket.close()


class Msg_Dispatcher(Msg_Streamer):
    '''
    Send messages with delivery guarantee.
    Not threadsafe. Make a new one for each thread.
    '''
    def __init__(self, ctx, url):
        self.socket = zmq.Socket(ctx, zmq.PUSH)
        self.socket.connect(url)

    def notify(self, notification):
        '''Send a pupil notification.
        see plugin.notify_all for documentation on notifications.
        '''
        if notification.get('remote_notify'):
            self.send("remote_notify.{}".format(notification['subject']),
                      notification)
        elif notification.get('delay', 0):
            self.send("delayed_notify.{}".format(notification['subject']),
                      notification)
        else:
            self.send("notify.{}".format(notification['subject']),
                      notification)
