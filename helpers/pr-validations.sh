set -ex

: '
When raised PR 17 from mkv/feature branch to merge on to master of
prathapreddy123/GoogleCloud repo below are values:

PROJECT_ID=prathap-poc
COMMIT_SHA=73434e300319db035d61783f6a2367a015992fee
SHORT_SHA=73434e3
REPO_NAME=GoogleCloud
BRANCH_NAME=feature
HEAD_BRANCH=feature
BASE_BRANCH=master
HEAD_REPO_URL=https://github.com/monikaduv/GoogleCloud
PR_NUMBER=17
'

echo "*** Printing all variables ***"

echo "PROJECT_ID=${PROJECT_ID}"
echo "COMMIT_SHA=${COMMIT_SHA}"
echo "SHORT_SHA=${SHORT_SHA}"
echo "REPO_NAME=${REPO_NAME}"
echo "BRANCH_NAME=${BRANCH_NAME}"
echo "HEAD_BRANCH=${HEAD_BRANCH}"
echo "BASE_BRANCH=${BASE_BRANCH}"
echo "HEAD_REPO_URL=${HEAD_REPO_URL}"
echo "PR_NUMBER=${PR_NUMBER}"

git clone "${BASE_REPO_URL}" --branch ${BASE_BRANCH} --single-branch
echo "Repo cloned successfully"
cd "${REPO_NAME}"
git config user.email "presubmit@example.com"
git config user.name "presubmit"
git fetch origin refs/pull/${PR_NUMBER}/head:validate#${PR_NUMBER}
echo "pull ref created"
git checkout validate#${PR_NUMBER}
#merge --ff-only rebase
if ! git rebase "origin/${BASE_BRANCH}"
then
  echo "PR#${PR_NUMBER} cannot be rebased automatically. Resolve conflicts manually"
  exit 1
fi

echo "PR#${PR_NUMBER} can be rebased successfully on ${BASE_BRANCH}."