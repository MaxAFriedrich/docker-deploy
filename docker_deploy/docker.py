# import shutil
# import subprocess
from pathlib import Path

import yaml

from docker_deploy import backend_map_lib
from docker_deploy import config_lib
from docker_deploy.ansible_deploy.task import Mkdir, Task, WriteFile, \
    DockerCompose, Rm, LocalCopy

DEPLOY_DIR = Path("deployments")


def init_deployment_dir() -> Task:
    return Mkdir(name="Create deployment directory",
                 path="/home/{{ansible_user}}/deployments")


# def load_compose():
#     if shutil.which("docker-compose") is not None:
#         return ["docker-compose"]
#     try:
#         result = subprocess.run(['docker', 'compose', '--version'],
#                                 stdout=subprocess.PIPE,
#                                 stderr=subprocess.PIPE,
#                                 text=True)
#
#         if result.returncode == 0:
#             return ['docker', 'compose']
#         raise FileNotFoundError("Docker Compose could not be found")
#
#     except FileNotFoundError:
#         raise FileNotFoundError("Docker Compose could not be found")
#
#
# COMPOSE = load_compose()


def no_ports_required(boxes: list[config_lib.Box]) -> int:
    count = 0
    for box in boxes:
        count += len(box.services)
    return count


def strip_docker_ports(docker_file: dict) -> dict:
    for service in docker_file['services']:
        if 'ports' in docker_file['services'][service]:
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
        docker_file: str,
        instance_id: int,
        start_port: int,
        deploy_host: str
) -> (backend_map_lib.Instance, list[Task]):
    tasks = []
    docker_file = yaml.safe_load(docker_file)

    target_dir = "/home/{{ansible_user}}" / DEPLOY_DIR / str(instance_id)

    tasks.append(LocalCopy(
        name="Copy target directory",
        src="/home/{{ansible_user}}/deployments/docker",
        dest=str(target_dir),
        is_dir=True
    ))

    if deploy_host == "localhost":
        deploy_host = "127.0.0.1"

    docker_file, instance_services = adapt_docker_compose(
        start_port,
        deploy_host,
        backend_map.layout,
        config.boxes,
        docker_file
    )

    tasks.append(WriteFile(
        name="Write docker-compose.yml",
        path=str(target_dir / 'docker-compose.yml'),
        content=yaml.dump(docker_file)
    ))

    return backend_map_lib.Instance(
        id=str(instance_id),
        services=instance_services
    ), tasks


def start_deployment(instance_id: int) -> list[Task]:
    # subprocess.run(
    #     COMPOSE + ["up", "-d", "--build", "--force-recreate"],
    #     cwd=DEPLOY_DIR / str(instance_id),
    # )
    return [
        DockerCompose(
            name="Start deployment",
            args="up -d --build --force-recreate",
            path=str("/home/{{ansible_user}}" / DEPLOY_DIR / str(instance_id))
        )
    ]


def stop_deployment(instance_id: int) -> list[Task]:
    # subprocess.run(
    #     COMPOSE + ["down"], cwd=DEPLOY_DIR / str(instance_id)
    # )
    return [
        DockerCompose(
            name="Stop deployment",
            args="down",
            path=str("/home/{{ansible_user}}" / DEPLOY_DIR / str(instance_id))
        )
    ]


def delete_deployment(instance_id: int) -> list[Task]:
    # subprocess.run(
    #     COMPOSE + ["rm", "--force", "--stop"], cwd=DEPLOY_DIR / str(
    #         instance_id)
    # )
    # shutil.rmtree(DEPLOY_DIR / str(instance_id))
    return [
        DockerCompose(
            name="Delete deployment",
            args="rm --force --stop",
            path=str("/home/{{ansible_user}}" / DEPLOY_DIR / str(instance_id))
        ),
        Rm(
            name="Delete deployment directory",
            path=str("/home/{{ansible_user}}" / DEPLOY_DIR / str(instance_id))
        )
    ]
