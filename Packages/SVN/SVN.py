import sublime
import sys
import os
import traceback
import time
import re

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer


lib_path = os.path.join(sublime.packages_path(), 'SVN', 'lib', 'all')
if os.name == 'nt':
    buf = create_unicode_buffer(512)
    if windll.kernel32.GetShortPathNameW(lib_path, buf, len(buf)):
        lib_path = buf.value

if lib_path not in sys.path:
    sys.path.append(lib_path)

if sublime.platform() == 'linux':
    lib_dynload_path = os.path.join(sublime.packages_path(), 'SVN', 'lib', 'linux-' + sublime.arch())
    if lib_dynload_path not in sys.path:
        sys.path.append(lib_dynload_path)

if sublime.platform() == 'osx':
    lib_dynload_path = os.path.join(sublime.packages_path(), 'SVN', 'lib', 'osx')
    if lib_dynload_path not in sys.path:
        sys.path.append(lib_dynload_path)

reloading = {
    'happening': False,
    'shown': False
}

# We reload in reverse order to solve some issues with super()
reload_mods = []
for mod in sys.modules:
    if (mod[0:11] == 'sublimesvn.' or mod == 'sublimesvn') and sys.modules[mod] != None:
        reload_mods.append(mod)
        reloading['happening'] = True

if reloading['happening']:
    _temp_status = __import__('sublimesvn.status', globals(), locals(),
        ['StatusCache'], -1)
    if hasattr(_temp_status.StatusCache, 'last_check_thread') and _temp_status.StatusCache.last_check_thread:
        _temp_status.StatusCache.last_check_thread.stop = True
    del _temp_status

# Prevent popups during reload, saving the callbacks for re-adding later
if reload_mods:
    old_callbacks = {}
    hook_match = re.search("<class '(\w+).ExcepthookChain'>", str(sys.excepthook))
    if hook_match:
        _temp = __import__(hook_match.group(1), globals(), locals(),
            ['ExcepthookChain'], -1)
        ExcepthookChain = _temp.ExcepthookChain
        old_callbacks = ExcepthookChain.names
    sys.excepthook = sys.__excepthook__

mods_load_order = [
    'sublimesvn',
    'sublimesvn.dpapi',
    'sublimesvn.times',
    'sublimesvn.views',
    'sublimesvn.errors',
    'sublimesvn.cmd',
    'sublimesvn.debug',
    'sublimesvn.output',
    'sublimesvn.config',
    'sublimesvn.paths',
    'sublimesvn.threads',
    'sublimesvn.input',
    'sublimesvn.proc',
    'sublimesvn.status',
    'sublimesvn.commands',
    'sublimesvn.listeners'
]

for mod in mods_load_order:
    if mod in reload_mods:
        reload(sys.modules[mod])

try:
    # First time installs sometimes suffer from import errors because the package
    # has not fully been extracted yet
    from sublimesvn.commands import SvnAddInteractiveCommand
except (ImportError):
    time.sleep(0.2)

from sublimesvn.commands import (SvnAddInteractiveCommand, SvnAddCommand, SvnBlameCommand,
    SvnBranchCommand, SvnChangelistAddCommand, SvnChangelistRemoveCommand,
    SvnCheckoutCommand, SvnCommitCommand, SvnCopyCommand, SvnCustomCommand,
    SvnCustomDiffCommand, SvnDeleteInteractiveCommand, SvnDeleteCommand,
    SvnDiffCommand, SvnFilePickCommand, SvnFilePropertiesCommand,
    SvnFolderPropertiesCommand, SvnIgnoreCommand, SvnInfoCommand,
    SvnLockCommand, SvnLogCommand, SvnMergeCommand, SvnMoveCommand,
    SvnOperationsCommand, SvnPropAddCommand, SvnPropDeleteCommand,
    SvnPropEditCommand, SvnPropListCommand, SvnRelocateCommand,
    SvnRerunCommand, SvnResolveCommand, SvnResolvePropertyConflictCommand,
    SvnResolveTreeConflictCommand, SvnRevertCommand, SvnStatusCommand,
    SvnSwitchCommand, SvnUnignoreCommand, SvnUnlockCommand, SvnUpdateCommand,
    SvnUpgradeCommand, SvnWcStatusCommand, SvnWcDiffCommand, SvnFileDiffCommand,
    SvnRevertInteractiveCommand, SvnWcLogCommand, SvnFileLogCommand,
    SvnWcCommitCommand)
from sublimesvn.listeners import (SvnSaveListener, SvnMessageSaveListener,
    SvnFocusListener)
from sublimesvn.status import (StatusCache)
from sublimesvn.proc import (SVN)

import sublimesvn.debug
import sublimesvn.times
import sublimesvn.paths
import sublimesvn.proc
import sublimesvn.threads


settings = sublime.load_settings('SVN.sublime-settings')
sublimesvn.debug.set_debug(settings.get('debug', False))
sublimesvn.debug.set_debug_log_file(settings.get('debug_log_file', None))


def reset_shown():
    SVN.shown_missing = {}

settings.add_on_change('svn_binary_path', reset_shown)
settings.add_on_change('auto_update_check_frequency', StatusCache.set_check_updates)
StatusCache.set_check_updates()

hook_match = re.search("<class '(\w+).ExcepthookChain'>", str(sys.excepthook))

if not hook_match:
    class ExcepthookChain(object):
        callbacks = []
        names = {}

        @classmethod
        def add(cls, name, callback):
            if name == 'sys.excepthook':
                if name in cls.names:
                    return
                cls.callbacks.append(callback)
            else:
                if name in cls.names:
                    cls.callbacks.remove(cls.names[name])
                cls.callbacks.insert(0, callback)
            cls.names[name] = callback

        @classmethod
        def hook(cls, type, value, tb):
            for callback in cls.callbacks:
                callback(type, value, tb)

        @classmethod
        def remove(cls, name):
            if name not in cls.names:
                return
            callback = cls.names[name]
            del cls.names[name]
            cls.callbacks.remove(callback)
else:
    _temp = __import__(hook_match.group(1), globals(), locals(),
        ['ExcepthookChain'], -1)
    ExcepthookChain = _temp.ExcepthookChain


# Override default uncaught exception handler
def svn_uncaught_except(type, value, tb):
    message = ''.join(traceback.format_exception(type, value, tb))

    if message.find('/sublimesvn/') != -1 or message.find('\\sublimesvn\\') != -1:
        def append_log():
            log_file_path = os.path.join(sublime.packages_path(), 'User',
                'SVN.errors.log')
            send_log_path = log_file_path
            timestamp = sublimesvn.times.timestamp_to_string(time.time(),
                    '%Y-%m-%d %H:%M:%S\n')
            with open(log_file_path, 'a') as f:
                f.write(timestamp)
                f.write(message)
            if sublimesvn.debug.get_debug() and sublimesvn.debug.get_debug_log_file():
                send_log_path = sublimesvn.debug.get_debug_log_file()
                sublimesvn.debug.debug_print(message)
            sublime.error_message(('%s: An unexpected error occurred, ' +
                'please send the file %s to support@wbond.net') % ('SVN',
                send_log_path))
            sublime.active_window().run_command('open_file',
                {'file': sublimesvn.paths.fix_windows_path(send_log_path)})
        if reloading['happening']:
            if not reloading['shown']:
                sublime.error_message('SVN: Sublime SVN was just upgraded' +
                    ', please restart Sublime to finish the upgrade')
                reloading['shown'] = True
        else:
            sublime.set_timeout(append_log, 10)

if reload_mods and old_callbacks:
    for name in old_callbacks:
        ExcepthookChain.add(name, old_callbacks[name])

ExcepthookChain.add('sys.excepthook', sys.__excepthook__)
ExcepthookChain.add('svn_uncaught_except', svn_uncaught_except)

if sys.excepthook != ExcepthookChain.hook:
    sys.excepthook = ExcepthookChain.hook

svn_binary_path = settings.get('svn_binary_path')


class SvnInit(sublimesvn.threads.HookedThread):
    def run(self):
        sublimesvn.proc.SVN.init(svn_binary_path=svn_binary_path)
SvnInit().start()


def unload_handler():
    StatusCache.stop()

    ExcepthookChain.remove('svn_uncaught_except')
