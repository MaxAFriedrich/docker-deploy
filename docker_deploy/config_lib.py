from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class Service:
    name: str
    description: str
    port: int
    protocol: str


@dataclass
class Box:
    name: str
    services: list[Service]


@dataclass
class Output:
    backend_map: str
    min_port: int
    max_port: int
    interface_ip: str


@dataclass
class Config:
    version: int
    output: Output
    target: str
    lb_endpoint: str
    launch_command: dict[str]
    stop_command: dict[str]
    boxes: list[Box]
    inventory: Optional[str] = None
    registry: Optional[str] = None


def load_config(file_path: str) -> Config:
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        return Config(
            version=data['version'],
            output=Output(
                backend_map=data['output']['backend_map'],
                min_port=data['output']['min_port'],
                max_port=data['output']['max_port'],
                interface_ip=data['output']['interface_ip']
            ),
            target=data['target'],
            lb_endpoint=data['lb_endpoint'],
            launch_command=data['launch_command'],
            stop_command=data['stop_command'],
            boxes=[Box(name=box['name'],
                       services=[Service(**service) for service in
                                 box['services']]) for box in data['boxes']],
            inventory=data.get('inventory'),
            registry=data.get('registry')
        )
