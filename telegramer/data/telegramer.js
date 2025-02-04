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

TelegramerPage = Ext.extend(Ext.TabPanel, {
    title: _('Telegramer'),
    header: false,
    border: false,
    activeTab: 0,

    initComponent: function () {
        TelegramerPage.superclass.initComponent.call(this);

        let panel = this.add({
            title: _('General'),
            layout: 'fit',
        });
        let fieldset = panel.add({
            xtype: 'fieldset',
            title: _('Bot Settings'),
            border: false,
            autoHeight: true,
            labelAlign: 'top',
            defaultType: 'textfield',
            defaults: {
                anchor: '100%'
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
            autoHeight: true,
            layout: 'hbox',
            defaults: {
                width: '72',
                margins: '4 6 0 0'
            },
            items: [{
                xtype: 'button',
                name: 'telegram_test',
                text: _('Test'),
                handler: this.onTestClick,
                scope: this
            }, {
                xtype: 'button',
                name: 'telegram_reload',
                text: _('Reload'),
                handler: this.onReloadClick,
                scope: this
            }]
        });

        fieldset = panel.add({
            xtype: 'fieldset',
            title: _('Notifications'),
            border: false,
            autoHeight: true,
            defaultType: 'checkbox',
            defaults: {
                anchor: '100%',
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

        panel = this.add({
            title: _('Sorting'),
            layout: 'fit',
        });
        this.categoriesStore = new Ext.data.SimpleStore({
            fields: [
                {name: 'id', mapping: 'id'},
                {name: 'name', mapping: 'name'},
                {name: 'directory', mapping: 'directory'},
            ]
        });
        this.categoriesListView = new Ext.list.ListView({
            store: this.categoriesStore,
            columns: [
                {
                    header: _('Name'),
                    dataIndex: 'name',
                    width: 0.3,
                },
                {
                    header: _('Directory'),
                    dataIndex: 'directory',
                },
            ],
            singleSelect: true,
            disableHeaders: true,
        });
        this.categoriesListView.on('selectionchange', this.onCategorySelectionChange, this);

        this.categoriesPanel = panel.add({
            items: [this.categoriesListView],
            bbar: {
                items: [
                    {
                        text: _('Add'),
                        iconCls: 'icon-add',
                        handler: this.onAddCategoryClick,
                        scope: this,
                    },
                    {
                        text: _('Edit'),
                        iconCls: 'icon-edit',
                        handler: this.onEditCategoryClick,
                        scope: this,
                        disabled: true,
                    },
                    '->',
                    {
                        text: _('Remove'),
                        iconCls: 'icon-remove',
                        handler: this.onRemoveCategoryClick,
                        scope: this,
                        disabled: true,
                    },
                ],
            },
        });

        this.on('show', this.onPreferencesShow, this);
    },

    onCategorySelectionChange: function (sender, selections) {
        if (selections.length) {
            this.categoriesPanel.getBottomToolbar().items.get(1).enable();
            this.categoriesPanel.getBottomToolbar().items.get(3).enable();
        } else {
            this.categoriesPanel.getBottomToolbar().items.get(1).disable();
            this.categoriesPanel.getBottomToolbar().items.get(3).disable();
        }
    },
    updateCategories: function () {
        deluge.client.telegramer.get_categories({
            success: function (categories) {
                this.categoriesStore.loadData(categories);
            },
            scope: this,
        });
    },
    applyCategory: function (dialog, name, directory, id) {
        if (id) {
            deluge.client.telegramer.update_category(
                id,
                name,
                directory,
                {
                    success: function () {
                        dialog.hide();
                        this.updateCategories();
                    },
                    scope: this,
                });
        } else {
            deluge.client.telegramer.add_category(
                name,
                directory,
                {
                    success: function () {
                        dialog.hide();
                        this.updateCategories();
                    },
                    scope: this,
                });
        }
    },
    showCategoryDialog: function(name = '', directory = '', id = '') {
        if (!this.categoryDialog) {
            this.categoryDialog = new CategoryDialog();
            this.categoryDialog.on('apply', this.applyCategory, this);
        }

        this.categoryDialog.show(name, directory, id);
    },
    onAddCategoryClick: function () {
        this.showCategoryDialog();
    },
    onEditCategoryClick: function () {
        let category = this.categoriesListView.getSelectedRecords()[0];
        this.showCategoryDialog(category.get('name'), category.get('directory'), category.get('id'));
    },
    onRemoveCategoryClick: function () {
        let category = this.categoriesListView.getSelectedRecords()[0];
        deluge.client.telegramer.remove_category(category.get('id'), {
            success: function () {
                this.updateCategories();
            },
            scope: this,
        });
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

                this.categoriesStore.loadData(config['categories']);
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
