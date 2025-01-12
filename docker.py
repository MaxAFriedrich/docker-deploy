import shutil
import subprocess
from pathlib import Path

import yaml

import backend_map_lib
import config_lib

DEPLOY_DIR = Path("./deployments")

DEPLOY_DIR.mkdir(exist_ok=True)


def no_ports_required(boxes: list[config_lib.Box]) -> int:
    count = 0
    for box in boxes:
        count += len(box.services)
    return count


def strip_docker_ports(docker_file: dict) -> dict:
    for service in docker_file['services']:
        docker_file['services'][service].pop('ports')
    return docker_file


def get_service_id(layout: list[backend_map_lib.Box],
                   target_service: config_lib.Service, box_id: str) -> str:
    out = ""
    for box in layout:
        if box.id != box_id:
            continue
        out = service_matches(box.services, target_service)

    if out == "":
        raise ValueError("Service not found in layout")

    return out


def service_matches(services: list[backend_map_lib.Service],
                    target_service: config_lib.Service) -> str:
    out = ""
    for service in services:
        if service.name != target_service.name:
            continue
        if service.proxy != target_service.protocol:
            continue
        if service.description != target_service.description:
            continue
        out = service.id
    return out


def get_box_id(layout: list[backend_map_lib.Box],
               target_box: config_lib.Box) -> str:
    out = ""
    for box in layout:
        if box.name != target_box.name:
            continue
        services_match = True
        for service in target_box.services:
            if service_matches(box.services, service) == "":
                services_match = False
                break
        if not services_match:
            continue
        out = box.id

    if out == "":
        raise ValueError("Box not found in layout")

    return out


def adapt_docker_compose(
        next_port: int,
        interface: str,
        backend_boxes: list[backend_map_lib.Box],
        config_boxes: list[config_lib.Box],
        docker_file: dict,
) -> (dict, list[backend_map_lib.ServiceInstance]):
    docker_file = strip_docker_ports(docker_file)
    instance_services = []
    for config_box in config_boxes:
        box_id = get_box_id(backend_boxes, config_box)
        for service in config_box.services:
            service_id = get_service_id(backend_boxes, service, box_id)
            new_port = f"{interface}:{next_port}:{service.port}"
            existing_ports = docker_file["services"][config_box.name].get(
                "ports", [])
            existing_ports.append(new_port)
            docker_file["services"][config_box.name]["ports"] = existing_ports

            instance_services.append(backend_map_lib.ServiceInstance(
                box_id=box_id,
                service_id=service_id,
                host=f"{interface}:{next_port}",
            ))

            next_port += 1

    return docker_file, instance_services


def create_deployment(
        config: config_lib.Config,
        backend_map: backend_map_lib.BackendMap,
        docker_file: dict,
        instance_id: int,
        start_port: int,
) -> backend_map_lib.Instance:
    target_dir = DEPLOY_DIR / str(instance_id)

    shutil.copytree(config.target.dir, target_dir)

    docker_file, instance_services = adapt_docker_compose(
        start_port,
        config.output.interface_ip,
        backend_map.layout,
        config.boxes,
        docker_file
    )

    with open(target_dir / config.target.docker_file, 'w') as file:
        yaml.dump(docker_file, file)

    return backend_map_lib.Instance(
        id=str(instance_id),
        services=instance_services
    )


def start_deployment(instance_id: int, docker_file: str) -> None:
    subprocess.run(
        ["docker-compose", "up", "-d", "--build", "--context",
         str(DEPLOY_DIR / str(instance_id)), "--project-name",
         f"instance-{instance_id}", "--remove-orphans", "--file",
         docker_file])


def stop_deployment(instance_id: int) -> None:
    subprocess.run(
        ["docker-compose", "down", "--context",
         str(DEPLOY_DIR / str(instance_id)), "--project-name",
         f"instance-{instance_id}"])


def delete_deployment(instance_id: int) -> None:
    subprocess.run(
        ["docker-compose", "rm", "--force", "--stop", "--context",
         str(DEPLOY_DIR / str(instance_id)), "--project-name",
         f"instance-{instance_id}"])
    shutil.rmtree(DEPLOY_DIR / str(instance_id))
