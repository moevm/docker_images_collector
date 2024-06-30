class DockerImageCollectorError(Exception):
    pass


class DockerDaemonNotRunningError(DockerImageCollectorError):
    pass


class GitRepositoryError(DockerImageCollectorError):
    pass


class InvalidGitRepository(GitRepositoryError):
    pass


class BranchCheckoutError(GitRepositoryError):
    pass
