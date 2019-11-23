# SPDX-License-Identifier: GPL-3.0-only

import collections
import hashlib
from json import JSONDecodeError
from revvy.file_storage import StorageInterface, StorageError


def hexdigest2bytes(hexdigest):
    """
    >>> hexdigest2bytes("aabbcc")
    b'\\xaa\\xbb\\xcc'
    >>> hexdigest2bytes("ABCDEF")
    b'\\xab\\xcd\\xef'
    >>> hexdigest2bytes("ABCD0F")
    b'\\xab\\xcd\\x0f'
    """
    return b"".join([int(hexdigest[i:i + 2], 16).to_bytes(1, byteorder="big") for i in range(0, len(hexdigest), 2)])


def bytes2hexdigest(hash_bytes):
    """
    >>> bytes2hexdigest(b'\\xaa\\xbb\\xcc')
    'aabbcc'
    >>> bytes2hexdigest(b'\\xAB\\xCD\\xEF')
    'abcdef'
    >>> bytes2hexdigest(b'\\xAB\\xCD\\x0F')
    'abcd0f'
    """
    return "".join(['{0:0>2x}'.format(byte) for byte in hash_bytes])


LongMessageStatusInfo = collections.namedtuple('LongMessageStatusInfo', ['status', 'md5', 'length'])


class LongMessageStatus:
    UNUSED = 0
    UPLOAD = 1
    VALIDATION = 2
    READY = 3
    VALIDATION_ERROR = 4


class LongMessageType:
    FIRMWARE_DATA = 1
    FRAMEWORK_DATA = 2
    CONFIGURATION_DATA = 3
    TEST_KIT = 4
    MAX = 5

    PermanentMessages = [FIRMWARE_DATA, FRAMEWORK_DATA]

    @staticmethod
    def validate(long_message_type):
        if not (0 < long_message_type < LongMessageType.MAX):
            raise LongMessageError("Invalid long message type {}".format(long_message_type))


class MessageType:
    SELECT_LONG_MESSAGE_TYPE = 0
    INIT_TRANSFER = 1
    UPLOAD_MESSAGE = 2
    FINALIZE_MESSAGE = 3


class LongMessageError(Exception):
    def __init__(self, message):
        self.message = message


class LongMessageStorage:
    """Store long messages using the given storage class, with extra validation"""

    def __init__(self, storage: StorageInterface, temp_storage: StorageInterface):
        self._storage = storage
        self._temp_storage = temp_storage

    def _get_storage(self, message_type):
        return self._storage if message_type in LongMessageType.PermanentMessages else self._temp_storage

    def read_status(self, long_message_type):
        """Return status with triplet of (LongMessageStatus, md5-hexdigest, length). Last two fields might be None)."""
        print("LongMessageStorage:read_status")
        LongMessageType.validate(long_message_type)
        try:
            storage = self._get_storage(long_message_type)
            data = storage.read_metadata(long_message_type)
            return LongMessageStatusInfo(LongMessageStatus.READY, data['md5'], data['length'])
        except (StorageError, JSONDecodeError):
            return LongMessageStatusInfo(LongMessageStatus.UNUSED, None, None)

    def set_long_message(self, long_message_type, data, md5):
        print("LongMessageStorage:set_long_message")
        LongMessageType.validate(long_message_type)
        storage = self._get_storage(long_message_type)
        storage.write(long_message_type, data, md5=md5)

    def get_long_message(self, long_message_type):
        print("LongMessageStorage:get_long_message")
        storage = self._get_storage(long_message_type)
        return storage.read(long_message_type)


class LongMessageAggregator:
    """Helper class for building long messages"""

    def __init__(self, md5):
        self.md5 = md5
        self.data = bytearray()
        self._md5calc = hashlib.md5()

    def append_data(self, data):
        self.data += data
        self._md5calc.update(data)

    def finalize(self):
        """Returns true if the uploaded data matches the predefined md5 checksum."""
        md5computed = self._md5calc.hexdigest()

        return md5computed == self.md5


class LongMessageHandler:
    """Implements the long message writer/status reader protocol"""

    def __init__(self, long_message_storage):
        self._long_message_storage = long_message_storage
        self._long_message_type = None
        self._status = "READ"
        self._aggregator = None
        self._callback = lambda x, y: None
        self._upload_started_callback = lambda mt: None
        self._upload_finished_callback = lambda mt: None

    def on_message_updated(self, callback):
        self._callback = callback

    def on_upload_started(self, callback):
        self._upload_started_callback = callback

    def on_upload_finished(self, callback):
        self._upload_finished_callback = callback

    def read_status(self):
        print("LongMessageHandler:read_status")
        if self._long_message_type is None:
            return LongMessageStatusInfo(LongMessageStatus.UNUSED, None, None)
        if self._status == "READ":
            return self._long_message_storage.read_status(self._long_message_type)
        if self._status == "INVALID":
            return LongMessageStatusInfo(LongMessageStatus.VALIDATION_ERROR, None, None)
        assert self._status == "WRITE"
        return LongMessageStatusInfo(LongMessageStatus.UPLOAD, self._aggregator.md5, len(self._aggregator.data))

    def select_long_message_type(self, long_message_type):
        if self._status == "WRITE":
            self._upload_finished_callback(long_message_type)

        print("LongMessageHandler:select_long_message_type")
        LongMessageType.validate(long_message_type)
        self._long_message_type = long_message_type
        self._status = "READ"

    def init_transfer(self, md5):
        print("LongMessageHandler:init_transfer")

        if self._status == "WRITE":
            self._upload_finished_callback(self._long_message_type)

        if self._long_message_type is None:
            raise LongMessageError("init-transfer needs to be called after select_long_message_type")
        self._status = "WRITE"
        self._aggregator = LongMessageAggregator(md5)
        self._upload_started_callback(self._long_message_type)

    def upload_message(self, data):
        print("LongMessageHandler:upload_message")
        if self._status != "WRITE":
            raise LongMessageError("init-transfer needs to be called before upload_message")
        self._aggregator.append_data(data)

    def finalize_message(self):
        print("LongMessageHandler:finalize_message")

        if self._status == "READ":
            # shortcut that activates a message which is already on the robot
            if self._long_message_type is None:
                raise LongMessageError("init-transfer needs to be called before finalize_message")
            # observer must take care of verifying that there is actually a message
            self._callback(self._long_message_storage, self._long_message_type)

        elif self._status == "WRITE":
            self._upload_finished_callback(self._long_message_type)
            if self._aggregator.finalize():
                self._long_message_storage.set_long_message(self._long_message_type, self._aggregator.data,
                                                            self._aggregator.md5)
                self._callback(self._long_message_storage, self._long_message_type)
                self._status = "READ"
            else:
                self._status = "INVALID"

        else:
            # INVALID status, finalize does nothing
            pass


class LongMessageProtocol:
    RESULT_SUCCESS = 0
    RESULT_INVALID_ATTRIBUTE_LENGTH = 1
    RESULT_UNLIKELY_ERROR = 2

    def __init__(self, handler: LongMessageHandler):
        self._handler = handler

    def handle_read(self):
        try:
            status = self._handler.read_status()
            value = status.status.to_bytes(1, byteorder="big")
            if status.md5 is not None:
                value += hexdigest2bytes(status.md5)
                value += status.length.to_bytes(4, byteorder="big")

            return value
        except (IOError, TypeError, JSONDecodeError):
            raise LongMessageError('Could not read long message')

    def handle_write(self, header, data):
        if header == MessageType.SELECT_LONG_MESSAGE_TYPE:
            if len(data) == 1:
                self._handler.select_long_message_type(data[0])
                result = LongMessageProtocol.RESULT_SUCCESS
            else:
                result = LongMessageProtocol.RESULT_INVALID_ATTRIBUTE_LENGTH

        elif header == MessageType.INIT_TRANSFER:
            if len(data) == 16:
                self._handler.init_transfer(bytes2hexdigest(data[0:16]))
                result = LongMessageProtocol.RESULT_SUCCESS
            else:
                result = LongMessageProtocol.RESULT_INVALID_ATTRIBUTE_LENGTH

        elif header == MessageType.UPLOAD_MESSAGE:
            if len(data) > 1:
                self._handler.upload_message(data)
                result = LongMessageProtocol.RESULT_SUCCESS
            else:
                result = LongMessageProtocol.RESULT_INVALID_ATTRIBUTE_LENGTH

        elif header == MessageType.FINALIZE_MESSAGE:
            if len(data) == 0:
                self._handler.finalize_message()
                result = LongMessageProtocol.RESULT_SUCCESS
            else:
                result = LongMessageProtocol.RESULT_INVALID_ATTRIBUTE_LENGTH

        else:
            result = LongMessageProtocol.RESULT_UNLIKELY_ERROR

        return result
