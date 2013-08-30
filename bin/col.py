import uuid
import json
import time
import subprocess
import libvirt
import random
import os

vmTypes = {}
imageList = {}
actualImageList = []
spec_imageList = {}
clientList = []
freeRAM = {}
activeVMs = []
simpleImageList = []

def createSpecImageList():
    innerList = []
    counter = 1
    global actualImageList
    for i in actualImageList:
        #print i
        x = {counter: i.split('/')[-1]}
        innerList.append(x)
        counter += 1
    #print innerList
    global spec_imageList
    spec_imageList = {"images":innerList}
    #print x
    #print type(x)

def getImages(imageStr):
    imageStr = imageStr.split('\r\n')
    imageStr = [i for i in imageStr if i is not '']

    global simpleImageList
    global actualImageList

    simpleImageList = [i for i in imageStr]
    actualImageList = [i.split(':')[1] for i in imageStr]

    #print actualImageList
    #print simpleImageList
 
    for i in imageStr:
        temp = i.split('/')[-1]
        global imageList
        imageList[temp] = i
    #print imageList
    createSpecImageList()

def getPMs(PMstr):
    PMstr = PMstr.split('\r\n')
    PMstr = [i for i in PMstr if i is not '']
    global clientList
    clientList = [i for i in PMstr]

def getVMTypes(VMstr):
    global vmTypes
    vmTypes = json.loads(VMstr)
    #print vmTypes

def resourceDiscovery():
    for i in clientList:
        print "Detecting resources for %s"%(i,)
        p = subprocess.Popen(["./bin/freeMem", i], shell=False, stdout=subprocess.PIPE)
        #time.sleep(1)
        ram = ''
        while ram == '':
            ram = p.stdout.read()
        ram = int(ram)
        ram = int(ram/1024.0)
        # ram -= 200
        print "%d MB available"%(ram,)
        freeRAM[i] = ram
    #print freeRAM
def getBit(host):
    cmd = ["ssh", host, "getconf", "LONG_BIT"]
    p = subprocess.Popen(["./bin/getBit", host], shell=False, stdout=subprocess.PIPE)
    bit = ''
    while bit == '':
        bit = p.stdout.read()
    #print bit
    bit = int(bit)
    return bit
def createVM(vmInfo):
    free = -1

    images = [i.split('/')[-1] for i in simpleImageList]
    image = images[vmInfo['image_id']-1]

    image = image.split('.')
    image = image[:-1]
    image = ''.join(image)
    imageBit = 32
    if image.endswith('_64'):
        imageBit = 64
    #print imageBit
    vmType = None
    for i in vmTypes["types"]:
        if vmInfo['instance_type'] == i['tid']:
            vmType = i
    print vmType
    target_instance_type = vmInfo['instance_type']

    for i in range(len(clientList)):
        free = freeRAM[clientList[i]]
        bit = getBit(clientList[i])
        if bit == 32 and imageBit == 64:
            free = -1
        if free > vmType['ram']:
            break
    if free == -1:
        return 1
    clientID = i+1
    
    print "Selected machine: %s"%(clientList[i],)
    targetMachine = clientList[i]

    # got machine, create xml, copy vmImage to machine, define VM
    mac = [random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff) ]
    macID =  ':'.join(map(lambda x: "%02x" % x, mac))

    target = {}

    target['name'] = vmInfo['name']
    target['uuid'] = str(uuid.uuid4())
    target['memm'] = str(int(vmType['ram'])*1024)
    target['emul'] = '/usr/bin/qemu-system-i386' if imageBit == 32 else '/usr/bin/qemu-system-x86_64'
    target['vcpu'] = vmType['cpu']
    target['arch'] = 'x86_64' if bit == 64 else 'i686'
    target['path'] = ""
    target['macc'] = macID
    target['inid'] = target_instance_type

    ######################

    imageName = simpleImageList[vmInfo['image_id']-1]
    imageName = imageName.split('/')[-1]
    imageName = imageName.split('.')
    imgName = ''.join(imageName[:-1])
    imgExt = imageName[-1]

    finalPath = "/vm/" + imgName + "_" + target['uuid'] + "." + imgExt

    #print "---", finalPath, "---"

    target['path'] = finalPath


    ######################

    sPath = simpleImageList[vmInfo['image_id']-1]
    #print sPath
    #print target 
    #print vmInfo
    #print targetMachine
    cmd = "scp "+sPath+" ."#+targetMachine+":"+target['path']
    fName = sPath.split('/')[-1]
    cmd_final = "scp "+fName+" "+targetMachine+":"+target['path']
    cmd2 = "ssh "+targetMachine+" \"mkdir -p /vm\""
    print cmd
    print cmd2
    print cmd_final
    os.system(cmd2)
    os.system(cmd)
    os.system(cmd_final)

    #######################
#   """
    # CreateXML
    xml = open('./bin/actual_ref.xml', 'r').read()
    xml = xml % (target['name'], target['uuid'], target['memm'], target['memm'], target['vcpu'], target['arch'], target['emul'], target['path'], target['macc'])
    # print xml
    #qemu+ssh://user@host/system
    connDest = "qemu+ssh://"+targetMachine+"/system"
    conn = libvirt.open(connDest)
    conn.defineXML(xml)
    vm = conn.lookupByName(target['name'])
    vm.create()
    returnID = vm.ID()
    conn.close()

    freeRAM[clientList[clientID-1]] -= (int(target['memm'])/1024.0)

    target['tid'] = clientID*1000 + returnID

    global activeVMs

    activeVMs.append(target)

    return clientID*1000+returnID # """
def queryVM(vmID):
    #pmID = vmID / 1000
    #vmID = vmID % 1000
    response = {}
    #print activeVMs
    for i in activeVMs:
        if i['tid'] == vmID:
            #print "muaah"
            response['pmid'] = vmID / 1000
            response['name'] = i['name']
            response['vmid'] = vmID
            response['instance_type'] = i['inid']
    return response
    
def destroyVM(vmID):
    backup_vmID = vmID
    pmID = vmID / 1000
    vmID = vmID % 1000
    pmID -= 1
    #print pmID, vmID
    global clientList
    client = clientList[pmID]
    #print client
    conn = libvirt.open("qemu+ssh://"+client+"/system")
    try:    
        domain = conn.lookupByID(vmID)
        retVal = domain.destroy()
    except libvirt.libvirtError:
        conn.close()
        return 0
    domain.undefine()
    conn.close()
    global activeVMs
    #print activeVMs
    #for i in activeVMs:
        #print '----------', i['tid'], vmID
        #if i['tid'] == backup_vmID:
            #print "--------------------------"
            #print "removed"
            #print "---------------------------"
            #activeVMs.remove[i]
    activeVMs = [i for i in activeVMs if i['tid'] != backup_vmID]
    return 1
