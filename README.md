# CyberRange Deployment Tool

This is an implementation of a CyberRange deployment tool that works with my `backend-map.yml` specification.

## Overview

The `deploy.py` script allows you to deploy, destroy, and restart instances in a standardized manner. It uses a
configuration file (`config.yml`) and a backend map file (`backend-map.yml`) to manage the deployment of instances.

## Usage

**Note:** This project uses Poetry for dependency management. Make sure you have Poetry installed and use the following
commands to run the script.

The script supports the following commands:

- `deploy <count>`: Deploys the specified number of instances.
- `destroy all`: Destroys all instances.
- `destroy <instance-id>`: Destroys the specified instance.
- `restart <instance-id>`: Restarts the specified instance.
- `restart all`: Restarts all instances.

These commands are the standard set of commands that my spec allows for.

## Arguments

- `deploy <count>`: Deploys the specified number of instances.
  ```sh
  poetry run python3 deploy.py deploy 20
  ```

- `destroy all`: Destroys all instances.
  ```sh
  poetry run python3 deploy.py destroy all
  ```

- `destroy <instance-id>`: Destroys the specified instance.
  ```sh
  poetry run python3 deploy.py destroy <instance-id>
  ```

- `restart <instance-id>`: Restarts the specified instance.
  ```sh
  poetry run python3 deploy.py restart <instance-id>
  ```

- `restart all`: Restarts all instances.
  ```sh
  poetry run python3 deploy.py restart all
  ```

## Features

- **Deploy Instances**: Deploys the specified number of instances and updates the `backend-map.yml` file.
- **Destroy Instances**: Destroys the specified instance or all instances, cleaning up and resetting everything.
- **Restart Instances**: Restarts the specified instance or all instances.
- **Logging**: Saves logs to `./deploy.log`.
- **Backend Map**: Saves the updated `backend-map.yml` to the current directory (`./`).
- **Unique Instance IDs**: Ensures that instance IDs are not reused.

## Configuration

The script expects a `config.yml` file in the current directory. The configuration file should contain the following

- `version`: The version of the configuration file (should be `1`).
- `target`: The directory to pull the docker config files from.
- `lb_endpoint`: The endpoint of the load balancer.
- `output`:
    - `backend_map`: The path to write the updated backend map file to.
    - `min_port`: The minimum port number to use for the instances.
    - `max_port`: The maximum port number to use for the instances.
    - `interface_ip`: The IP address of the interface to bind to.
- `boxes`: A list of boxes to deploy.
    - `name`: The name of the box.
        - `services`: A list of services each box provides.
            - `name`: The name of the service.
            - `description`: A description of the service.
            - `port`: The port to bind the service to.
            - `protocol`: The protocol to use for the service, that the load balancer supports.

An example configuration file is shown below:

```yaml
version: 1
target: ./testing/docker
lb_endpoint: http://localhost:8000
output:
  backend_map: ./testing/bins/backend-map.yml
  min_port: 3000
  max_port: 7999
  interface_ip: 127.0.0.1
boxes:
  - name: wireshark
    services:
      - name: HTTP VNC
        description: An example of a proxied vnc server running inside a container.
        port: 3000
        protocol: http
      - name: HTTPS VNC
        description: An example of a proxied vnc server running inside a container.
        port: 3001
        protocol: https
  - name: nginx
    services:
      - name: Simple Web Server
        description: An example of a simple web server running inside a container.
        port: 80
        protocol: http
  - name: webserver
    services:
      - name: Vulnerable Web Server
        description: An example of a vulnerable web server running inside a container.
        port: 80
        protocol: http
```
