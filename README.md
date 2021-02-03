# Cert Bundle Builder

## What this script does:
1. Ensure the operator is marked as certified
2. Remove service accounts in any side loaded role bindings or cluster role bindings.
3. Ensure the certification docker file has the required certification annotations

## How to setup

1. Copy the `parse_bundle.py` and `requirements.txt` script to hack/scripts

2. Add the the following `Makefile` targets

```
install-hack-dependencies:
        pip3 install -r hack/scripts/requirements.txt

certification-bundle: install-hack-dependencies
        $(KUSTOMIZE) build bundle | hack/scripts/parse_bundle.py
```


3. Assuming you already have a bundle directory. Create the `bundle/patches` directory

4. Create the file, labels in new created bundle/patches directory. It should look as shown below:
```
$ cat bundle/patches/labels
LABEL com.redhat.openshift.versions="v4.5,v4.6"
LABEL com.redhat.delivery.operator.bundle=true
LABEL com.redhat.delivery.backport=true
```
5. Create a kustomization.yaml file in the bundle directory

```
$ cd bundle
$ kustomize create --resources manifests/*
```

6. Add `related_images.yaml` inside the `bundle/patches` directory to support offline installs. See example below:

```
apiVersion: operators.coreos.com/v1alpha1
kind: ClusterServiceVersion
metadata:
  name: myoperator-operator:v0.1.1
spec:
  relatedImages:
  - name: container1
    image: registry.connect.redhat.com/<namespace>/container1@sha256:f57849226732751479033e67aa5517662ccb60e982084110650d15b4f7d21cfh
  - name:container2
    image: registry.connect.redhat.com/<namespace>/container2@sha256:0a6aehfedd84de751bbbcefea69170fadd269d9caaaa58d97b45dcd060ef44c31
  - name: kube-rbac-proxy
    image: registry.redhat.io/openshift4/ose-kube-rbac-proxy@sha256:<IMAGE_DIGEST>
```

7. Append to your `bundle/kustomization.yaml` file any patches file you created with the exception of the labels file.
Example:

```
patches:
  - path: patches/related_images.yaml
    target:
      kind: ClusterServiceVersion
```

**Note**:
- Be sure to set `enable_webhooks` to True in the parse_bundle.py script if you intend to deploy an operator with webhooks.
