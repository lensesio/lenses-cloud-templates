STACK_NAME?=dev1
KubeClusterName?=vdev-kube
S3Bucket?=vdev-k8
S3BucketPrefix?=functions
S3BucketModulesPrefix?=modules
AWS_DEFAULT_REGION?=eu-north-1
KafkaClusterName?=vdev-kafka-cluster
LensesLicense?=test
PROFILE?=default

.PHONY: inst_deps
inst_deps:
	@cd lambdas; rm -rf modules; mkdir -vp modules
	@cd lambdas; pip install -r requirements.txt -t ./modules

# Function to create a pipeline - can't be automated
.PHONY: cloudformation
cloudformation: s3
	#-@unset AWS_DEFAULT_REGION;
	aws cloudformation create-stack \
		--profile $(PROFILE) \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--template-body file://lenses.yml \
		--output text \
		--parameters \
			  ParameterKey=KubeClusterName,ParameterValue=$(KubeClusterName) \
			  ParameterKey=S3Bucket,ParameterValue=$(S3Bucket) \
			  ParameterKey=S3BucketPrefix,ParameterValue=$(S3BucketPrefix) \
			  ParameterKey=KafkaClusterName,ParameterValue=$(KafkaClusterName) \
			  ParameterKey=LensesLicense,ParameterValue=$(LensesLicense)


# Function to update a pipeline after its been created - can't be automated
.PHONY: update_cloudformation
update_cloudformation: s3
	aws cloudformation update-stack \
		--profile $(PROFILE) \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--template-body file://lenses.yml \
		--parameters \
			  ParameterKey=KubeClusterName,ParameterValue=$(KubeClusterName) \
			  ParameterKey=S3Bucket,ParameterValue=$(S3Bucket) \
			  ParameterKey=S3BucketPrefix,ParameterValue=$(S3BucketPrefix) \
			  ParameterKey=KafkaClusterName,ParameterValue=$(KafkaClusterName) \
			  ParameterKey=LensesLicense,ParameterValue=$(LensesLicense)


.PHONY: zip
zip:
	@-rm -f *.zip
	@cd lambdas; \
	zip -r ../lambdas . -x '*__pycache__*' -x 'test.py' > /dev/null

.PHONY: s3
s3: zip
	@aws s3 \
	--profile $(PROFILE) \
	cp lambdas.zip s3://$(S3Bucket)/$(S3BucketPrefix)/lambdas.zip

.PHONY: update_lambda
update_lambda: zip
	@aws lambda update-function-code --function-name dev02-LambdaEKSConfig-71W0VBC8NIVD --zip-file fileb://lambdas.zip

mkvirtenv:
	@if [ ! -e venv ]; then \
			python3 -m virtualenv -p $(shell which python3) venv; \
			. venv/bin/activate ;\
			./venv/bin/pip3 install -Ur requirements-dev.txt ; \
	fi

rmvirtenv:
	@if command -v deactivate; then \
			deactivate; \
	fi

	@rm -rf venv

virtenv: mkvirtenv
	@. venv/bin/activate ;
	@pip -V
