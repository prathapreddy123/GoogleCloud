###### Build a Docker Image using google cloud Build ######
PROJECT="Project-id"
REGION="us-central1"
BUCKETNAME="<bucket-name>"

#Values to build the docker image
IMAGENAME="dataflow/fakemessages"
TAGNAME="latest"
TEMPLATE_IMAGE="gcr.io/$PROJECT/${IMAGENAME}:${TAGNAME}"

#Values to build the flex template
TEMPLATE_PATH="gs://${BUCKETNAME}/templates/flex/specs/fakemessages.json"
METADATA_FILE="pipelinemetadata.json"

#Run time parameter values
JOB_NAME="fakemessages"
STAGING_LOCATION="gs://${BUCKETNAME}/staging/"
MESSAGE_COUNT=13
OUTPUT_PATH="gs://${BUCKETNAME}/output/fake_messages/sample"

###### Enable required services  ######
gcloud services enable \
cloudscheduler.googleapis.com \
containerregistry.googleapis.com \
cloudbuild.googleapis.com

###### Build a Docker Image using google cloud Build ######

# (Optional) Enable to use Kaniko cache by default.
gcloud config set builds/use_kaniko True

# Build the image into Container Registry, this is roughly equivalent to:
#   gcloud auth configure-docker
#   docker image build -t $TEMPLATE_IMAGE .
#   docker push $TEMPLATE_IMAGE
gcloud builds submit --tag "$TEMPLATE_IMAGE" .

#gcloud builds submit --config fkcloudbuild.yaml .

###### Build the Flex Template ######
gcloud beta dataflow flex-template build "${TEMPLATE_PATH}" \
  --image "${TEMPLATE_IMAGE}" \
  --sdk-language "PYTHON" \
  --metadata-file "${METADATA_FILE}"


###### Run the Flex Template ######
#Using gcloud
gcloud beta dataflow flex-template run "${JOB_NAME}-`date +%Y%m%d-%H%M%S`" \
  --region $REGION --project ${PROJECT} \
  --template-file-gcs-location "$TEMPLATE_PATH" \
  --parameters "staging_location=${STAGING_LOCATION},message-count=${MESSAGE_COUNT},output-path=${OUTPUT_PATH}"


#Using REST API end point
curl -X POST \
  "https://dataflow.googleapis.com/v1b3/projects/${PROJECT}/locations/${REGION}/flexTemplates:launch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -d '{
    "launch_parameter": {
      "jobName": "'${JOB_NAME}-`date +%Y%m%d-%H%M%S`'",
      "parameters": {
        "staging_location": "'${STAGING_LOCATION}'",
        "message-count": "'${MESSAGE_COUNT}'",
        "output-path": "'${OUTPUT_PATH}'"
      },
      "containerSpecGcsPath": "'${TEMPLATE_PATH}'"
    }
  }'


#Using cloud scheduler
gcloud scheduler jobs create http dataflow-fakemessages --schedule "*/10 * * * *" \
 --uri="https://dataflow.googleapis.com/v1b3/projects/${PROJECT}/locations/${REGION}/flexTemplates:launch" \
 --http-method=POST \
 --headers="Authorization=Bearer $(gcloud auth application-default print-access-token),Content-Type= application/json" \
 --message-body='{
        "launch_parameter": {
                "jobName": "'${JOB_NAME}'",
                "parameters": {
                    "staging_location": "'${STAGING_LOCATION}'",
                    "message-count": "'${MESSAGE_COUNT}'",
                    "output-path": "'${OUTPUT_PATH}'"
                },
                "containerSpecGcsPath": "'${TEMPLATE_PATH}'"
          }
    }'


: '
Supported run time parameters without need to add to metadata.json file:

"staging_location", "temp_location", "num_workers", "max_num_workers", "labels", "machine_type", "zone",
"service_account_email", "experiments", "network", "subnetwork","no_use_public_ips"(true|false) "enable_streaming_engine"(true|false)
'
