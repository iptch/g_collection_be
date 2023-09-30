from ..models import Card, User, Ownership


class OwnershipHelper:
    @staticmethod
    def transfer_ownership(to_user: User, giver_ownership: Ownership, card: Card):
        from_user = giver_ownership.user

        receiver_ownership = Ownership.objects.add_card_to_user(user=to_user, card=card)
        giver_ownership.otp_valid_to = None
        giver_ownership.otp_value = None
        giver_ownership.save()
        giver_ownership = Ownership.objects.remove_card_from_user(user=from_user, card=card)

        return giver_ownership, receiver_ownership
