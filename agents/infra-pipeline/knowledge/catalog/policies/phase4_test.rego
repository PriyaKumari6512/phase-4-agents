package main

test_variable_region_denied if {
    count(deny) > 0 with input as {"variables":{"region":{"value":"sa-east-1"}},
        "configuration":{"provider_config":{"aws":{"expressions":{"region":{"references":["var.region"]}}}}}}
}

test_variable_allowed_region if {
    count(deny) == 0 with input as {"variables":{"region":{"value":"ap-south-1"}},
        "configuration":{"provider_config":{"aws":{"expressions":{"region":{"references":["var.region"]}}}}}}
}

test_ipv6_public_ssh_denied if {
    count(deny) > 0 with input as {"resource_changes":[{"address":"aws_security_group.s","type":"aws_security_group",
        "change":{"actions":["create"],"after":{"ingress":[{"from_port":22,"ipv6_cidr_blocks":["::/0"]}]}}}]}
}

test_ipv6_standalone_ssh_denied if {
    count(deny) > 0 with input as {"resource_changes":[{"address":"aws_vpc_security_group_ingress_rule.s","type":"aws_vpc_security_group_ingress_rule",
        "change":{"actions":["create"],"after":{"from_port":22,"cidr_ipv6":"::/0"}}}]}
}

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
		"ingress": [{"from_port": 443, "to_port":443, "protocol":"tcp", "cidr_blocks": ["0.0.0.0/0"]}]}}}]}
}

test_web_port_range_cannot_open_arbitrary_ports if {
    count(deny) > 0 with input as {"resource_changes":[{"address":"aws_security_group.s","type":"aws_security_group",
        "change":{"actions":["create"],"after":{"ingress":[{"from_port":80,"to_port":65535,"protocol":"tcp","cidr_blocks":["0.0.0.0/0"]}]}}}]}
}

test_all_protocols_not_exempt_on_web_port if {
    count(deny) > 0 with input as {"resource_changes":[{"address":"aws_vpc_security_group_ingress_rule.s","type":"aws_vpc_security_group_ingress_rule",
        "change":{"actions":["create"],"after":{"from_port":443,"to_port":443,"ip_protocol":"-1","cidr_ipv6":"::/0"}}}]}
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
