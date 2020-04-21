#!/usr/bin/env python3

# KubeConfig Manifest
kubeconfig = """apiVersion: v1
clusters:
- cluster:
    server: {endpoint}
    certificate-authority-data: {ca_data}
  name: aws
contexts:
- context:
    cluster: aws
    user: aws
  name: aws
current-context: aws
kind: Config
preferences: {{}}
users:
- name: aws
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1alpha1
      command: /tmp/awsiam/aws-iam-authenticator
      args:
        - "token"
        - "-i"
        - "{cluster_name}"
"""

# Kube Lenses Pod Manifest
lenses_deployment_manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {lenses}
spec:
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: {lenses}
  replicas: 1
  template:
    metadata:
      labels:
        app: {lenses}
    spec:
      containers:
      - name: {lenses}
        image:  lensesio/lenses:{lv}
        imagePullPolicy:  IfNotPresent
        lifecycle:
          postStart:
            exec:
              command: [
                  "/bin/bash",
                  "-c",
                  "cp /mnt/secret/license.json \
                  /run/license.json; \
                  chmod 0777 /run/license.json"
                ]
        ports:
          - containerPort: 9991
        env:
            - name: LENSES_SQL_EXECUTION_MODE
              value: "IN_PROC"
            - name: LENSES_PORT
              value: "9991"
            - name: LENSES_JMX_PORT
              value: "9586"
            - name: LENSES_BOX
              value: "true"
            - name: LENSES_HEAP_OPTS
              value: "-Xmx1024M -Xmx320M"
            - name: LENSES_LICENSE_FILE
              value: /run/license.json
        resources:
          requests:
            memory: "1.0Gi"
          limits:
            memory: "1.8Gi"
        volumeMounts:
          - name: license-secret
            mountPath: /mnt/secret
      volumes:
        - name: license-secret
          secret:
            secretName: lenses-license
"""

# Kube Lenses Service Manifest
lenses_service_manifest = """
apiVersion: v1
kind: Service
metadata:
  name: "{lenses}-service"
spec:
  selector:
    app: {lenses}
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9991
"""
