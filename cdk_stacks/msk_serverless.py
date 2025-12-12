#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_logs,
  aws_msk
)
from constructs import Construct


class MSKServerlessStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    msk_cluster_name = self.node.try_get_context("msk_serverless_cluster_name") or f"{self.node.try_get_context('msk_cluster_name')}-serverless"

    MSK_CLIENT_SG_NAME = f'msk-serverless-client-sg-{msk_cluster_name}'
    sg_msk_client = aws_ec2.SecurityGroup(self, 'KafkaClientSecurityGroup',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for Amazon MSK Serverless client',
      security_group_name=MSK_CLIENT_SG_NAME
    )
    cdk.Tags.of(sg_msk_client).add('Name', MSK_CLIENT_SG_NAME)

    MSK_CLUSTER_SG_NAME = f'msk-serverless-cluster-sg-{msk_cluster_name}'
    sg_msk_cluster = aws_ec2.SecurityGroup(self, 'MSKSecurityGroup',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for Amazon MSK Serverless Cluster',
      security_group_name=MSK_CLUSTER_SG_NAME
    )
    # MSK Serverless uses IAM authentication and communicates over port 9098
    # No ZooKeeper ports needed (serverless doesn't use ZooKeeper)
    sg_msk_cluster.add_ingress_rule(peer=sg_msk_client, connection=aws_ec2.Port.tcp(9098),
      description='allow msk client to communicate with serverless brokers using IAM authentication')
    cdk.Tags.of(sg_msk_cluster).add('Name', MSK_CLUSTER_SG_NAME)

    # Serverless cluster configuration
    msk_serverless_vpc_config = aws_msk.CfnServerlessCluster.VpcConfigProperty(
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids,
      security_groups=[sg_msk_client.security_group_id, sg_msk_cluster.security_group_id]
    )

    # IAM authentication is required for serverless clusters
    msk_serverless_client_auth = aws_msk.CfnServerlessCluster.ClientAuthenticationProperty(
      sasl=aws_msk.CfnServerlessCluster.SaslProperty(
        iam=aws_msk.CfnServerlessCluster.IamProperty(
          enabled=True
        )
      )
    )

    msk_serverless_cluster = aws_msk.CfnServerlessCluster(self, 'AWSKafkaServerlessCluster',
      cluster_name=msk_cluster_name,
      client_authentication=msk_serverless_client_auth,
      vpc_configs=[msk_serverless_vpc_config]
    )

    self.sg_msk_client = sg_msk_client
    self.msk_cluster_name = msk_serverless_cluster.cluster_name
    self.msk_cluster_arn = msk_serverless_cluster.attr_arn
    # Expose security groups and subnets for KafkaConnector compatibility
    self.msk_security_groups = [sg_msk_client.security_group_id, sg_msk_cluster.security_group_id]
    self.msk_subnets = vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids

    cdk.CfnOutput(self, 'MSKServerlessSecurityGroupID', value=sg_msk_cluster.security_group_id,
      export_name=f'{self.stack_name}-ClusterSecurityGroupID')
    cdk.CfnOutput(self, 'KafkaServerlessClientSecurityGroupID', value=sg_msk_client.security_group_id,
      export_name=f'{self.stack_name}-ClientSecurityGroupID')
    cdk.CfnOutput(self, 'MSKServerlessClusterArn', value=msk_serverless_cluster.attr_arn,
      export_name=f'{self.stack_name}-MSKClusterArn')
    cdk.CfnOutput(self, 'MSKServerlessClusterName', value=self.msk_cluster_name,
      export_name=f'{self.stack_name}-MSKClusterName')
