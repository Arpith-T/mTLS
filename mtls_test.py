import requests
import json

IAAS = "AWS"
app = "it-trm"
space_id = "2c92d3e7-a833-4fbf-89e2-917c07cea220" # enter the space ID here
cf_base_url = "https://api.cf.sap.hana.ondemand.com"

def cf_oauth_token():
    url = "https://uaa.cf.sap.hana.ondemand.com/oauth/token"

    payload = "grant_type=password&client_id=cf&client_secret=&username=prism@global.corp.sap&password=Prisminfra529#5"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    # print(response.text)
    return (requests.request("POST", url, headers=headers, data=payload)).json()["access_token"]


token = cf_oauth_token()


def get_app_guid(token, app):
    try:
        url = f"{cf_base_url}/v3/apps?page=1&per_page=1000&space_guids={space_id}&names={app}"

        payload = {}
        headers = {
            'Authorization': f'Bearer {token}'
            # 'Cookie': 'JTENANTSESSIONID_kr19bxkapa=FPtRDK1dM3D1lD56pq9oAq9mvHn19ohxqXjClhqrbLI%3D'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        guid = json.loads(response.text)["resources"][0]["guid"]

        print(f"guid is: {guid}")

        return guid
    except:
        print(f"\n unable to fetch guid for {app}. There might couple of reasons for this - \n"
              f"1. Software Update might be in progress Or\n"
              f"2. There might be some deployment issue due to which there might be some duplication of applications.\n"
              f"3. Application name might be incorrect\n"
              f"Please contact Infra team to understand the root cause and resolution for the same"
              )

guid = get_app_guid(token, app)

# print(oauth_token)

def get_app_env_var():
    url = f"https://api.cf.sap.hana.ondemand.com/v3/apps/{guid}/env"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload).json()["system_env_json"]["VCAP_SERVICES"]["xsuaa"][0]["credentials"]

    clientid = response["clientid"]

    certificate = response["certificate"]

    certurl = response["certurl"]

    key = response["key"]

    # print(f"client_id: {clientid}\n")
    # print(f"certurl:\n {certurl}\n")
    # print(f"certificate:\n {certificate}\n")
    # print(f"key:\n {key}\n")
    #
    # # Open a file in write mode using the `with` statement
    # with open("certificate.pem", "w") as f:
    #     # Use the `write()` method to store the data in the file
    #     f.write(certificate)
    # # The file is automatically closed after the `with` block is executed
    #
    # # Open a file in write mode using the `with` statement
    # with open("key.pem", "w") as f:
    #     # Use the `write()` method to store the data in the file
    #     f.write(key)
    # # The file is automatically closed after the `with` block is executed

    return clientid, certurl, certificate, key






    # print(json.dumps(response, indent=4))

client_id, certurl, certificate, key = get_app_env_var()

# print(certurl)



def get_jwt_x509(certurl, client_id, certificate, key):
    auth_url = certurl + "/oauth/token?grant_type=client_credentials"
    payload = "client_id=" + client_id
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    cert_file = open(f"{IAAS}_certificate.pem", "w")
    cert_file.write(certificate)
    cert_file.close()

    key_file = open(f"{IAAS}_key.pem", "w")
    key_file.write(key)
    key_file.close()

    print("making api call...")
    response = requests.post(auth_url, data=payload, headers=headers, cert=("certificate.pem", "key.pem"))
    print("done.\n")

    print(f"STATUS_CODE = {response.status_code}")
    print("token:\n", response.json()["access_token"])

get_jwt_x509(certurl, client_id, certificate, key)