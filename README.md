# adminupdate.py

## Overview

# adminupdate
Welcome to adminupdate for VMware Cloud on AWS !

## What does this code do? ? 
It is a purpose-built tool for updating the security group "Allow-Admin-Access" 
in the Management and Compute Gateways in a VMware Cloud on AWS SDDC with your current IPv4 address.  To ensure that the group is "cleaned up" if/when your IP address changes, it looks for your previous IPv4 and removes it from the group.  The group is created if it does not exist.
Inclusion of the group to firewall rules is left to the user.

## What are the pre-requisites for adminupdate ?
- Python3 installed on your machine
- a VMware Cloud on AWS account

## How do I use adminupdate ?
- clone repo
- install dependencies
```
$ pip install -r requirements.txt
```
- copy config.ini.example to config.ini and add your own token
- Edit the config.ini with your own SDDC ID,  Organization (Org) ID and your access token.

## Do I need to know Python?
No! You can simply use it to consume and manage your VMware Cloud on AWS SDDC (Software-Defined Data Center). 

## Is it officially supported by VMware?
Sorry but no, this is a community-based effort. Use it at your own risk. 

## Which version of VMware Cloud on AWS has it been tested against?
Versions 1.16, 1.17. We don't guarantee support with previous versions. 

## Where can I find documentation about VMware Cloud on AWS:
Please check the online documentation:
https://docs.vmware.com/en/VMware-Cloud-on-AWS/index.html

## Credits and kudos
The structure of adminupdate, along with some code, was adapted from pyVMC.py,
a superb Python utility for VMware Cloud on AWS.  pyVMC.py is publicly available 
in GitHub.  Additional information can be found at:

https://nicovibert.com/2020/02/25/pyvmc-python-vmware-cloud-aws/

First main update:
https://nicovibert.com/2020/06/01/fling-update-pyvmc-1-1-release-and-a-walkthrough-through-some-python-code/

Additional Blog Posts:
http://www.patrickkremer.com/pyvmc/

## Release Notes


