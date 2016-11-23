#!/usr/bin/env python

"""
Dynamic Ansible inventory for Terraform.

For local `terraform.tfstate`:

  export TFSTATE_ROOT=terraform/web-cakes-dev-us-west-2
  ansible-playbook -i plugins/inventory/terraform.py openshift-ansible/playbooks/byo/config.yml

"""

from collections import defaultdict
import argparse
import json
import os


def iterate_tfstate_files(root):
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if os.path.splitext(name)[-1] == '.tfstate':
                yield os.path.join(dirpath, name)

def iterate_resources(filenames):
    for filename in filenames:
        with open(filename, 'r') as json_file:
            state = json.load(json_file)
            for module in state['modules']:
                name = module['path'][-1]
                for key, resource in module['resources'].items():
                    yield name, key, resource

"""
See http://docs.ansible.com/ansible/dev_guide/developing_inventory.html
"""
def build_groups(resources):
    groups = {
        'OSEv3': {
            'children': [
                'masters',
                'etcd',
                'nodes',
            ],
        },
        'masters': [],
        'etcd':    [],
        'nodes':   [],
    }

    for module_name, key, resource in resources:
        if not key.startswith('aws_instance.'):
            continue

        host_ip = resource['primary']['attributes']['private_ip']
        
        if key.startswith('aws_instance.master.'):
            groups['masters'].append(host_ip)
            groups['etcd'].append(host_ip)
            groups['nodes'].append(host_ip)

        if key.startswith('aws_instance.nodes.'):
            groups['nodes'].append(host_ip)

    groups['_meta'] = {'hostvars': {}}

    return groups

def main():
    parser = argparse.ArgumentParser(
        __file__, __doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    modes = parser.add_mutually_exclusive_group(required=False)

    modes.add_argument('--list',
                       action='store_true',
                       help='list all the groups to be managed by Ansible')

    default_root = os.environ.get('TFSTATE_ROOT',
                                  os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                               '..', '..', )))
    parser.add_argument('--root',
                        default=default_root,
                        help='`.tfstate` file root directory')

    args = parser.parse_args()

    resources = iterate_resources(iterate_tfstate_files(args.root))
    if args.list:
        groups = build_groups(resources)
        print(json.dumps(groups, indent=2))

    parser.exit()


if __name__ == '__main__':
    main()