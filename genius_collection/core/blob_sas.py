import datetime
from django.core.cache import cache
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    UserDelegationKey,
    generate_container_sas
)

STORAGE_ACCOUNT = "gcollection"

# Microsoft recommends the use of Azure AD credentials as a security best practice,
# rather than using the account key, which can be more easily compromised.
def request_user_delegation_key(blob_service_client: BlobServiceClient) -> UserDelegationKey:
    cache_key = "user_delegation_key"
    cached_key = cache.get(cache_key)
    if cached_key:
        return cached_key

    # If the key isn't in cache, fetch a new one.
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(days=1)

    user_delegation_key = blob_service_client.get_user_delegation_key(
        key_start_time=start_time,
        key_expiry_time=expiry_time
    )

    # Cache the key for 23 hours (1 hour less than its validity).
    cache_duration = expiry_time - start_time - datetime.timedelta(hours=1)
    cache.set(cache_key, user_delegation_key, cache_duration.seconds)
    
    return user_delegation_key

def create_container_sas(
    blob_service_client: BlobServiceClient,
    user_delegation_key: UserDelegationKey,
    container_name: str
) -> str:
    cached_sas = cache.get(container_name)
    if cached_sas:
        return cached_sas

    # If the SAS token isn't in cache, create a new one.
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(days=1)

    container_sas = generate_container_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    # Cache the key for 23 hours (1 hour less than its validity).
    cache_duration = expiry_time - start_time - datetime.timedelta(hours=1)
    cache.set(container_name, container_sas, cache_duration.seconds)

    return container_sas

def get_blob_sas_url(container_name: str, blob_name: str) -> str:
    account_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
    blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
    user_delegation_key = request_user_delegation_key(blob_service_client=blob_service_client)
    sas_token = create_container_sas(blob_service_client, user_delegation_key, container_name)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    return f"{blob_client.url}?{sas_token}"
