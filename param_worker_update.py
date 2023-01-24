# from main import access_token
import json
import os
import requests
from influxdb import InfluxDBClient
import time

# trm_url = "https://it-aciat001-trm.cfapps.sap.hana.ondemand.com/api/trm/v1"
worker_version = "6.36.0"
alias_name = "test_arp_0"
system_id = "acdev002"
app = "it-trm"
folder_path = "C:\\MC_files\\MC\\certificate_keys"
BuildDetail = "arp_test"

# Check the file and cleanup old data in the file if exists
with open("failed_subtasks.json", "w") as datafile:
    datafile.truncate()
print("Old data in the File is cleaned up. will be used to add new failed subtasks if any")

def read_config():
    with open('wu_config.json') as f:
        conf = json.load(f)
    return conf


config = read_config()

# chaos_url = json.dumps(config[system_id]['chaos_url']).strip('\"')
# chaos_auth = json.dumps(config[system_id]['chaos_auth']).strip('\"')
cf_oauth_url = json.dumps(config[system_id]['cf_oauth_url']).strip('\"')
user = json.dumps(config[system_id]['user']).strip('\"')
password = json.dumps(config[system_id]['password']).strip('\"')
cf_base_url = json.dumps(config[system_id]['cf_base_url']).strip('\"')
space_id = json.dumps(config[system_id]['space_id']).strip('\"')
trm_url = json.dumps(config[system_id]['trm_url']).strip('\"')


# trm_oauth_url = json.dumps(config[system_id]['trm_oauth_url']).strip('\"')
# trm_basic_auth = json.dumps(config[system_id]['trm_basic_auth']).strip('\"')
# influx_db = json.dumps(config[system_id]['influx_db']).strip('\"')
# db_store = json.dumps(config[system_id]['db_store']).strip('\"')

def cf_oauth_token():
    url = f"{cf_oauth_url}/oauth/token"

    payload = f"grant_type=password&client_id=cf&client_secret=&username={user}&password={password}"
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
    url = f"{cf_base_url}/v3/apps/{guid}/env"

    payload = {}
    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = \
            requests.request("GET", url, headers=headers, data=payload).json()["system_env_json"]["VCAP_SERVICES"][
                "xsuaa"][
                0]["credentials"]

        # print(f"response is :\n {response}")

        client_id = response["clientid"]
        # print(f"clientid is: {client_id}")

        certificate = response["certificate"]
        # print(f"certificate is {certificate}")

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

        return client_id, certurl, certificate, key
    except KeyError:
        response = \
            requests.request("GET", url, headers=headers, data=payload).json()["system_env_json"]["VCAP_SERVICES"][
                "xsuaa"][
                1]["credentials"]

        # print(f"response is :\n {response}")

        client_id = response["clientid"]
        # print(f"clientid is: {client_id}")

        certificate = response["certificate"]
        # print(f"certificate is {certificate}")

        certurl = response["certurl"]

        key = response["key"]

        return client_id, certurl, certificate, key

    # print(json.dumps(response, indent=4))


client_id, certurl, certificate, key = get_app_env_var()


# print(certurl)


def get_jwt_x509(certurl, client_id, certificate, key, folder_path):
    auth_url = certurl + "/oauth/token?grant_type=client_credentials"
    payload = "client_id=" + client_id
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Check if the folder exists, and create it if it does not
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Set the file path
    file_path1 = os.path.join(folder_path, f'{system_id}_{app}_certificate.pem')
    file_path2 = os.path.join(folder_path, f'{system_id}_{app}_key.pem')

    cert_file = open(file_path1, "w")
    cert_file.write(certificate)
    cert_file.close()

    key_file = open(file_path2, "w")
    key_file.write(key)
    key_file.close()

    print("making api call...")
    response = requests.post(auth_url, data=payload, headers=headers, cert=(file_path1, file_path2))
    print("done.\n")

    print(f"STATUS_CODE = {response.status_code}")
    # print("token:\n", response.json()["access_token"])

    return response.json()["access_token"]


access_token = get_jwt_x509(certurl, client_id, certificate, key, folder_path)


def get_current_alias_data():
    url = f"{trm_url}/tenant-softwares/versions?isCurrent=true"

    payload = ""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Cookie': '__VCAP_ID__=3cc90f93-1165-4d04-467a-2683; JSESSIONID=CAF3EF3734B444F9BE75F239CE3E39D0'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    prescript = response.json()[0]["preScript"]
    postscript = response.json()[0]["postScript"]
    workerconfiguration = response.json()[0]["workerConfiguration"]

    # print(f"{prescript}\n")
    # print(f"{postscript}\n")
    # print(f"{workerconfiguration}\n")

    return prescript, postscript, workerconfiguration


prescript, postscript, workerconfiguration = get_current_alias_data()


# def alias_creation(alias_name=os.getenv("ALIAS"), worker_version=os.getenv("worker_version")):
# print(f"my name is {alias_name}")
def alias_creation(alias_name=alias_name, worker_version=worker_version):
    url = f"{trm_url}/tenant-softwares/versions"

    payload = json.dumps({
        "alias-name": f"{alias_name}",
        "sw-version": f"{worker_version}",
        "repositoryLocation": f"cf://worker-{worker_version}",
        "isCurrent": False,
        "isActive": True,
        "swType": "WORKER",
        "swImgType": "JAR_CF",
        "preScript": f"{prescript}",
        "postScript": f"{postscript}",
        "defaultRoutePaths": [
            ""
        ],
        "workerConfiguration": f"{workerconfiguration}"
    })
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Cookie': 'JTENANTSESSIONID_kr19bxkapa=9iw0jy5xm%2FKXJ70RU4L5Z7hdMi5twfkpG0i8ImA3QgU%3D'
    }

    alias_creation_response = requests.request("POST", url, headers=headers, data=payload)

    print(f"alias creation: {alias_creation_response.status_code}, {alias_creation_response.content}")

    return alias_name



alias = alias_creation(alias_name, worker_version)


url = f"{trm_url}/tenant-softwares/versions/{alias}/tenants"

print(url)

payload = json.dumps(config["payload"])
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {access_token}',
    'Cookie': 'JTENANTSESSIONID_kr19bxkapa=9iw0jy5xm%2FKXJ70RU4L5Z7hdMi5twfkpG0i8ImA3QgU%3D'
}

worker_update_response = requests.request("PUT", url, headers=headers, data=payload)
worker_update_response.raise_for_status()
print(f"Worker Updates triggered for {alias}")
# response = worker_update_response.json()
# res_in_dict = json.dumps(response, indent=4)
# time.sleep(60)

print(json.dumps(worker_update_response.json(), indent=4))

#########################################################

def list_of_failed_tasks(worker_update_file):
    with open(worker_update_file) as datafile:
        worker_update_status = json.loads(datafile.read())
        # print(worker_update_status)
        # print(type(worker_update_status))
        failed_tasks = []
        for task in range(0, len(worker_update_status["tasks"])):
            if (worker_update_status["tasks"][task]["status"]) == "FAILED":
                failed_tasks.append((worker_update_status["tasks"][task]["taskId"]))
        print(failed_tasks)
        res_in_dict[task] = failed_tasks
        return failed_tasks

def failed_tasks(worker_update_file):
    task_sub_dict = {}
    subtask_dict = {}
    # failed_tasks = []
    for task in range(0, len(worker_update_file["tasks"])):
        if (worker_update_file["tasks"][task]["status"]) == "FAILED":
            taskId = worker_update_file["tasks"][task]["taskId"]
            url = f"{trm_url}/tasks/{taskId}/subtasks"

            # print(url)

            payload = {}
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            subtasks = requests.request("GET", url, headers=headers, data=payload)
            response_in_dict = json.loads(subtasks.text)

            # print(json.dumps(response_in_dict, indent=4))

            retrycount_list = []
            for subtask in range(0, len(response_in_dict)):
                list_value = int((response_in_dict[subtask]["retryCount"]))
                retrycount_list.append(list_value)
            # print(f"max retry count is {max(retrycount_list)}")

            for subtask in range(0, len(response_in_dict)):
                # print("test")
                if (response_in_dict[subtask]["retryCount"]) == max(retrycount_list):
                    # print(response_in_dict[subtask])
                    # subtask_affected = json.dumps(response_in_dict[subtask], indent=4)
                    subtask_affected = response_in_dict[subtask]
                    # print(subtask_affected)
                    subtask_dict[subtask] = subtask_affected
                    # subtask_dict[taskId] = subtask_affected
                    subtask_id = subtask_dict[subtask]["id"]
                    # print(taskId, subtask_id)
                    # task_sub_dict[taskId] = subtask_id
                    task_sub_dict[taskId] = subtask_affected
                    # print(f"subtask affected is - \n {subtask_affected}")
    # print(subtask_dict)
    print("\n")

    # TODO pushing the subtasks to json
    with open("failed_subtasks.json", "w") as data_file:
        json.dump(task_sub_dict, data_file)
    return task_sub_dict


def push_overall_status(worker_update_status):
    update_status_total = (worker_update_status["total"])
    update_status_updated = (worker_update_status["updated"])
    update_status_failed = (worker_update_status["failed"])
    update_status_time_taken = (worker_update_status["total_time_taken"])
    alias = (worker_update_status["alias"])

    overall_status_dict = [
        {
            "measurement": "worker_update_overall_status",
            "tags": {
                "alias": alias,
                "BuildDetail": BuildDetail,
                "IAAS": system_id
            },
            "fields": {
                "total": update_status_total,
                "updated": update_status_updated,
                "failed": update_status_failed,
                "time_taken": update_status_time_taken
            }
        }
    ]
    print(overall_status_dict)
    if infra_client.write_points(overall_status_dict, protocol='json'):
        print("Data Insertion success")
        pass
    else:
        print("Dev-Data Insertion Failed")
        print(overall_status_dict)


def push_worker_update_status(worker_update_status):
    alias = (worker_update_status["alias"])

    for data in worker_update_status["tasks"]:

        taskId = data["taskId"]
        tenantName = data["tenantName"]
        status = data["status"]
        errorDescription = data["errorDescription"]
        worker_update_dict = [
            {
                "measurement": "worker_update_status",
                "tags": {
                    "alias": alias,
                    "BuildDetail": BuildDetail,
                    "IAAS": system_id
                },
                "fields": {
                    "taskId": taskId,
                    "tenantName": tenantName,
                    "status": status,
                    "error": errorDescription
                }
            }
        ]
        print(worker_update_dict)

        if infra_client.write_points(worker_update_dict, protocol='json'):
            print("Data Insertion success")
            pass
        else:
            print("Dev-Data Insertion Failed")
            print(worker_update_dict)


def push_failed_subtask(failed_subtasks):
    dev_client = InfluxDBClient('hci-rit-prism-sel.cpis.c.eu-de-2.cloud.sap', 8086, 'arpdb')
    dev_client.switch_database('arpdb')

    for task, subtask in data.items():
        task_id = task
        subtask_id = data[task]["id"]
        failed_at = data[task]["type"]
        due_to = data[task]["comments"]
        no_of_retries = data[task]["retryCount"]
        creationTime = data[task]["creationTime"]
        timeOut = data[task]["timeOut"]
        rollbackTimeout = data[task]["rollbackTimeout"]
        rollbackComments = data[task]["rollbackComments"]
        status = data[task]["status"]

        Failed_Subtasks_Info = [
            {
                "measurement": "Failed_Subtasks_Info",
                "tags": {
                    "alias": alias,
                    "BuildDetail": BuildDetail,
                    "IAAS": system_id
                },
                "fields": {
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "failed_at": failed_at,
                    "no_of_retries": no_of_retries,
                    "creationTime": creationTime,
                    "timeOut": timeOut,
                    "rollbackTimeout": rollbackTimeout,
                    "rollbackComments": rollbackComments,
                    "status": status,
                    "due_to": due_to

                }
            }
        ]
        print(Failed_Subtasks_Info)
        if dev_client.write_points(Failed_Subtasks_Info, protocol='json'):
            print("Data Insertion success")
            pass
        else:
            print("Dev-Data Insertion Failed")
            print(Failed_Subtasks_Info)


###########################################################

time.sleep(25)
worker_update_status = requests.request("GET", url, headers=headers, data=payload)

res_in_dict = json.loads(worker_update_status.text)  # converts string to dictionary
print(res_in_dict)
print("\n")
total_no_of_workers = (len(res_in_dict["tasks"]))


start_time = time.time()
while res_in_dict["inProgress"] != 0:
    worker_update_status = requests.request("GET", url, headers=headers, data=payload)
    res_in_dict = json.loads(worker_update_status.text)  # converts string to dictionary

    print(json.dumps(res_in_dict, indent=4))
    time.sleep(60)
print("worker updates are completed")
end_time = time.time()
sec = end_time - start_time

worker_update_status = requests.request("GET", url, headers=headers, data=payload)
# res_in_dict = json.loads(worker_update_status.text)
res_in_dict = worker_update_status.json()
# print(f"the type of this is -  {res_in_dict}")
# print(f"length of {len(res_in_dict)}")

in_json = worker_update_status.json()
with open("worker_update.json", "w") as data_file:
    json.dump(in_json, data_file)

time.sleep(20)

if res_in_dict["failed"] > 0:
    failed_tasks(worker_update_file=res_in_dict)
    end_time = time.time()
    sec = end_time - start_time
    ty_res = time.gmtime(sec)
    total_time_taken = time.strftime("%H:%M:%S", ty_res)
    print(f"Total time taken to update '{total_no_of_workers}' workers is -  {total_time_taken} mins")
else:
    end_time = time.time()
    sec = end_time - start_time
    ty_res = time.gmtime(sec)
    total_time_taken = time.strftime("%H:%M:%S", ty_res)
    print(f"Total time taken to update '{total_no_of_workers}' workers is -  {total_time_taken} mins")

res_in_dict["total_time_taken"] = total_time_taken
res_in_dict["alias"] = alias

print(res_in_dict)
#
infra_client = InfluxDBClient('hci-rit-prism-sel.cpis.c.eu-de-2.cloud.sap', 8086, 'arpdb')

infra_client.switch_database('arpdb')

push_overall_status(worker_update_status=res_in_dict)
push_worker_update_status(worker_update_status=res_in_dict)
print("*****************")
try:
    with open("failed_subtasks.json", "r") as data_file:
        data = json.loads(data_file.read())
        push_failed_subtask(failed_subtasks=data)
except json.decoder.JSONDecodeError as e:
    if "Expecting value" in str(e):
        print("No failures. hence no subtasks pushed to the table")
    else:
        raise e