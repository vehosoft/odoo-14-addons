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
                /*console.log(client);
                if(client.zip === '' || client.zip === false || client.zip === null){ 
                    alert("El cliente no tiene establecido Codigo Postal");
                    //return false;
                }*/
                if(this.currentOrder.is_to_invoice() && client){
                    console.log('toggleIsToInvoice ...');
                    console.log(this.currentOrder);
                    console.log(client);
                    if(typeof client.cfdi_uso == 'object'){
                        var cfdi_uso = client.cfdi_uso[1].split(' - ');
                        cfdi_uso = cfdi_uso[0];
                        this.currentOrder.set_uso_cfdi(cfdi_uso);
                    }
                    if(typeof client.regimen_fiscal == 'object'){
                        var regimen_fiscal = client.regimen_fiscal[1].split(' - ');
                        regimen_fiscal = regimen_fiscal[0];
                        this.currentOrder.set_regimen_fiscal(regimen_fiscal);
                    }
                    if(typeof client.zip == 'string'){
                        this.currentOrder.set_domicilio_fiscal(client.zip);
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
            async setRegimenFiscal() {
                // click_setRegimenFiscal
                const { confirmed, payload } = await this.showPopup('RegimenFiscalPopup', {
                    title: 'Regimen Fiscal',
                    defaultRegimenFiscal: this.currentOrder.get_regimen_fiscal()
                });
    
                if (confirmed) {
                    this.currentOrder.set_regimen_fiscal(payload);
                    let client = this.currentOrder.get('client');
                    let pos = this.env.pos;
                    let regimen = pos.db.RegimenFiscal_by_code[payload];
                    console.log('RegimenFiscalPopup confirm');
                    console.log(payload);
                    if(typeof regimen == 'object'){
                        let partnerId = await pos.rpc({
                            model: 'res.partner',
                            method: 'create_from_ui',
                            args: [{
                                id: client.id,
                                regimen_fiscal: parseInt(regimen.id) || false,
                            }],
                        });
                        if(partnerId) pos.load_new_partners();
                    }
                }
                
            }
            async setDomicilioFiscal() {
                // click_setDomicilioFiscal
                const { confirmed, payload } = await this.showPopup('DomicilioFiscalPopup', {
                    title: 'Domicilio Fiscal',
                    defaultDomicilioFiscal: this.currentOrder.get_domicilio_fiscal()
                });
    
                if (confirmed) {
                    this.currentOrder.set_domicilio_fiscal(payload);
                    let client = this.currentOrder.get('client');
                    let pos = this.env.pos;
                    console.log('DomicilioFiscalPopup confirm');
                    console.log(payload);
                    console.log(pos);
                    let partnerId = await pos.rpc({
                        model: 'res.partner',
                        method: 'create_from_ui',
                        args: [{
                            id: client.id,
                            zip: payload,
                        }],
                    });
                    if(partnerId) pos.load_new_partners();
                    //await pos.load_new_partners();
                    
                }
                
            }
        };
    Registries.Component.extend(PaymentScreen, CFDIButtonsPaymentScreen);
    return CFDIButtonsPaymentScreen;
});