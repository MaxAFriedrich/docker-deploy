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
        self['hosts'] = hosts
        self['tasks'] = tasks

    def to_dict(self):
        return {
            "name": self['name'],
            "hosts": self['hosts'],
            "tasks": [task.to_dict() for task in self['tasks']],
            "gather_facts": False
        }


class Playbook(dict):

    def __init__(self, plays: list[Play]):
        super().__init__()
        self['plays'] = plays

    def to_dict(self):
        return [play.to_dict() for play in self['plays']]

    def write(self, file_path: str):
        with open(file_path, 'w') as file:
            yaml.dump(self.to_dict(), file)

    def run(self, inventory_file: str | None):
        playbook_tmp = "generated_playbook.yml"
        self.write(playbook_tmp)
        args = ['ansible-playbook', playbook_tmp]
        if inventory_file is not None:
            args.extend(['-i', inventory_file])

        print(" ".join(args))
        try:
            result = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True
            )
            logging.info(result.stdout)
        except subprocess.CalledProcessError as e:
            logging.error(
                f"Command '{e.cmd}' returned non-zero exit status "
                f"{e.returncode}.")
            logging.error(e.stderr)
            logging.error(e.stdout)


def get_hostnames(inventory_file: str) -> list[str]:
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[inventory_file])
    hostnames = []
    for host in inventory.get_hosts():
        hostnames.append(str(host.name))
    if len(hostnames) == 0:
        hostnames = ['localhost']
    return hostnames


def next_hostname(possible_hosts: list[str], backends: list[Instance]):
    backend_counts = {host: 0 for host in possible_hosts}
    for backend in backends:
        for service in backend.services:
            host = service.host.split(':')[0]
            if host == '127.0.0.1':
                continue
            if host not in backend_counts:
                logging.error(f"Host {host} not found in inventory.")
                continue
            backend_counts[host] += 1

    return min(backend_counts, key=backend_counts.get)


def get_host_for_instance(
        instance_id: int, instances: list[Instance]
) -> str:
    hosts = set()
    for instance in instances:
        if instance.id != instance_id:
            continue
        for service in instance.services:
            hosts.add(service.host.split(':')[0])
    if len(hosts) == 0:
        hosts.add('localhost')
    if len(hosts) > 1:
        logging.error(
            f"Instance {instance_id} has services on multiple hosts.")
        return
    return list(hosts)[0]
