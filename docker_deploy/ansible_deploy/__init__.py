import logging
import subprocess
import tempfile

import yaml
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

from docker_deploy.ansible_deploy.task import Task
from docker_deploy.backend_map_lib import Instance


class Play(dict):

    def __init__(self, name: str, tasks: list[Task], hosts: list[str]):
        super().__init__()
        self['name'] = name
        self['tasks'] = tasks
        self['hosts'] = hosts


class Playbook(dict):

    def __init__(self, name: str, plays: list[Play]):
        super().__init__()
        self['name'] = name
        self['plays'] = plays

    def write(self, file_path: str):
        with open(file_path, 'w') as file:
            yaml.dump(self, file)

    def run(self, inventory_file: str | None):
        playbook_tmp = tempfile.NamedTemporaryFile(delete=False)
        self.write(playbook_tmp.name)

        result = subprocess.run(
            ['ansible-playbook', playbook_tmp.name, '-i', inventory_file],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(result.stdout)


def get_hostnames(inventory_file: str) -> list[str]:
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[inventory_file])
    hostnames = inventory.get_hosts()
    if len(hostnames) == 0:
        hostnames = ['localhost']
    return hostnames


def next_hostname(possible_hosts: list[str], backends: list[Instance]):
    backend_counts = {host: 0 for host in possible_hosts}
    for backend in backends:
        for service in backend.services:
            host = service.host.split(':')[0]
            if host not in backend_counts:
                logging.error(f"Host {host} not found in inventory.")
                continue
            backend_counts[host] += 1

    return min(backend_counts, key=backend_counts.get)


def get_hosts_for_instance(
        instance_id: int, instances: list[Instance]
) -> list[str]:
    hosts = []
    for instance in instances:
        if instance.id != instance_id:
            continue
        for service in instance.services:
            hosts.append(service.host.split(':')[0])
    return hosts
