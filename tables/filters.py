"""
Functionality related with filters in a PyTables file.

:Author: Ivan Vilata i Balaguer
:Contact: ivilata at carabos dot com
:License: BSD
:Created: 2007-02-23
:Revision: $Id$

Variables
=========

`__docformat`__
    The format of documentation strings in this module.
`__version__`
    Repository version of this file.
`all_complibs`
    List of all compression libraries.
`default_complib`
    The default compression library.
"""

# Imports
# =======
import warnings
import numpy
from tables import utilsExtension


# Public variables
# ================
__docformat__ = 'reStructuredText'
"""The format of documentation strings in this module."""

__version__ = '$Revision$'
"""Repository version of this file."""

all_complibs = ['zlib', 'lzo', 'bzip2']
"""List of all compression libraries."""

default_complib = 'zlib'
"""The default compression library."""


# Private variables
# =================
_shuffle_flag = 0x1
_fletcher32_flag = 0x2


# Classes
# =======
class Filters(object):
    """
    Container for filter properties.

    Instance variables:

    `complevel`
        The compression level (0 disables compression).
    `complib`
        The compression filter used (irrelevant when compression is
        not enabled).
    `shuffle`
        Whether the *Shuffle* filter is active or not.
    `fletcher32`
        Whether the *Fletcher32* filter is active or not.
    """

    @classmethod
    def _from_leaf(class_, leaf):
        # Get a dictionary with all the filters
        filtersDict = utilsExtension.getFilters( leaf._v_parent._v_objectID,
                                                 leaf._v_hdf5name )
        if filtersDict is None:
            filtersDict = {}  # not chunked

        kwargs = dict(complevel=0, shuffle=False, fletcher32=False)  # all off
        for (name, values) in filtersDict.items():
            if name == 'deflate':
                name = 'zlib'
            if name in all_complibs:
                kwargs['complib'] = name
                kwargs['complevel'] = values[0]
            elif name in ['shuffle', 'fletcher32']:
                kwargs[name] = True
        return class_(**kwargs)

    @classmethod
    def _unpack(class_, packed):
        """
        Create a new `Filters` object from a packed version.

        >>> Filters._unpack(0)
        Filters(complevel=0, shuffle=False, fletcher32=False)
        >>> Filters._unpack(0x101)
        Filters(complevel=1, complib='zlib', shuffle=False, fletcher32=False)
        >>> Filters._unpack(0x30309)
        Filters(complevel=9, complib='bzip2', shuffle=True, fletcher32=True)
        >>> Filters._unpack(0x3030A)
        Traceback (most recent call last):
          ...
        ValueError: compression level must be between 0 and 9
        >>> Filters._unpack(0x1)
        Traceback (most recent call last):
          ...
        ValueError: invalid compression library id: 0
        """
        kwargs = {}
        # Byte 0: compression level.
        kwargs['complevel'] = complevel = packed & 0xff
        packed >>= 8
        # Byte 1: compression library id (0 for none).
        if complevel > 0:
            complib_id = int(packed & 0xff)
            if not (0 < complib_id <= len(all_complibs)):
                raise ValueError( "invalid compression library id: %d"
                                  % complib_id )
            kwargs['complib'] = all_complibs[complib_id - 1]
        packed >>= 8
        # Byte 2: parameterless filters.
        kwargs['shuffle'] = packed & _shuffle_flag
        kwargs['fletcher32'] = packed & _fletcher32_flag
        return class_(**kwargs)

    def _pack(self):
        """
        Pack the `Filters` object into a 64-bit NumPy integer.

        >>> type(Filters()._pack())
        <type 'numpy.int64'>
        >>> hex(Filters()._pack())
        '0x0'
        >>> hex(Filters(1, shuffle=False)._pack())
        '0x101'
        >>> hex(Filters(9, 'bzip2', shuffle=True, fletcher32=True)._pack())
        '0x30309'
        """
        packed = numpy.int64(0)
        # Byte 2: parameterless filters.
        if self.shuffle:
            packed |= _shuffle_flag
        if self.fletcher32:
            packed |= _fletcher32_flag
        packed <<= 8
        # Byte 1: compression library id (0 for none).
        if self.complevel > 0:
            packed |= all_complibs.index(self.complib) + 1
        packed <<= 8
        # Byte 0: compression level.
        packed |= self.complevel
        return packed

    def __init__( self, complevel=0, complib=default_complib,
                  shuffle=True, fletcher32=False ):
        """
        Create a new `Filters` instance.

        `complevel`
            Specifies a compression level for data.  The allowed range
            is 0-9.  A value of 0 (the default) disables compression.

        `complib`
            Specifies the compression library to be used.  Right now,
            'zlib' (the default), 'lzo' and 'bzip2' are supported.

        `shuffle`
            Whether or not to use the *Shuffle* filter in the HDF5
            library.  This is normally used to improve the compression
            ratio.  A false value disables shuffling and a true one
            enables it.  The default value depends on whether
            compression is enabled or not; if compression is enabled,
            shuffling defaults to be enabled, else shuffling is
            disabled.  Shuffling can only be used when compression is
            enabled.

        `fletcher32`
            Whether or not to use the *Fletcher32* filter in the HDF5
            library.  This is used to add a checksum on each data
            chunk.  A false value (the default) disables the checksum.
        """

        if not (0 <= complevel <= 9):
            raise ValueError( "compression level must be between 0 and 9" )
        if complib not in all_complibs:
            raise ValueError( "compression library ``%s`` is not supported; "
                              "it must be one of: %s"
                              % (complib, ", ".join(all_complibs)) )
        complevel = int(complevel)
        complib = str(complib)
        shuffle = bool(shuffle)
        fletcher32 = bool(fletcher32)

        # Override some inputs when compression is not enabled.
        if complevel == 0:
            complib = None  # make it clear there is no compression
            shuffle = False  # shuffling and not compressing makes no sense
        elif utilsExtension.whichLibVersion(complib) is None:
            warnings.warn( "compression library ``%s`` is not available; "
                           "using ``%s`` instead"
                           % (complib, default_complib) )
            complib = default_complib  # always available
        self.complevel = complevel
        self.complib = complib
        self.shuffle = shuffle
        self.fletcher32 = fletcher32

    def __repr__(self):
        args = []
        args.append('complevel=%d' % self.complevel)
        if self.complevel:
            args.append('complib=%r' % self.complib)
        args.append('shuffle=%s' % self.shuffle)
        args.append('fletcher32=%s' % self.fletcher32)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        if not isinstance(other, Filters):
            return False
        for attr in ['complib', 'complevel', 'shuffle', 'fletcher32']:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True


# Main part
# =========
def _test():
    """Run ``doctest`` on this module."""
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()