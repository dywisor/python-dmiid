# This file is part of dmiid.
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 André Erdmann <dywi@mailerd.de>
#
# Distributed under the terms of the MIT license.
# (See LICENSE.MIT or http://opensource.org/licenses/MIT)
#

"""Provides dict-style access to /sys/class/dmi/id."""

from __future__ import absolute_import
from __future__ import unicode_literals, division, generators
from __future__ import print_function, nested_scopes, with_statement

import os.path
import re

from . import sysfsattr

__all__ = [ 'DMIIDInfo', 'DMIInfo', ]


try:
   # pylint: disable=C0103,E0602
   _string_types = ( basestring, )
except NameError:
   # pylint: disable=C0103
   _string_types = ( str, )



class DMIIDInfo ( sysfsattr.ReadonlySysFsAttrDict ):
   """Read system information from /sys/class/dmi/id.

   @cvar RE_NONE_CATCH_PHRASES:  a regexp that matches text that should be
                                 interpreted as "no information available"
   @type RE_NONE_CATCH_PHRASES:  compiled regexp (C{re.compile()})
   """

   RE_NONE_CATCH_PHRASES = re.compile (
      r'^(?:not available|to be filled|DMI table is broken)',
      flags = ( re.I | re.M )
   )

   def __init__ ( self, root="/sys/class/dmi/id", *args, **kwargs ):
      """Constructor

      @param root:    dmi id directory. Defaults to I{/sys/class/dmi/id}.
      @type  root:    C{str}
      @param args:
      @param kwargs:
      """
      super ( DMIIDInfo, self ).__init__ ( root, *args, **kwargs )
   # --- end of __init__ (...) ---

   def deserialize_value ( self, attr_normkey, text ):
      """Converts text read from a sysfs file into python data.

      Removes whitespace at the beginning and end of each text line,
      drops empty lines and replaces useless information with None
      (see L{RE_NONE_CATCH_PHRASES}).

      @param attr_normkey: normalized attribute key
      @type  attr_normkey: C{str}
      @param text:         text data read from a sysfs file
      @type  text:         C{str}
      @return:             deserialized data or None
      @rtype:              C{str} or None
      """

      # strip each text line, then drop empty lines
      val = '\n'.join (
         filter ( None, ( l.strip() for l in text.splitlines() ) )
      )

      if self.RE_NONE_CATCH_PHRASES.match(val) is not None:
         return None
      else:
         return val
   # --- end of deserialize_value (...) ---

# --- end of DMIIDInfo ---


class DMIInfo ( DMIIDInfo ):
   """A DMI ID view with a fancy normalize_key() method that eases transition
   between python-dmidecode and dmiid.

   @cvar DMIDECODE_HANDLE_MAP:  mapping, C{dmidecode handle int => handle str}
   @type DMIDECODE_HANDLE_MAP:  C{dict :: int => str}
   @cvar ATTR_KEY_ALIAS_MAP:    mapping, C{dmidecode handle/field => dmi id key}
   @type ATTR_KEY_ALIAS_MAP:    C{dict :: str => ( dict :: str => str )}
   """

   DMIDECODE_HANDLE_MAP = {
      0x0 : 'BIOS',
      0x1 : 'SYSTEM',
      0x2 : 'BOARD',
      0x3 : 'CHASSIS',
   }

   ATTR_KEY_ALIAS_MAP = {
      'BIOS': {
          'Vendor'       : 'bios_vendor',
          'Version'      : 'bios_version',
          'Release Date' : 'bios_date',
       },

      'SYSTEM': {
         'Manufacturer'  : 'sys_vendor',
         'Product Name'  : 'product_name',
         'Version'       : 'product_version',
         'Serial Number' : 'product_serial',
         'UUID'          : 'product_uuid',
      },

      'BOARD': {
         'Manufacturer'  : 'board_vendor',
         'Product Name'  : 'board_name',
         'Version'       : 'board_version',
         'Serial Number' : 'board_serial',
         'Asset Tag'     : 'board_asset_tag',
      },

      'CHASSIS': {
         'Manufacturer'  : 'chassis_vendor',
         'Type'          : 'chassis_type',   # returns int, not str
         'Version'       : 'chassis_version',
         'Serial Number' : 'chassis_serial',
         'Asset Tag'     : 'chassis_asset_tag',
      },
   }

   @classmethod
   def _get_handle_key ( cls, handle ):
      if isinstance ( handle, int ):
         return cls.DMIDECODE_HANDLE_MAP.get ( handle )
      else:
         try:
            handle_int = int ( handle, 16 )
         except ValueError:
            try:
               return handle.upper()
            except AttributeError:
               return None
         else:
            return cls.DMIDECODE_HANDLE_MAP.get ( handle_int )
   # --- end of _get_handle_key (...) ---

   @classmethod
   def _deref_dmidecode_attr ( cls, handle, attr_name ):
      handle_key = cls._get_handle_key ( handle )
      if handle_key:
         return cls.ATTR_KEY_ALIAS_MAP [handle_key] [attr_name]
      else:
         raise KeyError ( handle )
   # --- end of _deref_dmidecode_attr (...) ---

   @classmethod
   def _normalize_attr_key_tuple ( cls, attr_key ):
      try:
         return cls._deref_dmidecode_attr ( attr_key[0], attr_key[1] )
      except KeyError:
         raise ValueError ( attr_key )
   # --- end of _normalize_attr_key_tuple (...) ---

   def normalize_key ( self, attr_key ):
      if (
         not isinstance ( attr_key, _string_types )
         and hasattr ( attr_key, '__getitem__' )
         and hasattr ( attr_key, '__len__'  )
         and len ( attr_key ) == 2
      ):
         return self._normalize_attr_key_tuple ( attr_key )
      # -- end if

      attr_normkey = super ( DMIInfo, self ).normalize_key ( attr_key )

      parts = os.path.split ( attr_normkey )
      if len(parts) == 2:
         try:
            k = self._normalize_attr_key_tuple ( parts )
         except ValueError:
            pass
         else:
            attr_normkey = k
      # --

      assert attr_normkey
      return attr_normkey
   # --- end of normalize_key (...) ---

# --- end of DMIInfo ---
