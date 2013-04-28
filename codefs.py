__author__ = 'wynand'

import os
from collections import namedtuple
import tarfile
from path import path
import cStringIO as StringIO
import json

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.filesystems import AbstractedFS, FilesystemError
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.servers import FTPServer


fake_stat = namedtuple("fake_stat", "st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime")


class Base(object):
    is_dir = False

    def __init__(self, parent, obj, name):
        self.parent = parent
        self._obj = obj
        self.name = name

    @property
    def path(self):
        if self.parent is not None:
            return self.parent.path / self.name
        else:
            return path(self.name)

    def stat(self):
        perm = tarfile.S_IFDIR | tarfile.TUREAD | tarfile.TUEXEC \
            if self.is_dir \
            else tarfile.S_IFREG | tarfile.TUREAD
        return fake_stat(st_mode=perm,
                        st_ino=id(self.obj), st_dev=0, st_nlink=1,
                        st_uid=os.getuid(), st_gid=os.getgid(),
                        st_size=1,
                        st_atime=0.0, st_mtime=0.0, st_ctime=0.0)


    def _set_obj(self, new_obj):
        self._obj = new_obj
        self.parent[self.name] = self

    def _get_obj(self):
        return self._obj

    def _del_obj(self):
        del self.parent[self.name]

    obj = property(_get_obj, _set_obj)


class Directory(Base):
    is_dir = True


class BaseBuffer(object):
    def __init__(self, file_obj):
        self.file_obj = file_obj
        self.buf = StringIO.StringIO()

    @property
    def name(self):
        return self.file_obj.name

    def close(self):
        self.buf.close()

    @property
    def closed(self):
        return self.buf.closed


class ReadBuffer(BaseBuffer):
    def __init__(self, file_obj):
        super(ReadBuffer, self).__init__(file_obj)
        self._initialized = False

    def dump(self, obj, fd):
        json.dump(obj, fd)

    def read(self, data):
        if not self._initialized:
            self.dump(self.file_obj.obj, self.buf)
            self.buf.seek(0)
            self._initialized = True
        return self.buf.read(data)


class WriteBuffer(BaseBuffer):
    def load(self, fd):
        return json.load(fd)

    def get_obj(self):
        self.buf.seek(0)
        return self.load(self.buf)

    def write(self, data):
        self.buf.write(data)

    def close(self):
        try:
            self.file_obj.obj = self.get_obj()
        except:
            import traceback
            traceback.print_exc()
        finally:
            self.buf.close()


class ReaderWriter(object):
    def __init__(self, parent, file_obj, buf):
        self.file_obj = file_obj
        self.buf = buf

    @property
    def name(self):
        return self.file_obj.name

    def read(self, data):
        return self.buf.read(data)

    def write(self, data):
        self.buf.write(data)

    def close(self):
        self.buf.close()

    @property
    def closed(self):
        return self.buf.closed


class File(Base):
    ReadBuffer = ReadBuffer
    WriteBuffer = WriteBuffer

    def __init__(self, parent, obj, name):
        super(File, self).__init__(parent, obj, name)

    def open(self, mode):
        if 'r' in mode:
            return self.ReadBuffer(self)
        else:
            return self.WriteBuffer(self)


def make_fs(root_obj):
    class CodeFS(AbstractedFS):
        def __init__(self, root, cmd_channel):
            AbstractedFS.__init__(self, root, cmd_channel)
            self.cwd = root

        def ftp2fs(self, ftppath):
            return self.ftpnorm(ftppath)

        def fs2ftp(self, fspath):
            return fspath

        def validpath(self, path):
            return True

        def isfile(self, path):
            try:
                return not self.navigate(path).is_dir
            except FilesystemError:
                return False

        def isdir(self, path):
            try:
                return self.navigate(path).is_dir
            except FilesystemError:
                return False

        def listdir(self, path):
            return self.navigate(path).listdir()

        def open(self, path, mode):
            return self.navigate(path).open(mode)

        def islink(self, path):
            return False

        def getmtime(self, path):
            return 0.0

        def chdir(self, path):
            """Change the current directory."""
            # note: process cwd will be reset by the caller
            assert isinstance(path, unicode), path
            self._cwd = self.fs2ftp(path)

        def realpath(self, path):
            return self.ftpnorm(path)

        def mkdir(self, path):
            raise FilesystemError("No mkdir for you")

        def rename(self, src, dst):
            raise FilesystemError("No rename for you")

        def remove(self, path):
            raise FilesystemError("No remove for you")

        def rmdir(self, path):
            raise FilesystemError("No rmdir for you")

        def chmod(self, path, mode):
            raise FilesystemError("No chmod for you")

        def mkstemp(self, suffix='', prefix='', dir=None, mode='wb'):
            raise FilesystemError("No mkstemp for you")

        def getsize(self, path):
            raise FilesystemError("Why? Because fuck you, that's why.")

        def readlink(self, path):
            return path

        def lexists(self, path):
            try:
                self.navigate(path)
                return True
            except KeyError:
                return False

        def stat(self, path):
            return self.navigate(path).stat()

        lstat = stat

        def navigate(self, obj_path):
            obj_path = path(obj_path)
            if obj_path.parent == obj_path:
                return root_obj
            item = root_obj
            for component in obj_path.splitall()[1:]:
                try:
                    item = item[component]
                except KeyError:
                    raise FilesystemError("No such file or directory: {0}".format(component))
            return item

    return CodeFS


class Handler(FTPHandler):
    def __init__(self, *args, **kwargs):
        FTPHandler.__init__(self, *args, **kwargs)
        self._available_facts = [fact for fact in self._available_facts
                                 if fact != 'size']


def make_server(root_obj, port, user, password):
    authorizer = DummyAuthorizer()
    authorizer.add_user(user, password, "/", perm="elradfmw")

    handler = Handler
    handler.authorizer = authorizer
    handler.abstracted_fs = make_fs(root_obj)

    return FTPServer(("127.0.0.1", port), Handler)
