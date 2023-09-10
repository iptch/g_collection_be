import datetime
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    BlobSasPermissions,
    UserDelegationKey,
    generate_blob_sas,
)

# Microsoft recommends the use of Azure AD credentials as a security best practice,
# rather than using the account key, which can be more easily compromised.
def request_user_delegation_key(blob_service_client: BlobServiceClient) -> UserDelegationKey:
    # Get a user delegation key that's valid for 1 day
    delegation_key_start_time = datetime.datetime.now(datetime.timezone.utc)
    delegation_key_expiry_time = delegation_key_start_time + datetime.timedelta(days=1)

    return blob_service_client.get_user_delegation_key(
        key_start_time=delegation_key_start_time,
        key_expiry_time=delegation_key_expiry_time
    )

def create_user_delegation_blob_sas(blob_client: BlobClient, user_delegation_key: UserDelegationKey) -> str:
        # Create a SAS token that's valid for 1 hour
        start_time = datetime.datetime.now(datetime.timezone.utc)
        expiry_time = start_time + datetime.timedelta(hours=1)

        return generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            user_delegation_key=user_delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry_time,
            start=start_time
        )

def get_blob_sas_url(blob_name: str) -> str:
    account_url = "https://gcollection.blob.core.windows.net"
    blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
    user_delegation_key = request_user_delegation_key(blob_service_client=blob_service_client)
    blob_client = blob_service_client.get_blob_client(container="card-high-res-images", blob=blob_name)
    sas_token = create_user_delegation_blob_sas(blob_client=blob_client, user_delegation_key=user_delegation_key)
    return f"{blob_client.url}?{sas_token}"
