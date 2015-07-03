# This file is part of dmiid.
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 André Erdmann <dywi@mailerd.de>
#
# Distributed under the terms of the MIT license.
# (See LICENSE.MIT or http://opensource.org/licenses/MIT)
#

"""Provides dict-style access to sysfs file."""

from __future__ import absolute_import
from __future__ import unicode_literals, division, generators
from __future__ import print_function, nested_scopes, with_statement

import errno
import collections
import io
import os

try:
   import collections.abc as _collections_abc
except ImportError:
   _collections_abc = collections

__all__ = [ 'ReadonlySysFsAttrDict', ]


class ReadonlySysFsAttrDict ( _collections_abc.Mapping ):
   """An object for accessing files under /sys/ in a dict-like fashion,
   meant for reading file that don't change often, e.g. information that
   gets initialized on bootup / module load.

   This class implements the readonly part.

   @cvar DICT_TYPE:     dict type of the L{data} instance variable
   @type DICT_TYPE:     C{type}
   @cvar FILE_ENCODING: default file encoding used when opening sysfs files
                        in text mode
   @type FILE_ENCODING: C{str}

   @ivar root:          filesystem location of the sysfs attributes being
                        inspected by this instance (should be a directory)
   @type root:          filesystem path (C{str})
   @ivar data:          dict for caching values read from sysfs
   @type data:          L{DICT_TYPE}
   @ivar _fname_cache:  a set of file names found in L{root} (non-recursive),
                         used to speed up __contains__ checks
   @type _fname_cache:  C{set}


   @group Attribute access:  __getitem__, get,
                             get_attributes, iget_attributes,
                             items, values, keys

   @group Data convertion / normalization: deserialize_value, normalize_key,
                                           get_fspath

   @group Cache management: clear, drop

   @group Private Methods:  _drop, _get, _get_filename_cache, _getitem,
                            _iget_attributes_v, _open_attr_text_file, _read_attr
   """

   DICT_TYPE     = dict
   FILE_ENCODING = "ascii"

   def __init__ ( self, root ):
      """Constructor.

      @param root: filesystem location of the sysfs view exposed by this
                   instance
      @type  root: C{str}
      """
      super ( ReadonlySysFsAttrDict, self ).__init__()
      self.root         = os.path.abspath ( root )
      self.data         = self.__class__.DICT_TYPE()
      self._fname_cache = self._get_filename_cache()
   # --- end of __init__ (...) ---

   def get_fspath ( self, relpath ):
      """Takes a relative filesystem path and turns it into an absolute path
      under L{self.root}.

      @param relpath: relative filesystem path (should not begin with C{os.sep})
      @type  relpath: C{str}
      @return:        absolute filesystem path
      @rtype:         C{str}
      """
      return os.path.join ( self.root, relpath )
   # --- end of get_fspath (...) ---

   def normalize_key ( self, attr_key ):
      """Converts an attribute key into a normalized variant that can be
      used for both dict-caching and filesystem access.

      In particular, strips any leading path separators from the attribute
      key and eliminates unnecessary relative path elements by means of
      C{os.normpath()}.

      (Normalizing an already normalized attribute key returns it unmodified.)

      @param attr_key: attribute key
      @type  attr_key: C{str}
      @return:         normalized attribute key
      @rtype:          C{str}
      """
      # pylint: disable=R0201
      return os.path.normpath ( attr_key ).lstrip ( os.path.sep )
   # --- end of normalize_key (...) ---

   def deserialize_value ( self, attr_normkey, text ):
      """Converts text read from a sysfs file into python data.

      The default implementation removes whitespace at the end of the string,
      but derived classes may override this method and return objects
      of arbitrary type.

      @param attr_normkey: normalized attribute key
      @type  attr_normkey: C{str}
      @param text:         text data read from a sysfs file
      @type  text:         C{str}
      @return:             deserialized data
      @rtype:              C{str}, see notes concerning derived classes above
      """
      # pylint: disable=R0201,W0613
      return text.rstrip() if text else text
   # --- end of deserialize_value (...) ---

   def _get_filename_cache ( self ):
      """Returns a set containing the names of all files in L{self.root}.

      @return: set of file names
      @rtype:  set
      """
      for _, _, filenames in os.walk ( self.root ):
         return set(filenames)
      return set()
   # --- end of _get_filename_cache (...) ---

   def clear ( self ):
      """Empties the data cache and regenerates the file name cache."""
      self.data.clear()
      self._fname_cache = self._get_filename_cache()
   # --- end of clear (...) ---

   def _drop ( self, attr_normkey ):
      """Removes an entry from the attribute data cache

      @param attr_normkey: normalized attribute key
      @type  attr_normkey: C{str}
      """
      try:
         del self.data [attr_normkey]
      except KeyError:
         pass
   # --- end of _drop (...) ---

   def drop ( self, attr_key ):
      """Removes an entry from the attribute data cache.

      @param attr_key: attribute key
      @type  attr_key: C{str}
      """
      return self._drop ( self.normalize_key ( attr_key ) )
   # --- end of drop (...) ---

   def __contains__ ( self, attr_key ):
      """Checks whether the given attribute exists.

      To realize this in a way that doesn't involve filesystem access on
      any negative lookup, this method searches for the attribute in both
      the data and file name cache and returns True or False based on the
      result (any hit => True).
      This does not imply the attribute is actually readable!

      Only "deep" attributes (attribute exists in a directory under
      L{self.root}) require a filesystem lookup, because recursively caching
      all file names is simply impractical.

      @param attr_key: attribute key (gets normalized)
      @type  attr_key: C{str}
      @return:         True or False
      @rtype:          bool
      """
      attr_normkey = self.normalize_key ( attr_key )

      if attr_normkey in self.data:
         return True

      elif attr_normkey in self._fname_cache:
         return True

      elif os.path.sep in attr_normkey:
         attr_path = self.get_fspath ( attr_normkey )
         return os.path.isfile ( attr_path )

      else:
         return False
   # --- end of __contains__ (...) ---

   def keys ( self ):
      """Returns a set of all attribute keys, which is a union of the
      data cache and the filename cache.

      @return: attribute keys (normalized)
      @rtype:  set
      """
      return set(self.data) | self._fname_cache
   # --- end of keys (...) ---

   def __len__ ( self ):
      """
      @return: number of all attribute keys
      @rtype:  int
      """
      return len(self.keys())
   # --- end of __len__ (...) ---

   def __bool__ ( self ):
      """
      @return: True if this sysfs view instance contains any attributes,
               else False
      @rtype:  bool
      """
      return bool(self.data) or bool(self._fname_cache)
   # --- end of __bool__ (...) ---

   __nonzero__ = __bool__
   # --- end of __nonzero___

   def __iter__ ( self ):
      return iter(self.keys())
   # --- end of __iter__ (...) ---

   def items ( self, sort_keys=False, **kwargs ):
      """Generator that yields key-value 2-tuples of all attributes.

      Suppresses read errors by default.

      @keyword sort_keys:  whether to output sorted tuples (sorted by key)
                           Defaults to False.
      @type  sort_keys:    bool
      @param kwargs:       See C{get()}.
      @return:             2-tuple C{(attribute_key, attribute_value)}
      @rtype:              2-tuple C{(str, any type)}
      """
      return self._iget_attributes_v (
         ( sorted(self.keys()) if sort_keys else self.keys() ),
         **kwargs
      )
   # --- end of items (...) ---

   def values ( self, **kwargs ):
      """Generator that yields the values of all attributes.

      Suppresses read errors by default.

      @param kwargs:
      @return:        attribute values or NotImplemented for unaccessible attributes
      @rtype:         any type
      """
      for _, attr_value in self.items ( **kwargs ):
         yield attr_value
   # --- end of values (...) ---

   def _open_attr_text_file ( self, attr_normkey, mode, **kwargs ):
      """Opens an attribute file in text mode.
      Uses L{FILE_ENCODING} as file encoding if not specified otherwise
      (in C{**kwargs}).

      @param attr_normkey: normalized attribute key
      @type  attr_normkey: C{str}
      @param mode:         mode
      @type  mode:         C{str}
      @param kwargs:
      @return:             file handle
      """
      kwargs.setdefault ( 'encoding', self.FILE_ENCODING )
      return io.open ( self.get_fspath(attr_normkey), mode, **kwargs )
   # --- end of _open_attr_text_file (...) ---

   def _read_attr ( self, attr_normkey ):
      """Reads an attribute file in text mode and deserializes its data.

      @param attr_normkey: normalized attribute key
      @type  attr_normkey: C{str}
      @return:             deserialized data
      @rtype:              any type
      """
      # pylint: disable=C0103
      with self._open_attr_text_file ( attr_normkey, "rt" ) as fh:
         text = fh.read()

      return self.deserialize_value ( attr_normkey, text )
   # --- end of _read_attr (... ) ---

   def _getitem (
      self, attr_normkey,
      bypass=False, refresh=False, nofail=False, nofail_fallback=None
    ):
      """Returns the (deserialized) value of the requested attribute.

      To speed things up, the attribute gets looked up in the data cache
      before trying to read it from /sys, which also means that the returned
      data may be invalid (outdated) if the attribute changed since being
      read from /sys. To deal with such inconsistencies, this method supports
      a few options that control how the attribute gets accessed.

      The C{bypass} option enforces filesystem read and does not involve
      the data cache at all.

      If the C{refresh} option is set, then the attribute gets removed from
      the data cache, resulting in a filesystem read.
      When used together with C{bybass}, the attribute does not get added back
      to the cache.

      The C{nofail} option suppresses read errors due to writeonly files etc.


      @raises IOError:         (only if C{nofail} is not set)
      @raises OSError:         (only if C{nofail} is not set)
      @raises KeyError:

      @param attr_normkey:     normalized attribute key
      @type  attr_normkey:     C{str}
      @param bypass:           whether to skip the data cache lookup and read
                               the attribute directly. Defaults to False.
      @type  bypass:           bool
      @param refresh:          whether to drop the attribute from the data cache
                               prior to looking it up, resulting in a fs read.
                               Defaults to False.
      @type  refresh:          bool
      @param nofail:           whether to suppress read errors (OSError/IOError)
                               and return nofail_fallback in that case
                               Defaults to False.
      @type  nofail:           bool
      @param nofail_fallback:  fallback value for read errors. Defaults to None.
      @type  nofail_fallback:  any type
      @return:                 deserialized data
      @rtype:                  any type
      """
      if refresh:
         self._drop ( attr_normkey )
      elif not bypass:
         # "refresh" implies skip-cache
         try:
            return self.data [attr_normkey]
         except KeyError:
            pass
      # -- end drop or return cached?

      try:
         value = self._read_attr ( attr_normkey )
      except ( IOError, OSError ) as err:
         if getattr ( err, 'errno', None ) == errno.ENOENT:
            raise KeyError ( attr_normkey )
         elif nofail:
            # nofail_fallback does not get cached.
            return nofail_fallback
         else:
            raise
      # -- end try read from fs

      if not bypass:
         self.data [attr_normkey] = value

      return value
   # --- end of _getitem (...) ---

   def __getitem__ ( self, attr_key ):
      """Similar to L{_getitem()}, but normalizes the attribute key
      before looking it up.

      @raises IOError:
      @raises OSError:
      @raises KeyError:

      @param attr_key:  attribute key
      @type  attr_key:  C{str}
      @return:          deserialized data
      @rtype:           any type
      """
      return self._getitem ( self.normalize_key(attr_key) )
   # --- end of __getitem__ (...) ---

   def _get ( self, attr_normkey, fallback=None, **kwargs ):
      """L{get()} variant that takes a normalized key as first arg."""
      try:
         return self._getitem ( attr_normkey, **kwargs )
      except KeyError:
         return fallback
   # --- end of _get (...) ---

   def get ( self, attr_key, fallback=None, **kwargs ):
      """Returns the (deserialized) value of the requested attribute.

      Similar to C{_get_filename_cache()}, but does not raise a C{KeyError}
      if the attribute does not exist.

      @raises IOError:  (only if C{nofail} is not set)
      @raises OSError:  (only if C{nofail} is not set)

      @param attr_key:  attribute key
      @type  attr_key:  C{str}
      @param fallback:  fallback value if the attribute cannot be retrieved
                        from the cache or sysfs. Defaults to None.
      @type  fallback:  any type
      @param kwargs:    additional keyword arguments, see C{_getitem()}
      @return:          deserialized data
      @rtype:           any type
      """
      return self._get ( self.normalize_key(attr_key), fallback, **kwargs )
   # --- end of get (...) ---

   def _iget_attributes_v ( self, attr_normkeys, nofail=True, **kwargs ):
      """Generator that yields a series of 2-tuples C{(normalized key,value)}.

      @param attr_normkeys:  iterable of normalized attribute keys
      @type  attr_normkeys:  iterable, e.g. list or generator
      @param nofail:         see L{get()}. Defaults to True.
      @type  nofail:         bool
      @param kwargs:         see L{get()}
      """
      for attr_normkey in attr_normkeys:
         yield (
            attr_normkey, self._get ( attr_normkey, nofail=nofail, **kwargs )
         )
   # --- end of _iget_attributes_v (...) ---

   def iget_attributes ( self, *attr_keys, **kwargs ):
      """Generator that yields a series of 2-tuples C{(normalized key,value)}.

      @param attr_keys:  attribute keys
      @type attr_keys:   *args
      @param kwargs:     see L{_iget_attributes_v()}
      """
      return self._iget_attributes_v (
         map ( self.normalize_key, attr_keys ), **kwargs
      )
   # --- end of iget_attributes (...) ---

   def get_attributes ( self, *attr_keys, **kwargs ):
      """Similar to L{iget_attributes()}, but returns a list of 2-tuples."""
      return list ( self.iget_attributes ( *attr_keys, **kwargs ) )
   # --- end of get_attributes (...) ---

# --- end of ReadonlySysFsAttrDict ---


##class WritableSysFsAttrDict ( ReadonlySysFsAttrDict ):
##   NotImplemented
