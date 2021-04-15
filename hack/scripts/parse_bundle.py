#!/usr/bin/env python3

import os
import sys
import shutil
from ruamel import yaml

enable_webhooks = False

def main():
    cleanup()

    cert_dir = get_cert_directory()

    copy_other_dirs(cert_dir)

    parse_certification_bundle()

    setup_dockerfile()

def cleanup():
    if os.path.isfile('certification.Dockerfile'):
        os.remove('certification.Dockerfile')

    if os.path.isdir('certification'):
        shutil.rmtree('certification')

def setup_dockerfile():
    with open('bundle.Dockerfile', 'r') as input:
        contents = input.readlines()
        input.close()

    with open('bundle/patches/labels', 'r') as labels_file:
        cert_labels = labels_file.readlines()
        labels_file.close()

        for label in cert_labels:
            if 'LABEL' in label:
                contents.insert(2, label)

    for line in contents:
        with open('certification.Dockerfile', 'a') as output:
            if 'COPY' in line:
                line = line.replace('bundle', 'certification')
            output.write(line)
            output.close()

def get_cert_directory():
    cert_dir = os.path.join(os.getcwd(), "certification")
    if not os.path.isdir(cert_dir):
      os.mkdir(cert_dir)

    manifests_dir = os.path.join(cert_dir, "manifests")
    if not os.path.isdir(manifests_dir):
        os.mkdir(manifests_dir)

    return cert_dir

def parse_certification_bundle():
    docs = yaml.round_trip_load_all(sys.stdin, preserve_quotes=True)

    for doc in docs:
        if doc["kind"] == "Service":
            parse_service(doc)

        if doc["kind"] == "CustomResourceDefinition":
            parse_crd(doc)

        if doc["kind"] == "Role" or doc["kind"] == "ClusterRole":
            parse_role(doc)

        if doc["kind"] == "RoleBinding" or doc["kind"] == "ClusterRoleBinding":
            parse_rolebinding(doc)

        if doc["kind"] == "ServiceAccount":
            parse_serviceaccount(doc)

        if doc["kind"] == "ClusterServiceVersion":
            parse_csv(doc)

def project_name():
    project = ''
    with open('PROJECT', 'r') as f:
        for line in f:
            if "projectName" in line:
                project = line.split(' ')[1]

    return project.strip()

def parse_serviceaccount(document):
    base_name = '_'.join([document["metadata"]["name"], document["apiVersion"], document["kind"]])
    name = '.'.join([base_name.lower(), "yaml"])
    copy_file(name)

def parse_csv(document):
    project = project_name()
    name = '.'.join([project, document["kind"], "yaml"]).lower()

    document["metadata"]["annotations"]["certified"] = "true"

    version = document["spec"]["version"]
    container_image = document["metadata"]["annotations"]["containerImage"]
    document["metadata"]["annotations"]["containerImage"] = container_image.replace("0.0.1", version)

    for deployment in document["spec"]["install"]["spec"]["deployments"]:
        for container in deployment["spec"]["template"]["spec"]["containers"]:
            if container["name"] == "kube-rbac-proxy":
                container["image"] = get_rbac_proxy_image()

            if container["name"] == "manager" and enable_webhooks == False:
                container["env"].append({'name':'ENABLE_WEBHOOKS','value':'false'})
                print(container["env"])

    try:
        if document["spec"]["webhookdefinitions"] and enable_webhooks == False:
            del document["spec"]["webhookdefinitions"]
    except KeyError:
        pass

    write_manifest(name, document)

def parse_rolebinding(document):
    group_version = document["apiVersion"].replace('/','_')
    base_name = '_'.join([document["metadata"]["name"], group_version, document["kind"]])
    name = '.'.join([base_name.lower(), "yaml"])

    for subject in document["subjects"]:
        del subject["namespace"]

    write_manifest(name, document)

def parse_role(document):
    group_version = document["apiVersion"].replace('/','_')
    base_name = '_'.join([document["metadata"]["name"], group_version, document["kind"]])
    name = '.'.join([base_name.lower(), "yaml"])
    copy_file(name)

def parse_service(document):
    base_name = '_'.join([document["metadata"]["name"], document["apiVersion"], document["kind"]])
    name = '.'.join([base_name.lower(), "yaml"])
    copy_file(name)

def parse_crd(document):
    base_name = '_'.join([document["spec"]["group"], document["spec"]["names"]["plural"]])
    name = '.'.join([base_name.lower(), "yaml"])
    copy_file(name)


def copy_file(filename):
    cert_manifests_dir = os.path.join(get_cert_directory(), "manifests")
    bundle_manifests_dir = os.path.join("bundle", "manifests")

    shutil.copy(os.path.join(bundle_manifests_dir, filename), cert_manifests_dir)

def write_manifest(name, document):
    cert_dir = get_cert_directory()

    try:
        del document["metadata"]["creationTimestamp"]
    except KeyError:
        pass

    filename = os.path.join(cert_dir, "manifests", name)
    with open(filename, 'w') as f:
        yaml.dump(document, f, Dumper=yaml.RoundTripDumper, default_flow_style=False)

def copy_other_dirs(cert_dir):
    dirs = ["tests", "metadata"]
    for target_dir in dirs:
        src = os.path.join("bundle", target_dir)
        dst = os.path.join(cert_dir, target_dir)

        shutil.copytree(src, dst)

def get_rbac_proxy_image():
    related_images = 'bundle/patches/related_images.yaml'
    if os.path.exists(related_images):
    	with open(related_images, 'r') as stream:
    		patch_file = yaml.safe_load(stream)

    	for image in patch_file["spec"]["relatedImages"]:
    		if image["name"] == "kube-rbac-proxy":
    			return image["image"]

if __name__ == '__main__':
    main()
