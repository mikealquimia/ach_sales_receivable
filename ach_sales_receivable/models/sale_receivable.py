# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime,timedelta
import pytz

class SaleReceivable(models.TransientModel):
    _name = 'sale.receivable'
    _description = 'Sale Receivable'

    name = fields.Char(string='Cash Sale')
    date = fields.Date(string='Date')
    journal_ids = fields.Many2many('account.journal', string="Journal", domain=[('type','=','sale')])
    team_ids = fields.Many2one('crm.team', string="Team Sale")
    user_ids = fields.Many2one('res.users', string="Seller")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    def get_pdf(self):
        return self.env.ref('ach_sales_receivable.action_pdf_sale_receivable').report_action(self)

    def get_hour_tz(self, tz):
        hour = 6
        return hour

    def sale_receivable(self):
        """
        1) Ventas sin facturas = total de la venta Y
        2) Ventas con Facturas de multiples ventas
            2.1) Ventas con facturas en estado pagada pero con factura rectificativa = total de la venta
            2.2) Ventas con facturas en estado pagada = Suma de ventas - total pagado (factura-saldo)
            2.3) Ventas con facturas en estado abierto = Suma de ventas - total pagado (factura-saldo)
        3) Ventas con factura individual
            3.1) Ventas con facturas en estado pagada pero con facturas rectificava = Total de la venta
            3.2) Ventas con facturas en estado pagada = Total venta - total pagado (factura-saldo)
            3.3) Ventas con facturas en estado abierto = Total venta - total pagado (factura-saldo)
        """
        sale_receivable = []
        #1
        query_sale_without_invoice = """
select so.name as sale, so.amount_total as sale_amount, 
' ' as invoice, 0 as invoice_amount, 0 as invoice_residual, ' ' as invoice_status, 
coalesce(rpru.name,'NO') as seller, 
(so.amount_total - coalesce(sum(payment.sale_payment),0)) as sale_residual 
from sale_order so 
left join res_users ru 
on ru.id = so.user_id 
left join res_partner rpru 
on rpru.id = ru.partner_id 
left join ( 
    select ap2.id, sum(ap2.amount) as sale_payment, ap2.sale_id as sale_id 
    from account_payment ap2
    where ap2.state_sale_invoice = 'no_add' 
    group by ap2.id 
) as payment 
on payment.sale_id = so.id 
where not exists (
	select *
	from account_invoice_sale_order_rel aisor 
	where aisor.sale_order_id = so.id
) and so.state in ('sale','done')
group by so.name, so.amount_total, rpru.name 
        """
        self.env.cr.execute(query_sale_without_invoice)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale': line['sale'],
                'sale_amount': line['sale_amount'],
                'invoice': line['invoice'],
                'invoice_amount': line['invoice_amount'],
                'invoice_residual': line['invoice_residual'],
                'invoice_status': line['invoice_status'],
                'seller': line['seller'],
                'sale_residual': line['sale_residual'],
            }
            sale_receivable.append(vals)
        #2 falta tomar en cuenta el escenario de tener una factura pagada pero con rectificativa 
        query_invoice_multi_sale = """
select distinct string_agg(so.name,',') as sale, sum(so.amount_total) as sale_amount, 
ai.number as invoice, ai.amount_total as invoice_amount, ai.residual as invoice_residual, ai.state as invoice_status, 
coalesce(rpru.name,'NO') as seller, 
( (coalesce(sum(so.amount_total),0)) - ((coalesce(ai.amount_total,0)-coalesce(ai.residual,0))) ) as sale_residual 
from account_invoice_sale_order_rel aisor 
inner join sale_order so 
on so.id = aisor.sale_order_id 
inner join account_invoice ai 
on ai.state not in ('draft', 'cancel') and ai.id = aisor.account_invoice_id 
and ai.residual > 0 and ai.refund_invoice_id is null 
left join res_users ru 
on ru.id = ai.user_id 
left join res_partner rpru 
on rpru.id = ru.partner_id 
group by aisor.account_invoice_id, ai.number, ai.amount_total, ai.residual, 
ai.state, rpru.name
having count(aisor.account_invoice_id)>1 
        """
        self.env.cr.execute(query_invoice_multi_sale)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale': line['sale'],
                'sale_amount': line['sale_amount'],
                'invoice': line['invoice'],
                'invoice_amount': line['invoice_amount'],
                'invoice_residual': line['invoice_residual'],
                'invoice_status': line['invoice_status'],
                'seller': line['seller'],
            }
            sale_receivable.append(vals)
        
        query_sale_with_one_invoice = """
select distinct string_agg(so.name,',') as sale, sum(so.amount_total) as sale_amount, 
ai.number as invoice, ai.amount_total as invoice_amount, ai.residual as invoice_residual, ai.state as invoice_status, 
coalesce(rpru.name,'NO') as seller 
from account_invoice_sale_order_rel aisor 
inner join sale_order so 
on so.id = aisor.sale_order_id 
inner join account_invoice ai 
on ai.state not in ('draft', 'cancel') and ai.id = aisor.account_invoice_id 
and ai.residual > 0 
left join res_users ru 
on ru.id = ai.user_id 
left join res_partner rpru 
on rpru.id = ru.partner_id 
group by aisor.account_invoice_id, ai.number, ai.amount_total, ai.residual, 
ai.state, rpru.name 
having count(aisor.account_invoice_id)=1 
        """
        self.env.cr.execute(query_sale_with_one_invoice)
        for line in self.env.cr.dictfetchall():
            vals = {
                'sale': line['sale'],
                'sale_amount': line['sale_amount'],
                'invoice': line['invoice'],
                'invoice_amount': line['invoice_amount'],
                'invoice_residual': line['invoice_residual'],
                'invoice_status': line['invoice_status'],
                'seller': line['seller'],
            }
            sale_receivable.append(vals)
        def myFunc(e):
            return e['seller']
        sale_receivable.sort(key=myFunc)
        return sale_receivable
    
    """
    select distinct string_agg(so.name,',') as sale, 
sum(so.amount_total) as sale_amount, 
ai.number as invoice, 
coalesce( coalesce(ai.amount_total,0)-coalesce(ai2.amount_total,0) ,0) as invoice_amount, 
case 
	when ai2.amount_total notnull then coalesce( coalesce(ai.amount_total,0)-coalesce(ai2.amount_total,0) ,0) 
	when ai2.amount_total isnull then coalesce(ai.residual,0) end as invoice_residual, 
coalesce(string_agg(ai2.number,','),'') as refund_invoice, 
count(aisor.account_invoice_id) as count_ai, count(aisor.sale_order_id) as count_so 
from account_invoice_sale_order_rel aisor 
left join sale_order so 
on so.id = aisor.sale_order_id 
left join account_invoice ai 
on ai.id = aisor.account_invoice_id 
and ai.state not in ('cancel', 'draft') 
and ai.type = 'out_invoice' 
left join account_invoice ai2 
on ai2.refund_invoice_id  = ai.id 
group by ai.number, ai.amount_total, ai2.amount_total, ai.residual  
having (case 
	when ai2.amount_total notnull then coalesce( coalesce(ai.amount_total,0)-coalesce(ai2.amount_total,0) ,0) 
	when ai2.amount_total isnull then coalesce(ai.residual,0) end) > 0
    """