## Certificate Authority & Private/Public Keys

### Certificate Authority

- Its own CSR (Certificate Signature request): https://github.com/cloudflare/cfssl/wiki/Creating-a-new-CSR
- Certificate authority config file.
- CA certificate
- CA private key

### Kubernetes

#### Client & Server Certificates

Certificate and private key will be created for each of the following by using CSR, CA config, CA certificate, CA private key.

- Controller Manager Client Certificate
- Kube-Proxy Client
- Admin Client Certificate
- Kubernetes API Server Certificate
- Scheduler Client Certificate
- Kubernetes API Server Certificate
- Service Account Certificate (will be used by controller to generate and sign service account tokens)
- Kubelet Client Certificate (for each worker): Each worker node needs to have this. CSR is specific for each worker (ie, `CN` part of the CSR)

### Distribution

#### Workers

- CA Certificate.
- Worker's certificate
- Worker's key

#### Controllers

- CA certificate
- CA key
- API Server certificate & key
- Service account certificate & key

## Kubernetes Configuration Files (Kubeconfigs)

### Kubelet

- Server Public IP (LB fronting API Server)
- CA
- Kubelet Client Certificate and key (each node has own client certificate created previously)

### Kube-proxy
- Server Public IP (LB fronting API Server)
- CA
- Kube-proxy certificate and key


### Kube Controller-manager
- Server Public IP (LB fronting API Server)
- CA
- Kube Controller Manager certificate and key

### Kube-Scheduler
- Server Public IP (LB fronting API Server)
- CA
- Kube-proxy certificate and key

### Admin user

- Server Public IP (LB fronting API Server)
- CA
- Admin certificate and key

### Distribution

#### Workers
- Kubelet kubconfig
- Kube-Proxy kubconfig

#### Controller
- Controller Manager kubeconfig
- kube scheduler kubeconfig
- admin kubeconfig.

## Data Encryption for Secrets and Cluster data

- Create an encryption key
- Create an encryption config
- send the config to each controller instance
