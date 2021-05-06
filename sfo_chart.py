import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import argparse
import json
import time
import geojson
from geojson import Feature, Point, FeatureCollection, Polygon
import re
import os
'''from geographiclib.geodesic import Geodesic
import math'''

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
    writeLogs("data saved in: "+file_path+"\n")
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

def checkLastVersion(v):
    if len(v) == 1:
        file_path = "./"
        file_name = v
    else:
        p = os.path.split(v)
        file_path = p[0]
        file_name = p[1]

    print("path: ",file_path,"name : ",file_name)

    file_list = os.listdir(file_path)
    lastUpdateName=''
    lastUpdate=0

    lname=len(file_name)
    for file in file_list:
        if file[0:lname]==file_name:
            try:
                fdate=int(getFileDate(file))
            except:
                writeLogs("ERROR: No date in the name of:"+ file)
                continue
            if fdate>lastUpdate:
                lastUpdate=fdate
                lastUpdateName=file
    if lastUpdate!=0:
        writeLogs('INFO: File used : '+ lastUpdateName +" in :"+file_path)
        return lastUpdateName
    writeLogs('INFO: no file found with the following name: '+file_name+ "in:"+file_path)
    return

def getFileDate(name):
    fulldate=re.search(r'\d+',name).group()
    return fulldate[0:8]

def getcolor(elem,type): # this function return the defined color that should be applied, or grey (#CBD2D0) if none
    if elem.get('color')!=None:return elem.get('color')
    if type in ['AIRSPACE','Airspace']: return '#CBD2D0'
    if type in ['DESIGNATEDPOINT','DesignatedPoint']: return '#549CE5'
    if type in ['NAVAID','Navaid']: return '#AAB2BA'
    return ''

def getActivity(Airspace): #check the activity Type
    activities=[]
    activations=findAllcheck(Airspace,'aixm:activation/aixm:AirspaceActivation')
    for activation in activations:
        activity=lookup(activation,'activity')
        if activity!='':activities.append(activity)
    return activities

def getElement(feature,allElements,elementsToAdd,doc):
    if len(elementsToAdd)==0:return [] #no element to be added to this chart
    elementForChart=[]
    for element in allElements:
        id=lookup(element, 'identifier')
        allElementTS=findAllcheck(element,'aixm:timeSlice/aixm:'+feature+'TimeSlice')
        for elementTS in allElementTS:
            designator=lookup(elementTS,'designator')
            type=lookup(elementTS,'type')
            for elementToAdd in elementsToAdd:
                if elementToAdd['type'] == type or elementToAdd['type'] =='': #if type='', it means that any type should be taken into consideration
                    if elementToAdd.get('activity')!=None:#for airspaces, an activity type could be define
                        if elementToAdd['activity'] not in getActivity(elementTS):
                            continue#if the activity does not correspond to the define one, ignore this element
                    if isinstance(elementToAdd['name'],str) and elementToAdd['name'] in designator: #if only one string is defined, we check if the designator contain this string
                        elementForChart.append({"name":designator,"featureType":feature,"type":type,'referencedoc':doc,'ref_uid':id,'color':getcolor(elementToAdd,feature)})
                    if isinstance(elementToAdd['name'],list):
                        for elem in elementToAdd['name']:
                            if elem in designator: #if a liste of name is defined, we check if the designator contain any of this string
                                elementForChart.append({"name":designator,"featureType":feature,"type":type,'referencedoc':doc,'ref_uid':id,'color':getcolor(elementToAdd,feature)})
    writeLogs(str(len(elementForChart))+" elements of type "+feature+" added to "+args.sfolayer+".json")
    return elementForChart

def getRoutesID(routes,routeNames):#return a dictionary with for each route id, a route name
    ids={}
    for name in routeNames:
        for route in routes:
            id=lookup(route, 'identifier')
            allrouteTS=findAllcheck(route,'aixm:timeSlice/aixm:RouteTimeSlice')
            for routeTS in allrouteTS:
                if name == lookup(routeTS,'name'):
                    ids[id]=name
    return ids
def showMe(runwayAxisIDs):
    for ra in runwayAxisIDs:
        writeLogs("Key : {} , first_dir : {}, second_dir : {}".format(ra['id'],ra['first_dir'],ra['second_dir']))
    exit()

def getRunwayDirectionID(runwaydirectionsxml,ref):
    for rwydir in runwaydirectionsxml:
        id=lookup(rwydir, 'identifier')
        allrwydirTS=findAllcheck(rwydir, 'aixm:timeSlice/aixm:RunwayDirectionTimeSlice')
        for rwydirTS in allrwydirTS:
            allrwyext=findAllcheck(rwydirTS, 'aixm:extension/cae:RunwayDirectionExtension')
            for rwyext in allrwyext:
                featureCode=lookup(rwyext, 'featureCode')
                if featureCode == ref:
                    return id
    return ''

def getRunwayCentrelinePoint(runwaycentrelinepointsxml,runwaydirid):
    result=[]
    for centrelinePoint in runwaycentrelinepointsxml:
        id=lookup(centrelinePoint, 'identifier')
        allpointTS=findAllcheck(centrelinePoint, 'aixm:timeSlice/aixm:RunwayCentrelinePointTimeSlice')
        for pointTS in allpointTS:
            onrwy=lookupattrib(pointTS,'onRunway',"href")
            role=lookup(pointTS, 'role')
            if runwaydirid in onrwy and role in RWYCENTRELINEPTROLE:
                allpositions=findAllcheck(pointTS, 'aixm:location/aixm:ElevatedPoint')
                for position in allpositions:
                    pos=lookup(position, 'pos')
                    result=[id,pos]
                    return result
    return []

def getSecondAxisPoint(startpos,refpos,len):
    pos=''
    # writeLogs("start position :"+startpos)
    # writeLogs("reference position :"+refpos)
    # start point
    startcoord=startpos.split(" ")
    startlat=float(startcoord[0])
    startlong=float(startcoord[1])
    # reference point
    refcoord=refpos.split(" ")
    reflat=float(refcoord[0])
    reflong=float(refcoord[1])

    geod=Geodesic.WGS84 # define the WGS84 ellipsoid
    # get distance between start and ref points
    distance=geod.Inverse(reflat, reflong, startlat, startlong)
    # get ratio
    ratio=(distance['s12']+(len*1.852e3))/distance['s12']
    # compute second axis point
    l=geod.InverseLine(reflat, reflong, startlat, startlong)
    g=l.Position(ratio * l.s13)
    pos="{:.15f} {:.15f}".format(g['lat2'],g['lon2'])
    return pos

def getRunwayAxisPoints(runwaydirectionsxml,runwaycentrelinepointsxml,elementsToAdd,doc):
    if len(elementsToAdd)==0:return
    elementForChart=[]
    for elementToAdd in elementsToAdd:
        if isinstance(elementToAdd['airport'],str) and isinstance(elementToAdd['axis'], str) and isinstance(elementToAdd['length'], int):
            directions=elementToAdd['axis'].split("_")
        if len(directions) != 2:
            continue
        # get runway directions IDs
        first_rwyref=directions[0]+" "+elementToAdd['airport']
        first_rwydirid=getRunwayDirectionID(runwaydirectionsxml,first_rwyref)
        second_rwyref=directions[1]+" "+elementToAdd['airport']
        second_rwydirid=getRunwayDirectionID(runwaydirectionsxml,second_rwyref)
        # get runway centreline points
        first_rwyref=elementToAdd['airport']+"_"+directions[0]
        second_rwyref=elementToAdd['airport']+"_"+directions[1]
        first_point=getRunwayCentrelinePoint(runwaycentrelinepointsxml,first_rwydirid)
        third_point=getRunwayCentrelinePoint(runwaycentrelinepointsxml,second_rwydirid)
        # compute coordinates
        second_point=getSecondAxisPoint(third_point[1],first_point[1],elementToAdd['length'])
        fourth_point=getSecondAxisPoint(first_point[1],third_point[1],elementToAdd['length'])

        first_points={'name':'START_POINT','featureType':'RunwayCentreLinePoint','referencedoc':doc,'ref_uid':first_point[0]},{'name':'END_POINT','featureType':'Point','coordinates':[fourth_point]}
        elementForChart.append({'name':first_rwyref,'featureType':'RunwayAxis','referencedoc':'','ref_uid':'','color':'#9B59B6','Points':first_points})
        second_points={'name':'START_POINT','featureType':'RunwayCentreLinePoint','referencedoc':doc,'ref_uid':third_point[0]},{'name':'END_POINT','featureType':'Point','coordinates':[second_point]}
        elementForChart.append({'name':second_rwyref,'featureType':'RunwayAxis','referencedoc':'','ref_uid':'','color':'#9B59B6','Points':second_points})
    writeLogs(str(len(elementForChart))+" elements of type RunwayAxis added to "+args.sfolayer+".json")
    return elementForChart

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
            for routeid in routeIDs:
                if routeid in routeref: #this route segment belong to a route that we need to include in the chart
                    startpoint=getPointRefID(segmentTS,"start")#ID of the designated point starting the segment
                    endpoint=getPointRefID(segmentTS,"end")#ID of the designated point ending the segment
                    segmentsforchart.append({'id':id,'route name':routeIDs[routeid],'refstart':startpoint,'refend':endpoint})
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
    segmentname=segment['route name']+' ('+startname+' - '+endname+')'
    startend=[{'name':startname,'featureType':segment['refstart']['type'],'referencedoc':docPoint,'ref_uid':segment['refstart']['id']},{'name':endname,'featureType':segment['refend']['type'],'referencedoc':docPoint,'ref_uid':segment['refend']['id']}]
    elementForChart.append({"name":segmentname,"featureType":'RouteSegment','referencedoc':docSegment,'ref_uid':segment['id'],'color':ROUTE_COLOR,"Points":startend})
    return elementForChart


def getRouteSegment(routesxml,routesegmentsxml,pointsxml,navaidsxml,routetoadd,docSegment,docPoint):
    if len(routetoadd)==0:return []
    elementForChart=[]
    routesID=getRoutesID(routesxml,routetoadd)#list of all the ID of the route to be displayed on the chart
    segmentsRef=getSegmentRefRoute(routesegmentsxml,routesID)#liste of the segment referencing those routes ID
    for segment in segmentsRef:
        startname=getPointName(segment['refstart'],pointsxml,navaidsxml)
        endname=getPointName(segment['refend'],pointsxml,navaidsxml)
        elementForChart=addSegment(elementForChart,segment,startname,endname,docSegment,docPoint)
    writeLogs(str(len(elementForChart))+" elements of type route segment added to "+args.sfolayer+".json")

    return elementForChart

def chartDefinition(airspaces,navaids,points,routesegments,routes,chartIn,chartConf):
    writeLogs("starting to collect the element to add to the .json for: "+chartIn['NAME'])
    airspaceForChart=getElement("Airspace",airspaces,chartIn['AIRSPACE'],'Airspace_NoRefGeoborder.xml')
    designatedPointForChart=getElement("DesignatedPoint",points,chartIn['POINT'],'DesignatedPoint_Navaid.xml')
    navaidForChart=getElement("Navaid",navaids,chartIn['NAVAID'],'DesignatedPoint_Navaid.xml')
    routesegmentForChart=getRouteSegment(routes,routesegments,points,navaids,chartIn['ROUTE'],'RouteSegment.xml','DesignatedPoint_Navaid.xml')
    runwaycentrelinepointForChart=getRunwayAxisPoints(runwaydirections,runwaycentrelinepoints,chartIn['RWYAXIS'],'RunwayCentrelinePoint.xml')


    elements=airspaceForChart+navaidForChart+designatedPointForChart+routesegmentForChart+runwaycentrelinepointForChart#list of elements contained in chartConf
    chartConf["sfo Layers"].append({"chartname":chartIn['NAME'], "elements":elements})
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
    #the subtype is the last string,some time indicated into ()
    try:
        fc=geojsonfc.split(' ')
        subtype=str(fc[len(fc)-1])
        if subtype[0]=="(":subtype=subtype[1:] #remove the () if any
        if subtype[-1]==")":subtype=subtype[:-1]
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

def insertGeojson(out,geometry, type,subtype,name,id,color):
    properties={"uid":id,"feature type":type,"type":subtype,"name":name,"color":color}
    feature=Feature(geometry=geometry,properties=properties)
    out["features"].append(Feature(geometry=geometry,properties=properties))
    return

def getFeatureGeojson(elementsDict,geojsonIn,geojsonOut,chartname):
    nb=0#count the number of element added
    if len(elementsDict)==0:return #no element to be added to this geojson
    featurescol=readGeojson(geojsonIn)
    for feature in featurescol["features"]:
        featureCode=feature['properties']['featureCode']
        featureType=getFeatureType(feature['properties']['dataType'])
        if featureType in ["AIRSPACE","DESIGNATEDPOINT","NAVAID"]:
            featureSubType=getFeatureSubType(featureCode)
        else: continue #in case the feature is another type (for exemple DME or GEOBORDDER) we do not add it
        featureName=getFeatureName(featureCode)
        featureID=feature['properties']["identifier"]['value']

        for element in elementsDict: #check if the feature is part of the list of element to be added in the chart
            if element['type'] == featureSubType or element['type'] =='': #if type='', it means that any type should be taken into consideration
                if isinstance(element['name'],str):#if the name is a string, just check if it is contained in the feauture code
                    if element['name'] in featureName:
                        insertGeojson(geojsonOut,feature['geometry'],featureType,featureSubType,featureName,featureID,getcolor(element,featureType))
                        nb+=1
                    continue
                if isinstance(element['name'],list):#if the name is a list of name, I need to check if any of them is contained into the feature featureCode
                    for name in element['name']:
                        if name in featureName:
                            insertGeojson(geojsonOut,feature['geometry'],featureType,featureSubType,featureName,featureID,getcolor(element,featureType))
                            nb+=1
                        continue
                    continue
                else:
                    writeLogs("The attribute name of "+element[name]+" should be a string or a list")
    writeLogs(str(nb)+" elements of type "+featureType+" added to "+chartname+".geojson")
    return

def getRouteGeojson(routesDict,geojsonIn,geojsonOut,chartname):
    nb=0#count the number of element added
    if len(routesDict)==0:return #no element to be added to this geojson
    featurescol=readGeojson(geojsonIn)
    for feature in featurescol["features"]:
        featureCode=feature['properties']['featureCode']
        featureRouteName=getFeatureName(featureCode)
        featureType=getFeatureType(feature['properties']['dataType'])
        featureID=feature['properties']["identifier"]['value']

        for route in routesDict: #check if the feature is part of the list of element to be added in the chart
            if route == featureRouteName:
                insertGeojson(geojsonOut,feature['geometry'],featureType,'',featureCode,featureID,ROUTE_COLOR)
                nb+=1
    writeLogs(str(nb)+" elements of type "+featureType+" added to "+chartname+".geojson")
    return

def chartGeojson(airspaceGeojson,navaidGeojson,designatedpointGeojson,RouteSegmentGesojson,chartIn):
    writeLogs("Start to collect the element to create: "+chartIn['NAME']+".geojson")
    chartGeojson=FeatureCollection([]) #geojson for this chart
    getFeatureGeojson(chartIn['AIRSPACE'],airspaceGeojson,chartGeojson,chartIn['NAME'])
    getFeatureGeojson(chartIn['POINT'],designatedpointGeojson,chartGeojson,chartIn['NAME'])
    getFeatureGeojson(chartIn['NAVAID'],navaidGeojson,chartGeojson,chartIn['NAME'])
    getRouteGeojson(chartIn['ROUTE'],RouteSegmentGesojson,chartGeojson,chartIn['NAME'])
    savegeojson(chartGeojson,chartIn['NAME'])
    return

#########GLOBAL VARIABLE########################################
AIXM_NAMESPACE={'aixm-message':'http://www.aixm.aero/schema/5.1/message','aixm':"http://www.aixm.aero/schema/5.1",'gml':"http://www.opengis.net/gml/3.2",'xlink':"http://www.w3.org/1999/xlink"}
ROUTE_COLOR='#3D5B74'

######### ZRH Lower Chart ##############
ZRH_LOWER={}
ZRH_LOWER['NAME']="ZRH Lower Chart" #name that will appears on the App
ZRH_LOWER['NAVAID']=[{"type":"VOR","name":''},{"type":"DME","name":''},{"type":"NDB","name":''},{"type":"VOR_DME","name":''},{"type":"VORTAC","name":''}] #Navaid that will be displayed
ZRH_LOWER['POINT']=[{"type":"ICAO","name":''}]#designated point to be displayed. '' means all
ZRH_LOWER['ROUTE']=["L613","W112","Z119","Z83"]#route that should be displayed
ZRH_LOWER['AIRSPACE']=[{"type":"SECTOR","name":["NORTH","EAST","WEST","SOUTH"]}] #airspace to be displayed. No name means all Airspace of this type

######### ZRH Upper Chart ##############
ZRH_UPPER={}
ZRH_UPPER['NAME']="ZRH Upper Chart" #name that will appears on the App
ZRH_UPPER['NAVAID']=[{"type":"VOR","name":''},{"type":"DME","name":''},{"type":"NDB","name":''},{"type":"VOR_DME","name":''},{"type":"VORTAC","name":''}] #Navaid that will be displayed
ZRH_UPPER['POINT']=[{"type":"ICAO","name":''}]#designated point to be displayed. '' means all
ZRH_UPPER['ROUTE']=["UL613","UP131","Z119","UZ6113","UZ630"]#route that should be displayed
ZRH_UPPER['AIRSPACE']=[{"type":"SECTOR","name":["M2","M1"],"color":"#79B8A9"}] #airspace to be displayed. No name means all Airspace of this type

######### GVA Lower Chart ##############
GVA_LOWER={}
GVA_LOWER['NAME']="GVA Lower Chart" #name that will appears on the App
GVA_LOWER['NAVAID']=[{"type":"VOR","name":''},{"type":"DME","name":''},{"type":"NDB","name":''},{"type":"VOR_DME","name":''},{"type":"VORTAC","name":''}] #Navaid that will be displayed
GVA_LOWER['POINT']=[{"type":"ICAO","name":''}]#designated point to be displayed. '' means all
GVA_LOWER['ROUTE']=[]#route that should be displayed
GVA_LOWER['AIRSPACE']=[{"type":"SECTOR","name":["L1"],"color":"#79B8A9"},{"type":"AWY","name":''},{"type":"CTR","name":''},{"type":"TMA","name":"LS"}] #airspace to be displayed. No name means all Airspace of this type

######### GVA Upper Chart ##############
GVA_UPPER={}
GVA_UPPER['NAME']="GVA Upper Chart" #name that will appears on the App
GVA_UPPER['NAVAID']=[{"type":"VOR","name":''},{"type":"DME","name":''},{"type":"NDB","name":''},{"type":"VOR_DME","name":''},{"type":"VORTAC","name":''}] #Navaid that will be displayed
GVA_UPPER['POINT']=[{"type":"ICAO","name":''}]#designated point to be displayed. '' means all
GVA_UPPER['ROUTE']=['UN852','UN853','UL153','UN869','UN871','UM729','UM135','UM730','Y24','UP860','UT45','UL612','UM975']#route that should be displayed
GVA_UPPER['AIRSPACE']=[{"type":"SECTOR","name":["L1"],"color":"#79B8A9"},{"type":"AWY","name":''},{"type":"CTR","name":''},{"type":"TMA","name":"LS"} ] #airspace to be displayed. No name means all Airspace of this type

######### TWR/APP Chart ##############
TWR_APP={}
TWR_APP['NAME']="TWR APP Chart" #name that will appears on the App
TWR_APP['NAVAID']=[{"type":"VOR","name":''},{"type":"DME","name":''},{"type":"NDB","name":''},{"type":"VOR_DME","name":''},{"type":"VORTAC","name":''}] #Navaid that will be displayed
TWR_APP['POINT']=[{"type":"ICAO","name":''},{"type":"OTHER:VFR_REP","name":'','color':"#67E175"}]#designated point to be displayed. '' means all
TWR_APP['ROUTE']=[]#route that should be displayed
TWR_APP['AIRSPACE']=[{"type":"SECTOR","name":'LSZH',"color":"#79B8A9"},{"type":"AWY","name":''},{"type":"CTR","name":''},{"type":"TMA","name":"LS"},{"type":"R","name":'','color':'#909491','activity':'GLIDING'} ] #airspace to be displayed. No name means all Airspace of this type
TWR_APP['RWYAXIS']=[{"airport":"LSGG","axis":"04_22","length":20},{"airport":"LSZH","axis":"10_28","length":20},{"airport":"LSZH","axis":"16_34","length":20},{"airport":"LSZH","axis":"14_32","length":20},{"airport":"LSMD","axis":"11_29","length":10}]

##### list of charts#######
CHART_LIST=[ZRH_LOWER,ZRH_UPPER,GVA_LOWER,GVA_UPPER,TWR_APP]
################################################################
parser = argparse.ArgumentParser()
parser.add_argument('--airspace-path', type=str,  help='path of Airspace file without version nor extension', dest='airspace', default='./Airspace')
parser.add_argument('--routesegment-path', type=str,  help='path of RouteSegment file without version nor extension', dest='routesegment', default='./RouteSegment')
parser.add_argument('--navaid-designatedpoint-path', type=str, help='path of Navaid_DesignatedPoint file without version nor extension', dest='designatedPointNavaid', default='./DesignatedPoint_Navaid')
parser.add_argument('--sfo-layer-path', type=str, help='path of sfos_layer file without version nor extension', dest='sfolayer', default='./SFO_layer')
parser.add_argument('--runwaycentrelinepoint-path', type=str, help='path of RunwayCentrelinePoint file without version nor extension', dest='runwaycentrelinepoint', default='./RunwayCentrePoint')

args = parser.parse_args()
args = parser.parse_args()

#input
routesegmentxml=checkLastVersion(args.routesegment)
airspacexml=checkLastVersion(args.airspace)
pointxml=checkLastVersion(args.designatedPointNavaid)
runwaycentrelinepointxml=checkLastVersion(args.runwaycentrelinepoint)

print('\n')


airspaceGeojson="Airspace.geojson"
designatedpointGeojson="DesignatedPoint.geojson"
navaidGeojson="Navaid.geojson"
RouteSegmentGesojson="RouteSegment.geojson"
#output
#fsfolayer=checkLastVersion(args.sfolayer)

#extract elements from the xml
airspaces=extractFeatureAIXM(airspacexml,"Airspace")
navaids=extractFeatureAIXM(pointxml,"Navaid")
points=extractFeatureAIXM(pointxml,"DesignatedPoint")
routesegments=extractFeatureAIXM(routesegmentxml, "RouteSegment")
routes=extractFeatureAIXM(routesegmentxml, "Route")
runwaydirections=extractFeatureAIXM(runwaycentrelinepointxml, "RunwayDirection")
runwaycentrelinepoints=extractFeatureAIXM(runwaycentrelinepointxml, "RunwayCentrelinePoint")

sfolayer={}
sfolayer["sfo Layers"]=[]
'''for chartdef in CHART_LIST:

    chartGeojson(airspaceGeojson,navaidGeojson,designatedpointGeojson,RouteSegmentGesojson,chartdef)'''

for chartdef in CHART_LIST:

    chartDefinition(airspaces,navaids,points,routesegments,routes,chartdef,sfolayer)
    print('\n')

savejson(sfolayer,args.sfolayer)
writeLogs("File Updated")
writeLogs("Done!")
