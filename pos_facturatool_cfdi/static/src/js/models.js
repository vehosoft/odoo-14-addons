odoo.define("pos_facturatool_cfdi.models", function (require) {
    "use strict";

    const models = require("point_of_sale.models");
    models.load_fields("res.partner", ["cfdi_uso"]);
    models.load_fields("res.company", ["zip"]);
    models.load_fields("product.product", ["clave_sat"]);

    models.load_models([
        {
            model: "sat.cfdi.uso",
            label: "UsoCFDI",
            before: "res.partner",
            fields: ["code", "name"],
            loaded: function(self, usosCFDI) {
                self.db.usosCFDI = usosCFDI;
                self.db.usosCFDI_by_code = usosCFDI.reduce(
                    (map, rec) => ((map[rec.code] = rec), map),
                    {}
                );
            },
        },
    ]);

    var PosModelSuper = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        push_and_invoice_order: function (order) {
            var self = this;
            var invoiced = new Promise(function (resolveInvoiced, rejectInvoiced) {
                if(!order.get_client()){
                    rejectInvoiced({code:400, message:'Missing Customer', data:{}});
                }
                else {
                    var order_id = self.db.add_order(order.export_as_JSON());
    
                    self.flush_mutex.exec(function () {
                        var done =  new Promise(function (resolveDone, rejectDone) {
                            // send the order to the server
                            // we have a 30 seconds timeout on this push.
                            // FIXME: if the server takes more than 30 seconds to accept the order,
                            // the client will believe it wasn't successfully sent, and very bad
                            // things will happen as a duplicate will be sent next time
                            // so we must make sure the server detects and ignores duplicated orders
    
                            var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:30000, to_invoice:true});
    
                            transfer.catch(function (error) {
                                rejectInvoiced(error);
                                rejectDone();
                            });
    
                            // on success, get the order id generated by the server
                            transfer.then(function(order_server_id){
                                console.log('push_and_invoice_order facturatool.....');
                                console.log('order_server_id');
                                console.log(order_server_id);
                                // generate the pdf and download it
                                if (order_server_id.length) {
                                    ////////
                                    self.rpc({
                                        model: 'pos.order',
                                        method: 'get_invoice_data',
                                        args: [order_server_id],
                                        kwargs: {context: self.session.user_context},
                                    }, {
                                        timeout: 30000,
                                    })
                                    .then(function (order_invoice_data) {
                                        console.log('get_invoice_data');
                                        console.log(order_invoice_data);
                                        order.order_name = order_invoice_data[0].name;
                                        order.account_move = order_invoice_data[0].account_move;
                                        self.do_action('point_of_sale.pos_invoice_report',{additional_context:{
                                            active_ids:order_server_id,
                                        }}).then(function () {
                                            resolveInvoiced(order_server_id);
                                            resolveDone();
                                        }).guardedCatch(function (error) {
                                            rejectInvoiced({code:401, message:'Backend Invoice', data:{order: order}});
                                            rejectDone();
                                        });
                                        
                                    }).catch(function (reason){
                                        rejectInvoiced({code:401, message:'Backend Invoice', data:{order: order}});
                                        rejectDone();
                                    })    
                                    ////////
                                    
                                } else if (order_server_id.length) {
                                    resolveInvoiced(order_server_id);
                                    resolveDone();
                                } else {
                                    // The order has been pushed separately in batch when
                                    // the connection came back.
                                    // The user has to go to the backend to print the invoice
                                    rejectInvoiced({code:401, message:'Backend Invoice', data:{order: order}});
                                    rejectDone();
                                }
                            });
                            return done;
                        });
                    });
                }
            });
    
            return invoiced;
        },
    });
    
    var OrderlineSuper = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        export_for_printing: function(){
            var receiptLine = OrderlineSuper.export_for_printing.apply(this, arguments);
            var clave_sat = this.get_product().clave_sat;
            if(typeof clave_sat == 'object'){
                clave_sat = clave_sat[1].split(' - ');
                clave_sat = clave_sat[0];
                receiptLine.clave_sat = clave_sat;
            }else receiptLine.clave_sat = '';
            return receiptLine;
        }
    });  

    var OrderSuper = models.Order.prototype;
    models.Order = models.Order.extend({
        
        initialize: function(attributes,options){
            var initialize_resp = OrderSuper.initialize.apply(this, arguments);
            this.order_name = '';
            this.uso_cfdi = '';
            this.account_move = false;
            //return OrderSuper.initialize.call(this, attributes,options);
            return initialize_resp;
        },
        set_uso_cfdi: function(value) {
            this.uso_cfdi = value;
        },
        get_uso_cfdi: function() {
            console.log(this);
            return this.uso_cfdi;
        },
        have_uso_cfdi: function(){
            if(this.uso_cfdi!='') return true;
            else return false;
        },
        export_as_JSON: function() {
            var json = OrderSuper.export_as_JSON.apply(this, arguments);
            var order = this.pos.get('selectedOrder');
            console.log('export_as_JSON');
            if (order) {
                console.log(order);
                json.uso_cfdi = this.uso_cfdi;
            }
            console.log(json);
            return json;
        },
        export_for_printing: function(){
            var receipt = OrderSuper.export_for_printing.apply(this, arguments);
            var company = this.pos.company;
            var client  = this.get('client');
            console.log('export_for_printing');
            console.log(this.to_invoice);
            console.log(receipt);
            //if(this.to_invoice){
                receipt.to_invoice = this.to_invoice;
                receipt.uso_cfdi = this.uso_cfdi;
                receipt.account_move = this.account_move;
                if(this.account_move && this.to_invoice){
                    receipt.account_move.cfdi_cadena_original_wrapped = this.generate_wrapped_cfdi_cadena_original();
                    receipt.account_move.cfdi_sello_digital_wrapped = this.generate_wrapped_cfdi_string(receipt.account_move.cfdi_sello_digital);
                    receipt.account_move.cfdi_sello_sat_wrapped = this.generate_wrapped_cfdi_string(receipt.account_move.cfdi_sello_sat);
                }
                receipt.company.address = company.state_id[1]+', C.P. '+company.zip;
            //}
            return receipt;
        },
        generate_wrapped_cfdi_cadena_original: function() {
            var MAX_LENGTH = 60; // 40 * line ratio of .6
            var wrapped = [];
            var name = this.account_move.cfdi_cadena_original;
            var ciclos = name.length / MAX_LENGTH;
            var ciclo = 1;
            var indiceA = 0;
            var indiceB = MAX_LENGTH;
            if ((ciclos % 2)> 0) ciclos += 1;
            console.log('name.length:'+name.length);
            console.log('ciclos:'+ciclos);
            console.log('===============');
            if(ciclos > 0){
                while(ciclo <= ciclos){
                    console.log('ciclo:'+ciclo);
                    console.log('indiceA:'+indiceA);
                    console.log('indiceB:'+indiceB);
                    console.log('--------------');
                    wrapped.push(name.substring(indiceA,indiceB));
                    ciclo++;
                    indiceA = indiceB
                    if(ciclo < ciclos) indiceB = MAX_LENGTH * ciclo
                    else indiceB = name.length
                }
            }else wrapped.push(name);
            console.log(wrapped);
            return wrapped;
        },
        generate_wrapped_cfdi_string: function(cadena) {
            var MAX_LENGTH = 60; // 40 * line ratio of .6
            var wrapped = [];
            var ciclos = cadena.length / MAX_LENGTH;
            var ciclo = 1;
            var indiceA = 0;
            var indiceB = MAX_LENGTH;
            if ((ciclos % 2)> 0) ciclos += 1;
            if(ciclos > 0){
                while(ciclo <= ciclos){
                    wrapped.push(cadena.substring(indiceA,indiceB));
                    ciclo++;
                    indiceA = indiceB
                    if(ciclo < ciclos) indiceB = MAX_LENGTH * ciclo
                    else indiceB = cadena.length
                }
            }else wrapped.push(cadena);
            return wrapped;
        },
    });
    
    return models;
});