from pathlib import Path


class Task(dict):

    def __init__(self, name: str, action: str, args: dict):
        super().__init__()
        self['name'] = name
        self['action'] = action
        self['args'] = args

    def to_dict(self):
        return {
            "name": self['name'],
            self['action']: self['args']
        }


class Mkdir(Task):

    def __init__(self, name: str, path: str):
        super().__init__(name, 'file', {'path': path, 'state': 'directory'})


class Copy(Task):

    def __init__(self, name: str, src: str, dest: str):
        if Path(src).is_dir():
            src = src.rstrip('/')+"/."
            dest = dest.rstrip('/')
        super().__init__(name, 'copy', {'src': src, 'dest': dest})


class WriteFile(Task):

    def __init__(self, name: str, path: str, content: str):
        super().__init__(name, 'copy', {'content': content, 'dest': path})


class Rm(Task):

    def __init__(self, name: str, path: str):
        super().__init__(name, 'file', {'path': path, 'state': 'absent'})


class DockerCompose(Task):

    def __init__(self, name: str, args: str, path: str):
        super().__init__(
            name,
            'command',
            {
                'cmd': f"bash -c 'if command -v docker-compose &> /dev/null; "
                       f"then docker-compose {args}; else docker compose "
                       f"{args}; fi'",
                'chdir': path
            })
