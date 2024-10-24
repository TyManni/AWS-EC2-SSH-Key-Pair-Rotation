# AWS-EC2-SSH-Key-Pair-Rotation
Automates the rotation of SSH key pairs for AWS EC2 instances, enhancing security by invalidating old keys and deploying new ones securely. By regularly rotating SSH keys, we mitigate the risk of unauthorized access to EC2 instances.

Features

Create a new SSH key pair using the AWS EC2 API
Add the new public key to the EC2 instance's authorized keys
Remove the old SSH key from the instance
Prerequisites

Before using this project, make sure you have the following tools installed:

Python 3.6+
pip for installing dependencies
AWS CLI configured with proper IAM credentials
boto3 and paramiko Python libraries

Update Configuration
In the key_rotation.py script, update the following variables with your AWS configuration and EC2 instance details:

REGION: The AWS region your EC2 instance is running in (e.g., us-east-1)
INSTANCE_ID: The ID of the EC2 instance for which you want to rotate the SSH key
OLD_KEY_NAME: The name of the old SSH key that will be removed
NEW_KEY_NAME: The name of the new SSH key pair to be created

Error Handling
If an error occurs, the script will provide error messages to help you troubleshoot.
