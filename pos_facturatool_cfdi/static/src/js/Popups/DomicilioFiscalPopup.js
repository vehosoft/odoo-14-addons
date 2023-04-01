odoo.define("pos_facturatool_cfdi.DomicilioFiscalPopup", function (require) {
    "use strict";

    const { parse } = require('web.field_utils');
    const { useErrorHandlers } = require('point_of_sale.custom_hooks');
    const {useListener} = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { useState } = owl;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const models = require('point_of_sale.models');

    // formerly 
    class DomicilioFiscalPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string|null} props.defaultDomicilioFiscal Starting value of the popup.
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
            if (this.props.defaultDomicilioFiscal != '') {
                defaultValue = this.props.defaultDomicilioFiscal;
            }
            this.DomicilioFiscal = defaultValue;
        }
        confirm(event) {
            const bufferState = event.detail;
            this.DomicilioFiscal = $('#DomicilioFiscal').val();
            if (this.DomicilioFiscal !== '') {
                super.confirm();
            }
        }
        getPayload() {
            return this.DomicilioFiscal;
        }
        
    }
    DomicilioFiscalPopup.template = 'DomicilioFiscalPopup';
    DomicilioFiscalPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Domicilio Fiscal',
        body: '',
        cheap: false,
    };

    Registries.Component.add(DomicilioFiscalPopup);

    return DomicilioFiscalPopup;
});