# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import socket
from hashlib import sha256

import requests
from werkzeug import urls

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

from odoo.addons.payment_urway.controllers.main import UrwayController
from odoo.addons.payment_urway.controllers.responsecodes import URWAY_RESPONSE_CODE

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    urway_payment_id = fields.Char(string='URWAY Transaction ID', readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return custom-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'urway':
            return res

        base_url = self.provider_id.get_base_url()
        billing_address = {
            "address1": self.partner_address,
            "postalCode": self.partner_zip,
            "city": self.partner_city,
            "countryCode": self.partner_country_id.code,
        }
        order = {
            "orderType": "ECOM",
            "amount": self.amount,
            "currencyCode": self.currency_id.name,
            "name": self.partner_name,
            "orderDescription": self.reference,
            "customerOrderCode": self.reference,
            "billingAddress": billing_address
        }
        merchantKey = self.provider_id.urway_merchant_key
        terminalId = self.provider_id.urway_terminal_id
        password = self.provider_id.urway_password
        URL = self.provider_id.urway_request_url

        orderid = order['customerOrderCode']
        amount = order['amount']
        currency = order['currencyCode']
        country = billing_address['countryCode']
        lang = self.partner_lang
        email = self.partner_email
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)

        txn_details = "" + orderid + "|" + terminalId + "|" + password + "|" + merchantKey + "|" + str(
            amount) + "|" + currency
        hs = sha256(txn_details.encode('utf-8')).hexdigest()

        response_url = urls.url_join(base_url, UrwayController._process_url)

        fields = {
            'trackid': orderid,
            'terminalId': terminalId,
            'customerEmail': email,
            'action': "1",
            'merchantIp': IPAddr,
            'password': password,
            'currency': currency,
            'country': country,
            'amount': amount,
            'udf5': "ODOO",
            'udf3': lang[:2],
            'udf4': "",
            'udf1': "",
            'udf2': response_url,
            'requestHash': hs
        }

        r = requests.post(URL, json=fields)
        if r.status_code == 200:
            urldecode = r.json()
        else:
            raise ValidationError(
                "URWAY cannot communicate with the server. Please contact administrator to resolve the issue.")

        if urldecode['result'] == 'Successful' or urldecode['payid']:
            urway_tx_values = ({
                'api_url': urldecode['targetUrl'] + "?paymentid=" + urldecode['payid'],
                'reference': self.reference
            })
            return urway_tx_values
        else:
            raise ValidationError(
                "ERRCODE %s : %s" % (urldecode['responseCode'], URWAY_RESPONSE_CODE.get(urldecode['responseCode'])))

    def urway_get_form_action_url(self):
        self.ensure_one()
        return self.get_base_url() + UrwayController._process_url

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on custom data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification feedback data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'urway' or len(tx) == 1:
            return tx

        reference = notification_data.get('TrackId')
        if not reference:
            urway_error = notification_data.get('ResponseCode', {})
            _logger.error('URWAY: invalid reply received from URWAY Servers, looks like '
                          'the transaction failed. (error: %s)', urway_error or 'n/a')
            error_msg = "We're sorry to report that the transaction has failed."
            if urway_error:
                error_msg += " " + ("URWAY gave us the following info about the problem: '%s'" %
                                    URWAY_RESPONSE_CODE.get(urway_error))
            error_msg += " " + ("Perhaps the problem can be solved by double-checking your "
                                "credit card details.")
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'urway')])
        if not tx:
            error_msg = ('URWAY: no order found for reference %s', reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        elif len(tx) > 1:
            error_msg = ('URWAY: %s orders found for reference %s' % (len(tx), reference))
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        transaction = tx
        acquirer = transaction['provider_id']
        merchantKey = acquirer.urway_merchant_key
        terminalId = acquirer.urway_terminal_id
        password = acquirer.urway_password
        URL = acquirer.urway_request_url
        currency = transaction['currency_id'].name
        lang = transaction["partner_lang"][0:2]
        email = transaction['partner_email']
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)

        txn_details = "" + reference + "|" + terminalId + "|" + password + "|" + merchantKey + "|" + str(
            notification_data.get('amount')) + "|" + currency
        hs1 = sha256(txn_details.encode('utf-8')).hexdigest()

        fields = {
            'trackid': reference,
            'terminalId': terminalId,
            'customerEmail': email,
            'action': "10",
            'merchantIp': IPAddr,
            'password': password,
            'currency': currency,
            'country': notification_data.get("TranId"),
            'amount': notification_data.get("amount"),
            'udf5': "ODOO",
            'udf3': lang[:2],
            'udf4': "",
            'udf1': "",
            'udf2': "",
            'requestHash': hs1
        }

        r = requests.post(URL, json=fields)
        inquiry = r.json()

        hs2 = sha256((notification_data.get("TranId") + "|" + merchantKey + "|" + notification_data.get(
            "ResponseCode") + "|" + notification_data.get("amount")
                      + "").encode('utf-8')).hexdigest()

        if hs2 == notification_data.get("responseHash") or notification_data.get("Result") == 'Successful':
            return tx
        else:
            if inquiry['result'] != 'Successful' or inquiry['responseCode'] != '000':
                error_msg = (
                        'ERRCODE %s:%s | URWAY: The transcation is invalid %s. Please try again' % (
                    inquiry['responseCode'], URWAY_RESPONSE_CODE.get(inquiry['responseCode']), reference))
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            error_msg = (
                    'ERRCODE %s:%s | URWAY: The transcation response receieved %s might be tempered. Please try again' % (
                notification_data.get("ResponseCode"), URWAY_RESPONSE_CODE.get(notification_data.get("ResponseCode")),
                reference))
            _logger.error(error_msg)
            raise ValidationError(error_msg)

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on custom data.

        Note: self.ensure_one()

        :param dict notification_data: The custom data
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'urway':
            return

        _logger.info(
            "cehcking urway payment for transaction with reference %s ....",
            self.reference
        )
        if self.state not in ("draft", "pending"):
            _logger.info('URWAY: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = notification_data.get('Result')
        tx_id = notification_data.get('TranId')
        self.provider_reference = tx_id
        self.urway_payment_id = tx_id
        if status == 'Successful':
            self._set_done()
        else:
            error = notification_data.get("ResponseCode")
            self._set_error("ERRCODE %s : %s | URWAY: Transaction failed %s" % (
                error, URWAY_RESPONSE_CODE.get(error), notification_data.get('TrackId')))
