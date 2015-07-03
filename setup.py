#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

setuptools.setup (
   name          = "dmiid",
   version       = "0.1.0",
   description   = "read system information from /sys/class/dmi/id",
   author        = "Andr\xe9 Erdmann",
   author_email  = "dywi@mailerd.de",
   license       = "MIT",
   packages      = setuptools.find_packages ( exclude=[ 'tests', 'tests.*' ] ),
   classifiers   = [
      "Development Status :: 4 - Beta",
      "Intended Audience :: Developers",
      "Intended Audience :: System Administrators",
      "Operating System :: POSIX :: Linux",
      "Programming Language :: Python :: 2.7",
      "Programming Language :: Python :: 3",
      "Topic :: System",
      "License :: OSI Approved :: MIT License",
   ],
)
