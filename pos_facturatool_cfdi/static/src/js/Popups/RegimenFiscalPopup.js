odoo.define("pos_facturatool_cfdi.RegimenFiscalPopup", function (require) {
    "use strict";

    const { parse } = require('web.field_utils');
    const { useErrorHandlers } = require('point_of_sale.custom_hooks');
    const {useListener} = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { useState } = owl;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const models = require('point_of_sale.models');

    // formerly UsoCFDIPopupWidget
    class RegimenFiscalPopup extends AbstractAwaitablePopup {
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
            if (this.props.defaultRegimenFiscal != '') {
                defaultValue = this.props.defaultRegimenFiscal;
            }
            this.RegimenFiscal = defaultValue;
            //carga el array de RegimenFiscal
            console.log('this.env.pos.db.RegimenFiscal');
            console.log(this.env.pos.db.RegimenFiscal);
            this.props.array = this.env.pos.db.RegimenFiscal;
            ////
        }
        confirm(event) {
            const bufferState = event.detail;
            this.RegimenFiscal = $('#RegimenFiscal').val();
            if (this.RegimenFiscal !== '') {
                super.confirm();
            }
        }
        getPayload() {
            return this.RegimenFiscal;
        }
        
    }
    RegimenFiscalPopup.template = 'RegimenFiscalPopup';
    RegimenFiscalPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Regimen Fiscal',
        body: '',
        cheap: false,
        //defaultRegimenFiscal: 'G03',
        array: []
    };

    Registries.Component.add(RegimenFiscalPopup);

    return RegimenFiscalPopup;
});