package main

ok_tags := {"project": "p", "environment": "dev", "owner": "o", "managed-by": "x"}

test_missing_tags_denied if {
	count(deny) > 0 with input as {"resource_changes": [{"address": "aws_sqs_queue.q", "type": "aws_sqs_queue",
		"change": {"actions": ["create"], "after": {"tags_all": {"project": "p"}}}}]}
}

test_tags_ok if {
	count(deny) == 0 with input as {"resource_changes": [{"address": "aws_sqs_queue.q", "type": "aws_sqs_queue",
		"change": {"actions": ["create"], "after": {"tags_all": ok_tags}}}]}
}

test_wildcard_iam_denied if {
	count(deny) > 0 with input as {"resource_changes": [{"address": "aws_iam_policy.p", "type": "aws_iam_policy",
		"change": {"actions": ["create"], "after": {"tags_all": ok_tags,
		"policy": "{\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"*\",\"Resource\":\"*\"}]}"}}}]}
}

test_public_ssh_denied if {
	count(deny) > 0 with input as {"resource_changes": [{"address": "aws_security_group.s", "type": "aws_security_group",
		"change": {"actions": ["create"], "after": {"tags_all": ok_tags,
		"ingress": [{"from_port": 22, "cidr_blocks": ["0.0.0.0/0"]}]}}}]}
}

test_https_public_allowed if {
	count(deny) == 0 with input as {"resource_changes": [{"address": "aws_security_group.s", "type": "aws_security_group",
		"change": {"actions": ["create"], "after": {"tags_all": ok_tags,
		"ingress": [{"from_port": 443, "cidr_blocks": ["0.0.0.0/0"]}]}}}]}
}

test_db_destroy_denied if {
	count(deny) > 0 with input as {"resource_changes": [{"address": "aws_db_instance.d", "type": "aws_db_instance",
		"change": {"actions": ["delete", "create"], "after": {}}}]}
}

test_unencrypted_db_denied if {
	count(deny) > 0 with input as {"resource_changes": [{"address": "aws_db_instance.d", "type": "aws_db_instance",
		"change": {"actions": ["create"], "after": {"tags_all": ok_tags, "storage_encrypted": false,
		"deletion_protection": true}}}]}
}

test_unpinned_module_denied if {
	count(deny) > 0 with input as {"configuration": {"root_module": {"module_calls": {"vpc": {
		"source": "terraform-aws-modules/vpc/aws"}}}}}
}

test_bad_region_denied if {
	count(deny) > 0 with input as {"configuration": {"provider_config": {"aws": {"expressions": {
		"region": {"constant_value": "sa-east-1"}}}}}}
}
