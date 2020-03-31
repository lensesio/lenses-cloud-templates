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


.PHONY: cloudformation
cloudformation: s3
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
	@aws lambda update-function-code --function-name dev-LambdaEKSConfig-NNN --zip-file fileb://lambdas.zip

