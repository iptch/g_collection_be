
from ..models import Card, User, Ownership

class OwnershipHelper():

    @staticmethod
    def transfer_ownership(current_user: User, ownership: Ownership, card: Card):
        if ownership.quantity == 1:
            ownership.user = current_user
            ownership.otp = None
            ownership.save()
            return
        elif ownership.quantity > 1:
            new_ownership = OwnershipHelper().__create_new_ownership(current_user, card)
            new_ownership.save()
    
        OwnershipHelper().__decrease_quantity_by_one(ownership)
        return
    
    def __create_new_ownership(self, user: User, card: Card):
        return Ownership.objects.add_card_to_user(user=user, card=card)

    def __decrease_quantity_by_one(self, ownership: Ownership):
        ownership.quantity -= 1