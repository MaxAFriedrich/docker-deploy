import argparse
import logging
import threading
from pathlib import Path

import yaml

import backend_map_lib
import config_lib
import docker

# Set up logging
logging.basicConfig(filename='deploy.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def deploy_instances(count: int, backend_map: backend_map_lib.BackendMap,
                     config: config_lib.Config) -> backend_map_lib.BackendMap:
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

    threads = []
    new_backends = []

    def deploy_and_collect(*args):
        map_instance = docker.create_deployment(*args)
        docker.start_deployment(int(map_instance.id))
        new_backends.append(map_instance)

    for _ in range(count):
        logging.info(f'Starting deployment of instance {next_instance_id}.')
        thread = threading.Thread(target=deploy_and_collect, args=(
            config,
            backend_map,
            docker_file,
            next_instance_id,
            next_free_port
        ))
        threads.append(thread)
        thread.start()
        next_instance_id += 1
        next_free_port += required_ports

    for thread in threads:
        thread.join()

    backend_map.backends.extend(new_backends)

    logging.info(f'Completed deployment of {count} instances.')

    return backend_map


def destroy_instance(instance_id, instances: list[backend_map_lib.Instance]) \
        -> list[backend_map_lib.Instance]:
    logging.info(f'Destroying instance {instance_id}.')

    if not (docker.DEPLOY_DIR / instance_id).exists():
        logging.error(f'Instance {instance_id} does not exist.')
        return instances

    docker.delete_deployment(instance_id)

    for i in range(len(instances)):
        if instances[i].id == instance_id:
            del instances[i]
            break

    return instances


def destroy_all():
    logging.info('Destroying all instances.')

    instance_ids = all_running_instances()

    threads = []

    for instance_id in instance_ids:
        logging.info(f'Starting destruction of instance {instance_id}.')
        thread = threading.Thread(target=docker.delete_deployment,
                                  args=(instance_id,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logging.info(f'Completed destruction of all {len(instance_ids)} instances.')


def restart_instance(instance_id):
    logging.info(f'Restarting instance {instance_id}.')

    if not (docker.DEPLOY_DIR / instance_id).exists():
        logging.error(f'Instance {instance_id} does not exist.')
        return

    docker.stop_deployment(instance_id)
    docker.start_deployment(instance_id)


def restart_all():
    logging.info('Restarting all instances.')
    instance_ids = all_running_instances()

    threads = []

    for instance_id in instance_ids:
        logging.info(f'Starting restart of instance {instance_id}.')
        thread = threading.Thread(target=restart_instance,
                                  args=(instance_id,))
        threads.append(thread)
        thread.start()


def all_running_instances():
    instance_ids = []
    for potential_id in docker.DEPLOY_DIR.iterdir():
        if potential_id.is_dir():
            instance_ids.append(potential_id.name)
    return instance_ids


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

    args = parser.parse_args()

    backend_map = backend_map_lib.build_backend_map_base(
        config.output.backend_map,
        config.lb_endpoint,
        config.boxes
    )

    if args.command == 'deploy':
        backend_map = deploy_instances(args.count, backend_map, config)
        backend_map_lib.save_backend_map(backend_map, config.output.backend_map)

    elif args.command == 'destroy':
        if args.target == 'all':
            destroy_all()
            backend_map.backends = []
        else:
            backend_map.backends = destroy_instance(args.target,
                                                    backend_map.backends)
        backend_map_lib.save_backend_map(backend_map, config.output.backend_map)
    elif args.command == 'restart':
        if args.target == 'all':
            restart_all()
        else:
            restart_instance(args.target)


if __name__ == '__main__':
    main()
