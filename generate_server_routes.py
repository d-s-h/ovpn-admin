import sys
import subprocess
import ipaddress
from datetime import datetime

def is_valid_ip(address):
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False

def convert_ip_mask_to_full_mask(ip_mask):
    try:
        network = ipaddress.IPv4Network(ip_mask, strict=False)
        ip_address = str(network.network_address)
        full_mask = str(network.netmask)
        return ip_address, full_mask
    except ValueError:
        return None, None
    
def set_zero_after_last_dot(ip_address):
    parts = ip_address.rsplit('.', 1)
    if len(parts) == 2:
        return parts[0] + '.0'
    else:
        # Invalid IP address format
        return None

# Check if a routes file is provided as a command-line argument
if len(sys.argv) > 1:
    route_file = sys.argv[1]
else:
    print("Please provide a domain names file as a command-line argument.")
    sys.exit(1)

# Read the domain names from the file
with open(route_file, "r") as file:
    route_lines = file.read().splitlines()

# Check if any domain names are found
if not route_lines:
    print("The routes file is empty.")
    sys.exit(1)

# Run Bash command for each domain name
output_file_name = "DEFAULT"
if len(sys.argv) > 2:
    output_file_name = sys.argv[2]

with open(output_file_name, "w", newline='\n') as output_file:
    # Fill out a file header
    current_datetime = datetime.now()
    datetime_string = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    current_script_name = sys.argv[0]
    output_file.write(f"# This file is generated from {route_file} at {datetime_string} by {current_script_name}\n")

    # generate routes
    for line in route_lines:
        # Bash command to run for each domain
        ip, mask = convert_ip_mask_to_full_mask(line)
        if(ip != None):
            # Don't try to resolve, use as is
            mask = mask if mask != None else "255.255.255.255"
            output_file.write(f"push \"route {ip} {mask} vpn_gateway\" # {line}\n")
        elif line.startswith('#') or line.strip() == "":
            # A comment line, write out as is
            output_file.write(line + '\n')
        else:
            # Resolve a domain name into an IP address
            # Execute the Bash command using subprocess
            #bash_command = f"echo {line}" # for test
            bash_command = f"dig -4 -t A +short {line}"
            process = subprocess.Popen(bash_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()
            
            # Handle any errors if needed
            if not error:
                ip_lines = output.decode().splitlines()
                for ip in ip_lines:
                    if(is_valid_ip(ip)):
                        # For resolved addresses use a subnet route form to cover different servers and names (e.g. instagram)
                        subnet = set_zero_after_last_dot(ip)
                        mask = "255.255.255.0"
                        output_file.write(f"push \"route {subnet} {mask} vpn_gateway\" # {line} is resolved to {ip}\n")
                    else:
                        output_file.write(f"# {line} is resolved to non-valid IP\n")
            else:
                output_file.write(f"# DNS resolve error for {line}:\n", error.decode())
                print(f"# DNS resolve error for {line}:\n", error.decode())
