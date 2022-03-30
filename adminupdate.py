"""
Program: adminupdate.py
Author: Vern Bolinius
Date: March 27, 2022


Welcome to adminupdate.py!
This program updates the security group Allow-Admin-Access (for both MGW and CGW) for VMware Cloud on AWS
This is a standalone program, though much code has been borrowed from pyVMC.py

VMware Cloud on AWS API Documentation is available at: https://code.vmware.com/apis/920/vmware-cloud-on-aws
CSP API documentation is available at https://console.cloud.vmware.com/csp/gateway/api-docs
vCenter API documentation is available at https://code.vmware.com/apis/366/vsphere-automation

You can install python 3.9 from https://www.python.org/downloads/windows/ (Windows) or https://www.python.org/downloads/mac-osx/ (MacOs).

You can install the dependent python packages locally (handy for Lambda) with:
pip3 install requests or pip3 install requests -t . --upgrade
pip3 install configparser or pip3 install configparser -t . --upgrade

With git BASH on Windows, you might need to use 'python -m pip install' instead of pip3 install

"""

import requests                         # need this for Get/Post/Delete
import configparser                     # parsing config file
import operator
import time
import json
import sys
from os.path import exists
import ipaddress                        # required to determine client's IPv4 address

if not exists("./config.ini"):
    print('config.ini is missing - rename config.ini.example to config.ini and populate the required values inside the file.')
    sys.exit()

DEBUG_MODE = False

config = configparser.ConfigParser()
config.read("./config.ini")
strProdURL      = config.get("vmcConfig", "strProdURL")
strCSPProdURL   = config.get("vmcConfig", "strCSPProdURL")
Refresh_Token   = config.get("vmcConfig", "refresh_Token")
ORG_ID          = config.get("vmcConfig", "org_id")
SDDC_ID         = config.get("vmcConfig", "sddc_id")


if len(strProdURL) == 0 or len(strCSPProdURL) == 0 or len(Refresh_Token) == 0 or len(ORG_ID) == 0 or len(SDDC_ID) == 0:
    print('strProdURL, strCSPProdURL, Refresh_Token, ORG_ID, and SDDC_ID must all be populated in config.ini')
    sys.exit()

def getAccessToken(myKey):
    """ Gets the Access Token using the Refresh Token """
    params = {'api_token': myKey}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post('https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize', params=params, headers=headers)
    jsonResponse = response.json()
    access_token = jsonResponse['access_token']
    return access_token

def getNSXTproxy(org_id, sddc_id, sessiontoken):
    """ Gets the Reverse Proxy URL """
    myHeader = {'csp-auth-token': sessiontoken}
    myURL = "{}/vmc/api/orgs/{}/sddcs/{}".format(strProdURL, org_id, sddc_id)
    response = requests.get(myURL, headers=myHeader)
    json_response = response.json()
    proxy_url = json_response['resource_config']['nsx_api_public_endpoint_url']
    return proxy_url

def validate_ip_address(address):
    """ Validates an IP address """
    try:
        ip = ipaddress.ip_address(address)
        is_valid = True
        # print("IP address {} is valid. The object returned is {}".format(address, ip))
    except ValueError:
        is_valid = False
        # print("IP address {} is not valid".format(address))
    return is_valid

def get_current_and_former_ip_addresses():
    """ Returns the current and previous IPv4 address using a combination of an API call and file in the current directory """
   
    current_ipv4 = requests.get('https://api.ipify.org').content.decode('utf8')
    address_file_name = "ipaddress.txt"

    # Validate current IP address
    current_ip_is_valid = validate_ip_address(current_ipv4)

    if current_ip_is_valid:
        # print("Current IP4 address is " + current_ipv4)
        address_file_exists = exists(address_file_name)
        if address_file_exists:
            # print("Address file exists")
            f = open(address_file_name, "r")
            ipaddress_on_file = (f.read())
            f.close()
            # Validate IP address on file
            ip_on_file_is_valid = validate_ip_address(ipaddress_on_file)
            if ip_on_file_is_valid:
                # print("IP address on file is " + ipaddress_on_file)
                former_ipv4 = ipaddress_on_file
                if former_ipv4 != current_ipv4:
                    # print("IP address on file is not the same as your current IP")
                    f = open(address_file_name, "w")
                    f.write(current_ipv4)
                    # print("Wrote current IP address " + current_ipv4 + " to file")
                    f.close()
            else:
                # print ("IP address on file is not valid")
                former_ipv4 = ""
                f = open(address_file_name, "w")
                f.write(current_ipv4)
                # print("Wrote current IP address " + current_ipv4 + " to file")
                f.close()
        else:
            # print("Address file does not exist")
            former_ipv4 = ""
            f = open(address_file_name, "w")
            f.write(current_ipv4)
            # print("Wrote current IP address " + current_ipv4 + " to address file")
            f.close()
        # print("Current IP is: " + current_ipv4)
        # print("Former IP is: " + former_ipv4)
    else:
        print("Current IP is not valid")
        current_ipv4 = ""
        former_ipv4 = ""
    return current_ipv4, former_ipv4

def updateAdminGroup(proxy_url,sessiontoken,gw,group_id):
    """ Updates the single SDDC Group 'group_id' with the client's current IPv4 address and removes the client's prior IPv4. Uses 'mgw' or 'cgw' as the gw parameter """
    """ If the group does not exist, it will be created """

    current_ipv4_address, former_ipv4_address = get_current_and_former_ip_addresses()
    print("Your current IPv4 address is: " + current_ipv4_address)
    print("Your former IPv4 address is: " + former_ipv4_address)
    
    if current_ipv4_address != "":
        myHeader = {'csp-auth-token': sessiontoken}
        proxy_url_short = proxy_url.rstrip("sks-nsxt-manager")
        # removing 'sks-nsxt-manager' from proxy url to get correct URL

        # Get expression_id and list of IP addresses for group 
        myGetURL = proxy_url_short + "policy/api/v1/infra/domains/" + gw + "/groups/" + group_id
        response = requests.get(myGetURL, headers=myHeader)
        json_response = response.json()

        if str(response.status_code) == "404":
            print("Group " + group_id + "does not exist for " + gw + ".  Will attempt to create it.")
            # Create the group and add the current IP4 address
            if newSDDCGroupIPaddress(proxy_url,sessiontoken,gw,group_id,current_ipv4_address) != "200":
                print("Unable to create group " + group_id)
            else:
                print("Created group " + group_id + " and added IP address " + current_ipv4_address)
        
        elif "expression" in str(json_response):
            if "IPAddressExpression" in str(json_response):
                # Loop through list/array elements until we find the one with "IPAddressExpression"
                i = 0
                while "IPAddressExpression" not in str(json_response["expression"][i]):
                    i = i + 1
                group_criteria = json_response["expression"][i]
                expression_id = group_criteria["id"]
                group_IP_list = group_criteria["ip_addresses"]
                print("IP addresses currently in the group: ")
                print(group_IP_list)
                # Handle currrent IP address
                if current_ipv4_address not in group_IP_list:
                    myPostURL = proxy_url_short + "policy/api/v1/infra/domains/" + gw + "/groups/" + group_id + "/ip-address-expressions/" + expression_id + "?action=add"
                    body = {
                        "ip_addresses":[current_ipv4_address]
                    }
                    response = requests.post(myPostURL, json=body, headers=myHeader)
                    print(response)
                    print("Your current IPv4 address has been added to the group")
                else:
                    print("Your current IPv4 address is already in the group")
                # Handle former IP address
                if former_ipv4_address != "":
                    if former_ipv4_address in group_IP_list:
                        if (former_ipv4_address != current_ipv4_address):
                            myPostURL = proxy_url_short + "policy/api/v1/infra/domains/" + gw + "/groups/" + group_id + "/ip-address-expressions/" + expression_id + "?action=remove"
                            body = {
                                "ip_addresses":[former_ipv4_address]
                            }
                            response = requests.post(myPostURL, json=body, headers=myHeader)
                            print("Your former IPv4 address was removed from group")
                        else:
                            print("Your IPv4 address has not changed since the last time this program was run")
                    else:
                        print("Your former IPv4 address was not in the group")    
                else:
                    print("Unable to get former IPv4 address")  

            else:
                print("The group " + group_id + " is not based on the IP addresses criteria")
        else:
            print('API call failed.  Expected a response containing the field "expression"')
    else:
       print ("Unable to get current IPv4 address") 
    return


def newSDDCGroupIPaddress(proxy_url,sessiontoken,gw,group_id,ip_addresses):
    """ Creates a single SDDC Group based on IP addresses. Use 'mgw' or 'cgw' as the parameter """
    myHeader = {'csp-auth-token': sessiontoken}
    proxy_url_short = proxy_url.rstrip("sks-nsxt-manager")
    # removing 'sks-nsxt-manager' from proxy url to get correct URL
    myURL = proxy_url_short + "policy/api/v1/infra/domains/" + gw + "/groups/" + group_id
    json_data = {
    "expression" : [ {
      "ip_addresses" : ip_addresses,
      "resource_type" : "IPAddressExpression"
    } ],
    "id" : group_id,
    "display_name" : group_id,
    "resource_type" : "Group"}
    response = requests.put(myURL, headers=myHeader, json=json_data)
    json_response_status_code = response.status_code
    return json_response_status_code


# --------------------------------------------
# ---------------- Main ----------------------
# --------------------------------------------


session_token = getAccessToken(Refresh_Token)
proxy = getNSXTproxy(ORG_ID, SDDC_ID, session_token)
gw_list = ["mgw", "cgw"]
group_id = "Allow-Admin-Access" 

for gw in gw_list:
    print("\n" + "Running against gateway: " + gw)
    updateComplete = updateAdminGroup(proxy,session_token,gw,group_id)

    
