.PHONY: vpn subnet firewall static-ip create-masters show-instances create-workers

PY=$(shell which python3)

vpc:
	gcloud compute networks create kubernetes-the-hard-way --subnet-mode custom

subnet:
	gcloud compute networks subnets create kubernetes \
		  --network kubernetes-the-hard-way \
		  --range 10.240.0.0/24

firewall:
	gcloud compute firewall-rules create kubernetes-the-hard-way-allow-external \
		  --allow tcp:22,tcp:6443,icmp \
		  --network kubernetes-the-hard-way \
	      --source-ranges 0.0.0.0/0
	# internal
	gcloud compute firewall-rules create kubernetes-the-hard-way-allow-internal \
		 --allow tcp,udp,icmp \
		 --network kubernetes-the-hard-way \
		 --source-ranges 10.240.0.0/24,10.200.0.0/16
	# show that it's created.
	gcloud compute firewall-rules list --filter="network:kubernetes-the-hard-way" 

static-ip: 
	gcloud compute addresses create kubernetes-the-hard-way \
		  --region $$(gcloud config get-value compute/region)
	# verify if it's created.
	gcloud compute addresses list --filter="name=('kubernetes-the-hard-way')"

create-controllers:
	# 3 compute instances for kubernetes control plane.
	for i in 0 1 2; do \
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
		--tags kubernetes-the-hard-way,controller; \
	done

create-workers:
	for i in 0 1 2; do \
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
	gcloud compute instances list > $@

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
