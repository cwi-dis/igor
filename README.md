# Igor, your personal IoT butler

[![Build Status](https://travis-ci.org/cwi-dis/igor.svg?branch=master)](https://travis-ci.org/cwi-dis/igor)
[![Coverage Status](https://coveralls.io/repos/github/cwi-dis/igor/badge.svg?branch=master)](https://coveralls.io/github/cwi-dis/igor?branch=master)
[![Documentation status](https://readthedocs.org/projects/igor-iot/badge/)](https://igor-iot.readthedocs.io/en/latest/)
[![PyPI version](https://badge.fury.io/py/igor-iot.svg)](https://badge.fury.io/py/igor-iot)

Igor is named after the Discworld characters of the same name. 
You should think of it as a butler (or valet, or majordomo, 
whatever the difference is) that knows everything 
that goes on in your household, and makes sure everything runs smoothly. 
It performs its tasks without passing judgements and maintains complete 
discretion, even within the household. It can work together with other Igors 
(lending a hand) and with lesser servants such as [Iotsa-based devices](https://github.com/cwi-dis/iotsa).

Igor includes a Certificate Authority implementation that allows you to use
secure communication over https on the local network (for Igor and for other applications like
web browsers). Igor also includes a privacy and security mechanism based on capabilities to allow fine-grained control over data access.

Home page is <https://github.com/cwi-dis/igor>. 
This software is licensed under the [MIT license](LICENSE.txt) by the CWI DIS group, <http://www.dis.cwi.nl>.

## Overview

Igor is primarily an XML database. It has a REST interface to communicate to the outside world, and it can emit requests as well.
It performs its tasks of managing your household by knowing three things:

1. what is going on at the moment,
2. what needs to happen when, and
3. how to make that happen.

Igor has a plugin mechanism, and you can add plugins for all kinds of sensors (point 1). You can also add plugins that can control external devies (point 3). Finally you add rules to connect these (point 2).

Igor has a web interface to allow you to control and maintain it.
It also comes with a number of useful plugins and a set of Python modules and command line utilities that interact with it.

## Documentation

Formatted documentation is available online, at <https://igor-iot.readthedocs.io>.

When viewing source documentation is also available [here](doc/index.rst). 


## Getting Started

You need to have Python 3.6 or later installed.
(Python 2.7 is also still supported but Python 3 is preferred).

You need the _pip_ package manager for the version of Python that you are going to use.

```
python3 -m pip install igor-iot
```

After that follow the instructions in <https://igor-iot.readthedocs.io/en/latest/setup.html>
or [doc/setup.rst](doc/setup.rst) to setup your Igor system.



