from odoo import tools, fields
from odoo.osv import osv


class sale_custom_report_base(osv.osv):
    _name = "sale.custom.report.base"
    _auto = False
    _order = 'date desc'
    #    _rec_name = 'date'

    date = fields.Datetime('Date Order', readonly=True)  # TDE FIXME master= rename into date_order
    date_confirm = fields.Date('Date Confirm', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom = fields.Many2one('product.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('# of Qty', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    price_total = fields.Float('Total Price', readonly=True)
    delay = fields.Float('Commitment Delay', digits=(16, 2), readonly=True)
    categ_id = fields.Many2one('product.category', 'Category of Product', readonly=True)
    nbr = fields.Integer('# of Lines', readonly=True),  # TDE FIXME master= rename into nbr_lines
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('waiting_date', 'Waiting Schedule'),
        ('manual', 'Manual In Progress'),
        ('progress', 'In Progress'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Order Status', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    section_id = fields.Many2one('crm.case.section', 'Sales Team', readonly=True)
    shop_id = fields.Many2one('sale.shop', 'Shop', readonly=True)
    payment_method_id = fields.Many2one('payment.method.ecommerce', 'Payment Method', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_custom_report_base')
        cr.execute("""
            create or replace view sale_custom_report_base as (
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(l.product_uom_qty * l.price_unit * (100.0-l.discount) / 100.0) as price_total,
                    count(*) as nbr,
                    s.date_order as date,
                    s.date_confirm as date_confirm,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    s.state,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id,
                    s.section_id as section_id,
                    s.shop_id as shop_id,
                    s.payment_method_id as payment_method_id,
                    p.default_code as default_code
                    
                    
                    From sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    
                    GROUP BY l.product_id,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    s.state,
                    s.pricelist_id,
                    s.project_id,
                    s.section_id,
                    s.shop_id,
                    s.payment_method_id,
                    p.default_code
            )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
