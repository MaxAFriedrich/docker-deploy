import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Buildable:
    context: str
    dockerfile: str
    args: dict[str, str]
    tag: str

    def build(self):
        subprocess.run([
            'docker', 'build',
            '.',
            '-t', self.tag,
            '-f', self.dockerfile,
            *[f'--build-arg {key}={value}' for key, value in self.args.items()]
        ],cwd=self.context)

    def push(self):
        subprocess.run(['docker', 'push', self.tag])


def extract_images(docker_compose: dict) -> list[str]:
    images = []
    for service in docker_compose['services'].values():
        if 'image' in service:
            images.append(service['image'])
    return images


def pull_push_image(image: str, registry_url: str) -> str:
    subprocess.run(['docker', 'pull', image])
    name = image.split('/')[-1]
    tag = f'{registry_url}/{name}'
    subprocess.run(['docker', 'tag', image, tag])
    subprocess.run(['docker', 'push', tag])
    return tag


def replace_images(docker_compose: dict, images: list[str],
                   image_tags: list[str]) -> dict:
    if len(images) != len(image_tags):
        raise ValueError("Length of images and image_tags must match.")
    for i, image in enumerate(images):
        for service in docker_compose['services'].values():
            if 'image' in service and service['image'] == image:
                service['image'] = image_tags[i]
    return docker_compose


def convert_buildable(docker_compose: dict, registry_url: str,
                      cwd: str) -> dict:
    for name, service in docker_compose['services'].items():
        if 'build' not in service:
            continue
        tag = f"{registry_url}/{name}:latest"
        if type(service['build']) is str:
            extract = Buildable(
                context=Path(cwd) / service['build'],
                dockerfile='Dockerfile',
                args={},
                tag=tag,
            )
        else:
            extract = Buildable(
                context=Path(cwd) / service['build'].get('context', '.'),
                dockerfile=service['build'].get('dockerfile', 'Dockerfile'),
                args=service['build'].get('args', {}),
                tag=tag,
            )
            print(extract)
        extract.build()
        extract.push()
        service['image'] = tag
        del service['build']
    return docker_compose


def build(docker_compose: str, registry_url: str, cwd: str) -> str:
    docker_compose = yaml.safe_load(docker_compose)

    images = extract_images(docker_compose)
    image_tags = [pull_push_image(image, registry_url) for image in images]
    docker_compose = replace_images(docker_compose, images, image_tags)

    docker_compose = convert_buildable(docker_compose, registry_url, cwd)

    return yaml.dump(docker_compose)


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print("Usage: python -m docker_deploy.registry "
              "<docker-compose.yml> <registry_url> <cwd>")
        exit(1)

    with open(sys.argv[1], 'r') as file:
        print(build(file.read(), sys.argv[2], sys.argv[3]))
