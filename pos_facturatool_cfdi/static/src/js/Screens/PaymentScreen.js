odoo.define("pos_facturatool_cfdi.PaymentScreen", function (require) {
    "use strict";

    const { parse } = require('web.field_utils');
    const { useErrorHandlers } = require('point_of_sale.custom_hooks');
    const {useListener} = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const { useState } = owl;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PaymentScreen = require('point_of_sale.PaymentScreen');

    const CFDIButtonsPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            toggleIsToInvoice() {
                // click_invoice
                super.toggleIsToInvoice();
                var client = this.currentOrder.get('client')
                if(this.currentOrder.is_to_invoice() && client){
                    console.log('toggleIsToInvoice');
                    console.log(client);
                    console.log(client.cfdi_uso);
                    if(typeof client.cfdi_uso == 'object'){
                        var cfdi_uso = client.cfdi_uso[1].split(' - ');
                        cfdi_uso = cfdi_uso[0];
                        this.currentOrder.set_uso_cfdi(cfdi_uso);
                    }
                }
            }
            async setUsoCFDI() {
                // click_usoCFDI
                const { confirmed, payload } = await this.showPopup('UsoCFDIPopup', {
                    title: 'Uso del CFDI',
                    defaultUso: this.currentOrder.get_uso_cfdi()
                });
    
                if (confirmed) {
                    console.log(payload);
                    this.currentOrder.set_uso_cfdi(payload);
                }
                
            }
        };
    Registries.Component.extend(PaymentScreen, CFDIButtonsPaymentScreen);
    return CFDIButtonsPaymentScreen;
});