odoo.define("pos_facturatool_cfdi.UsoCFDIPopup", function (require) {
    "use strict";

    const { parse } = require('web.field_utils');
    const { useErrorHandlers } = require('point_of_sale.custom_hooks');
    const {useListener} = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { useState } = owl;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const models = require('point_of_sale.models');

    // formerly UsoCFDIPopupWidget
    class UsoCFDIPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string|null} props.defaultUso Starting value of the popup.
         *
         * Resolve to { confirmed, payload } when used with showPopup method.
         * @confirmed {Boolean}
         * @payload {String}
         */
        constructor() {
            super(...arguments);
            useListener('accept-input', this.confirm);
            useListener('close-this-popup', this.cancel);
            let defaultValue = '';
            if (this.props.defaultUso != '') {
                defaultValue = this.props.defaultUso;
            }
            this.usoCFDI = defaultValue;
            //carga el array de UsosCFDI
            console.log('this.env.pos.db.usosCFDI');
            console.log(this.env.pos.db.usosCFDI);
            this.props.array = this.env.pos.db.usosCFDI;
            ////
        }
        confirm(event) {
            const bufferState = event.detail;
            this.usoCFDI = $('#usoCFDI').val();
            if (this.usoCFDI !== '') {
                super.confirm();
            }
        }
        getPayload() {
            return this.usoCFDI;
        }
        
    }
    UsoCFDIPopup.template = 'UsoCFDIPopup';
    UsoCFDIPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Uso del CFDI',
        body: '',
        cheap: false,
        defaultUso: 'G03',
        array: []
    };

    Registries.Component.add(UsoCFDIPopup);

    return UsoCFDIPopup;
});