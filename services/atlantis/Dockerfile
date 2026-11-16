# Atlantis v0.49 no longer bundles Terraform/OpenTofu; this image adds OpenTofu + policy/cost tooling.
FROM ghcr.io/runatlantis/atlantis:v0.49.0
USER root
ARG TOFU_VERSION=1.13.2
ARG CONFTEST_VERSION=0.71.0
RUN apk add --no-cache curl unzip jq openssl python3 py3-pip \
 && curl -fsSL -o /tmp/tofu.zip https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_linux_amd64.zip \
 && unzip /tmp/tofu.zip tofu -d /usr/local/bin && rm /tmp/tofu.zip \
 && curl -fsSL https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz | tar xz -C /usr/local/bin conftest \
 && pip3 install --break-system-packages --no-cache-dir checkov==3.4.3 \
 && curl -fsSL https://raw.githubusercontent.com/infracost/cli/main/scripts/install.sh | sh
COPY repos.yaml /home/atlantis/repos.yaml
COPY policies/ /home/atlantis/policies/
ENV ATLANTIS_REPO_CONFIG=/home/atlantis/repos.yaml \
    ATLANTIS_ENABLE_POLICY_CHECKS=true \
    ATLANTIS_DEFAULT_TF_DISTRIBUTION=opentofu \
    ATLANTIS_DEFAULT_TF_VERSION=${TOFU_VERSION} \
    ATLANTIS_TF_DOWNLOAD=false
USER atlantis
