#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  VpcStack,
  AuroraMysqlStack,
  MSKProvisionedStack,
  MSKServerlessStack,
  MSKClusterPolicyStack,
  KafkaConnectorStack,
  KinesisFirehoseStack,
  BastionHostEC2InstanceStack,
  S3Stack
)

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

vpc_stack = VpcStack(app, 'MSKtoS3VpcStack',
  env=AWS_ENV)

aurora_mysql_stack = AuroraMysqlStack(app, 'AuroraMySQLAsDataSourceStack',
  vpc_stack.vpc,
  env=AWS_ENV
)
aurora_mysql_stack.add_dependency(vpc_stack)

# Choose between provisioned or serverless MSK cluster
# Both expose the same interface (msk_cluster_name, msk_security_groups, msk_subnets)
# so downstream stacks (KafkaConnector, Firehose, etc.) work with either option

# Option 1: Provisioned MSK Cluster
# - Configurable broker instance types and EBS volumes
# - Supports ZooKeeper and IAM authentication
# - More control over cluster configuration
# msk_stack = MSKProvisionedStack(app, 'MSKStack',
#   vpc_stack.vpc,
#   env=AWS_ENV
# )
# msk_stack.add_dependency(aurora_mysql_stack)

# Option 2: Serverless MSK Cluster (currently active)
# - No broker management required
# - Automatic scaling based on workload
# - IAM authentication only
# - No ZooKeeper (uses KRaft)
msk_stack = MSKServerlessStack(app, 'MSKServerlessStack',
  vpc_stack.vpc,
  env=AWS_ENV
)
msk_stack.add_dependency(aurora_mysql_stack)

msk_policy_stack = MSKClusterPolicyStack(app, 'MSKClusterPolicy',
  vpc_stack.vpc,
  msk_stack.msk_cluster_name,
  env=AWS_ENV
)
msk_policy_stack.add_dependency(msk_stack)

bastion_host = BastionHostEC2InstanceStack(app, 'BastionHost',
  vpc_stack.vpc,
  aurora_mysql_stack.sg_mysql_client,
  msk_stack.sg_msk_client,
  msk_stack.msk_cluster_name,
  env=AWS_ENV
)
bastion_host.add_dependency(msk_policy_stack)

msk_connector_stack = KafkaConnectorStack(app, 'KafkaConnectorStack',
  vpc_stack.vpc,
  aurora_mysql_stack.db_hostname,
  aurora_mysql_stack.sg_mysql_client,
  aurora_mysql_stack.rds_credentials,
  msk_stack.msk_cluster_name,
  msk_stack.msk_security_groups,
  msk_stack.msk_subnets,
  env=AWS_ENV
)
msk_connector_stack.add_dependency(bastion_host)

s3_stack = S3Stack(app, 'S3AsFirehoseDestinationStack',
  env=AWS_ENV
)
s3_stack.add_dependency(bastion_host)

firehose_stack = KinesisFirehoseStack(app, 'FirehosefromMSKtoS3Stack',
  msk_stack.msk_cluster_name,
  msk_stack.msk_cluster_arn,
  s3_stack.s3_bucket,
  env=AWS_ENV
)
firehose_stack.add_dependency(s3_stack)

app.synth()
