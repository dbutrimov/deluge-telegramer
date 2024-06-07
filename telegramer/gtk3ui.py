# -*- coding: utf-8 -*-
#
# gtk3ui.py
#
# Copyright (C) 2016-2017 Noam <noamgit@gmail.com>
# https://github.com/noam09
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
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
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

import logging

import gi  # isort:skip (Required before Gtk import).

gi.require_version('Gtk', '3.0')  # NOQA: E402

# isort:imports-thirdparty
from gi.repository import Gtk

# isort:imports-firstparty
import deluge.component as component
from deluge.plugins.pluginbase import Gtk3PluginBase
from deluge.ui.client import client

# isort:imports-localfolder
from .common import get_resource

log = logging.getLogger(__name__)


class CategoryDialog(object):
    def __init__(self):
        self.name_entry = None
        self.directory_entry = None
        self.add_button = None
        self.apply_button = None
        self.dialog = None

    def show(self, name=None, directory=None, id_=None):
        builder = Gtk.Builder()
        builder.add_from_file(get_resource("category_dialog.ui"))

        dialog = builder.get_object('category_dialog')
        dialog.set_transient_for(component.get('Preferences').pref_dialog)

        name_entry = builder.get_object('name_entry')
        directory_entry = builder.get_object('directory_entry')
        add_button = builder.get_object('add_button')
        apply_button = builder.get_object('apply_button')

        name_entry.set_text(name or '')
        directory_entry.set_text(directory or '')

        if id_:
            dialog.set_title('Edit category')
            add_button.hide()
            apply_button.show()
        else:
            dialog.set_title('Add category')
            add_button.show()
            apply_button.hide()

        is_valid = name_entry.get_text() and directory_entry.get_text()
        add_button.set_sensitive(is_valid)
        apply_button.set_sensitive(is_valid)

        self.name_entry = name_entry
        self.directory_entry = directory_entry
        self.add_button = add_button
        self.apply_button = apply_button
        self.dialog = dialog

        builder.connect_signals(self)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = name_entry.get_text()
            directory = directory_entry.get_text()
            result = name, directory, id_
        else:
            result = None

        dialog.destroy()

        self.name_entry = None
        self.directory_entry = None
        self.add_button = None
        self.apply_button = None
        self.dialog = None

        return result

    def on_entry_changed(self, editable, user_data=None):
        is_valid = self.name_entry.get_text() and self.directory_entry.get_text()
        self.add_button.set_sensitive(is_valid)
        self.apply_button.set_sensitive(is_valid)

    def on_cancel_button_clicked(self, event=None):
        self.dialog.response(Gtk.ResponseType.CANCEL)

    def on_add_button_clicked(self, event=None):
        self.dialog.response(Gtk.ResponseType.OK)

    def on_apply_button_clicked(self, event=None):
        self.dialog.response(Gtk.ResponseType.OK)


class TelegramerPreferences(object):
    def __init__(self, plugin):
        self.plugin = plugin

        self.builder = None

        self.telegram_token = None
        self.telegram_user = None
        self.telegram_users = None
        self.telegram_users_notify = None
        self.telegram_notify_added = None
        self.telegram_notify_finished = None

        self.categories_store = None
        self.categories_selection = None
        self.edit_category_button = None
        self.delete_category_button = None

    def load(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(get_resource("config.ui"))

        self.plugin.add_preferences_page("Telegramer", self.builder.get_object("prefs_box"))

        self.telegram_notify_added = self.builder.get_object("telegram_notify_added")
        self.telegram_notify_finished = self.builder.get_object("telegram_notify_finished")
        self.telegram_token = self.builder.get_object("telegram_token")
        self.telegram_user = self.builder.get_object("telegram_user")
        self.telegram_users = self.builder.get_object("telegram_users")
        self.telegram_users_notify = self.builder.get_object("telegram_users_notify")

        self.categories_store = self.builder.get_object("categories_store")
        self.categories_selection = self.builder.get_object("categories_selection")
        self.edit_category_button = self.builder.get_object("edit_category")
        self.delete_category_button = self.builder.get_object("delete_category")

        store, iter = self.categories_selection.get_selected()
        has_selection = iter is not None
        self.edit_category_button.set_sensitive(has_selection)
        self.delete_category_button.set_sensitive(has_selection)

        self.plugin.register_hook("on_apply_prefs", self.on_apply_prefs)
        self.plugin.register_hook("on_show_prefs", self.on_show_prefs)

        self.builder.connect_signals(self)

    def unload(self):
        self.plugin.remove_preferences_page("Telegramer")
        self.plugin.deregister_hook("on_apply_prefs", self.on_apply_prefs)
        self.plugin.deregister_hook("on_show_prefs", self.on_show_prefs)

    def update_categories(self, categories):
        self.categories_store.clear()
        if not categories:
            return

        for category in categories:
            self.categories_store.append([category['id'], category['name'], category['directory']])

    def update_config(self, config):
        self.telegram_token.set_text(config["telegram_token"])
        self.telegram_user.set_text(config["telegram_user"])
        self.telegram_users.set_text(config["telegram_users"])
        self.telegram_users_notify.set_text(config["telegram_users_notify"])
        self.telegram_notify_added.set_active(config["telegram_notify_added"])
        self.telegram_notify_finished.set_active(config["telegram_notify_finished"])

        self.update_categories(config["categories"])

    def on_apply_prefs(self):
        log.debug("Telegramer: applying prefs for Telegramer")
        config = {
            "telegram_token": self.telegram_token.get_text(),
            "telegram_user": self.telegram_user.get_text(),
            "telegram_users": self.telegram_users.get_text(),
            "telegram_users_notify": self.telegram_users_notify.get_text(),
            "telegram_notify_added": self.telegram_notify_added.get_active(),
            "telegram_notify_finished": self.telegram_notify_finished.get_active()
        }
        client.telegramer.set_config(config)

    def on_show_prefs(self):
        client.telegramer.get_config().addCallback(self.update_config)

    def on_button_test_clicked(self, event=None):
        client.telegramer.send_test_message()

    def on_button_reload_clicked(self, event=None):
        client.telegramer.restart()

    def on_add_category_clicked(self, event=None):
        dialog = CategoryDialog()
        result = dialog.show()
        if not result:
            return

        name, directory, _ = result
        client.telegramer.add_category(name, directory)
        client.telegramer.get_categories().addCallback(self.update_categories)

    def on_edit_category_clicked(self, event=None):
        store, iter = self.categories_selection.get_selected()
        if not iter:
            return

        item = store[iter]
        id_ = item[0]
        name = item[1]
        directory = item[2]

        dialog = CategoryDialog()
        result = dialog.show(name, directory, id_)
        if not result:
            return

        name, directory, id_ = result
        client.telegramer.update_category(id_, name, directory)
        client.telegramer.get_categories().addCallback(self.update_categories)

    def on_delete_category_clicked(self, event=None):
        store, iter = self.categories_selection.get_selected()
        if not iter:
            return

        category_id = store[iter][0]
        client.telegramer.remove_category(category_id)
        client.telegramer.get_categories().addCallback(self.update_categories)

    def on_categories_selection_changed(self, event=None):
        store, iter = self.categories_selection.get_selected()
        has_selection = iter is not None
        self.edit_category_button.set_sensitive(has_selection)
        self.delete_category_button.set_sensitive(has_selection)


class Gtk3UI(Gtk3PluginBase):
    def enable(self):
        self.plugin = component.get('PluginManager')
        self.preferences = TelegramerPreferences(self.plugin)
        self.preferences.load()

    def disable(self):
        self.preferences.unload()
