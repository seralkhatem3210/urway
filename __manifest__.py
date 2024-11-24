# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: URWAY (Redirect)",
    'version': '17.0.1.2.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 300,
    'summary': "Allows you to accept mada / VISA / MasterCard via secure payment gateway.",
    'depends': ['payment', 'account'],  
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_urway_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'installable': True,  
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'auto_install': False,
    'license': 'LGPL-3',
}