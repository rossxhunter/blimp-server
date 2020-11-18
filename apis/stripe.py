import stripe
import os
stripe.api_key = os.environ["STRIPE_KEY"]


def get_payment_cards(user_stripe_id):
    cards_response = stripe.Customer.list_sources(
        user_stripe_id,
        object="card",
    )
    return cards_response["data"]


def add_new_stripe_customer():
    customer = stripe.Customer.create()
    return customer["id"]


def delete_card_for_customer(customer_id, card_id):
    stripe.Customer.delete_source(
        customer_id,
        card_id,
    )


def add_new_card_for_customer(customer_id, card_number, expiry_month, expiry_year, cvv, card_holder_name):
    token = stripe.Token.create(
        card={
            "number": card_number,
            "exp_month": expiry_month,
            "exp_year": expiry_year,
            "cvc": cvv,
            "name": card_holder_name,
        },
    )

    new_card = stripe.Customer.create_source(
        customer_id, source=token["id"],
    )

    return new_card
