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


def adapt_docker_compose(
        next_port: int,
        interface: str,
        map_boxes: list[backend_map_lib.Box],
        config_boxes: list[config_lib.Box],
        docker_file: dict
) -> dict:
    docker_file = strip_docker_ports(docker_file)
    for config_box in config_boxes:
        for service in config_box.services:
            new_port = f"{interface}:{next_port}:{service.port}"
            existing_ports = docker_file["services"][config_box.name].get(
                "ports", [])
            existing_ports.append(new_port)
            docker_file["services"][config_box.name]["ports"] = existing_ports

            # TODO add to backend_map

            next_port += 1

    return docker_file


def create_deployment(
        config: config_lib.Config,
        backend_map: backend_map_lib.BackendMap,
        docker_file: dict,
        instance_id: int
) -> None:
    target_dir = DEPLOY_DIR / str(instance_id)

    shutil.copytree(config.target.dir, target_dir)

    docker_file = adapt_docker_compose(
        config.output.min_port,
        config.output.interface_ip,
        backend_map.docker_boxes,
        config.boxes,
        docker_file
    )

    with open(target_dir / config.target.docker_file, 'w') as file:
        yaml.dump(docker_file, file)


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
