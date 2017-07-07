import yaml


def read_config(file):
    with open(file, 'r') as stream:
        return yaml.load(stream)
