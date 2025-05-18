
from dotenv import load_dotenv
load_dotenv()

import os
AZURE_TENANT_ID= os.getenv('DOCUMENT_LOADER_AZURE_TENANT_ID')
AZURE_SUBSCRIPTION_ID= os.getenv('DOCUMENT_LOADER_AZURE_SUBSCRIPTION_ID') 
AZURE_CLIENT_ID= os.getenv('DOCUMENT_LOADER_AZURE_CLIENT_ID') 
AZURE_CLIENT_SECRET= os.getenv('DOCUMENT_LOADER_AZURE_CLIENT_SECRET') 
AZURE_RESOURCE_LOCATION= os.getenv('DOCUMENT_LOADER_AZURE_RESOURCE_LOCATION')
AZURE_RESOURCE_GROUP_NAME= os.getenv('DOCUMENT_LOADER_AZURE_RESOURCE_GROUP_NAME')

AZURE_STORAGE_ACCOUNT_NAME= "documentloader001"
AZURE_STORAGE_CONTAINER_NAME= "testset001"


azure_tenant_id = AZURE_TENANT_ID
azure_subscription_id = AZURE_SUBSCRIPTION_ID
azure_client_id = AZURE_CLIENT_ID
azure_client_secret = AZURE_CLIENT_SECRET
azure_resource_location = AZURE_RESOURCE_LOCATION
azure_resource_group_name = AZURE_RESOURCE_GROUP_NAME
azure_storage_account_name = AZURE_STORAGE_ACCOUNT_NAME
azure_storage_container_name = AZURE_STORAGE_CONTAINER_NAME


from azwrap import Identity, Subscription, ResourceGroup, StorageAccount, Container
def get_container() -> Container:
    identity = Identity( 
        tenant_id=azure_tenant_id, 
        client_id=azure_client_id, 
        client_secret=azure_client_secret
    )
    subscription: Subscription = identity.get_subscription(azure_subscription_id)
    resource_group: ResourceGroup = subscription.get_resource_group(azure_resource_group_name)
    storage_account:StorageAccount = resource_group.get_storage_account(azure_storage_account_name)
    containers = storage_account.get_containers() 
    for container in containers:
        print(container.name)

    container: Container = storage_account.get_container(azure_storage_container_name)
    container = storage_account.create_container("testset002", public_access_level="blob")

    return container

if __name__ == "__main__":
    get_container()