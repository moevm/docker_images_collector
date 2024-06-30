import os
import subprocess
from .exception import DockerDaemonNotRunningError


def is_docker_running():
    try:
        subprocess.run(["docker", "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def image_exists(image):
    try:
        subprocess.run(["docker", "inspect", image], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def pull_docker_image(image):
    try:
        subprocess.run(["docker", "pull", image], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def save_docker_image(image, directory):
    if not image_exists(image):
        print(f"Image {image} not found locally. Attempting to pull from Docker Hub...")
        if not pull_docker_image(image):
            print(f"Failed to pull image {image} from Docker Hub.")
            return False

    if not os.path.exists(directory):
        os.makedirs(directory)

    image_name = image.replace("/", "_").replace(":", "_")
    file_name = os.path.join(directory, image_name + ".tar")

    try:
        subprocess.run(["docker", "save", "-o", file_name, image], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to save Docker image {image} to {file_name}. Error: {e}")
        return False


def save_docker_images(images, directory):
    if not is_docker_running():
        raise DockerDaemonNotRunningError("Docker daemon is not running. Please start Docker and try again.")

    for image in images:
        print(f"Starting to save Docker image {image} as tar archive*")
        success = save_docker_image(image, directory)
        if success:
            print(f"Successfully saved {image}.\n")
        else:
            print(f"Failed to save {image}.\n")

