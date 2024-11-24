odoo.define('payment_urway.post_processing', require => {
    'use strict';

    const paymentPostProcessing = require('payment.post_processing');

    paymentPostProcessing.include({
        /**
         * Override the processPolledData method to handle URWAY transactions specifically.
         * Redirect customers immediately for URWAY transactions to avoid pending states.
         *
         * @override method from `payment.post_processing`
         * @param {Object} display_values_list - The post-processing values of the transactions
         */

        processPolledData: function (display_values_list) {
            if (display_values_list.length > 0 && display_values_list[0].provider_code === 'urway') {
                if (display_values_list[0].landing_route) {
                    window.location.href = display_values_list[0].landing_route;
                } else {
                    console.error('URWAY landing route is not defined.');
                    alert('An error occurred: Please contact support.');
                }
            } else {
                // Call the parent method for other providers
                return this._super(...arguments);
            }
        }


    
    });
});
