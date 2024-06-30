import os
import yaml
import tempfile
from git import Repo, GitCommandError, InvalidGitRepositoryError
from .exception import GitRepositoryError, InvalidGitRepository, BranchCheckoutError
from urllib.parse import urlparse


def scan_repositories(base_path):
    return [
        root for root, dirs, files in os.walk(base_path) if '.git' in dirs
    ]


def scan_remote_repos(repo_urls):
    repos = []
    for url in repo_urls:
        try:
            parsed_url = urlparse(url)
            repo_name = os.path.splitext(os.path.basename(parsed_url.path))[0]
            local_path = os.path.join(tempfile.gettempdir(), repo_name)

            if os.path.exists(local_path):
                repos.append(local_path)
            else:
                Repo.clone_from(url, local_path)
                repos.append(local_path)
        except GitCommandError as e:
            raise GitRepositoryError(f"Error cloning repository: {e}")
    return repos


def get_all_branches(repo_path):
    try:
        repo = Repo(repo_path)
        branches = [ref.name.split('/')[-1] for ref in repo.refs if 'HEAD' not in ref.name]

        if 'origin' in repo.remotes:
            branches += [ref.name.split('/')[-1] for ref in repo.remote('origin').refs if 'HEAD' not in ref.name]

        return list(set(branches))
    except InvalidGitRepositoryError as e:
        raise InvalidGitRepository(f"Invalid git repository: {e}")
    except ValueError as e:
        raise GitRepositoryError(f"Error: {e}")


def has_unmerged_paths(repo):
    return bool(repo.index.unmerged_blobs())


def list_changed_files(repo):
    return [item.a_path for item in repo.index.diff(None)]


def checkout_branch(repo, branch_name):
    git = repo.git

    try:
        if not repo.head.is_valid():
            raise BranchCheckoutError("HEAD is not in a valid state. Can't switch branches.")

        if repo.head.is_detached:
            raise BranchCheckoutError("HEAD is detached. Can't switch branches.")

        current_branch = repo.active_branch.name

        if repo.index.unmerged_blobs():
            raise BranchCheckoutError(
                "There are unmerged paths in the working directory. Staying on the current branch.")

        if repo.is_dirty(untracked_files=False):
            git.stash('save', 'Auto-stash before checkout')
            git.checkout(branch_name)

            try:
                git.stash('pop')
            except GitCommandError as e:
                raise BranchCheckoutError(
                    f"An error occurred while popping stash. A merge conflict occurred. " +
                    f"Please resolve the conflicts manually and commit the changes.")
        else:
            git.checkout(branch_name)

        return True
    except GitCommandError as e:
        try:
            git.checkout(current_branch)
        except GitCommandError as checkout_error:
            raise BranchCheckoutError(
                f"An error occurred. Returning to the current branch '{current_branch}'. Failed to return to the current branch '{current_branch}': {checkout_error}\nPlease resolve any conflicts manually and commit the changes.")

        raise BranchCheckoutError(f"An error occurred. Returning to the current branch '{current_branch}'.")
    except InvalidGitRepositoryError as e:
        raise InvalidGitRepository(f"Invalid git repository")
    except ValueError as e:
        raise GitRepositoryError(f"Error accessing repository")


def parse_dockerfile(dockerfile_path):
    images = []
    with open(dockerfile_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('FROM'):
                images.append(line.split()[1])
    return images


def parse_docker_compose(compose_path):
    images = []
    with open(compose_path, 'r', encoding='utf-8') as file:
        compose_content = yaml.safe_load(file)
        services = compose_content.get('services', {})
        for service in services.values():
            image = service.get('image')
            if image:
                images.append(image)
    return images


def find_images_recursive(data):
    images = []

    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'image' and isinstance(value, str):
                images.append(value)
            elif isinstance(value, (dict, list)):
                images.extend(find_images_recursive(value))
    elif isinstance(data, list):
        for item in data:
            images.extend(find_images_recursive(item))

    return images


def parse_github_actions(actions_path):
    images = []
    try:
        with open(actions_path, 'r', encoding='utf-8') as file:
            actions_content = yaml.safe_load(file)
            if not actions_content:
                return images

            images = find_images_recursive(actions_content)

    except (yaml.YAMLError, IOError) as e:
        raise GitRepositoryError(f"Error parsing YAML file {actions_path}: {e}")

    return images


def process_docker_files(repo_path):
    docker_images = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file == 'Dockerfile':
                dockerfile_images = parse_dockerfile(os.path.join(root, file))
                if dockerfile_images:
                    docker_images += dockerfile_images
            elif file == 'docker-compose.yml':
                compose_images = parse_docker_compose(os.path.join(root, file))
                if compose_images:
                    docker_images += compose_images
            elif file.endswith('.yml') or file.endswith('.yaml'):
                actions_images = parse_github_actions(os.path.join(root, file))
                if actions_images:
                    docker_images += actions_images

    return docker_images


def process_repository_images(repo_path):
    all_images = set()
    original_branch = None
    try:
        repo = Repo(repo_path)
        branches = get_all_branches(repo_path)

        original_branch = repo.active_branch.name

        for branch in branches:
            checkout_result = checkout_branch(repo, branch)

            if not checkout_result:
                break

            images = process_docker_files(repo_path)
            all_images |= set(images)

    except BranchCheckoutError as e:
        images = process_docker_files(repo_path)
        all_images |= set(images)

    except (InvalidGitRepository, GitRepositoryError, InvalidGitRepositoryError, ValueError) as e:
        pass

    finally:
        if original_branch:
            try:
                repo = Repo(repo_path)
                git = repo.git
                git.checkout(original_branch)
            except BranchCheckoutError as e:
                print(f"Failed to return to the original branch '{original_branch}': {e}")

    return all_images


def filter_images(images):
    return [image for image in images if ':' in image and 'latest' not in image.split(':')[1]]


def get_all_images_with_tags(base_path):
    all_images = set()
    print(f"Scanning local repositories in {base_path}*")
    repositories = scan_repositories(base_path)

    for repo_path in repositories:
        print(f"Processing repository: {repo_path}")
        images = process_repository_images(repo_path)
        all_images.update(images)
        if images:
            print(f"Found images in {repo_path}: {images}\n")
        else:
            print(f"No images found in {repo_path}.\n")

    return filter_images(all_images)


def get_remote_repo_images_with_tags(repo_urls):
    all_images = set()
    print(f"Cloning remote repositories: {repo_urls}...")
    repositories = scan_remote_repos(repo_urls)

    for repo_path in repositories:
        print(f"Processing repository: {repo_path}")
        images = process_repository_images(repo_path)
        all_images.update(images)
        if images:
            print(f"Found images in {repo_path}: {images}\n")
        else:
            print(f"No images found in {repo_path}.\n")

    return filter_images(all_images)
