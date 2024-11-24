# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)

class UrwayController(Controller):
    _process_url = '/payment/urway/process'

    @route(_process_url, type='http', auth='public', methods=['POST','GET'], csrf=False, save_session=False)
    def urway_process_transaction(self, **data):
        _logger.info("Handling urway processing with data:\n%s" % data)
        request.env['payment.transaction'].sudo()._handle_notification_data('urway', data)
        return request.redirect('/payment/status')
