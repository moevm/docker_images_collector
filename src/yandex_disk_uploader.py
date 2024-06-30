import os
import requests
import hashlib


def calculate_md5(file_path, chunk_size=8192):
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def get_yandex_disk_files_md5(directory_path, token):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }
    params = {
        "path": directory_path,
        "fields": "_embedded.items.name,_embedded.items.md5",
        "limit": 10000
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        items = response.json().get("_embedded", {}).get("items", [])
        return {item["name"]: item["md5"] for item in items if "md5" in item}
    else:
        print(f"Failed to get file info for {directory_path} on Yandex.Disk: {response.text}")
        return {}


def create_yandex_disk_directory(directory_path, token):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }
    params = {
        "path": directory_path,
    }

    requests.put(url, headers=headers, params=params)


def upload_to_yandex_disk(directory, token, yandex_disk_directory):
    create_yandex_disk_directory(yandex_disk_directory, token)
    yandex_files_md5 = get_yandex_disk_files_md5(yandex_disk_directory, token)

    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"

    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    for file_name in files:
        file_path = os.path.join(directory, file_name)
        local_md5 = calculate_md5(file_path)

        if local_md5 in yandex_files_md5.values():
            print(f"File {file_name} already exists on Yandex.Disk. Skipping upload.", flush=True)
            continue

        params = {
            "path": f"{yandex_disk_directory}/{file_name}",
            "overwrite": "true",
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            upload_url = response.json()["href"]
            print(f"Starting upload of {file_name} to Yandex.Disk*", flush=True)

            with open(file_path, "rb") as file:
                upload_response = requests.put(
                    upload_url,
                    headers={"Content-Type": "application/octet-stream"},
                    data=iter(lambda: file.read(4096), b''),
                    stream=True
                )

                if upload_response.status_code == 201:
                    print(f"Uploaded {file_name} to Yandex.Disk", flush=True)
                else:
                    print(f"Failed to upload {file_name} to Yandex.Disk: {upload_response.text}", flush=True)
        else:
            print(f"Failed to get upload URL for {file_name}: {response.text}", flush=True)

