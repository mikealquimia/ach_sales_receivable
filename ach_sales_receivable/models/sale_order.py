# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_residual = fields.Float(string="Residual", compute="_residual_sale_order")

    def _residual_sale_order(self):
        for rec in self:
            if rec.state in ['sale', 'done']:
                sql = """
select distinct so.name as order, so.amount_total as sale, coalesce(string_agg(ai.number,','),'') as invoice, 
coalesce(sum(ai.amount_total),0) as invoice, coalesce(sum(ai.residual),0) as residual_invoice, 
(so.amount_total-coalesce(sum(ai.amount_total),0)+coalesce(sum(ai.residual),0)) as residual_sale 
from sale_order so
left join account_invoice_sale_order_rel aisor 
on aisor.sale_order_id = so.id 
left join account_invoice ai 
on ai.id = aisor.account_invoice_id and ai.state not in ('draft', 'cancel')
where so.id = {id} 
group by so.name, so.amount_total """.format(id=rec.id)
                self.env.cr.execute(sql)
                query = self.env.cr.dictfetchone()
                rec.total_residual = query['residual_sale']
            else:
                rec.total_residual = 0
        return