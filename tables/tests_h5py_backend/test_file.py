from common import TempFileMixin
import unittest

import numpy as np
import tables as tb


class Record(tb.IsDescription):
    var1 = tb.StringCol(itemsize=4)  # 4-character String
    var2 = tb.IntCol()      # integer
    var3 = tb.Int16Col()    # short integer


class CreateFile(TempFileMixin, unittest.TestCase):

    def test_create_array(self):
        array = self.h5file.create_array(self.root, 'anarray',
                                         [1], "Array title")
        assert array[:] == np.array([1], dtype="int")

    def test_create_table(self):
        table = self.h5file.create_table(self.root, 'atable',
                                         Record, "Table title")
        row = ('abcd', 0, 1)
        table.append([row] * 10)

        assert len(table) == 10

    def test_create_group(self):
        group = self.h5file.create_group(self.root, 'agroup', "Group title")

        assert group._v_pathname in self.h5file


class ReadTable(TempFileMixin, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.table = self.h5file.create_table(self.root, 'atable',
                                              Record, "Table title")
        self.row = (b'abcd', 0, 1)
        self.table.append([self.row] * 10)

    def test_read_all(self):
        readout = self.table[:]
        assert len(readout) == 10
        recarr = np.array([self.row]*10, dtype="S4,i4,i2")
        np.testing.assert_equal(readout['var1'], recarr['f0'])
        for f1, f2 in zip(('f0', 'f1', 'f2'), ('var1', 'var2', 'var3')):
            np.testing.assert_equal(readout[f2], recarr[f1])

    def test_iter(self):
        for row in self.table:
            assert row[:] == self.row

    def test_iterrows(self):
        for row in self.table.iterrows():
            assert row[:] == self.row
