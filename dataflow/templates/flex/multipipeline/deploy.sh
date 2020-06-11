########################################
# Construct a docker file
# Build Docker Image
# Build flex template
########################################

set -e

# variables
PROJECT="<Project-id>"
BUCKETNAME="<bucket-name>"

#Values to build the docker image
IMAGENAME="csoml/dataflow/${1}"
TAGNAME="latest"
TEMPLATE_IMAGE="gcr.io/$PROJECT/${IMAGENAME}:${TAGNAME}"

#Values to build the flex template
TEMPLATE_PATH="gs://${BUCKETNAME}/templates/flex/specs/${1}.json"
METADATA_FILE="./deps/${1}_metadata.json"

function build_dockerfile() {
  local pipeline_name=$1
  echo "Building Dockerfile for pipeline: ${pipeline_name}"
  rm -f Dockerfile || exit 0

  #Write base docker file
  cat BaseDockerfile > Dockerfile

  #Add pipeline specific config
  cat << EOF >> Dockerfile

COPY deps/${pipeline_name}_requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy source files
COPY setup.py .
COPY ${pipeline_name}.py ./main.py
COPY fake_messages ./fake_messages
EOF
}

#source builddocker.sh

# Alternate way of building  Docker file
#function build_dockerfile() {
#  local pipeline_name=$1
#  rm -f Dockerfile || exit 0
#  $1
#}

# Build Docker image using google cloud Build
function build_dockerimage() {
  echo "Building Docker image.."
  # (Optional) Enable to use Kaniko cache by default.
  gcloud config set builds/use_kaniko True

  # Build the image into Container Registry, this is roughly equivalent to:
  # gcloud auth configure-docker
  # docker image build -t $TEMPLATE_IMAGE .
  # docker push $TEMPLATE_IMAGE
  gcloud --project $PROJECT builds submit --tag "$TEMPLATE_IMAGE" .

}

# Build the Flex Template
function build_flextemplate() {
  gcloud --project $PROJECT beta dataflow flex-template build "${TEMPLATE_PATH}" \
  --image "${TEMPLATE_IMAGE}" \
  --sdk-language "PYTHON" \
  --metadata-file "${METADATA_FILE}"
}

function main() {
    build_dockerfile $1
    build_dockerimage
    build_flextemplate
}

usage() {
  echo "Usage: $0 <pipeline name>"
}


if [ $# != 1 ]; then
  echo "Invalid number of arguments!"
  usage
  exit 1
fi

main "$@"


