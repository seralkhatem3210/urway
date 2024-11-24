
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

SUPPORTED_CURRENCIES = ('SAR', 'USD')
_logger = logging.getLogger(__name__)


class PaymentProviderUrway(models.Model):
    _inherit = 'payment.provider'


    code = fields.Selection([
        ('urway', 'URWAY'),
    ], string='Provider Code', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    display_as = fields.Char(string="Display As")
   
    urway_merchant_key = fields.Char(  required=True,  groups='base.group_user', string="Merchant Key", help="Enter Merchant Key provided by URWAY team." ) # Adjust this based on your validation logic
    urway_merchant_key = fields.Char( required=True, groups='base.group_user', string="Merchant Key",  help="Enter Merchant Key provided by URWAY team." ) # Adjust this based on your validation logic    
    urway_terminal_id = fields.Char( required=True, groups='base.group_user', string="Terminal ID", help="Enter Terminal ID provided by URWAY team." ) # Adjust this based on your validation logic
    urway_password = fields.Char( required=True,  groups='base.group_user', string='Terminal Password', help="Enter Terminal password provided by URWAY team."  ) # Adjust this based on your validation logic
    urway_request_url = fields.Char( required=True, groups='base.group_user',  string="Request URL",  help="URL to send request to." ) # Adjust this based on your validation logic
        

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Override to unlist Urway acquirers when the currency is not SAR."""
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)
        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            providers = providers.filtered(lambda p: p.code != 'urway')
        return providers

    def _get_default_payment_method_id(self):
        """Override to ensure URWAY payment method and method line exist."""
        self.ensure_one()

        # Check if the provider is URWAY
        if self.provider == 'urway':
            # Get or create the payment method for URWAY
            payment_method = self.env['account.payment.method'].search([
                ('name', '=', 'URWAY'),
                ('payment_type', '=', 'inbound'),
                ('code', '=', 'urway')
            ], limit=1)

            if not payment_method:
                # Create the payment method if it doesn't exist
                payment_method = self.env['account.payment.method'].create({
                    'name': 'URWAY',
                    'payment_type': 'inbound',
                    'code': 'urway',
                    'provider_ids': [(4, self.id)],  # Link to this provider
                })

            # Now check or create the payment method line
            payment_method_line = self.env['account.payment.method.line'].search([
                ('payment_method_id', '=', payment_method.id),
                ('code', '=', 'urway')
                # ('journal_id', '=', self.journal_id.id),  # Ensure it's tied to the correct journal
                # ('payment_account_id', '=', self.payment_account_id.id)  # Ensure linked to the right account
            ], limit=1)

            if not payment_method_line:
                # Create the payment method line if not found
                payment_method_line = self.env['account.payment.method.line'].create({
                    'payment_method_id': payment_method.id,
                    'journal_id': self.journal_id.id,
                    'sequence': 10,  # Default sequence
                    'payment_provider_id': self.id,  # Link to the URWAY provider
                    'payment_account_id': self.payment_account_id.id,  # Assign payment account
                    'state': 'test',  # Set the state, could be dynamic based on environment
                })

            return payment_method.id

        return super()._get_default_payment_method_id()


    def write(self, vals):
        # Call the super method to execute the default write logic
        res = super(PaymentProviderUrway, self).write(vals)

        # If the provider is updated, update the associated payment method lines
        for provider in self:
            provider._update_payment_method_lines()

        return res

    def _update_payment_method_lines(self):
        _logger.info(f"Updating payment method lines for providers: {self.ids}")

        payment_method_lines = self.env['account.payment.method.line'].search([('code', '=', 'urway')])
        for payment_method_line in payment_method_lines:

            
            print("payment_method_line:", payment_method_line)
            payment_method_line.journal_id = self.journal_id # Add this line # Use the correct way to update the field

        # Find all payment methods linked to this provider
        payment_methods = self.env['account.payment.method'].search([('provider_ids', 'in', self.ids)])
        
        # Update the payment method lines for each payment method
        for payment_method in payment_methods:
            payment_method._update_payment_method_lines()


class PaymentToken(models.Model):
    _name = 'payment.token'
    
    company_id = fields.Many2one('res.company', string='Company', required=True)
    provider_id = fields.Many2one('payment.provider', string='Payment Provider')
    provider_code = fields.Char(string='Provider Code', compute='_compute_provider_code', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    @api.depends('provider_id')
    def _compute_provider_code(self):
        """Compute the provider code based on the selected payment provider."""
        for record in self:
            record.provider_code = record.provider_id.code if record.provider_id else False

class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'


    provider_ids = fields.Many2many(
    'payment.provider',
    'payment_provider_payment_method_rel',  # the name of the relation table
    'payment_method_id',
    'provider_id',
    string='Payment Providers'
    )

class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    # Optionally, you can add methods to handle changes in journal_id or other behaviors
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        
        # Logic to handle any actions when the journal_id changes
        # For example, you could log the change or update other fields
        pass
 
        


