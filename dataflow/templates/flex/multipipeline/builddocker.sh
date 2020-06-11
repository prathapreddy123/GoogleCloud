function fake_to_gcs() {
 cat BaseDockerfile > Dockerfile
 cat << EOF >> Dockerfile

COPY deps/fake_to_gcs_requirements.txt .
RUN pip install -r requirements.txt

# Copy source files
COPY setup.py .
COPY fake_to_gcs.py ./main.py
COPY fake_messages ./fake_messages
EOF
}
