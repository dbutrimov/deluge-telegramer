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

import base64
import logging
import os
import random
import uuid

import urllib3
from deluge import component
from deluge.common import fsize, fpcnt, fspeed, fpeer, ftime, fdate, is_url, is_magnet
from deluge.configmanager import ConfigManager
from deluge.core.core import Core as DelugeCore
from deluge.core.eventmanager import EventManager
from deluge.core.rpcserver import export
from deluge.core.torrentmanager import TorrentManager
from deluge.plugins.pluginbase import CorePluginBase
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, MAX_MESSAGE_LENGTH
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, BaseFilter, ConversationHandler
from telegram.utils.request import Request

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
    'categories': []
}

PREFS_TO_RESTART = [
    'telegram_token'
]

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
    'canceled': 'Operation canceled',
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


def _send_message(bot, chat_id, text, **kwargs):
    to_send = text
    text_length = len(to_send)
    while text_length > 0:
        if text_length <= MAX_MESSAGE_LENGTH:
            bot.send_message(chat_id, to_send, **kwargs)
            break

        part = to_send[:MAX_MESSAGE_LENGTH]
        first_lnbr = part.rfind('\n')
        if first_lnbr < 0:
            bot.send_message(chat_id, part, **kwargs)
            to_send = to_send[MAX_MESSAGE_LENGTH:]
            text_length = len(to_send)
            continue

        bot.send_message(chat_id, part[:first_lnbr], **kwargs)
        to_send = to_send[(first_lnbr + 1):]
        text_length = len(to_send)

    return text


def _reply_text(update, text, **kwargs):
    to_send = text
    text_length = len(to_send)
    while text_length > 0:
        if text_length <= MAX_MESSAGE_LENGTH:
            update.message.reply_text(to_send, **kwargs)
            break

        part = to_send[:MAX_MESSAGE_LENGTH]
        first_lnbr = part.rfind('\n')
        if first_lnbr < 0:
            update.message.reply_text(part, **kwargs)
            to_send = to_send[MAX_MESSAGE_LENGTH:]
            text_length = len(to_send)
            continue

        update.message.reply_text(part[:first_lnbr], **kwargs)
        to_send = to_send[(first_lnbr + 1):]
        text_length = len(to_send)

    return text


class Core(CorePluginBase):
    def __init__(self, *args):
        super(Core, self).__init__(*args)

        self._core = component.get('Core')  # type: DelugeCore
        self._event_manager = component.get('EventManager')  # type: EventManager
        self._torrent_manager = component.get('TorrentManager')  # type: TorrentManager
        self._registered_events = {}

        self._bot = None
        self._updater = None

        self._config = None
        self._whitelist = []
        self._notifylist = []
        self._commands = {
            # '?': self._help,  # invalid command
            'help': self._help,
            'start': self._help,
            'commands': self._help,
            'list': self._list,
            'down': self._list_downloading,
            'downloading': self._list_downloading,
            'up': self._list_uploading,
            'uploading': self._list_uploading,
            'seed': self._list_uploading,
            'seeding': self._list_uploading,
            'paused': self._list_paused,
            'queued': self._list_paused,
            'cancel': self._cancel,
            'reload': self.restart
        }

        log.debug('Initialize class')

    def _init_users(self, config):
        self._whitelist = []
        self._notifylist = []

        if config['telegram_user']:
            self._whitelist.append(str(config['telegram_user']))
            self._notifylist.append(str(config['telegram_user']))
        if config['telegram_users']:
            telegram_user_list = filter(None, [x.strip() for x in
                                               str(config['telegram_users']).split(',')])
            # Merge with whitelist and remove duplicates - order will be lost
            self._whitelist = list(set(self._whitelist + telegram_user_list))
            log.debug('Whitelist: ' + str(self._whitelist))
        if config['telegram_users_notify']:
            n = filter(None, [x.strip() for x in
                              str(config['telegram_users_notify']).split(',')])
            telegram_user_list_notify = [a for a in n if is_int(a)]
            # Merge with notifylist and remove duplicates - order will be lost
            self._notifylist = list(set(self._notifylist + telegram_user_list_notify))
            log.debug('Notify: ' + str(self._notifylist))

    def enable(self):
        self._whitelist = []
        self._notifylist = []

        try:
            self._config = ConfigManager('telegramer.conf', DEFAULT_PREFS)

            telegram_token = self._config['telegram_token']
            if not telegram_token:
                return

            self._init_users(self._config)

            self._bot = Bot(telegram_token, request=Request(con_pool_size=8))
            # Create the EventHandler and pass it bot's token.
            self._updater = Updater(bot=self._bot, use_context=True)
            # Get the dispatcher to register handlers
            dispatcher = self._updater.dispatcher

            # Add conversation handler with the different states
            dispatcher.add_handler(
                ConversationHandler(
                    entry_points=[
                        CommandHandler('add', self._add),
                        MessageHandler(magnet_filter, self._add_magnet),
                        MessageHandler(url_filter, self._add_url),
                        MessageHandler(Filters.document, self._add_torrent)
                    ],
                    states={
                        SET_CATEGORY: [MessageHandler(Filters.text, self._set_category)],
                        SET_LABEL: [MessageHandler(Filters.text, self._set_label)],
                        SET_TORRENT_TYPE: [MessageHandler(Filters.text, self._set_torrent_type)],
                        SET_MAGNET: [MessageHandler(Filters.text, self._set_magnet)],
                        SET_TORRENT: [MessageHandler(Filters.document, self._set_torrent)],
                        SET_URL: [MessageHandler(Filters.text, self._set_url)]
                    },
                    fallbacks=[CommandHandler('cancel', self._cancel)]
                )
            )

            for key, value in self._commands.items():
                dispatcher.add_handler(CommandHandler(key, value))

            # Log all errors
            dispatcher.add_error_handler(self._handle_error)

            # Start the Bot
            self._updater.start_polling(poll_interval=0.05)

            self._connect_events()

        except Exception as e:
            log.exception(e)

    def disable(self):
        try:
            self._whitelist = None
            self._notifylist = None

            self._disconnect_events()
            self._bot = None

            if self._updater:
                self._updater.stop()
                self._updater = None

        except Exception as e:
            log.exception(e)

    def update(self):
        pass

    def _handle_error(self, update, context):
        log.warning('Update caused an error "{0}":\n{1}'.format(context.error, update))
        update.message.reply_text(
            "{0}\n{1}".format(STRINGS['error'], context.error),
            reply_markup=ReplyKeyboardRemove())

    def _is_white_user(self, user_id):
        return self._whitelist and user_id in self._whitelist

    def _is_notify_user(self, user_id):
        return self._notifylist and user_id in self._notifylist

    def _verify_user(self, update, context):
        if self._is_white_user(str(update.message.chat.id)):
            return None

        update.message.reply_text(STRINGS['invalid_user'], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def _notify(self, bot, text, to=None, **kwargs):
        if not to:
            to = self._config['telegram_user']

        if not isinstance(to, (list,)):
            to = [to]

        for chat_id in to:
            # Every outgoing message filtered here
            if not self._is_white_user(chat_id) and not self._is_notify_user(chat_id):
                continue

            _send_message(bot, chat_id, text, **kwargs)

        return text

    def _cancel(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        log.info("User {0} canceled the conversation.".format(update.message.chat.id))

        context.user_data.clear()
        update.message.reply_text(STRINGS['canceled'], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def _help(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        chat_id = str(update.message.chat.id)
        log.debug(chat_id + " in whitelist")
        log.debug("telegram_send to " + chat_id)
        update.message.reply_text(HELP_MESSAGE, parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def _list_torrents(self, filter=lambda _: True):
        return '\n'.join([format_torrent_info(t) for t
                          in self._torrent_manager.torrents.values()
                          if filter(t)] or [STRINGS['no_items']])

    def _list(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        # log.error(self.list_torrents())
        _reply_text(
            update,
            self._list_torrents(lambda t:
                                t.get_status(('state',))['state'] in
                                ('Active', 'Downloading', 'Seeding',
                                 'Paused', 'Checking', 'Error', 'Queued')),
            parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def _list_downloading(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        _reply_text(
            update,
            self._list_torrents(lambda t: t.get_status(('state',))['state'] == 'Downloading'),
            parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def _list_uploading(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        _reply_text(
            update,
            self._list_torrents(lambda t: t.get_status(('state',))['state'] == 'Seeding'),
            parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def _list_paused(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        _reply_text(
            update,
            self._list_torrents(lambda t: t.get_status(('state',))['state'] in ('Paused', 'Queued')),
            parse_mode=MARKDOWN_PARSE_MODE)
        return ConversationHandler.END

    def _proc_set_category(self, update, context):
        text = update.message.text
        log.info("set_category: {0}".format(text))

        if text != STRINGS['no_category']:
            move_completed_path = None
            for category in self._config['categories']:
                category_name = category['name']
                if category_name == text:
                    move_completed_path = category['directory']
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
                context.user_data['torrent_options'] = {
                    'move_completed_path': move_completed_path,
                    'move_completed': True
                }

        context.user_data['category'] = text
        return None

    def _proc_set_label(self, update, context):
        label = update.message.text.lower()
        log.info("set_label: {0}".format(label))

        context.user_data['label'] = label
        return None

    def _proc_set_torrent_type(self, update, context):
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

    def _proc_set_magnet(self, update, context):
        magnet = update.message.text
        log.info("set_magnet: {0}".format(magnet))

        if not is_magnet(magnet):
            update.message.reply_text(STRINGS['not_magnet'], reply_markup=ReplyKeyboardRemove())
            return SET_MAGNET

        context.user_data['magnet'] = magnet
        return None

    def _proc_set_torrent(self, update, context):
        document = update.message.document
        log.info("set_torrent: {0}".format(document))

        file_ext = os.path.splitext(document.file_name)[-1].lower()
        if document.mime_type != 'application/x-bittorrent' and file_ext != '.torrent':
            update.message.reply_text(STRINGS['not_file'], reply_markup=ReplyKeyboardRemove())
            return SET_TORRENT

        try:
            # Get file info
            file_info = context.bot.get_file(document.file_id)

            # Download file
            response = http.request('GET', file_info.file_path, headers=HEADERS)
            file_content = response.data

            # Base64 encode file data
            context.user_data['torrent'] = base64.b64encode(file_content)
            context.user_data['file_name'] = document.file_name
        except Exception as e:
            log.error(e)
            update.message.reply_text(STRINGS['download_fail'], reply_markup=ReplyKeyboardRemove())
            return SET_TORRENT

        return None

    def _proc_set_url(self, update, context):
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
            context.user_data['torrent'] = base64.b64encode(file_content)
            # context.user_data['file_name'] = ''  # TODO: extract file name from url
        except Exception as e:
            log.error(e)
            update.message.reply_text(STRINGS['download_fail'], reply_markup=ReplyKeyboardRemove())
            return SET_URL

        return None

    def _proc_conv_step(self, step, update, context):
        if step == SET_CATEGORY:
            return self._proc_set_category(update, context)
        if step == SET_LABEL:
            return self._proc_set_label(update, context)
        if step == SET_TORRENT_TYPE:
            return self._proc_set_torrent_type(update, context)
        if step == SET_MAGNET:
            return self._proc_set_magnet(update, context)
        if step == SET_TORRENT:
            return self._proc_set_torrent(update, context)
        if step == SET_URL:
            return self._proc_set_url(update, context)

        return None

    def _proc_conv(self, step, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        step_result = self._proc_conv_step(step, update, context)
        if step_result:
            return step_result

        if 'category' not in context.user_data:
            if 'categories' in self._config:
                categories = self._config['categories']
                if len(categories) > 0:
                    keyboard_options = []
                    for category in categories:
                        category_directory = category['directory']
                        if not os.path.isdir(category_directory):
                            continue

                        category_name = category['name']
                        log.debug(category_name + ' ' + category_directory)
                        keyboard_options.append([category_name])

                    keyboard_options.append([STRINGS['no_category']])

                    update.message.reply_text(
                        '{0}\n{1}'.format(STRINGS['which_cat'], STRINGS['cancel']),
                        reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

                    return SET_CATEGORY

            context.user_data['category'] = STRINGS['no_category']

        if 'label' not in context.user_data:
            keyboard_options = []
            try:
                if 'Label' in self._core.get_enabled_plugins():
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

            context.user_data['label'] = STRINGS['no_label'].lower()

        if 'torrent' not in context.user_data and 'magnet' not in context.user_data:
            # Request torrent type
            keyboard_options = [['Magnet'], ['.torrent'], ['URL']]
            update.message.reply_text(
                STRINGS['what_kind'],
                reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

            return SET_TORRENT_TYPE

        torrent_id = None
        error = None
        if 'torrent' in context.user_data:
            file_name = context.user_data.get('file_name') or ''
            torrent = context.user_data['torrent']
            torrent_options = context.user_data.get('torrent_options') or {}
            log.info("Adding torrent `{0}` from base64 string using options `{1}` ..."
                     .format(file_name, torrent_options))
            try:
                torrent_id = self._core.add_torrent_file(file_name, torrent, torrent_options)
            except Exception as e:
                log.error(e)
                error = e
        elif 'magnet' in context.user_data:
            magnet = context.user_data['magnet']
            torrent_options = context.user_data.get('torrent_options') or {}
            log.debug('Adding torrent from magnet URI `{0}` using options `{1}` ...'
                      .format(magnet, torrent_options))
            try:
                torrent_id = self._core.add_torrent_magnet(magnet, torrent_options)
            except Exception as e:
                log.error(e)
                error = e

        if torrent_id:
            self._apply_label(torrent_id, context.user_data)
            update.message.reply_text(
                'Added Torrent ID *{0}*'.format(torrent_id),
                parse_mode=MARKDOWN_PARSE_MODE,
                reply_markup=ReplyKeyboardRemove())
        else:
            if error:
                update.message.reply_text(
                    "{0}\n{1}".format(STRINGS['error'], error),
                    reply_markup=ReplyKeyboardRemove())
            else:
                update.message.reply_text(STRINGS['error'], reply_markup=ReplyKeyboardRemove())

        context.user_data.clear()

        return ConversationHandler.END

    def _add(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        context.user_data.clear()
        return self._proc_conv(NEXT, update, context)

    def _add_magnet(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        context.user_data.clear()
        return self._proc_conv(SET_MAGNET, update, context)

    def _add_url(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        context.user_data.clear()
        return self._proc_conv(SET_URL, update, context)

    def _add_torrent(self, update, context):
        verify_result = self._verify_user(update, context)
        if verify_result:
            return verify_result

        context.user_data.clear()
        return self._proc_conv(SET_TORRENT, update, context)

    def _set_category(self, update, context):
        return self._proc_conv(SET_CATEGORY, update, context)

    def _set_label(self, update, context):
        return self._proc_conv(SET_LABEL, update, context)

    def _set_torrent_type(self, update, context):
        return self._proc_conv(SET_TORRENT_TYPE, update, context)

    def _set_magnet(self, update, context):
        return self._proc_conv(SET_MAGNET, update, context)

    def _set_torrent(self, update, context):
        return self._proc_conv(SET_TORRENT, update, context)

    def _set_url(self, update, context):
        return self._proc_conv(SET_URL, update, context)

    def _apply_label(self, torrent_id, options):
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
            self._core.enable_plugin('Label')
            label_plugin = component.get('CorePlugin.Label')
            if not label_plugin:
                return

            # Add label if neccessary
            if label not in label_plugin.get_labels():
                label_plugin.add(label)

            label_plugin.set_torrent(torrent_id, label)
            log.debug('Set label `{0}` to torrent `{1}`'.format(label, torrent_id))
        except Exception as e:
            log.error(e)

    def _connect_events(self):
        event_manager = self._event_manager
        if not event_manager:
            return

        # Go through the commands list and register event handlers
        for event in EVENT_MAP.keys():
            if event in self._registered_events:
                continue

            def create_event_handler(ev):
                def event_handler(torrent_id, *arg):
                    self._handle_torrent_event(torrent_id, ev, *arg)

                return event_handler

            handler = create_event_handler(event)
            event_manager.register_event_handler(EVENT_MAP[event], handler)
            self._registered_events[event] = handler

    def _disconnect_events(self):
        event_manager = self._event_manager
        if not event_manager:
            return

        for event, handler in self._registered_events.items():
            event_manager.deregister_event_handler(EVENT_MAP[event], handler)

    def _handle_torrent_added(self, torrent_id):
        if not self._config['telegram_notify_added']:
            return

        bot = self._bot
        if not bot:
            return

        try:
            # torrent_id = str(alert.handle.info_hash())
            torrent = self._torrent_manager[torrent_id]
            torrent_status = torrent.get_status(['name'])
            message = 'Added Torrent *{0}*'.format(torrent_status['name'])
            log.info('Sending torrent added message to ' + str(self._notifylist))
            self._notify(bot, message, to=self._notifylist, parse_mode=MARKDOWN_PARSE_MODE)
        except Exception as e:
            log.error(e)

    def _handle_torrent_complete(self, torrent_id):
        if not self._config['telegram_notify_finished']:
            return

        bot = self._bot
        if not bot:
            return

        try:
            # torrent_id = str(alert.handle.info_hash())
            torrent = self._torrent_manager[torrent_id]
            torrent_status = torrent.get_status(['name'])
            message = 'Finished Downloading *{0}*'.format(torrent_status['name'])
            log.info('Sending torrent finished message to ' + str(self._notifylist))
            self._notify(bot, message, to=self._notifylist, parse_mode=MARKDOWN_PARSE_MODE)
        except Exception as e:
            log.error(e)

    def _handle_torrent_event(self, torrent_id, event, *arg):
        if event == 'added':
            if arg[0]:
                # No further action as from_state (arg[0]) is True
                return

            self._handle_torrent_added(torrent_id)
            return

        if event == 'complete':
            self._handle_torrent_complete(torrent_id)
            return

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
        if not self._config:
            return DEFAULT_PREFS

        return self._config.config

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        log.debug('Set config')
        dirty = False
        restart = False
        for key in config.keys():
            if key in self._config and self._config[key] == config[key]:
                continue

            self._config[key] = config[key]
            dirty = True

            if key in PREFS_TO_RESTART:
                restart = True

        if not dirty:
            return

        log.info('Config changed, reloading')
        self._config.save()

        if not restart:
            # Reload users white/notify list
            self._init_users(self._config)
            return

        # Restart bot service
        self.restart()

    @export
    def get_categories(self):
        if not self._config or 'categories' not in self._config:
            return []

        return self._config['categories']

    @export
    def add_category(self, name, directory):
        categories = self._config['categories']
        categories.append({'id': uuid.uuid4().hex, 'name': name, 'directory': directory})

        self._config['categories'] = categories
        self._config.save()

    @export
    def update_category(self, id_, name, directory):
        categories = self._config['categories']
        indices = [i for i, x in enumerate(categories) if x['id'] == id_]
        if len(indices) <= 0:
            log.warning('Unknown category id: {0}'.format(id_))
            return

        category = categories[indices[0]]
        category['name'] = name
        category['directory'] = directory

        self._config['categories'] = categories
        self._config.save()

    @export
    def remove_category(self, id_):
        categories = self._config['categories']
        indices = [i for i, x in enumerate(categories) if x['id'] == id_]
        if len(indices) <= 0:
            log.warning('Unknown category id: {0}'.format(id_))
            return

        categories.pop(indices[0])

        self._config['categories'] = categories
        self._config.save()

    @export
    def send_test_message(self):
        """Sends Telegram test message"""

        bot = self._bot
        if not bot:
            return

        bot.send_sticker(self._config['telegram_user'], random.choice(list(STICKERS.values())))
        self._notify(bot, STRINGS['test_success'])
