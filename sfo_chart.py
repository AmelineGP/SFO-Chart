import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import argparse
import json
import time
import geojson
from geojson import Feature, Point, FeatureCollection, Polygon
import re

def writeLogs(line):
    print(line)
    file='logs_'+time.strftime("%Y%m%d")
    f=open(file,'a')
    if f.mode=="a":
        f.write(time.strftime("%Y%m%d%H%M%S")+' '+line+"\n")
    return

def savejson(data, file_path):
    complete_path=file_path + '_'+time.strftime("%Y%m%d")+".json"
    writejson(data,complete_path)
    return

def savegeojson(data, file_path):
    complete_path=file_path + '_'+time.strftime("%Y%m%d")+".geojson"
    writejson(data,complete_path)
    return

def writejson(data,file_path):
    str_data = open(file_path,'w')
    json.dump(data, str_data, indent=1)
    return

def lookup(complex_element,key):
    for element in complex_element:
        if element.tag == key:
            return element.text
    #in case one of the namespace is used, we should look for the key + namespace
    for ns in AIXM_NAMESPACE.values():
        for element in complex_element:
            if element.tag == "{"+ns+"}"+key:
                return element.text
    return ''

def lookupattrib(complex_element,key,keyattribute):
    for element in complex_element:
        if element.tag == key:
            return element.attrib[keyattribute]
    #in case one of the namespace is used, we should look for the key + namespace
    for ns in AIXM_NAMESPACE.values():
        for element in complex_element:
            if element.tag == "{"+ns+"}"+key:
                if keyattribute in element.attrib:
                    return element.attrib[keyattribute]
                for ns in AIXM_NAMESPACE.values():#in case one of the namespace is used, we should look for the keyattribute + namespace
                    if "{"+ns+"}"+keyattribute in element.attrib:
                        return element.attrib["{"+ns+"}"+keyattribute]
    return ''

def findAllcheck(tree,path):
    try:
        elements = tree.findall(path,AIXM_NAMESPACE)
    except:
        writeLogs("ERROR: impossible to parse the path "+path+ " with the namespaces "+AIXM_NAMESPACE)
        return None
    if elements== []:
        writeLogs("there is no Element  with the tag "+path)

    return elements

def extractFeatureAIXM(fxml,featureType): #return all the feature of this feature type as a liste
    elements=[]
    elementTree = ET.parse(fxml)
    elements = findAllcheck(elementTree,'aixm-message:hasMember/aixm:'+featureType)
    return elements

'''def addAirspaces(allAirspaces,airspacesToAdd,airspaceForChart,geojson):
    if len(airspacesToAdd)==0:return #no Airspaces to be added to this chart
    for airspace in allAirspaces:
        id=lookup(airspace, 'identifier')#airspace uuid
        allAirspacesTS=findAllcheck(airspace,'aixm:timeSlice/aixm:AirspaceTimeSlice')
        for airspaceTS in allAirspacesTS:
            designator=lookup(airspaceTS,'designator')#airspace code
            type=lookup(airspaceTS,'type')#airspace Type
            for airspaceToAdd in airspacesToAdd:
                if airspaceToAdd['type']==type and airspaceToAdd['name'] in designator:
                    airspaceForChart.append({"name":designator,"featureType":"airspace","type":type,'referencedoc':"Airspace_NoRefGeoborder.xml",'ref_uid':id})
    return airspaceForChart'''


def getElement(feature,allElements,elementsToAdd,doc):
    if len(elementsToAdd)==0:return #no element to be added to this chart
    elementForChart=[]
    for element in allElements:
        id=lookup(element, 'identifier')
        allElementTS=findAllcheck(element,'aixm:timeSlice/aixm:'+feature+'TimeSlice')
        for elementTS in allElementTS:
            designator=lookup(elementTS,'designator')
            type=lookup(elementTS,'type')
            for elementToAdd in elementsToAdd:
                if elementToAdd['type'] in type:
                    if isinstance(elementToAdd['name'],str) and elementToAdd['name'] in designator: #if only one string is defined, we check if the designator contain this string
                        elementForChart.append({"name":designator,"featureType":feature,"type":type,'referencedoc':doc,'ref_uid':id})
                    if isinstance(elementToAdd['name'],list) and designator in elementToAdd['name']: #if a lsite of name is defined, we check if the designator is part of this liste
                        elementForChart.append({"name":designator,"featureType":feature,"type":type,'referencedoc':doc,'ref_uid':id})

    return elementForChart

def getRoutesID(routes,routeNames):
    ids={}
    for route in routes:
        id=lookup(route, 'identifier')
        allrouteTS=findAllcheck(route,'aixm:timeSlice/aixm:RouteTimeSlice')
        for routeTS in allrouteTS:
            for name in routeNames:
                if name == lookup(routeTS,'name'):
                    ids[name]=id
                continue
    return ids

def getPointRefID(segment,startorend):
    point=segment.find('aixm:'+startorend+'/aixm:EnRouteSegmentPoint',AIXM_NAMESPACE)
    pointid=lookupattrib(point,'pointChoice_fixDesignatedPoint',"href")
    if pointid!='': #the start or end of the segment is a designatedpoint
     return {'type':"DesignatedPoint",'id':pointid[9:]} #remove "urn:uuid:" from the id
    pointid=lookupattrib(point,'pointChoice_navaidSystem','href')
    if pointid!='': #the start or end of the segment is a Navaid
     return {'type':"Navaid",'id':pointid[9:]}
    return ''

def getSegmentRefRoute(segmentsxml,routeIDs):
    segmentsforchart=[]
    for segment in segmentsxml:
        id=lookup(segment,'identifier')
        allsegmentTS=findAllcheck(segment,'aixm:timeSlice/aixm:RouteSegmentTimeSlice')
        for segmentTS in allsegmentTS:
            routeref=lookupattrib(segmentTS,'routeFormed',"href")
            for route in routeIDs:
                if routeIDs[route] in routeref: #this route segment belong to a route that we need to include in the chart
                    startpoint=getPointRefID(segmentTS,"start")#ID of the designated point starting the segment
                    endpoint=getPointRefID(segmentTS,"end")#ID of the designated point ending the segment
                    segmentsforchart.append({'id':id,'route name':route,'refstart':startpoint,'refend':endpoint})
                continue
    return segmentsforchart

def getPointName(point,pointsxml,navaidsxml):
    if point['type']=="DesignatedPoint":
        for dpoint in pointsxml:
            if point['id']==lookup(dpoint,'identifier'):
                pointTS=dpoint.find('aixm:timeSlice/aixm:DesignatedPointTimeSlice',AIXM_NAMESPACE)
    if point['type']=="Navaid":
        for navaid in navaidsxml:
            if point['id']==lookup(navaid,'identifier'):
                pointTS=navaid.find('aixm:timeSlice/aixm:NavaidTimeSlice',AIXM_NAMESPACE)
    return lookup(pointTS,'designator')

def addSegment(elementForChart,segment,startname,endname,docSegment,docPoint):
    segmentname=segment['route name']+' ('+startname+' - '+endname+' )'
    startend=[{'name':startname,'featureType':segment['refstart']['type'],'referencedoc':docPoint,'ref_uid':segment['refstart']['id']},{'name':endname,'featureType':segment['refend']['type'],'referencedoc':docPoint,'ref_uid':segment['refend']['id']}]
    elementForChart.append({"name":segmentname,"featureType":'RouteSegment','referencedoc':docSegment,'ref_uid':segment['id'],"Points":startend})
    return elementForChart


def getRouteSegment(routesxml,routesegmentsxml,pointsxml,navaidsxml,routetoadd,docSegment,docPoint):
    if len(routetoadd)==0:return
    elementForChart=[]
    routesID=getRoutesID(routesxml,routetoadd)#list of all the ID of the route to be displayed on the chart
    segmentsRef=getSegmentRefRoute(routesegmentsxml,routesID)#liste of the segment referencing those routes ID
    for segment in segmentsRef:
        startname=getPointName(segment['refstart'],pointsxml,navaidsxml)
        endname=getPointName(segment['refend'],pointsxml,navaidsxml)
        elementForChart=addSegment(elementForChart,segment,startname,endname,docSegment,docPoint)


    return elementForChart

def chartDefinition(airspaces,navaids,points,routesegments,routes,chartIn,chartConf):
    airspaceForChart=getElement("Airspace",airspaces,chartIn['AIRSPACE'],'Airspace_NoRefGeoborder.xml')
    navaidForChart=getElement("Navaid",navaids,chartIn['NAVAID'],'DesignatedPoint_Navaid.xml')
    designatedPointForChart=getElement("DesignatedPoint",points,chartIn['POINT'],'DesignatedPoint_Navaid.xml')
    routesegmentForChart=getRouteSegment(routes,routesegments,points,navaids,chartIn['ROUTE'],'RouteSegment.xml','DesignatedPoint_Navaid.xml')


    elements=airspaceForChart+navaidForChart+designatedPointForChart+routesegmentForChart#list of elements contained in chartConf
    chartConf["Global Layers"].append({"chartname":chartIn['NAME'], "elements":elements})
    return

def readGeojson(fgeojson):
    data=open(fgeojson,'r')
    return geojson.load(data)

def getFeatureType(geojsontype):#the type is indicated in the Type data as ""<feauretype>TYPE"
    try:
        type=re.search('(.*)%s' % ("TYPE"),geojsontype).group(1)
    except:
        writeLogs("Can't find type in: "+ geojsontype)
        return
    return type

def getFeatureSubType(geojsonfc):
    #the subtype is the last string indicated into ()
    try:
        fc=geojsonfc.split(' ')
        subtype=str(fc[len(fc)-1])
        subtype=subtype[1:-1]
    except:
        writeLogs("Can't find subtype in: "+ geojsonfc)
        return ''
    return subtype

def getFeatureName(geojsonfc):
    #the name is the first string in the feature code
    try:
        fc=geojsonfc.split(' ')
        name=fc[0]
    except:
        writeLogs("Can't find name in: "+ geojsonfc)
        return '',''
    return name

def insertGeojson(out,geometry, type,subtype,name,id):
    properties=[{"uid":id,"feature type":type,"type":subtype,"name":name}]
    feature=Feature(geometry=geometry,properties=properties)
    out["features"].append(Feature(geometry=geometry,properties=properties))
    return

def getFeatureGeojson(elementsDict,geojsonIn,geojsonOut):
    if len(elementsDict)==0:return #no element to be added to this geojson
    featurescol=readGeojson(geojsonIn)
    for feature in featurescol["features"]:
        featureCode=feature['properties']['featureCode']
        featureType=getFeatureType(feature['properties']['dataType'])
        featureSubType=getFeatureSubType(featureCode)
        featureName=getFeatureName(featureCode)
        featureID=feature['properties']["identifier"]['value']

        for element in elementsDict: #check if the feature is part of the list of element to be added in the chart
            if element['type'] in featureSubType: #check that the type of element is mentionned in the
                if isinstance(element['name'],str):#if the name is a string, just check if it is contained in the feauture code
                    if element['name'] in featureName:
                        insertGeojson(geojsonOut,feature['geometry'],featureType,featureSubType,featureName,featureID)
                    continue
                if isinstance(element['name'],list):#if the name is a list of name, I need to check if any of them is contained into the feature featureCode
                    for name in element['name']:
                        if name in featureName:
                            insertGeojson(geojsonOut,feature['geometry'],featureType,featureSubType,featureName,featureID)
                            continue
                    continue
                else:
                    writeLogs("The attribute name of "+element[name]+" should be a string or a list")
    return

def getRouteGeojson(routesDict,geojsonIn,geojsonOut):
    if len(routesDict)==0:return #no element to be added to this geojson
    featurescol=readGeojson(geojsonIn)
    for feature in featurescol["features"]:
        featureCode=feature['properties']['featureCode']
        featureRouteName=getFeatureName(featureCode)
        featureType=getFeatureType(feature['properties']['dataType'])
        featureID=feature['properties']["identifier"]['value']

        for route in routesDict: #check if the feature is part of the list of element to be added in the chart
            if route == featureRouteName:
                insertGeojson(geojsonOut,feature['geometry'],featureType,'',featureCode,featureID)
    return

def chartGeojson(airspaceGeojson,navaidGeojson,designatedpointGeojson,RouteSegmentGesojson,chartIn):
    chartGeojson=FeatureCollection([]) #geojson for this chart
    getFeatureGeojson(chartIn['AIRSPACE'],airspaceGeojson,chartGeojson)
    getFeatureGeojson(chartIn['POINT'],designatedpointGeojson,chartGeojson)
    getFeatureGeojson(chartIn['NAVAID'],navaidGeojson,chartGeojson)
    getRouteGeojson(chartIn['ROUTE'],RouteSegmentGesojson,chartGeojson)
    savegeojson(chartGeojson,chartIn['NAME'])
    return



#########GLOBAL VARIABLE########################################
AIXM_NAMESPACE={'aixm-message':'http://www.aixm.aero/schema/5.1/message','aixm':"http://www.aixm.aero/schema/5.1",'gml':"http://www.opengis.net/gml/3.2",'xlink':"http://www.w3.org/1999/xlink"}
######### ZRH Lower Chart ##############
ZRH_LOWER={}
ZRH_LOWER['NAME']="ZRH Lower Chart" #name that will appears on the App
ZRH_LOWER['NAVAID']=[{"type":"","name":["PAS","SPR","FRI","LPS","WIL","ALG","SUL","ZUE","HOC","TRA","GLA","SPR","GVA","BLM","KPT"]}] #Navaid that will be displayed
ZRH_LOWER['POINT']=[{"type":"ICAO","name":''}]#designated point to be displayed. '' means all
ZRH_LOWER['ROUTE']=["L613","W112","Z119","Z83"]#route that should be displayed
ZRH_LOWER['AIRSPACE']=[{"type":"SECTOR","name":"LSZH"},{"type":"AWY","name":''}] #airspace to be displayed. No name means all Airspace of this type


################################################################
parser = argparse.ArgumentParser()
parser.add_argument('--airspace-path', type=str,  help='path of Airspace file without version nor extension', dest='airspace', default='./Airspace')
parser.add_argument('--routesegment-path', type=str,  help='path of RouteSegment file without version nor extension', dest='routesegment', default='./RouteSegment')
parser.add_argument('--navaid-designatedpoint-path', type=str, help='path of Navaid_DesignatedPoint file without version nor extension', dest='navaidDesignatedPoint', default='./Navaid_DesignatedPoint')
parser.add_argument('--globals-layer-path', type=str, help='path of Globals_layer file without version nor extension', dest='globalslayer', default='./Globals_layer')

args = parser.parse_args()

#input
routesegmentxml='RouteSegment_20210331.xml'#checkLastVersion(args.routesegment)
airspacexml='Airspace_NoRefGeoborder_20201231.xml'#checkLastVersion(args.airspace)
pointxml='DesignatedPoint_Navaid_20210329.xml'#checkLastVersion(args.navaidDesignatedPoint)
routesegmentxml="RouteSegment_20210331.xml"

airspaceGeojson="Airspace.geojson"
designatedpointGeojson="DesignatedPoint.geojson"
navaidGeojson="Navaid.geojson"
RouteSegmentGesojson="RouteSegment.geojson"
#output
#fglobalslayer=checkLastVersion(args.globalslayer)

#extract elements from the xml
airspaces=extractFeatureAIXM(airspacexml,"Airspace")
navaids=extractFeatureAIXM(pointxml,"Navaid")
points=extractFeatureAIXM(pointxml,"DesignatedPoint")
routesegments=extractFeatureAIXM(routesegmentxml, "RouteSegment")
routes=extractFeatureAIXM(routesegmentxml, "Route")

globalslayer={}
globalslayer["Global Layers"]=[]

chartDefinition(airspaces,navaids,points,routesegments,routes,ZRH_LOWER,globalslayer)
chartGeojson(airspaceGeojson,navaidGeojson,designatedpointGeojson,RouteSegmentGesojson,ZRH_LOWER)



savejson(globalslayer,args.globalslayer)
writeLogs("File Updated")
writeLogs("Done!")
