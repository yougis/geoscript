import subprocess

wgsCRS= QgsCoordinateReferenceSystem(4326)
mercator = QgsCoordinateReferenceSystem(3857)
p = QgsProject().instance()
xform= QgsCoordinateTransform(mercator,wgsCRS,p)

path = '/home/yogis/Bureau/'
file = '7052'
ext = '.png'
canvas = iface.mapCanvas()
        # on utilise le param pour que le canvas s'ajuste aux params
        # on export le canvas asImage
canvas.saveAsImage(path+file+ext) # ecraser ?
rect = canvas.extent()
#canvas.zoomToFeatureExtent(rect)
xmin = canvas.extent().xMinimum() # lonMin
ymin = canvas.extent().yMinimum() # latMin
pmin = QgsGeometry(QgsPoint(xmin, ymin))
pmin.transform(xform)
pmin.asPoint().x()
pmin.asPoint().y()

ymax = canvas.extent().yMaximum() # latMax
xmax = canvas.extent().xMaximum() # lonMax
pmax = QgsGeometry(QgsPoint(xmax, ymax))
pmax.transform(xform)
pmax.asPoint().x()
pmax.asPoint().y()    
        
        # run imgKap sur l'image créée avec les params 
        
imgkapCommand =  'imgkap '+ path+file+ext + ' ' + str(pmax.asPoint().y()) + ' ' + str(pmin.asPoint().x())+' ' + str(pmin.asPoint().y())+ ' ' + str(pmax.asPoint().x()) + ' ' + path +file+'.kap'
#commands.getstatusoutput(imgkapCommand)

subprocess.run(imgkapCommand, shell=True)
