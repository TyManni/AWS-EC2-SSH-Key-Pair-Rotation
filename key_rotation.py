import boto3
import time
import paramiko
import botocore
import os
import subprocess

# Constants
REGION = "your-region"  # Change to your region
INSTANCE_ID = "your-instance-id"  # Replace with your instance ID
OLD_KEY_NAME = "old-key-name"  # Name of the old key to be removed
NEW_KEY_NAME = "new-key-name"  # Name for the new key pair

# Initialize EC2 client
ec2_client = boto3.client("ec2", region_name=REGION)


def get_instance_public_ip(instance_id):
    try:
        instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
        public_ip = instance_info["Reservations"][0]["Instances"][0].get(
            "PublicIpAddress"
        )
        return public_ip
    except botocore.exceptions.ClientError as e:
        print(f"Error retrieving public IP: {e}")
        return None


def create_new_key_pair():
    try:
        response = ec2_client.create_key_pair(KeyName=NEW_KEY_NAME)
        new_key_material = response["KeyMaterial"]
        with open(f"{NEW_KEY_NAME}.pem", "w") as key_file:
            key_file.write(new_key_material)
        os.chmod(f"{NEW_KEY_NAME}.pem", 0o400)
        print(
            f"New key pair '{NEW_KEY_NAME}' created and saved as '{NEW_KEY_NAME}.pem'"
        )
        return new_key_material
    except botocore.exceptions.ClientError as e:
        print(f"Error creating key pair: {e}")
        return None


def add_new_public_key_to_instance(public_ip):
    try:
        result = subprocess.run(
            ["ssh-keygen", "-y", "-f", f"./{NEW_KEY_NAME}.pem"],
            capture_output=True,
            text=True,
        )
        public_key = result.stdout.strip()

        if not public_key:
            print("Error: Could not generate public key.")
            return

        old_private_key = paramiko.RSAKey.from_private_key_file(f"{OLD_KEY_NAME}.pem")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=public_ip, username="ec2-user", pkey=old_private_key
        )

        command = f"echo '{public_key}' >> /home/ec2-user/.ssh/authorized_keys"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        stdout.channel.recv_exit_status()
        print("New public key added to the instance's authorized_keys.")
        ssh_client.close()
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def remove_old_key(public_ip):
    try:
        new_private_key = paramiko.RSAKey.from_private_key_file(f"{NEW_KEY_NAME}.pem")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=public_ip, username="ec2-user", pkey=new_private_key
        )

        command = f"sed -i '/{OLD_KEY_NAME}/d' /home/ec2-user/.ssh/authorized_keys"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        stdout.channel.recv_exit_status()
        print("Old SSH key removed from authorized_keys.")
        ssh_client.close()
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    new_key_material = create_new_key_pair()
    if new_key_material:
        public_ip = get_instance_public_ip(INSTANCE_ID)
        if public_ip:
            add_new_public_key_to_instance(public_ip)
            remove_old_key(public_ip)
        else:
            print("Unable to retrieve public IP. Aborting key rotation.")
    else:
        print("Failed to create a new key pair. Aborting key rotation.")


if __name__ == "__main__":
    main()
