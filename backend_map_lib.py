import logging
from dataclasses import dataclass

import yaml

from config_lib import Config


@dataclass
class Service:
    friendly_name: str
    friendly_description: str
    id: str
    proxy_type: str
    ports: list[int]

    def layout_dict(self):
        return {
            "name": self.friendly_name,
            "description": self.friendly_description,
            "id": self.id,
            "proxy": self.proxy_type,
        }


@dataclass
class Box:
    friendly_name: str
    id: str
    services: list[Service]
    hostname: str

    @property
    def no_instances(self):
        return min([len(service.ports) for service in self.services])

    def layout_dict(self):
        return {
            "name": self.friendly_name,
            "id": self.id,
            "services": [service.layout_dict() for service in self.services],
        }

    def backend_services(self, instance_id):
        out = []
        for service in self.services:
            port = service.ports[instance_id]
            out.append({
                "box_id": self.id,
                "service_id": service.id,
                "host": f"{self.hostname}:{port}",
            })
        return out


@dataclass
class BackendMap:
    lb_endpoint: str
    docker_boxes: list[Box]

    @property
    def __no_instances(self):
        return min([box.no_instances for box in self.docker_boxes])

    @property
    def layout(self):
        return [box.layout_dict() for box in self.docker_boxes]

    @property
    def backends(self):
        instances = []
        for instance_id in range(self.__no_instances):
            services = []
            for box in self.docker_boxes:
                services.extend(box.backend_services(instance_id))
            instances.append({
                "services": services,
                "id": instance_id
            })
        return instances

    def to_dict(self):
        return {
            "lb_endpoint": self.lb_endpoint,
            "layout": self.layout,
            "backends": self.backends
        }


def save_backend_map(backend_map: BackendMap, output_file: str):
    with open(output_file, 'w') as file:
        yaml.dump(backend_map.to_dict(), file)
    logging.info(f'Backend map saved to {output_file}')
