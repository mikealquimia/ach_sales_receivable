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
        sale_receivable = []
        query_invoice_multi_sale = """
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
        query_sale_without_invoice = """
select so.name as sale, so.amount_total as sale_amount, 
' ' as invoice, 0 as invoice_amount, 0 as invoice_residual, ' ' as invoice_status, 
coalesce(rpru.name,'NO') as seller 
from sale_order so 
left join res_users ru 
on ru.id = so.user_id 
left join res_partner rpru 
on rpru.id = ru.partner_id 
where not exists (
	select *
	from account_invoice_sale_order_rel aisor 
	where aisor.sale_order_id = so.id
) and so.state in ('sale','done')
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