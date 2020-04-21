STACK_NAME?=dev1
KubeClusterName?=vdev-kube
S3Bucket?=vdev-k8
S3BucketPrefix?=functions
S3BucketModulesPrefix?=modules
AWS_DEFAULT_REGION?=eu-north-1
KafkaClusterName?=vdev-kafka
LensesLicense?=test
LambdaRole?=roleArn
LambdaFunctionName?=dev-LambdaEKSConfig-NNN
PROFILE?=default
PROJECT=lambdas

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
		--template-body file://lenses-eks.yml \
		--output text \
		--parameters \
			  ParameterKey=KubeClusterName,ParameterValue=$(KubeClusterName) \
			  ParameterKey=S3Bucket,ParameterValue=$(S3Bucket) \
			  ParameterKey=S3BucketPrefix,ParameterValue=$(S3BucketPrefix) \
			  ParameterKey=KafkaClusterName,ParameterValue=$(KafkaClusterName) \
			  ParameterKey=LensesLicense,ParameterValue=$(LensesLicense) \
			  ParameterKey=LambdaRole,ParameterValue=$(LambdaRole)


.PHONY: update_cloudformation
update_cloudformation: s3
	aws cloudformation update-stack \
		--profile $(PROFILE) \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--template-body file://lenses-eks.yml \
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
	@aws lambda update-function-code --function-name $(LambdaFunctionName) --zip-file fileb://lambdas.zip

mkvirtenv:
	@if [ ! -e venv ]; then \
			python3 -m virtualenv -p $(shell which python3) venv; \
			. venv/bin/activate ;\
			./venv/bin/pip3 install -U pytest flake8 awscli; \
			./venv/bin/pip3 install -Ur lambdas/requirements.txt; \
	fi

rmvirtenv:
	@if command -v deactivate; then \
			deactivate; \
	fi

	@rm -rf venv

virtenv: mkvirtenv
	@. venv/bin/activate ;
	@pip -V

pep8: virtenv
	@. venv/bin/activate ; flake8 lambdas/lambdas.py \
		lambdas/backend_config.py \
		lambdas/eks_config.py \
		lambdas/exac.py \
		lambdas/manifests.py \
		lambdas/setup_lenses.py \
		--count --select=E9,F63,F7,F82 --show-source --statistic
	@. venv/bin/activate ; flake8 lambdas/lambdas.py \
		lambdas/backend_config.py \
		lambdas/eks_config.py \
		lambdas/exac.py \
		lambdas/manifests.py \
		lambdas/setup_lenses.py \
	--count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

tests: virtenv
	@. venv/bin/activate ; python3 -m pytest ./tests/

