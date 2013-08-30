from flask import Flask, jsonify, request, Response
import col
import sys
import libvirt
import json

# XML construction - (name, uuid, memory, vcpu, source file, mac (last 3 octets))

globalImagesList = {'images':[{'id': 100, 'name': 'Chubuntu'}, {'id': 101, 'name': 'Fedora'}]}
app = Flask(__name__)

def parseOpts():
    #pm_file image_file types_file
    #print sys.argv
    with open(sys.argv[1], 'r') as f:
        pm_file = f.read()
        col.getPMs(pm_file)
    with open(sys.argv[2], 'r') as g:
        image_file = g.read()
        col.getImages(image_file)
    with open(sys.argv[3], 'r') as h:
        vmTypes_str = h.read()
        #print vmTypes_str
        col.getVMTypes(vmTypes_str)

# create?name=test_vm&instance_type=type&image_id=id
@app.route("/vm/create")
def createVM():
    vmInfo = {'name': request.args.get('name'), 'instance_type': int(request.args.get('instance_type')), 'image_id': (int(request.args.get('image_id')))}
    retVal = col.createVM(vmInfo)
    if retVal == 1:
        return jsonify({'vmid': 0})
    return jsonify({'vmid': retVal})

@app.route("/vm/query")
def queryVM():
    vmID = int(request.args.get('vmid'))
    retVal = col.queryVM(vmID)
    return jsonify(retVal)

@app.route("/vm/destroy")
def destroyVM():
    vmID = int(request.args.get('vmid'))
    retVal = col.destroyVM(vmID)
    return jsonify({'status':retVal})

@app.route("/vm/types")
def listTypes():
    return jsonify(col.vmTypes)

@app.route("/image/list")
def listImages():
    #return Response(json.dumps(col.spec_imageList), mimetype='application/json')
    return jsonify(col.spec_imageList)

if __name__ == '__main__':
    app.debug = True
    parseOpts()
    col.resourceDiscovery()
    app.run()
