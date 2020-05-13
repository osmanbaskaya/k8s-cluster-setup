from utils import GCLOUD, run_command, template_dir
from key_generate import generate_kubelet_client_cert, distribute_cert_and_keys


def _get_available_private_network_ip():
    pass


def _get_default_template(node_type, tags, subnet):
    # Check empty ips. --private-network-ip doesn't work well.
    templates = {
        "worker": (
            "--async "
            "--boot-disk-size 200GB "
            "--can-ip-forward "
            "--image-family ubuntu-1804-lts "
            "--image-project ubuntu-os-cloud "
            "--machine-type n1-standard-1 "
            "--scopes compute-rw,storage-ro,service-management,service-control,logging-write, "
            f"monitoring --subnet {subnet} --tags {tags}"
        ),
        "controller": (
            "--async "
            "--boot-disk-size 200GB "
            "--can-ip-forward "
            "--image-family ubuntu-1804-lts "
            "--image-project ubuntu-os-cloud "
            "--machine-type n1-standard-1 "
            "--scopes compute-rw,storage-ro,service-management,service-control,logging-write, "
            f"monitoring --subnet {subnet} --tags {tags}"
        ),
    }
    return templates[node_type]


def create_node(node_id, config):
    run_command(f"gcloud compute instances create {node_id} {config}")


def _bootstrap_worker_node(node_id, config):
    create_node(node_id, config)


def bootstrap_node(nodes, config, force_create=False):
    for node_id in nodes:
        node_type, _ = node_id.split("-")
        last_node = get_last_worker_node(pattern=node_type)
        last_node_ip = last_node.split()
        _bootstrap_worker_node(node_id, config)
        kwargs = {"instances": [node_type], "node_type": node_type, "force_create": force_create}
        if node_type == "worker":
            with template_dir():
                generate_kubelet_client_cert(**kwargs)
                distribute_cert_and_keys(**kwargs)
                # kubelet kubeconfig
                # kube-proxy
        elif node_type == "controller":
            distribute_cert_and_keys(**kwargs)
            # Controller Manager kubeconfig
            # kube scheduler kubeconfig
            # admin kubeconfig.


def get_last_worker_node(pattern):
    nodes = get_nodes(pattern)
    print(nodes)
    return nodes


def get_nodes(pattern):
    command = f"{GCLOUD} compute instances list | grep {pattern}"
    return run_command(command)


def run():
    import argparse

    command_func_mapper = {"bootstrap-node": bootstrap_node}

    parser = argparse.ArgumentParser(description="Instance Stuff")
    parser.add_argument(
        "--command", type=str, required=True, choices=set(command_func_mapper.keys())
    )
    parser.add_argument("--nodes", default=None, type=str, nargs="+")
    parser.add_argument("--config", default=None, type=str, nargs="+")

    args = parser.parse_args().__dict__
    command = args.pop("command")
    func = command_func_mapper[command]
    func(**args)


if __name__ == "__main__":
    run()
