import argparse
from copy import deepcopy
import tempfile
import logging
from logging.config import dictConfig
import subprocess
from pathlib import Path
import json

logging_config = dict(
    version=1,
    formatters={"f": {"format": "%(asctime)s %(name)-4s [%(levelname)s] %(message)s"}},
    handlers={"h": {"class": "logging.StreamHandler", "formatter": "f", "level": logging.DEBUG}},
    root={"handlers": ["h"], "level": logging.DEBUG},
)

dictConfig(logging_config)

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
GCLOUD = "gcloud"


def _run_command(command, log=True):
    if log:
        logging.info(f"Command to run: '{command}'")
    ps = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    return ps.communicate()[0].decode("utf8").splitlines()


def generate_certificate_authority(args):
    command = f"cfssl gencert -initca ca-csr.json | cfssljson -bare ca"
    _run_command(command)


def generate_admin_client_cert(args):
    command = (
        f"cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json "
        f"-profile=kubernetes admin-csr.json | cfssljson -bare admin"
    )
    _run_command(command)


def generate_kubelet_client_cert(args):
    instances = args.instances
    if instances is None:
        if args.pattern is None:
            raise ValueError()

        command = (
            f"{GCLOUD} compute instances list | grep {args.pattern} | grep RUNNING | "
            f"awk '{{print $1}}'"
        )
        instances = _run_command(command)

    logger.info(instances)

    template = json.load(open("instance-csr.json"))

    for instance in instances:
        with tempfile.NamedTemporaryFile("w") as instance_template:
            current_template = deepcopy(template)
            current_template["CN"] = f"system:node:{instance}"
            print(json.dumps(current_template), file=instance_template, flush=True)
            external_ip = _run_command(
                f"{GCLOUD} compute instances describe {instance} "
                "--format 'value(networkInterfaces[0].accessConfigs[0].natIP)'"
            )[0]
            internal_ip = _run_command(
                f"{GCLOUD} compute instances describe {instance} "
                f"--format 'value(networkInterfaces[0].networkIP)'"
            )[0]
            _run_command(
                "cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json "
                f"-hostname={instance},{external_ip},{internal_ip} -profile=kubernetes "
                f"{instance_template.name} | cfssljson -bare {instance}"
            )

        print(instances, external_ip, internal_ip)


def generate_controller_manager_client_cert(args):
    _run_command(
        """cfssl gencert \
              -ca=ca.pem \
              -ca-key=ca-key.pem \
              -config=ca-config.json \
              -profile=kubernetes \
              kube-controller-manager-csr.json | cfssljson -bare kube-controller-manager"""
    )


def generate_proxy_client_cert(args):
    _run_command(
        """cfssl gencert \
              -ca=ca.pem \
              -ca-key=ca-key.pem \
              -config=ca-config.json \
              -profile=kubernetes \
              kube-proxy-csr.json | cfssljson -bare kube-proxy """
    )


def generate_scheduler_client_cert(args):
    _run_command(
        """cfssl gencert \
              -ca=ca.pem \
              -ca-key=ca-key.pem \
              -config=ca-config.json \
              -profile=kubernetes \
              kube-scheduler-csr.json | cfssljson -bare kube-scheduler"""
    )


def generate_k8s_api_server_cert(args):
    kubernetes_public_address = _run_command(
        "gcloud compute addresses describe kubernetes-the-hard-way "
        "--region $(gcloud config get-value compute/region) "
        "--format 'value(address)'"
    )

    k8s_hostnames = (
        "kubernetes,kubernetes.default,kubernetes.default.svc,"
        "kubernetes.default.svc.cluster,kubernetes.svc.cluster.local"
    )

    _run_command(
        f"""cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -hostname=10.32.0.1,10.240.0.10,10.240.0.11,10.240.0.12,{kubernetes_public_address[0]},127.0.0.1,{k8s_hostnames} -profile=kubernetes kubernetes-csr.json | cfssljson -bare kubernetes"""
    )


def generate_service_acc_key_pair(args):
    _run_command(
        """cfssl gencert \
              -ca=ca.pem \
              -ca-key=ca-key.pem \
              -config=ca-config.json \
              -profile=kubernetes \
              service-account-csr.json | cfssljson -bare service-account"""
    )


def distribute_cert_and_private_keys_for_workers(args):
    instances = args.instances
    for instance in instances:
        _run_command(f"gcloud compute scp ca.pem {instance}-key.pem {instance}.pem {instance}:~/")


def distribute_cert_and_private_keys_for_controllers(args):
    cert_and_keys = (
        "ca.pem ca-key.pem kubernetes-key.pem kubernetes.pem service-account-key.pem "
        "service-account.pem"
    )
    instances = args.instances
    for instance in instances:
        _run_command(f"gcloud compute scp {cert_and_keys} {instance}:~/")


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
        "distribute-cert-keys-workers": distribute_cert_and_private_keys_for_workers,
        "distribute-cert-keys-controllers": distribute_cert_and_private_keys_for_controllers,
    }
    parser = argparse.ArgumentParser(description="CA Stuff")
    parser.add_argument(
        "--command", type=str, required=True, choices=set(command_func_mapper.keys())
    )
    parser.add_argument("--instances", default=None, type=str, nargs="+")
    parser.add_argument("--pattern", default=None, type=str)

    args = parser.parse_args()
    func = command_func_mapper[args.command]
    import os

    os.chdir("templates/")
    func(args)


if __name__ == "__main__":
    run()
