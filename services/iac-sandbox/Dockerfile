# IaC validation sandbox: no cloud credentials, run with --network limited to registries.
FROM python:3.12-slim
# Optional PEM trust bundle for environments with an HTTPS inspection proxy.
# docker build --secret id=build-ca,src=/path/to/public-ca-bundle.pem ...
RUN --mount=type=secret,id=build-ca if [ -s /run/secrets/build-ca ]; then \
    cp /run/secrets/build-ca /usr/local/share/ca-certificates/phase4-build.crt && update-ca-certificates; fi
ARG TOFU_VERSION=1.13.2
ARG TFLINT_VERSION=0.65.0
ARG TRIVY_VERSION=0.76.1
ARG CONFTEST_VERSION=0.71.0
ARG ACTIONLINT_VERSION=1.7.12
ARG GITLEAKS_VERSION=8.30.1
ARG HELM_VERSION=4.3.1
ARG KUBECONFORM_VERSION=0.7.0
RUN apt-get update && apt-get install -y --no-install-recommends bash curl unzip ca-certificates git && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL -o /tmp/t.zip https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_linux_amd64.zip && unzip /tmp/t.zip tofu -d /usr/local/bin \
 && curl -fsSL -o /tmp/l.zip https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_amd64.zip && unzip /tmp/l.zip -d /usr/local/bin \
 && curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz | tar xz -C /usr/local/bin trivy \
 && curl -fsSL https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz | tar xz -C /usr/local/bin conftest \
 && curl -fsSL https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz | tar xz -C /usr/local/bin actionlint \
 && curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz | tar xz -C /usr/local/bin gitleaks \
 && curl -fsSL https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz | tar xz -C /tmp && mv /tmp/linux-amd64/helm /usr/local/bin/helm \
 && curl -fsSL https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/kubeconform-linux-amd64.tar.gz | tar xz -C /usr/local/bin kubeconform \
 && pip install --no-cache-dir checkov==3.4.3 \
 && rm -f /tmp/*.zip
RUN useradd -m sandbox
USER sandbox
WORKDIR /work
