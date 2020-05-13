import argparse
import os
import json
import logging
import tempfile
from copy import deepcopy

from utils import configure_logger, GCLOUD, run_command, template_dir

configure_logger()
logger = logging.getLogger(__name__)


def generate_certificate_authority(**kwargs):
    command = f"cfssl gencert -initca ca-csr.json | cfssljson -bare ca"
    run_command(command)


def _create_certificate(resource):
    command = f"""cfssl gencert \
                  -ca=ca.pem \
                  -ca-key=ca-key.pem \
                  -config=ca-config.json \
                  -profile=kubernetes \
                  {resource}-csr.json | cfssljson -bare {resource}"""
    return run_command(command)


def generate_admin_client_cert(**kwargs):
    command = (
        f"cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json "
        f"-profile=kubernetes admin-csr.json | cfssljson -bare admin"
    )
    run_command(command)


def generate_kubelet_client_cert(**kwargs):
    instances = kwargs["instances"]
    if instances is None:
        if kwargs["pattern"] is None:
            raise ValueError()

        command = (
            f"{GCLOUD} compute instances list | grep {kwargs['pattern']} | grep RUNNING | "
            f"awk '{{print $1}}'"
        )
        instances = run_command(command)

    logger.info(instances)

    template = json.load(open("instance-csr.json"))

    for instance in instances:
        with tempfile.NamedTemporaryFile("w") as instance_template:
            current_template = deepcopy(template)
            current_template["CN"] = f"system:node:{instance}"
            print(json.dumps(current_template), file=instance_template, flush=True)
            external_ip = run_command(
                f"{GCLOUD} compute instances describe {instance} "
                "--format 'value(networkInterfaces[0].accessConfigs[0].natIP)'"
            )[0]
            internal_ip = run_command(
                f"{GCLOUD} compute instances describe {instance} "
                f"--format 'value(networkInterfaces[0].networkIP)'"
            )[0]
            run_command(
                "cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json "
                f"-hostname={instance},{external_ip},{internal_ip} -profile=kubernetes "
                f"{instance_template.name} | cfssljson -bare {instance}"
            )

        print(instances, external_ip, internal_ip)


def generate_controller_manager_client_cert(**kwargs):
    _create_certificate("kube-controller-manager")


def generate_proxy_client_cert(**kwargs):
    _create_certificate("kube-proxy")


def generate_scheduler_client_cert(**kwargs):
    _create_certificate("kube-scheduler")


def generate_k8s_api_server_cert(**kwargs):
    kubernetes_public_address = run_command(
        "gcloud compute addresses describe kubernetes-the-hard-way "
        "--region $(gcloud config get-value compute/region) "
        "--format 'value(address)'"
    )

    k8s_hostnames = (
        "kubernetes,kubernetes.default,kubernetes.default.svc,"
        "kubernetes.default.svc.cluster,kubernetes.svc.cluster.local"
    )

    run_command(
        f"cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json "
        f"-hostname=10.32.0.1,10.240.0.10,10.240.0.11,10.240.0.12,{kubernetes_public_address[0]},"
        f"127.0.0.1,{k8s_hostnames} -profile=kubernetes kubernetes-csr.json "
        f"| cfssljson -bare kubernetes"
    )


def generate_service_acc_key_pair(**kwargs):
    _create_certificate("service-account")


def distribute_cert_and_keys(**kwargs):
    node_type = kwargs.get("node_type", None)
    if node_type is None:
        raise ValueError("Please provide `node_type`: worker | controller")

    if node_type == "worker":
        _distribute_cert_and_keys_for_workers(**kwargs)
    elif node_type == "controller":
        _distribute_cert_and_keys_for_controllers(**kwargs)


def _distribute_cert_and_keys_for_workers(**kwargs):
    instances = kwargs["instances"]
    for instance in instances:
        run_command(f"gcloud compute scp ca.pem {instance}-key.pem {instance}.pem {instance}:~/")


def _distribute_cert_and_keys_for_controllers(**kwargs):
    cert_and_keys = (
        "ca.pem ca-key.pem kubernetes-key.pem kubernetes.pem service-account-key.pem "
        "service-account.pem"
    )
    instances = kwargs["instances"]
    for instance in instances:
        run_command(f"gcloud compute scp {cert_and_keys} {instance}:~/")


def run():
    command_func_mapper = {
        "certificate-authority": generate_certificate_authority,
        "admin-client": generate_admin_client_cert,
        "kubelet-client": generate_kubelet_client_cert,
        "controller-manager": generate_controller_manager_client_cert,
        "proxy-client": generate_proxy_client_cert,
        "scheduler-client": generate_scheduler_client_cert,
        "api-server": generate_k8s_api_server_cert,
        "service-acc-key-pair": generate_service_acc_key_pair,
        "distribute-cert-keys": distribute_cert_and_keys,
    }
    parser = argparse.ArgumentParser(description="CA Stuff")
    parser.add_argument(
        "--command", type=str, required=True, choices=set(command_func_mapper.keys())
    )
    parser.add_argument("--instances", default=None, type=str, nargs="+")
    parser.add_argument("--pattern", default=None, type=str)
    parser.add_argument("--node-type", default=None, type=str)

    args = parser.parse_args().__dict__
    command = args.pop("command")
    func = command_func_mapper[command]

    with template_dir():
        func(**args)


if __name__ == "__main__":
    run()
