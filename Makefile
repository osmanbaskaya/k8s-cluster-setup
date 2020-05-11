.PHONY: vpn subnet firewall static-ip create-masters show-instances create-workers

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
	# show that it's created.
	gcloud compute firewall-rules list --filter="network:kubernetes-the-hard-way" 

static-ip: 
	gcloud compute addresses create kubernetes-the-hard-way \
		  --region $$(gcloud config get-value compute/region)
	# verify if it's created.
	gcloud compute addresses list --filter="name=('kubernetes-the-hard-way')"

create-masters:
	# 3 compute instances for kubernetes control plane.
	for i in 0 1 2; do
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
		--tags kubernetes-the-hard-way,controller
	done

create-workers:
	for i in 0 1 2; do
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
		--tags kubernetes-the-hard-way,worker
	done
	gcloud compute instances list > $@

# verify the instances
show-instances: 
	gcloud compute instances list

ca-generate:
	python key_generate.py --command certificate-authority 
	python key_generate.py --command admin-client
	python key_generate.py --command kubelet-client --pattern worker 
	# or python key_generate.py --command kubelet-client --instances worker-0 worker-1 ...
	python key_generate.py --command controller-manager
	python key_generate.py --command scheduler-client
	python key_generate.py --command api-server
	python key_generate.py --command service-acc-key-pair

distribute-cert-keys-worker:
	python key_generate.py --command distribute-cert-keys-workers --instances worker-0 worker-1 worker-2


distribute-cert-keys-controller:
	python key_generate.py --command distribute-cert-keys-controllers --instances controller-0 controller-1 controller-2  
