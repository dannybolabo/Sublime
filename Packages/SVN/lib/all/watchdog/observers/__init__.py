#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Yesudeep Mangalapilly <yesudeep@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
:module: watchdog.observers
:synopsis: Observer that picks a native implementation if available.
:author: Yesudeep Mangalapilly <yesudeep@gmail.com>


Classes
=======
.. autoclass:: Observer
   :members:
   :show-inheritance:
   :inherited-members:

"""

from watchdog.observers.api import BaseObserver, DEFAULT_OBSERVER_TIMEOUT

# Ensure FSEvents is checked *before* kqueue here. Mac OS X supports
# both FSEvents and kqueue, and FSEvents is the preferred way of monitoring
# file system events on this OS.
try: # pragma: no cover
    from watchdog.observers.inotify import InotifyObserver as _Observer
    print 'Watchdog: using inotify'
except ImportError: # pragma: no cover
    try: # pragma: no cover
        from watchdog.observers.fsevents import FSEventsObserver as _Observer
        print 'Watchdog: using fsevents'
    except ImportError: # pragma: no cover
        try: # pragma: no cover
            from watchdog.observers.kqueue import KqueueObserver as _Observer
            print 'Watchdog: using kqueue'
        except ImportError: # pragma: no cover
            try: # pragma: no cover
                from watchdog.observers.read_directory_changes_async import WindowsApiAsyncObserver as _Observer
                print 'Watchdog: using windowsapiasync'
            except ImportError: # pragma: no cover
                try: # pragma: no cover
                    from watchdog.observers.read_directory_changes import WindowsApiObserver as _Observer
                    print 'Watchdog: using windowsapi'
                except ImportError: # pragma: no cover
                    from watchdog.observers.polling import PollingObserver as _Observer
                    print 'Watchdog: using polling'


class Observer(_Observer):
    """
    Observer thread that schedules watching directories and dispatches
    calls to event handlers.
    """
