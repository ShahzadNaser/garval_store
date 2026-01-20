frappe.ready(function() {
	// Initialize Stripe
	const stripe = Stripe('{{ publishable_key }}');
	const elements = stripe.elements();

	// Shared element styles
	const elementStyles = {
		base: {
			fontSize: '16px',
			color: '#32325d',
			fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
			'::placeholder': {
				color: '#aab7c4'
			}
		},
		invalid: {
			color: '#fa755a',
			iconColor: '#fa755a'
		}
	};

	// Create separate card elements
	const cardNumberElement = elements.create('cardNumber', {
		style: elementStyles,
		placeholder: '1234 1234 1234 1234'
	});

	const cardExpiryElement = elements.create('cardExpiry', {
		style: elementStyles
	});

	const cardCvcElement = elements.create('cardCvc', {
		style: elementStyles,
		placeholder: '123'
	});

	// Mount elements
	cardNumberElement.mount('#card-number-element');
	cardExpiryElement.mount('#card-expiry-element');
	cardCvcElement.mount('#card-cvc-element');

	// Handle real-time validation errors
	const displayError = document.getElementById('card-errors');

	cardNumberElement.on('change', function(event) {
		if (event.error) {
			displayError.textContent = event.error.message;
		} else {
			displayError.textContent = '';
		}
	});

	cardExpiryElement.on('change', function(event) {
		if (event.error) {
			displayError.textContent = event.error.message;
		} else {
			displayError.textContent = '';
		}
	});

	cardCvcElement.on('change', function(event) {
		if (event.error) {
			displayError.textContent = event.error.message;
		} else {
			displayError.textContent = '';
		}
	});

	// Handle form submission
	const form = document.getElementById('payment-form');
	const submitButton = document.getElementById('submit');

	form.addEventListener('submit', async function(event) {
		event.preventDefault();

		// Disable submit button to prevent double submission
		submitButton.disabled = true;
		submitButton.textContent = 'Processing...';

		// Create token
		const {token, error} = await stripe.createToken(cardNumberElement, {
			name: document.getElementById('cardholder-name').value,
			email: document.getElementById('cardholder-email').value
		});

		if (error) {
			// Show error to customer
			const errorElement = document.getElementById('card-errors');
			errorElement.textContent = error.message;
			submitButton.disabled = false;
			submitButton.textContent = 'Pay {{ amount }}';
		} else {
			// Send token to server
			processPayment(token.id);
		}
	});

	function processPayment(tokenId) {
		console.log('Processing payment with token:', tokenId);

		const data = {
			amount: '{{ amount }}'.replace(/[^0-9.]/g, ''),
			title: '{{ title }}',
			description: '{{ description }}',
			reference_doctype: '{{ reference_doctype }}',
			reference_docname: '{{ reference_docname }}',
			payer_name: document.getElementById('cardholder-name').value,
			payer_email: document.getElementById('cardholder-email').value,
			order_id: '{{ reference_docname }}',
			currency: '{{ currency }}'
		};

		console.log('Payment data:', data);

		frappe.call({
			method: 'garval_store.api.payment.process_payment',
			args: {
				stripe_token_id: tokenId,
				data: JSON.stringify(data),
				reference_doctype: '{{ reference_doctype }}',
				reference_docname: '{{ reference_docname }}',
				payment_gateway: '{{ payment_gateway }}'
			},
			callback: function(response) {
				console.log('Payment response:', response);
				if (response.message && response.message.redirect_to) {
					window.location.href = '/' + response.message.redirect_to;
				} else {
					document.querySelector('.outcome .success').hidden = false;
					setTimeout(function() {
						window.location.href = '/';
					}, 2000);
				}
			},
			error: function(error) {
				console.error('Payment error:', error);
				const errorMsg = error.message || 'An error occurred during payment processing';
				displayError.textContent = errorMsg;
				document.querySelector('.outcome .error').hidden = false;
				submitButton.disabled = false;
				submitButton.textContent = 'Pay {{ amount }}';
			}
		});
	}
});
