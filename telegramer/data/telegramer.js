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
        this.opts = new Deluge.OptionsManager();

        var fieldset = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Bot Settings'),
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'textfield'
        });
        this.opts.bind(
            'telegram_token',
            fieldset.add({
                fieldLabel: _('Telegram bot token'),
                name: 'telegram_token',
                width: '97%',
                emptyText: 'Contact @BotFather and create a bot'
            }));
        this.opts.bind(
            'telegram_user',
            fieldset.add({
                fieldLabel: _('Telegram user ID'),
                name: 'telegram_user',
                width: '97%',
                emptyText: 'Contact @MyIDbot'
            }));
        this.opts.bind(
            'telegram_users',
            fieldset.add({
                fieldLabel: _('Additional IDs'),
                name: 'telegram_users',
                width: '97%',
                emptyText: 'IDs should be comma-separated'
            }));
        this.opts.bind(
            'telegram_users_notify',
            fieldset.add({
                fieldLabel: _('Notify IDs'),
                name: 'telegram_users_notify',
                width: '97%',
                emptyText: _('IDs should be comma-separated')
            }));
        this.buttons = fieldset.add({
            xtype: 'container',
            layout: 'hbox',
            defaults: {
                width: '72',
                margins: '3 6 0 0'
            },
            items: [{
                xtype: 'button',
                name: 'telegram_test',
                text: 'Test',
            }, {
                xtype: 'button',
                name: 'telegram_reload',
                text: 'Reload',
            }]
        });

        fieldset = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Notifications'),
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'checkbox',
        });
        this.opts.bind(
            'telegram_notify_added',
            fieldset.add({
                hideLabel: true,
                boxLabel: _('Send Telegram notification when torrents are added'),
                width: '97%',
                height: 12,
                name: 'telegram_notify_added',
                id: 'telegram_notify_added'
            }));
        this.opts.bind(
            'telegram_notify_finished',
            fieldset.add({
                hideLabel: true,
                boxLabel: _('Send Telegram notification when torrents finish'),
                width: '97%',
                height: 12,
                name: 'telegram_notify_finished',
                id: 'telegram_notify_finished'
            }));

        fieldset = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Sorting'),
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'textfield',
            layout: {
                type: 'table',
                columns: 2,
                tableAttrs: {
                    style: 'width: 100%; border-spacing: 6px;'
                }
            },
            defaults: {
                width: '94%'
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
        this.opts.bind(
            'cat1',
            fieldset.add({
                fieldLabel: _('Category 1'),
                name: 'cat1',
                id: 'cat1',
                value: ''
            }));
        this.opts.bind(
            'dir1',
            fieldset.add({
                fieldLabel: _('Directory 1'),
                name: 'dir1',
                id: 'dir1',
                value: ''
            }));
        this.opts.bind(
            'cat2',
            fieldset.add({
                fieldLabel: _('Category 2'),
                name: 'cat2',
                id: 'cat2',
                value: ''
            }));
        this.opts.bind(
            'dir2',
            fieldset.add({
                fieldLabel: _('Directory 2'),
                name: 'dir2',
                id: 'dir2',
                value: ''
            }));
        this.opts.bind(
            'cat3',
            fieldset.add({
                fieldLabel: _('Category 3'),
                name: 'cat3',
                id: 'cat3',
                value: ''
            }));
        this.opts.bind(
            'dir3',
            fieldset.add({
                fieldLabel: _('Directory 3'),
                name: 'dir3',
                id: 'dir3',
                value: ''
            }));

        this.buttons.getComponent(0).setHandler(this.teleTest, this);
        this.buttons.getComponent(1).setHandler(this.teleReload, this);
        deluge.preferences.on('show', this.onPreferencesShow, this);
    },

    teleTest: function () {
        this.onApply();
        deluge.client.telegramer.send_test_message();
    },

    teleReload: function () {
        this.onApply();
        deluge.client.telegramer.restart();
    },

    onPreferencesShow: function () {
        deluge.client.telegramer.get_config({
            success: function (config) {
                if (!Ext.isEmpty(config['telegram_token'])) {
                    config['telegram_token'] = config['telegram_token'];
                }
                if (!Ext.isEmpty(config['telegram_user'])) {
                    config['telegram_user'] = config['telegram_user'];
                }
                if (!Ext.isEmpty(config['telegram_users'])) {
                    config['telegram_users'] = config['telegram_users'];
                }
                if (!Ext.isEmpty(config['telegram_users_notify'])) {
                    config['telegram_users_notify'] = config['telegram_users_notify'];
                }
                if (!Ext.isEmpty(config['telegram_notify_added'])) {
                    config['telegram_notify_added'] = config['telegram_notify_added'];
                }
                if (!Ext.isEmpty(config['telegram_notify_finished'])) {
                    config['telegram_notify_finished'] = config['telegram_notify_finished'];
                }
                if (!Ext.isEmpty(config['cat1'])) {
                    config['cat1'] = config['cat1'];
                }
                if (!Ext.isEmpty(config['cat2'])) {
                    config['cat2'] = config['cat2'];
                }
                if (!Ext.isEmpty(config['cat3'])) {
                    config['cat3'] = config['cat3'];
                }
                if (!Ext.isEmpty(config['dir1'])) {
                    config['dir1'] = config['dir1'];
                }
                if (!Ext.isEmpty(config['dir2'])) {
                    config['dir2'] = config['dir2'];
                }
                if (!Ext.isEmpty(config['dir3'])) {
                    config['dir3'] = config['dir3'];
                }
                //Ext.getCmp("mycheck").checked;
                this.opts.set(config);
            },
            scope: this,
        });
    },
    onApply: function (e) {
        var changed = this.opts.getDirty();
        if (!Ext.isObjectEmpty(changed)) {
            if (!Ext.isEmpty(changed['telegram_token'])) {
                changed['telegram_token'] = changed['telegram_token'];
            }
            if (!Ext.isEmpty(changed['telegram_user'])) {
                changed['telegram_user'] = changed['telegram_user'];
            }
            if (!Ext.isEmpty(changed['telegram_users'])) {
                changed['telegram_users'] = changed['telegram_users'];
            }
            if (!Ext.isEmpty(changed['telegram_notify_added'])) {
                changed['telegram_notify_added'] = changed['telegram_notify_added'];
            }
            if (!Ext.isEmpty(changed['telegram_notify_finished'])) {
                changed['telegram_notify_finished'] = changed['telegram_notify_finished'];
            }
            if (!Ext.isEmpty(changed['cat1'])) {
                changed['cat1'] = changed['cat1'];
            }
            if (!Ext.isEmpty(changed['cat2'])) {
                changed['cat2'] = changed['cat2'];
            }
            if (!Ext.isEmpty(changed['cat3'])) {
                changed['cat3'] = changed['cat3'];
            }
            if (!Ext.isEmpty(changed['dir1'])) {
                changed['dir1'] = changed['dir1'];
            }
            if (!Ext.isEmpty(changed['dir2'])) {
                changed['dir2'] = changed['dir2'];
            }
            if (!Ext.isEmpty(changed['dir3'])) {
                changed['dir3'] = changed['dir3'];
            }

            deluge.client.telegramer.set_config(changed, {
                success: this.onSetConfig,
                scope: this,
            });
        }
    },
    onSetConfig: function () {
        this.opts.commit();
    },
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
