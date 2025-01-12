import logging
from dataclasses import dataclass

import yaml

import config_lib


@dataclass
class Service:
    id: str
    name: str
    description: str
    proxy: str

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "proxy": self.proxy
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            proxy=data['proxy']
        )


@dataclass
class Box:
    id: str
    name: str
    services: list[Service]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "services": [service.to_dict() for service in self.services]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data['id'],
            name=data['name'],
            services=[Service.from_dict(service) for service in
                      data['services']]
        )


@dataclass
class ServiceInstance:
    box_id: str
    service_id: str
    host: str

    def to_dict(self):
        return {
            "box_id": self.box_id,
            "service_id": self.service_id,
            "host": self.host
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            box_id=data['box_id'],
            service_id=data['service_id'],
            host=data['host']
        )


@dataclass
class Instance:
    id: str
    name: str
    services: list[ServiceInstance]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "services": [service.to_dict() for service in self.services]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data['id'],
            name=data['name'],
            services=[ServiceInstance.from_dict(service) for service in
                      data['services']]
        )


@dataclass
class BackendMap:
    lb_endpoint: str
    layout: list[Box]
    backends: list[Instance]

    def to_dict(self):
        return {
            "lb_endpoint": self.lb_endpoint,
            "layout": self.layout,
            "backends": self.backends
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            lb_endpoint=data['lb_endpoint'],
            layout=[Box.from_dict(box) for box in data['layout']],
            backends=[Instance.from_dict(backend) for backend in
                      data['backends']]
        )


def save_backend_map(backend_map: BackendMap, output_file: str):
    with open(output_file, 'w') as file:
        yaml.dump(backend_map.to_dict(), file)
    logging.info(f'Backend map saved to {output_file}')


def load_backend_map(file_path: str) -> BackendMap:
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        return BackendMap.from_dict(data)


def strip_name(name: str) -> str:
    out = name.replace(" ", "_").lower()
    for char in out:
        if not char.isalnum() and char != "_":
            out = out.replace(char, "")

    return out


def generate_id(current_ids: set[str], name: str) -> str:
    name = strip_name(name)
    if name not in current_ids:
        return name
    current_count = 1
    while f"{name}_{current_count}" in current_ids:
        current_count += 1
    return f"{name}_{current_count}"


def config_boxes_to_backend_map_boxes(boxes: list[config_lib.Box]) -> list[Box]:
    box_ids = set()
    backend_map_boxes = []
    for box in boxes:
        service_ids = set()
        services = []
        for service in box.services:
            services.append(Service(
                id=generate_id(service_ids, box.name),
                name=service.name,
                description=service.description,
                proxy=service.protocol
            ))
        backend_map_boxes.append(Box(
            id=generate_id(box_ids, "box"),
            name=box.name,
            services=services
        ))
    return backend_map_boxes


def build_backend_map_base(target_location: str, lb_endpoint: str,
                           boxes: list[config_lib.Box]) -> BackendMap:
    try:
        backend_map = load_backend_map(target_location)
        logging.info(f'Loaded existing backend map from {target_location}')
        return backend_map
    except FileNotFoundError:
        logging.info('No existing backend map found. Creating new backend map.')
    except KeyError:
        logging.error('Invalid backend map file. Creating new backend map.')
    return BackendMap(
        lb_endpoint=lb_endpoint,
        layout=config_boxes_to_backend_map_boxes(boxes),
        backends=[]
    )
