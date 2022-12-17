odoo.define("pos_facturatool_customerpanel.models", function (require) {
    "use strict";

    const models = require("point_of_sale.models");

    models.load_models([
        {
            model: "facturatool.account",
            label: "Cuenta FacturaTool",
            before: "res.partner",
            fields: ["cfdi_portal", "cfdi_portal_politica", "cfdi_portal_host", "company_id"],
            loaded: function(self, ftAccounts) {
                self.db.ftAccounts = ftAccounts;
                self.db.ftAccounts_by_company = ftAccounts.reduce(
                    (map, rec) => ((map[rec.company_id[0]] = rec), map),
                    {}
                );
            },
        },
    ]);

    var OrderSuper = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            var initialize_resp = OrderSuper.initialize.apply(this, arguments);
            console.log(' models.Order initialize');
            console.log(this.uid);
            this.cfdi_ticket_codigo = this.generate_unique_ticket_code();
            console.log(this.uid);
            //return OrderSuper.initialize.call(this, attributes,options);
            //return OrderSuper.initialize.apply(this, arguments);
            return initialize_resp;
        },
        
        export_as_JSON: function() {
            var json = OrderSuper.export_as_JSON.apply(this, arguments);
            var order = this.pos.get('selectedOrder');
            if (order) {
                json.cfdi_ticket_codigo = this.cfdi_ticket_codigo;
            }
            return json;
        },
        export_for_printing: function(){
            var receipt = OrderSuper.export_for_printing.apply(this, arguments);
            var date_deadline = new Date();
            var ft_account = this.pos.db.ftAccounts_by_company[this.pos.company.id]
            receipt.cfdi_portal = false;
            if(typeof ft_account == 'object' && ft_account.cfdi_portal){
                receipt.cfdi_portal = {
                    'politica': ft_account.cfdi_portal_politica,
                    'host': ft_account.cfdi_portal_host
                };
                receipt.cfdi_ticket_codigo = this.cfdi_ticket_codigo;
                receipt.cfdi_ticket_deadline = false;
                switch(ft_account.cfdi_portal_politica){
                    case 'inMonth':
                        date_deadline = new Date(date_deadline.getFullYear(), date_deadline.getMonth()+1, 0);
                        //date_deadline.setDate(date_deadline.getDate() - 1);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    case '3days':
                        date_deadline.setDate(date_deadline.getDate() + 3);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    case '7days':
                        date_deadline.setDate(date_deadline.getDate() + 7);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    case '15days':
                        date_deadline.setDate(date_deadline.getDate() + 15);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    case '30days':
                        date_deadline.setDate(date_deadline.getDate() + 30);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    case '3months':
                        date_deadline.setMonth(date_deadline.getMonth() + 3);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                    default: //inMonth
                        date_deadline = new Date(date_deadline.getFullYear(), date_deadline.getMonth()+1, 0);
                        receipt.cfdi_ticket_deadline = date_deadline.getFullYear()+'-'+(date_deadline.getMonth()+1)+'-'+date_deadline.getDate();
                        break;
                }
                
                receipt.cfdi_ticket_qr = '/report/barcode/?type=QR&value='+ft_account.cfdi_portal_host+'?codigo='+this.cfdi_ticket_codigo+'&width=160&height=160';
                
            }
            return receipt;
        },
        
        generate_unique_ticket_code_old: function() {
            // Generates a public identification number for the order.
            // The generated number must be unique and sequential. They are made 12 digit long
            // to fit into EAN-13 barcodes, should it be needed

            function generate_letter_random(){
                const characters ='ABCDEFGHJKLMNPQRSTUVWXYZ';
                const charactersLength = characters.length;
                return characters.charAt(Math.floor(Math.random() * charactersLength));
            }
    
            function get_str_pad(num,size){
                var cad = num+'';
                if(cad.length < size) return generate_letter_random()+cad;
                else return cad.substring(cad.length - size - 1, cad.length);
            }
            
            return  generate_letter_random() +
                    get_str_pad(this.pos.pos_session.id,2) +
                    generate_letter_random() +
                    get_str_pad(this.pos.pos_session.login_number,2) +
                    generate_letter_random() +
                    get_str_pad(this.sequence_number,2) +
                    generate_letter_random();
        },
        generate_unique_ticket_code: function() {
            // Generates a public identification number for the order.
            // The generated number must be unique and sequential. They are made 12 digit long
            // to fit into EAN-13 barcodes, should it be needed

            function gt_letter(index){
                console.log(index);
                const characters ='ABCDEFGHJKLMNPQRSTUVWXYZ';
                const charactersLength = characters.length;
                index = index % charactersLength
                console.log(index);
                return characters[index];
            }
    
            function get_str_pad(num,size,config_id){
                var cad = num+'';
                if(cad.length < size) return gt_letter(num * config_id)+cad;
                else return cad.substring(cad.length - size - 1, cad.length);
            }
            console.log('generate_unique_ticket_code');
            console.log(this);
            const order_uid_arrray = this.uid.split('-'); 
            const pos_session_id = parseInt(order_uid_arrray[0]), 
                  login_number=parseInt(order_uid_arrray[1]), 
                  sequence_number=parseInt(order_uid_arrray[2]);
            const lt1 = pos_session_id * sequence_number * this.pos.config.id,
                  lt2 = login_number * sequence_number * this.pos.config.id,
                  lt3 = pos_session_id * login_number * this.pos.config.id,
                  lt4 = lt1 * lt2 * lt3;

            return  gt_letter(lt1) +
                    get_str_pad(pos_session_id,2,this.pos.config.id) +
                    gt_letter(lt2) +
                    get_str_pad(login_number,2,this.pos.config.id) +
                    gt_letter(lt3) +
                    get_str_pad(sequence_number,2,this.pos.config.id) +
                    gt_letter(lt4);
        },
        
    });
    
    return models;
});