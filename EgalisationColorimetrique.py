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
                       QgsRasterLayer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingOutputBoolean)
from qgis import processing


class EgalisationColorimetrique(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    REFERENCE = 'REFERENCE'
    MASK = 'MASK'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return EgalisationColorimetrique()

    def name(self):
        return 'egalisationColorimetrique'

    def displayName(self):
        return self.tr('Egalisation Colorimetrique')

    def group(self):
        return self.tr('Satellite')

    def groupId(self):
        return 'satellite'

    def shortHelpString(self):
        return self.tr("Algorithme permantant une égalisation colorimétrique par rapport à une image de référence basé sur un 'Histogram Matching'")

    def initAlgorithm(self, config=None):
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Couche en entrée')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.REFERENCE,
                self.tr('Couche de référence')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.MASK,
                self.tr('Zone de travail')
            )
        )
        
        self.addOutput(
            QgsProcessingOutputBoolean(
                'SUCCESS',
                self.tr('Success')
            )
        )

    def computeHistoMatch(self, band, match_provider, ref_provider):
        
        ref_histo = ref_provider.histogram(band,0)
        match_histo = match_provider.histogram(band,0)
        
        ref_cumulhist = [sum(ref_histo.histogramVector[:x+1]) for x in range(len(ref_histo.histogramVector))]
        match_cumulhist = [sum(match_histo.histogramVector[:x+1]) for x in range(len(match_histo.histogramVector))]
        if len(ref_cumulhist) == 0 or len(match_cumulhist) == 0 :
            return (0,0)
            
        ref_nbpix = ref_cumulhist[-1]
        seuil = 0
        for i in ref_cumulhist :
            if i < (ref_nbpix/10) :
                seuil+=1
            else :
                break
            
        ref_seuil_debut=(seuil*100)/len(ref_cumulhist)
        
        seuil = 0
        for i in ref_cumulhist :
            if i < (ref_nbpix - ref_nbpix/10) :
                seuil+=1
            else :
                break
            
        ref_seuil_fin=(seuil*100)/len(ref_cumulhist)
        
        match_nbpix = match_cumulhist[-1]
        seuil = 0
        for i in match_cumulhist :
            if i < (match_nbpix/10) :
                seuil+=1
            else :
                break
            
        match_seuil_debut = seuil
        
        seuil = 0
        for i in match_cumulhist :
            if i < (match_nbpix - match_nbpix/10) :
                seuil+=1
            else :
                break
            
        match_seuil_fin = seuil
        
        val_pourcent = (match_seuil_fin-match_seuil_debut)/(ref_seuil_fin-ref_seuil_debut)
        return (match_seuil_debut-(ref_seuil_debut*val_pourcent), match_seuil_fin+((100-ref_seuil_fin)*val_pourcent))
    
    def generateClippedInput(self, parameters, context, feedback):
        
        feedback.pushInfo("......Application du mask vecteur sur l'image d'entrée")    
        clip_result = processing.run(
            'gdal:cliprasterbymasklayer',
            {
                'INPUT': parameters['INPUT'],
                'MASK' : parameters['MASK'],
                'NODATA' : 0,
                'ALPHA_BAND' : True,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(clip_result['OUTPUT'])
    
    def generateClippedReference(self, parameters, context, feedback):
        
        feedback.pushInfo("......Application du mask vecteur sur l'image de référence")    
        clip_result = processing.run(
            'gdal:cliprasterbymasklayer',
            {
                'INPUT': parameters['REFERENCE'],
                'MASK' : parameters['MASK'],
                'ALPHA_BAND' : True,
                'NODATA' : 0,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(clip_result['OUTPUT'])
        
    def processAlgorithm(self, parameters, context, feedback):
        
        source = self.parameterAsRasterLayer(
            parameters,
            self.INPUT,
            context
        )
        
        reference = self.parameterAsRasterLayer(
            parameters,
            self.REFERENCE,
            context
        )
        
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        if reference is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.REFERENCE))
        
        feedback.setProgress(5)
        feedback.pushInfo('Début clip des images')
        clip_source = self.generateClippedInput(parameters,context,feedback)
        
        feedback.setProgress(15)
        if feedback.isCanceled():
            return {'SUCCESS': False}
            
        clip_reference = self.generateClippedReference(parameters,context,feedback)
        feedback.pushInfo('Fin clip des images')

        match_provider = clip_source.dataProvider()
        ref_provider = clip_reference.dataProvider()
        
        feedback.setProgress(20)
        if feedback.isCanceled():
            return {'SUCCESS': False}
           
        feedback.pushInfo('Début Histo bande rouge')
        (min,max) = self.computeHistoMatch(1, match_provider, ref_provider)
        if min==0 and max ==0 : 
            feedback.reportError("Impossible de calculer l'histogramme",True)
            return {'SUCCESS': False}
        
        source.renderer().redContrastEnhancement().setMinimumValue(min)
        source.renderer().redContrastEnhancement().setMaximumValue(max)
        
        feedback.setProgress(40)
        if feedback.isCanceled():
            return {'SUCCESS': False}
        
        feedback.pushInfo('Début Histo bande verte')
        (min,max) = self.computeHistoMatch(2, match_provider, ref_provider)
        source.renderer().greenContrastEnhancement().setMinimumValue(min)
        source.renderer().greenContrastEnhancement().setMaximumValue(max)
        
        feedback.setProgress(65)
        if feedback.isCanceled():
            return {'SUCCESS': False}
        
        feedback.pushInfo('Début Histo bande bleue')
        (min,max) = self.computeHistoMatch(3, match_provider, ref_provider)
        source.renderer().blueContrastEnhancement().setMinimumValue(min)
        source.renderer().blueContrastEnhancement().setMaximumValue(max)
        
        feedback.setProgress(95)
        
        source.triggerRepaint()
        
        return {'SUCCESS': True}
