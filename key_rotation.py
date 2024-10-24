import boto3
import time
import paramiko
import botocore

# Constants
REGION = "your-region"  # Change to your region
INSTANCE_ID = "your-instance-id"  # Replace with your instance ID
OLD_KEY_NAME = "old-key-name"  # Name of the old key to be removed
NEW_KEY_NAME = "new-key-name"  # Name for the new key pair

# Initialize Boto3 EC2 client
ec2_client = boto3.client("ec2", region_name=REGION)


def get_instance_public_ip(instance_id):
    try:
        # Retrieve public IP of the instance
        instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
        public_ip = instance_info["Reservations"][0]["Instances"][0].get(
            "PublicIpAddress"
        )
        return public_ip
    except botocore.exceptions.ClientError as e:
        print(f"Error retrieving instance public IP: {e}")
        return None


def create_new_key_pair():
    try:
        # Create a new SSH key pair
        response = ec2_client.create_key_pair(KeyName=NEW_KEY_NAME)
        new_key_material = response["KeyMaterial"]

        # Save the private key to a file
        with open(f"{NEW_KEY_NAME}.pem", "w") as key_file:
            key_file.write(new_key_material)

        # Change permissions of the key file
        import os

        os.chmod(f"{NEW_KEY_NAME}.pem", 0o400)

        print(
            f"New key pair '{NEW_KEY_NAME}' created and saved as '{NEW_KEY_NAME}.pem'"
        )
        return new_key_material

    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "LimitExceeded":
            print(
                "Error: You have reached your limit for key pairs. Please delete some old key pairs to proceed."
            )
        else:
            print(f"Error creating key pair: {e}")
        return None


def add_new_public_key_to_instance(public_ip, new_key_material):
    try:
        # Generate the public key from the private key file
        import subprocess

        result = subprocess.run(
            ["ssh-keygen", "-y", "-f", f"./{NEW_KEY_NAME}.pem"],
            capture_output=True,
            text=True,
        )
        public_key = result.stdout.strip()

        # Connect to the instance using the old key (so we can add the new one)
        old_private_key = paramiko.RSAKey.from_private_key_file(f"{OLD_KEY_NAME}.pem")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect using the old key to modify authorized_keys
        ssh_client.connect(
            hostname=public_ip, username="ec2-user", pkey=old_private_key
        )

        # Add the new public key to the instance
        command = f"echo '{public_key}' >> /home/ec2-user/.ssh/authorized_keys"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        stdout.channel.recv_exit_status()  # Wait for command to finish

        print("New SSH public key added to the instance's authorized_keys.")

        # Close the SSH connection
        ssh_client.close()

    except paramiko.ssh_exception.SSHException as e:
        print(f"SSH connection error: {e}")
    except Exception as e:
        print(f"An error occurred while adding the new key: {e}")


def remove_old_key(public_ip):
    try:
        # Connect to the instance to remove the old key
        new_private_key = paramiko.RSAKey.from_private_key_file(f"{NEW_KEY_NAME}.pem")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_client.connect(
            hostname=public_ip, username="ec2-user", pkey=new_private_key
        )

        # Remove the old key from authorized_keys
        command = f"sed -i '/{OLD_KEY_NAME}/d' /home/ec2-user/.ssh/authorized_keys"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        stdout.channel.recv_exit_status()  # Wait for command to finish

        print("Old SSH key removed from the instance's authorized_keys.")

        # Close the SSH connection
        ssh_client.close()

    except paramiko.ssh_exception.SSHException as e:
        print(f"SSH connection error: {e}")
    except Exception as e:
        print(f"An error occurred while removing the old key: {e}")


def main():
    # Step 1: Create a new key pair
    new_key_material = create_new_key_pair()
    if new_key_material:
        # Step 2: Get the public IP of the instance
        public_ip = get_instance_public_ip(INSTANCE_ID)
        if public_ip:
            # Step 3: Add the new public key to the instance's authorized_keys
            add_new_public_key_to_instance(public_ip, new_key_material)

            # Step 4: Remove the old key from authorized_keys
            remove_old_key(public_ip)
        else:
            print("Unable to retrieve public IP. Aborting key rotation.")
    else:
        print("Failed to create a new key pair. Aborting key rotation.")


if __name__ == "__main__":
    main()
