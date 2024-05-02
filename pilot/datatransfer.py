
#%%

import globus_sdk

#%%

CLIENT_ID = 'f2dc0c01-966f-429f-aefa-ec1a5036839e'
client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
#%%
client.oauth2_start_flow()
authorize_url = client.oauth2_get_authorize_url()
print(f"Please go to this URL and login:\n\n{authorize_url}\n")
#%%
auth_code = input("Please enter the code you get after login here: ").strip()
token_response = client.oauth2_exchange_code_for_tokens(auth_code)
#%%
globus_auth_data = token_response.by_resource_server["auth.globus.org"]
globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]
#%%
# most specifically, you want these tokens as strings
AUTH_TOKEN = globus_auth_data["access_token"]
TRANSFER_TOKEN = globus_transfer_data["access_token"]
#%%
authorizer = globus_sdk.AccessTokenAuthorizer(TRANSFER_TOKEN)
tc = globus_sdk.TransferClient(authorizer=authorizer)


#%%
print("My Endpoints:")
for ep in tc.endpoint_search(filter_scope="my-endpoints"):
    print("[{}] {}".format(ep["id"], ep["display_name"]))
# %%
transfer_client = globus_sdk.TransferClient(
    authorizer=globus_sdk.AccessTokenAuthorizer(globus_transfer_data["access_token"])
)
# %%
