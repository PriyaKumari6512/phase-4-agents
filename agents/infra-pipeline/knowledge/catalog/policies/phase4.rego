# Phase 4 infra policy library. Evaluated by Conftest on `tofu show -json` plan output.
# Policy failures block apply until a policy owner runs `atlantis approve_policies`.
package main

required_tags := {"project", "environment", "owner", "managed-by"}

allowed_regions := {"us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-south-1"}

stateful_types := {
	"aws_db_instance", "aws_rds_cluster", "aws_elasticache_replication_group", "aws_s3_bucket",
	"aws_dynamodb_table", "aws_efs_file_system", "aws_ebs_volume",
}

changing(rc) if {
	some a in rc.change.actions
	a in {"create", "update"}
}

# ---- required tags (AWS default_tags surface in tags_all) ----
deny contains msg if {
	some rc in input.resource_changes
	changing(rc)
	tags := object.get(rc.change.after, "tags_all", null)
	is_object(tags)
	missing := required_tags - {k | some k, _ in tags}
	count(missing) > 0
	msg := sprintf("%s is missing required tags: %v", [rc.address, sort(missing)])
}

# ---- allowed regions ----
provider_regions contains region if {
    region := input.configuration.provider_config.aws.expressions.region.constant_value
}

provider_regions contains region if {
    "var.region" in input.configuration.provider_config.aws.expressions.region.references
    region := input.variables.region.value
}

deny contains msg if {
    some region in provider_regions
	not region in allowed_regions
	msg := sprintf("provider region %s is not on the allow-list", [region])
}

deny contains "AWS provider region could not be resolved from the plan" if {
    input.configuration.provider_config.aws
    count(provider_regions) == 0
}

# ---- wildcard IAM ----
deny contains msg if {
	some rc in input.resource_changes
	rc.type in {"aws_iam_policy", "aws_iam_role_policy", "aws_iam_user_policy", "aws_iam_group_policy"}
	changing(rc)
	doc := json.unmarshal(rc.change.after.policy)
	some st in as_array(doc.Statement)
	st.Effect == "Allow"
	"*" in as_array(st.Action)
	"*" in as_array(st.Resource)
	msg := sprintf("%s grants Action * on Resource *", [rc.address])
}

# ---- public ingress (only 80/443 may be world-open) ----
web_only(rule) if {
    rule.from_port in {80, 443}
    rule.to_port == rule.from_port
    object.get(rule, "protocol", object.get(rule, "ip_protocol", "")) in {"tcp", "6"}
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_security_group"
	changing(rc)
	some rule in rc.change.after.ingress
	"0.0.0.0/0" in rule.cidr_blocks
	not web_only(rule)
	msg := sprintf("%s opens port %v to 0.0.0.0/0", [rc.address, rule.from_port])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_vpc_security_group_ingress_rule"
	changing(rc)
	rc.change.after.cidr_ipv4 == "0.0.0.0/0"
	not web_only(rc.change.after)
	msg := sprintf("%s opens port %v to 0.0.0.0/0", [rc.address, rc.change.after.from_port])
}

deny contains msg if {
    some rc in input.resource_changes
    rc.type == "aws_security_group"
    changing(rc)
    some rule in rc.change.after.ingress
    "::/0" in object.get(rule, "ipv6_cidr_blocks", [])
    not web_only(rule)
    msg := sprintf("%s opens port %v to ::/0", [rc.address, rule.from_port])
}

deny contains msg if {
    some rc in input.resource_changes
    rc.type == "aws_vpc_security_group_ingress_rule"
    changing(rc)
    rc.change.after.cidr_ipv6 == "::/0"
    not web_only(rc.change.after)
    msg := sprintf("%s opens port %v to ::/0", [rc.address, rc.change.after.from_port])
}

# ---- encryption and deletion protection for stateful data ----
deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_db_instance"
	changing(rc)
	rc.change.after.storage_encrypted != true
	msg := sprintf("%s must have storage_encrypted = true", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_db_instance"
	changing(rc)
	rc.change.after.deletion_protection != true
	msg := sprintf("%s must have deletion_protection = true", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_elasticache_replication_group"
	changing(rc)
	rc.change.after.at_rest_encryption_enabled != true
	msg := sprintf("%s must enable at-rest encryption", [rc.address])
}

# ---- never destroy or replace stateful resources without explicit policy approval ----
deny contains msg if {
	some rc in input.resource_changes
	rc.type in stateful_types
	"delete" in rc.change.actions
	msg := sprintf("%s would be destroyed or replaced (stateful) - requires policy owner approval", [rc.address])
}

# ---- module sources must be pinned ----
deny contains msg if {
	some name, call in input.configuration.root_module.module_calls
	not call.version_constraint
	not startswith(call.source, "./")
	not startswith(call.source, "../")
	msg := sprintf("module %s (%s) has no version pin", [name, call.source])
}

as_array(x) := x if is_array(x)

as_array(x) := [x] if not is_array(x)
