#!/usr/bin/python3
import ipaddress
import requests
from urllib.parse import urlencode

from config import API_KEY, my_domains

# see also https://github.com/clempaul/dreamhost-dynamic-dns

# https://help.dreamhost.com/hc/en-us/articles/217555707-DNS-API-commands
def make_request(command, params={}):
    full_params = params.copy()
    full_params["key"] = API_KEY
    full_params["cmd"] = command
    url = f"https://api.dreamhost.com/?{urlencode(full_params)}"
    r = requests.get(url)
    r.raise_for_status()
    return r

def get_records():
    req = make_request("dns-list_records")
    response = req.text
    if response.startswith("success\n"):
        # response = response.lstrip('success\n')
        response = response.lstrip('suce\n') # how lstrip actually works
    return parse_tsv(response)

def remove_record(dns_record):
    params = {
        "record": dns_record["record"],
        "type": dns_record["type"],
        "value": dns_record["value"],
    }
    make_request("dns-remove_record", params)

def add_record(domain, ip, dns_type="A", comment="set by ddns script"):
    params = {
        "record": domain,
        "type": dns_type,
        "value": ip,
        "comment": comment
    }
    return make_request("dns-add_record", params)

def get_my_ip():
    # https://api.ipify.org/
    # https://icanhazip.com/ - adds newline
    r = requests.get('https://api.ipify.org')
    r.raise_for_status()
    ip = r.text.strip() # call strip, icanhazip will add a newline
    # make sure ip address is valid (will raise error if isnt)
    ipaddress.ip_address(ip)
    return ip

def parse_tsv(text):
    # csv.DictReader not working...
    delimiter = '\t'
    arr = text.split('\n')
    headers = (arr[0]).split(delimiter)
    response = []
    for line in arr[1:]:
        values = line.split(delimiter)
        if not values or len(values) < 2:
            continue
        d = {headers[i]: values[i] for i in range(len(values))}
        # d = dict(map(lambda i,j : (i,j) , headers,values))
        response.append(d)
    return response

def get_dns_record(dns_records, domain, dns_type="A"):
    # return the A record for a given domain
    # each row has keys: account_id, zone, record, type, value, comment, editable
    return next((
        record for record in dns_records if record['record'] == domain and record['type'] == dns_type
    ), None)

def check_domains(hosted_domains):
    current_ip = get_my_ip()
    dns_records = get_records()
    for domain in hosted_domains:
        record = get_dns_record(dns_records, domain)
        if not record:
            print(f"Could not find matching DNS record for {domain}")
            continue
        elif record['editable'] != '1':
            print(f"DNS record for {domain} is not editable")
            continue
        elif record['value'] == current_ip:
            print(f"DNS record for {domain} is already set to {current_ip}")
            continue
        else:
            print(f"Updating {domain} from {record['value']} to {current_ip}")
            remove_record(record)
            add_record(domain, current_ip, dns_type=record['type'])


if __name__=="__main__":
    check_domains(my_domains)