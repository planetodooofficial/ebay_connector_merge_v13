{
    "name" : "Base Shipping V13",
    "version" : "1.1.1",
    "depends" : ["base", "product","sale","stock","delivery","account"],
    "author" : "Planet Odoo",
    "description": """
        Base Shipping V13\n
        Create Shipments\n
        Print Labels\n
    """,
    "website" : "www.planet-odoo.com",
    'images': [],
    "category" : "Shipping",
    'summary': 'Base Shipping V13',
    "demo" : [],
	'currency': 'GBP',
    "data" : [

            'views/sequence.xml',
            'security/base_shipping_security.xml',
            'views/stock_picking_view.xml',
            'views/delivery_carrier.xml',
            'wizard/batch_force_availability.xml',
            'wizard/update_picking_view.xml',
            # 'wizard/print_picklist_view.xml',
            'wizard/search_pickings_view.xml',
            'views/base_carrier_code_view.xml',
            'views/manifest_view.xml',
            'report/base_manifest_report.xml',
            'report/base_manifest_template.xml',
            'views/report_paperformat.xml',
            'views/base_shipping_logs.xml',
            'views/product_view.xml',
            'wizard/res_config_settings.xml',
            'wizard/update_weight_dimension_wizard.xml',
            'security/ir.model.access.csv',


    ],
    'auto_install': False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


