.PHONY: vpn subnet firewall static-ip create-masters show-instances create-workers

PY=$(shell which python3)

PROJECT_NAME ?= "homemade"
REGION ?= "us-west1"
ZONE ?= "${REGION}-a"

NUM_OF_CONTROLLER = 1
NUM_OF_INITIAL_WORKER = 2

gcloud-setup:
	gcloud config set compute/zone ${ZONE}
	gcloud config set compute/region ${REGION}
	gcloud config set project $$(cat .project-id.txt)

vpc:
	gcloud compute networks create ${PROJECT_NAME} --subnet-mode custom

subnet:
	gcloud compute networks subnets create kubernetes \
		  --network ${PROJECT_NAME} \
		  --range 10.240.0.0/24

firewall:
	# external
	gcloud compute firewall-rules create ${PROJECT_NAME}-allow-external \
		  --allow tcp:22,tcp:6443,icmp \
		  --network ${PROJECT_NAME} \
	      --source-ranges 0.0.0.0/0
	# internal
	gcloud compute firewall-rules create ${PROJECT_NAME}-allow-internal \
		 --allow tcp,udp,icmp \
		 --network ${PROJECT_NAME} \
		 --source-ranges 10.240.0.0/24,10.200.0.0/16
	# show that it's created.
	gcloud compute firewall-rules list --filter="network:${PROJECT_NAME}" 

static-ip: 
	gcloud compute addresses create ${PROJECT_NAME} \
		  --region $$(gcloud config get-value compute/region)
	# verify if it's created.
	gcloud compute addresses list --filter="name=('${PROJECT_NAME}')"

create-controllers:
	# compute instances for kubernetes control plane.
	# doesn't support more than 10 instance as today.
	for i in $$(seq 0 ${NUM_OF_CONTROLLER}); do \
		gcloud compute instances create controller-$${i} \
		--async \
		--boot-disk-size 200GB \
		--can-ip-forward \
		--image-family ubuntu-1804-lts \
		--image-project ubuntu-os-cloud \
		--machine-type n1-standard-1 \
		--private-network-ip 10.240.0.1$${i} \
		--scopes compute-rw,storage-ro,service-management,service-control,logging-write,monitoring \
		--subnet kubernetes \
		--tags ${PROJECT_NAME},controller; \
	done

create-workers:
	for i in $$(seq 0 ${NUM_OF_INITIAL_WORKER}); do \
	  gcloud compute instances create worker-$${i} \
		--async \
		--boot-disk-size 200GB \
		--can-ip-forward \
		--image-family ubuntu-1804-lts \
		--image-project ubuntu-os-cloud \
		--machine-type n1-standard-1 \
		--metadata pod-cidr=10.200.$${i}.0/24 \
		--private-network-ip 10.240.0.2$${i} \
		--scopes compute-rw,storage-ro,service-management,service-control,logging-write,monitoring \
		--subnet kubernetes \
		--tags kubernetes-the-hard-way,worker; \
	done

# verify the instances
show-instances: 
	gcloud compute instances list

ca-generate:
	${PY} key_generate.py --command certificate-authority
	${PY} key_generate.py --command admin-client
	${PY} key_generate.py --command kubelet-client --pattern worker 
	# or $PY key_generate.py --command kubelet-client --instances worker-0 worker-1 ...
	${PY} key_generate.py --command controller-manager
	${PY} key_generate.py --command scheduler-client
	${PY} key_generate.py --command api-server
	${PY} key_generate.py --command service-acc-key-pair

distribute-cert-keys-worker:
	$(PY) key_generate.py --command distribute-cert-keys-workers --instances worker-0 worker-1
	worker-2


distribute-cert-keys-controller:
	$(PY) key_generate.py --command distribute-cert-keys-controllers --instances controller-0
	controller-1 controller-2
