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
HOST = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
USER_DELEGATION_KEY_CACHE = "user_delegation_key"
CACHE_BUFFER_TIME = datetime.timedelta(minutes=1)


# Microsoft recommends the use of Azure AD credentials as a security best practice,
# rather than using the account key, which can be more easily compromised.
def request_user_delegation_key() -> UserDelegationKey:
    start_time = datetime.datetime.now(datetime.timezone.utc)
    cached_key = cache.get(USER_DELEGATION_KEY_CACHE)
    if cached_key and cached_key["expiry"] > start_time + CACHE_BUFFER_TIME:
        return cached_key["value"]

    # If the key isn't in cache, fetch a new one.
    print("Requesting user delegation key")
    expiry_time = start_time + datetime.timedelta(days=1)
    blob_service_client = BlobServiceClient(HOST, credential=DefaultAzureCredential())
    user_delegation_key = blob_service_client.get_user_delegation_key(
        key_start_time=start_time,
        key_expiry_time=expiry_time
    )

    # Cache the key for its validity period.
    cache_duration = int((expiry_time - start_time).total_seconds())
    print(f"Caching user delegation key for {cache_duration} seconds")
    cache.set(USER_DELEGATION_KEY_CACHE, {"value": user_delegation_key, "expiry": expiry_time}, cache_duration)

    return user_delegation_key


def create_container_sas(
        user_delegation_key: UserDelegationKey,
        container_name: str
) -> str:
    start_time = datetime.datetime.now(datetime.timezone.utc)
    cached_sas = cache.get(container_name)
    if cached_sas and cached_sas["expiry"] > start_time + CACHE_BUFFER_TIME:
        return cached_sas["value"]

    # If the SAS token isn't in cache, create a new one.
    print(f"Creating {container_name} container SAS token")
    expiry_time = start_time + datetime.timedelta(days=1)
    container_sas = generate_container_sas(
        account_name=STORAGE_ACCOUNT,
        container_name=container_name,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    # Cache the SAS token for its validity period.
    cache_duration = int((expiry_time - start_time).total_seconds())
    print(f"Caching {container_name} container SAS token for {cache_duration} seconds")
    cache.set(container_name, {"value": container_sas, "expiry": expiry_time}, cache_duration)

    return container_sas


def get_blob_sas_url(container_name: str, acronym: str) -> str:
    blob_name = f'{acronym.lower()}.jpg'
    user_delegation_key = request_user_delegation_key()
    sas_token = create_container_sas(user_delegation_key, container_name)
    return f"{HOST}/{container_name}/{blob_name}?{sas_token}"
