# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterDestination)
from qgis import processing


class To8BitsFromStyle(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    MASK = 'MASK'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return To8BitsFromStyle()

    def name(self):
        return 'to8BitsFromStyle'

    def displayName(self):
        return self.tr('To 8 Bits From Style')

    def group(self):
        return self.tr('Satellite')

    def groupId(self):
        return 'satellite'

    def shortHelpString(self):
        return self.tr("Algorithme permettant de transformer un raster en 8 Bits en prenant en compte le style définit dans QGIS")

    def initAlgorithm(self, config=None):
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Couche en entrée')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.MASK,
                self.tr('Zone de découpe'),
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr('Couche en sortie')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        
        apply_mask = True
        
        source = self.parameterAsRasterLayer(
            parameters,
            self.INPUT,
            context
        )
        
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        mask = self.parameterAsVectorLayer(
            parameters,
            self.MASK,
            context
        )
        if mask is None:
            apply_mask = False
        
        min_red = source.renderer().redContrastEnhancement().minimumValue()
        max_red = source.renderer().redContrastEnhancement().maximumValue()
        min_green = source.renderer().greenContrastEnhancement().minimumValue()
        max_green = source.renderer().greenContrastEnhancement().maximumValue()
        min_blue = source.renderer().blueContrastEnhancement().minimumValue()
        max_blue = source.renderer().blueContrastEnhancement().maximumValue()
        
        input = parameters['INPUT']
        if apply_mask :
            clip_result = processing.run(
            'gdal:cliprasterbymasklayer',
            {
                'INPUT': parameters['INPUT'],
                'MASK' : parameters['MASK'],
                'ALPHA_BAND' : True,
                'NODATA' : 0,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            input = clip_result['OUTPUT']
        
        extra_param = '-b 1 -b 2 -b 3 -b 4 -a_nodata none -scale_1 '+str(min_red)+' '+str(max_red)+' -scale_2 '+str(min_green)+' '+str(max_green)+' -scale_3 '+str(min_blue)+' '+str(max_blue)+' -scale_4 0 1 -colorinterp_4 alpha'
        translate_result = processing.run(
            'gdal:translate',
            {
                'INPUT': input,
                'EXTRA': extra_param,
                'DATA_TYPE': 1,
                'OUTPUT': parameters['OUTPUT']
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
        
        return {'OUTPUT': translate_result['OUTPUT']}
