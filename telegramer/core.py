# -*- coding: utf-8 -*-
#
# core.py
#
# Copyright (C) 2016-2017 Noam <noamgit@gmail.com>
# https://github.com/noam09
#
# Much credit to:
# Copyright (C) 2011 Innocenty Enikeew <enikesha@gmail.com>
# https://bitbucket.org/enikesha/deluge-xmppnotify
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
#   The Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor
#   Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

from __future__ import unicode_literals

import os
import logging

import urllib3

from deluge.core.eventmanager import EventManager
from deluge.core.torrentmanager import TorrentManager
from deluge.core.core import Core as DelugeCore
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, BaseFilter, ConversationHandler
from telegram.utils.request import Request
from base64 import b64encode
from random import choice
import deluge.configmanager
import deluge.component as component
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase
from deluge.common import fsize, fpcnt, fspeed, fpeer, ftime, fdate, is_url, is_magnet
from .common import is_int

log = logging.getLogger(__name__)
http = urllib3.PoolManager()

HELP_MESSAGE = \
    '/add - Add a new torrent\n' \
    '/list - List all torrents\n' \
    '/down - List downloading torrents\n' \
    '/up - List uploading torrents\n' \
    '/paused - List paused torrents\n' \
    '/cancel - Cancels the current operation\n' \
    '/help - Show this help message'

MARKDOWN_PARSE_MODE = 'Markdown'

NEXT, SET_CATEGORY, SET_LABEL, SET_TORRENT_TYPE, SET_MAGNET, SET_TORRENT, SET_URL = range(7)

DEFAULT_PREFS = {
    'telegram_token': '',
    'telegram_user': '',
    'telegram_users': '',
    'telegram_users_notify': '',
    'telegram_notify_finished': True,
    'telegram_notify_added': True,
    'dir1': '',
    'cat1': '',
    'dir2': '',
    'cat2': '',
    'dir3': '',
    'cat3': ''
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
                  '(KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
}

STICKERS = {
    'lincoln': 'BQADBAADGQADyIsGAAE2WnfSWOhfUgI',
    'dali': 'BQADBAADHAADyIsGAAFZfq1bphjqlgI',
    'chan': 'BQADBAADPQADyIsGAAHaVWyyLugSFAI',
    'marley': 'BQADBAADJQADyIsGAAGdzbYn4WkdaAI',
    'snow': 'CAADAgADZQUAAgi3GQJyjRNCuIA54gI',
    'borat': 'CAADBAADmwQAAjJQbQAB5DpM4iETWoQC'
}

EMOJI = {
    'seeding': u'\u23eb',
    'queued': u'\u23ef',
    'paused': u'\u23f8',
    'error': u'\u2757\ufe0f',
    'downloading': u'\u23ec'
}

STRINGS = {
    'no_label': 'No Label',
    'no_category': 'Use Default Settings',
    'cancel': 'Send /cancel at any time to abort',
    'test_success': 'It works!',
    'which_cat': 'Which category/directory?\nRemember to quote ' +
                 'directory paths ("/path/to/dir")',
    'which_label': 'Which label?',
    'what_kind': 'What kind?',
    'send_magnet': 'Please send me the magnet link',
    'send_file': 'Please send me the torrent file',
    'send_url': 'Please send me the address',
    'added': 'Added',
    'eta': 'ETA',
    'error': 'Error',
    'not_magnet': 'Aw man... That\'s not a magnet link',
    'not_file': 'Aw man... That\'s not a torrent file',
    'not_url': 'Aw man... Bad link',
    'download_fail': 'Aw man... Download failed',
    'no_items': 'No items',
    'invalid_user': 'Who are you?..'
}

INFO_DICT = (
    ('queue', lambda i, s: i != -1 and str(i) or '#'),
    ('state', None),
    ('name', lambda i, s: u' %s *%s* ' %
                          (s['state'] if s['state'].lower() not in EMOJI
                           else EMOJI[s['state'].lower()],
                           i)),
    ('total_wanted', lambda i, s: '(%s) ' % fsize(i)),
    ('progress', lambda i, s: '%s\n' % fpcnt(i / 100)),
    ('num_seeds', None),
    ('num_peers', None),
    ('total_seeds', None),
    ('total_peers', lambda i, s: '%s / %s seeds\n' %
                                 tuple(map(fpeer, (s['num_seeds'], s['num_peers']),
                                           (s['total_seeds'], s['total_peers'])))),
    ('download_payload_rate', None),
    ('upload_payload_rate', lambda i, s: '%s : %s\n' %
                                         tuple(map(fspeed, (s['download_payload_rate'], i)))),
    ('eta', lambda i, s: i > 0 and '*ETA:* %s ' % ftime(i) or ''),
    ('time_added', lambda i, s: '*Added:* %s' % fdate(i))
)

INFOS = [i[0] for i in INFO_DICT]

EVENT_MAP = {
    'added': 'TorrentAddedEvent',
    'complete': 'TorrentFinishedEvent'
}


def format_torrent_info(torrent):
    status = torrent.get_status(INFOS)
    log.debug(status)
    try:
        return u''.join([f(status[i], status) for i, f in INFO_DICT if f is not None])
    # except UnicodeDecodeError as e:
    except Exception as e:
        log.error(e)
    return None


class MagnetFilter(BaseFilter):
    def filter(self, message):
        text = message.text
        return text and not text.startswith('/') and is_magnet(text)


class UrlFilter(BaseFilter):
    def filter(self, message):
        text = message.text
        return text and not text.startswith('/') and is_url(text)


magnet_filter = MagnetFilter()
url_filter = UrlFilter()


class Core(CorePluginBase):
    def __init__(self, *args):
        super(Core, self).__init__(*args)

        self.__core = component.get('Core')  # type: DelugeCore
        self.__event_manager = component.get('EventManager')  # type: EventManager
        self.__torrent_manager = component.get('TorrentManager')  # type: TorrentManager
        self.__registered_events = {}

        self.__bot = None
        self.__updater = None

        self.__config = None
        self.__whitelist = []
        self.__notifylist = []
        self.__conv_options = None
        self.__torrent_options = None
        self.__commands = {
            'list': self.cmd_list,
            'down': self.cmd_down,
            'downloading': self.cmd_down,
            'up': self.cmd_up,
            'uploading': self.cmd_up,
            'seed': self.cmd_up,
            'seeding': self.cmd_up,
            'paused': self.cmd_paused,
            'queued': self.cmd_paused,
            '?': self.cmd_help,
            'cancel': self.cmd_cancel,
            'help': self.cmd_help,
            'start': self.cmd_help,
            'reload': self.restart,
            'commands': self.cmd_help
        }

        log.debug('Initialize class')

    def enable(self):
        log.info('Enable')

        self.__whitelist = []
        self.__notifylist = []
        self.__conv_options = None
        self.__torrent_options = None

        try:
            self.__config = deluge.configmanager.ConfigManager('telegramer.conf', DEFAULT_PREFS)

            log.debug('Initialize bot')

            telegram_token = self.__config['telegram_token']
            if not telegram_token:
                return

            if self.__config['telegram_user']:
                self.__whitelist.append(str(self.__config['telegram_user']))
                self.__notifylist.append(str(self.__config['telegram_user']))
                if self.__config['telegram_users']:
                    telegram_user_list = filter(None, [x.strip() for x in
                                                       str(self.__config['telegram_users']).split(',')])
                    # Merge with whitelist and remove duplicates - order will be lost
                    self.__whitelist = list(set(self.__whitelist + telegram_user_list))
                    log.debug('Whitelist: ' + str(self.__whitelist))
                if self.__config['telegram_users_notify']:
                    n = filter(None, [x.strip() for x in
                                      str(self.__config['telegram_users_notify']).split(',')])
                    telegram_user_list_notify = [a for a in n if is_int(a)]
                    # Merge with notifylist and remove duplicates - order will be lost
                    self.__notifylist = list(set(self.__notifylist + telegram_user_list_notify))
                    log.debug('Notify: ' + str(self.__notifylist))

            self.__bot = Bot(telegram_token, request=Request(con_pool_size=8))
            # Create the EventHandler and pass it bot's token.
            self.__updater = Updater(bot=self.__bot)
            # Get the dispatcher to register handlers
            dp = self.__updater.dispatcher

            # Add conversation handler with the different states
            dp.add_handler(
                ConversationHandler(
                    entry_points=[
                        CommandHandler('add', self.add),
                        MessageHandler(magnet_filter, self.add_magnet),
                        MessageHandler(url_filter, self.add_url),
                        MessageHandler(Filters.document, self.add_torrent)
                    ],
                    states={
                        SET_CATEGORY: [MessageHandler(Filters.text, self.set_category)],
                        SET_LABEL: [MessageHandler(Filters.text, self.set_label)],
                        SET_TORRENT_TYPE: [MessageHandler(Filters.text, self.set_torrent_type)],
                        SET_MAGNET: [MessageHandler(Filters.text, self.set_magnet)],
                        SET_TORRENT: [MessageHandler(Filters.document, self.set_torrent)],
                        SET_URL: [MessageHandler(Filters.text, self.set_url)]
                    },
                    fallbacks=[CommandHandler('cancel', self.cmd_cancel)]
                )
            )

            for key, value in self.__commands.items():
                dp.add_handler(CommandHandler(key, value))

            # Log all errors
            dp.add_error_handler(self.error)

            # Start the Bot
            self.__updater.start_polling(poll_interval=0.05)

            self.connect_events()

        except Exception as e:
            log.error(e)

    def disable(self):
        log.info('Disable')

        try:
            self.__whitelist = None
            self.__notifylist = None

            self.disconnect_events()
            self.__bot = None

            if self.__updater:
                self.__updater.stop()
                self.__updater = None
        except Exception as e:
            log.error(e)

    def error(self, bot, update, error):
        log.warning('Update "{0}" caused error "{1}"'.format(update, error))

    def update(self):
        pass

    def is_white_user(self, user_id):
        return user_id in self.__whitelist

    def is_notify_user(self, user_id):
        return user_id in self.__notifylist

    def send_message(self, message, to=None, parse_mode=None):
        if not self.__bot:
            return

        log.debug('Send message')
        if not to:
            to = self.__config['telegram_user']
        else:
            log.debug('send_message, to set')

        if not isinstance(to, (list,)):
            log.debug('Convert to to list')
            to = [to]

        log.debug("[to] " + str(to))
        for chat_id in to:
            # Every outgoing message filtered here
            if not self.is_white_user(chat_id) and not self.is_notify_user(chat_id):
                continue

            log.debug("to: " + chat_id)
            if len(message) > 4096:
                log.debug('Message length is {0}'.format(len(message)))
                tmp = ''
                for line in message.split('\n'):
                    tmp += line + '\n'
                    if len(tmp) < 4000:
                        continue

                    if parse_mode:
                        self.__bot.send_message(chat_id, tmp, parse_mode=parse_mode)
                    else:
                        self.__bot.send_message(chat_id, tmp)
                    tmp = ''

                if tmp:
                    if parse_mode:
                        self.__bot.send_message(chat_id, tmp, parse_mode=parse_mode)
                    else:
                        self.__bot.send_message(chat_id, tmp)

                continue

            if parse_mode:
                self.__bot.send_message(chat_id, message, parse_mode=parse_mode)
            else:
                self.__bot.send_message(chat_id, message)

        log.debug('return')

    def verify_user(self, bot, update):
        if self.is_white_user(str(update.message.chat.id)):
            return True

        update.message.reply_text(STRINGS['invalid_user'], reply_markup=ReplyKeyboardRemove())
        return False

    def cmd_cancel(self, bot, update):
        if not self.verify_user(bot, update):
            return

        log.info("User %s canceled the conversation." % str(update.message.chat.id))

        if not self.__conv_options and not self.__torrent_options:
            update.message.reply_text('No active operation', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        self.__conv_options = None
        self.__torrent_options = None

        update.message.reply_text('Operation cancelled', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def cmd_help(self, bot, update):
        log.debug("Entered cmd_help")
        if not self.verify_user(bot, update):
            return

        chat_id = str(update.message.chat.id)
        log.debug(chat_id + " in whitelist")
        log.debug("telegram_send to " + chat_id)
        self.send_message(HELP_MESSAGE, to=[chat_id], parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def cmd_list(self, bot, update):
        if not self.verify_user(bot, update):
            return

        # log.error(self.list_torrents())
        self.send_message(self.list_torrents(lambda t:
                                             t.get_status(('state',))['state'] in
                                             ('Active', 'Downloading', 'Seeding',
                                              'Paused', 'Checking', 'Error', 'Queued')),
                          to=[str(update.message.chat.id)],
                          parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def cmd_down(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.send_message(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Downloading'),
                          to=[str(update.message.chat.id)],
                          parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def cmd_up(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.send_message(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Seeding'),
                          to=[str(update.message.chat.id)],
                          parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def cmd_paused(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.send_message(self.list_torrents(lambda t: t.get_status(('state',))['state'] in ('Paused', 'Queued')),
                          to=[str(update.message.chat.id)],
                          parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def __set_category(self, bot, update):
        text = update.message.text
        log.info("set_category: {0}".format(text))

        if text != STRINGS['no_category']:
            move_completed_path = None
            for i in range(3):
                i += 1
                cat_key = 'cat' + str(i)
                if self.__config[cat_key] == text:
                    dir_key = 'dir' + str(i)
                    move_completed_path = self.__config[dir_key]
                    break

            # If none of the existing categories were selected,
            # maybe user is trying to save to a new directory
            if not move_completed_path:
                log.debug('Custom directory entered: ' + str(text))
                if text[0] == '"' and text[-1] == '"':
                    custom_path = os.path.abspath(os.path.realpath(text[1:-1]))
                    log.debug('Attempt to create and save to: ' + str(custom_path))
                    if not os.path.exists(custom_path):
                        os.makedirs(custom_path)
                    move_completed_path = custom_path

            if move_completed_path:
                # move_completed_path vs download_location
                self.__torrent_options['move_completed_path'] = move_completed_path
                self.__torrent_options['move_completed'] = True

        self.__conv_options['category'] = text

    def __set_label(self, bot, update):
        label = update.message.text.lower()
        log.info("set_label: {0}".format(label))

        self.__conv_options['label'] = label

    def __set_torrent_type(self, bot, update):
        torrent_type = update.message.text
        log.info("set_torrent_type: {0}".format(torrent_type))

        if torrent_type == 'Magnet':
            update.message.reply_text(STRINGS['send_magnet'], reply_markup=ReplyKeyboardRemove())
            return SET_MAGNET

        if torrent_type == '.torrent':
            update.message.reply_text(STRINGS['send_file'], reply_markup=ReplyKeyboardRemove())
            return SET_TORRENT

        if torrent_type == 'URL':
            update.message.reply_text(STRINGS['send_url'], reply_markup=ReplyKeyboardRemove())
            return SET_URL

        update.message.reply_text(STRINGS['error'], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def __set_magnet(self, bot, update):
        magnet = update.message.text
        log.info("set_magnet: {0}".format(magnet))

        if not is_magnet(magnet):
            update.message.reply_text(STRINGS['not_magnet'], reply_markup=ReplyKeyboardRemove())
            return SET_MAGNET

        self.__conv_options['magnet'] = magnet

    def __set_torrent(self, bot, update):
        document = update.message.document
        log.info("set_torrent: {0}".format(document))

        if document.mime_type != 'application/x-bittorrent':
            update.message.reply_text(STRINGS['not_file'], reply_markup=ReplyKeyboardRemove())
            return SET_TORRENT

        try:
            # Get file info
            file_info = bot.get_file(document.file_id)

            # Download file
            response = http.request('GET', file_info.file_path, headers=HEADERS)
            file_content = response.data

            # Base64 encode file data
            self.__conv_options['torrent'] = b64encode(file_content)
        except Exception as e:
            log.error(e)
            update.message.reply_text(STRINGS['download_fail'], reply_markup=ReplyKeyboardRemove())
            return SET_TORRENT

    def __set_url(self, bot, update):
        url = update.message.text.strip()
        log.info("set_url: {0}".format(url))

        if not is_url(url):
            update.message.reply_text(STRINGS['not_url'], reply_markup=ReplyKeyboardRemove())
            return SET_URL

        try:
            # Download file
            response = http.request('GET', url, headers=HEADERS)
            file_content = response.data

            # Base64 encode file data
            self.__conv_options['torrent'] = b64encode(file_content)
        except Exception as e:
            log.error(e)
            update.message.reply_text(STRINGS['download_fail'], reply_markup=ReplyKeyboardRemove())
            return SET_URL

    def __proc_conv_step(self, step, bot, update):
        if step == NEXT:
            return
        if step == SET_CATEGORY:
            return self.__set_category(bot, update)
        if step == SET_LABEL:
            return self.__set_label(bot, update)
        if step == SET_TORRENT_TYPE:
            return self.__set_torrent_type(bot, update)
        if step == SET_MAGNET:
            return self.__set_magnet(bot, update)
        if step == SET_TORRENT:
            return self.__set_torrent(bot, update)
        if step == SET_URL:
            return self.__set_url(bot, update)

    def __proc_conv(self, step, bot, update):
        if not self.verify_user(bot, update):
            return

        if not self.__conv_options:
            self.__conv_options = {}
        if not self.__torrent_options:
            self.__torrent_options = {}

        step_result = self.__proc_conv_step(step, bot, update)
        if step_result:
            return step_result

        if 'category' not in self.__conv_options:
            keyboard_options = []
            """Currently there are 3 possible categories so
            loop through cat1-3 and dir1-3, check if directories exist
            """
            for i in range(3):
                i += 1

                dir_key = 'dir' + str(i)
                if not os.path.isdir(self.__config[dir_key]):
                    continue

                cat_key = 'cat' + str(i)
                log.debug(self.__config[cat_key] + ' ' + self.__config[dir_key])
                keyboard_options.append([self.__config[cat_key]])

            keyboard_options.append([STRINGS['no_category']])

            update.message.reply_text(
                '{0}\n{1}'.format(STRINGS['which_cat'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

            return SET_CATEGORY

        if 'label' not in self.__conv_options:
            keyboard_options = []
            try:
                if 'Label' in self.__core.get_enabled_plugins():
                    label_plugin = component.get('CorePlugin.Label')
                    if label_plugin:
                        for label in label_plugin.get_labels():
                            keyboard_options.append([label])

                    keyboard_options.append([STRINGS['no_label']])
            except Exception as e:
                log.debug('Enabling Label plugin failed')
                log.error(e)

            if len(keyboard_options) > 0:
                update.message.reply_text(
                    STRINGS['which_label'],
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

                return SET_LABEL

            self.__conv_options['label'] = STRINGS['no_label'].lower()

        if 'torrent' not in self.__conv_options and 'magnet' not in self.__conv_options:
            # Request torrent type
            keyboard_options = [['Magnet'], ['.torrent'], ['URL']]
            update.message.reply_text(
                STRINGS['what_kind'],
                reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

            return SET_TORRENT_TYPE

        torrent_id = None
        if 'torrent' in self.__conv_options:
            torrent = self.__conv_options['torrent']
            log.info('Adding torrent from base64 string using options `%s` ...', self.__torrent_options)
            torrent_id = self.__core.add_torrent_file('', torrent, self.__torrent_options or {})
        elif 'magnet' in self.__conv_options:
            magnet = self.__conv_options['magnet']
            log.debug('Adding torrent from magnet URI `%s` using options `%s` ...', magnet, self.__torrent_options)
            torrent_id = self.__core.add_torrent_magnet(magnet, self.__torrent_options or {})

        if torrent_id:
            self.apply_label(torrent_id, self.__conv_options)
        else:
            update.message.reply_text(STRINGS['error'], reply_markup=ReplyKeyboardRemove())

        self.__conv_options = None
        self.__torrent_options = None

        return ConversationHandler.END

    def add(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.__conv_options = None
        self.__torrent_options = None

        return self.__proc_conv(NEXT, bot, update)

    def add_magnet(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.__conv_options = None
        self.__torrent_options = None

        return self.__proc_conv(SET_MAGNET, bot, update)

    def add_url(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.__conv_options = None
        self.__torrent_options = None

        return self.__proc_conv(SET_URL, bot, update)

    def add_torrent(self, bot, update):
        if not self.verify_user(bot, update):
            return

        self.__conv_options = None
        self.__torrent_options = None

        return self.__proc_conv(SET_TORRENT, bot, update)

    def set_category(self, bot, update):
        return self.__proc_conv(SET_CATEGORY, bot, update)

    def set_label(self, bot, update):
        return self.__proc_conv(SET_LABEL, bot, update)

    def set_torrent_type(self, bot, update):
        return self.__proc_conv(SET_TORRENT_TYPE, bot, update)

    def set_magnet(self, bot, update):
        return self.__proc_conv(SET_MAGNET, bot, update)

    def set_torrent(self, bot, update):
        return self.__proc_conv(SET_TORRENT, bot, update)

    def set_url(self, bot, update):
        return self.__proc_conv(SET_URL, bot, update)

    def apply_label(self, torrent_id, options):
        if not options or not isinstance(options, dict):
            return

        label = options.get('label')
        if not label:
            return

        label = label.lower()
        if label == STRINGS['no_label'].lower():
            return

        try:
            # Enable Label plugin
            self.__core.enable_plugin('Label')
            label_plugin = component.get('CorePlugin.Label')
            if not label_plugin:
                return

            # Add label if neccessary
            if label not in label_plugin.get_labels():
                label_plugin.add(label)

            label_plugin.set_torrent(torrent_id, label)
            log.debug('Set label {0} to torrent {1}'.format(label, torrent_id))
        except Exception as e:
            log.error(e)

    def update_stats(self):
        log.debug('update_stats')

    def connect_events(self):
        event_manager = self.__event_manager
        if not event_manager:
            return

        # Go through the commands list and register event handlers
        for event in EVENT_MAP.keys():
            if event in self.__registered_events:
                continue

            def create_event_handler(event):
                def event_handler(torrent_id, *arg):
                    self.on_torrent_event(torrent_id, event, *arg)

                return event_handler

            handler = create_event_handler(event)
            event_manager.register_event_handler(EVENT_MAP[event], handler)
            self.__registered_events[event] = handler

    def disconnect_events(self):
        event_manager = self.__event_manager
        if not event_manager:
            return

        for event, handler in self.__registered_events.items():
            event_manager.deregister_event_handler(EVENT_MAP[event], handler)

    def on_torrent_added(self, torrent_id):
        if not self.__config['telegram_notify_added']:
            return

        try:
            # torrent_id = str(alert.handle.info_hash())
            torrent = self.__torrent_manager[torrent_id]
            torrent_status = torrent.get_status(['name'])
            message = 'Added Torrent *{0}*'.format(torrent_status['name'])
            log.info('Sending torrent added message to ' + str(self.__notifylist))
            self.send_message(message, to=self.__notifylist, parse_mode=MARKDOWN_PARSE_MODE)
        except Exception as e:
            log.error(e)

    def on_torrent_complete(self, torrent_id):
        if not self.__config['telegram_notify_finished']:
            return

        try:
            # torrent_id = str(alert.handle.info_hash())
            torrent = self.__torrent_manager[torrent_id]
            torrent_status = torrent.get_status(['name'])
            message = 'Finished Downloading *{0}*'.format(torrent_status['name'])
            log.info('Sending torrent finished message to ' + str(self.__notifylist))
            self.send_message(message, to=self.__notifylist, parse_mode=MARKDOWN_PARSE_MODE)
        except Exception as e:
            log.error(e)

    def on_torrent_event(self, torrent_id, event, *arg):
        if event == 'added':
            if arg[0]:
                # No further action as from_state (arg[0]) is True
                return

            self.on_torrent_added(torrent_id)
            return

        if event == 'complete':
            self.on_torrent_complete(torrent_id)
            return

    def list_torrents(self, filter=lambda _: True):
        return '\n'.join([format_torrent_info(t) for t
                          in self.__torrent_manager.torrents.values()
                          if filter(t)] or [STRINGS['no_items']])

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        log.debug('Set config')
        dirty = False
        for key in config.keys():
            if key in self.__config and self.__config[key] == config[key]:
                continue

            self.__config[key] = config[key]
            dirty = True

        if not dirty:
            return

        log.info('Config changed, reloading')
        self.__config.save()
        # Restart bot service
        self.restart()

    @export
    def restart(self):
        """Disable and enable plugin"""
        log.info('Restarting Telegramer plugin')
        self.disable()
        self.enable()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        log.debug('Get config')
        if not self.__config:
            return DEFAULT_PREFS

        return self.__config.config

    @export
    def send_test_message(self):
        """Sends Telegram test message"""
        log.info('Send test')
        self.__bot.send_sticker(self.__config['telegram_user'], choice(list(STICKERS.values())))
        self.send_message(STRINGS['test_success'])
