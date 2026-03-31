#!/bin/bash
export AWS_REGION=eu-west-2
export AWS_DEFAULT_REGION=eu-west-2
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

create_queue() {
  local QUEUE_NAME_TO_CREATE=$1
  local VISIBILITY_TIMEOUT=$2
  local DLQ_NAME="${QUEUE_NAME_TO_CREATE}-deadletter"

  awslocal --endpoint-url=${LOCALSTACK_ENDPOINT:-http://localhost:4566} sqs create-queue \
    --queue-name ${DLQ_NAME} \
    --region ${AWS_REGION} \
    --attributes VisibilityTimeout=60

  local DLQ_ARN=$(awslocal --endpoint-url=${LOCALSTACK_ENDPOINT:-http://localhost:4566} sqs get-queue-attributes \
    --queue-url http://sqs.${AWS_REGION}.${LOCALSTACK_HOST}.localstack.cloud:${PORT}/000000000000/${DLQ_NAME} \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)

  awslocal --endpoint-url=${LOCALSTACK_ENDPOINT:-http://localhost:4566} sqs create-queue \
    --queue-name ${QUEUE_NAME_TO_CREATE} \
    --region ${AWS_REGION} \
    --attributes '{
      "VisibilityTimeout": "'${VISIBILITY_TIMEOUT}'",
      "RedrivePolicy": "{\"deadLetterTargetArn\":\"'${DLQ_ARN}'\",\"maxReceiveCount\":\"1\"}"
    }'

  echo "Queue ${QUEUE_NAME_TO_CREATE} created successfully"
}

aws --endpoint-url=http://localhost:4566 s3 mb s3://ai-uc-content-swarm-context

create_queue "ai_content_swarm_invoke" 300
