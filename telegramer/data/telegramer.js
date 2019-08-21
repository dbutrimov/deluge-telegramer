/*
Script: telegramer.js
    The client-side javascript code for the Telegramer plugin.

Copyright:
    (C) Noam 2016-2017 <noamgit@gmail.com>
    https://github.com/noam09

    Much credit to:
    (C) Innocenty Enikeew 2011 <enikesha@gmail.com>
    https://bitbucket.org/enikesha/deluge-xmppnotify

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3, or (at your option)
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, write to:
        The Free Software Foundation, Inc.,
        51 Franklin Street, Fifth Floor
        Boston, MA  02110-1301, USA.

    In addition, as a special exception, the copyright holders give
    permission to link the code of portions of this program with the OpenSSL
    library.
    You must obey the GNU General Public License in all respects for all of
    the code used other than OpenSSL. If you modify file(s) with this
    exception, you may extend this exception to your version of the file(s),
    but you are not obligated to do so. If you do not wish to do so, delete
    this exception statement from your version. If you delete this exception
    statement from all source files in the program, then also delete it here.
*/

TelegramerPage = Ext.extend(Ext.Panel, {
    title: _("Telegramer"),
    // header: false,
    autoHeight: true,
    border: false,

    initComponent: function () {
        TelegramerPage.superclass.initComponent.call(this);

        let fieldset = this.add({
            xtype: 'fieldset',
            title: _('Bot Settings'),
            border: false,
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'textfield',
            defaults: {
                width: '97%'
            }
        });
        this.telegram_token = fieldset.add({
            name: 'telegram_token',
            fieldLabel: _('Telegram bot token'),
            emptyText: _('Contact @BotFather and create a bot')
        });
        this.telegram_user = fieldset.add({
            name: 'telegram_user',
            fieldLabel: _('Telegram user ID'),
            emptyText: _('Contact @MyIDbot')
        });
        this.telegram_users = fieldset.add({
            name: 'telegram_users',
            fieldLabel: _('Additional IDs'),
            emptyText: _('IDs should be comma-separated')
        });
        this.telegram_users_notify = fieldset.add({
            name: 'telegram_users_notify',
            fieldLabel: _('Notify IDs'),
            emptyText: _('IDs should be comma-separated')
        });
        fieldset.add({
            xtype: 'container',
            layout: 'hbox',
            defaults: {
                width: '72',
                margins: '3 6 0 0'
            },
            items: [{
                xtype: 'button',
                name: 'telegram_test',
                text: _('Test'),
                scope: this,
                handler: this.onTestClick
            }, {
                xtype: 'button',
                name: 'telegram_reload',
                text: _('Reload'),
                scope: this,
                handler: this.onReloadClick
            }]
        });

        fieldset = this.add({
            xtype: 'fieldset',
            title: _('Notifications'),
            border: false,
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'checkbox',
            defaults: {
                width: '97%',
                height: 12,
                hideLabel: true
            }
        });
        this.telegram_notify_added = fieldset.add({
            name: 'telegram_notify_added',
            boxLabel: _('Send Telegram notification when torrents are added')
        });
        this.telegram_notify_finished = fieldset.add({
            name: 'telegram_notify_finished',
            boxLabel: _('Send Telegram notification when torrents finish')
        });

        fieldset = this.add({
            xtype: 'fieldset',
            title: _('Sorting'),
            border: false,
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'textfield',
            defaults: {
                width: '94%'
            },
            layout: {
                type: 'table',
                columns: 2,
                tableAttrs: {
                    style: 'width: 100%; border-spacing: 6px;'
                }
            }
        });
        fieldset.add({
            xtype: 'label',
            text: _('Category'),
            style: 'display: inline-block; text-align: center;'
        });
        fieldset.add({
            xtype: 'label',
            text: _('Directory'),
            style: 'display: inline-block; text-align: center;'
        });
        this.cat1 = fieldset.add({
            name: 'cat1',
            fieldLabel: _('Category 1')
        });
        this.dir1 = fieldset.add({
            name: 'dir1',
            fieldLabel: _('Directory 1')
        });
        this.cat2 = fieldset.add({
            name: 'cat2',
            fieldLabel: _('Category 2')
        });
        this.dir2 = fieldset.add({
            name: 'dir2',
            fieldLabel: _('Directory 2')
        });
        this.cat3 = fieldset.add({
            name: 'cat3',
            fieldLabel: _('Category 3')
        });
        this.dir3 = fieldset.add({
            name: 'dir3',
            fieldLabel: _('Directory 3')
        });

        this.on('show', this.onPreferencesShow, this);
    },

    onTestClick: function () {
        this.onApply();
        deluge.client.telegramer.send_test_message();
    },
    onReloadClick: function () {
        this.onApply();
        deluge.client.telegramer.restart();
    },

    onPreferencesShow: function () {
        deluge.client.telegramer.get_config({
            success: function (config) {
                this.telegram_token.setValue(config['telegram_token']);
                this.telegram_user.setValue(config['telegram_user']);
                this.telegram_users.setValue(config['telegram_users']);
                this.telegram_users_notify.setValue(config['telegram_users_notify']);

                this.telegram_notify_added.setValue(config['telegram_notify_added']);
                this.telegram_notify_finished.setValue(config['telegram_notify_finished']);

                this.cat1.setValue(config['cat1']);
                this.dir1.setValue(config['dir1']);
                this.cat2.setValue(config['cat2']);
                this.dir2.setValue(config['dir2']);
                this.cat3.setValue(config['cat3']);
                this.dir3.setValue(config['dir3']);
            },
            scope: this,
        });
    },

    onApply: function () {
        let config = {};

        config['telegram_token'] = this.telegram_token.getValue();
        config['telegram_user'] = this.telegram_user.getValue();
        config['telegram_users'] = this.telegram_users.getValue();

        config['telegram_notify_added'] = this.telegram_notify_added.getValue();
        config['telegram_notify_finished'] = this.telegram_notify_finished.getValue();

        config['cat1'] = this.cat1.getValue();
        config['dir1'] = this.dir1.getValue();
        config['cat2'] = this.cat2.getValue();
        config['dir2'] = this.dir2.getValue();
        config['cat3'] = this.cat3.getValue();
        config['dir3'] = this.dir3.getValue();

        deluge.client.telegramer.set_config(config);
    },

    onOk: function () {
        this.onApply();
    }
});


TelegramerPlugin = Ext.extend(Deluge.Plugin, {
    name: "Telegramer",

    onDisable: function () {
        deluge.preferences.removePage(this.prefsPage);
    },

    onEnable: function () {
        this.prefsPage = deluge.preferences.addPage(
            new TelegramerPage()
        );
    }
});

Deluge.registerPlugin('Telegramer', TelegramerPlugin);
