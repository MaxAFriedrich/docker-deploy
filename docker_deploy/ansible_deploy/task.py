class Task(dict):

    def __init__(self, name: str, action: str, args: dict):
        super().__init__()
        self['name'] = name
        self['action'] = action
        self['args'] = args


class Mkdir(Task):

    def __init__(self, name: str, path: str):
        super().__init__(name, 'file', {'path': path, 'state': 'directory'})


class Copy(Task):

    def __init__(self, name: str, src: str, dest: str):
        super().__init__(name, 'copy', {'src': src, 'dest': dest})


class WriteFile(Task):

    def __init__(self, name: str, path: str, content: str):
        super().__init__(name, 'copy', {'content': content, 'dest': path})


class Rm(Task):

    def __init__(self, name: str, path: str):
        super().__init__(name, 'file', {'path': path, 'state': 'absent'})


class DockerCompose(Task):

    def __init__(self, name: str, state: str, path: str):
        super().__init__(name, 'docker_compose_v2', {
            'state': state,
            'project_src': path,
            'remove_orphans': True,
            'recreate': "always"
        })
