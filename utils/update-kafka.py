import boto3

cluster_arn = 'arn:aws:kafka:us-west-2:664418978161:cluster/retail-trans/bac868d5-24d7-489a-a409-77478dbcdc5c-4'
region = 'us-west-2'

client = boto3.client('kafka', region_name=region)
cluster_info = client.describe_cluster_v2(ClusterArn=cluster_arn)
current_version = cluster_info['ClusterInfo']['CurrentVersion']

client_authentication = {
  "Sasl": {
    "Scram": {
      "Enabled": False
    },
    "Iam": {
      "Enabled": True
    }
  },
  "Unauthenticated": {
    "Enabled": False
  }
}

connectivity_info = {
  "VpcConnectivity": {
    "ClientAuthentication": {
      "Sasl": {
        "Scram": {
          "Enabled": False
        },
        "Iam": {
          "Enabled": True
        }
      }
    }
  }
}

response = client.update_connectivity(ClusterArn=cluster_arn,
                                      ConnectivityInfo=connectivity_info,
                                      CurrentVersion=current_version)

response = client.update_security(ClientAuthentication=client_authentication,
                                  ClusterArn=cluster_arn,
                                  CurrentVersion=current_version)