from genius_collection.core.models import User, Card, Ownership
from django.test import TestCase
from django.db.models import Sum

# Create your tests here.
def test_assign_ownership():
    num_samples = 5
    # TODO: This currently only works with a populated local database and 
    # without using TestCase -> Rewrite as integration test
    user = User.objects.all()[0]
    manager = Ownership.objects
    ownerships_before = Ownership.objects.aggregate(Sum("quantity"))['quantity__sum']
    manager.distribute_random_cards(user, qty=num_samples)
    ownerships_after = Ownership.objects.aggregate(Sum("quantity"))['quantity__sum']
    assert num_samples == (ownerships_after - ownerships_before)

test_assign_ownership()