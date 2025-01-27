import argparse
import logging
from pathlib import Path

import yaml

from docker_deploy import backend_map_lib, registry
from docker_deploy import config_lib
from docker_deploy import docker
from docker_deploy.ansible_deploy import Play, Playbook, get_hostnames, \
    next_hostname, get_host_for_instance

# Set up logging
logging.basicConfig(filename='deploy.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# TODO fix logging to be relvent with ansible system


def deploy_instances(
        count: int,
        backend_map: backend_map_lib.BackendMap,
        config: config_lib.Config
) -> (backend_map_lib.BackendMap, list[Play]):
    plays = []
    possible_hosts = get_hostnames(config.inventory)

    logging.info(f'Deploying {count} instances.')

    next_instance_id = max(
        [int(instance.id) for instance in backend_map.backends] + [0]) + 1
    next_free_port = config.output.min_port
    required_ports = 0

    for box in config.boxes:
        required_ports += len(box.services)

    for instance in backend_map.backends:
        for service in instance.services:
            port = int(service.host.split(':')[1])
            next_free_port = max(next_free_port, port + 1)

    with open(Path(config.target) / 'docker-compose.yml', 'r') as file:
        docker_file = file.read()

    if config.registry is not None:
        docker_file = registry.build(docker_file, config.registry,
                                     config.target)

    for _ in range(count):
        # logging.info(f'Starting deployment of instance {next_instance_id}.')
        logging.info(
            f'Building playbook to deploy instance {next_instance_id}.')
        map_instance, tasks = docker.create_deployment(
            config,
            backend_map,
            docker_file,
            next_instance_id,
            next_free_port,
            next_hostname(possible_hosts, backend_map.backends)
        )
        tasks.extend(docker.start_deployment(int(map_instance.id)))
        backend_map.backends.append(map_instance)
        next_instance_id += 1
        next_free_port += required_ports
        target_host = next_hostname(possible_hosts, backend_map.backends)
        plays.append(Play(
            name=f'Deploy Instance {map_instance.id}',
            tasks=tasks,
            hosts=[target_host]
        ))

    # logging.info(f'Completed deployment of {count} instances.')
    return backend_map, plays


def destroy_instance(
        instance_id,
        instances: list[backend_map_lib.Instance]
) -> (list[backend_map_lib.Instance], list[Play]):
    instance_index = get_instance_index(instance_id, instances)

    if instance_index is None:
        logging.error(f'Instance {instance_id} does not exist.')
        return instances, []

    logging.info(f'Destroying instance {instance_id}.')

    plays = [Play(
        name=f'Destroy Instance {instance_id}',
        tasks=docker.delete_deployment(instance_id),
        hosts=[get_host_for_instance(instance_id, instances)]
    )]

    instances.pop(instance_index)

    return instances, plays


def get_instance_index(instance_id, instances):
    instance_index = None
    for i in range(len(instances)):
        if instances[i].id == instance_id:
            instance_index = i
            break
    return instance_index


def destroy_all(instances) -> list[Play]:
    logging.info('Destroying all instances.')

    instance_ids = [instance.id for instance in instances]

    plays = []

    for instance_id in instance_ids:
        logging.info(f'Starting destruction of instance {instance_id}.')

        plays.append(Play(
            name=f'Destroy Instance {instance_id}',
            tasks=docker.delete_deployment(instance_id),
            hosts=[get_host_for_instance(instance_id, instances)]
        ))

    logging.info(f'Completed destruction of all {len(instance_ids)} instances.')

    return plays


def restart_instance(instance_id, instances) -> list[Play]:
    instance_index = get_instance_index(instance_id, instances)

    if instance_index is None:
        logging.error(f'Instance {instance_id} does not exist.')
        return []

    logging.info(f'Restarting instance {instance_id}.')
    tasks = []
    tasks.extend(docker.stop_deployment(instance_id))
    tasks.extend(docker.delete_deployment(instance_id))
    tasks.extend(docker.start_deployment(instance_id))

    plays = [
        Play(
            name=f'Stop Instance {instance_id}',
            tasks=tasks,
            hosts=[get_host_for_instance(instance_id, instances)]
        )
    ]

    return plays


def restart_all(instances) -> list[Play]:
    logging.info('Restarting all instances.')
    plays = []
    instance_ids = [instance.id for instance in instances]

    for instance_id in instance_ids:
        logging.info(f'Starting restart of instance {instance_id}.')
        plays.extend(restart_instance(instance_id, instances))

    return plays


# def all_running_instances():
#     instance_ids = []
#     for potential_id in docker.DEPLOY_DIR.iterdir():
#         if potential_id.is_dir():
#             instance_ids.append(potential_id.name)
#     return instance_ids


def print_ids(instances: list[backend_map_lib.Instance]) -> None:
    for instance in instances:
        print(instance.id)


def main():
    config = config_lib.load_config('config.yml')

    parser = argparse.ArgumentParser(description='Deploy and manage instances.')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy instances')
    deploy_parser.add_argument('count', type=int,
                               help='Number of instances to deploy')

    # Destroy command
    destroy_parser = subparsers.add_parser('destroy', help='Destroy instances')
    destroy_parser.add_argument('target',
                                help='Instance ID or "all" to destroy all '
                                     'instances')

    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart instances')
    restart_parser.add_argument('target',
                                help='Instance ID or "all" to restart all '
                                     'instances')

    # List ids command
    subparsers.add_parser('ids', help='List all instance IDs')

    args = parser.parse_args()

    plays: list[Play] = [Play(
        name='Init Deploy Dir',
        tasks=[
            docker.init_deployment_dir()
        ],
        hosts=['all'] if config.inventory is not None else ['localhost']
    )]

    backend_map = backend_map_lib.build_backend_map_base(
        config.output.backend_map,
        config.lb_endpoint,
        config.boxes
    )

    if args.command == 'deploy':
        backend_map, deploy_plays = deploy_instances(
            args.count,
            backend_map,
            config
        )
        plays.extend(deploy_plays)

        backend_map_lib.save_backend_map(
            backend_map,
            config.output.backend_map,
            config.launch_command
        )

    elif args.command == 'destroy':
        if args.target == 'all':
            destroy_plays = destroy_all(backend_map.backends)
            backend_map.backends = []
        else:
            backend_map.backends, destroy_plays = destroy_instance(
                args.target,
                backend_map.backends
            )

        plays.extend(destroy_plays)
        backend_map_lib.save_backend_map(
            backend_map,
            config.output.backend_map,
            config.launch_command
        )

        # if args.target == 'all':
        #     subprocess.run(config.stop_command["command"],
        #                    cwd=config.stop_command["context"],
        #                    shell=True, check=True)
        #     logging.info(f"Ran stop command: {config.stop_command}")
    elif args.command == 'restart':
        if args.target == 'all':
            restart_plays = restart_all(backend_map.backends)
        else:
            restart_plays = restart_instance(args.target, backend_map.backends)
        plays.extend(restart_plays)

    elif args.command == 'ids':
        print_ids(backend_map.backends)

    # TODO remove this debugging
    print(yaml.dump(Playbook(plays).to_dict()))
    # Playbook(plays).run(config.inventory)


if __name__ == '__main__':
    main()
