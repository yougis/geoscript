
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterExtent,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsProject,
                       QgsLayout,
                       QgsLayoutItemMap,
                       QgsLayoutSize,
                       QgsGeometry,
                       QgsPoint,
                       QgsPointXY,
                       QgsUnitTypes,
                       QgsLayoutExporter,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorLayer
                       )
import processing, subprocess
from qgis.utils import iface

class MapillaryAlgorithm(QgsProcessingAlgorithm):
    
    LAYER= 'LAYER'
    
    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MapillaryAlgorithm()
    
    def name(self):
        return 'mapillary'
        
    def displayName(self):
        return self.tr('mapillary')
    
    
    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Mapillary')

        
    def groupId(self):
        return 'mapillary script'
    
    
    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Example algorithm short description")

    def initAlgorithm(self, config=None):
        self.addParameter( 
        QgsProcessingParameterVectorLayer(self.LAYER)
        )
    
    
    def processAlgorithm(self, parameters, context, feedback):
        
        wgsCRS= QgsCoordinateReferenceSystem(4326)
        
        p = QgsProject()
        projectCRS = p.instance().crs()
        xform= QgsCoordinateTransform(projectCRS,wgsCRS,p)

        layout = QgsLayout(p)
        layout.initializeDefaults()

        layer = self.parameterAsVectorLayer(parameters,self.LAYER, context)
        return {}

    def getPointFromLayer(self, layer):
        ...