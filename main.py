import argparse
import requests
from src.docker_image_extractor import get_all_images_with_tags, get_remote_repo_images_with_tags
from src.docker_image_loader import save_docker_images, is_docker_running
from src.yandex_disk_uploader import upload_to_yandex_disk


def check_yandex_disk_token(token):
    url = "https://cloud-api.yandex.net/v1/disk"
    headers = {"Authorization": f"OAuth {token}"}
    response = requests.get(url, headers=headers)
    return response.status_code == 200


def main():
    parser = argparse.ArgumentParser(description="Docker Images Collector")
    parser.add_argument("--function", choices=["local", "remote"], required=True, help="Function to execute")
    parser.add_argument("--base_path", help="Base path for local repositories")
    parser.add_argument("--repo_urls", help="Comma-separated list of remote repository URLs")
    parser.add_argument("--save_directory", required=True, help="Directory to save Docker images")
    parser.add_argument("--yandex_disk_directory", required=False, help="Directory on Yandex Disk to upload files")
    parser.add_argument("--yandex_disk_token", required=False, help="Token for Yandex Disk")

    args = parser.parse_args()

    if not is_docker_running():
        print("Docker daemon is not running. Please start Docker and try again.")
        return

    if args.function == "local" and not args.base_path:
        parser.error("--base_path is required for local function")

    if args.function == "remote" and not args.repo_urls:
        parser.error("--repo_urls is required for remote function")

    if args.function == "local":
        images = get_all_images_with_tags(args.base_path)
    else:
        repo_urls = args.repo_urls.split(",")
        images = get_remote_repo_images_with_tags(repo_urls)

    if not images:
        print("No correct images found.")
        return
    else:
        print(f"Correct images: {images}.\n")

    save_docker_images(images, args.save_directory)

    if args.yandex_disk_token and args.yandex_disk_directory:
        if check_yandex_disk_token(args.yandex_disk_token):
            upload_to_yandex_disk(args.save_directory, args.yandex_disk_token, args.yandex_disk_directory)
            print("Files uploaded to Yandex Disk successfully.")
        else:
            print("Invalid Yandex Disk token provided. Skipping upload.")
    else:
        print("Skipping upload to Yandex Disk. Token or directory not provided.")


if __name__ == "__main__":
    main()
