__author__ = 'wynand'

import codefs
import numpy as np


class CSVReadBuffer(codefs.ReadBuffer):
    def __init__(self, file_obj):
        super(CSVReadBuffer, self).__init__(file_obj)
        self.row_index = 0

    def read(self, num_bytes):
        self.buf.seek(0)
        array = self.file_obj.obj
        num_rows, num_cols = array.shape
        new_row_index = min(self.row_index + 10000, num_rows)
        np.savetxt(self.buf, array[self.row_index:new_row_index], fmt='%.18g', delimiter=',')
        self.row_index = new_row_index
        bytes_written = self.buf.tell()
        self.buf.seek(0)
        return self.buf.read(bytes_written)


class CSVWriteBuffer(codefs.WriteBuffer):
    def load(self, fd):
        return np.genfromtxt(fd, delimiter=',')


class CSVFile(codefs.File):
    ReadBuffer = CSVReadBuffer
    WriteBuffer = CSVWriteBuffer
