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
                       QgsRectangle,
                       QgsRasterLayer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingOutputBoolean)
from qgis import processing
from osgeo import gdal, osr
import numpy as np
import os


class HistogramMatching(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    REFERENCE = 'REFERENCE'
    MASK = 'MASK'
    DESATURATION = 'DESATURATION'
    SATURATION = 'SATURATION'
    DECOUPE = 'DECOUPE'
    OUTPUT = 'OUTPUT'


    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return HistogramMatching()

    def name(self):
        return 'histogramMatching'

    def displayName(self):
        return self.tr('Histogram Matching')

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
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DESATURATION,
                self.tr('Poucentage de désaturation'),
                defaultValue = 1,
                minValue = 0, 
                maxValue = 100
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SATURATION,
                self.tr('Poucentage de saturation'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue = 0,
                minValue = 0, 
                maxValue = 100
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.DECOUPE,
                self.tr('Zone de découpe finale'),
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('VRT final'),
                'VRT files (*.vrt)'
            )
        )
        
        self.addOutput(
            QgsProcessingOutputBoolean(
                'SUCCESS',
                self.tr('Success')
            )
        )
    
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
    
    def generateFinalClip(self, parameters, context, feedback):
        
        feedback.pushInfo("......Application du mask final sur l'image d'entrée")    
        clip_result = processing.run(
            'gdal:cliprasterbymasklayer',
            {
                'INPUT': parameters['INPUT'],
                'MASK' : parameters['DECOUPE'],
                'ALPHA_BAND' : True,
                'NODATA' : 0,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(clip_result['OUTPUT'])

    def generateTravailMask(self, parameters, context, feedback):
        
        feedback.pushInfo("......Création du mask de travail")    
        mask_result = processing.run(
            'gdal:rasterize',
            {
                'INPUT': parameters['MASK'],
                'BURN' : 255,
                'NODATA': 0,
                'EXTENT': parameters['MASK'],
                'UNITS' : 1,
                'WIDTH' : 0.5,
                'HEIGHT' : 0.5,
                'DATA_TYPE' : 0,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(mask_result['OUTPUT'])

    def generateFinalMask(self, parameters, context, feedback):
        
        feedback.pushInfo("......Création du mask final")    
        mask_result = processing.run(
            'gdal:rasterize',
            {
                'INPUT': parameters['DECOUPE'],
                'BURN' : 255,
                'NODATA': 0,
                'EXTENT': parameters['DECOUPE'],
                'UNITS' : 1,
                'WIDTH' : 0.5,
                'HEIGHT' : 0.5,
                'DATA_TYPE' : 0,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(mask_result['OUTPUT'])
    
    def getDesaturationTuple(self,band,ref_provider,match_provider,ref_cumulhist, match_cumulhist, pourcent_desaturation,pourcent_saturation) :
        
        max_ref = len(ref_cumulhist)
        max_match = 0
        for i in match_cumulhist :
            if i < match_cumulhist[-1]-(match_cumulhist[-1]*pourcent_saturation/100) :
                max_match+=1
            else :
                break
        
        min_ref = int(max_ref-(max_ref*pourcent_desaturation/100))
        min_match = 0
        for i in match_cumulhist :
            if (i/match_cumulhist[-1]) < (ref_cumulhist[min_ref]/ref_cumulhist[-1]) :
                min_match+=1
            else :
                break
        
        pas_match = (max_match - min_match)/pourcent_desaturation
        pas_ref = (max_ref - min_ref)/pourcent_desaturation
        
        return (min_ref, min_match, pas_match, pas_ref)
    
    def getRefValue(self,indice, match_cumulhist,ref_cumulhist, desaturation) :
        
        (min_ref, min_match, pas_match, pas_ref) = desaturation
        value = 0
        for i in ref_cumulhist :
            if (i/ref_cumulhist[-1]) < (match_cumulhist[indice]/match_cumulhist[-1]) and (value < min_ref) :
                value+=1
            else :
                break
        
        if value == min_ref :
            nbPas = (indice-min_match)/pas_match
            value = int(min_ref + nbPas*pas_ref)
        
        return value
    
    def generateVRT(self,liste_vrt,parameters,context,feedback) :
        
        vrt_result = processing.run(
            'gdal:buildvirtualraster',
            {
                'INPUT': liste_vrt,
                'RESOLUTION': 1,
                'SEPARATE': False,
                'OUTPUT': parameters['OUTPUT']
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
            
        return QgsRasterLayer(vrt_result['OUTPUT'])
    
    def generateOverview(self,parameters,context,feedback) :
        
        processing.run(
            'gdal:overviews',
            {
                'INPUT': parameters['OUTPUT'],
                'LEVELS': '2 4 8 16 32 64 128',
                'RESAMPLING': 1,
                'FORMAT': 1,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
    
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
        
        pourcent_desaturation = self.parameterAsInt(
            parameters,
            self.DESATURATION,
            context
        )
        
        pourcent_saturation = self.parameterAsDouble(
            parameters,
            self.SATURATION,
            context
        )
        
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        if reference is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.REFERENCE))
        
        feedback.setProgress(1)
        feedback.pushInfo('Début clip des images')
        clip_source = self.generateClippedInput(parameters,context,feedback)
        
        feedback.setProgress(5)
        if feedback.isCanceled():
            return {'SUCCESS': False}
            
        clip_reference = self.generateClippedReference(parameters,context,feedback)
        feedback.pushInfo('Fin clip des images')

        match_provider = clip_source.dataProvider()
        ref_provider = clip_reference.dataProvider()
        
        feedback.setProgress(10)
        if feedback.isCanceled():
            return {'SUCCESS': False}
        
        feedback.pushInfo('Calcul Histo bande rouge')
        ref_histo = ref_provider.histogram(1,0)
        match_histo = match_provider.histogram(1,0)
        
        if len(match_histo.histogramVector) == 0 : 
            feedback.reportError("Impossible de calculer l'histogramme",True)
            return {'SUCCESS': False}
        
        ref_cumulhist_red = [sum(ref_histo.histogramVector[:x+1]) for x in range(len(ref_histo.histogramVector))]
        match_cumulhist_red = [sum(match_histo.histogramVector[:x+1]) for x in range(len(match_histo.histogramVector))]
        
        desaturation_red = self.getDesaturationTuple(1,ref_provider,match_provider,ref_cumulhist_red, match_cumulhist_red, pourcent_desaturation,pourcent_saturation)
        transformation_table_red = [self.getRefValue(x,match_cumulhist_red,ref_cumulhist_red,desaturation_red) for x in range(len(match_cumulhist_red))]
        
        feedback.setProgress(20)
        if feedback.isCanceled():
            return {'SUCCESS': False}
        
        
        feedback.pushInfo('Calcul Histo bande verte')
        ref_histo = ref_provider.histogram(2,0)
        match_histo = match_provider.histogram(2,0)
        
        ref_cumulhist_green = [sum(ref_histo.histogramVector[:x+1]) for x in range(len(ref_histo.histogramVector))]
        match_cumulhist_green = [sum(match_histo.histogramVector[:x+1]) for x in range(len(match_histo.histogramVector))]
        
        desaturation_green = self.getDesaturationTuple(1,ref_provider,match_provider,ref_cumulhist_green, match_cumulhist_green, pourcent_desaturation,pourcent_saturation)
        transformation_table_green = [self.getRefValue(x,match_cumulhist_green,ref_cumulhist_green,desaturation_green) for x in range(len(match_cumulhist_green))]

        feedback.setProgress(30)
        if feedback.isCanceled():
            return {'SUCCESS': False}
        
        
        feedback.pushInfo('Calcul Histo bande bleue')
        ref_histo = ref_provider.histogram(3,0)
        match_histo = match_provider.histogram(3,0)
        
        ref_cumulhist_blue = [sum(ref_histo.histogramVector[:x+1]) for x in range(len(ref_histo.histogramVector))]
        match_cumulhist_blue = [sum(match_histo.histogramVector[:x+1]) for x in range(len(match_histo.histogramVector))]
        
        desaturation_blue = self.getDesaturationTuple(1,ref_provider,match_provider,ref_cumulhist_blue, match_cumulhist_blue, pourcent_desaturation,pourcent_saturation)
        transformation_table_blue = [self.getRefValue(x,match_cumulhist_blue,ref_cumulhist_blue,desaturation_blue) for x in range(len(match_cumulhist_blue))]

        feedback.setProgress(40)
        feedback.pushInfo('Création du Raster 8 bits')
        
        liste_vrt=[]
        mask_travail = self.parameterAsVectorLayer(
            parameters,
            self.MASK,
            context
        )
        
        mask_final = self.parameterAsVectorLayer(
            parameters,
            self.DECOUPE,
            context
        )
        masked = True
        if mask_final is None:
            mask_raster = None
            masked = False
        elif mask_final == mask_travail :
            mask_raster = self.generateTravailMask(parameters,context,feedback)
        else :
            mask_raster = self.generateFinalMask(parameters,context,feedback)
        
        feedback.setProgress(50)
        if feedback.isCanceled():
            return {'SUCCESS': False}

        final_provider = source.dataProvider()
        if masked:
            mask_provider = mask_raster.dataProvider()
            origin_extent = mask_provider.extent()
        else :
            origin_extent = final_provider.extent()
           

        if int(str(int(origin_extent.xMinimum()))[2:]) < 5000 :
            fe_xmin = int(origin_extent.xMinimum()/10000)*10000
        else :
            fe_xmin = (int(origin_extent.xMinimum()/10000)*10000) + 5000 

        if int(str(int(origin_extent.yMinimum()))[2:]) < 5000 :
            fe_ymin = int(origin_extent.yMinimum()/10000)*10000
        else :
            fe_ymin = (int(origin_extent.yMinimum()/10000)*10000) + 5000 

        if int(str(int(origin_extent.xMaximum()))[2:]) == 0 :
            fe_xmax = origin_extent.xMaximum()
        elif int(str(int(origin_extent.xMaximum()))[2:]) <= 5000 :
            fe_xmax = (int(origin_extent.xMaximum()/10000)*10000) + 5000
        else :
            fe_xmax = (int(origin_extent.xMaximum()/10000)*10000) + 10000 

        if int(str(int(origin_extent.yMaximum()))[2:]) == 0 :
            fe_ymax = origin_extent.yMaximum()
        elif int(str(int(origin_extent.yMaximum()))[2:]) <= 5000 :
            fe_ymax = (int(origin_extent.yMaximum()/10000)*10000) + 5000
        else :
            fe_ymax = (int(origin_extent.yMaximum()/10000)*10000) + 10000 

        width_dalle = int(5000 / float(source.rasterUnitsPerPixelX()))
        height_dalle = int(5000 / float(source.rasterUnitsPerPixelX()))
        
        feedback.setProgress(60)
        if feedback.isCanceled():
            return {'SUCCESS': False}
            
        if not os.path.exists(self.parameterAsFileOutput(parameters, self.OUTPUT, context).split('.')[0]):
            os.mkdir(self.parameterAsFileOutput(parameters, self.OUTPUT, context).split('.')[0])
            
        feedback.pushInfo('Création des dalles 8BITS')
        feedback.pushDebugInfo ('Extent finale : ('+str(fe_xmin)+','+str(fe_ymin)+','+str(fe_xmax)+','+str(fe_ymax)+')')
        for i in range(int((fe_xmax-fe_xmin)/5000)) :
            for j in range(int((fe_ymax-fe_ymin)/5000)) :
                
                feedback.pushInfo('..........PSUD_SAT50_'+str(fe_xmin+i*5000)+'_'+str(fe_ymin+j*5000)+'_2019_5KM')
                extent_dalle = QgsRectangle(fe_xmin+i*5000,fe_ymin+j*5000,(fe_xmin+i*5000)+5000,(fe_ymin+j*5000)+5000)

                band_red = np.zeros((height_dalle,width_dalle))
                block_source_red = final_provider.block(1, extent_dalle, width_dalle, height_dalle)
                band_green = np.zeros((height_dalle,width_dalle))
                block_source_green = final_provider.block(2, extent_dalle, width_dalle, height_dalle)
                band_blue = np.zeros((height_dalle,width_dalle))
                block_source_blue = final_provider.block(3, extent_dalle, width_dalle, height_dalle)
                band_alpha = np.zeros((height_dalle,width_dalle))
                if masked:
                    block_alpha =  mask_provider.block(1, extent_dalle, width_dalle, height_dalle)
        
                for x in range(height_dalle):
                    for y in range(width_dalle):
                        if (not block_source_red.isNoData(x,y)) and (masked and int(block_alpha.value(x,y)) == 255):
                            
                            if int(block_source_red.value(x,y)) > len(transformation_table_red)-1 :
                                band_red[x,y] = int(transformation_table_red[-1])
                                #feedback.pushDebugInfo ('Valeur hors limites : '+str(block_source_red.value(x,y)))
                            else :
                                band_red[x,y] = int(transformation_table_red[int(block_source_red.value(x,y))])
                            
                            if int(block_source_green.value(x,y)) > len(transformation_table_green)-1 :
                                band_green[x,y]=int(transformation_table_green[-1])
                                #feedback.pushDebugInfo ('Valeur hors limites : '+str(block_source_green.value(x,y)))
                            else :
                                band_green[x,y]=int(transformation_table_green[int(block_source_green.value(x,y))])
                            
                            if int(block_source_blue.value(x,y)) > len(transformation_table_blue)-1 :
                                band_blue[x,y]=int(transformation_table_blue[-1])
                                #feedback.pushDebugInfo ('Valeur hors limites : '+str(block_source_blue.value(x,y)))
                            else :
                                band_blue[x,y]=int(transformation_table_blue[int(block_source_blue.value(x,y))])
                            
                            band_alpha[x,y]=255
                
                driver = gdal.GetDriverByName('GTiff')
                ds = driver.Create(self.parameterAsFileOutput(parameters, self.OUTPUT, context).split('.')[0]+'/PSUD_SAT50_'+str(fe_xmin+i*5000)+'_'+str(fe_ymin+j*5000)+'_2019_5KM.tif', xsize=width_dalle, ysize=height_dalle, bands=4, eType=gdal.GDT_Byte, options=['compress=deflate','predictor=2'])
                ds.GetRasterBand(1).WriteArray(band_red)
                ds.GetRasterBand(2).WriteArray(band_green)
                ds.GetRasterBand(3).WriteArray(band_blue)
                ds.GetRasterBand(4).WriteArray(band_alpha)
                
                geot = [extent_dalle.xMinimum(), source.rasterUnitsPerPixelX(), 0, extent_dalle.yMaximum(), 0, -source.rasterUnitsPerPixelY()]
                ds.SetGeoTransform(geot)
                srs = osr.SpatialReference()
                srs.ImportFromEPSG(int(source.crs().authid().split(':')[1]))
                ds.SetProjection(srs.ExportToWkt())
                ds = None
                
                liste_vrt.append(self.parameterAsFileOutput(parameters, self.OUTPUT, context).split('.')[0]  + '/PSUD_SAT50_'+str(fe_xmin+i*5000)+'_'+str(fe_ymin+j*5000)+'_2019_5KM.tif')
                
                avance = int((i*((fe_ymax-fe_ymin)/5000)+j)*40/(((fe_xmax-fe_xmin)/5000)*((fe_ymax-fe_ymin)/5000)))
                feedback.setProgress(60+avance)
                if feedback.isCanceled():
                    return {'SUCCESS': False}
        
        vrt_raster = self.generateVRT(liste_vrt,parameters,context,feedback)
        self.generateOverview(parameters,context,feedback)
        
        return {'SUCCESS': True}



