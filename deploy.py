import argparse
import logging

import backend_map_lib
import config_lib

# Set up logging
logging.basicConfig(filename='deploy.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def deploy_instances(count):
    # Placeholder for deploying instances
    logging.info(f'Deploying {count} instances.')
    # Implement deployment logic here
    # TODO
    pass


def destroy_instance(instance_id):
    # Placeholder for destroying a specific instance
    logging.info(f'Destroying instance {instance_id}.')
    # Implement destruction logic here
    # TODO
    pass


def destroy_all():
    # Placeholder for destroying all instances
    logging.info('Destroying all instances.')
    # Implement destruction logic here
    # TODO
    pass


def restart_instance(instance_id):
    # Placeholder for restarting a specific instance
    logging.info(f'Restarting instance {instance_id}.')
    # Implement restart logic here
    # TODO
    pass


def restart_all():
    # Placeholder for restarting all instances
    logging.info('Restarting all instances.')
    # Implement restart logic here
    # TODO
    pass


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
        deploy_instances(args.count)
        backend_map_lib.save_backend_map(backend_map, config.output.backend_map)

    elif args.command == 'destroy':
        if args.target == 'all':
            destroy_all()
        else:
            destroy_instance(args.target)
    elif args.command == 'restart':
        if args.target == 'all':
            restart_all()
        else:
            restart_instance(args.target)


if __name__ == '__main__':
    main()
