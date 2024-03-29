# SPDX-License-Identifier: GPL-3.0-only

import os
import json
from collections import namedtuple
from json import JSONDecodeError

from revvy.functions import bytestr_hash, read_json


class StorageError(Exception):
    pass


class StorageElementNotFoundError(StorageError):
    pass


class IntegrityError(StorageError):
    pass


class StorageInterface:
    def read_metadata(self, filename): raise NotImplementedError
    def write(self, filename, data, metadata=None, md5=None): raise NotImplementedError
    def read(self, filename): raise NotImplementedError


MemoryStorageItem = namedtuple('MemoryStorageItem', ['md5', 'data', 'meta'])


class MemoryStorage(StorageInterface):
    def __init__(self):
        self._entries = {}

    def read_metadata(self, name):
        if name not in self._entries:
            raise StorageElementNotFoundError

        file_entry = self._entries[name]
        return {
            **file_entry.meta,
            'md5':    file_entry.md5,
            'length': len(file_entry.data)
        }

    def write(self, name, data, metadata=None, md5=None):
        if md5 is None:
            md5 = bytestr_hash(data)

        if metadata is None:
            metadata = {}

        self._entries[name] = MemoryStorageItem(md5, data, metadata)

    def read(self, name):
        metadata = self.read_metadata(name)
        data = self._entries[name].data

        if bytestr_hash(data) != metadata['md5']:
            raise IntegrityError('Checksum')
        return data


class FileStorage(StorageInterface):
    """
    Stores files on disk, under the storage_dir directory.

    Stores 2 files for each stored file:
      x.meta: stores md5 and length in json format for the data
      x.data: stores the actual data
    """

    def __init__(self, storage_dir):
        self._storage_dir = storage_dir
        try:
            os.makedirs(self._storage_dir, 0o755, True)
            with open(self._access_file(), "w") as fp:
                fp.write("true")
        except IOError as err:
            print("Invalid storage directory set. Not writable.")
            print(err)
            raise

    def _path(self, filename):
        return os.path.join(self._storage_dir, filename)

    def _access_file(self):
        return self._path("access-test")

    def _storage_file(self, filename):
        return self._path("{}.data".format(filename))

    def _meta_file(self, filename):
        return self._path("{}.meta".format(filename))

    def read_metadata(self, filename):
        try:
            return read_json(self._meta_file(filename))
        except IOError:
            raise StorageElementNotFoundError

    def write(self, filename, data, metadata=None, md5=None):
        if md5 is None:
            md5 = bytestr_hash(data)

        if metadata is None:
            metadata = {}

        metadata["md5"] = md5
        metadata["length"] = len(data)

        with open(self._storage_file(filename), "wb") as data_file, open(self._meta_file(filename), "w") as meta_file:
            data_file.write(data)
            json.dump(metadata, meta_file)

    def read(self, filename):
        try:
            data_file_path = self._storage_file(filename)
            meta_file_path = self._meta_file(filename)
            with open(data_file_path, "rb") as data_file, open(meta_file_path, "r") as meta_file:
                metadata = json.load(meta_file)
                data = data_file.read()
                if len(data) != metadata['length']:
                    raise IntegrityError('Length')
                if bytestr_hash(data) != metadata['md5']:
                    raise IntegrityError('Checksum')
                return data
        except IOError:
            raise StorageElementNotFoundError
        except JSONDecodeError:
            raise IntegrityError('Metadata')
