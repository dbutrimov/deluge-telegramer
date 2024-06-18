CategoryDialog = Ext.extend(Ext.Window, {
    layout: 'fit',
    width: 400,
    height: 130,
    closeAction: 'hide',
    modal: true,

    initComponent: function () {
        CategoryDialog.superclass.initComponent.call(this);

        this.addButton(_('Cancel'), this.onCancelClick, this);
        this.applyButton = this.addButton(_('Apply'), this.onApplyClick, this);

        this.form = this.add({
            xtype: 'form',
            baseCls: 'x-plain',
            bodyStyle: 'padding: 5px',
            items: [
                {
                    xtype: 'textfield',
                    fieldLabel: _('Name'),
                    name: 'name',
                    width: 270,
                    enableKeyEvents: true,
                    listeners: {
                        change: this.updateButtons,
                        keyup: this.updateButtons,
                        scope: this,
                    },
                },
                {
                    xtype: 'textfield',
                    fieldLabel: _('Directory'),
                    name: 'directory',
                    width: 270,
                    enableKeyEvents: true,
                    listeners: {
                        change: this.updateButtons,
                        keyup: this.updateButtons,
                        scope: this,
                    },
                },
            ],
        });

        this.addEvents('apply');
    },

    onCancelClick: function () {
        this.hide();
    },

    onApplyClick: function () {
        let values = this.form.getForm().getFieldValues();
        this.fireEvent(
            'apply',
            this,
            values.name,
            values.directory,
            this.id
        );
    },

    validateValues: function() {
        let values = this.form.getForm().getFieldValues();
        return !Object.values(values).some(v => !v);
    },

    updateButtons: function() {
        if (this.validateValues()) {
            this.applyButton.enable();
        } else {
            this.applyButton.disable();
        }
    },

    show: function (name = '', directory = '', id = '') {
        if (id) {
            this.setTitle(_('Edit Category'));
            this.applyButton.setText(_('Save'));
        } else {
            this.setTitle(_('Add Category'));
            this.applyButton.setText(_('Add'));
        }

        this.form.getForm().setValues({
            name: name,
            directory: directory,
        });

        this.id = id;
        this.updateButtons();

        CategoryDialog.superclass.show.call(this);
    },
});
