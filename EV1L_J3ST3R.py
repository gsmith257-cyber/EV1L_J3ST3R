import os
import re
import requests
import multiprocessing
import subprocess
import pycurl
from bs4 import BeautifulSoup
from googlesearch import search
from sqlalchemy import except_all
import xml.etree.cElementTree as ET

#notes:
#1: user input
#2: create md file for report
#3: scan subnet / ip
#4: add active ones to section of report
#5: nmap scan all active IPs
#6: add nmap scans in md format to md report, create a section for each IP
#7: do exploit db search for all services and version numbers running on machines
#8: add exploit-db results to report for each device
#9: attempt inital access with stuff like anonymous login to ftp or samba

def main():
    #get user input
    #get ip or subnet to scan
    print('''                    (                   (                  (     
                 )  )\ )             )  )\ )  *   )     )  )\ )  
 (    (   (   ( /( (()/(     (    ( /( (()/(` )  /(  ( /( (()/(  
 )\   )\  )\  )\()) /(_))    )\   )\()) /(_))( )(_)) )\()) /(_)) 
((_) ((_)((_)((_)\ (_))     ((_) ((_)\ (_)) (_(_()) ((_)\ (_))   
| __|\ \ / /  / (_)| |     _ | ||__ (_)/ __||_   _||__ (_)| _ \  
| _|  \ V /   | |  | |__  | || | |_ \  \__ \  | |   |_ \  |   /  
|___|  \_/    |_|  |____|  \__/ |___/  |___/  |_|  |___/  |_|_\  
                                                                 

''')
    print("Created by: S1n1st3r")

    activeIPs = []                                                   
    choice = input("Enter 1 for subnet scan or 2 for single IP: ")

    if choice == "1":
        userInput = input("Enter subnet to scan, exclude the /24: ")
        activeIPs = scanSubnet(userInput)
    elif choice == "2":
        userInput = input("Enter IP to scan: ")
        if ping_ip(userInput):
            print("IP is active")
            activeIPs = [userInput]
        else:
            print("IP is not active")
            quit()
    else:
        print("Invalid input")
        return
    #create md file for report
    notesFile = open("notes.md", "w")
    notesFile.write("#Notes for " + userInput + " scan\n<br>")
    notesFile.close()
    #add active ones to section of report
    notesFile = open("notes.md", "a")
    notesFile.write("\n##Active IPs\n<br>")
    for ip in activeIPs:
        notesFile.write(ip + "\n<br>")
    notesFile.close()
    #nmap scan all active IPs
    #add nmap scans in md format to md report, create a section for each IP
    listOfServices = nmapScan(activeIPs)
    #attempt inital access with stuff like anonymous login to ftp or samba
    for service in listOfServices:
        #if listOfServices contains smb, try smb login
        if "smb" in service or "SMB" in service:
            for ip in activeIPs:
                SAMBAcheck(ip)
        #if listOfServices contains ftp, try ftp login
        if "ftp" in service or "FTP" in service:
            for ip in activeIPs:
                ftpCheck(ip)
        #if listOfServices contains http, try http check
        if "http" in service or "HTTP" in service:
            for ip in activeIPs:
                httpCheck(ip)
        #if listOfServices contains ssh, try ssh check
        if "ssh" in service or "SSH" in service:
            for ip in activeIPs:
                sshCheck(ip)
        #if listOfServices contains telnet, try telnet check
        if "telnet" in service or "TELNET" in service:
            for ip in activeIPs:
                telnetCheck(ip)
        #if listOfServices contains snmp, try snmp check
        if "snmp" in service or "SNMP" in service:
            for ip in activeIPs:
                snmpCheck(ip)
        #if mysql is in listOfServices, try mysql check
        if "mysql" in service or "MYSQL" in service:
            for ip in activeIPs:
                mysqlCheck(ip)
        #if listOfServices contains icmp, try icmp check
        if "icmp" in service or "ICMP" in service:
            for ip in activeIPs:
                icmpCheck(ip)
        #if listOfServices contains dns, try dns check
        if "dns" in service or "DNS" in service:
            for ip in activeIPs:
                dnsCheck(ip)
        #if listOfServices contains smtp, try smtp check
        if "smtp" in service or "SMTP" in service:
            for ip in activeIPs:
                smtpCheck(ip)
        #if listOfServices contains pop3, try pop3 check
        if "pop3" in service or "POP3" in service:
            for ip in activeIPs:
                pop3Check(ip)
    #do exploit db search for all services and version numbers running on machines
    #add exploit-db results to report for each device
    searchExploitDB(listOfServices)

def ping_ip(ip):
    #ping IP
    DEVNULL = open(os.devnull, 'w')
    try:
        response = os.popen(f"ping -c 2 {ip}").read()
        if "Received = 4" in response:
            return False
        else:
            return True
    except Exception:
            return False

def ping(ip, results):
    #ping IPs
    DEVNULL = open(os.devnull, 'w')
    while True:
        if ip is None: break
        try:
            subprocess.check_call(['ping', '-c', '1', ip], stdout=DEVNULL)
            results.append(ip)
        except:
            pass

def scanSubnet(subnet):
    list = []
    pool_size = 255
    jobs = multiprocessing.Queue()
    results = multiprocessing.Queue()
    #scan subnet
    actives = []
    #get active IPs
    pool = [ multiprocessing.Process(target=ping, args=(jobs,results))
             for i in range(pool_size) ]
    for p in pool:
        p.start()

    for i in range(1,255):
        jobs.put('192.168.1.{0}'.format(i))

    for p in pool:
        jobs.put(None)

    for p in pool:
        p.join()

    while not results.empty():
        ip = results.get()
        list = list.append(ip)
    return list

def getServiceListOutput():
    servicesList = []
    tree = ET.parse('temp.xml')
    root = tree.getroot()
    for item in list(root):
        if item.tag == 'host':
            for child in list(item):
                if child.tag == 'ports':
                    for port in list(child):
                        if port.tag == 'port':
                            for service in list(port):
                                if service.tag == 'service':
                                    try:
                                        servicesList.append(service.attrib['product'] + ' ' + service.attrib['version'])
                                    except KeyError:
                                        pass
    return servicesList 

def nmapScan(ipList):
    #nmap scan all active IPs
    #add nmap scans in md format to md report, create a section for each IP
    print("Nmap scan started")
    for ip in ipList:
        cmd = "nmap -sV -sC -T4 -oX temp.xml " + ip
        os.system(cmd)
        print("Nmap scan for " + ip + " complete")    
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        notesFile.write("\n##" + ip + "\n")
        with open("temp.md") as f:
            for line in f:
                notesFile.write(line)
        notesFile.close()
        listOfServices = getServiceListOutput()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")
    print("Nmap scan complete")
    return listOfServices

class ContentCallback:
    def __init__(self):
        self.contents = ''

    def content_callback(self, buf):
        self.contents = self.contents + str(buf)

def searchExploitDB(services):
    #do exploit db search for all services and version numbers running on machines
    notesFile = open("notes.md", "a")
    notesFile.write("<br>\n##Exploits found: ")
    notesFile.close()
    for service in services:
        try:
            query = service + ' ' + 'site:https://www.exploit-db.com'
            for data in  search(query, tld="com", num=10, start=0, stop=25, pause=2):
                if "https://www.exploit-db.com/exploits" in data:
                    t = ContentCallback()
                    curlObj = pycurl.Curl()
                    curlObj.setopt(curlObj.URL, '{}'.format(data))
                    curlObj.setopt(curlObj.WRITEFUNCTION, t.content_callback)
                    curlObj.perform()
                    curlObj.close()
                    #url = data 
                    soup = BeautifulSoup(t.contents,'lxml')
                    desc = soup.find("meta", property="og:title")
                    publish = soup.find("meta", property="article:published_time")
                    #write results to md file
                    notesFile = open("notes.md", "a")
                    notesFile.write("<br>\n###" + desc.get('content') + "<br>\n")
                    notesFile.write("\n" + publish.get('content') + "<br>\n")
                    notesFile.write("\n" + data + "<br>\n")
                    notesFile.close()

        except:
            print("Error connecting to ExploitDB")
    
def SAMBAcheck(ip):
    #check if samba is running on machine
    if ping_ip(ip):
        cmd = "nmap --script smb-enum-shares.nse,smb-os-discovery.nse,smb-vuln-conficker.nse,smb-vuln-cve2009-3103.nse,smb-vuln-cve-2017-7494.nse,smb-vuln-ms06-025.nse,smb-vuln-ms07-029.nse,smb-vuln-ms08-067.nse,smb-vuln-ms10-054.nse,smb-vuln-ms10-061.nse,smb-vuln-ms17-010.nse,smb-vuln-regsvc-dos.nse,smb-vuln-webexec.nse -p445 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##Samba enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def ftpCheck(ip):
    #check if ftp is running on machine
    if ping_ip(ip):
        cmd = "nmap --script ftp-anon.nse,ftp-banner.nse,ftp-proftpd-backdoor.nse,ftp-vsftpd-backdoor.nse -p21 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##FTP enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def httpCheck(ip):
    #check if http is running on machine
    if ping_ip(ip):
        cmd = "nikto -output temp.xml --host http://" + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        notesFile = open("notes.md", "a")
        notesFile.write("\n##HTTP enumeration: <br>\n")
        with open("temp.xml") as f:
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")

def sshCheck(ip):
    #check if ssh is running on machine
    if ping_ip(ip):
        cmd = "nmap --script ssh2-enum-algos.nse,ssh-hostkey.nse -p22 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##SSH enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def telnetCheck(ip):
    #check if telnet is running on machine
    if ping_ip(ip):
        cmd = "nmap --script telnet-encryption.nse -p23 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##Telnet enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def snmpCheck(ip):
    #check if snmp is running on machine
    if ping_ip(ip):
        cmd = "nmap --script snmp-netstat.nse,snmp-processes.nse,snmp-sysdescr.nse,snmp-win32-services.nse -p161 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##SNMP enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def mysqlCheck(ip):
    #check if mysql is running on machine
    if ping_ip(ip):
        cmd = "nmap --script mysql-enum.nse -p3306 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##MySQL enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def icmpCheck(ip):
    #check if icmp is running on machine
    if ping_ip(ip):
        cmd = "nmap --script icmp-echo.nse -p icmp -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##ICMP enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def smtpCheck(ip):
    #check if smtp is running on machine
    if ping_ip(ip):
        cmd = "nmap --script smtp-commands.nse,smtp-enum-users.nse,smtp-open-relay.nse -p25 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##SMTP enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def dnsCheck(ip):
    #check if dns is running on machine
    if ping_ip(ip):
        cmd = "nmap --script dns-recursion.nse,dns-zone-transfer.nse -p53 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##DNS enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")

def pop3Check(ip):
    #check if pop3 is running on machine
    if ping_ip(ip):
        cmd = "nmap --script pop3-capabilities.nse,pop3-enum-users.nse -p110 -oX temp.xml " + ip
        os.system(cmd)
        #convert to markdown and add to notes file
        cmd = "xsltproc temp.xml -o temp.md"
        os.system(cmd)
        notesFile = open("notes.md", "a")
        with open("temp.md") as f:
            notesFile.write("\n##POP3 enumeration: <br>\n")
            for line in f:
                notesFile.write(line)
        notesFile.close()
        #remove temp files
        os.remove("temp.xml")
        os.remove("temp.md")


    
main()